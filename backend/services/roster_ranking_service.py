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
        
        rosters = await self.sleeper_service.get_league_rosters(league_id)
        if not rosters:
            logger.error(f"No rosters found for league {league_id}")
            raise ValueError(f"No rosters found for league {league_id}")
        
        logger.info(f"Found {len(rosters)} rosters for league {league_id}")
        
        users_list = await self.sleeper_service.get_league_users(league_id)
        # Convert users list to dictionary mapping user_id -> display_name
        users = {}
        if users_list:
            for user in users_list:
                user_id = user.get('user_id')
                display_name = user.get('display_name') or user.get('username') or f"User {user_id}"
                users[user_id] = display_name
        
        logger.info(f"Found {len(users)} users for league {league_id}")
        
        # Get all player data for detailed info
        all_players = await self.sleeper_service.get_all_players()
        if not all_players:
            logger.error("Failed to fetch player data from Sleeper")
            raise ValueError("Failed to fetch player data from Sleeper")
        
        logger.info(f"Loaded {len(all_players)} players from Sleeper")
        league_details = self.league_cache_service.get_cached_league_details(league_id) or {}
        league_name = league_details.get('name', f'League {league_id}')
        rankings = []
        for roster in rosters:
            stats = await self._calculate_roster_stats(roster, all_players, scoring_settings)
            rankings.append({
                'roster_id': roster['roster_id'],
                'owner_id': roster.get('owner_id'),
                'owner_name': users.get(roster.get('owner_id'), f"Team {roster['roster_id']}"),
                'total_fantasy_points': stats['total_fantasy_points'],
                'wins': roster.get('settings', {}).get('wins', 0),
                'losses': roster.get('settings', {}).get('losses', 0),
                'category_scores': stats['category_scores'],
                'category_percentiles': {},
                'player_breakdown': stats.get('player_breakdown', []),  # Detailed per-player contributions
                'active_players': stats.get('active_players', 0),
                'excluded_players': stats.get('excluded_players', [])  # Players excluded due to injury
            })
        # Sort and rank
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
                'position': player.get('position', 'N/A'),
                'team': player.get('team', 'N/A'),
                'total_points': round(player_total, 2),
                'category_contributions': {k: round(v, 2) for k, v in cat_scores.items() if abs(v) > 0.01},
                'games_played': games_played,
                'season': stats.get('season_used', stats.get('season', 'N/A'))
            })
        
        logger.info(f"Processed {active_players}/{len(player_ids)} active players for roster {roster.get('roster_id')}")
        return {
            'total_fantasy_points': total_fantasy_points,
            'category_scores': category_scores,
            'player_count': active_players,
            'player_breakdown': sorted(player_breakdown, key=lambda x: x['total_points'], reverse=True),
            'active_players': active_players,
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
            
            # Find appropriate season stats
            current_season_stats = None
            last_season_stats = None
            most_recent_stats = None
            
            # Log available seasons for debugging
            available_seasons = [(s.get("season", ""), s.get("games", 0)) for s in regular_season if s.get("games", 0) > 0]
            logger.info(f"{player_name}: Available seasons: {available_seasons[:3]}")
            
            for season_stats in regular_season:
                season_id = season_stats.get("season", "")
                gp = season_stats.get("games", 0)
                
                # Track most recent season with games
                if not most_recent_stats or season_id > most_recent_stats.get("season", ""):
                    if gp > 0:
                        most_recent_stats = season_stats
                
                if self.current_season in season_id:
                    current_season_stats = season_stats
                elif self.last_season in season_id:
                    last_season_stats = season_stats
            
            # ALWAYS use current season games for the calculation (actual production this year)
            # But use per-game stats from last season if current season sample is too small
            selected_stats = None
            season_used = None
            actual_games_played = 0  # Games played THIS season (for total calculation)
            
            if current_season_stats and current_season_stats.get("games", 0) >= self.min_games_threshold:
                # Enough games in current season to use it for both per-game and total
                selected_stats = current_season_stats
                actual_games_played = current_season_stats.get("games", 0)
                season_used = self.current_season
                logger.debug(f"{player_name}: Using current season ({actual_games_played} games)")
            elif current_season_stats and current_season_stats.get("games", 0) > 0:
                # Use current season games for total, but last season per-game rates
                actual_games_played = current_season_stats.get("games", 0)
                if last_season_stats and last_season_stats.get("games", 0) > 0:
                    selected_stats = last_season_stats  # Per-game rates from last season
                    season_used = f"{self.last_season} (rates) × {actual_games_played} games"
                    logger.debug(f"{player_name}: Using last season rates × {actual_games_played} current games")
                else:
                    # No last season data, use current season even if small sample
                    selected_stats = current_season_stats
                    season_used = self.current_season
                    logger.debug(f"{player_name}: Using current season only ({actual_games_played} games)")
            elif last_season_stats and last_season_stats.get("games", 0) > 0:
                # No current season data at all, use last season
                selected_stats = last_season_stats
                actual_games_played = last_season_stats.get("games", 0)
                season_used = self.last_season
                logger.debug(f"{player_name}: Using last season ({actual_games_played} games)")
            elif most_recent_stats:
                # Use most recent season with data as last resort
                selected_stats = most_recent_stats
                actual_games_played = most_recent_stats.get("games", 0)
                season_used = most_recent_stats.get("season", "recent")
                logger.debug(f"{player_name}: Using most recent season {season_used} ({actual_games_played} games)")
            
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
