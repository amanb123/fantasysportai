"""
League data cache service for managing Sleeper league data caching.
"""

import logging
from typing import Optional, Dict, List, Tuple, Any
from datetime import datetime, timezone

from backend.config import settings
from backend.services.redis_service import RedisService
from backend.services.sleeper_service import SleeperService

logger = logging.getLogger(__name__)


class LeagueDataCacheService:
    """Service for managing Sleeper league data caching with Redis."""
    
    def __init__(self, redis_service: RedisService, sleeper_service: SleeperService):
        """Initialize cache service with dependencies."""
        self.redis_service = redis_service
        self.sleeper_service = sleeper_service
        
        # Load cache configuration
        self.league_ttl = settings.SLEEPER_LEAGUE_CACHE_TTL
        self.roster_ttl = settings.SLEEPER_ROSTER_CACHE_TTL
        self.transaction_ttl = settings.SLEEPER_TRANSACTION_CACHE_TTL
        self.matchup_ttl = settings.SLEEPER_MATCHUP_CACHE_TTL
        
        # Load cache key prefixes
        self.league_prefix = settings.SLEEPER_LEAGUE_CACHE_KEY_PREFIX
        self.roster_prefix = settings.SLEEPER_ROSTER_CACHE_KEY_PREFIX
        self.transaction_prefix = settings.SLEEPER_TRANSACTION_CACHE_KEY_PREFIX
        self.matchup_prefix = settings.SLEEPER_MATCHUP_CACHE_KEY_PREFIX
        
        # Load polling configuration
        self.transaction_rounds_to_fetch = settings.SLEEPER_TRANSACTION_ROUNDS_TO_FETCH
        self.matchup_weeks_to_fetch = settings.SLEEPER_MATCHUP_WEEKS_TO_FETCH
    
    async def cache_league_data(self, league_id: str, user_id: Optional[str] = None, season: Optional[str] = None) -> Tuple[bool, Optional[str]]:
        """
        Fetch league data from Sleeper API and cache in Redis.
        
        Args:
            league_id: Sleeper league ID
            user_id: Optional user ID for caching user's leagues list
            season: Optional season for user leagues (default: "2024")
            
        Returns:
            Tuple: (success: bool, error_message: Optional[str])
        """
        try:
            logger.info(f"Caching league data for league {league_id}")
            
            # Check Redis connection
            if not self.redis_service.is_connected():
                return False, "Redis connection unavailable"
            
            # Fetch and cache individual league metadata
            async with SleeperService() as sleeper:
                # Get league details via GET /league/{league_id}
                # Note: Using the client directly to access the league endpoint
                try:
                    response = await sleeper.client.get(f"/league/{league_id}")
                    if response.status_code == 200:
                        league_data = response.json()
                        
                        # Cache league metadata
                        cache_key = self._build_cache_key(self.league_prefix, league_id)
                        success = self.redis_service.set_json(cache_key, league_data, self.league_ttl)
                        
                        if not success:
                            return False, "Failed to cache league data in Redis"
                        
                        logger.info(f"Successfully cached league data for league {league_id}")
                    else:
                        logger.warning(f"League {league_id} not found or inaccessible")
                except Exception as e:
                    logger.warning(f"Could not fetch league metadata for {league_id}: {e}")
                
                # If user_id provided, cache user's leagues list
                if user_id:
                    season = season or "2024"
                    leagues = await sleeper.get_user_leagues(user_id, "nba", season)
                    
                    if leagues:
                        # Cache under user:season key
                        user_leagues_key = f"{self.league_prefix}:user:{user_id}:{season}"
                        success = self.redis_service.set_json(user_leagues_key, leagues, self.league_ttl)
                        
                        if not success:
                            logger.warning(f"Failed to cache leagues list for user {user_id}")
                        else:
                            logger.info(f"Successfully cached {len(leagues)} leagues for user {user_id}, season {season}")
            
            return True, None
            
        except Exception as e:
            error_msg = f"Error caching league data for {league_id}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    async def cache_rosters(self, league_id: str) -> Tuple[bool, Optional[str]]:
        """
        Fetch rosters from Sleeper API and cache in Redis.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            Tuple: (success: bool, error_message: Optional[str])
        """
        try:
            logger.info(f"Caching rosters for league {league_id}")
            
            # Check Redis connection
            if not self.redis_service.is_connected():
                return False, "Redis connection unavailable"
            
            # Fetch rosters from Sleeper API
            async with SleeperService() as sleeper:
                rosters = await sleeper.get_league_rosters(league_id)
            
            if rosters is None:
                return False, "Failed to fetch rosters from Sleeper API"
            
            # Store in Redis with TTL
            cache_key = self._build_cache_key(self.roster_prefix, league_id)
            success = self.redis_service.set_json(cache_key, rosters, self.roster_ttl)
            
            if not success:
                return False, "Failed to cache rosters in Redis"
            
            logger.info(f"Successfully cached {len(rosters)} rosters for league {league_id}")
            return True, None
            
        except Exception as e:
            error_msg = f"Error caching rosters for {league_id}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    async def cache_transactions(self, league_id: str, rounds: Optional[List[int]] = None) -> Tuple[bool, Optional[str]]:
        """
        Fetch transactions from Sleeper API and cache in Redis.
        
        Args:
            league_id: Sleeper league ID
            rounds: List of round numbers to fetch (None = fetch last N rounds from settings)
            
        Returns:
            Tuple: (success: bool, error_message: Optional[str])
        """
        try:
            logger.info(f"Caching transactions for league {league_id}")
            
            # Check Redis connection
            if not self.redis_service.is_connected():
                return False, "Redis connection unavailable"
            
            # Determine rounds to fetch
            if rounds is None:
                # Fetch last N rounds based on settings
                current_round = await self._get_current_round()
                rounds = list(range(max(1, current_round - self.transaction_rounds_to_fetch + 1), current_round + 1))
            
            # Fetch transactions for multiple rounds
            async with SleeperService() as sleeper:
                transactions_bulk = await sleeper.get_league_transactions_bulk(league_id, rounds)
            
            if not transactions_bulk:
                logger.warning(f"No transactions fetched for league {league_id}")
                return True, None  # Not an error, just no data
            
            # Store each round separately with TTL
            for round_num, transactions in transactions_bulk.items():
                cache_key = self._build_cache_key(self.transaction_prefix, league_id, str(round_num))
                self.redis_service.set_json(cache_key, transactions, self.transaction_ttl)
            
            logger.info(f"Successfully cached transactions for {len(transactions_bulk)} rounds for league {league_id}")
            return True, None
            
        except Exception as e:
            error_msg = f"Error caching transactions for {league_id}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    async def cache_matchups(self, league_id: str, weeks: Optional[List[int]] = None) -> Tuple[bool, Optional[str]]:
        """
        Fetch matchups from Sleeper API and cache in Redis.
        
        Args:
            league_id: Sleeper league ID
            weeks: List of week numbers to fetch (None = fetch last N weeks from settings)
            
        Returns:
            Tuple: (success: bool, error_message: Optional[str])
        """
        try:
            logger.info(f"Caching matchups for league {league_id}")
            
            # Check Redis connection
            if not self.redis_service.is_connected():
                return False, "Redis connection unavailable"
            
            # Determine weeks to fetch
            if weeks is None:
                # Fetch last N weeks based on settings
                current_week = await self._get_current_round()  # Use same logic as rounds
                weeks = list(range(max(1, current_week - self.matchup_weeks_to_fetch + 1), current_week + 1))
            
            # Fetch matchups for multiple weeks
            async with SleeperService() as sleeper:
                matchups_bulk = await sleeper.get_league_matchups_bulk(league_id, weeks)
            
            if not matchups_bulk:
                logger.warning(f"No matchups fetched for league {league_id}")
                return True, None  # Not an error, just no data
            
            # Store each week separately with TTL
            for week_num, matchups in matchups_bulk.items():
                cache_key = self._build_cache_key(self.matchup_prefix, league_id, str(week_num))
                self.redis_service.set_json(cache_key, matchups, self.matchup_ttl)
            
            logger.info(f"Successfully cached matchups for {len(matchups_bulk)} weeks for league {league_id}")
            return True, None
            
        except Exception as e:
            error_msg = f"Error caching matchups for {league_id}: {e}"
            logger.error(error_msg)
            return False, error_msg
    
    def get_cached_rosters(self, league_id: str) -> Optional[List[Dict]]:
        """
        Retrieve rosters from Redis cache.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            List[Dict]: Cached roster data or None if cache miss
        """
        try:
            if not self.redis_service.is_connected():
                logger.warning("Redis connection unavailable for roster cache retrieval")
                return None
            
            cache_key = self._build_cache_key(self.roster_prefix, league_id)
            cached_data = self.redis_service.get_json(cache_key)
            
            if cached_data is None:
                logger.info(f"Roster cache miss for league {league_id}")
                return None
            
            ttl_remaining = self.redis_service.get_ttl(cache_key)
            logger.info(f"Roster cache hit for league {league_id}: {len(cached_data)} rosters, TTL: {ttl_remaining}s")
            return cached_data
            
        except Exception as e:
            logger.error(f"Error retrieving cached rosters for league {league_id}: {e}")
            return None
    
    def get_cached_transactions(self, league_id: str, round: Optional[int] = None) -> Optional[Dict]:
        """
        Retrieve transactions from Redis cache.
        
        Args:
            league_id: Sleeper league ID
            round: Specific round to fetch (None = fetch all cached rounds)
            
        Returns:
            Dict: Transaction data (single round or all rounds) or None if cache miss
        """
        try:
            if not self.redis_service.is_connected():
                logger.warning("Redis connection unavailable for transaction cache retrieval")
                return None
            
            if round is not None:
                # Fetch specific round
                cache_key = self._build_cache_key(self.transaction_prefix, league_id, str(round))
                cached_data = self.redis_service.get_json(cache_key)
                
                if cached_data is None:
                    logger.info(f"Transaction cache miss for league {league_id}, round {round}")
                    return None
                
                logger.info(f"Transaction cache hit for league {league_id}, round {round}")
                return {round: cached_data}
            else:
                # Fetch all cached rounds
                result = {}
                # Try to fetch last N rounds
                # Use cached week value if available, otherwise use default
                cache_key_week = "sleeper:nba_state:current_week"
                cached_week = self.redis_service.get(cache_key_week)
                if cached_week is not None:
                    try:
                        current_round = int(cached_week)
                    except (ValueError, TypeError):
                        current_round = 1  # Default to week 1
                else:
                    current_round = 1  # Default to week 1
                rounds = list(range(max(1, current_round - self.transaction_rounds_to_fetch + 1), current_round + 1))
                
                for round_num in rounds:
                    cache_key = self._build_cache_key(self.transaction_prefix, league_id, str(round_num))
                    cached_data = self.redis_service.get_json(cache_key)
                    if cached_data is not None:
                        result[round_num] = cached_data
                
                if not result:
                    logger.info(f"Transaction cache miss for league {league_id} (all rounds)")
                    return None
                
                logger.info(f"Transaction cache hit for league {league_id}: {len(result)} rounds")
                return result
            
        except Exception as e:
            logger.error(f"Error retrieving cached transactions for league {league_id}: {e}")
            return None
    
    def get_cached_matchups(self, league_id: str, week: Optional[int] = None) -> Optional[Dict]:
        """
        Retrieve matchups from Redis cache.
        
        Args:
            league_id: Sleeper league ID
            week: Specific week to fetch (None = fetch all cached weeks)
            
        Returns:
            Dict: Matchup data (single week or all weeks) or None if cache miss
        """
        try:
            if not self.redis_service.is_connected():
                logger.warning("Redis connection unavailable for matchup cache retrieval")
                return None
            
            if week is not None:
                # Fetch specific week
                cache_key = self._build_cache_key(self.matchup_prefix, league_id, str(week))
                cached_data = self.redis_service.get_json(cache_key)
                
                if cached_data is None:
                    logger.info(f"Matchup cache miss for league {league_id}, week {week}")
                    return None
                
                logger.info(f"Matchup cache hit for league {league_id}, week {week}")
                return {week: cached_data}
            else:
                # Fetch all cached weeks
                result = {}
                # Try to fetch last N weeks
                # Use cached week value if available, otherwise use default
                cache_key_week = "sleeper:nba_state:current_week"
                cached_week = self.redis_service.get(cache_key_week)
                if cached_week is not None:
                    try:
                        current_week = int(cached_week)
                    except (ValueError, TypeError):
                        current_week = 1  # Default to week 1
                else:
                    current_week = 1  # Default to week 1
                weeks = list(range(max(1, current_week - self.matchup_weeks_to_fetch + 1), current_week + 1))
                
                for week_num in weeks:
                    cache_key = self._build_cache_key(self.matchup_prefix, league_id, str(week_num))
                    cached_data = self.redis_service.get_json(cache_key)
                    if cached_data is not None:
                        result[week_num] = cached_data
                
                if not result:
                    logger.info(f"Matchup cache miss for league {league_id} (all weeks)")
                    return None
                
                logger.info(f"Matchup cache hit for league {league_id}: {len(result)} weeks")
                return result
            
        except Exception as e:
            logger.error(f"Error retrieving cached matchups for league {league_id}: {e}")
            return None
    
    async def refresh_all_data(self, league_id: str) -> Dict[str, bool]:
        """
        Refresh all data types for a league.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            Dict: Success status for each data type
        """
        try:
            logger.info(f"Refreshing all data for league {league_id}")
            
            results = {}
            
            # Refresh rosters
            success, error = await self.cache_rosters(league_id)
            results['rosters'] = success
            if error:
                logger.error(f"Roster refresh error: {error}")
            
            # Refresh transactions
            success, error = await self.cache_transactions(league_id)
            results['transactions'] = success
            if error:
                logger.error(f"Transaction refresh error: {error}")
            
            # Refresh matchups
            success, error = await self.cache_matchups(league_id)
            results['matchups'] = success
            if error:
                logger.error(f"Matchup refresh error: {error}")
            
            logger.info(f"Refresh complete for league {league_id}: {results}")
            return results
            
        except Exception as e:
            logger.error(f"Error refreshing all data for league {league_id}: {e}")
            return {'rosters': False, 'transactions': False, 'matchups': False}
    
    def invalidate_league_cache(self, league_id: str) -> bool:
        """
        Delete all cached data for a league.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            bool: True if successful
        """
        try:
            if not self.redis_service.is_connected():
                logger.warning("Redis connection unavailable for cache invalidation")
                return False
            
            # Delete rosters
            roster_key = self._build_cache_key(self.roster_prefix, league_id)
            self.redis_service.delete(roster_key)
            
            # Delete all transactions by pattern (not just last N rounds)
            trans_pattern = f"{self.transaction_prefix}:{league_id}:*"
            trans_deleted = self.redis_service.delete_by_pattern(trans_pattern)
            logger.info(f"Deleted {trans_deleted} transaction cache keys for league {league_id}")
            
            # Delete all matchups by pattern (not just last N weeks)
            match_pattern = f"{self.matchup_prefix}:{league_id}:*"
            match_deleted = self.redis_service.delete_by_pattern(match_pattern)
            logger.info(f"Deleted {match_deleted} matchup cache keys for league {league_id}")
            
            # Delete league metadata
            league_key = self._build_cache_key(self.league_prefix, league_id)
            self.redis_service.delete(league_key)
            
            logger.info(f"Successfully invalidated cache for league {league_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error invalidating cache for league {league_id}: {e}")
            return False
    
    def get_cache_stats(self, league_id: str) -> Dict[str, Any]:
        """
        Get cache metadata and statistics for a league.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            Dict: Cache status information
        """
        try:
            if not self.redis_service.is_connected():
                return {
                    "league_id": league_id,
                    "rosters_cached": False,
                    "transactions_cached": False,
                    "matchups_cached": False,
                    "redis_connected": False
                }
            
            stats = {"league_id": league_id, "redis_connected": True}
            
            # Check rosters
            roster_key = self._build_cache_key(self.roster_prefix, league_id)
            stats['rosters_cached'] = self.redis_service.exists(roster_key)
            stats['rosters_ttl'] = self.redis_service.get_ttl(roster_key) if stats['rosters_cached'] else None
            
            # Check transactions
            # Use cached week value if available, otherwise use default
            cache_key_week = "sleeper:nba_state:current_week"
            cached_week = self.redis_service.get(cache_key_week)
            if cached_week is not None:
                try:
                    current_round = int(cached_week)
                except (ValueError, TypeError):
                    current_round = 1  # Default to week 1
            else:
                current_round = 1  # Default to week 1
            rounds = list(range(max(1, current_round - self.transaction_rounds_to_fetch + 1), current_round + 1))
            cached_rounds = []
            for round_num in rounds:
                trans_key = self._build_cache_key(self.transaction_prefix, league_id, str(round_num))
                if self.redis_service.exists(trans_key):
                    cached_rounds.append(round_num)
            stats['transactions_cached'] = len(cached_rounds) > 0
            stats['transactions_rounds'] = cached_rounds if cached_rounds else None
            
            # Check matchups
            weeks = list(range(max(1, current_round - self.matchup_weeks_to_fetch + 1), current_round + 1))
            cached_weeks = []
            for week_num in weeks:
                match_key = self._build_cache_key(self.matchup_prefix, league_id, str(week_num))
                if self.redis_service.exists(match_key):
                    cached_weeks.append(week_num)
            stats['matchups_cached'] = len(cached_weeks) > 0
            stats['matchups_weeks'] = cached_weeks if cached_weeks else None
            
            stats['last_updated'] = datetime.now(timezone.utc).isoformat()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting cache stats for league {league_id}: {e}")
            return {
                "league_id": league_id,
                "rosters_cached": False,
                "transactions_cached": False,
                "matchups_cached": False,
                "redis_connected": False,
                "error": str(e)
            }
    
    def _build_cache_key(self, prefix: str, league_id: str, suffix: Optional[str] = None) -> str:
        """
        Build Redis cache key from components.
        
        Args:
            prefix: Cache key prefix
            league_id: Sleeper league ID
            suffix: Optional suffix (e.g., round number, week number)
            
        Returns:
            str: Complete cache key
        """
        if suffix:
            return f"{prefix}:{league_id}:{suffix}"
        return f"{prefix}:{league_id}"
    
    async def _get_current_round(self) -> int:
        """
        Get current NBA round/week from Sleeper state API with caching.
        
        Returns:
            int: Current round number (defaults to 1 if API unavailable)
        """
        # Check cache first (cache for 1 hour to avoid excessive API calls)
        cache_key = "sleeper:nba_state:current_week"
        cached_week = self.redis_service.get(cache_key)
        
        if cached_week is not None:
            try:
                week = int(cached_week)
                logger.debug(f"Using cached current week: {week}")
                return week
            except (ValueError, TypeError):
                pass
        
        # Fetch from API (now properly async)
        try:
            async with SleeperService() as sleeper:
                state_data = await sleeper.get_nba_state()
            
            if state_data:
                # Try to extract week or leg information
                week = state_data.get("week") or state_data.get("leg") or 1
                
                # Cache for 1 hour (3600 seconds)
                self.redis_service.set(cache_key, str(week), ttl=3600)
                logger.info(f"Fetched current NBA week from API: {week}")
                return week
                
        except Exception as e:
            logger.warning(f"Failed to fetch current NBA week: {e}")
        
        # Default fallback (season start)
        default_week = 1
        logger.info(f"Using default week: {default_week}")
        return default_week
    
    def get_cached_league_details(self, league_id: str) -> Optional[Dict]:
        """
        Retrieve league details from Redis cache.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            Dict: Cached league details with settings or None if cache miss
        """
        try:
            if not self.redis_service.is_connected():
                logger.warning("Redis connection unavailable for league details retrieval")
                return None
            
            cache_key = self._build_cache_key(self.league_prefix, league_id)
            cached_data = self.redis_service.get_json(cache_key)
            
            if cached_data is None:
                logger.debug(f"Cache miss for league details: {league_id}")
                return None
            
            logger.debug(f"Cache hit for league details: {league_id}")
            return cached_data
            
        except Exception as e:
            logger.error(f"Error retrieving cached league details for {league_id}: {e}")
            return None
    
    def get_league_scoring_settings(self, league_id: str) -> Optional[Dict]:
        """
        Get league scoring settings from cache.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            Dict: Scoring settings or None if not available
        """
        try:
            league_details = self.get_cached_league_details(league_id)
            
            if not league_details:
                logger.debug(f"No cached league details for scoring settings: {league_id}")
                return None
            
            scoring_settings = league_details.get("scoring_settings")
            
            if scoring_settings:
                logger.debug(f"Retrieved scoring settings for league {league_id}")
            else:
                logger.debug(f"No scoring settings found for league {league_id}")
            
            return scoring_settings
            
        except Exception as e:
            logger.error(f"Error retrieving scoring settings for {league_id}: {e}")
            return None
    
    def get_league_roster_positions(self, league_id: str) -> Optional[List[str]]:
        """
        Get league roster positions from cache.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            List[str]: Roster position slots or None if not available
        """
        try:
            league_details = self.get_cached_league_details(league_id)
            
            if not league_details:
                logger.debug(f"No cached league details for roster positions: {league_id}")
                return None
            
            roster_positions = league_details.get("roster_positions")
            
            if roster_positions:
                logger.debug(f"Retrieved {len(roster_positions)} roster positions for league {league_id}")
            else:
                logger.debug(f"No roster positions found for league {league_id}")
            
            return roster_positions
            
        except Exception as e:
            logger.error(f"Error retrieving roster positions for {league_id}: {e}")
            return None
