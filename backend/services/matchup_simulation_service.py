"""
Matchup Simulation Service

Simulates fantasy basketball matchups using NBA schedule data and player projections.
Calculates win probability for next N weeks with/without trade.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio

from backend.services.sleeper_service import SleeperService
from backend.services.nba_stats_service import NBAStatsService
from backend.config import settings


logger = logging.getLogger(__name__)


class MatchupSimulationService:
    """Service for simulating fantasy matchups with trade scenarios"""
    
    def __init__(
        self,
        sleeper_service: SleeperService,
        nba_stats_service: NBAStatsService
    ):
        self.sleeper_service = sleeper_service
        self.nba_stats_service = nba_stats_service
        # Cache schedule during a single simulation to avoid redundant fetches
        self._schedule_cache: Dict[str, List[Dict[str, Any]]] = {}
    
    async def simulate_next_weeks(
        self,
        league_id: str,
        user_roster_id: int,
        opponent_roster_id: int,  # NOTE: This parameter is now IGNORED - we get real matchups from Sleeper
        user_players_out: List[str],
        user_players_in: List[str],
        weeks: int = 3
    ) -> Dict[str, Any]:
        """
        Simulate fantasy matchups for next N weeks with/without trade.
        
        **NEW BEHAVIOR**: Simulates against ACTUAL scheduled opponents for each week,
        not just a single opponent. Gets matchup schedule from Sleeper API.
        
        Args:
            league_id: Sleeper league ID
            user_roster_id: User's roster ID
            opponent_roster_id: IGNORED - kept for API compatibility only
            user_players_out: Players user trades away
            user_players_in: Players user receives
            weeks: Number of weeks to simulate (default 3)
            
        Returns:
            Dict with week-by-week simulation results:
            {
                "weeks": [
                    {
                        "week": 15,
                        "opponent_roster_id": 2,
                        "opponent_team_name": "Team Name",
                        "without_trade": {...},
                        "with_trade": {...}
                    },
                    ...
                ],
                "summary": {
                    "total_wins_without": 1,
                    "total_wins_with": 2,
                    "wins_improvement": 1
                },
                "disclaimer": "..."
            }
        """
        try:
            # Clear schedule cache for this simulation
            self._schedule_cache = {}
            
            logger.info(f"Simulating {weeks} weeks for league {league_id} (user roster {user_roster_id})")
            
            # Fetch league info to get current week and settings
            league_info = await self.sleeper_service.get_league_info(league_id)
            if not league_info:
                raise ValueError("Could not fetch league information")
            
            scoring_settings = league_info.get("scoring_settings", {})
            current_week = league_info.get("settings", {}).get("leg", 1)  # Current matchup week
            
            logger.info(f"Current league week: {current_week}")
            
            # Calculate which weeks to simulate (next N weeks starting from current_week + 1)
            weeks_to_simulate = list(range(current_week + 1, current_week + weeks + 1))
            logger.info(f"Simulating weeks: {weeks_to_simulate}")
            
            # Fetch matchups for these weeks
            matchups_by_week = await self.sleeper_service.get_league_matchups_bulk(league_id, weeks_to_simulate)
            
            # Fetch league users for team names
            league_users = await self.sleeper_service.get_league_users(league_id)
            user_lookup = {user.get("user_id"): user for user in (league_users or [])}
            
            # Fetch all rosters once
            all_rosters = await self.sleeper_service.get_league_rosters(league_id)
            roster_lookup = {roster.get("roster_id"): roster for roster in (all_rosters or [])}
            
            user_roster = roster_lookup.get(user_roster_id)
            if not user_roster:
                raise ValueError(f"Could not find user roster {user_roster_id}")
            
            all_players = await self.sleeper_service.get_all_players()
            
            # Simulate each week
            weekly_results = []
            
            for week_num in weeks_to_simulate:
                logger.info(f"Simulating week {week_num}...")
                
                # Get matchups for this week
                week_matchups = matchups_by_week.get(week_num, [])
                if not week_matchups:
                    logger.warning(f"No matchups found for week {week_num}, skipping")
                    continue
                
                # Find user's matchup
                user_matchup = None
                for matchup in week_matchups:
                    if matchup.get("roster_id") == user_roster_id:
                        user_matchup = matchup
                        break
                
                if not user_matchup:
                    logger.warning(f"User roster {user_roster_id} not found in week {week_num} matchups")
                    continue
                
                matchup_id = user_matchup.get("matchup_id")
                if not matchup_id:
                    logger.warning(f"No matchup_id for user in week {week_num}, might be bye week")
                    continue
                
                # Find opponent with same matchup_id
                opponent_matchup = None
                for matchup in week_matchups:
                    if matchup.get("matchup_id") == matchup_id and matchup.get("roster_id") != user_roster_id:
                        opponent_matchup = matchup
                        break
                
                if not opponent_matchup:
                    logger.warning(f"No opponent found for user in week {week_num}")
                    continue
                
                opponent_roster_id_this_week = opponent_matchup.get("roster_id")
                opponent_roster = roster_lookup.get(opponent_roster_id_this_week)
                
                if not opponent_roster:
                    logger.warning(f"Could not find opponent roster {opponent_roster_id_this_week}")
                    continue
                
                # Get opponent team name
                opponent_owner_id = opponent_roster.get("owner_id")
                opponent_user = user_lookup.get(opponent_owner_id, {})
                opponent_team_name = (
                    opponent_user.get("metadata", {}).get("team_name") or
                    opponent_user.get("display_name") or
                    opponent_user.get("username") or
                    f"Team {opponent_roster_id_this_week}"
                )
                
                # Calculate date range for this week (7 days)
                # Estimate: weeks start on Mondays
                from datetime import datetime, timedelta
                today = datetime.now().date()
                days_until_week = (week_num - current_week) * 7
                week_start = today + timedelta(days=days_until_week)
                week_end = week_start + timedelta(days=6)
                
                logger.info(f"Week {week_num}: {week_start} to {week_end}, opponent: {opponent_team_name}")
                
                # Calculate projections for this week
                logger.info(f"→ Calculating opponent ({opponent_team_name}) projection...")
                opponent_points = await self._calculate_projected_points_via_mcp(
                    roster=opponent_roster,
                    all_players=all_players,
                    scoring_settings=scoring_settings,
                    start_date=week_start,
                    end_date=week_end,
                    players_to_remove=[],
                    players_to_add=[]
                )
                
                logger.info(f"→ Calculating user projection WITHOUT trade...")
                user_points_without = await self._calculate_projected_points_via_mcp(
                    roster=user_roster,
                    all_players=all_players,
                    scoring_settings=scoring_settings,
                    start_date=week_start,
                    end_date=week_end,
                    players_to_remove=[],
                    players_to_add=[]
                )
                
                logger.info(f"→ Calculating user projection WITH trade...")
                user_points_with = await self._calculate_projected_points_via_mcp(
                    roster=user_roster,
                    all_players=all_players,
                    scoring_settings=scoring_settings,
                    start_date=week_start,
                    end_date=week_end,
                    players_to_remove=user_players_out,
                    players_to_add=user_players_in
                )
                
                # Calculate win probabilities
                win_prob_without = self._calculate_win_probability(user_points_without, opponent_points)
                win_prob_with = self._calculate_win_probability(user_points_with, opponent_points)
                
                # Determine winners
                wins_without = 1 if user_points_without > opponent_points else 0
                wins_with = 1 if user_points_with > opponent_points else 0
                
                weekly_results.append({
                    "week": week_num,
                    "opponent_roster_id": opponent_roster_id_this_week,
                    "opponent_team_name": opponent_team_name,
                    "without_trade": {
                        "projected_points": round(user_points_without, 2),
                        "opponent_projected_points": round(opponent_points, 2),
                        "win_probability": round(win_prob_without, 2),
                        "wins": wins_without
                    },
                    "with_trade": {
                        "projected_points": round(user_points_with, 2),
                        "opponent_projected_points": round(opponent_points, 2),
                        "win_probability": round(win_prob_with, 2),
                        "wins": wins_with
                    },
                    "point_differential": round(user_points_with - user_points_without, 2)
                })
                
                logger.info(f"Week {week_num} complete: without={user_points_without:.1f}, with={user_points_with:.1f}, opponent={opponent_points:.1f}")
            
            # Calculate summary
            total_wins_without = sum(w["without_trade"]["wins"] for w in weekly_results)
            total_wins_with = sum(w["with_trade"]["wins"] for w in weekly_results)
            total_weeks = len(weekly_results)
            total_losses_without = total_weeks - total_wins_without
            total_losses_with = total_weeks - total_wins_with
            
            result = {
                "weeks": weekly_results,
                "summary": {
                    "total_wins_without": total_wins_without,
                    "total_losses_without": total_losses_without,
                    "total_wins_with": total_wins_with,
                    "total_losses_with": total_losses_with,
                    "wins_improvement": total_wins_with - total_wins_without,
                    "weeks_simulated": total_weeks
                },
                "disclaimer": (
                    "Note: Projections currently use average statistics from the 2024-25 season due to limited 2025-26 season data. "
                    "Once enough games have been played in the current season (typically 25+ games per player), "
                    "projections will automatically switch to using current season performance data for more accurate results."
                )
            }
            
            logger.info(f"Simulation complete - {len(weekly_results)} weeks simulated, wins improvement: {total_wins_with - total_wins_without}")
            return result
            
        except Exception as e:
            logger.error(f"Error simulating matchup: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            raise
    
    async def _calculate_projected_points_via_mcp(
        self,
        roster: Dict[str, Any],
        all_players: Dict[str, Dict],
        scoring_settings: Dict[str, float],
        start_date: datetime,
        end_date: datetime,
        players_to_remove: List[str] = None,
        players_to_add: List[str] = None
    ) -> float:
        """
        Calculate projected fantasy points for a roster over a date range.
        
        Uses NBA MCP to fetch player stats and applies league scoring.
        
        Args:
            roster: Sleeper roster object
            all_players: All players dict
            scoring_settings: League scoring settings
            start_date: Simulation start date
            end_date: Simulation end date
            players_to_remove: Player IDs to exclude (for trade simulation)
            players_to_add: Player IDs to include (for trade simulation)
            
        Returns:
            Total projected fantasy points
        """
        try:
            # Get active roster (apply trade modifications)
            active_players = roster.get("players", []) or []
            
            if players_to_remove:
                active_players = [p for p in active_players if p not in players_to_remove]
            if players_to_add:
                active_players.extend(players_to_add)
            
            if not active_players:
                return 0.0
            
            # Prepare tasks for parallel execution
            tasks = []
            player_data = []
            
            for player_id in active_players:
                player = all_players.get(player_id, {})
                full_name = player.get("full_name", player_id)
                
                # Skip if player is injured/out
                injury_status = player.get("injury_status", "")
                if injury_status in ["Out", "IR", "Suspension"]:
                    logger.info(f"Skipping {full_name} - {injury_status}")
                    continue
                
                # Create task for this player
                tasks.append(self._get_player_projection_via_mcp(
                    player=player,
                    scoring_settings=scoring_settings,
                    start_date=start_date,
                    end_date=end_date
                ))
                player_data.append((player_id, full_name))
            
            # Execute all player projections in parallel
            if not tasks:
                return 0.0
            
            logger.debug(f"Calculating {len(tasks)} player projections in parallel...")
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Sum up results
            total_points = 0.0
            for (player_id, full_name), result in zip(player_data, results):
                if isinstance(result, Exception):
                    logger.warning(f"Could not project {full_name}: {result}")
                    continue
                
                if result > 0:
                    total_points += result
                    logger.debug(f"Added {full_name}: {result:.1f} pts (running total: {total_points:.1f})")
            
            logger.info(f"Total projected points: {total_points:.1f} ({len(active_players)} players)")
            return total_points
            
        except Exception as e:
            logger.error(f"Error calculating projected points: {e}")
            raise
    
    async def _get_player_projection_via_mcp(
        self,
        player: Dict[str, Any],
        scoring_settings: Dict[str, float],
        start_date: datetime,
        end_date: datetime
    ) -> float:
        """
        Project fantasy points for a single player over date range.
        
        Uses NBA MCP to fetch recent stats and schedule to estimate output.
        
        Args:
            player: Player dict from Sleeper
            scoring_settings: League scoring settings
            start_date: Projection start date
            end_date: Projection end date
            
        Returns:
            Projected fantasy points for period
        """
        try:
            full_name = player.get("full_name", "Unknown")
            team = player.get("team", "")
            
            if not team or team == "FA":
                logger.debug(f"{full_name}: Free agent or no team, returning 0")
                return 0.0
            
            # Get upcoming games count for player's team
            # Convert to date objects if datetime objects are passed
            start = start_date.date() if isinstance(start_date, datetime) else start_date
            end = end_date.date() if isinstance(end_date, datetime) else end_date
            
            # Fetch season schedule and filter by date range
            # Determine season year from start date
            if start.month >= 10:  # Oct-Dec
                season = str(start.year)
            else:  # Jan-Sep
                season = str(start.year - 1)
            
            # Use cached schedule if available
            if season not in self._schedule_cache:
                logger.debug(f"Fetching and caching schedule for season {season}")
                schedule = await self.nba_stats_service.fetch_season_schedule(season=season)
                self._schedule_cache[season] = schedule or []
            else:
                logger.debug(f"Using cached schedule for season {season}")
                schedule = self._schedule_cache[season]
            
            if not schedule:
                logger.debug(f"{full_name} ({team}): Could not fetch schedule")
                return 0.0
            
            # Filter games by date range and team
            team_games = [
                game for game in schedule
                if game.get("game_date") and start <= game.get("game_date") <= end
                and (game.get("home_team_tricode") == team or game.get("away_team_tricode") == team)
            ]
            
            num_games = len(team_games)
            
            if num_games == 0:
                logger.debug(f"{full_name} ({team}): No games {start} to {end}")
                return 0.0
            
            # Get player's PPG using NBA stats
            # Try current season first, fall back to last season if < 25 games
            ppg = await self._get_player_ppg(player, full_name)
            
            # Project over simulation period
            projected_total = ppg * num_games
            
            logger.info(f"{full_name} ({team}): {ppg:.2f} PPG × {num_games} games ({start} to {end}) = {projected_total:.2f}")
            return projected_total
            
        except Exception as e:
            logger.warning(f"Error projecting player: {e}")
            return 0.0
    
    def _calculate_fantasy_points(
        self,
        stats: Dict[str, Any],
        scoring_settings: Dict[str, float]
    ) -> float:
        """
        Calculate fantasy points from player stats using league scoring.
        
        Args:
            stats: Player stats dict (from NBA MCP)
            scoring_settings: League scoring settings
            
        Returns:
            Fantasy points per game
        """
        points = 0.0
        
        # Map NBA stats to Sleeper scoring categories
        stat_mapping = {
            "pts": "PTS",
            "reb": "REB",
            "ast": "AST",
            "blk": "BLK",
            "stl": "STL",
            "fgm": "FGM",
            "fga": "FGA",
            "ftm": "FTM",
            "fta": "FTA",
            "fg3m": "FG3M",
            "fg3a": "FG3A",
            "turnover": "TOV"
        }
        
        for sleeper_key, nba_key in stat_mapping.items():
            if sleeper_key in scoring_settings and nba_key in stats:
                stat_value = stats.get(nba_key, 0.0)
                scoring_value = scoring_settings.get(sleeper_key, 0.0)
                points += stat_value * scoring_value
        
        # Handle calculated stats
        if "fgmi" in scoring_settings:  # FG Missed = FGA - FGM
            fga = stats.get("FGA", 0.0)
            fgm = stats.get("FGM", 0.0)
            points += (fga - fgm) * scoring_settings["fgmi"]
        
        if "ftmi" in scoring_settings:  # FT Missed = FTA - FTM
            fta = stats.get("FTA", 0.0)
            ftm = stats.get("FTM", 0.0)
            points += (fta - ftm) * scoring_settings["ftmi"]
        
        if "fg3mi" in scoring_settings:  # 3PT Missed = FG3A - FG3M
            fg3a = stats.get("FG3A", 0.0)
            fg3m = stats.get("FG3M", 0.0)
            points += (fg3a - fg3m) * scoring_settings["fg3mi"]
        
        # TODO: Add double-double / triple-double detection if needed
        # This requires game-by-game logs, not season averages
        
        return points
    
    def _calculate_win_probability(
        self,
        user_points: float,
        opponent_points: float
    ) -> float:
        """
        Calculate win probability based on projected point differential.
        
        Uses simple logistic model:
        - If user > opponent by 20+: ~90% win probability
        - If even: 50%
        - If user < opponent by 20+: ~10%
        
        Args:
            user_points: User's projected points
            opponent_points: Opponent's projected points
            
        Returns:
            Win probability percentage (0-100)
        """
        if opponent_points == 0:
            return 100.0 if user_points > 0 else 50.0
        
        # Calculate point differential
        diff = user_points - opponent_points
        
        # Simple logistic curve: P(win) = 1 / (1 + e^(-k*diff))
        # where k controls steepness (use k=0.05 for reasonable spread)
        import math
        k = 0.05
        prob = 1.0 / (1.0 + math.exp(-k * diff))
        
        # Convert to percentage
        return prob * 100.0
    
    async def _get_player_ppg(self, player: Dict[str, Any], player_name: str) -> float:
        """
        Get player's fantasy points per game average.
        Uses current season if available and >= 25 games played.
        Falls back to last season if current season < 25 games.
        
        Args:
            player: Player dictionary from Sleeper API
            player_name: Player's full name
            
        Returns:
            Fantasy points per game (defaults to 25.0 if no data)
        """
        try:
            # Extract NBA person ID from Sleeper player data using name matching
            nba_person_id = self.nba_stats_service.match_sleeper_to_nba_id(player)
            
            if not nba_person_id:
                logger.debug(f"{player_name}: Could not match to NBA ID, using default PPG")
                return 25.0
            
            # Get career stats from NBA Stats API
            career_stats = await self.nba_stats_service.fetch_player_career_stats(nba_person_id)
            
            if not career_stats or not career_stats.get("regular_season"):
                logger.debug(f"{player_name}: No career stats found, using default PPG")
                return 25.0
            
            # We're in October 2025, so 2025-26 season is just starting
            # Use current season if >= 25 games, otherwise use last completed season (2024-25)
            current_season = "2025-26"
            last_season = "2024-25"
            
            regular_season = career_stats["regular_season"]
            
            # Try to find current season stats
            current_season_stats = None
            last_season_stats = None
            most_recent_stats = None  # Fallback to most recent season with data
            
            for season_stats in regular_season:
                season_id = season_stats.get("season", "")  # Transformed key
                gp = season_stats.get("games", 0)  # Transformed key
                
                # Track most recent season (for fallback)
                if not most_recent_stats or season_id > most_recent_stats.get("season", ""):
                    if gp > 0:  # Only consider seasons with games played
                        most_recent_stats = season_stats
                
                if current_season in season_id:
                    current_season_stats = season_stats
                elif last_season in season_id:
                    last_season_stats = season_stats
            
            # Use current season if >= 25 games, otherwise fall back to last season or most recent
            selected_stats = None
            season_used = None
            
            if current_season_stats and current_season_stats.get("games", 0) >= 25:
                selected_stats = current_season_stats
                season_used = current_season
                logger.debug(f"{player_name}: Using current season ({current_season_stats.get('games')} games)")
            elif last_season_stats and last_season_stats.get("games", 0) > 0:
                selected_stats = last_season_stats
                season_used = last_season
                logger.debug(f"{player_name}: Using last season ({last_season_stats.get('games')} games)")
            elif most_recent_stats:
                selected_stats = most_recent_stats
                season_used = most_recent_stats.get("season", "recent")
                logger.debug(f"{player_name}: Using most recent season {season_used} ({most_recent_stats.get('games')} games)")
            
            if not selected_stats:
                logger.debug(f"{player_name}: No usable season stats, using default PPG")
                return 25.0
            
            # Calculate fantasy PPG using league scoring settings
            # Using transformed keys from nba_stats_service
            pts = selected_stats.get("ppg", 0.0)  # Already per-game
            reb = selected_stats.get("rpg", 0.0)  # Already per-game
            ast = selected_stats.get("apg", 0.0)  # Already per-game
            stl = selected_stats.get("spg", 0.0)  # Already per-game
            blk = selected_stats.get("bpg", 0.0)  # Already per-game
            tov = selected_stats.get("tov", 0.0)  # Already per-game
            
            fantasy_ppg = pts + (1.2 * reb) + (1.5 * ast) + (3 * stl) + (3 * blk) - tov
            
            logger.info(f"{player_name}: {fantasy_ppg:.2f} fantasy PPG ({season_used} season)")
            
            return max(fantasy_ppg, 5.0)  # Floor at 5.0 to avoid negative/zero
            
        except Exception as e:
            logger.warning(f"Error getting PPG for {player_name}: {e}, using default")
            return 25.0
