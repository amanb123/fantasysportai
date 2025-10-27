"""
NBA Schedule Cache Service

Fetches and caches the full NBA season schedule.
The schedule is static once released, so we cache it for the entire season.
"""

import logging
from typing import List, Dict, Optional
from datetime import datetime, timedelta, date
import json
import httpx

from backend.services.redis_service import RedisService
from backend.config import settings

logger = logging.getLogger(__name__)


class NBAScheduleCacheService:
    """Service for caching NBA season schedule."""
    
    # Cache key for full season schedule
    SCHEDULE_CACHE_KEY = "nba:schedule:2025-26"
    
    # Cache for 90 days (schedule is static once released)
    SCHEDULE_TTL = 90 * 24 * 60 * 60  # 90 days in seconds
    
    def __init__(self, redis_service: RedisService, nba_mcp_service=None):
        """
        Initialize schedule cache service.
        
        Args:
            redis_service: Redis service for caching
            nba_mcp_service: NBA MCP service for fetching schedule
        """
        logger.info(f"Initializing NBAScheduleCacheService with redis={redis_service}, nba_mcp={nba_mcp_service}")
        self.redis = redis_service
        self.nba_mcp = nba_mcp_service
        self._memory_cache = None
    
    async def get_full_season_schedule(self) -> List[Dict]:
        """
        Get the full 2025-26 NBA regular season schedule.
        Uses triple caching: memory -> Redis -> API fetch
        
        Returns:
            List of game dictionaries for the entire season
        """
        logger.info(f"get_full_season_schedule called. redis={self.redis is not None}, nba_mcp={self.nba_mcp is not None}")
        
        # Check memory cache first
        if self._memory_cache is not None:
            logger.info(f"Returning {len(self._memory_cache)} games from memory cache")
            return self._memory_cache
        
        try:
            # Check Redis cache
            if self.redis is None:
                logger.warning("Redis service is None! Cannot use Redis caching - fetching directly")
                games = await self._fetch_full_schedule()
                self._memory_cache = games
                return games
                
            cached_data = self.redis.get(self.SCHEDULE_CACHE_KEY)  # Sync call, not await
            if cached_data:
                games = json.loads(cached_data)
                logger.info(f"Loaded {len(games)} games from Redis cache")
                self._memory_cache = games
                return games
            
            # Cache miss - fetch from API
            logger.info("Cache miss - fetching full season schedule from NBA API")
            games = await self._fetch_full_schedule()
            
            # Cache in Redis
            if games:
                self.redis.set(  # Sync call, not await
                    self.SCHEDULE_CACHE_KEY,
                    json.dumps(games),
                    ttl=self.SCHEDULE_TTL
                )
                logger.info(f"Cached {len(games)} games for 2025-26 season")
            
            # Cache in memory
            self._memory_cache = games
            return games
            
        except Exception as e:
            logger.error(f"Error getting season schedule: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def _fetch_full_schedule(self) -> List[Dict]:
        """
        Fetch the full NBA season schedule from NBA CDN.
        This includes all future games for the current season.
        
        Returns:
            List of game dictionaries
        """
        try:
            logger.info("Fetching full season schedule from NBA CDN")
            
            # Use NBA CDN to get the full season schedule (includes future games)
            async with httpx.AsyncClient(
                base_url=settings.NBA_CDN_BASE_URL,
                timeout=settings.NBA_CDN_TIMEOUT,
                headers={"User-Agent": "Fantasy Basketball League App"}
            ) as client:
                response = await client.get("staticData/scheduleLeagueV2_1.json")
                
                if response.status_code != 200:
                    logger.error(f"NBA CDN returned status {response.status_code}")
                    return []
                
                data = response.json()
                
                # Extract games from the schedule
                games = []
                league_schedule = data.get("leagueSchedule", {})
                game_dates = league_schedule.get("gameDates", [])
                
                for game_date_entry in game_dates:
                    game_date_str = game_date_entry.get("gameDate", "")
                    for game in game_date_entry.get("games", []):
                        # Transform to our format
                        transformed_game = {
                            'game_id': game.get('gameId', ''),
                            'game_date': game_date_str,
                            'home_team': game.get('homeTeam', {}).get('teamName', ''),
                            'home_team_tricode': game.get('homeTeam', {}).get('teamTricode', ''),
                            'away_team': game.get('awayTeam', {}).get('teamName', ''),
                            'away_team_tricode': game.get('awayTeam', {}).get('teamTricode', ''),
                            'game_status': game.get('gameStatusText', 'Scheduled'),
                            'arena_name': game.get('arenaName', ''),
                            'home_team_score': game.get('homeTeam', {}).get('score', 0),
                            'away_team_score': game.get('awayTeam', {}).get('score', 0),
                        }
                        games.append(transformed_game)
                
                logger.info(f"Successfully fetched {len(games)} games from NBA CDN")
                return games
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching NBA schedule from CDN")
            return []
        except httpx.RequestError as e:
            logger.error(f"Request error fetching NBA schedule: {e}")
            return []
        except Exception as e:
            logger.error(f"Error fetching full schedule from NBA CDN: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    async def get_games_for_date_range(
        self,
        start_date: date,
        end_date: date,
        team_tricodes: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get games for a specific date range from the cached schedule.
        
        Args:
            start_date: Start date
            end_date: End date
            team_tricodes: Optional list of team abbreviations to filter by
            
        Returns:
            List of games in the date range
        """
        try:
            full_schedule = await self.get_full_season_schedule()
            
            if not full_schedule:
                logger.warning("Full schedule is empty!")
                return []
            
            # Debug: log first game to see structure
            if full_schedule and len(full_schedule) > 0:
                logger.info(f"Sample game structure: {full_schedule[0]}")
            
            filtered_games = []
            for game in full_schedule:
                # Parse game date
                game_date_str = game.get('GAME_DATE_EST', game.get('game_date', ''))
                if not game_date_str:
                    logger.debug(f"Game missing date: {game}")
                    continue
                
                try:
                    # Handle different date formats
                    if 'T' in game_date_str:
                        # ISO format: YYYY-MM-DDTHH:MM:SS
                        game_date = datetime.fromisoformat(game_date_str.replace('Z', '+00:00')).date()
                    elif '/' in game_date_str:
                        # MM/DD/YYYY format (from NBA CDN)
                        game_date = datetime.strptime(game_date_str.split()[0], '%m/%d/%Y').date()
                    else:
                        # YYYY-MM-DD format
                        game_date = datetime.strptime(game_date_str[:10], '%Y-%m-%d').date()
                except Exception as e:
                    logger.debug(f"Failed to parse date '{game_date_str}': {e}")
                    continue
                
                # Check date range
                if not (start_date <= game_date <= end_date):
                    continue
                
                # Check team filter
                if team_tricodes:
                    home_team = game.get('HOME_TEAM_ABBREVIATION', game.get('home_team_tricode', ''))
                    away_team = game.get('VISITOR_TEAM_ABBREVIATION', game.get('away_team_tricode', ''))
                    
                    if home_team not in team_tricodes and away_team not in team_tricodes:
                        continue
                
                filtered_games.append(game)
            
            logger.info(f"Found {len(filtered_games)} games from {start_date} to {end_date}")
            return filtered_games
            
        except Exception as e:
            logger.error(f"Error filtering games by date range: {e}")
            return []
    
    async def invalidate_cache(self):
        """Invalidate the schedule cache (useful if schedule changes)."""
        try:
            await self.redis.delete(self.SCHEDULE_CACHE_KEY)
            self._memory_cache = None
            logger.info("Schedule cache invalidated")
        except Exception as e:
            logger.error(f"Error invalidating schedule cache: {e}")


# Singleton instance
_schedule_cache_service: Optional[NBAScheduleCacheService] = None


def get_schedule_cache_service(
    redis_service: RedisService = None,
    nba_mcp_service = None
) -> Optional[NBAScheduleCacheService]:
    """
    Get or create the schedule cache service singleton.
    
    Args:
        redis_service: Redis service (required for first call)
        nba_mcp_service: NBA MCP service (required for first call)
        
    Returns:
        Schedule cache service instance or None if disabled
    """
    global _schedule_cache_service
    
    if _schedule_cache_service is None:
        if redis_service and nba_mcp_service:
            logger.info(f"Creating new NBAScheduleCacheService singleton")
            _schedule_cache_service = NBAScheduleCacheService(redis_service, nba_mcp_service)
    
    return _schedule_cache_service
