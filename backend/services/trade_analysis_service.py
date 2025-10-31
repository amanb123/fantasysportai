"""
Trade Analysis Service

Orchestrates trade evaluation using LLM agents + NBA data.
Builds comprehensive context for AI trade analysis.
Works with or without NBA MCP - uses nba_stats_service as fallback.
"""

import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta
import json
import asyncio

from backend.agents.agent_factory import AgentFactory
from backend.services.sleeper_service import SleeperService
from backend.config import settings


logger = logging.getLogger(__name__)


class TradeAnalysisService:
    """Service for analyzing fantasy basketball trades with AI + data"""
    
    def __init__(
        self,
        agent_factory: AgentFactory,
        sleeper_service: SleeperService,
        nba_news_service=None,
        nba_stats_service=None,  # NBA stats via nba_api
        nba_cache_service=None   # For schedule data
    ):
        self.agent_factory = agent_factory
        self.nba_stats_service = nba_stats_service
        self.nba_cache_service = nba_cache_service
        self.sleeper_service = sleeper_service
        self.nba_news_service = nba_news_service
        
        # Schedule cache for trade analysis session
        self._schedule_cache: Optional[List[Dict]] = None
        self._schedule_cache_date: Optional[datetime] = None
        
        # Log which services are available
        if nba_stats_service:
            logger.info("TradeAnalysisService: Using NBA Stats API")
        else:
            logger.warning("TradeAnalysisService: No NBA data services available - limited functionality")
    
    async def analyze_trade(
        self,
        league_id: str,
        user_roster_id: int,
        opponent_roster_id: int,
        user_players_out: List[str],
        user_players_in: List[str],
    ) -> Dict[str, Any]:
        """
        Analyze a proposed trade using AI + NBA data.
        
        Args:
            league_id: Sleeper league ID
            user_roster_id: User's roster ID
            opponent_roster_id: Opponent's roster ID
            user_players_out: Player IDs user is trading away
            user_players_in: Player IDs user is receiving
            
        Returns:
            Dict with pros, cons, favorability_score, reasoning, recommendation
        """
        try:
            logger.info(f"Starting trade analysis for league {league_id}")
            
            # Build comprehensive context for LLM
            trade_context = await self.build_trade_analysis_context(
                league_id=league_id,
                user_roster_id=user_roster_id,
                opponent_roster_id=opponent_roster_id,
                user_players_out=user_players_out,
                user_players_in=user_players_in
            )
            
            # Create trade analyzer agent with context
            agent = self.agent_factory.create_trade_analyzer_agent(trade_context)
            
            # Generate analysis
            logger.info("Generating AI trade analysis...")
            response = await agent.a_generate_reply(
                messages=[{
                    "role": "user",
                    "content": "Please analyze this trade proposal."
                }]
            )
            
            # Parse JSON response with robust error handling
            # Handle dict response with 'content' key from agent
            if isinstance(response, dict) and 'content' in response:
                analysis_text = response['content']
            elif isinstance(response, str):
                analysis_text = response
            else:
                logger.error(f"Unexpected response format: {type(response)}")
                return {
                    "pros": ["Unable to parse AI response"],
                    "cons": ["AI returned unexpected format"],
                    "favorability_score": 50.0,
                    "reasoning": "Error: AI response format invalid",
                    "recommendation": "Manual review required"
                }
            
            # Check for null/empty content
            if not analysis_text or not analysis_text.strip():
                logger.error("Empty response content from LLM")
                return {
                    "pros": ["Unable to parse AI response"],
                    "cons": ["AI returned empty content"],
                    "favorability_score": 50.0,
                    "reasoning": "Error: AI returned empty response",
                    "recommendation": "Manual review required"
                }
            
            logger.info(f"Raw LLM response ({len(analysis_text)} chars): {analysis_text[:200]}...")
            
            # Extract JSON from response (handle markdown code blocks and various formats)
            cleaned_text = analysis_text.strip()
            
            # Remove markdown code fences if present
            if "```json" in cleaned_text:
                json_start = cleaned_text.find("```json") + 7
                json_end = cleaned_text.find("```", json_start)
                cleaned_text = cleaned_text[json_start:json_end].strip()
            elif "```" in cleaned_text:
                json_start = cleaned_text.find("```") + 3
                json_end = cleaned_text.find("```", json_start)
                cleaned_text = cleaned_text[json_start:json_end].strip()
            
            # Try to find JSON object boundaries
            if not cleaned_text.startswith('{'):
                # Find first { and last }
                start_idx = cleaned_text.find('{')
                end_idx = cleaned_text.rfind('}')
                if start_idx != -1 and end_idx != -1:
                    cleaned_text = cleaned_text[start_idx:end_idx + 1]
            
            # Parse JSON
            try:
                analysis_result = json.loads(cleaned_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON decode error: {e}")
                logger.error(f"Attempted to parse: {cleaned_text[:500]}")
                # Return a structured error response
                return {
                    "pros": ["Unable to parse AI response"],
                    "cons": ["AI returned malformed JSON"],
                    "favorability_score": 50.0,
                    "reasoning": f"Error parsing LLM response: {str(e)}. Raw response: {analysis_text[:200]}",
                    "recommendation": "Manual review required"
                }
            
            # Validate structure
            required_fields = ["pros", "cons", "favorability_score", "reasoning", "recommendation"]
            if not all(field in analysis_result for field in required_fields):
                logger.warning(f"Analysis missing required fields. Got: {list(analysis_result.keys())}")
                # Fill in missing fields with defaults
                for field in required_fields:
                    if field not in analysis_result:
                        if field in ["pros", "cons"]:
                            analysis_result[field] = []
                        elif field == "favorability_score":
                            analysis_result[field] = 50.0
                        else:
                            analysis_result[field] = "Not provided"
            
            logger.info(f"Trade analysis complete - Score: {analysis_result['favorability_score']}")
            return analysis_result
            
        except Exception as e:
            logger.error(f"Error analyzing trade: {e}")
            raise
    
    async def build_trade_analysis_context(
        self,
        league_id: str,
        user_roster_id: int,
        opponent_roster_id: int,
        user_players_out: List[str],
        user_players_in: List[str],
    ) -> str:
        """
        Build comprehensive markdown context for trade analysis.
        
        Includes:
        - League scoring settings
        - Current rosters (before/after trade)
        - Player statistics from NBA MCP
        - Upcoming schedule strength
        - Recent performance trends
        
        Returns:
            Formatted markdown context string
        """
        try:
            logger.info("Building trade context...")
            
            # Fetch league data
            league_info = await self.sleeper_service.get_league_info(league_id)
            if not league_info:
                raise ValueError(f"Could not fetch league info for {league_id}")
            scoring_settings = league_info.get("scoring_settings", {})
            
            # Fetch rosters
            user_roster = await self.sleeper_service.get_roster(league_id, user_roster_id)
            if not user_roster:
                raise ValueError(f"Could not fetch user roster {user_roster_id}")
                
            opponent_roster = await self.sleeper_service.get_roster(league_id, opponent_roster_id)
            if not opponent_roster:
                raise ValueError(f"Could not fetch opponent roster {opponent_roster_id}")
            
            # Fetch all players data
            all_players = await self.sleeper_service.get_all_players()
            if not all_players:
                raise ValueError("Could not fetch player data from Sleeper")
            
            # Validate all_players is a dictionary
            if not isinstance(all_players, dict):
                logger.error(f"all_players is type {type(all_players)}, expected dict. Value: {str(all_players)[:200]}")
                raise ValueError(f"Player data has invalid type: {type(all_players)}")
            
            # Calculate opponent's traded players
            opponent_players_out = user_players_in  # What user receives, opponent gives
            opponent_players_in = user_players_out  # What opponent receives, user gives
            
            # Build context sections
            context_parts = [
                "# TRADE PROPOSAL EVALUATION\n",
                "## League Scoring Settings",
                self._format_league_scoring(scoring_settings),
                "",
                "## Trade Details",
                f"**PRIMARY USER (Roster {user_roster_id}) is:**",
                f"- **Giving:** {len(user_players_out)} player(s)",
                f"- **Receiving:** {len(user_players_in)} player(s)",
                "",
                "## PRIMARY USER - Before Trade",
                await self._format_roster_with_trade(
                    roster=user_roster,
                    all_players=all_players,
                    label="CURRENT ROSTER"
                ),
                "",
                "## PRIMARY USER - After Trade",
                await self._format_roster_with_trade(
                    roster=user_roster,
                    all_players=all_players,
                    players_out=user_players_out,
                    players_in=user_players_in,
                    label="PROJECTED ROSTER (AFTER TRADE)"
                ),
                "",
                "## Players User is TRADING AWAY",
                await self._format_player_stats(user_players_out, all_players),
                "",
                "## Players User is RECEIVING",
                await self._format_player_stats(user_players_in, all_players),
                "",
                "## Opponent's Trade Impact (for reference)",
                f"**OPPONENT (Roster {opponent_roster_id}) is:**",
                f"- **Giving:** {len(opponent_players_out)} player(s)",
                f"- **Receiving:** {len(opponent_players_in)} player(s)",
            ]
            
            context = "\n".join(context_parts)
            logger.info(f"Built trade context ({len(context)} chars)")
            return context
            
        except Exception as e:
            logger.error(f"Error building trade context: {e}")
            raise
    
    def _format_league_scoring(self, scoring_settings: Dict[str, float]) -> str:
        """Format league scoring settings as markdown table"""
        if not scoring_settings:
            return "*No custom scoring settings*"
        
        lines = ["| Stat | Points |", "|------|--------|"]
        
        # Map Sleeper stat keys to readable names
        stat_names = {
            "pts": "Points",
            "reb": "Rebounds",
            "ast": "Assists",
            "blk": "Blocks",
            "stl": "Steals",
            "fgm": "FG Made",
            "fga": "FG Attempted",
            "fgmi": "FG Missed",
            "ftm": "FT Made",
            "fta": "FT Attempted",
            "ftmi": "FT Missed",
            "fg3m": "3PT Made",
            "fg3a": "3PT Attempted",
            "fg3mi": "3PT Missed",
            "turnover": "Turnovers",
            "dd": "Double Double",
            "td": "Triple Double",
        }
        
        for key, value in sorted(scoring_settings.items()):
            stat_name = stat_names.get(key, key.upper())
            lines.append(f"| {stat_name} | {value} |")
        
        return "\n".join(lines)
    
    async def _format_roster_with_trade(
        self,
        roster: Dict[str, Any],
        all_players: Dict[str, Dict],
        players_out: Optional[List[str]] = None,
        players_in: Optional[List[str]] = None,
        label: str = "ROSTER"
    ) -> str:
        """
        Format roster with trade modifications applied.
        
        Args:
            roster: Sleeper roster object
            all_players: All players dict
            players_out: Player IDs being removed (optional)
            players_in: Player IDs being added (optional)
            label: Section label
            
        Returns:
            Formatted markdown string
        """
        # Debug logging
        logger.info(f"_format_roster_with_trade: roster type={type(roster)}, all_players type={type(all_players)}")
        if not isinstance(all_players, dict):
            logger.error(f"BUG: all_players is {type(all_players)}: {str(all_players)[:200]}")
            raise TypeError(f"all_players must be dict, got {type(all_players)}")
        
        current_players = roster.get("players", []) or []
        
        # Apply trade modifications
        if players_out:
            current_players = [p for p in current_players if p not in players_out]
        if players_in:
            current_players.extend(players_in)
        
        if not current_players:
            return f"**{label}:** *Empty roster*"
        
        lines = [f"**{label}** ({len(current_players)} players):", ""]
        
        for player_id in current_players:
            player = all_players.get(player_id, {})
            full_name = player.get("full_name", "Unknown Player")
            position = player.get("position", "N/A")
            team = player.get("team", "FA")
            injury_status = player.get("injury_status", "")
            
            status_tag = f" ({injury_status})" if injury_status else ""
            lines.append(f"- **{full_name}** - {position} - {team}{status_tag}")
        
        return "\n".join(lines)
    
    async def _format_player_stats(
        self,
        player_ids: List[str],
        all_players: Dict[str, Dict]
    ) -> str:
        """
        Fetch and format player statistics from NBA MCP.
        Uses parallel processing for faster performance.
        
        Args:
            player_ids: List of Sleeper player IDs
            all_players: All players dict for name lookup
            
        Returns:
            Formatted markdown with player stats
        """
        if not player_ids:
            return "*No players*"
        
        # Fetch all player data in parallel
        async def fetch_player_data(player_id: str) -> Dict[str, Any]:
            """Fetch all data for a single player concurrently."""
            player = all_players.get(player_id, {})
            full_name = player.get("full_name", "Unknown Player")
            position = player.get("position", "N/A")
            team = player.get("team", "FA")
            injury_status = player.get("injury_status", "")
            nba_id = player.get("player_id")
            espn_id = player.get("espn_id")
            
            # Fetch stats and injury news in parallel
            tasks = []
            
            # Task 1: Player stats
            stats_task = self._calculate_roster_stats(
                player_name=full_name,
                player_id=nba_id or espn_id
            )
            tasks.append(stats_task)
            
            # Task 2: Injury news (if service available)
            if self.nba_news_service:
                injury_task = self.nba_news_service.check_injury_status(full_name)
                tasks.append(injury_task)
            else:
                tasks.append(asyncio.sleep(0))  # Placeholder
            
            # Execute in parallel
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            stats_summary = results[0] if not isinstance(results[0], Exception) else "*Stats unavailable*"
            injury_news = results[1] if len(results) > 1 and not isinstance(results[1], Exception) else None
            
            return {
                "full_name": full_name,
                "position": position,
                "team": team,
                "injury_status": injury_status,
                "stats_summary": stats_summary,
                "injury_news": injury_news
            }
        
        # Fetch all players in parallel
        logger.info(f"Fetching data for {len(player_ids)} players in parallel...")
        player_data_list = await asyncio.gather(
            *[fetch_player_data(pid) for pid in player_ids],
            return_exceptions=True
        )
        
        # Get all unique teams for schedule fetching
        teams = list(set([
            player_data.get("team") 
            for player_data in player_data_list 
            if isinstance(player_data, dict) and player_data.get("team") and player_data.get("team") != "FA"
        ]))
        
        # Fetch upcoming games for all teams in parallel
        logger.info(f"Fetching upcoming games for {len(teams)} teams in parallel...")
        upcoming_games_map = {}
        if teams:
            games_results = await asyncio.gather(
                *[self._get_upcoming_games_count(team) for team in teams],
                return_exceptions=True
            )
            for team, games_count in zip(teams, games_results):
                if not isinstance(games_count, Exception):
                    upcoming_games_map[team] = games_count
        
        # Format results
        lines = []
        for i, player_data in enumerate(player_data_list):
            if isinstance(player_data, Exception):
                logger.error(f"Error fetching player data: {player_data}")
                lines.append(f"### Unknown Player - Error loading data")
                continue
            
            # Get upcoming games from the map
            upcoming_games = upcoming_games_map.get(player_data["team"], 0)
            
            # Format player section
            status_tag = f" **({player_data['injury_status']})**" if player_data['injury_status'] else ""
            lines.append(f"### {player_data['full_name']} - {player_data['position']} - {player_data['team']}{status_tag}")
            lines.append(f"**Upcoming Games (Next 7 Days):** {upcoming_games}")
            lines.append(player_data['stats_summary'])
            
            # Add injury news if available (must be a dict, not a string)
            injury_news = player_data.get('injury_news')
            if injury_news and isinstance(injury_news, dict):
                lines.append(f"\n**Latest News (ESPN):**")
                lines.append(f"- **Status:** {injury_news.get('status', 'Unknown')}")
                if injury_news.get('description'):
                    lines.append(f"- **Details:** {injury_news['description']}")
                if injury_news.get('date'):
                    lines.append(f"- **Updated:** {injury_news['date']}")
            
            lines.append("")
        
        return "\n".join(lines)
    
    async def _calculate_roster_stats(
        self,
        player_name: str,
        player_id: Optional[str] = None
    ) -> str:
        """
        Calculate player season averages using NBA stats service.
        
        Args:
            player_name: Player full name
            player_id: NBA player ID (optional, for lookup)
            
        Returns:
            Formatted stats string (e.g., "25.3 PPG, 5.2 RPG, 4.8 APG")
        """
        try:
            # Use nba_stats_service if available
            if self.nba_stats_service:
                # Get player career stats from nba_stats_service
                # This returns per-game averages for the current season
                stats = await self.nba_stats_service.fetch_player_career_stats(player_name)
                
                if stats and len(stats) > 0:
                    # Get most recent season (first in list)
                    recent_season = stats[0]
                    ppg = recent_season.get("PTS", 0.0)
                    rpg = recent_season.get("REB", 0.0)
                    apg = recent_season.get("AST", 0.0)
                    fg_pct = recent_season.get("FG_PCT", 0.0)
                    
                    return f"**Season Averages:** {ppg:.1f} PPG, {rpg:.1f} RPG, {apg:.1f} APG, {fg_pct*100:.1f}% FG"
            
            return "*No stats available*"
            
        except Exception as e:
            logger.warning(f"Could not calculate stats for {player_name}: {e}")
            return "*Stats unavailable*"
    
    async def _get_upcoming_games_count(self, team_abbr: str) -> int:
        """
        Get count of upcoming games in next 7 days using NBA cache service.
        Uses instance-level schedule caching to avoid redundant API calls.
        
        Args:
            team_abbr: Team abbreviation (e.g., "LAL")
            
        Returns:
            Number of games in next 7 days
        """
        try:
            if not team_abbr or team_abbr == "FA":
                return 0
            
            today = datetime.now().date()
            end_date = today + timedelta(days=7)
            
            # Use nba_cache_service if available
            if self.nba_cache_service:
                # Fetch schedule once and cache it for this trade analysis
                if self._schedule_cache is None or self._schedule_cache_date != today:
                    logger.info("Fetching schedule for trade analysis (will be cached)")
                    self._schedule_cache = await self.nba_cache_service.get_cached_schedule(
                        start_date=str(today),
                        end_date=str(end_date)
                    )
                    self._schedule_cache_date = today
                else:
                    logger.debug("Using cached schedule for trade analysis")
                
                schedule = self._schedule_cache
                
                # Filter for upcoming games in next 7 days for this team
                team_games = []
                for game in schedule:
                    game_date_str = game.get("GAME_DATE_EST") or game.get("game_date")
                    if not game_date_str:
                        continue
                    
                    # Parse game date
                    try:
                        if isinstance(game_date_str, str):
                            game_date = datetime.strptime(game_date_str.split('T')[0], "%Y-%m-%d").date()
                        else:
                            game_date = game_date_str
                        
                        # Check if game is in next 7 days
                        if today <= game_date <= end_date:
                            # Check if this team is playing
                            home_team = game.get("HOME_TEAM_ABBREVIATION") or game.get("home_team_tricode") or ""
                            away_team = game.get("VISITOR_TEAM_ABBREVIATION") or game.get("away_team_tricode") or ""
                            
                            if team_abbr in (home_team, away_team):
                                team_games.append(game)
                    except Exception as parse_err:
                        logger.debug(f"Could not parse game date {game_date_str}: {parse_err}")
                        continue
                
                return len(team_games)
            
            # No services available
            logger.warning(f"No NBA schedule services available for {team_abbr}")
            return 0
            
        except Exception as e:
            logger.warning(f"Could not get schedule for {team_abbr}: {e}")
            import traceback
            logger.warning(f"Traceback: {traceback.format_exc()}")
            return 0
