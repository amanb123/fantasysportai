"""
NBA Stats service for fetching NBA schedule and player data.
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime
import httpx
import asyncio
import json
from backend.config import settings

logger = logging.getLogger(__name__)


class NBAStatsService:
    """Service for interacting with NBA CDN and nba_api."""
    
    def __init__(self, redis_service=None):
        """Initialize NBA stats service with HTTP client configuration and optional Redis."""
        self.cdn_base_url = settings.NBA_CDN_BASE_URL
        self.timeout = settings.NBA_CDN_TIMEOUT
        self.redis_service = redis_service
        # Cache configuration
        self.historical_cache_ttl = settings.NBA_HISTORICAL_STATS_CACHE_TTL
        self.historical_cache_prefix = settings.NBA_HISTORICAL_STATS_CACHE_KEY_PREFIX
        # Don't store client - create per request for concurrency safety
    
    async def __aenter__(self):
        """Async context manager entry - no-op for backward compatibility."""
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - no-op for backward compatibility."""
        pass
    
    def _get_stats_cache_ttl(self, season_year: str) -> int:
        """
        Determine appropriate cache TTL based on whether it's the current season.
        Current season stats change daily, historical seasons are static.
        
        Args:
            season_year: Season in format "2025-26"
            
        Returns:
            TTL in seconds (6 hours for current season, 7 days for historical)
        """
        # Get current date to determine active season
        from datetime import datetime
        current_date = datetime.now()
        current_year = current_date.year
        current_month = current_date.month
        
        # NBA season runs from October to June
        # If it's Oct-Dec, current season is YYYY-YY format (e.g., 2025-26)
        # If it's Jan-Sep, current season is (YYYY-1)-(YY) format (e.g., 2024-25 in Jan 2025)
        if current_month >= 10:  # October, November, December
            current_season = f"{current_year}-{str(current_year + 1)[-2:]}"
        else:  # January through September
            current_season = f"{current_year - 1}-{str(current_year)[-2:]}"
        
        # If this is the current season, use shorter TTL (6 hours = 21600 seconds)
        # Stats update daily, so 6 hours ensures fresh data without hammering the API
        if season_year == current_season:
            return 21600  # 6 hours
        else:
            # Historical seasons don't change, cache for 7 days
            return self.historical_cache_ttl
    
    async def fetch_season_schedule(self, season: str = "2024") -> Optional[List[Dict]]:
        """
        Fetch full season schedule from NBA CDN.
        
        Args:
            season: Season year (e.g., "2024")
            
        Returns:
            List[Dict]: List of game dicts or None on error
        """
        try:
            logger.info(f"Fetching NBA season schedule for {season}")
            
            # Create client per request for concurrency safety
            async with httpx.AsyncClient(
                base_url=self.cdn_base_url,
                timeout=self.timeout,
                headers={"User-Agent": "Fantasy Basketball League App"}
            ) as client:
                # NBA CDN schedule endpoint (no leading slash - relative to base_url)
                response = await client.get("staticData/scheduleLeagueV2_1.json")
                
                if response.status_code != 200:
                    logger.error(f"NBA CDN returned status {response.status_code}")
                    return None
                
                data = response.json()
                
                # Extract games from the schedule
                games = []
                league_schedule = data.get("leagueSchedule", {})
                game_dates = league_schedule.get("gameDates", [])
                
                for game_date_entry in game_dates:
                    for game in game_date_entry.get("games", []):
                        transformed_game = self._transform_schedule_game(game, season)
                        if transformed_game:
                            games.append(transformed_game)
                
                logger.info(f"Retrieved {len(games)} games from NBA schedule")
                return games
            
        except httpx.TimeoutException:
            logger.error("Timeout fetching NBA schedule")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching NBA schedule: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching NBA schedule: {e}")
            return None
    
    async def fetch_todays_scoreboard(self) -> Optional[List[Dict]]:
        """
        Fetch today's games from NBA CDN with live scores.
        
        Returns:
            List[Dict]: List of game dicts with scores or None on error
        """
        try:
            logger.info("Fetching today's NBA scoreboard")
            
            # Create client per request for concurrency safety
            async with httpx.AsyncClient(
                base_url=self.cdn_base_url,
                timeout=self.timeout,
                headers={"User-Agent": "Fantasy Basketball League App"}
            ) as client:
                # NBA CDN scoreboard endpoint (no leading slash - relative to base_url)
                response = await client.get("liveData/scoreboard/todaysScoreboard_00.json")
                
                if response.status_code == 404:
                    logger.info("No games today or scoreboard not available")
                    return []
                
                if response.status_code != 200:
                    logger.error(f"NBA CDN scoreboard returned status {response.status_code}")
                    return None
                
                data = response.json()
                
                # Extract games from scoreboard
                games = []
                scoreboard = data.get("scoreboard", {})
                game_list = scoreboard.get("games", [])
                
                for game in game_list:
                    transformed_game = self._transform_scoreboard_game(game)
                    if transformed_game:
                        games.append(transformed_game)
                
                logger.info(f"Retrieved {len(games)} games from today's scoreboard")
                return games
            
        except httpx.TimeoutException:
            logger.error("Timeout fetching today's scoreboard")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching scoreboard: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching scoreboard: {e}")
            return None
    
    async def fetch_player_info(self, nba_person_id: int) -> Optional[Dict]:
        """
        Fetch player info using nba_api.
        
        Args:
            nba_person_id: NBA.com person ID
            
        Returns:
            Dict: Player info dict or None on error
        """
        try:
            logger.info(f"Fetching NBA player info for person ID {nba_person_id}")
            
            # Import nba_api dynamically to avoid startup errors if not installed
            try:
                from nba_api.stats.endpoints import commonplayerinfo
            except ImportError:
                logger.error("nba_api not installed - cannot fetch player info")
                return None
            
            # Fetch player info
            player_info = commonplayerinfo.CommonPlayerInfo(player_id=nba_person_id)
            player_data = player_info.get_dict()
            
            # Extract player info from response
            result_sets = player_data.get("resultSets", [])
            if not result_sets:
                logger.warning(f"No result sets for player {nba_person_id}")
                return None
            
            # First result set contains player info
            player_info_set = result_sets[0]
            headers = player_info_set.get("headers", [])
            rows = player_info_set.get("rowSet", [])
            
            if not rows:
                logger.warning(f"No player data for {nba_person_id}")
                return None
            
            # Convert to dict
            player_row = rows[0]
            player_dict = dict(zip(headers, player_row))
            
            # Transform to internal format
            transformed = self._transform_player_info(player_dict)
            return transformed
            
        except Exception as e:
            logger.error(f"Error fetching player info for {nba_person_id}: {e}")
            return None
    
    def match_sleeper_to_nba_id(self, sleeper_player_data: Dict) -> Optional[int]:
        """
        Match Sleeper player to NBA person ID using name-based resolution.
        
        Args:
            sleeper_player_data: Sleeper player data dict
            
        Returns:
            int: NBA person ID or None if no match found
        """
        try:
            # Get player name from Sleeper data - try multiple fields
            player_name = (
                sleeper_player_data.get("name") or           # Sleeper NBA format
                sleeper_player_data.get("full_name") or       # Alternative format  
                sleeper_player_data.get("player_name")        # Another alternative
            )
            
            if not player_name:
                # Try constructing from first/last
                first = sleeper_player_data.get("first_name", "")
                last = sleeper_player_data.get("last_name", "")
                player_name = f"{first} {last}".strip()
            
            if not player_name:
                logger.debug(f"No name found for player {sleeper_player_data.get('player_id')}")
                return None
            
            # Use nba_api static players to find by name
            try:
                from nba_api.stats.static import players
                
                # Find players by full name
                found_players = players.find_players_by_full_name(player_name)
                
                if not found_players:
                    logger.debug(f"No NBA player found for name: {player_name}")
                    return None
                
                # If multiple matches, try to disambiguate by team
                if len(found_players) > 1:
                    sleeper_team = sleeper_player_data.get("team", "").upper()
                    if sleeper_team:
                        for player in found_players:
                            # Check if player is currently on the team
                            # Note: nba_api static data may not have current team, so take first active match
                            if player.get("is_active"):
                                logger.info(f"Matched {player_name} to NBA ID {player['id']} (active player)")
                                return player["id"]
                
                # Return first match (most likely current/active player)
                nba_id = found_players[0]["id"]
                logger.info(f"Matched {player_name} to NBA ID {nba_id}")
                return nba_id
                
            except ImportError:
                logger.error("nba_api not installed - cannot match player by name")
                return None
                
        except Exception as e:
            logger.error(f"Error matching player IDs: {e}")
            return None
    
    def _transform_schedule_game(self, raw_game: Dict, season: str) -> Optional[Dict]:
        """
        Transform NBA CDN game format to internal format.
        
        Args:
            raw_game: Raw game dict from NBA CDN
            season: Season year
            
        Returns:
            Dict: Transformed game dict or None
        """
        try:
            game_id = raw_game.get("gameId", "")
            game_date_str = raw_game.get("gameDateTimeUTC", "")
            
            # Parse datetime
            game_time_utc = None
            if game_date_str:
                try:
                    game_time_utc = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                except:
                    game_time_utc = datetime.utcnow()
            
            home_team = raw_game.get("homeTeam", {})
            away_team = raw_game.get("awayTeam", {})
            
            return {
                "game_id": game_id,
                "season": season,
                "game_date": game_time_utc.date() if game_time_utc else None,
                "game_time_utc": game_time_utc if game_time_utc else None,
                "home_team_id": str(home_team.get("teamId", "")),
                "home_team_name": home_team.get("teamName", ""),
                "home_team_tricode": home_team.get("teamTricode", ""),
                "home_score": None,
                "away_team_id": str(away_team.get("teamId", "")),
                "away_team_name": away_team.get("teamName", ""),
                "away_team_tricode": away_team.get("teamTricode", ""),
                "away_score": None,
                "game_status": "scheduled"
            }
            
        except Exception as e:
            logger.error(f"Error transforming schedule game: {e}")
            return None
    
    def _transform_scoreboard_game(self, raw_game: Dict) -> Optional[Dict]:
        """
        Transform NBA CDN scoreboard game format to internal format.
        
        Args:
            raw_game: Raw game dict from NBA CDN scoreboard
            
        Returns:
            Dict: Transformed game dict or None
        """
        try:
            game_id = raw_game.get("gameId", "")
            game_date_str = raw_game.get("gameTimeUTC", "")
            
            # Parse datetime
            game_time_utc = None
            if game_date_str:
                try:
                    game_time_utc = datetime.fromisoformat(game_date_str.replace("Z", "+00:00"))
                except:
                    game_time_utc = datetime.utcnow()
            
            home_team = raw_game.get("homeTeam", {})
            away_team = raw_game.get("awayTeam", {})
            
            # Extract scores
            home_score = home_team.get("score")
            away_score = away_team.get("score")
            
            # Determine game status
            game_status_code = raw_game.get("gameStatus", 1)
            if game_status_code == 1:
                game_status = "scheduled"
            elif game_status_code == 2:
                game_status = "in_progress"
            elif game_status_code == 3:
                game_status = "final"
            else:
                game_status = "unknown"
            
            return {
                "game_id": game_id,
                "game_date": game_time_utc.date() if game_time_utc else None,
                "game_time_utc": game_time_utc if game_time_utc else None,
                "home_team_id": str(home_team.get("teamId", "")),
                "home_team_name": home_team.get("teamName", ""),
                "home_team_tricode": home_team.get("teamTricode", ""),
                "home_score": home_score,
                "away_team_id": str(away_team.get("teamId", "")),
                "away_team_name": away_team.get("teamName", ""),
                "away_team_tricode": away_team.get("teamTricode", ""),
                "away_score": away_score,
                "game_status": game_status,
                "season": raw_game.get("seasonYear", settings.NBA_CURRENT_SEASON)
            }
            
        except Exception as e:
            logger.error(f"Error transforming scoreboard game: {e}")
            return None
    
    def _transform_player_info(self, nba_player_dict: Dict) -> Dict:
        """
        Transform nba_api player info to internal format (matches PlayerInfoModel).
        
        Args:
            nba_player_dict: Player data from nba_api
            
        Returns:
            Dict: Transformed player info
        """
        try:
            # Parse birthdate to date object if present
            birthdate = None
            if nba_player_dict.get("BIRTHDATE"):
                try:
                    from datetime import datetime
                    birthdate = datetime.strptime(nba_player_dict["BIRTHDATE"], "%Y-%m-%dT%H:%M:%S").date()
                except:
                    try:
                        birthdate = datetime.fromisoformat(nba_player_dict["BIRTHDATE"]).date()
                    except:
                        pass
            
            return {
                "nba_person_id": str(nba_player_dict.get("PERSON_ID", "")),
                "full_name": nba_player_dict.get("DISPLAY_FIRST_LAST", ""),
                "first_name": nba_player_dict.get("FIRST_NAME", ""),
                "last_name": nba_player_dict.get("LAST_NAME", ""),
                "birthdate": birthdate,
                "country": nba_player_dict.get("COUNTRY"),
                "height": nba_player_dict.get("HEIGHT"),  # Keep as "6-7" format
                "weight": str(nba_player_dict.get("WEIGHT", "")) if nba_player_dict.get("WEIGHT") else None,
                "jersey_number": nba_player_dict.get("JERSEY"),
                "position": nba_player_dict.get("POSITION"),
                "draft_year": int(nba_player_dict.get("DRAFT_YEAR")) if nba_player_dict.get("DRAFT_YEAR") and str(nba_player_dict.get("DRAFT_YEAR")).isdigit() else None,
                "draft_round": int(nba_player_dict.get("DRAFT_ROUND")) if nba_player_dict.get("DRAFT_ROUND") and str(nba_player_dict.get("DRAFT_ROUND")).isdigit() else None,
                "draft_number": int(nba_player_dict.get("DRAFT_NUMBER")) if nba_player_dict.get("DRAFT_NUMBER") and str(nba_player_dict.get("DRAFT_NUMBER")).isdigit() else None,
                "nba_team_id": str(nba_player_dict.get("TEAM_ID", "")) if nba_player_dict.get("TEAM_ID") else None,
                "nba_team_name": nba_player_dict.get("TEAM_NAME"),
                "school": nba_player_dict.get("SCHOOL")
            }
        except Exception as e:
            logger.error(f"Error transforming player info: {e}")
            return {}
    
    def _parse_height(self, height_str: Optional[str]) -> Optional[int]:
        """
        Parse height string (e.g., "6-7") to inches.
        
        Args:
            height_str: Height string in format "feet-inches"
            
        Returns:
            int: Total inches or None
        """
        if not height_str:
            return None
        
        try:
            parts = height_str.split("-")
            if len(parts) == 2:
                feet = int(parts[0])
                inches = int(parts[1])
                return (feet * 12) + inches
        except:
            pass
        
        return None

    # Historical Stats Methods
    
    async def fetch_player_career_stats(self, nba_person_id: int) -> Optional[Dict]:
        """
        Fetch career stats for a player using nba_api.
        
        Args:
            nba_person_id: NBA person ID
            
        Returns:
            Dict with regular_season and playoffs career stats or None on error
        """
        try:
            # Check cache first
            if self.redis_service and self.redis_service.is_connected():
                cache_key = f"{self.historical_cache_prefix}:career:{nba_person_id}"
                cached_data = self.redis_service.get_json(cache_key)
                if cached_data:
                    logger.info(f"Retrieved career stats from cache for player {nba_person_id}")
                    return cached_data
            
            logger.info(f"Fetching career stats for NBA player {nba_person_id}")
            
            # Lazy import nba_api
            try:
                from nba_api.stats.endpoints import playercareerstats
            except ImportError as ie:
                logger.error(f"nba_api not installed: {ie}")
                return None
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(settings.NBA_API_REQUEST_DELAY)
            
            # Fetch career stats - run in thread pool since nba_api is synchronous
            career_stats = await asyncio.to_thread(
                playercareerstats.PlayerCareerStats,
                player_id=nba_person_id,
                per_mode36="PerGame"
            )
            
            # Extract data frames
            regular_season_df = career_stats.get_data_frames()[0]
            playoffs_df = career_stats.get_data_frames()[1] if len(career_stats.get_data_frames()) > 1 else None
            
            # Transform to internal format
            result = self._transform_career_stats({
                "regular_season": regular_season_df.to_dict('records') if not regular_season_df.empty else [],
                "playoffs": playoffs_df.to_dict('records') if playoffs_df is not None and not playoffs_df.empty else []
            })
            
            # Cache the result with dynamic TTL based on most recent season
            if result and self.redis_service and self.redis_service.is_connected():
                # Determine TTL based on most recent season in the data
                cache_ttl = self.historical_cache_ttl  # Default to 7 days
                
                if result.get('regular_season') and len(result['regular_season']) > 0:
                    # Get the most recent season (last item in the list)
                    most_recent_season = result['regular_season'][-1].get('season', '')
                    if most_recent_season:
                        cache_ttl = self._get_stats_cache_ttl(most_recent_season)
                        logger.info(f"Using {cache_ttl}s TTL for player {nba_person_id} (most recent season: {most_recent_season})")
                
                cache_key = f"{self.historical_cache_prefix}:career:{nba_person_id}"
                self.redis_service.set_json(cache_key, result, cache_ttl)
                logger.info(f"Cached career stats for player {nba_person_id}")
            
            logger.info(f"Successfully fetched career stats for player {nba_person_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching career stats for player {nba_person_id}: {e}")
            return None
    
    async def fetch_player_game_log(
        self, 
        nba_person_id: int, 
        season: str = "2024-25", 
        season_type: str = "Regular Season"
    ) -> Optional[List[Dict]]:
        """
        Fetch game log for a player using nba_api.
        
        Args:
            nba_person_id: NBA person ID
            season: Season string (e.g., "2024-25")
            season_type: "Regular Season" or "Playoffs"
            
        Returns:
            List of game dicts or None on error
        """
        try:
            logger.info(f"Fetching game log for NBA player {nba_person_id}, season {season}")
            
            # Lazy import nba_api
            try:
                from nba_api.stats.endpoints import playergamelog
            except ImportError as ie:
                logger.error(f"nba_api not installed: {ie}")
                return None
            
            # Add delay to avoid rate limiting
            await asyncio.sleep(settings.NBA_API_REQUEST_DELAY)
            
            # Fetch game log - run in thread pool
            game_log = await asyncio.to_thread(
                playergamelog.PlayerGameLog,
                player_id=nba_person_id,
                season=season,
                season_type_all_star=season_type
            )
            
            # Extract data frame
            game_log_df = game_log.get_data_frames()[0]
            
            # Transform to internal format
            result = self._transform_game_log(game_log_df.to_dict('records') if not game_log_df.empty else [])
            
            logger.info(f"Successfully fetched {len(result)} games for player {nba_person_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching game log for player {nba_person_id}: {e}")
            return None
    
    async def fetch_player_season_averages(
        self, 
        nba_person_id: int, 
        season: str = "2024-25"
    ) -> Optional[Dict]:
        """
        Fetch season averages for a specific season using nba_api.
        
        Args:
            nba_person_id: NBA person ID
            season: Season string (e.g., "2024-25")
            
        Returns:
            Dict with season averages or None on error
        """
        try:
            # Check cache first
            if self.redis_service and self.redis_service.is_connected():
                cache_key = f"{self.historical_cache_prefix}:season:{nba_person_id}:{season}"
                cached_data = self.redis_service.get_json(cache_key)
                if cached_data:
                    logger.info(f"Retrieved season averages from cache for player {nba_person_id}, season {season}")
                    return cached_data
            
            logger.info(f"Fetching season averages for NBA player {nba_person_id}, season {season}")
            
            # Fetch career stats (includes all seasons)
            career_stats = await self.fetch_player_career_stats(nba_person_id)
            
            if not career_stats or not career_stats.get("regular_season"):
                return None
            
            # Filter to specific season
            result = None
            for season_stats in career_stats["regular_season"]:
                if season_stats.get("season") == season:
                    logger.info(f"Found season averages for player {nba_person_id}, season {season}")
                    result = {
                        "ppg": season_stats.get("ppg", 0),
                        "rpg": season_stats.get("rpg", 0),
                        "apg": season_stats.get("apg", 0),
                        "spg": season_stats.get("spg", 0),
                        "bpg": season_stats.get("bpg", 0),
                        "tov": season_stats.get("tov", 0),
                        "fg_pct": season_stats.get("fg_pct", 0),
                        "ft_pct": season_stats.get("ft_pct", 0),
                        "fg3_pct": season_stats.get("fg3_pct", 0)
                    }
                    break
            
            if not result:
                logger.warning(f"Season {season} not found for player {nba_person_id}")
                return None
            
            # Cache the result with dynamic TTL based on season
            if self.redis_service and self.redis_service.is_connected():
                cache_ttl = self._get_stats_cache_ttl(season)
                cache_key = f"{self.historical_cache_prefix}:season:{nba_person_id}:{season}"
                self.redis_service.set_json(cache_key, result, cache_ttl)
                logger.info(f"Cached season averages for player {nba_person_id}, season {season} with {cache_ttl}s TTL")
            
            return result
            
        except Exception as e:
            logger.error(f"Error fetching season averages for player {nba_person_id}: {e}")
            return None
    
    async def fetch_player_stats_by_date_range(
        self, 
        nba_person_id: int, 
        start_date: str, 
        end_date: str
    ) -> Optional[List[Dict]]:
        """
        Fetch player stats filtered by date range.
        
        Args:
            nba_person_id: NBA person ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of games and computed averages or None on error
        """
        try:
            # Check cache first
            if self.redis_service and self.redis_service.is_connected():
                cache_key = f"{self.historical_cache_prefix}:daterange:{nba_person_id}:{start_date}:{end_date}"
                cached_data = self.redis_service.get_json(cache_key)
                if cached_data:
                    logger.info(f"Retrieved date range stats from cache for player {nba_person_id}")
                    return cached_data
            
            logger.info(f"Fetching stats by date range for player {nba_person_id}: {start_date} to {end_date}")
            
            # Determine season from start_date
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            season_year = start_dt.year if start_dt.month >= 10 else start_dt.year - 1
            season = f"{season_year}-{str(season_year + 1)[-2:]}"
            
            # Fetch full game log for season
            game_log = await self.fetch_player_game_log(nba_person_id, season)
            
            if not game_log:
                return None
            
            # Filter games by date range
            filtered_games = []
            for game in game_log:
                game_date_str = game.get("game_date", "")
                if game_date_str:
                    try:
                        game_dt = datetime.strptime(game_date_str, "%Y-%m-%d")
                        if start_dt <= game_dt <= datetime.strptime(end_date, "%Y-%m-%d"):
                            filtered_games.append(game)
                    except:
                        continue
            
            if not filtered_games:
                logger.warning(f"No games found in date range for player {nba_person_id}")
                return None
            
            # Calculate averages
            averages = self._calculate_date_range_averages(filtered_games)
            result = {
                "games": filtered_games,
                "averages": averages,
                "game_count": len(filtered_games)
            }
            
            # Cache the result with dynamic TTL based on season
            if self.redis_service and self.redis_service.is_connected():
                cache_ttl = self._get_stats_cache_ttl(season)
                cache_key = f"{self.historical_cache_prefix}:daterange:{nba_person_id}:{start_date}:{end_date}"
                self.redis_service.set_json(cache_key, result, cache_ttl)
                logger.info(f"Cached date range stats for player {nba_person_id} with {cache_ttl}s TTL")
            
            logger.info(f"Found {len(filtered_games)} games in date range for player {nba_person_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching date range stats for player {nba_person_id}: {e}")
            return None
    
    async def search_player_by_name(self, player_name: str) -> Optional[int]:
        """
        Search for player by name and return NBA person ID.
        
        Args:
            player_name: Player full name
            
        Returns:
            NBA person ID or None if not found
        """
        try:
            logger.info(f"Searching for player: {player_name}")
            
            # Lazy import nba_api
            try:
                from nba_api.stats.static import players as nba_players
            except ImportError as ie:
                logger.error(f"nba_api not installed: {ie}")
                return None
            
            # Search using nba_api - run in thread pool
            matches = await asyncio.to_thread(
                nba_players.find_players_by_full_name,
                player_name
            )
            
            if not matches:
                logger.warning(f"No matches found for player: {player_name}")
                return None
            
            # Prefer active players
            for match in matches:
                if match.get("is_active", False):
                    player_id = match.get("id")
                    logger.info(f"Found active player {player_name} with ID {player_id}")
                    return player_id
            
            # Fall back to first match if no active players
            player_id = matches[0].get("id")
            logger.info(f"Found player {player_name} with ID {player_id} (inactive)")
            return player_id
            
        except Exception as e:
            logger.error(f"Error searching for player {player_name}: {e}")
            return None
    
    # Helper Methods for Data Transformation
    
    def _transform_career_stats(self, raw_data: Dict) -> Dict:
        """Transform nba_api career stats to internal format."""
        try:
            result = {
                "regular_season": [],
                "playoffs": []
            }
            
            # Transform regular season
            for season_data in raw_data.get("regular_season", []):
                result["regular_season"].append({
                    "season": season_data.get("SEASON_ID", ""),
                    "team": season_data.get("TEAM_ABBREVIATION", ""),
                    "games": season_data.get("GP", 0),
                    "ppg": season_data.get("PTS", 0),
                    "rpg": season_data.get("REB", 0),
                    "apg": season_data.get("AST", 0),
                    "spg": season_data.get("STL", 0),
                    "bpg": season_data.get("BLK", 0),
                    "tov": season_data.get("TOV", 0),
                    "fg_pct": season_data.get("FG_PCT", 0),
                    "ft_pct": season_data.get("FT_PCT", 0),
                    "fg3_pct": season_data.get("FG3_PCT", 0),
                    # Shooting stats (per game since we use per_mode36="PerGame")
                    "fgm": season_data.get("FGM", 0),
                    "fga": season_data.get("FGA", 0),
                    "ftm": season_data.get("FTM", 0),
                    "fta": season_data.get("FTA", 0),
                    "fg3m": season_data.get("FG3M", 0),
                    "fg3a": season_data.get("FG3A", 0),
                    "dreb": season_data.get("DREB", 0),
                    "oreb": season_data.get("OREB", 0),
                    "pf": season_data.get("PF", 0)
                })
            
            # Transform playoffs
            for season_data in raw_data.get("playoffs", []):
                result["playoffs"].append({
                    "season": season_data.get("SEASON_ID", ""),
                    "team": season_data.get("TEAM_ABBREVIATION", ""),
                    "games": season_data.get("GP", 0),
                    "ppg": season_data.get("PTS", 0),
                    "rpg": season_data.get("REB", 0),
                    "apg": season_data.get("AST", 0),
                    "spg": season_data.get("STL", 0),
                    "bpg": season_data.get("BLK", 0),
                    "tov": season_data.get("TOV", 0),
                    "fg_pct": season_data.get("FG_PCT", 0),
                    "ft_pct": season_data.get("FT_PCT", 0),
                    "fg3_pct": season_data.get("FG3_PCT", 0),
                    # Shooting stats (per game since we use per_mode36="PerGame")
                    "fgm": season_data.get("FGM", 0),
                    "fga": season_data.get("FGA", 0),
                    "ftm": season_data.get("FTM", 0),
                    "fta": season_data.get("FTA", 0),
                    "fg3m": season_data.get("FG3M", 0),
                    "fg3a": season_data.get("FG3A", 0),
                    "dreb": season_data.get("DREB", 0),
                    "oreb": season_data.get("OREB", 0),
                    "pf": season_data.get("PF", 0)
                })
            
            return result
            
        except Exception as e:
            logger.error(f"Error transforming career stats: {e}")
            return {"regular_season": [], "playoffs": []}
    
    def _transform_game_log(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform game log to internal format."""
        try:
            result = []
            for game in raw_data:
                result.append({
                    "game_date": game.get("GAME_DATE", ""),
                    "matchup": game.get("MATCHUP", ""),
                    "wl": game.get("WL", ""),
                    "minutes": game.get("MIN", ""),
                    "points": game.get("PTS", 0),
                    "rebounds": game.get("REB", 0),
                    "assists": game.get("AST", 0),
                    "steals": game.get("STL", 0),
                    "blocks": game.get("BLK", 0),
                    "turnovers": game.get("TOV", 0),
                    "fg_pct": game.get("FG_PCT", 0),
                    "ft_pct": game.get("FT_PCT", 0),
                    "fg3_pct": game.get("FG3_PCT", 0)
                })
            return result
            
        except Exception as e:
            logger.error(f"Error transforming game log: {e}")
            return []
    
    def _calculate_date_range_averages(self, games: List[Dict]) -> Dict:
        """Calculate averages from game list, including shooting percentages."""
        try:
            if not games:
                return {}
            
            totals = {
                "points": 0,
                "rebounds": 0,
                "assists": 0,
                "steals": 0,
                "blocks": 0,
                "turnovers": 0,
                # Shooting stats for percentage calculations
                "fgm": 0,  # Field goals made
                "fga": 0,  # Field goals attempted
                "fg3m": 0, # Three-pointers made
                "fg3a": 0, # Three-pointers attempted
                "ftm": 0,  # Free throws made
                "fta": 0   # Free throws attempted
            }
            
            for game in games:
                totals["points"] += game.get("points", 0)
                totals["rebounds"] += game.get("rebounds", 0)
                totals["assists"] += game.get("assists", 0)
                totals["steals"] += game.get("steals", 0)
                totals["blocks"] += game.get("blocks", 0)
                totals["turnovers"] += game.get("turnovers", 0)
                
                # Accumulate shooting stats
                totals["fgm"] += game.get("fgm", 0)
                totals["fga"] += game.get("fga", 0)
                totals["fg3m"] += game.get("fg3m", 0)
                totals["fg3a"] += game.get("fg3a", 0)
                totals["ftm"] += game.get("ftm", 0)
                totals["fta"] += game.get("fta", 0)
            
            game_count = len(games)
            averages = {
                "ppg": round(totals["points"] / game_count, 1),
                "rpg": round(totals["rebounds"] / game_count, 1),
                "apg": round(totals["assists"] / game_count, 1),
                "spg": round(totals["steals"] / game_count, 1),
                "bpg": round(totals["blocks"] / game_count, 1),
                "tov": round(totals["turnovers"] / game_count, 1)
            }
            
            # Calculate shooting percentages (weighted by total attempts across all games)
            if totals["fga"] > 0:
                averages["fg_pct"] = round((totals["fgm"] / totals["fga"]) * 100, 1)
            else:
                averages["fg_pct"] = 0.0
                
            if totals["fg3a"] > 0:
                averages["fg3_pct"] = round((totals["fg3m"] / totals["fg3a"]) * 100, 1)
            else:
                averages["fg3_pct"] = 0.0
                
            if totals["fta"] > 0:
                averages["ft_pct"] = round((totals["ftm"] / totals["fta"]) * 100, 1)
            else:
                averages["ft_pct"] = 0.0
            
            return averages
            
        except Exception as e:
            logger.error(f"Error calculating averages: {e}")
            return {}
