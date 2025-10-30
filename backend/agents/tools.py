"""
Tool definitions for LLM function calling.
Provides real-time Sleeper API access to the roster advisor agent.
"""

from typing import List, Dict, Any, Optional
import logging
import asyncio

logger = logging.getLogger(__name__)


# Tool definitions for LLM function calling
ROSTER_ADVISOR_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "search_available_players",
            "description": "Search for available players on the waiver wire with comprehensive performance statistics and ESPN injury analysis. Returns a FULLY FORMATTED report with: 1) Top free agents ranked by injury-adjusted fantasy scores, 2) Detailed stats (PPG, RPG, APG), 3) Real-time ESPN injury reports with score adjustments shown (e.g., 45.8 → 13.7), 4) Complete explanation of ranking methodology. IMPORTANT: Return the tool's output EXACTLY as provided - it's already perfectly formatted for the user with all calculations, injury data, and explanations. Do NOT summarize or reformat. Use this when user asks about free agents, waiver wire pickups, or available players.",
            "parameters": {
                "type": "object",
                "properties": {
                    "position": {
                        "type": "string",
                        "description": "Filter by position (e.g., PG, SG, SF, PF, C). Leave empty for all positions.",
                        "enum": ["", "PG", "SG", "SF", "PF", "C"]
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of players to return (default: 10, max: 25)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 25
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_opponent_roster",
            "description": "Get the roster of another team in the league. Use this when the user asks about a specific opponent's team or wants to compare rosters.",
            "parameters": {
                "type": "object",
                "properties": {
                    "team_name": {
                        "type": "string",
                        "description": "The name of the opponent's team to look up"
                    }
                },
                "required": ["team_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_recent_transactions",
            "description": "Get recent adds, drops, and trades in the league. Use this when the user asks what's happened recently, who was picked up, or what trades occurred.",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Number of recent transactions to return (default: 10)",
                        "default": 10,
                        "minimum": 1,
                        "maximum": 50
                    }
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_all_league_rosters",
            "description": "Get all team rosters in the league with standings. Use this when the user asks about league standings, all teams, or wants an overview of the entire league.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_player_details",
            "description": "Search for detailed information about a specific player including NBA stats, team, position, injury status, AND which fantasy team owns them in your league. Use this when the user asks about a specific player or which team a player is on.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "The name of the player to search for (e.g., 'LeBron James', 'Victor Wembanyama')"
                    }
                },
                "required": ["player_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_player_season_stats",
            "description": "Get comprehensive NBA statistics for a specific player including season averages AND recent game-by-game performance (last 10 games with full box scores including PTS, REB, AST, STL, BLK, TOV for each game). Provides trend analysis, hot/cold streak detection, and consistency metrics. IMPORTANT: When user asks about 'last game' or wants to see fantasy point calculations, use the individual game stats from the game log, NOT season averages. Use this when the user asks about a player's performance, stats, averages, recent games, last game, trends, or how they're doing.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "The name of the player to get stats for (e.g., 'LeBron James', 'Luka Doncic')"
                    }
                },
                "required": ["player_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_espn_injury_news",
            "description": "Get the latest injury news and status from ESPN.com for a specific player. Returns real-time injury reports including injury type, game status (Out, Questionable, Doubtful, etc.), and detailed description. Use this when the user asks about injuries, what ESPN is reporting, player health status, or when they return from injury.",
            "parameters": {
                "type": "object",
                "properties": {
                    "player_name": {
                        "type": "string",
                        "description": "The name of the player to get injury news for (e.g., 'Jayson Tatum', 'Stephen Curry')"
                    }
                },
                "required": ["player_name"]
            }
        }
    }
]


