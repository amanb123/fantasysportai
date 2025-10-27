"""
Player cache service for managing Sleeper player data caching.
"""

import logging
from typing import Optional, Dict, Tuple
from datetime import datetime, timezone

from backend.config import settings
from backend.services.redis_service import RedisService
from backend.services.sleeper_service import SleeperService

logger = logging.getLogger(__name__)


class PlayerCacheService:
    """Service for managing Sleeper player data caching with Redis."""
    
    def __init__(self, redis_service: RedisService, sleeper_service: SleeperService):
        """Initialize cache service with dependencies."""
        self.redis_service = redis_service
        self.sleeper_service = sleeper_service
        self.cache_key = settings.SLEEPER_PLAYERS_CACHE_KEY
        self.cache_ttl = settings.SLEEPER_PLAYERS_CACHE_TTL
    
    async def fetch_and_cache_players(self) -> Tuple[bool, Optional[str]]:
        """
        Fetch all NBA players from Sleeper API and cache them.
        
        Returns:
            Tuple: (success: bool, error_message: Optional[str])
        """
        try:
            logger.info("Starting NBA player fetch from Sleeper API")
            
            # Check Redis connection
            if not self.redis_service.is_connected():
                return False, "Redis connection unavailable"
            
            # Fetch players from Sleeper API
            async with self.sleeper_service as sleeper:
                raw_players = await sleeper.get_nba_players()
            
            if raw_players is None:
                return False, "Failed to fetch players from Sleeper API"
            
            # Transform to simplified format
            simplified_players = self._transform_players(raw_players)
            
            # Store in Redis with TTL
            success = self.redis_service.set_json(
                self.cache_key, 
                simplified_players, 
                self.cache_ttl
            )
            
            if not success:
                return False, "Failed to cache players in Redis"
            
            player_count = len(simplified_players)
            expiry_time = datetime.now(timezone.utc).isoformat()
            
            logger.info(f"Successfully cached {player_count} NBA players")
            logger.info(f"Cache expires in {self.cache_ttl} seconds ({self.cache_ttl/3600:.1f} hours)")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error fetching and caching players: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_cached_players(self) -> Optional[Dict[str, Dict]]:
        """
        Retrieve players from Redis cache.
        
        Returns:
            Dict: Cached player data or None if cache miss/error
        """
        try:
            if not self.redis_service.is_connected():
                logger.warning("Redis connection unavailable for player cache retrieval")
                return None
            
            cached_data = self.redis_service.get_json(self.cache_key)
            
            if cached_data is None:
                logger.info("Player cache miss")
                return None
            
            player_count = len(cached_data)
            ttl_remaining = self.redis_service.get_ttl(self.cache_key)
            
            logger.info(f"Player cache hit: {player_count} players, TTL: {ttl_remaining}s")
            return cached_data
            
        except Exception as e:
            logger.error(f"Error retrieving cached players: {e}")
            return None
    
    def get_player_by_id(self, player_id: str) -> Optional[Dict]:
        """
        Get single player from cache.
        
        Args:
            player_id: Sleeper player ID
            
        Returns:
            Dict: Player data or None if not found
        """
        try:
            cached_players = self.get_cached_players()
            if cached_players is None:
                return None
            
            return cached_players.get(player_id)
            
        except Exception as e:
            logger.error(f"Error retrieving player {player_id} from cache: {e}")
            return None
    
    def get_players_bulk(self, player_ids: list) -> Dict[str, Dict]:
        """
        Get multiple players from cache by their IDs.
        
        Args:
            player_ids: List of Sleeper player IDs
            
        Returns:
            Dict: Mapping of player_id -> player data
        """
        try:
            cached_players = self.get_cached_players()
            if cached_players is None:
                return {}
            
            # Return only the players that match the requested IDs
            return {
                player_id: cached_players[player_id]
                for player_id in player_ids
                if player_id in cached_players
            }
            
        except Exception as e:
            logger.error(f"Error retrieving players bulk from cache: {e}")
            return {}
    
    def is_cache_valid(self) -> bool:
        """
        Check if cache exists and has not expired.
        
        Returns:
            bool: True if cache is fresh
        """
        try:
            if not self.redis_service.is_connected():
                return False
            
            exists = self.redis_service.exists(self.cache_key)
            if not exists:
                return False
            
            ttl = self.redis_service.get_ttl(self.cache_key)
            # TTL returns -1 if no expiry, -2 if key doesn't exist, >0 if has remaining time
            return ttl > 0 or ttl == -1
            
        except Exception as e:
            logger.error(f"Error checking cache validity: {e}")
            return False
    
    def invalidate_cache(self) -> bool:
        """
        Delete cached player data.
        
        Returns:
            bool: True if successful
        """
        try:
            if not self.redis_service.is_connected():
                logger.warning("Redis connection unavailable for cache invalidation")
                return False
            
            success = self.redis_service.delete(self.cache_key)
            if success:
                logger.info("Player cache invalidated successfully")
            else:
                logger.warning("Failed to invalidate player cache")
            
            return success
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return False
    
    def get_cache_stats(self) -> Dict[str, any]:
        """
        Get cache metadata and statistics.
        
        Returns:
            Dict: Cache status information
        """
        try:
            if not self.redis_service.is_connected():
                return {
                    "exists": False,
                    "ttl_remaining": 0,
                    "player_count": 0,
                    "last_updated": None,
                    "is_valid": False,
                    "redis_connected": False
                }
            
            exists = self.redis_service.exists(self.cache_key)
            ttl_remaining = self.redis_service.get_ttl(self.cache_key) if exists else 0
            
            player_count = 0
            if exists:
                cached_data = self.redis_service.get_json(self.cache_key)
                if cached_data:
                    player_count = len(cached_data)
            
            is_valid = exists and (ttl_remaining > 0 or ttl_remaining == -1)
            
            # Calculate last_updated from TTL
            last_updated = None
            if exists and ttl_remaining > 0:
                seconds_since_cache = self.cache_ttl - ttl_remaining
                last_updated = (datetime.now(timezone.utc).timestamp() - seconds_since_cache)
                last_updated = datetime.fromtimestamp(last_updated, timezone.utc).isoformat()
            
            return {
                "exists": exists,
                "ttl_remaining": ttl_remaining,
                "player_count": player_count,
                "last_updated": last_updated,
                "is_valid": is_valid,
                "redis_connected": True
            }
            
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {
                "exists": False,
                "ttl_remaining": 0,
                "player_count": 0,
                "last_updated": None,
                "is_valid": False,
                "redis_connected": False,
                "error": str(e)
            }
    
    def _transform_players(self, raw_players: Dict[str, Dict]) -> Dict[str, Dict]:
        """
        Transform Sleeper player schema to simplified format.
        
        Args:
            raw_players: Raw player data from Sleeper API
            
        Returns:
            Dict: Transformed player data
        """
        simplified = {}
        
        for player_id, player_data in raw_players.items():
            try:
                # Skip players without required fields
                if not self._validate_player_data(player_data):
                    continue
                
                # Build simplified player record
                first_name = player_data.get("first_name", "")
                last_name = player_data.get("last_name", "")
                name = f"{first_name} {last_name}".strip()
                
                if not name:
                    continue
                
                simplified_player = {
                    "name": name,
                    "team": player_data.get("team"),
                    "positions": player_data.get("fantasy_positions", []),
                    "player_id": player_id,
                    "status": player_data.get("status"),
                    "injury_status": player_data.get("injury_status"),
                }
                
                simplified[player_id] = simplified_player
                
            except Exception as e:
                logger.warning(f"Error transforming player {player_id}: {e}")
                continue
        
        logger.info(f"Transformed {len(simplified)} players from {len(raw_players)} raw entries")
        return simplified
    
    def _validate_player_data(self, player_data: Dict) -> bool:
        """
        Validate required fields exist in player data.
        
        Args:
            player_data: Player data dictionary
            
        Returns:
            bool: True if valid, False otherwise
        """
        required_fields = ["first_name", "last_name", "fantasy_positions"]
        
        for field in required_fields:
            if field not in player_data or player_data[field] is None:
                return False
        
        # Check if fantasy_positions is a non-empty list
        positions = player_data.get("fantasy_positions", [])
        if not isinstance(positions, list) or len(positions) == 0:
            return False
        
        return True