"""
Roster context builder service for creating LLM context for roster chat.
"""

import logging
from typing import Optional, Dict, List, TYPE_CHECKING
from datetime import datetime, timedelta
import re

from backend.config import settings

if TYPE_CHECKING:
    from backend.services.nba_mcp_service import NBAMCPService
    from backend.services.roster_ranking_service import RosterRankingService
from backend.services.player_cache_service import PlayerCacheService
from backend.services.league_data_cache_service import LeagueDataCacheService
from backend.services.nba_cache_service import NBACacheService
from backend.services.nba_stats_service import NBAStatsService
from backend.session.repository import BasketballRepository

logger = logging.getLogger(__name__)


class RosterContextBuilder:
    """Service for building comprehensive roster context for LLM."""
    
    def __init__(
        self,
        player_cache_service: PlayerCacheService,
        league_data_cache_service: LeagueDataCacheService,
        nba_cache_service: NBACacheService,
        nba_stats_service: Optional[NBAStatsService],
        basketball_repository: BasketballRepository,
        nba_mcp_service: Optional['NBAMCPService'] = None,
        roster_ranking_service: Optional['RosterRankingService'] = None
    ):
        """
        Initialize with service dependencies.
        
        Args:
            nba_stats_service: Optional NBAStatsService. If None, historical stats will be disabled.
            nba_mcp_service: Optional NBAMCPService for NBA data via MCP server.
            roster_ranking_service: Optional RosterRankingService for league rankings.
        """
        self.player_cache = player_cache_service
        self.league_cache = league_data_cache_service
        self.nba_cache = nba_cache_service
        self.nba_stats = nba_stats_service  # Can be None for graceful degradation
        self.repository = basketball_repository
        self.nba_mcp = nba_mcp_service  # Can be None, will use database fallback
        self.roster_ranking = roster_ranking_service  # Can be None for graceful degradation
        
        # Load configuration
        self.max_context_tokens = settings.ROSTER_CHAT_MAX_CONTEXT_TOKENS
        self.enable_historical_stats = settings.ROSTER_CHAT_ENABLE_HISTORICAL_STATS and (nba_stats_service is not None)
    
    async def build_roster_context(
        self,
        league_id: str,
        roster_id: int,
        sleeper_user_id: str,
        include_historical: bool = False,
        historical_query: Optional[str] = None
    ) -> str:
        """
        Build comprehensive roster context for LLM.
        
        Args:
            league_id: Sleeper league ID
            roster_id: Sleeper roster ID
            sleeper_user_id: Sleeper user ID
            include_historical: Whether to fetch historical stats
            historical_query: Query string for historical stats parsing
            
        Returns:
            Formatted context string
        """
        try:
            logger.info(f"Building roster context for league {league_id}, roster {roster_id}")
            
            context_parts = []
            
            # 1. League rules and scoring
            league_rules = await self._get_league_rules_context(league_id)
            if league_rules:
                context_parts.append(league_rules)
            
            # 2. Roster summary
            roster_summary = await self._get_roster_summary(league_id, roster_id, sleeper_user_id)
            if roster_summary:
                context_parts.append(roster_summary)
            
            # 2b. League rankings
            ranking_context = await self._get_roster_ranking_context(league_id, roster_id)
            if ranking_context:
                context_parts.append(ranking_context)
            
            # 3. Current matchup information
            current_matchup = await self._get_current_matchup_context(league_id, roster_id)
            if current_matchup:
                context_parts.append(current_matchup)
            
            # 3b. Upcoming fantasy matchups
            upcoming_matchups = await self._get_upcoming_matchups_context(league_id, roster_id, weeks_ahead=3)
            if upcoming_matchups:
                context_parts.append(upcoming_matchups)
            
            # 4. Historical stats if requested
            if include_historical and historical_query and self.enable_historical_stats:
                historical_stats = await self._fetch_historical_stats_if_needed(historical_query)
                if historical_stats:
                    context_parts.append(historical_stats)
            
            # 4. Upcoming schedule (limit to manage tokens)
            roster_players = await self._get_roster_player_ids(league_id, roster_id)
            if roster_players:
                schedule_context = await self._get_schedule_context(roster_players, days_ahead=7)
                if schedule_context:
                    context_parts.append(schedule_context)
            
            # 5. Injury report
            if roster_players:
                injury_context = await self._get_injury_context(roster_players)
                if injury_context:
                    context_parts.append(injury_context)
            
            # 6. Recent performance (limit to 2 weeks)
            performance_context = await self._get_recent_performance_context(league_id, roster_id, weeks=2)
            if performance_context:
                context_parts.append(performance_context)
            
            # Combine all parts
            full_context = "\n\n".join(context_parts)
            
            # Log token estimate
            estimated_tokens = len(full_context.split()) * 1.3  # Rough estimate
            logger.info(f"Built roster context (~{int(estimated_tokens)} tokens)")
            
            # DEBUG: Log the actual context being sent to LLM
            logger.info(f"DEBUG - Roster context preview:\n{full_context[:500]}...")
            
            return full_context
            
        except Exception as e:
            logger.error(f"Error building roster context: {e}")
            return "## Error\nUnable to load complete roster context. Proceeding with limited information."
    
    async def _get_league_rules_context(self, league_id: str) -> str:
        """Get league rules and scoring context."""
        try:
            league_details = self.league_cache.get_cached_league_details(league_id)
            
            if not league_details:
                return "## League Rules\nLeague details unavailable."
            
            context_parts = ["## League Rules & Scoring"]
            
            # League name and basic info
            league_name = league_details.get("name", "Unknown League")
            total_rosters = league_details.get("total_rosters", "Unknown")
            context_parts.append(f"**League:** {league_name} ({total_rosters} teams)")
            
            # Detect lock-in mode
            settings_data = league_details.get("settings", {})
            metadata = league_details.get("metadata", {})
            
            # Check for lock-in indicators
            is_lockin = metadata.get("lock_in_mode") or settings_data.get("lock_in_mode") or False
            
            if is_lockin:
                context_parts.append("**League Type:** Lock-In Mode")
                context_parts.append("**Lock-In Rules:** Lineups lock at game start. You must lock each player's game before their next game starts. One game per week per player counts.")
            else:
                context_parts.append("**League Type:** Standard Sleeper League")
            
            # Scoring settings
            scoring_settings = league_details.get("scoring_settings", {})
            if scoring_settings:
                context_parts.append("\n**Scoring Categories:**")
                
                # Common scoring categories with readable names
                category_names = {
                    "pts": "Points",
                    "reb": "Rebounds",
                    "ast": "Assists",
                    "stl": "Steals",
                    "blk": "Blocks",
                    "to": "Turnovers",
                    "fgm": "Field Goals Made",
                    "fga": "Field Goals Attempted",
                    "ftm": "Free Throws Made",
                    "fta": "Free Throws Attempted",
                    "fg3m": "3-Pointers Made",
                    "fg3a": "3-Pointers Attempted"
                }
                
                for key, value in scoring_settings.items():
                    readable_name = category_names.get(key, key.upper())
                    context_parts.append(f"- {readable_name}: {value}")
            
            # Roster positions
            roster_positions = league_details.get("roster_positions", [])
            if roster_positions:
                # Count position slots
                position_counts = {}
                for pos in roster_positions:
                    position_counts[pos] = position_counts.get(pos, 0) + 1
                
                context_parts.append("\n**Roster Positions:**")
                formatted_positions = []
                for pos, count in position_counts.items():
                    if count > 1:
                        formatted_positions.append(f"{count}×{pos}")
                    else:
                        formatted_positions.append(pos)
                context_parts.append(", ".join(formatted_positions))
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building league rules context: {e}")
            return "## League Rules\nUnable to load league rules."
    
    async def _get_roster_summary(self, league_id: str, roster_id: int, sleeper_user_id: str) -> str:
        """Get roster summary with players and stats."""
        try:
            # Get rosters
            rosters = self.league_cache.get_cached_rosters(league_id)
            if not rosters:
                return "## Your Roster\nRoster data unavailable."
            
            # Find user's roster
            user_roster = None
            for roster in rosters:
                if roster.get("roster_id") == roster_id or roster.get("owner_id") == sleeper_user_id:
                    user_roster = roster
                    break
            
            if not user_roster:
                return "## Your Roster\nRoster not found."
            
            # Get user's display name
            user_display_name = None
            league_details = self.league_cache.get_cached_league_details(league_id)
            
            if not league_details or not league_details.get("users"):
                # Try to fetch league users from API
                logger.info(f"League users not in cache, fetching from API for league {league_id}")
                try:
                    from backend.services.sleeper_service import SleeperService
                    async with SleeperService() as sleeper:
                        league_users = await sleeper.get_league_users(league_id)
                        if league_users:
                            if league_details:
                                league_details["users"] = league_users
                            else:
                                league_details = {"users": league_users}
                except Exception as e:
                    logger.error(f"Failed to fetch league users: {e}")
            
            if league_details:
                users = league_details.get("users", [])
                for user in users:
                    if user.get("user_id") == sleeper_user_id:
                        user_display_name = user.get("display_name", user.get("username"))
                        break
            
            # Build header with username
            if user_display_name:
                context_parts = [f"## Your Roster ({user_display_name})"]
            else:
                context_parts = ["## Your Roster"]
            
            # Get player IDs
            player_ids = user_roster.get("players", [])
            starters = user_roster.get("starters", [])
            
            # Get player details from cache
            player_data = self.player_cache.get_players_bulk(player_ids) if player_ids else {}
            
            # DEBUG: Log player data lookup
            logger.info(f"DEBUG - Looking up {len(player_ids)} players")
            logger.info(f"DEBUG - Player data returned: {len(player_data)} players")
            if player_ids and not player_data:
                logger.warning(f"DEBUG - No player data found for IDs: {player_ids[:5]}...")
            elif player_ids:
                sample_id = player_ids[0]
                sample_data = player_data.get(sample_id, {})
                logger.info(f"DEBUG - Sample player {sample_id}: {sample_data}")
            
            # Separate starters and bench
            starter_details = []
            bench_details = []
            
            for player_id in player_ids:
                player_info = player_data.get(player_id, {})
                player_name = player_info.get("name", player_info.get("full_name", "Unknown Player"))
                positions = player_info.get("positions", [])
                position = "/".join(positions) if positions else ""
                team = player_info.get("team", "")
                injury_status = player_info.get("injury_status", "")
                
                player_string = f"{player_name}"
                if position:
                    player_string += f" ({position})"
                if team:
                    player_string += f" - {team}"
                
                # Add injury status
                if injury_status and injury_status not in ["Healthy", "ACT"]:
                    player_string += f" - {injury_status}"
                else:
                    player_string += " - Healthy"
                
                if player_id in starters:
                    starter_details.append(player_string)
                else:
                    bench_details.append(player_string)
            
            # Format starters
            if starter_details:
                context_parts.append("\n**Starting Lineup:**")
                for player in starter_details:
                    context_parts.append(f"- {player}")
            
            # Format bench
            if bench_details:
                context_parts.append("\n**Bench:**")
                for player in bench_details:
                    context_parts.append(f"- {player}")
            
            # Add roster stats
            wins = user_roster.get("settings", {}).get("wins", 0)
            losses = user_roster.get("settings", {}).get("losses", 0)
            total_points = user_roster.get("settings", {}).get("fpts", 0)
            
            context_parts.append(f"\n**Record:** {wins}-{losses}")
            if total_points:
                context_parts.append(f"**Total Points This Season:** {total_points}")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building roster summary: {e}")
            return "## Your Roster\nUnable to load roster details."
    
    async def _get_current_matchup_context(self, league_id: str, roster_id: int) -> str:
        """Get current week matchup information."""
        try:
            context_parts = ["## This Week's Matchup"]
            
            # Get current week
            current_week = await self.league_cache._get_current_round()
            
            # Get matchups for current week
            matchups = self.league_cache.get_cached_matchups(league_id, current_week)
            if not matchups:
                # Cache miss - fetch from API
                logger.info(f"Matchup cache miss, fetching from Sleeper API for week {current_week}")
                success, error = await self.league_cache.cache_matchups(league_id, [current_week])
                if success:
                    matchups = self.league_cache.get_cached_matchups(league_id, current_week)
                if not matchups:
                    logger.warning(f"No matchup data available for league {league_id}, week {current_week}")
                    return ""  # No matchup data available yet (season hasn't started or data not available)
            
            # Extract the list of matchups
            week_matchups = matchups.get(current_week, []) if isinstance(matchups, dict) else matchups
            
            # Find user's matchup
            user_matchup = None
            opponent_matchup = None
            for matchup in week_matchups:
                if matchup.get("roster_id") == roster_id:
                    user_matchup = matchup
                    matchup_id = matchup.get("matchup_id")
                    # Find opponent with same matchup_id
                    for other_matchup in week_matchups:
                        if other_matchup.get("matchup_id") == matchup_id and other_matchup.get("roster_id") != roster_id:
                            opponent_matchup = other_matchup
                            break
                    break
            
            if not user_matchup or not opponent_matchup:
                return ""  # No matchup this week (bye week or data not available)
            
            # Get opponent roster details
            opponent_roster_id = opponent_matchup.get("roster_id")
            rosters = self.league_cache.get_cached_rosters(league_id)
            opponent_roster = None
            opponent_owner_id = None
            
            if rosters:
                for roster in rosters:
                    if roster.get("roster_id") == opponent_roster_id:
                        opponent_roster = roster
                        opponent_owner_id = roster.get("owner_id")
                        break
            
            # Get league details to find team name
            league_details = self.league_cache.get_cached_league_details(league_id)
            opponent_name = "Unknown Team"
            
            if not league_details:
                # Cache miss - try to fetch league details
                logger.info(f"League details cache miss, fetching from API for league {league_id}")
                try:
                    from backend.services.sleeper_service import SleeperService
                    async with SleeperService() as sleeper:
                        league_info = await sleeper.get_league(league_id)
                        league_users = await sleeper.get_league_users(league_id)
                        if league_info and league_users:
                            league_details = {**league_info, "users": league_users}
                except Exception as e:
                    logger.error(f"Failed to fetch league details: {e}")
            
            if league_details and opponent_owner_id:
                users = league_details.get("users", [])
                logger.info(f"Looking for opponent with owner_id {opponent_owner_id} in {len(users)} users")
                for user in users:
                    if user.get("user_id") == opponent_owner_id:
                        opponent_name = user.get("display_name", user.get("username", "Unknown Team"))
                        logger.info(f"Found opponent name: {opponent_name}")
                        break
                if opponent_name == "Unknown Team":
                    logger.warning(f"Could not find user with owner_id {opponent_owner_id} in league users")
            
            # Add matchup info
            user_points = user_matchup.get("points", 0)
            opponent_points = opponent_matchup.get("points", 0)
            
            context_parts.append(f"**Week {current_week}** - vs **{opponent_name}**")
            context_parts.append(f"**Current Score:** {user_points:.1f} - {opponent_points:.1f}")
            
            # Get opponent's key players
            if opponent_roster:
                opponent_players = opponent_roster.get("starters", []) or opponent_roster.get("players", [])[:9]  # Get starters or first 9 players
                if opponent_players:
                    player_data = self.player_cache.get_players_bulk(opponent_players[:5])  # Get top 5 opponent players
                    if player_data:
                        context_parts.append("\n**Opponent's Key Players:**")
                        for player_id in opponent_players[:5]:
                            player_info = player_data.get(player_id, {})
                            player_name = player_info.get("name", player_info.get("full_name", "Unknown"))
                            positions = player_info.get("positions", [])
                            position = "/".join(positions) if positions else ""
                            team = player_info.get("team", "")
                            if player_name != "Unknown":
                                player_str = f"- {player_name}"
                                if position:
                                    player_str += f" ({position})"
                                if team:
                                    player_str += f" - {team}"
                                context_parts.append(player_str)
            
            context_parts.append("\n*Use `get_opponent_roster` tool for full opponent roster details*")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building matchup context: {e}")
            return ""  # Return empty string on error to not break context
    
    async def _get_upcoming_matchups_context(self, league_id: str, roster_id: int, weeks_ahead: int = 3) -> str:
        """Get upcoming fantasy matchups for the next few weeks."""
        try:
            context_parts = [f"## Upcoming Fantasy Matchups (Next {weeks_ahead} Weeks)"]
            
            # Get current week
            current_week = await self.league_cache._get_current_round()
            
            # Get league details for usernames
            league_details = self.league_cache.get_cached_league_details(league_id)
            if not league_details or not league_details.get("users"):
                # Try to fetch from API
                try:
                    from backend.services.sleeper_service import SleeperService
                    async with SleeperService() as sleeper:
                        league_info = await sleeper.get_league(league_id)
                        league_users = await sleeper.get_league_users(league_id)
                        if league_info and league_users:
                            league_details = {**league_info, "users": league_users}
                except Exception as e:
                    logger.error(f"Failed to fetch league details: {e}")
                    return ""
            
            if not league_details:
                return ""
            
            users = league_details.get("users", [])
            rosters = self.league_cache.get_cached_rosters(league_id)
            
            # Helper function to get username from roster_id
            def get_username(rid):
                if not rosters:
                    return "Unknown"
                for roster in rosters:
                    if roster.get("roster_id") == rid:
                        owner_id = roster.get("owner_id")
                        for user in users:
                            if user.get("user_id") == owner_id:
                                return user.get("display_name", user.get("username", "Unknown"))
                return "Unknown"
            
            # Fetch matchups for upcoming weeks
            upcoming_matchups = []
            for week_offset in range(weeks_ahead):
                week = current_week + week_offset
                matchups = self.league_cache.get_cached_matchups(league_id, week)
                
                if not matchups:
                    # Try to fetch from API
                    success, error = await self.league_cache.cache_matchups(league_id, [week])
                    if success:
                        matchups = self.league_cache.get_cached_matchups(league_id, week)
                
                if matchups:
                    week_matchups = matchups.get(week, []) if isinstance(matchups, dict) else matchups
                    
                    # Find user's matchup
                    for matchup in week_matchups:
                        if matchup.get("roster_id") == roster_id:
                            matchup_id = matchup.get("matchup_id")
                            
                            # Find opponent
                            opponent_name = "BYE WEEK"
                            for other_matchup in week_matchups:
                                if (other_matchup.get("matchup_id") == matchup_id and 
                                    other_matchup.get("roster_id") != roster_id):
                                    opponent_roster_id = other_matchup.get("roster_id")
                                    opponent_name = get_username(opponent_roster_id)
                                    break
                            
                            if week == current_week:
                                upcoming_matchups.append(f"- **Week {week} (Current):** vs {opponent_name}")
                            else:
                                upcoming_matchups.append(f"- **Week {week}:** vs {opponent_name}")
                            break
            
            if upcoming_matchups:
                context_parts.extend(upcoming_matchups)
            else:
                context_parts.append("No upcoming matchup data available.")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building upcoming matchups context: {e}")
            return ""
    
    async def _get_roster_player_ids(self, league_id: str, roster_id: int) -> List[str]:
        """Get list of player IDs on roster."""
        try:
            rosters = self.league_cache.get_cached_rosters(league_id)
            if not rosters:
                return []
            
            for roster in rosters:
                if roster.get("roster_id") == roster_id:
                    return roster.get("players", [])
            
            return []
            
        except Exception as e:
            logger.error(f"Error getting roster player IDs: {e}")
            return []
    
    async def _get_schedule_context(self, roster_players: List[str], days_ahead: int = 7) -> str:
        """Get upcoming schedule context with game counts and analysis."""
        try:
            context_parts = [f"## Upcoming Schedule (Next {days_ahead} Days)"]
            
            # Get player details to extract NBA teams
            player_data = self.player_cache.get_players_bulk(roster_players)
            
            # Map players to their NBA teams
            player_teams = {}
            for player_id, player_info in player_data.items():
                team = player_info.get("team", "")
                player_name = player_info.get("name", player_info.get("full_name", "Unknown"))
                if team:
                    player_teams[player_name] = team
            
            logger.info(f"Schedule context: Mapped {len(player_teams)} players to NBA teams: {list(player_teams.values())}")
            
            # Get date range
            today = datetime.now().date()
            end_date = today + timedelta(days=days_ahead)
            
            # Get games from MCP service if available, otherwise use database
            if self.nba_mcp and settings.nba_mcp_enabled:
                logger.info("Using NBA MCP Service for schedule data")
                try:
                    games = await self.nba_mcp.get_schedule_for_date_range(
                        today,
                        end_date,
                        team_tricodes=list(set(player_teams.values()))
                    )
                    logger.info(f"Schedule context: Retrieved {len(games)} games from MCP service ({today} to {end_date})")
                except Exception as mcp_error:
                    logger.warning(f"MCP schedule retrieval failed, falling back to database: {mcp_error}")
                    games = self.repository.get_games_by_date_range(str(today), str(end_date))
                    logger.info(f"Schedule context: Retrieved {len(games)} games from database ({today} to {end_date})")
            else:
                # Use database fallback
                games = self.repository.get_games_by_date_range(
                    str(today),
                    str(end_date)
                )
                logger.info(f"Schedule context: Retrieved {len(games)} games from database ({today} to {end_date})")
            
            if not games:
                logger.warning(f"No games found in database for date range {today} to {end_date}")
                context_parts.append("Schedule data unavailable.")
                return "\n".join(context_parts)
            
            # Group games by player with dates
            player_schedules = {}
            team_game_counts = {}
            
            for player_name, team in player_teams.items():
                player_games = []
                game_dates = []
                
                for game in games:
                    if game.get("home_team_tricode") == team or game.get("away_team_tricode") == team:
                        game_date = game.get("game_date", "")
                        home_team = game.get("home_team_tricode", "")
                        away_team = game.get("away_team_tricode", "")
                        
                        # Determine opponent and home/away
                        if home_team == team:
                            matchup = f"vs {away_team}"
                        else:
                            matchup = f"@ {home_team}"
                        
                        player_games.append({"date": game_date, "matchup": matchup})
                        game_dates.append(game_date)
                
                if player_games:
                    player_schedules[player_name] = player_games
                    team_game_counts[team] = len(player_games)
            
            # Add summary
            if player_schedules:
                # Count games per player
                game_count_summary = {}
                for player, games in player_schedules.items():
                    count = len(games)
                    if count not in game_count_summary:
                        game_count_summary[count] = []
                    game_count_summary[count].append(player)
                
                context_parts.append("\n**Game Count Summary:**")
                for count in sorted(game_count_summary.keys(), reverse=True):
                    players = game_count_summary[count]
                    context_parts.append(f"- {count} games: {', '.join(players)}")
                
                context_parts.append("\n**Player Schedule Details:**")
                # Sort by game count (most games first)
                sorted_players = sorted(player_schedules.items(), key=lambda x: len(x[1]), reverse=True)
                
                for player_name, games in sorted_players:
                    team = player_teams[player_name]
                    game_list = [f"{g['matchup']} ({g['date']})" for g in games]
                    
                    # Check for back-to-back
                    if len(games) >= 2:
                        dates = [g['date'] for g in games]
                        has_b2b = any(
                            abs((datetime.strptime(dates[i], "%Y-%m-%d") - 
                                datetime.strptime(dates[i+1], "%Y-%m-%d")).days) <= 1
                            for i in range(len(dates)-1)
                        )
                        b2b_indicator = " 🔥 B2B" if has_b2b else ""
                    else:
                        b2b_indicator = ""
                    
                    context_parts.append(f"- **{player_name} ({team})** [{len(games)} games{b2b_indicator}]: {', '.join(game_list)}")
            else:
                context_parts.append("No upcoming games found for roster players.")
            
            result = "\n".join(context_parts)
            logger.info(f"Schedule context result length: {len(result)} chars, {len(context_parts)} lines")
            logger.info(f"Schedule context preview: {result[:300]}...")
            return result
            
        except Exception as e:
            logger.error(f"Error building schedule context: {e}")
            return f"## Upcoming Schedule\nUnable to load schedule data."
    
    async def _get_injury_context(self, roster_players: List[str]) -> str:
        """Get injury report context."""
        try:
            context_parts = ["## Injury Report"]
            
            # Get player details
            player_data = self.player_cache.get_players_bulk(roster_players)
            
            injured_players = []
            for player_id, player_info in player_data.items():
                injury_status = player_info.get("injury_status", "")
                if injury_status and injury_status.lower() not in ["healthy", ""]:
                    player_name = player_info.get("full_name", "Unknown")
                    injury_notes = player_info.get("injury_notes", "")
                    
                    injury_str = f"- **{player_name}:** {injury_status}"
                    if injury_notes:
                        injury_str += f" - {injury_notes}"
                    
                    injured_players.append(injury_str)
            
            if injured_players:
                context_parts.extend(injured_players)
            else:
                context_parts.append("No injuries reported.")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building injury context: {e}")
            return "## Injury Report\nUnable to load injury data."
    
    async def _get_recent_performance_context(self, league_id: str, roster_id: int, weeks: int = 2) -> str:
        """Get recent performance context."""
        try:
            context_parts = [f"## Recent Performance (Last {weeks} Weeks)"]
            
            # Get current week
            current_week = await self.league_cache._get_current_round()
            
            # Get matchups for recent weeks
            recent_weeks = list(range(max(1, current_week - weeks + 1), current_week + 1))
            
            week_performances = []
            for week in recent_weeks:
                matchups = self.league_cache.get_cached_matchups(league_id, week)
                if not matchups:
                    continue
                
                # Extract the list of matchups from the response
                week_matchups = matchups.get(week, []) if isinstance(matchups, dict) else matchups
                
                # Find user's matchup
                for matchup in week_matchups:
                    if matchup.get("roster_id") == roster_id:
                        points = matchup.get("points", 0)
                        
                        # Find opponent's points
                        matchup_id = matchup.get("matchup_id")
                        opponent_points = 0
                        for other_matchup in week_matchups:
                            if other_matchup.get("matchup_id") == matchup_id and other_matchup.get("roster_id") != roster_id:
                                opponent_points = other_matchup.get("points", 0)
                                break
                        
                        # Determine result
                        if points > opponent_points:
                            result = "W"
                        elif points < opponent_points:
                            result = "L"
                        else:
                            result = "T"
                        
                        week_performances.append(f"- Week {week}: {points:.1f} pts ({result})")
                        break
            
            if week_performances:
                context_parts.extend(week_performances)
                
                # Calculate average
                if len(week_performances) > 0:
                    total_points = sum(float(perf.split(":")[1].split("pts")[0].strip()) for perf in week_performances)
                    avg_points = total_points / len(week_performances)
                    context_parts.append(f"\n**Average:** {avg_points:.1f} pts/week")
            else:
                context_parts.append("No recent performance data available.")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building performance context: {e}")
            return f"## Recent Performance\nUnable to load performance data."
    
    async def _get_roster_ranking_context(self, league_id: str, roster_id: int) -> str:
        """Get league roster ranking context."""
        try:
            if not self.roster_ranking:
                return ""
            
            # Get rankings
            rankings_data = await self.roster_ranking.get_roster_rankings(league_id)
            
            if not rankings_data or not rankings_data.rankings:
                return ""
            
            context_parts = ["## League Power Rankings"]
            
            # Find user's rank
            user_rank = None
            user_ranking = None
            for ranking in rankings_data.rankings:
                if ranking.roster_id == roster_id:
                    user_rank = ranking.rank
                    user_ranking = ranking
                    break
            
            if user_ranking:
                # User's position
                total_teams = rankings_data.total_rosters
                percentile = (user_rank / total_teams) * 100
                
                if percentile <= 25:
                    tier = "🥇 Top Tier"
                elif percentile <= 50:
                    tier = "🥈 Upper Mid Tier"
                elif percentile <= 75:
                    tier = "🥉 Lower Mid Tier"
                else:
                    tier = "⚠️ Bottom Tier"
                
                context_parts.append(f"**Your Team:** Ranked #{user_rank} of {total_teams} ({tier})")
                context_parts.append(f"**Total Points:** {user_ranking.total_fantasy_points:.2f}")
                
                # Category strengths/weaknesses
                if user_ranking.category_percentiles:
                    strengths = []
                    weaknesses = []
                    for cat, percentile in user_ranking.category_percentiles.items():
                        if percentile >= 75:
                            strengths.append(f"{cat.upper()} ({percentile:.0f}th percentile)")
                        elif percentile <= 25:
                            weaknesses.append(f"{cat.upper()} ({percentile:.0f}th percentile)")
                    
                    if strengths:
                        context_parts.append(f"**Strengths:** {', '.join(strengths)}")
                    if weaknesses:
                        context_parts.append(f"**Weaknesses:** {', '.join(weaknesses)}")
                
                # Show top 3 teams
                context_parts.append("\n**Top 3 Teams:**")
                for i, ranking in enumerate(rankings_data.rankings[:3], 1):
                    emoji = "🥇" if i == 1 else "🥈" if i == 2 else "🥉"
                    context_parts.append(f"{emoji} #{i} {ranking.owner_name}: {ranking.total_fantasy_points:.2f} pts")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error building ranking context: {e}")
            return ""
    
    async def _fetch_historical_stats_if_needed(self, query: str) -> Optional[str]:
        """Fetch historical stats if query contains historical keywords."""
        try:
            # Check if NBA stats service is available
            if not self.nba_stats:
                logger.warning("Historical stats requested but NBAStatsService unavailable")
                return None
            
            # Detect historical query
            historical_keywords = [
                "2022", "2023", "2021", "2020", "2019",
                "last year", "last season", "career",
                "average in", "stats in", "around this time",
                "historically", "previous season"
            ]
            
            query_lower = query.lower()
            is_historical = any(keyword in query_lower for keyword in historical_keywords)
            
            if not is_historical:
                return None
            
            logger.info(f"Detected historical query: {query}")
            
            # Extract player name (simple approach - look for capitalized words)
            player_name = self._extract_player_name(query)
            if not player_name:
                logger.warning("Could not extract player name from historical query")
                player_name = query.strip()
                
            # Use MCP service if available, otherwise fall back to nba_stats
            if self.nba_mcp and settings.nba_mcp_enabled:
                logger.info(f"Using NBA MCP Service for player stats lookup: {player_name}")
                player_info = await self.nba_mcp.get_player_info(player_name)
                if not player_info:
                    logger.warning(f"Player not found via MCP: {player_name}")
                    return None
                player_id = player_info.get('player_id')
                if not player_id:
                    logger.warning(f"No player ID found via MCP for: {player_name}")
                    return None
                logger.info(f"Found player via MCP: {player_name} (ID: {player_id})")
            else:
                # Fallback: try searching with the raw query directly
                player_id = await self.nba_stats.search_player_by_name(query)
                if not player_id:
                    logger.warning(f"Player not found with raw query: {query}")
                    return None
                logger.info(f"Found player using nba_stats: {player_name}")
            
            # Handle "around this time" queries with date-range logic
            if "around this time" in query_lower:
                from datetime import datetime, timedelta
                
                # Extract year from query
                season = self._extract_season(query)
                if season:
                    # Parse season to get the year (e.g., "2021-22" -> 2022)
                    year = int(season.split("-")[1])
                    if year < 100:  # Handle 2-digit year
                        year = 2000 + year
                    
                    # Get current date but in the specified year
                    today = datetime.now()
                    target_date = datetime(year, today.month, today.day)
                    
                    # Compute date range (±14 days around this time)
                    start_date = (target_date - timedelta(days=14)).strftime("%Y-%m-%d")
                    end_date = (target_date + timedelta(days=14)).strftime("%Y-%m-%d")
                    
                    logger.info(f"Using date range {start_date} to {end_date} for 'around this time' query")
                    
                    # Fetch date range stats
                    date_range_stats = await self.nba_stats.fetch_player_stats_by_date_range(
                        player_id, start_date, end_date
                    )
                    
                    if date_range_stats:
                        return self._format_historical_stats(player_name, date_range_stats, "date_range", season)
                    else:
                        logger.info("No games found in date range, falling back to season averages")
                        # Fallback to season averages
                        season_stats = await self.nba_stats.fetch_player_season_averages(player_id, season)
                        if season_stats:
                            return self._format_historical_stats(player_name, season_stats, "season", season)
            
            # Determine what type of stats to fetch
            if "career" in query_lower or "season" in query_lower or "average" in query_lower or "avg" in query_lower:
                # Fetch career/season stats via MCP if available
                if self.nba_mcp and settings.nba_mcp_enabled:
                    logger.info(f"Fetching player stats via MCP for player_id: {player_id}")
                    stats = await self.nba_mcp.get_player_stats(player_name, season=None)
                    if stats:
                        logger.info(f"Retrieved stats via MCP for {player_name}")
                        return self._format_mcp_stats(player_name, stats, query_lower)
                    else:
                        logger.warning(f"No stats found via MCP for {player_name}")
                else:
                    # Fallback to old service
                    career_stats = await self.nba_stats.fetch_player_career_stats(player_id)
                    if career_stats:
                        return self._format_historical_stats(player_name, career_stats, "career")
            
            # Extract year/season
            season = self._extract_season(query)
            if season:
                if self.nba_mcp and settings.nba_mcp_enabled:
                    stats = await self.nba_mcp.get_player_stats(player_name, season=season)
                    if stats:
                        return self._format_mcp_stats(player_name, stats, query_lower)
                else:
                    # Fetch season averages
                    season_stats = await self.nba_stats.fetch_player_season_averages(player_id, season)
                    if season_stats:
                        return self._format_historical_stats(player_name, season_stats, "season", season)
            
            # Default to recent career stats
            if self.nba_mcp and settings.nba_mcp_enabled:
                stats = await self.nba_mcp.get_player_stats(player_name)
                if stats:
                    return self._format_mcp_stats(player_name, stats, query_lower)
            else:
                career_stats = await self.nba_stats.fetch_player_career_stats(player_id)
                if career_stats:
                    return self._format_historical_stats(player_name, career_stats, "career")
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching historical stats: {e}")
            return None
    
    def _extract_player_name(self, query: str) -> Optional[str]:
        """
        Extract player name from query using simple heuristics.
        
        Handles both capitalized names (e.g., "LeBron James") and lowercase queries
        (e.g., "lebron james") by falling back to longest alphabetic tokens.
        """
        # Look for capitalized words (player names)
        # Common patterns: "LeBron James", "Stephen Curry", etc.
        words = query.split()
        capitalized = []
        
        for word in words:
            # Remove punctuation
            clean_word = word.strip(',.!?":;')
            if clean_word and clean_word[0].isupper() and not clean_word.isupper():
                capitalized.append(clean_word)
        
        # Try to form full name (take first 2 capitalized words)
        if len(capitalized) >= 2:
            return f"{capitalized[0]} {capitalized[1]}"
        elif len(capitalized) == 1:
            return capitalized[0]
        
        # Fallback for lowercase queries: find longest two alphabetic tokens
        # This handles queries like "lebron james stats" or "how is giannis"
        alphabetic_words = []
        for word in words:
            # Remove punctuation and keep only alphabetic words
            clean_word = re.sub(r'[^a-zA-Z]', '', word)
            if clean_word and len(clean_word) > 2:  # Ignore short words like "is", "in"
                alphabetic_words.append(clean_word)
        
        # Sort by length and take the two longest words as likely first/last name
        if len(alphabetic_words) >= 2:
            sorted_words = sorted(alphabetic_words, key=len, reverse=True)
            # Return the two longest words, title-cased
            return f"{sorted_words[0].title()} {sorted_words[1].title()}"
        elif len(alphabetic_words) == 1:
            return alphabetic_words[0].title()
        
        return None
    
    def _extract_season(self, query: str) -> Optional[str]:
        """
        Extract season year from query with enhanced parsing.
        
        Handles multiple formats:
        1. Explicit ranges: "2022-23", "2021-22" → returns as-is
        2. Single years: "2022", "2021" → converts to NBA season format (2021-22)
        3. Ambiguous phrasing: Falls back to year conversion
        """
        # First, look for explicit season ranges like "2022-23" or "2021-22"
        # NBA seasons are formatted as YYYY-YY (e.g., "2022-23" for 2022-2023 season)
        range_match = re.search(r'\b(20\d{2})[-–](20)?\d{2}\b', query)
        if range_match:
            # Extract the matched season range
            season_str = range_match.group(0)
            # Normalize to YYYY-YY format
            parts = re.split(r'[-–]', season_str)
            if len(parts) == 2:
                start_year = parts[0]
                end_year = parts[1]
                # If end year is 2-digit, use it directly; if 4-digit, take last 2
                if len(end_year) == 4:
                    end_year = end_year[-2:]
                return f"{start_year}-{end_year}"
        
        # Fallback: Look for single 4-digit year and convert to NBA season format
        # (NBA season 2022-23 corresponds to year 2022, which started in fall 2022)
        year_match = re.search(r'\b(20\d{2})\b', query)
        if year_match:
            year = int(year_match.group(1))
            # Convert to NBA season format (e.g., 2022 → "2021-22")
            # Note: A query for "2022" typically means the 2021-22 season
            return f"{year-1}-{str(year)[-2:]}"
        
        return None
    
    def _format_historical_stats(
        self,
        player_name: str,
        stats_data: Dict,
        query_type: str,
        season: Optional[str] = None
    ) -> str:
        """Format historical stats as markdown."""
        try:
            context_parts = []
            
            if query_type == "season":
                context_parts.append(f"## Historical Stats: {player_name} ({season} Season)")
                context_parts.append(f"- Points: {stats_data.get('ppg', 0):.1f} PPG")
                context_parts.append(f"- Rebounds: {stats_data.get('rpg', 0):.1f} RPG")
                context_parts.append(f"- Assists: {stats_data.get('apg', 0):.1f} APG")
                context_parts.append(f"- Steals: {stats_data.get('spg', 0):.1f} SPG")
                context_parts.append(f"- Blocks: {stats_data.get('bpg', 0):.1f} BPG")
                context_parts.append(f"- Turnovers: {stats_data.get('tov', 0):.1f} TOV")
                
                fg_pct = stats_data.get('fg_pct', 0) * 100
                fg3_pct = stats_data.get('fg3_pct', 0) * 100
                ft_pct = stats_data.get('ft_pct', 0) * 100
                context_parts.append(f"- FG%: {fg_pct:.1f}%, 3P%: {fg3_pct:.1f}%, FT%: {ft_pct:.1f}%")
            
            elif query_type == "date_range":
                game_count = stats_data.get('game_count', 0)
                averages = stats_data.get('averages', {})
                context_parts.append(f"## Historical Stats: {player_name} (Around This Time in {season})")
                context_parts.append(f"**Games Played:** {game_count}")
                context_parts.append(f"- Points: {averages.get('ppg', 0):.1f} PPG")
                context_parts.append(f"- Rebounds: {averages.get('rpg', 0):.1f} RPG")
                context_parts.append(f"- Assists: {averages.get('apg', 0):.1f} APG")
                context_parts.append(f"- Steals: {averages.get('spg', 0):.1f} SPG")
                context_parts.append(f"- Blocks: {averages.get('bpg', 0):.1f} BPG")
                context_parts.append(f"- Turnovers: {averages.get('tov', 0):.1f} TOV")
                
                fg_pct = averages.get('fg_pct', 0) * 100
                fg3_pct = averages.get('fg3_pct', 0) * 100
                ft_pct = averages.get('ft_pct', 0) * 100
                context_parts.append(f"- FG%: {fg_pct:.1f}%, 3P%: {fg3_pct:.1f}%, FT%: {ft_pct:.1f}%")
            
            elif query_type == "career":
                context_parts.append(f"## Career Stats: {player_name}")
                
                regular_season = stats_data.get("regular_season", [])
                if regular_season:
                    # Show last 3 seasons
                    recent_seasons = regular_season[-3:] if len(regular_season) > 3 else regular_season
                    
                    for season_data in reversed(recent_seasons):
                        season_id = season_data.get("season", "")
                        ppg = season_data.get("ppg", 0)
                        rpg = season_data.get("rpg", 0)
                        apg = season_data.get("apg", 0)
                        context_parts.append(f"- **{season_id}:** {ppg:.1f} PPG, {rpg:.1f} RPG, {apg:.1f} APG")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error formatting historical stats: {e}")
            return f"## Historical Stats: {player_name}\nUnable to format stats."
    
    def _format_mcp_stats(self, player_name: str, stats_data: Dict, query_lower: str) -> str:
        """Format stats retrieved from MCP service."""
        try:
            context_parts = []
            
            # Extract season totals from MCP response
            # MCP returns playercareerstats format with resultSets
            result_sets = stats_data.get('resultSets', [])
            if not result_sets:
                return f"## Stats: {player_name}\nNo stats data available."
            
            # Find SeasonTotalsRegularSeason
            season_data = None
            for result_set in result_sets:
                if result_set.get('name') == 'SeasonTotalsRegularSeason':
                    season_data = result_set
                    break
            
            if not season_data or not season_data.get('rowSet'):
                return f"## Stats: {player_name}\nNo season data available."
            
            headers = season_data.get('headers', [])
            rows = season_data.get('rowSet', [])
            
            # Get the most recent season (last row)
            if rows:
                latest_season = rows[-1]
                
                # Create a dict mapping headers to values
                stats_dict = dict(zip(headers, latest_season))
                
                # Format the stats nicely
                season_id = stats_dict.get('SEASON_ID', 'Unknown')
                context_parts.append(f"## Season Stats: {player_name} ({season_id})")
                context_parts.append("")
                
                gp = stats_dict.get('GP', 0)
                pts = stats_dict.get('PTS', 0)
                reb = stats_dict.get('REB', 0)
                ast = stats_dict.get('AST', 0)
                stl = stats_dict.get('STL', 0)
                blk = stats_dict.get('BLK', 0)
                tov = stats_dict.get('TOV', 0)
                fgm = stats_dict.get('FGM', 0)
                fga = stats_dict.get('FGA', 0)
                fg3m = stats_dict.get('FG3M', 0)
                fg3a = stats_dict.get('FG3A', 0)
                ftm = stats_dict.get('FTM', 0)
                fta = stats_dict.get('FTA', 0)
                
                # Calculate averages
                if gp > 0:
                    ppg = pts / gp
                    rpg = reb / gp
                    apg = ast / gp
                    spg = stl / gp
                    bpg = blk / gp
                    tovpg = tov / gp
                    
                    context_parts.append(f"**Games Played:** {gp}")
                    context_parts.append("")
                    context_parts.append(f"**Averages:**")
                    context_parts.append(f"- Points: {ppg:.1f} PPG")
                    context_parts.append(f"- Rebounds: {rpg:.1f} RPG")
                    context_parts.append(f"- Assists: {apg:.1f} APG")
                    context_parts.append(f"- Steals: {spg:.1f} SPG")
                    context_parts.append(f"- Blocks: {bpg:.1f} BPG")
                    context_parts.append(f"- Turnovers: {tovpg:.1f} TOV")
                    context_parts.append("")
                    
                    # Shooting percentages
                    fg_pct = (fgm / fga * 100) if fga > 0 else 0
                    fg3_pct = (fg3m / fg3a * 100) if fg3a > 0 else 0
                    ft_pct = (ftm / fta * 100) if fta > 0 else 0
                    
                    context_parts.append(f"**Shooting:**")
                    context_parts.append(f"- FG%: {fg_pct:.1f}%")
                    context_parts.append(f"- 3P%: {fg3_pct:.1f}%")
                    context_parts.append(f"- FT%: {ft_pct:.1f}%")
                
                # If asking for career, show multiple seasons
                if "career" in query_lower and len(rows) > 1:
                    context_parts.append("")
                    context_parts.append("**Recent Seasons:**")
                    # Show last 3 seasons
                    recent = rows[-3:] if len(rows) > 3 else rows
                    for row in reversed(recent):
                        season_dict = dict(zip(headers, row))
                        s_id = season_dict.get('SEASON_ID', '')
                        s_gp = season_dict.get('GP', 0)
                        s_pts = season_dict.get('PTS', 0)
                        s_reb = season_dict.get('REB', 0)
                        s_ast = season_dict.get('AST', 0)
                        if s_gp > 0:
                            s_ppg = s_pts / s_gp
                            s_rpg = s_reb / s_gp
                            s_apg = s_ast / s_gp
                            context_parts.append(f"- **{s_id}:** {s_ppg:.1f} PPG, {s_rpg:.1f} RPG, {s_apg:.1f} APG")
            
            return "\n".join(context_parts)
            
        except Exception as e:
            logger.error(f"Error formatting MCP stats: {e}")
            return f"## Stats: {player_name}\nUnable to format stats from MCP."
    
    def _estimate_token_count(self, text: str) -> int:
        """Rough estimation: ~4 characters per token."""
        return len(text) // 4
    
    def _truncate_context_if_needed(self, context_parts: List[str], max_tokens: int) -> str:
        """Truncate context if exceeds token limit."""
        full_context = "\n\n".join(context_parts)
        estimated_tokens = self._estimate_token_count(full_context)
        
        if estimated_tokens <= max_tokens:
            return full_context
        
        logger.warning(f"Context exceeds token limit ({estimated_tokens} > {max_tokens}), truncating...")
        
        # Simple truncation - just cut off excess
        target_chars = max_tokens * 4
        truncated = full_context[:target_chars]
        truncated += "\n\n[Context truncated due to length...]"
        
        return truncated