class RosterAdvisorTools:
    """
    Tool executor for roster advisor agent.
    Executes function calls and returns results to the LLM.
    """
    
    def __init__(
        self,
        league_id: str,
        roster_id: int,
        sleeper_user_id: str,
        league_cache_service,
        player_cache_service,
        sleeper_service,
        nba_stats_service=None,
        nba_news_service=None
    ):
        """Initialize tools with necessary services."""
        self.league_id = league_id
        self.roster_id = roster_id
        self.sleeper_user_id = sleeper_user_id
        self.league_cache = league_cache_service
        self.player_cache = player_cache_service
        self.sleeper_service = sleeper_service
        self.nba_stats = nba_stats_service
        self.nba_news = nba_news_service
        
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """
        Execute a tool call and return formatted result.
        
        Args:
            tool_name: Name of the tool to execute
            arguments: Arguments for the tool
            
        Returns:
            Formatted string result for LLM
        """
        try:
            logger.info(f"🔧 Executing tool: {tool_name} with args: {arguments}")
            
            if tool_name == "search_available_players":
                return await self._search_available_players(
                    position=arguments.get("position", ""),
                    limit=arguments.get("limit", 10)
                )
            
            elif tool_name == "get_opponent_roster":
                return await self._get_opponent_roster(
                    team_name=arguments["team_name"]
                )
            
            elif tool_name == "get_recent_transactions":
                return await self._get_recent_transactions(
                    limit=arguments.get("limit", 10)
                )
            
            elif tool_name == "get_all_league_rosters":
                return await self._get_all_league_rosters()
            
            elif tool_name == "search_player_details":
                return await self._search_player_details(
                    player_name=arguments["player_name"]
                )
            
            elif tool_name == "get_player_season_stats":
                return await self._get_player_season_stats(
                    player_name=arguments["player_name"]
                )
            
            elif tool_name == "get_espn_injury_news":
                return await self._get_espn_injury_news(
                    player_name=arguments["player_name"]
                )
            
            else:
                return f"Error: Unknown tool '{tool_name}'"
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return f"Error executing {tool_name}: {str(e)}"
    
    async def _search_available_players(self, position: str, limit: int) -> str:
        """Search for available players on waiver wire with performance stats."""
        try:
            # Get all rosters to find rostered players
            rosters = self.league_cache.get_cached_rosters(self.league_id)
            if not rosters:
                async with self.sleeper_service as sleeper:
                    rosters = await sleeper.get_league_rosters(self.league_id)
            
            # Collect all rostered player IDs
            rostered_ids = set()
            for roster in rosters:
                players = roster.get("players", [])
                rostered_ids.update(players)
            
            # Get all players
            all_players = self.player_cache.get_cached_players()
            if not all_players:
                return "Error: Player data not available"
            
            # Determine current season (2025-26 NBA season)
            from datetime import datetime
            current_date = datetime.now()
            # NBA season starts in October, so if we're in Oct-Dec, use current year as start
            # If Jan-Sep, use previous year as start
            if current_date.month >= 10:  # October-December: current year is season start
                season_year = current_date.year
            else:  # January-September: previous year was season start
                season_year = current_date.year - 1
            current_season = f"{season_year}-{str(season_year + 1)[-2:]}"  # e.g., "2025-26"
            logger.info(f"Free agent search using current NBA season: {current_season}")
            
            # Filter available players
            available = []
            for player_id, player_info in all_players.items():
                # Skip if rostered
                if player_id in rostered_ids:
                    continue
                
                # Skip if not active
                status = player_info.get("status", "")
                if status not in ["Active", "ACT", ""]:
                    continue
                
                # Filter by position if specified
                if position:
                    positions = player_info.get("positions", [])
                    if position not in positions:
                        continue
                
                player_data = {
                    "player_id": player_id,
                    "name": player_info.get("name", "Unknown"),
                    "positions": player_info.get("positions", []),
                    "team": player_info.get("team", ""),
                    "injury_status": player_info.get("injury_status", "Healthy"),
                    "ppg": 0.0,
                    "rpg": 0.0,
                    "apg": 0.0,
                    "fantasy_score": 0.0
                }
                
                # Try to get stats to make informed recommendations
                if self.nba_stats:
                    try:
                        # Match to NBA ID
                        player_info_with_id = player_info.copy()
                        player_info_with_id["player_id"] = player_id
                        nba_person_id = self.nba_stats.match_sleeper_to_nba_id(player_info_with_id)
                        logger.debug(f"Matched {player_data['name']} to NBA ID: {nba_person_id}")
                        
                        if nba_person_id:
                            # Get career stats to check game counts
                            career_stats_dict = await self.nba_stats.fetch_player_career_stats(nba_person_id)
                            
                            selected_season_stats = None
                            season_used = current_season
                            
                            if career_stats_dict and isinstance(career_stats_dict, dict):
                                # Get regular season stats list
                                career_stats = career_stats_dict.get('regular_season', [])
                                logger.debug(f"Career stats for {player_data['name']}: {len(career_stats)} seasons")
                                
                                # Check current season (2025-26) first
                                current_season_stats = next(
                                    (s for s in career_stats if s.get('season') == current_season),
                                    None
                                )
                                
                                # If current season has 25+ games, use it
                                if current_season_stats and current_season_stats.get('games', 0) >= 25:
                                    selected_season_stats = current_season_stats
                                    season_used = current_season
                                else:
                                    # Fall back to previous season (2024-25)
                                    previous_season = f"{season_year - 1}-{str(season_year)[-2:]}"
                                    previous_season_stats = next(
                                        (s for s in career_stats if s.get('season') == previous_season),
                                        None
                                    )
                                    
                                    if previous_season_stats and previous_season_stats.get('games', 0) >= 25:
                                        selected_season_stats = previous_season_stats
                                        season_used = previous_season
                                    elif previous_season_stats:
                                        # Use previous season even with < 25 games if it's all we have
                                        selected_season_stats = previous_season_stats
                                        season_used = previous_season
                                    elif current_season_stats:
                                        # Use current season as last resort
                                        selected_season_stats = current_season_stats
                                        season_used = current_season
                            
                            if selected_season_stats:
                                ppg = selected_season_stats.get('ppg', 0)
                                rpg = selected_season_stats.get('rpg', 0)
                                apg = selected_season_stats.get('apg', 0)
                                spg = selected_season_stats.get('spg', 0)
                                bpg = selected_season_stats.get('bpg', 0)
                                tov = selected_season_stats.get('tov', 0)
                                
                                player_data['ppg'] = ppg
                                player_data['rpg'] = rpg
                                player_data['apg'] = apg
                                player_data['season_used'] = season_used
                                
                                # Calculate fantasy score (same formula as simulation)
                                player_data['fantasy_score'] = ppg + (1.2 * rpg) + (1.5 * apg) + (3 * spg) + (3 * bpg) - tov
                                logger.info(f"✅ {player_data['name']}: {ppg:.1f} PPG, {rpg:.1f} RPG, {apg:.1f} APG (Fantasy: {player_data['fantasy_score']:.1f}) from {season_used}")
                    except Exception as stat_error:
                        logger.warning(f"Could not fetch stats for {player_data['name']}: {stat_error}")
                        import traceback
                        logger.debug(f"Traceback: {traceback.format_exc()}")
                        # Continue without stats
                
                available.append(player_data)
            
            if not available:
                pos_text = f" at {position}" if position else ""
                return f"No available players found{pos_text}."
            
            # Fetch injury news for ALL players BEFORE sorting (in parallel for speed)
            if self.nba_news:
                try:
                    # Fetch news for all available players concurrently
                    logger.info(f"Fetching ESPN injury news for {len(available)} available players")
                    news_tasks = [
                        self.nba_news.get_player_injury(player['name'])
                        for player in available
                    ]
                    injury_news_results = await asyncio.gather(*news_tasks, return_exceptions=True)
                    
                    # Add news to player data and apply injury penalty to fantasy score
                    for player, injury_data in zip(available, injury_news_results):
                        if injury_data and not isinstance(injury_data, Exception):
                            game_status = injury_data.get('game_status', '').upper()
                            injury_type = injury_data.get('injury', '')
                            
                            # Store full injury info
                            player['espn_injury'] = injury_data
                            player['espn_status'] = game_status
                            
                            # Store original score before applying penalties
                            original_score = player['fantasy_score']
                            player['original_score'] = original_score
                            
                            if 'OUT' in game_status:
                                # Severe penalty for "Out" players
                                if any(keyword in injury_type.lower() for keyword in ['season', 'surgery', 'tear', 'rupture']):
                                    # Season-ending or major injury: Remove from consideration
                                    player['fantasy_score'] = -999
                                    player['injury_penalty'] = 'Season-ending injury - Not recommended'
                                    logger.info(f"❌ {player['name']}: Season-ending injury, removing from recommendations")
                                else:
                                    # Regular "Out" status: Major penalty
                                    player['fantasy_score'] *= 0.3  # 70% penalty
                                    player['injury_penalty'] = 'Currently Out - High risk'
                                    logger.info(f"⚠️ {player['name']}: Out status, penalty applied ({original_score:.1f} → {player['fantasy_score']:.1f})")
                            
                            elif 'DOUBTFUL' in game_status:
                                # Moderate penalty for doubtful
                                player['fantasy_score'] *= 0.6  # 40% penalty
                                player['injury_penalty'] = 'Doubtful - Moderate risk'
                                logger.info(f"⚠️ {player['name']}: Doubtful, penalty applied ({original_score:.1f} → {player['fantasy_score']:.1f})")
                            
                            elif 'QUESTIONABLE' in game_status or 'DAY-TO-DAY' in game_status:
                                # Light penalty for questionable
                                player['fantasy_score'] *= 0.85  # 15% penalty
                                player['injury_penalty'] = 'Questionable - Monitor closely'
                                logger.info(f"⚠️ {player['name']}: Questionable, light penalty applied ({original_score:.1f} → {player['fantasy_score']:.1f})")
                        
                except Exception as e:
                    logger.warning(f"Could not fetch injury news: {e}")
            
            # Filter out season-ending injuries
            available = [p for p in available if p['fantasy_score'] > -900]
            
            # Sort by adjusted fantasy score (descending) to show best players first
            available = sorted(available, key=lambda x: x["fantasy_score"], reverse=True)[:limit]
            
            # Format results with stats and news - Use XML markers to prevent LLM summarization
            result = "\n<TOOL_OUTPUT_START - DO NOT MODIFY OR SUMMARIZE - DISPLAY EXACTLY AS IS>\n\n"
            result += "="*70 + "\n"
            result += f"🏀 **TOP {len(available)} AVAILABLE FREE AGENTS"
            if position:
                result += f" (Position: {position})"
            result += "**\n"
            result += "="*70 + "\n"
            result += "✨ *Rankings intelligently adjusted using real-time ESPN injury data*\n\n"
            
            for i, player in enumerate(available, 1):
                pos_str = "/".join(player["positions"])
                result += f"{i}. **{player['name']}** ({pos_str}) - {player['team']}"
                
                if player['fantasy_score'] > 0:
                    season_label = player.get('season_used', current_season)
                    result += f"\n   📊 {season_label} Stats: {player['ppg']:.1f} PPG, {player['rpg']:.1f} RPG, {player['apg']:.1f} APG"
                    
                    # Show original score if injury penalty was applied
                    if player.get('original_score') and player.get('injury_penalty'):
                        original = player['original_score']
                        adjusted = player['fantasy_score']
                        result += f"\n   ⭐ Fantasy Score: {original:.1f} → **{adjusted:.1f}** (injury-adjusted)"
                    else:
                        result += f"\n   ⭐ Fantasy Score: {player['fantasy_score']:.1f}"
                else:
                    result += f"\n   ⚠️ No stats available"
                
                # Show ESPN injury details with clear explanation
                if player.get('espn_injury'):
                    espn_injury = player['espn_injury']
                    injury_type = espn_injury.get('injury', 'Unknown')
                    game_status = espn_injury.get('game_status', 'Unknown')
                    result += f"\n   📰 **ESPN Report:** {game_status} - {injury_type}"
                    
                    # Show injury penalty explanation
                    if player.get('injury_penalty'):
                        result += f"\n   🚨 **Risk Assessment:** {player['injury_penalty']}"
                
                # Show Sleeper injury status (if no ESPN data but Sleeper has injury)
                elif player["injury_status"] not in ["Healthy", "ACT", "", "None"]:
                    result += f"\n   🏥 Sleeper Status: {player['injury_status']}"
                
                result += "\n\n"
            
            # Add comprehensive explanation section
            result += "\n" + "="*60 + "\n"
            result += "💡 **HOW THESE RANKINGS WORK:**\n"
            result += "="*60 + "\n\n"
            result += f"**Step 1: Calculate Base Fantasy Score** ({current_season} season stats)\n"
            result += "• Formula: PTS + (1.2 × REB) + (1.5 × AST) + (3 × STL) + (3 × BLK) - TOV\n"
            result += "• Example: Player with 20 PPG, 5 RPG, 7 APG = 20 + 6 + 10.5 = 36.5 points\n"
            result += "• **Want to see a real calculation?** Ask me to show a specific player's last game!\n\n"
            result += "**Step 2: Apply ESPN Injury Adjustments**\n"
            result += "• 🚨 **Out**: -70% penalty (major risk, unlikely to play soon)\n"
            result += "• ⚠️ **Doubtful**: -40% penalty (moderate risk, probably won't play)\n"
            result += "• ⚡ **Questionable**: -15% penalty (minor risk, game-time decision)\n"
            result += "• ❌ **Season-Ending**: Completely removed from recommendations\n\n"
            result += "**Step 3: Re-rank by Adjusted Scores**\n"
            result += "• Healthy players rise to the top\n"
            result += "• Injured players drop based on severity\n"
            result += "• You see BOTH original and adjusted scores for transparency\n\n"
            result += "**Data Sources:**\n"
            result += f"• NBA Stats: {current_season} season (official NBA API)\n"
            result += "• Injury Reports: ESPN.com (updated throughout the day)\n"
            result += "• This ensures you get the most current, accurate recommendations!\n\n"
            result += "<TOOL_OUTPUT_END>\n"
            
            logger.info(f"Free agent search output length: {len(result)} chars")
            logger.info(f"Output starts with: {result[:200]}")
            logger.info(f"Output ends with: {result[-200:]}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching available players: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error searching available players: {str(e)}"
    
    async def _get_opponent_roster(self, team_name: str) -> str:
        """Get roster of a specific opponent team."""
        try:
            # Get all rosters
            rosters = self.league_cache.get_cached_rosters(self.league_id)
            if not rosters:
                async with self.sleeper_service as sleeper:
                    rosters = await sleeper.get_league_rosters(self.league_id)
            
            # Get league details for team names
            league = self.league_cache.get_cached_league_details(self.league_id)
            if not league:
                logger.info(f"League details cache miss, fetching from API for league {self.league_id}")
                async with self.sleeper_service as sleeper:
                    league_info = await sleeper.get_league(self.league_id)
                    league_users = await sleeper.get_league_users(self.league_id)
                    if league_info and league_users:
                        league = {**league_info, "users": league_users}
            else:
                # League is cached but might not have users
                if "users" not in league or not league.get("users"):
                    logger.info(f"League details cached but missing users, fetching users from API")
                    async with self.sleeper_service as sleeper:
                        league_users = await sleeper.get_league_users(self.league_id)
                        if league_users:
                            league["users"] = league_users
            
            # Build roster to team name map
            roster_to_team_name = {}
            if league:
                users = league.get("users", [])
                for roster in rosters:
                    roster_id = roster.get("roster_id")
                    owner_id = roster.get("owner_id")
                    
                    # Find user display name
                    team_display_name = f"Team {roster_id}"
                    if owner_id:
                        for user in users:
                            if user.get("user_id") == owner_id:
                                team_display_name = user.get("display_name", user.get("username", team_display_name))
                                break
                    
                    roster_to_team_name[roster_id] = team_display_name
            
            # Find matching roster by team name
            target_roster = None
            actual_team_name = None
            
            for roster in rosters:
                roster_id = roster.get("roster_id")
                current_team_name = roster_to_team_name.get(roster_id, f"Team {roster_id}")
                
                # Case-insensitive partial match
                if team_name.lower() in current_team_name.lower():
                    target_roster = roster
                    actual_team_name = current_team_name
                    break
            
            if not target_roster:
                return f"Could not find team matching '{team_name}'. Try being more specific."
            
            # Get player details
            player_ids = target_roster.get("players", [])
            starters = target_roster.get("starters", [])
            
            if not player_ids:
                return f"**{actual_team_name}** has no players on their roster."
            
            player_data = self.player_cache.get_players_bulk(player_ids)
            
            # Build roster display
            result = f"**{actual_team_name}** Roster:\n\n"
            
            # Record
            wins = target_roster.get("settings", {}).get("wins", 0)
            losses = target_roster.get("settings", {}).get("losses", 0)
            result += f"**Record:** {wins}-{losses}\n\n"
            
            # Starters
            starter_list = []
            bench_list = []
            
            for player_id in player_ids:
                player_info = player_data.get(player_id, {})
                name = player_info.get("name", "Unknown Player")
                positions = player_info.get("positions", [])
                pos_str = "/".join(positions) if positions else ""
                team = player_info.get("team", "")
                injury = player_info.get("injury_status", "")
                
                player_str = f"{name}"
                if pos_str:
                    player_str += f" ({pos_str})"
                if team:
                    player_str += f" - {team}"
                if injury and injury not in ["Healthy", "ACT", ""]:
                    player_str += f" - {injury}"
                
                if player_id in starters:
                    starter_list.append(player_str)
                else:
                    bench_list.append(player_str)
            
            if starter_list:
                result += "**Starters:**\n"
                for p in starter_list:
                    result += f"- {p}\n"
                result += "\n"
            
            if bench_list:
                result += "**Bench:**\n"
                for p in bench_list:
                    result += f"- {p}\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting opponent roster: {e}")
            return f"Error getting opponent roster: {str(e)}"
    
    async def _get_recent_transactions(self, limit: int) -> str:
        """Get recent league transactions."""
        try:
            # Fetch transactions from Sleeper
            async with self.sleeper_service as sleeper:
                transactions = await sleeper.get_league_transactions(self.league_id, week=None)
            
            if not transactions:
                return "No recent transactions found in the league."
            
            # Sort by timestamp (most recent first)
            transactions = sorted(
                transactions,
                key=lambda x: x.get("created", 0),
                reverse=True
            )[:limit]
            
            # Get player cache for names
            player_cache = self.player_cache.get_cached_players() or {}
            
            # Format transactions
            result = f"**Recent League Transactions** (Last {len(transactions)}):\n\n"
            
            for trans in transactions:
                trans_type = trans.get("type", "unknown")
                roster_ids = trans.get("roster_ids", [])
                adds = trans.get("adds", {})
                drops = trans.get("drops", {})
                
                if trans_type == "waiver":
                    # Waiver claim
                    for player_id, roster_id in adds.items():
                        player_name = player_cache.get(player_id, {}).get("name", player_id)
                        result += f"- Waiver: **{player_name}** added\n"
                    for player_id, roster_id in drops.items():
                        player_name = player_cache.get(player_id, {}).get("name", player_id)
                        result += f"- Waiver: **{player_name}** dropped\n"
                
                elif trans_type == "free_agent":
                    # Free agent add/drop
                    for player_id, roster_id in adds.items():
                        player_name = player_cache.get(player_id, {}).get("name", player_id)
                        result += f"- FA Add: **{player_name}**\n"
                    for player_id, roster_id in drops.items():
                        player_name = player_cache.get(player_id, {}).get("name", player_id)
                        result += f"- FA Drop: **{player_name}**\n"
                
                elif trans_type == "trade":
                    # Trade
                    result += f"- Trade between {len(roster_ids)} teams:\n"
                    for player_id, roster_id in adds.items():
                        player_name = player_cache.get(player_id, {}).get("name", player_id)
                        result += f"  - **{player_name}** traded\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting recent transactions: {e}")
            return f"Error getting recent transactions: {str(e)}"
    
    async def _get_all_league_rosters(self) -> str:
        """Get all team rosters with standings."""
        try:
            # Get rosters
            rosters = self.league_cache.get_cached_rosters(self.league_id)
            if not rosters:
                async with self.sleeper_service as sleeper:
                    rosters = await sleeper.get_league_rosters(self.league_id)
            
            # Get league details
            league = self.league_cache.get_cached_league_details(self.league_id)
            if not league:
                logger.info(f"League details cache miss, fetching from API for league {self.league_id}")
                async with self.sleeper_service as sleeper:
                    league_info = await sleeper.get_league(self.league_id)
                    league_users = await sleeper.get_league_users(self.league_id)
                    if league_info and league_users:
                        league = {**league_info, "users": league_users}
            else:
                # League is cached but might not have users
                if "users" not in league or not league.get("users"):
                    logger.info(f"League details cached but missing users, fetching users from API")
                    async with self.sleeper_service as sleeper:
                        league_users = await sleeper.get_league_users(self.league_id)
                        if league_users:
                            league["users"] = league_users
            
            # Build roster to team name map
            roster_to_team_name = {}
            if league:
                users = league.get("users", [])
                for roster in rosters:
                    roster_id = roster.get("roster_id")
                    owner_id = roster.get("owner_id")
                    
                    # Find user display name
                    team_display_name = f"Team {roster_id}"
                    if owner_id:
                        for user in users:
                            if user.get("user_id") == owner_id:
                                team_display_name = user.get("display_name", user.get("username", team_display_name))
                                break
                    
                    roster_to_team_name[roster_id] = team_display_name
            
            # Sort by wins
            rosters_with_record = []
            for roster in rosters:
                roster_id = roster.get("roster_id")
                wins = roster.get("settings", {}).get("wins", 0)
                losses = roster.get("settings", {}).get("losses", 0)
                total_points = roster.get("settings", {}).get("fpts", 0)
                
                team_name = roster_to_team_name.get(roster_id, f"Team {roster_id}")
                
                rosters_with_record.append({
                    "name": team_name,
                    "wins": wins,
                    "losses": losses,
                    "points": total_points,
                    "roster_id": roster_id
                })
            
            # Sort by wins, then points
            rosters_with_record.sort(key=lambda x: (x["wins"], x["points"]), reverse=True)
            
            # Format standings
            result = f"**League Standings** ({len(rosters_with_record)} teams):\n\n"
            
            for i, team in enumerate(rosters_with_record, 1):
                result += f"{i}. **{team['name']}** - {team['wins']}-{team['losses']} ({team['points']:.1f} pts)\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting league rosters: {e}")
            return f"Error getting league rosters: {str(e)}"
    
    async def _search_player_details(self, player_name: str) -> str:
        """Search for detailed player information including fantasy team ownership."""
        try:
            # Get all players
            all_players = self.player_cache.get_cached_players()
            if not all_players:
                return "Error: Player data not available"
            
            # Search for player (case-insensitive)
            matches = []
            search_lower = player_name.lower()
            
            for player_id, player_info in all_players.items():
                name = player_info.get("name", "")
                if search_lower in name.lower():
                    player_info_copy = player_info.copy()
                    player_info_copy["player_id"] = player_id
                    matches.append(player_info_copy)
            
            if not matches:
                return f"No players found matching '{player_name}'"
            
            if len(matches) > 5:
                return f"Found {len(matches)} players matching '{player_name}'. Please be more specific."
            
            # Get all rosters to check ownership
            rosters = self.league_cache.get_cached_rosters(self.league_id)
            if not rosters:
                async with self.sleeper_service as sleeper:
                    rosters = await sleeper.get_league_rosters(self.league_id)
            
            # Get league details for team names
            league = self.league_cache.get_cached_league_details(self.league_id)
            
            # If league details not cached, fetch from API
            if not league:
                logger.info(f"League details cache miss, fetching from API for league {self.league_id}")
                async with self.sleeper_service as sleeper:
                    league_info = await sleeper.get_league(self.league_id)
                    league_users = await sleeper.get_league_users(self.league_id)
                    if league_info and league_users:
                        league = {**league_info, "users": league_users}
            else:
                # League is cached but might not have users
                if "users" not in league or not league.get("users"):
                    logger.info(f"League details cached but missing users, fetching users from API")
                    async with self.sleeper_service as sleeper:
                        league_users = await sleeper.get_league_users(self.league_id)
                        if league_users:
                            league["users"] = league_users
            
            logger.info(f"League has {len(league.get('users', []))} users" if league else "League is None")
            
            # Build ownership map
            ownership_map = {}  # player_id -> (roster_id, team_name)
            if rosters:
                for roster in rosters:
                    roster_id = roster.get("roster_id")
                    owner_id = roster.get("owner_id")
                    players = roster.get("players", [])
                    
                    # Get team name
                    team_name = f"Team {roster_id}"
                    if league and owner_id:
                        users = league.get("users", [])
                        for user in users:
                            if user.get("user_id") == owner_id:
                                team_name = user.get("display_name", user.get("username", team_name))
                                break
                    
                    for player_id in players:
                        ownership_map[player_id] = (roster_id, team_name)
            
            # Format results
            result = f"**Player Details for '{player_name}':**\n\n"
            
            for player in matches:
                name = player.get("name", "Unknown")
                player_id = player.get("player_id")
                positions = player.get("positions", [])
                pos_str = "/".join(positions) if positions else "N/A"
                team = player.get("team", "FA")
                status = player.get("status", "Unknown")
                injury = player.get("injury_status", "Healthy")
                
                result += f"**{name}**\n"
                result += f"- Position: {pos_str}\n"
                result += f"- NBA Team: {team}\n"
                result += f"- Status: {status}\n"
                if injury not in ["Healthy", "ACT", ""]:
                    result += f"- Injury: {injury}\n"
                
                # Add fantasy team ownership
                if player_id in ownership_map:
                    roster_id, fantasy_team = ownership_map[player_id]
                    result += f"- **Fantasy Team: {fantasy_team}** (Roster #{roster_id})\n"
                else:
                    result += f"- **Fantasy Team: Available (Free Agent)**\n"
                
                result += "\n"
            
            return result
            
        except Exception as e:
            logger.error(f"Error searching player details: {e}")
            return f"Error searching player details: {str(e)}"
    
    async def _get_player_season_stats(self, player_name: str) -> str:
        """Get NBA season statistics for a specific player including recent game performance."""
        try:
            # Use NBA stats service
            if not self.nba_stats:
                return "NBA stats service is not available. Historical stats are disabled."
            
            # Get all players to find player ID
            all_players = self.player_cache.get_cached_players()
            if not all_players:
                return "Error: Player data not available"
            
            # Search for player (case-insensitive)
            sleeper_player_data = None
            search_lower = player_name.lower()
            
            for pid, player_info in all_players.items():
                name = player_info.get("name", "")
                if search_lower in name.lower():
                    sleeper_player_data = player_info.copy()
                    sleeper_player_data["player_id"] = pid
                    player_name = name  # Use the exact name
                    break
            
            if not sleeper_player_data:
                return f"No player found matching '{player_name}'"
            
            # Match Sleeper player to NBA person ID
            nba_person_id = self.nba_stats.match_sleeper_to_nba_id(sleeper_player_data)
            
            if not nba_person_id:
                return f"**{player_name}**\n\nCould not find NBA stats for this player. They may be a retired player or not currently tracked by NBA.com."
            
            # Determine current NBA season dynamically
            from datetime import datetime
            current_date = datetime.now()
            if current_date.month >= 10:  # Oct-Dec: current year to next year
                season_year = current_date.year
            else:  # Jan-Sep: previous year to current year
                season_year = current_date.year - 1
            current_season = f"{season_year}-{str(season_year + 1)[-2:]}"
            
            # Get current season stats
            season_stats = await self.nba_stats.fetch_player_season_averages(
                nba_person_id=nba_person_id,
                season=current_season
            )
            
            if not season_stats:
                return f"**{player_name}**\n\nNo season stats available yet for the {current_season} season. The player may not have played any games yet."
            
            # Format the season averages
            result = f"**{current_season} NBA Season Stats for {player_name}:**\n\n"
            result += f"**Season Averages:**\n"
            result += f"- Points: {season_stats.get('ppg', 0):.1f} PPG\n"
            result += f"- Rebounds: {season_stats.get('rpg', 0):.1f} RPG\n"
            result += f"- Assists: {season_stats.get('apg', 0):.1f} APG\n"
            result += f"- Steals: {season_stats.get('spg', 0):.1f} SPG\n"
            result += f"- Blocks: {season_stats.get('bpg', 0):.1f} BPG\n"
            result += f"- Turnovers: {season_stats.get('tov', 0):.1f} TOV\n"
            result += f"- FG%: {season_stats.get('fg_pct', 0):.1%}\n"
            result += f"- 3P%: {season_stats.get('fg3_pct', 0):.1%}\n"
            result += f"- FT%: {season_stats.get('ft_pct', 0):.1%}\n\n"
            
            # Fetch recent game log for context
            try:
                game_log = await self.nba_stats.fetch_player_game_log(
                    nba_person_id=nba_person_id,
                    season=current_season
                )
                
                # If no games in current season yet, try previous season
                game_log_season = current_season
                if not game_log or len(game_log) == 0:
                    logger.info(f"No games found for {player_name} in {current_season}, trying previous season")
                    previous_season_year = season_year - 1
                    previous_season = f"{previous_season_year}-{str(previous_season_year + 1)[-2:]}"
                    game_log = await self.nba_stats.fetch_player_game_log(
                        nba_person_id=nba_person_id,
                        season=previous_season
                    )
                    game_log_season = previous_season
                
                if game_log and len(game_log) > 0:
                    # Show last 10 games for comprehensive recent performance context
                    num_recent_games = min(10, len(game_log))
                    recent_games = game_log[:num_recent_games]
                    
                    # Show which season the game log is from
                    if game_log_season != current_season:
                        result += f"**Last {num_recent_games} Games** (from {game_log_season} season - {current_season} season just started):\n"
                    else:
                        result += f"**Last {num_recent_games} Games:**\n"
                    
                    for i, game in enumerate(recent_games, 1):
                        date = game.get('game_date', 'N/A')
                        matchup = game.get('matchup', 'N/A')
                        pts = game.get('points', 0)
                        reb = game.get('rebounds', 0)
                        ast = game.get('assists', 0)
                        stl = game.get('steals', 0)
                        blk = game.get('blocks', 0)
                        tov = game.get('turnovers', 0)
                        wl = game.get('wl', '')
                        
                        # Calculate fantasy points for this game
                        fantasy_pts = pts + (1.2 * reb) + (1.5 * ast) + (3 * stl) + (3 * blk) - tov
                        
                        result += f"{i}. {date} {matchup} ({wl}): {pts} PTS, {reb} REB, {ast} AST, {stl} STL, {blk} BLK, {tov} TOV"
                        result += f" → **Fantasy: {fantasy_pts:.1f}**\n"
                    
                    # Calculate comprehensive recent trends
                    recent_ppg = sum(g.get('points', 0) for g in recent_games) / len(recent_games)
                    recent_rpg = sum(g.get('rebounds', 0) for g in recent_games) / len(recent_games)
                    recent_apg = sum(g.get('assists', 0) for g in recent_games) / len(recent_games)
                    
                    # Determine trend based on scoring
                    season_ppg = season_stats.get('ppg', 0)
                    if recent_ppg > season_ppg * 1.1:
                        trend = "� Hot"
                    elif recent_ppg < season_ppg * 0.85:
                        trend = "📉 Cold"
                    else:
                        trend = "➡️ Steady"
                    
                    result += f"\n**Recent Performance ({num_recent_games} games):**\n"
                    result += f"- {trend} streak\n"
                    result += f"- Scoring: {recent_ppg:.1f} PPG (Season: {season_ppg:.1f})\n"
                    result += f"- Rebounding: {recent_rpg:.1f} RPG (Season: {season_stats.get('rpg', 0):.1f})\n"
                    result += f"- Assists: {recent_apg:.1f} APG (Season: {season_stats.get('apg', 0):.1f})\n"
                    
                    # Add consistency note
                    if len(recent_games) >= 3:
                        last_3_ppg = sum(g.get('points', 0) for g in recent_games[:3]) / 3
                        consistency = "consistent" if abs(last_3_ppg - recent_ppg) < 3 else "volatile"
                        result += f"- Performance: {consistency.capitalize()}\n"
            
            except Exception as game_log_error:
                logger.warning(f"Could not fetch game log for {player_name}: {game_log_error}")
                # Continue without game log data - season averages are still valuable
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting player season stats: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error getting player season stats: {str(e)}"
    
    
    async def _get_espn_injury_news(self, player_name: str) -> str:
        """Get ESPN injury news for a specific player."""
        try:
            if not self.nba_news:
                return "ESPN injury news service is not available."
            
            logger.info(f"🏥 Fetching ESPN injury news for {player_name}")
            
            # Get injury information from ESPN
            injury_data = await self.nba_news.get_player_injury(player_name)
            
            if not injury_data:
                return f"**ESPN Injury Report for {player_name}:**\n\nNo injury information found. Player appears to be healthy or not listed on ESPN's injury report."
            
            # Format the injury report
            result = f"**ESPN Injury Report for {player_name}:**\n\n"
            result += f"**Team:** {injury_data.get('team', 'Unknown')}\n"
            result += f"**Position:** {injury_data.get('position', 'N/A')}\n"
            result += f"**Game Status:** {injury_data.get('game_status', 'Unknown')}\n"
            result += f"**Injury:** {injury_data.get('injury', 'Not specified')}\n"
            
            date = injury_data.get('date', '')
            if date:
                result += f"**Date Updated:** {date}\n"
            
            result += f"\n📰 *Source: ESPN.com Injury Report (updated throughout the day)*"
            
            logger.info(f"✅ ESPN injury news retrieved for {player_name}: {injury_data.get('game_status', 'N/A')}")
            
            return result
            
        except Exception as e:
            logger.error(f"Error getting ESPN injury news for {player_name}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return f"Error fetching ESPN injury news for {player_name}: {str(e)}"
