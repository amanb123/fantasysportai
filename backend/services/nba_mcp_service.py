"""
NBA MCP Service - High-level service for NBA data using MCP.

This service provides a clean interface for NBA data retrieval
using the obinopaul/nba-mcp-server, maintaining compatibility with
the existing codebase.

Server: https://github.com/obinopaul/nba-mcp-server
"""

import logging
from typing import Dict, List, Optional
from datetime import datetime, date, timedelta

from .nba_mcp_client import NBAMCPClient

logger = logging.getLogger(__name__)


class NBAMCPService:
    """Service for retrieving NBA data via MCP."""
    
    _instance = None
    _client: Optional[NBAMCPClient] = None
    _schedule_cache_service = None
    
    def __init__(self, server_path: str):
        """
        Initialize the NBA MCP service.
        
        Args:
            server_path: Path to nba_server.py from obinopaul/nba-mcp-server
        """
        self.server_path = server_path
        self._initialized = False
    
    @classmethod
    def get_instance(cls, server_path: Optional[str] = None):
        """Get or create singleton instance."""
        if cls._instance is None:
            if server_path is None:
                raise ValueError("Server path required for first initialization")
            cls._instance = cls(server_path)
        return cls._instance
    
    async def initialize(self):
        """Initialize the MCP client connection."""
        if self._initialized:
            return
        
        try:
            self._client = NBAMCPClient(self.server_path)
            await self._client.initialize()
            self._initialized = True
            logger.info("NBA MCP service initialized")
        except Exception as e:
            logger.error(f"Failed to initialize NBA MCP service: {e}")
            raise
    
    async def close(self):
        """Close the MCP client connection."""
        if self._client:
            await self._client.close()
            self._initialized = False
    
    def set_schedule_cache_service(self, schedule_cache_service):
        """Set the schedule cache service (called after initialization)."""
        self._schedule_cache_service = schedule_cache_service
        logger.info("Schedule cache service attached to NBA MCP service")
    
    async def get_schedule_for_date_range(
        self,
        start_date: date,
        end_date: date,
        team_tricodes: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Get NBA schedule for a date range.
        
        Args:
            start_date: Start date
            end_date: End date
            team_tricodes: Optional list of team abbreviations to filter by
            
        Returns:
            List of game dictionaries compatible with existing format
        """
        # Try to initialize, but don't fail if it doesn't work and we have schedule cache
        if not self._initialized:
            try:
                await self.initialize()
            except Exception as e:
                if not self._schedule_cache_service:
                    # No schedule cache fallback available
                    raise
                logger.warning(f"NBA MCP initialization failed, will use schedule cache: {e}")
        
        try:
            # Use schedule cache if available (preferred since NBA MCP subprocess is broken)
            if self._schedule_cache_service:
                logger.info("Using schedule cache service")
                games = await self._schedule_cache_service.get_games_for_date_range(
                    start_date, end_date, team_tricodes
                )
                
                # Format for compatibility
                formatted_games = []
                for game in games:
                    # Parse game date to YYYY-MM-DD format
                    game_date_raw = game.get('GAME_DATE_EST', game.get('game_date', ''))
                    if '/' in game_date_raw:
                        # MM/DD/YYYY format - convert to YYYY-MM-DD
                        try:
                            from datetime import datetime
                            dt = datetime.strptime(game_date_raw.split()[0], '%m/%d/%Y')
                            game_date_formatted = dt.strftime('%Y-%m-%d')
                        except:
                            game_date_formatted = game_date_raw[:10]
                    else:
                        game_date_formatted = game_date_raw[:10]
                    
                    formatted_game = {
                        'game_id': game.get('GAME_ID', game.get('game_id', '')),
                        'game_date': game_date_formatted,
                        'game_time_utc': game_date_raw,
                        'home_team_tricode': game.get('HOME_TEAM_ABBREVIATION', game.get('home_team_tricode', '')),
                        'home_team_name': game.get('HOME_TEAM_NAME', game.get('home_team', '')),
                        'away_team_tricode': game.get('VISITOR_TEAM_ABBREVIATION', game.get('away_team_tricode', '')),
                        'away_team_name': game.get('VISITOR_TEAM_NAME', game.get('away_team', '')),
                        'home_score': game.get('HOME_TEAM_SCORE', game.get('home_team_score')),
                        'away_score': game.get('VISITOR_TEAM_SCORE', game.get('away_team_score')),
                        'game_status': game.get('GAME_STATUS_TEXT', game.get('game_status', 'Scheduled')),
                        'season': '2025-26'
                    }
                    formatted_games.append(formatted_game)
                
                logger.info(f"Retrieved {len(formatted_games)} games from schedule cache")
                return formatted_games
            
            # Fallback: Query each date individually
            formatted_games = []
            
            # Query each date individually using nba_list_todays_games
            current_date = start_date
            while current_date <= end_date:
                games = await self._client.get_games_by_date(current_date)
                logger.debug(f"MCP returned {len(games)} games for {current_date}")
                
                # Convert to format compatible with existing code
                for game in games:
                    # Extract team abbreviations from different possible formats
                    home_team_abbr = game.get('HOME_TEAM_ABBREVIATION', 
                                             game.get('HOME_TEAM_TRICODE', ''))
                    visitor_team_abbr = game.get('VISITOR_TEAM_ABBREVIATION',
                                                 game.get('AWAY_TEAM_ABBREVIATION', ''))
                    
                    # Filter by team tricodes if provided
                    if team_tricodes:
                        if home_team_abbr not in team_tricodes and visitor_team_abbr not in team_tricodes:
                            continue
                    
                    formatted_game = {
                        'game_id': game.get('GAME_ID', ''),
                        'game_date': current_date.isoformat(),
                        'game_time_utc': game.get('GAME_DATE_EST', current_date.isoformat()),
                        'home_team_tricode': home_team_abbr,
                        'home_team_name': game.get('HOME_TEAM_NAME', ''),
                        'away_team_tricode': visitor_team_abbr,
                        'away_team_name': game.get('VISITOR_TEAM_NAME', ''),
                        'home_score': game.get('HOME_TEAM_SCORE'),
                        'away_score': game.get('VISITOR_TEAM_SCORE'),
                        'game_status': game.get('GAME_STATUS_TEXT', 'Scheduled'),
                        'season': '2025-26'  # Current season
                    }
                    formatted_games.append(formatted_game)
                
                current_date += timedelta(days=1)
            
            logger.info(f"Retrieved {len(formatted_games)} games via MCP for date range")
            return formatted_games
            
        except Exception as e:
            logger.error(f"Error getting schedule via MCP: {e}")
            return []
    
    def _extract_team_abbreviation(self, game: Dict, team_type: str) -> str:
        """Extract team abbreviation from game data."""
        team_key = f"{team_type}_team"
        
        # Try different possible keys
        if team_key in game:
            if isinstance(game[team_key], dict):
                return game[team_key].get('abbreviation', '')
            return str(game[team_key])
        
        # Try direct abbreviation key
        abbr_key = f"{team_type}_team_abbreviation"
        if abbr_key in game:
            return game[abbr_key]
        
        return ''
    
    def _extract_team_name(self, game: Dict, team_type: str) -> str:
        """Extract team name from game data."""
        team_key = f"{team_type}_team"
        
        if team_key in game:
            if isinstance(game[team_key], dict):
                return game[team_key].get('full_name', game[team_key].get('name', ''))
            return str(game[team_key])
        
        # Try direct name key
        name_key = f"{team_type}_team_name"
        if name_key in game:
            return game[name_key]
        
        return ''
    
    async def get_player_info(self, player_name: str) -> Optional[Dict]:
        """
        Get player information by name.
        
        Args:
            player_name: Player name to search for
            
        Returns:
            Player info dictionary or None
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            player = await self._client.search_player(player_name)
            
            if not player:
                return None
            
            # Convert to format compatible with existing code
            return {
                'player_id': player.get('player_id', player.get('id')),
                'full_name': player.get('full_name', ''),
                'first_name': player.get('first_name', ''),
                'last_name': player.get('last_name', ''),
                'team': player.get('team_name', ''),
                'team_abbreviation': player.get('team_abbreviation', ''),
                'position': player.get('position', ''),
                'jersey_number': player.get('jersey_number', ''),
                'height': player.get('height', ''),
                'weight': player.get('weight', ''),
                'college': player.get('college', ''),
            }
            
        except Exception as e:
            logger.error(f"Error getting player info via MCP: {e}")
            return None
    
    async def get_player_stats(
        self,
        player_name: str,
        season: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Get player statistics.
        
        Args:
            player_name: Player name
            season: Season (e.g., "2025-26") - if None, gets career stats
            
        Returns:
            Player stats dictionary or None
        """
        if not self._initialized:
            await self.initialize()
        
        try:
            # First get player info to get ID
            player = await self._client.search_player(player_name)
            if not player:
                logger.warning(f"Player '{player_name}' not found")
                return None
            
            player_id = player.get('id')
            if not player_id:
                logger.warning(f"No player ID for '{player_name}'")
                return None
            
            # Get career stats
            stats = await self._client.get_player_career_stats(str(player_id))
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting player stats via MCP: {e}")
            return None
    
    async def get_player_game_logs(
        self,
        player_id: int,
        start_date: Optional[object] = None,
        end_date: Optional[object] = None
    ) -> List[Dict]:
        """
        Get game logs for a player within a date range.
        Delegates to NBAMCPClient.
        
        Args:
            player_id: NBA player ID
            start_date: Start date (datetime.date object)
            end_date: End date (datetime.date object)
            
        Returns:
            List of game log dictionaries
        """
        try:
            if not self._client:
                logger.error("MCP client not initialized")
                return []
            
            # Convert player_id to string as required by NBAMCPClient
            return await self._client.get_player_game_logs(
                player_id=str(player_id),
                start_date=start_date,
                end_date=end_date
            )
        except Exception as e:
            logger.error(f"Error getting player game logs via MCP: {e}")
            return []


# Singleton instance getter
_nba_mcp_service_instance: Optional[NBAMCPService] = None


def get_nba_mcp_service(server_path: Optional[str] = None) -> Optional[NBAMCPService]:
    """
    Get or create the NBA MCP service singleton.
    
    Args:
        server_path: Path to nba_server.py (required for first call)
        
    Returns:
        NBA MCP service instance or None if disabled
    """
    global _nba_mcp_service_instance
    
    if _nba_mcp_service_instance is None:
        if server_path:
            _nba_mcp_service_instance = NBAMCPService(server_path)
    
    return _nba_mcp_service_instance
