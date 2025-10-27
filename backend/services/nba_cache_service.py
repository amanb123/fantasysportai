"""
NBA cache service for managing NBA data caching.
"""

import logging
from typing import Optional, Dict, List, Tuple, Any
from datetime import date, datetime, timezone

from backend.config import settings
from backend.services.redis_service import RedisService
from backend.services.nba_stats_service import NBAStatsService
from backend.session.repository import BasketballRepository

logger = logging.getLogger(__name__)


class NBACacheService:
    """Service for managing NBA data caching with Redis."""
    
    def __init__(self, redis_service: RedisService, nba_stats_service: NBAStatsService, repository: BasketballRepository):
        """Initialize cache service with dependencies."""
        self.redis_service = redis_service
        self.nba_stats_service = nba_stats_service
        self.repository = repository
        
        # Load cache configuration
        self.schedule_ttl = settings.NBA_SCHEDULE_CACHE_TTL
        self.player_info_ttl = settings.NBA_PLAYER_INFO_CACHE_TTL
        self.schedule_cache_key = settings.NBA_SCHEDULE_CACHE_KEY
        self.player_info_key_prefix = settings.NBA_PLAYER_INFO_CACHE_KEY_PREFIX
    
    async def fetch_and_cache_schedule(self, season: Optional[str] = None) -> Optional[List[Dict]]:
        """
        Fetch season schedule and cache in Redis + database.
        
        Args:
            season: Season year (e.g., "2024"). If not provided, uses current season from config.
        
        Returns:
            List[Dict]: List of game dicts or None on error
        """
        try:
            use_season = season or settings.NBA_CURRENT_SEASON
            logger.info(f"Fetching and caching NBA schedule for season {use_season}")
            
            # Fetch schedule from NBA CDN using injected service
            async with self.nba_stats_service as nba_service:
                games = await nba_service.fetch_season_schedule(use_season)
            
            if games is None:
                logger.error("Failed to fetch schedule from NBA CDN")
                # Don't abort - still try to query from database
                return None
            
            # Store in Redis if available
            if self.redis_service.is_connected():
                success = self.redis_service.set_json(self.schedule_cache_key, games, self.schedule_ttl)
                if not success:
                    logger.warning("Failed to cache schedule in Redis, continuing with DB upsert")
            else:
                logger.warning("Redis unavailable, skipping cache, proceeding to DB")
            
            # Bulk upsert to database (always do this regardless of Redis)
            games_synced = self.repository.bulk_upsert_game_schedules(games)
            
            logger.info(f"Successfully cached {games_synced} games for season {use_season}")
            return games
            
        except Exception as e:
            error_msg = f"Error caching schedule: {e}"
            logger.error(error_msg)
            return None
    
    async def get_cached_schedule(self, start_date: Optional[str] = None, end_date: Optional[str] = None, season: Optional[str] = None) -> List[Dict]:
        """
        Get cached schedule with optional date filters.
        
        Args:
            start_date: Optional start date filter (YYYY-MM-DD string)
            end_date: Optional end date filter (YYYY-MM-DD string)
            season: Optional season filter (e.g., "2024")
            
        Returns:
            List[Dict]: List of game dicts
        """
        try:
            # Try Redis cache first
            cached_games = self.redis_service.get_json(self.schedule_cache_key)
            
            if cached_games:
                logger.info(f"Schedule cache hit: {len(cached_games)} games")
                # Apply filters if provided
                filtered_games = cached_games
                
                if start_date or end_date or season:
                    filtered_games = []
                    for game in cached_games:
                        game_date_str = game.get("game_date")
                        game_season = game.get("season")
                        
                        # Apply season filter
                        if season and game_season != season:
                            continue
                        
                        # Apply date filters
                        if game_date_str and (start_date or end_date):
                            if start_date and game_date_str < start_date:
                                continue
                            if end_date and game_date_str > end_date:
                                continue
                        
                        filtered_games.append(game)
                
                return filtered_games
            
            # Cache miss - query database
            logger.info("Schedule cache miss - querying database")
            
            # Guard against None dates when falling back to DB
            # Only query if we have both start and end dates, or neither
            if (start_date is not None and end_date is not None) or (start_date is None and end_date is None):
                games = self.repository.get_games_by_date_range(start_date, end_date, season)
                
                # Convert models to dicts if needed
                if games and isinstance(games[0], dict):
                    return games
                elif games:
                    return [game.to_pydantic() if hasattr(game, 'to_pydantic') else game for game in games]
            else:
                logger.warning(f"Incomplete date range provided: start_date={start_date}, end_date={end_date}. Returning empty list.")
            
            return []
            
        except Exception as e:
            logger.error(f"Error retrieving cached schedule: {e}")
            return []
    
    async def get_todays_games(self) -> Optional[List[Dict]]:
        """
        Get today's games with live scores.
        
        Returns:
            List[Dict]: Today's games or None
        """
        try:
            logger.info("Fetching today's games")
            
            # Fetch from NBA CDN scoreboard using injected service
            async with self.nba_stats_service as nba_service:
                games = await nba_service.fetch_todays_scoreboard()
            
            if games is None:
                return None
            
            # Update database with live scores/status
            for game in games:
                try:
                    self.repository.upsert_game_schedule(game)
                except Exception as e:
                    logger.warning(f"Failed to update game {game.get('game_id')}: {e}")
            
            return games
            
        except Exception as e:
            logger.error(f"Error fetching today's games: {e}")
            return None
    
    async def fetch_and_cache_player_info(self, sleeper_player_id: str, sleeper_player_data: Dict) -> Optional[Dict]:
        """
        Fetch and cache single player info.
        
        Args:
            sleeper_player_id: Sleeper player ID
            sleeper_player_data: Sleeper player data
            
        Returns:
            Dict: Merged player data or None on error
        """
        try:
            logger.info(f"Fetching player info for {sleeper_player_id}")
            
            # Extract NBA person ID using injected service
            async with self.nba_stats_service as nba_service:
                nba_person_id = nba_service.match_sleeper_to_nba_id(sleeper_player_data)
            
            if not nba_person_id:
                logger.debug(f"No NBA ID found for player {sleeper_player_id}")
                return None
            
            # Fetch player info from NBA API using injected service
            async with self.nba_stats_service as nba_service:
                nba_data = await nba_service.fetch_player_info(nba_person_id)
            
            if not nba_data:
                logger.warning(f"Failed to fetch NBA data for player {sleeper_player_id}")
                return None
            
            # Merge with Sleeper data
            merged_data = self._merge_player_data(nba_data, sleeper_player_data)
            merged_data["sleeper_player_id"] = sleeper_player_id
            
            # Upsert to database
            self.repository.upsert_player_info(merged_data)
            
            # Get response-shaped data from repository (via to_pydantic())
            response_shaped_data = self.repository.get_player_info_by_sleeper_id(sleeper_player_id)
            
            # Store response-shaped data in Redis if available
            if response_shaped_data and self.redis_service.is_connected():
                cache_key = f"{self.player_info_key_prefix}:{sleeper_player_id}"
                self.redis_service.set_json(cache_key, response_shaped_data, self.player_info_ttl)
            
            logger.info(f"Successfully cached player info for {sleeper_player_id}")
            return response_shaped_data
            
        except Exception as e:
            logger.error(f"Error caching player info for {sleeper_player_id}: {e}")
            return None
    
    async def fetch_and_cache_players_batch(self, sleeper_player_ids: List[str], player_cache_service) -> List[Dict]:
        """
        Fetch and cache multiple players.
        
        Args:
            sleeper_player_ids: List of Sleeper player IDs
            player_cache_service: PlayerCacheService instance to fetch Sleeper data
            
        Returns:
            List[Dict]: List of successfully synced player data
        """
        synced_players = []
        total_count = len(sleeper_player_ids)
        
        logger.info(f"Batch processing {total_count} players")
        
        for player_id in sleeper_player_ids:
            try:
                # Get Sleeper player data
                sleeper_data = None
                if player_cache_service:
                    sleeper_data = player_cache_service.get_player_by_id(player_id)
                
                # Fetch and cache
                player_info = await self.fetch_and_cache_player_info(player_id, sleeper_data or {})
                
                if player_info:
                    synced_players.append(player_info)
                    
                # Log progress every 50 players
                if len(synced_players) % 50 == 0:
                    logger.info(f"Processed {len(synced_players)}/{total_count} players")
                    
            except Exception as e:
                logger.error(f"Error syncing player {player_id}: {e}")
                continue
        
        logger.info(f"Batch complete: {len(synced_players)}/{total_count} players synced")
        return synced_players
    
    async def get_cached_player_info(self, sleeper_player_id: str, player_cache_service=None) -> Optional[Dict]:
        """
        Get cached player info with automatic fetch if not cached.
        
        Args:
            sleeper_player_id: Sleeper player ID
            player_cache_service: Optional PlayerCacheService to fetch Sleeper data if needed
            
        Returns:
            Dict: Player info or None
        """
        try:
            # Try Redis cache first
            cache_key = f"{self.player_info_key_prefix}:{sleeper_player_id}"
            cached_data = self.redis_service.get_json(cache_key)
            
            if cached_data:
                logger.debug(f"Player info cache hit for {sleeper_player_id}")
                return cached_data
            
            # Cache miss - query database
            logger.debug(f"Player info cache miss for {sleeper_player_id}, checking database")
            player_model = self.repository.get_player_info_by_sleeper_id(sleeper_player_id)
            
            if player_model:
                # Cache it in Redis
                self.redis_service.set_json(cache_key, player_model, self.player_info_ttl)
                return player_model
            
            # Not in cache or database - try fetching
            logger.debug(f"Player not in cache or database, attempting fetch for {sleeper_player_id}")
            if player_cache_service:
                sleeper_data = player_cache_service.get_player_by_id(sleeper_player_id)
                if sleeper_data:
                    return await self.fetch_and_cache_player_info(sleeper_player_id, sleeper_data)
            
            return None
            
        except Exception as e:
            logger.error(f"Error retrieving player info for {sleeper_player_id}: {e}")
            return None
    
    async def invalidate_schedule_cache(self) -> bool:
        """
        Delete schedule cache from Redis.
        
        Returns:
            bool: Success status
        """
        try:
            if not self.redis_service.is_connected():
                return False
            
            self.redis_service.delete(self.schedule_cache_key)
            logger.info("Schedule cache invalidated")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating schedule cache: {e}")
            return False
    
    async def invalidate_player_info_cache(self, player_id: Optional[str] = None) -> bool:
        """
        Delete player info cache.
        
        Args:
            player_id: Specific player ID or None for all
            
        Returns:
            bool: Success status
        """
        try:
            if not self.redis_service.is_connected():
                return False
            
            if player_id:
                # Delete specific player
                cache_key = f"{self.player_info_key_prefix}:{player_id}"
                self.redis_service.delete(cache_key)
                logger.info(f"Player info cache invalidated for {player_id}")
            else:
                # Delete all player info caches using pattern
                pattern = f"{self.player_info_key_prefix}:*"
                deleted = self.redis_service.delete_by_pattern(pattern)
                logger.info(f"Invalidated {deleted} player info caches")
            
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating player info cache: {e}")
            return False
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Dict: Cache stats
        """
        try:
            if not self.redis_service.is_connected():
                return {
                    "schedule_cached": False,
                    "schedule_games_count": 0,
                    "player_info_cached": False,
                    "player_info_count": 0,
                    "redis_connected": False
                }
            
            stats = {"redis_connected": True}
            
            # Check schedule cache
            schedule_key = self.schedule_cache_key
            stats['schedule_cached'] = self.redis_service.exists(schedule_key)
            stats['schedule_ttl'] = self.redis_service.get_ttl(schedule_key) if stats['schedule_cached'] else None
            
            # Get schedule game count
            if stats['schedule_cached']:
                cached_schedule = self.redis_service.get_json(schedule_key)
                stats['schedule_games_count'] = len(cached_schedule) if cached_schedule else 0
            else:
                stats['schedule_games_count'] = 0
            
            # Count player info in database
            with self.repository.get_session() as session:
                from backend.session.models import PlayerInfoModel
                player_count = session.query(PlayerInfoModel).count()
                stats['player_info_count'] = player_count
                stats['player_info_cached'] = player_count > 0
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "schedule_cached": False,
                "player_info_cached_count": 0,
                "redis_connected": False,
                "error": str(e)
            }
    
    def _merge_player_data(self, nba_data: Dict, sleeper_data: Dict) -> Dict:
        """
        Merge NBA API data with Sleeper data (outputs PlayerInfoModel compatible dict).
        
        Args:
            nba_data: Data from NBA API (already transformed to model format)
            sleeper_data: Data from Sleeper
            
        Returns:
            Dict: Merged data matching PlayerInfoModel fields
        """
        # Start with NBA data as base
        merged = nba_data.copy()
        
        # Ensure full_name is set (required field)
        if not merged.get("full_name"):
            # Try Sleeper name formats
            sleeper_name = sleeper_data.get("name") or sleeper_data.get("full_name")
            if sleeper_name:
                merged["full_name"] = sleeper_name
            else:
                # Fall back to first/last
                merged["full_name"] = f"{merged.get('first_name', '')} {merged.get('last_name', '')}".strip()
        
        # Override with Sleeper data for specific fields
        if sleeper_data.get("injury_status"):
            merged["injury_status"] = sleeper_data["injury_status"]
        
        if sleeper_data.get("injury_body_part") or sleeper_data.get("injury_notes"):
            merged["injury_description"] = f"{sleeper_data.get('injury_body_part', '')} {sleeper_data.get('injury_notes', '')}".strip()
        
        # Prefer Sleeper team info if available (more current)
        if sleeper_data.get("team"):
            merged["nba_team_name"] = sleeper_data["team"]
        
        return merged
