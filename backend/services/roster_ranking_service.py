"""
RosterRankingService: Calculates league-wide roster rankings using NBA MCP stats and league scoring settings.
References: MatchupSimulationService, NBAMCPService, SleeperService, LeagueDataCacheService, RedisService
"""
import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime
from backend.config import settings

logger = logging.getLogger(__name__)

class RosterRankingService:
    def __init__(self, sleeper_service, redis_service, league_cache_service, nba_stats_service=None):
        self.nba_stats_service = nba_stats_service  # For per-game stats
        self.sleeper_service = sleeper_service
        self.redis_service = redis_service
        self.league_cache_service = league_cache_service
        self.cache_ttl = getattr(settings, 'ROSTER_RANKING_CACHE_TTL', 3600)
        self.cache_key_prefix = getattr(settings, 'ROSTER_RANKING_CACHE_KEY_PREFIX', 'roster_ranking')
        self.max_players = getattr(settings, 'ROSTER_RANKING_MAX_PLAYERS_TO_ANALYZE', 15)
        self.enable_category_breakdown = getattr(settings, 'ROSTER_RANKING_ENABLE_CATEGORY_BREAKDOWN', True)
        # Season selection logic (October 2025 -> use 2025-26 current, 2024-25 last)
        self.current_season = "2025-26"
        self.last_season = "2024-25"
        self.min_games_threshold = 25

    async def calculate_league_rankings(self, league_id: str, force_refresh: bool = False) -> Dict[str, Any]:
        cache_key = self._build_cache_key(league_id)
        if not force_refresh and self.redis_service and self.redis_service.is_connected():
            cached = self.redis_service.get_json(cache_key)
            if cached:
                logger.info(f"Roster rankings cache hit for league {league_id}")
                # Sanitize cached data to fix any None values
                cached = self._sanitize_rankings_data(cached)
                cached['cached'] = True
                return cached
        logger.info(f"Calculating roster rankings for league {league_id}")
        
        # Ensure league data is cached (includes scoring settings)
        scoring_settings = self.league_cache_service.get_league_scoring_settings(league_id)
        if not scoring_settings:
            logger.info(f"Scoring settings not cached, fetching league data for {league_id}")
            await self.league_cache_service.cache_league_data(league_id)
            scoring_settings = self.league_cache_service.get_league_scoring_settings(league_id)
        
        if not scoring_settings:
            logger.warning(f"No scoring settings found for league {league_id} even after fetching")
            scoring_settings = {}  # Default to empty dict
        else:
            logger.info(f"Using scoring settings with {len(scoring_settings)} categories for league {league_id}")
        
        # Use a single async context manager for all Sleeper API calls
        async with self.sleeper_service as sleeper:
            # Fetch rosters
            rosters = await sleeper.get_league_rosters(league_id)
            
            if not rosters:
                error_msg = f"No rosters found for league {league_id}. This could mean: 1) Invalid league ID, 2) League has no rosters yet, 3) Sleeper API is down, or 4) Network connectivity issue"
                logger.error(error_msg)
                
                # Try to fetch league details to verify the league exists
                try:
                    league_info = await sleeper.get_league(league_id)
                    if league_info:
                        logger.info(f"League exists: {league_info.get('name')}, but has no rosters")
                    else:
                        logger.error(f"League {league_id} does not exist or is not accessible")
                except Exception as verify_err:
                    logger.error(f"Could not verify league existence: {verify_err}")
                
                raise ValueError(error_msg)
            
            logger.info(f"Found {len(rosters)} rosters for league {league_id}")
            
            # Fetch users
            users_list = await sleeper.get_league_users(league_id)
            
            # Fetch all player data
            all_players = await sleeper.get_all_players()
        
        # Convert users list to dictionary mapping user_id -> display_name
        users = {}
        if users_list:
            for user in users_list:
                user_id = user.get('user_id')
                display_name = user.get('display_name') or user.get('username') or f"User {user_id}"
                users[user_id] = display_name
        
        logger.info(f"Found {len(users)} users for league {league_id}")
        
        if not all_players:
            logger.error("Failed to fetch player data from Sleeper")
            raise ValueError("Failed to fetch player data from Sleeper")
        
        logger.info(f"Loaded {len(all_players)} players from Sleeper")
        league_details = self.league_cache_service.get_cached_league_details(league_id) or {}
        league_name = league_details.get('name', f'League {league_id}')
        
        # Win/Loss multiplier constants
        WIN_BONUS = 0.10  # 10% bonus per win
        LOSS_PENALTY = 0.05  # 5% penalty per loss
        
        rankings = []
        for roster in rosters:
            stats = await self._calculate_roster_stats(roster, all_players, scoring_settings)
            
            # Get wins/losses from roster settings - ensure they're integers
            settings = roster.get('settings', {})
            wins = int(settings.get('wins', 0) or 0)  # Handle None values
            losses = int(settings.get('losses', 0) or 0)  # Handle None values
            
            # Log the roster data to debug win/loss values
            logger.info(f"Roster {roster.get('roster_id')}: wins={wins} (type={type(wins)}), losses={losses} (type={type(losses)}), settings={settings}")
            
            base_points = stats['total_fantasy_points']
            
            # Calculate multiplier: (1 + 0.10 * wins - 0.05 * losses)
            win_multiplier = 1 + (WIN_BONUS * wins) - (LOSS_PENALTY * losses)
            adjusted_points = base_points * win_multiplier
            
            # Calculate actual bonus/penalty values
            win_bonus_value = base_points * WIN_BONUS * wins if wins > 0 else 0.0
            loss_penalty_value = base_points * LOSS_PENALTY * losses if losses > 0 else 0.0
            
            logger.info(f"Roster {roster.get('roster_id')}: base={base_points:.2f}, win_bonus={win_bonus_value:.2f}, loss_penalty={loss_penalty_value:.2f}, adjusted={adjusted_points:.2f}")
            
            rankings.append({
                'roster_id': roster['roster_id'],
                'owner_id': roster.get('owner_id'),
                'owner_name': users.get(roster.get('owner_id'), f"Team {roster['roster_id']}"),
                'base_fantasy_points': base_points,  # Points before win/loss adjustment
                'total_fantasy_points': adjusted_points,  # Final adjusted points
                'wins': wins,
                'losses': losses,
                'win_multiplier': win_multiplier,
                'win_bonus': win_bonus_value,
                'loss_penalty': loss_penalty_value,
                'category_scores': stats['category_scores'],
                'category_percentiles': {},
                'player_breakdown': stats.get('player_breakdown', []),  # Detailed per-player contributions
                'excluded_players': stats.get('excluded_players', [])  # Players excluded due to injury
            })
        # Sort and rank by adjusted points
        rankings.sort(key=lambda r: r['total_fantasy_points'], reverse=True)
        for i, r in enumerate(rankings):
            r['rank'] = i + 1
        # Calculate percentiles
        rankings = self._calculate_category_percentiles(rankings)
        result = {
            'league_id': league_id,
            'league_name': league_name,
            'rankings': rankings,
            'total_rosters': len(rankings),
            'scoring_settings': scoring_settings,
            'last_updated': datetime.utcnow().isoformat(),
            'cached': False
        }
        if self.redis_service and self.redis_service.is_connected():
            self.redis_service.set_json(cache_key, result, self.cache_ttl)
        return result

    async def _calculate_roster_stats(self, roster: Dict, all_players: Dict, scoring_settings: Dict) -> Dict:
        player_ids = roster.get('players', [])[:self.max_players]
        total_fantasy_points = 0.0
        category_scores = {}
        player_breakdown = []
        excluded_players = []
        active_players = 0
        
        for pid in player_ids:
            player = all_players.get(pid)
            if not player:
                logger.debug(f"Player {pid} not found in all_players dict, skipping")
                excluded_players.append({
                    'name': f'Unknown Player ({pid})',
                    'status': 'unknown',
                    'reason': 'Not found in player database'
                })
                continue
            
            player_name = player.get('full_name') or player.get('name') or f'Player {pid}'
            status = (player.get('injury_status') or '').lower()
            
            # Exclude injured/out players
            if status in ['out', 'ir', 'suspension']:
                excluded_players.append({
                    'name': player_name,
                    'status': status,
                    'reason': 'Injured/Out'
                })
                continue
            
            # Get player stats using NBA Stats API (same logic as matchup simulation)
            try:
                stats = await self._get_player_season_stats(player, player_name)
            except Exception as e:
                logger.warning(f"Exception getting stats for {player_name}: {e}")
                stats = None
                
            if not stats:
                logger.debug(f"No stats returned for player: {player_name}")
                excluded_players.append({
                    'name': player_name,
                    'status': player.get('injury_status', 'active'),
                    'reason': 'No stats available'
                })
                continue
            
            active_players += 1
            
            # Log stats for first player as sample
            if not hasattr(self, '_logged_sample_stats'):
                logger.info(f"Sample stats for {player_name}: {stats}")
                self._logged_sample_stats = True
            
            cat_scores = self._calculate_fantasy_points_per_category(stats, scoring_settings)
            
            # Multiply by ACTUAL games played this season to get total production
            games_played = stats.get('actual_games_played', stats.get('games', 0))
            if games_played > 0:
                cat_scores = {k: v * games_played for k, v in cat_scores.items()}
            
            player_total = sum(cat_scores.values())
            
            # Log calculation for first player
            if not hasattr(self, '_logged_sample_calc'):
                logger.info(f"Sample calculation for {player_name}: cat_scores={cat_scores}, games={games_played}, total={player_total}")
                self._logged_sample_calc = True
            
            # Add to category totals
            for cat, val in cat_scores.items():
                category_scores[cat] = category_scores.get(cat, 0.0) + val
            total_fantasy_points += player_total
            
            # Store player breakdown for tooltip/hover
            player_breakdown.append({
                'name': player_name,
                'position': player.get('position') or 'N/A',
                'team': player.get('team') or 'FA',  # Handle None values
                'total_points': round(player_total, 2),
                'category_contributions': {k: round(v, 2) for k, v in cat_scores.items() if abs(v) > 0.01},
                'games_played': games_played,
                'season': stats.get('season_used', stats.get('season', 'N/A'))
            })
        
        # Sort players by total points and take only top 9 (max active roster spots per week)
        sorted_players = sorted(player_breakdown, key=lambda x: x['total_points'], reverse=True)
        top_9_players = sorted_players[:9]
        
        # Recalculate totals using only top 9 players
        total_fantasy_points = sum(p['total_points'] for p in top_9_players)
        category_scores = {}
        for player in top_9_players:
            for cat, val in player['category_contributions'].items():
                category_scores[cat] = category_scores.get(cat, 0.0) + val
        
        logger.info(f"Processed {active_players}/{len(player_ids)} active players for roster {roster.get('roster_id')}, using top 9 for scoring")
        return {
            'total_fantasy_points': total_fantasy_points,
            'category_scores': category_scores,
            'player_count': active_players,
            'player_breakdown': sorted_players,  # Show all players but mark top 9
            'active_players': len(top_9_players),
            'excluded_players': excluded_players
        }
    
    async def _get_player_season_stats(self, player: Dict, player_name: str) -> Optional[Dict]:
        """
        Get player's per-game stats, using current season if >= 25 games, else last season.
        Same logic as matchup simulation service.
        """
        if not self.nba_stats_service:
            logger.warning("NBA Stats Service not available, skipping player stats")
            return None
        
        try:
            # Match Sleeper player to NBA ID
            nba_person_id = self.nba_stats_service.match_sleeper_to_nba_id(player)
            if not nba_person_id:
                logger.debug(f"{player_name}: Could not match to NBA ID")
                return None
            
            # Get career stats
            career_stats = await self.nba_stats_service.fetch_player_career_stats(nba_person_id)
            if not career_stats or not career_stats.get("regular_season"):
                logger.debug(f"{player_name}: No career stats found")
                return None
            
            regular_season = career_stats["regular_season"]
            
            # Find current season (2025-2026) stats only
            current_season_stats = None
            
            # Log available seasons for debugging
            available_seasons = [(s.get("season", ""), s.get("games", 0)) for s in regular_season if s.get("games", 0) > 0]
            logger.info(f"{player_name}: Available seasons: {available_seasons[:3]}")
            
            for season_stats in regular_season:
                season_id = season_stats.get("season", "")
                gp = season_stats.get("games", 0)
                
                if self.current_season in season_id and gp > 0:
                    current_season_stats = season_stats
                    break
            
            # ONLY use 2025-2026 season stats
            selected_stats = None
            season_used = "Calculated with 2025-2026 season avgs"
            actual_games_played = 0
            
            if current_season_stats and current_season_stats.get("games", 0) > 0:
                selected_stats = current_season_stats
                actual_games_played = current_season_stats.get("games", 0)
                logger.debug(f"{player_name}: Using current season ({actual_games_played} games)")
            else:
                logger.debug(f"{player_name}: No 2025-2026 season data available")
            
            if not selected_stats:
                logger.debug(f"{player_name}: No usable season stats")
                return None
            
            # Add actual_games_played to the return value for use in total calculation
            result = dict(selected_stats)
            result['actual_games_played'] = actual_games_played
            result['season_used'] = season_used
            
            logger.info(f"{player_name}: Using {season_used} ({actual_games_played} games)")
            return result
            
        except Exception as e:
            logger.warning(f"Error getting stats for {player_name}: {e}")
            return None

    def _calculate_fantasy_points_per_category(self, stats: Dict, scoring_settings: Dict) -> Dict[str, float]:
        """
        Calculate fantasy points per category using per-game stats from NBA Stats API.
        Stats keys come from nba_stats_service transformation (ppg, rpg, apg, etc.)
        """
        # Safety check
        if not stats or not scoring_settings:
            return {}
        
        # Map Sleeper scoring categories to NBA Stats API per-game stat keys
        # These are the transformed keys from nba_stats_service
        stat_map = {
            'pts': 'ppg',      # Points per game
            'reb': 'rpg',      # Rebounds per game
            'ast': 'apg',      # Assists per game
            'stl': 'spg',      # Steals per game
            'blk': 'bpg',      # Blocks per game
            'to': 'tov',       # Turnovers per game
            'turnover': 'tov',
            'fgm': 'fgm',      # Field goals made
            'fga': 'fga',      # Field goals attempted
            'ftm': 'ftm',      # Free throws made
            'fta': 'fta',      # Free throws attempted
            'fg3m': 'fg3m',    # Three pointers made
            'tpm': 'fg3m',     # Alternate key
            'fg3a': 'fg3a',    # Three pointers attempted
            'tpa': 'fg3a',     # Alternate key
            'dreb': 'dreb',    # Defensive rebounds
            'oreb': 'oreb',    # Offensive rebounds
            'pf': 'pf',        # Personal fouls
            'plus_minus': 'plus_minus',
        }
        
        cat_scores = {}
        for cat, weight in scoring_settings.items():
            weight = float(weight)
            if weight == 0:  # Skip categories with zero weight
                cat_scores[cat] = 0.0
                continue
            
            val = 0.0
            
            # Handle special calculated categories
            if cat in ['fgmi', 'ftmi', 'fg3mi', 'tpmi']:
                # Missed shots
                if cat == 'fgmi':
                    val = float(stats.get('fga', 0)) - float(stats.get('fgm', 0))
                elif cat == 'ftmi':
                    val = float(stats.get('fta', 0)) - float(stats.get('ftm', 0))
                elif cat in ['fg3mi', 'tpmi']:
                    val = float(stats.get('fg3a', 0)) - float(stats.get('fg3m', 0))
            elif cat in ['dd', 'td']:
                # Double-doubles and triple-doubles
                # These would require game log data, so we'll estimate based on averages
                pts = float(stats.get('ppg', 0))
                reb = float(stats.get('rpg', 0))
                ast = float(stats.get('apg', 0))
                stl = float(stats.get('spg', 0))
                blk = float(stats.get('bpg', 0))
                
                # Count how many categories are >= 10
                double_digit_cats = sum(1 for x in [pts, reb, ast, stl, blk] if x >= 10)
                
                if cat == 'dd' and double_digit_cats >= 2:
                    val = 0.3  # Rough estimate: 30% chance per game
                elif cat == 'td' and double_digit_cats >= 3:
                    val = 0.1  # Rough estimate: 10% chance per game
            else:
                # Regular per-game stats
                stat_key = stat_map.get(cat, cat)
                val = float(stats.get(stat_key, 0))
            
            cat_scores[cat] = val * weight
        
        return cat_scores

    def _calculate_category_percentiles(self, rankings: List[Dict]) -> List[Dict]:
        if not rankings:
            return rankings
        categories = set()
        for r in rankings:
            categories.update(r['category_scores'].keys())
        max_vals = {cat: max((r['category_scores'].get(cat, 0) for r in rankings), default=1) for cat in categories}
        for r in rankings:
            r['category_percentiles'] = {cat: (r['category_scores'].get(cat, 0) / max_vals[cat] * 100 if max_vals[cat] else 0) for cat in categories}
        return rankings

    def _build_cache_key(self, league_id: str) -> str:
        return f"{self.cache_key_prefix}:{league_id}"

    def invalidate_rankings_cache(self, league_id: str) -> bool:
        cache_key = self._build_cache_key(league_id)
        if self.redis_service and self.redis_service.is_connected():
            self.redis_service.delete(cache_key)
            logger.info(f"Cleared roster rankings cache for league {league_id}")
            return True
        return False

    def get_cache_stats(self, league_id: str) -> Dict:
        cache_key = self._build_cache_key(league_id)
        cached = False
        ttl = None
        last_updated = None
        if self.redis_service and self.redis_service.is_connected():
            cached = self.redis_service.exists(cache_key)
            ttl = self.redis_service.get_ttl(cache_key)
            data = self.redis_service.get_json(cache_key)
            if data:
                last_updated = data.get('last_updated')
        return {
            'league_id': league_id,
            'cached': bool(cached),
            'ttl_remaining': ttl,
            'last_updated': last_updated
        }

    def generate_roster_analysis(self, roster_data: Dict, all_rankings: List[Dict]) -> Dict[str, Any]:
        """
        Generate AI-powered analysis of a roster's strengths, weaknesses, and outlook.
        Returns structured analysis with key strengths, weaknesses, and overall assessment.
        """
        owner_name = roster_data.get('owner_name', 'Unknown')
        rank = roster_data.get('rank', 0)
        total_rosters = len(all_rankings)
        category_scores = roster_data.get('category_scores', {})
        category_percentiles = roster_data.get('category_percentiles', {})
        player_breakdown = roster_data.get('player_breakdown', [])
        excluded_players = roster_data.get('excluded_players', [])
        total_points = roster_data.get('total_fantasy_points', 0)
        
        # Find top strengths (>80th percentile)
        strengths = []
        for cat, percentile in sorted(category_percentiles.items(), key=lambda x: x[1], reverse=True):
            if percentile >= 80:
                score = category_scores.get(cat, 0)
                rank_text = ""
                if percentile >= 99:
                    rank_text = " (league best!)"
                elif percentile >= 95:
                    rank_text = " (elite!)"
                elif percentile >= 90:
                    rank_text = " (top tier)"
                
                cat_display = cat.upper() if len(cat) <= 3 else cat.replace('_', ' ').title()
                strengths.append(f"+{score:.1f} from {cat_display} ({percentile:.1f} percentile{rank_text})")
        
        # Find weaknesses (negative scores or <50th percentile)
        weaknesses = []
        for cat, score in sorted(category_scores.items(), key=lambda x: x[1]):
            percentile = category_percentiles.get(cat, 50)
            if score < 0 or percentile < 50:
                cat_display = cat.upper() if len(cat) <= 3 else cat.replace('_', ' ').title()
                if score < 0:
                    weaknesses.append(f"{score:.1f} from {cat_display} (negative impact)")
                else:
                    weaknesses.append(f"+{score:.1f} from {cat_display} ({percentile:.1f} percentile - below average)")
        
        # Get top players
        top_players = sorted(player_breakdown, key=lambda p: p.get('total_points', 0), reverse=True)[:3]
        top_player_names = [p.get('name', 'Unknown') for p in top_players]
        
        # Get injured/out players
        injured_count = len(excluded_players)
        injured_names = [p.get('name', 'Unknown') for p in excluded_players[:3]]  # Top 3 injured
        
        # Generate analysis text
        analysis_parts = []
        
        # Mention top players and their contribution
        if top_player_names:
            top_3_str = ", ".join(top_player_names[:2])
            if len(top_player_names) > 2:
                top_3_str += f", and {top_player_names[2]}"
            analysis_parts.append(f"{owner_name} is led by {top_3_str}")
        
        # Mention dominant categories
        if len(strengths) >= 3:
            dominant_cats = [s.split(' from ')[1].split(' (')[0] for s in strengths[:2]]
            analysis_parts.append(f"dominating in {' and '.join(dominant_cats)}")
        
        # Mention injury concerns
        if injured_count > 0:
            if injured_count == 1:
                analysis_parts.append(f"Currently dealing with {injured_names[0]} out")
            elif injured_count <= 3:
                analysis_parts.append(f"Missing {', '.join(injured_names)}")
            else:
                analysis_parts.append(f"Dealing with {injured_count} injuries ({', '.join(injured_names[:2])}, etc.)")
        
        # Mention ranking position
        if rank == 1:
            analysis_parts.append(f"Currently #1 in the league with elite production")
        elif rank <= 3:
            analysis_parts.append(f"Sitting at #{rank} with championship potential")
        elif rank <= total_rosters // 2:
            analysis_parts.append(f"Currently #{rank}, firmly in playoff contention")
        else:
            analysis_parts.append(f"Ranked #{rank}, needs improvement to make playoffs")
        
        # Health/outlook
        if injured_count >= 3:
            analysis_parts.append(f"When healthy, this team could jump {min(3, rank - 1)} spots")
        elif injured_count > 0:
            analysis_parts.append(f"Health will be key to climbing the rankings")
        
        analysis = ". ".join(analysis_parts) + "."
        
        return {
            'owner_name': owner_name,
            'rank': rank,
            'total_points': total_points,
            'strengths': strengths[:5],  # Top 5 strengths
            'weaknesses': weaknesses[:5],  # Top 5 weaknesses
            'analysis': analysis,
            'top_players': top_player_names,
            'injured_players': injured_names,
            'injured_count': injured_count
        }

    def _sanitize_rankings_data(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Sanitize cached rankings data to fix None values that cause validation errors.
        Also recalculates win/loss bonuses if they're missing (for backward compatibility).
        This is a migration helper for old cached data.
        """
        if not data or 'rankings' not in data:
            return data
        
        WIN_BONUS = 0.10  # 10% bonus per win
        LOSS_PENALTY = 0.05  # 5% penalty per loss
        
        for ranking in data['rankings']:
            # Fix player_breakdown None values
            if 'player_breakdown' in ranking:
                for player in ranking['player_breakdown']:
                    # Fix None team values
                    if player.get('team') is None:
                        player['team'] = 'FA'
                    # Fix None position values
                    if player.get('position') is None:
                        player['position'] = 'N/A'
                    # Fix None name values (shouldn't happen but be safe)
                    if player.get('name') is None:
                        player['name'] = 'Unknown'
            
            # Recalculate win/loss bonuses and total points if needed (backward compatibility)
            base_points = ranking.get('base_fantasy_points', 0)
            wins = ranking.get('wins', 0) or 0
            losses = ranking.get('losses', 0) or 0
            
            # Check if we need to recalculate (if bonus fields missing or total == base)
            total_points = ranking.get('total_fantasy_points', 0)
            needs_recalc = False
            
            if base_points > 0 and (wins > 0 or losses > 0):
                # If total_fantasy_points equals base_fantasy_points, it wasn't adjusted
                if abs(total_points - base_points) < 0.01:
                    needs_recalc = True
                # Or if bonus fields are missing
                elif 'win_bonus' not in ranking or 'loss_penalty' not in ranking:
                    needs_recalc = True
            
            if needs_recalc:
                # Recalculate everything
                win_multiplier = 1 + (WIN_BONUS * wins) - (LOSS_PENALTY * losses)
                adjusted_points = base_points * win_multiplier
                win_bonus_value = base_points * WIN_BONUS * wins if wins > 0 else 0.0
                loss_penalty_value = base_points * LOSS_PENALTY * losses if losses > 0 else 0.0
                
                ranking['total_fantasy_points'] = adjusted_points
                ranking['win_multiplier'] = win_multiplier
                ranking['win_bonus'] = win_bonus_value
                ranking['loss_penalty'] = loss_penalty_value
                
                logger.info(f"Recalculated for roster {ranking.get('roster_id')}: base={base_points:.2f}, adjusted={adjusted_points:.2f}, win_bonus={win_bonus_value:.2f}")
        
        return data
