"""
Redis service for caching operations.
"""

import json
import logging
from typing import Optional, Dict, Any, List
import redis
from redis.connection import ConnectionPool

from backend.config import settings

logger = logging.getLogger(__name__)


class RedisService:
    """Redis service for caching operations with connection pooling."""
    
    def __init__(self, redis_host: str = None, redis_port: int = None, redis_db: int = None,
                 redis_password: str = None, redis_ssl: bool = None, decode_responses: bool = None):
        """Initialize Redis service with configuration."""
        # Use provided parameters or fall back to settings
        self.host = redis_host or settings.REDIS_HOST
        self.port = redis_port or settings.REDIS_PORT
        self.db = redis_db or settings.REDIS_DB
        self.password = redis_password or settings.REDIS_PASSWORD
        self.ssl = redis_ssl if redis_ssl is not None else settings.REDIS_SSL
        self.decode_responses = decode_responses if decode_responses is not None else settings.REDIS_DECODE_RESPONSES
        
        # Initialize connection pool
        self.pool = None
        self.client = None
        self._initialize_client()
    
    def _initialize_client(self):
        """Initialize Redis client with connection pooling."""
        try:
            # Build connection pool parameters
            pool_params = {
                'host': self.host,
                'port': self.port,
                'db': self.db,
                'decode_responses': self.decode_responses,
                'socket_connect_timeout': 5,
                'socket_timeout': 5,
                'retry_on_timeout': True
            }
            
            # Only add password if provided
            if self.password:
                pool_params['password'] = self.password
            
            # Only add SSL if explicitly enabled (for remote Redis)
            if self.ssl:
                pool_params['ssl'] = True
            
            # Create connection pool
            self.pool = ConnectionPool(**pool_params)
            
            # Create Redis client
            self.client = redis.Redis(connection_pool=self.pool)
            
            # Test connection
            self.client.ping()
            logger.info(f"Redis connection established: {self.host}:{self.port}/{self.db}")
            
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis connection failed: {e}")
            self.client = None
        except Exception as e:
            logger.error(f"Redis initialization error: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Redis is connected and available."""
        if not self.client:
            return False
        try:
            self.client.ping()
            return True
        except (redis.ConnectionError, redis.TimeoutError):
            return False
    
    def get(self, key: str) -> Optional[str]:
        """
        Get value by key.
        
        Args:
            key: Redis key
            
        Returns:
            Value as string or None if not found or error
        """
        if not self.client:
            return None
            
        try:
            return self.client.get(key)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis get error for key {key}: {e}")
            return None
    
    def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Set value with optional TTL.
        
        Args:
            key: Redis key
            value: Value to store
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            if ttl:
                return bool(self.client.setex(key, ttl, value))
            else:
                return bool(self.client.set(key, value))
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """
        Delete key.
        
        Args:
            key: Redis key to delete
            
        Returns:
            True if successful, False otherwise
        """
        if not self.client:
            return False
            
        try:
            return bool(self.client.delete(key))
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """
        Check if key exists.
        
        Args:
            key: Redis key
            
        Returns:
            True if exists, False otherwise
        """
        if not self.client:
            return False
            
        try:
            return bool(self.client.exists(key))
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis exists error for key {key}: {e}")
            return False
    
    def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for key.
        
        Args:
            key: Redis key
            
        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist, 0 on error
        """
        if not self.client:
            return 0
            
        try:
            return self.client.ttl(key)
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis TTL error for key {key}: {e}")
            return 0
    
    def set_json(self, key: str, data: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Store JSON data.
        
        Args:
            key: Redis key
            data: Dictionary to store as JSON
            ttl: Time to live in seconds
            
        Returns:
            True if successful, False otherwise
        """
        try:
            json_str = json.dumps(data, separators=(',', ':'))
            return self.set(key, json_str, ttl)
        except (TypeError, ValueError) as e:
            logger.error(f"JSON serialization error for key {key}: {e}")
            return False
    
    def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and parse JSON data.
        
        Args:
            key: Redis key
            
        Returns:
            Parsed dictionary or None if not found or error
        """
        json_str = self.get(key)
        if json_str is None:
            return None
            
        try:
            return json.loads(json_str)
        except (TypeError, ValueError, json.JSONDecodeError) as e:
            logger.error(f"JSON deserialization error for key {key}: {e}")
            return None
    
    def scan_keys(self, pattern: str) -> List[str]:
        """
        Scan for keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "sleeper:transactions:123:*")
            
        Returns:
            List[str]: List of matching keys
        """
        if not self.client:
            return []
        
        try:
            # Use scan_iter for memory-efficient iteration
            keys = []
            for key in self.client.scan_iter(match=pattern, count=100):
                keys.append(key)
            return keys
        except (redis.ConnectionError, redis.TimeoutError) as e:
            logger.error(f"Redis scan error for pattern {pattern}: {e}")
            return []
    
    def delete_by_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "sleeper:transactions:123:*")
            
        Returns:
            int: Number of keys deleted
        """
        if not self.client:
            return 0
        
        try:
            keys = self.scan_keys(pattern)
            if not keys:
                return 0
            
            # Delete in batches
            deleted = 0
            for key in keys:
                if self.delete(key):
                    deleted += 1
            
            logger.info(f"Deleted {deleted} keys matching pattern: {pattern}")
            return deleted
            
        except Exception as e:
            logger.error(f"Error deleting keys by pattern {pattern}: {e}")
            return 0
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def close(self):
        """Close Redis connection and cleanup resources."""
        if self.client:
            try:
                self.client.close()
                logger.info("Redis connection closed")
            except Exception as e:
                logger.error(f"Error closing Redis connection: {e}")
        
        if self.pool:
            try:
                self.pool.disconnect()
            except Exception as e:
                logger.error(f"Error disconnecting Redis pool: {e}")