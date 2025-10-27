"""
Shared dependency injection functions for FastAPI.
"""

from typing import Optional
import logging

from backend.session.database import get_repository
from backend.session.repository import BasketballRepository
from backend.services.redis_service import RedisService
from backend.services.player_cache_service import PlayerCacheService
from backend.services.league_data_cache_service import LeagueDataCacheService
from backend.services.sleeper_service import sleeper_service
from backend.services.nba_news_service_scrape import NBANewsService
from backend.config import settings

logger = logging.getLogger(__name__)

# Global service instances
_redis_service = None
_player_cache_service = None
_league_data_cache_service = None
_nba_news_service = None


def get_basketball_repository() -> BasketballRepository:
    """
    Dependency to get the basketball repository.
    
    Returns:
        BasketballRepository: Singleton repository instance
    """
    return get_repository()


def get_redis_service() -> Optional[RedisService]:
    """
    Dependency to get the Redis service.
    
    Returns:
        RedisService: Singleton Redis service instance or None if unavailable
    """
    global _redis_service
    
    if _redis_service is None:
        try:
            _redis_service = RedisService(
                redis_host=settings.REDIS_HOST,
                redis_port=settings.REDIS_PORT,
                redis_db=settings.REDIS_DB,
                redis_password=settings.REDIS_PASSWORD,
                redis_ssl=settings.REDIS_SSL,
                decode_responses=settings.REDIS_DECODE_RESPONSES
            )
            
            # Test connection
            if not _redis_service.is_connected():
                logger.warning("Redis service created but connection failed")
                return None
                
        except Exception as e:
            logger.error(f"Failed to create Redis service: {e}")
            return None
    
    return _redis_service


def get_player_cache_service() -> Optional[PlayerCacheService]:
    """
    Dependency to get the player cache service.
    
    Returns:
        PlayerCacheService: Player cache service instance or None if Redis unavailable
    """
    global _player_cache_service
    
    if _player_cache_service is None:
        redis_service = get_redis_service()
        if redis_service is None:
            logger.warning("Cannot create PlayerCacheService: Redis unavailable")
            return None
            
        _player_cache_service = PlayerCacheService(
            redis_service=redis_service,
            sleeper_service=sleeper_service
        )
    
    return _player_cache_service


def get_league_data_cache_service() -> Optional[LeagueDataCacheService]:
    """
    Dependency to get the league data cache service.
    
    Returns:
        LeagueDataCacheService: League data cache service instance or None if Redis unavailable
    """
    global _league_data_cache_service
    
    if _league_data_cache_service is None:
        redis_service = get_redis_service()
        if redis_service is None:
            logger.warning("Cannot create LeagueDataCacheService: Redis unavailable")
            return None
            
        _league_data_cache_service = LeagueDataCacheService(
            redis_service=redis_service,
            sleeper_service=sleeper_service
        )
    
    return _league_data_cache_service


def get_sleeper_service():
    """
    Dependency to get the Sleeper service.
    
    Returns:
        SleeperService: Singleton Sleeper service instance
    """
    return sleeper_service


# ===== NBA Stats Service Dependencies =====

# Global NBA service instances
_nba_stats_service = None
_nba_cache_service = None


def get_nba_stats_service():
    """
    Dependency to get the NBA stats service.
    
    Returns:
        NBAStatsService: Singleton NBA stats service instance or None if disabled
    """
    global _nba_stats_service
    
    if not settings.nba_stats_enabled:
        logger.info("NBA stats integration is disabled")
        return None
    
    if _nba_stats_service is None:
        try:
            from backend.services.nba_stats_service import NBAStatsService
            
            # Get redis service for caching
            redis_service = get_redis_service()
            _nba_stats_service = NBAStatsService(redis_service=redis_service)
            logger.info("NBA stats service initialized with Redis caching")
            
        except Exception as e:
            logger.error(f"Failed to create NBA stats service: {e}")
            return None
    
    return _nba_stats_service


def get_nba_mcp_service():
    """
    Dependency to get the NBA MCP service.
    
    Returns:
        NBAMCPService: Singleton NBA MCP service instance or None if disabled
    """
    if not settings.nba_mcp_enabled or not settings.nba_mcp_server_path:
        return None
    
    try:
        from backend.services.nba_mcp_service import get_nba_mcp_service as _get_mcp
        return _get_mcp()
    except Exception as e:
        logger.error(f"Failed to get NBA MCP service: {e}")
        return None


def get_nba_news_service() -> Optional[NBANewsService]:
    """
    Dependency to get the NBA News service.
    
    Returns:
        NBANewsService: Singleton NBA News service instance
    """
    global _nba_news_service
    
    if _nba_news_service is None:
        redis_service = get_redis_service()
        _nba_news_service = NBANewsService(redis_service=redis_service)
        logger.info("NBA News Service (ESPN scrape) initialized")
    
    return _nba_news_service


def get_nba_cache_service():
    """
    Dependency to get the NBA cache service.
    
    Returns:
        NBACacheService: Singleton NBA cache service instance or None if disabled/unavailable
    """
    global _nba_cache_service
    
    if not settings.nba_stats_enabled:
        logger.info("NBA stats integration is disabled")
        return None
    
    if _nba_cache_service is None:
        redis_service = get_redis_service()
        if redis_service is None:
            logger.warning("Cannot create NBACacheService: Redis unavailable")
            return None
        
        nba_stats_service = get_nba_stats_service()
        if nba_stats_service is None:
            logger.warning("Cannot create NBACacheService: NBAStatsService unavailable")
            return None
        
        try:
            from backend.services.nba_cache_service import NBACacheService
            
            _nba_cache_service = NBACacheService(
                redis_service=redis_service,
                nba_stats_service=nba_stats_service,
                repository=get_basketball_repository()
            )
            logger.info("NBA cache service initialized")
            
        except Exception as e:
            logger.error(f"Failed to create NBA cache service: {e}")
            return None
    
    return _nba_cache_service


# ===== Roster Ranking Service Dependencies =====

_roster_ranking_service = None


def get_roster_ranking_service() -> Optional['RosterRankingService']:
    """
    Dependency to get the roster ranking service.
    
    Returns:
        RosterRankingService: Singleton instance or None if unavailable
    """
    global _roster_ranking_service
    
    if _roster_ranking_service is None:
        try:
            from backend.services.roster_ranking_service import RosterRankingService
            
            # Get dependencies
            nba_stats_service = get_nba_stats_service()  # For per-game stats
            sleeper_service = get_sleeper_service()
            redis_service = get_redis_service()
            league_cache_service = get_league_data_cache_service()
            
            # Check critical dependencies (nba_stats_service can work without MCP)
            if not (sleeper_service and redis_service and league_cache_service):
                logger.warning("RosterRankingService dependencies unavailable")
                return None
            
            # NBA stats service is optional but recommended
            if not nba_stats_service:
                logger.warning("RosterRankingService: NBAStatsService unavailable - using fallback logic")
            
            # Get NBA MCP service (optional - for advanced features)
            nba_mcp_service = get_nba_mcp_service()
            
            _roster_ranking_service = RosterRankingService(
                nba_mcp_service=nba_mcp_service,  # Can be None
                sleeper_service=sleeper_service,
                redis_service=redis_service,
                league_cache_service=league_cache_service,
                nba_stats_service=nba_stats_service  # Can be None
            )
            logger.info("RosterRankingService initialized")
            
        except Exception as e:
            logger.error(f"Failed to create RosterRankingService: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    return _roster_ranking_service


# Roster Context Builder
_roster_context_builder = None


def get_roster_context_builder() -> Optional['RosterContextBuilder']:
    """
    Dependency to get the roster context builder service.
    
    Returns:
        RosterContextBuilder: Singleton instance or None if unavailable
    """
    global _roster_context_builder
    
    if _roster_context_builder is None:
        try:
            # Import here to avoid circular dependencies
            from backend.services.roster_context_builder import RosterContextBuilder
            
            # Get dependencies
            player_cache = get_player_cache_service()
            league_cache = get_league_data_cache_service()
            nba_cache = get_nba_cache_service()
            nba_stats = get_nba_stats_service()  # May be None if nba_api unavailable
            repository = get_basketball_repository()
            
            # Get NBA MCP service (optional, for schedule/player data)
            nba_mcp = None
            if settings.nba_mcp_enabled and settings.nba_mcp_server_path:
                try:
                    from backend.services.nba_mcp_service import get_nba_mcp_service
                    nba_mcp = get_nba_mcp_service()
                    if nba_mcp:
                        logger.info("NBA MCP Service available for roster context")
                except Exception as mcp_err:
                    logger.warning(f"NBA MCP Service unavailable for roster context: {mcp_err}")
            
            # Check critical dependencies
            if not player_cache:
                logger.warning("Cannot create RosterContextBuilder: PlayerCacheService unavailable")
                return None
            
            if not league_cache:
                logger.warning("Cannot create RosterContextBuilder: LeagueDataCacheService unavailable")
                return None
            
            # NBAStatsService is optional - allow graceful degradation
            if not nba_stats:
                logger.warning("NBAStatsService unavailable - historical stats will be disabled")
            
            # Get roster ranking service (optional)
            roster_ranking = None
            try:
                roster_ranking = get_roster_ranking_service()
                if roster_ranking:
                    logger.info("Roster ranking service available for roster context")
            except Exception as ranking_err:
                logger.warning(f"Roster ranking service unavailable for roster context: {ranking_err}")
            
            # Create service (nba_stats, nba_mcp, and roster_ranking can be None)
            _roster_context_builder = RosterContextBuilder(
                player_cache_service=player_cache,
                league_data_cache_service=league_cache,
                nba_cache_service=nba_cache,
                nba_stats_service=nba_stats,
                basketball_repository=repository,
                nba_mcp_service=nba_mcp,
                roster_ranking_service=roster_ranking
            )
            
            logger.info("Roster context builder service initialized")
            
        except Exception as e:
            logger.error(f"Failed to create roster context builder: {e}")
            return None
    
    return _roster_context_builder


# ===== Trade Assistant Service Dependencies =====

_trade_analysis_service = None
_matchup_simulation_service = None


def get_trade_analysis_service():
    """
    Dependency to get the Trade Analysis service.
    
    Returns:
        TradeAnalysisService: Singleton instance or None if unavailable
    """
    global _trade_analysis_service
    
    if _trade_analysis_service is None:
        try:
            from backend.services.trade_analysis_service import TradeAnalysisService
            from backend.agents.agent_factory import AgentFactory
            
            # Get services (NBA MCP is optional)
            sleeper = get_sleeper_service()
            agent_factory = AgentFactory()
            nba_news = get_nba_news_service()
            nba_mcp = get_nba_mcp_service()  # Optional
            nba_stats = get_nba_stats_service()  # Fallback
            nba_cache = get_nba_cache_service()  # For schedules
            
            # Check critical dependencies
            if not sleeper:
                logger.warning("Cannot create TradeAnalysisService: Sleeper service unavailable")
                return None
            
            # At least one NBA data source is recommended
            if not (nba_mcp or nba_stats):
                logger.warning("TradeAnalysisService: No NBA data services available - limited functionality")
            
            _trade_analysis_service = TradeAnalysisService(
                agent_factory=agent_factory,
                sleeper_service=sleeper,
                nba_news_service=nba_news,
                nba_mcp_service=nba_mcp,  # Can be None
                nba_stats_service=nba_stats,  # Can be None
                nba_cache_service=nba_cache  # Can be None
            )
            
            logger.info("Trade Analysis service initialized")
            
        except Exception as e:
            logger.error(f"Failed to create Trade Analysis service: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    return _trade_analysis_service


def get_matchup_simulation_service():
    """
    Dependency to get the Matchup Simulation service.
    
    Returns:
        MatchupSimulationService: Singleton instance or None if unavailable
    """
    global _matchup_simulation_service
    
    if _matchup_simulation_service is None:
        try:
            from backend.services.matchup_simulation_service import MatchupSimulationService
            
            # Get required dependencies
            nba_mcp = get_nba_mcp_service()
            if nba_mcp is None:
                logger.warning("Cannot create MatchupSimulationService: NBA MCP unavailable")
                return None
            
            sleeper = get_sleeper_service()
            nba_stats = get_nba_stats_service()
            
            _matchup_simulation_service = MatchupSimulationService(
                nba_mcp_service=nba_mcp,
                sleeper_service=sleeper,
                nba_stats_service=nba_stats
            )
            
            logger.info("Matchup Simulation service initialized")
            
        except Exception as e:
            logger.error(f"Failed to create Matchup Simulation service: {e}")
            return None
    
    return _matchup_simulation_service
