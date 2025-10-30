"""
Sleeper API integration service for fetching and validating Sleeper usernames.
"""

import logging
from typing import Optional, Tuple, Dict, List
import httpx
from backend.config import settings

logger = logging.getLogger(__name__)


class SleeperService:
    """Service for interacting with Sleeper API."""
    
    def __init__(self):
        """Initialize Sleeper service with HTTP client."""
        self.base_url = settings.SLEEPER_API_BASE_URL
        self.timeout = settings.SLEEPER_API_TIMEOUT
        # Create persistent client for singleton usage
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"User-Agent": "Fantasy Basketball League App"}
        )
    
    async def __aenter__(self):
        """Async context manager entry."""
        self.client = httpx.AsyncClient(
            base_url=self.base_url,
            timeout=self.timeout,
            headers={"User-Agent": "Fantasy Basketball League App"}
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.client:
            await self.client.aclose()
    
    def _ensure_client(self):
        """Ensure the HTTP client is open and ready."""
        if self.client is None or self.client.is_closed:
            logger.info("Recreating closed Sleeper HTTP client")
            self.client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=self.timeout,
                headers={"User-Agent": "Fantasy Basketball League App"}
            )
    
    async def get_user_by_username(self, username: str) -> Optional[Dict]:
        """
        Get user data from Sleeper API by username.
        
        Args:
            username: Sleeper username
            
        Returns:
            Dict: User data with user_id, username, display_name, avatar, or None if not found
        """
        try:
            self._ensure_client()
            logger.info(f"Fetching Sleeper user: {username}")
            
            response = await self.client.get(f"/user/{username}")
            
            if response.status_code == 404:
                logger.warning(f"Sleeper user not found: {username}")
                return None
            
            response.raise_for_status()
            user_data = response.json()
            
            logger.info(f"Retrieved Sleeper user {username}: {user_data.get('user_id')}")
            return user_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching Sleeper user {username}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching Sleeper user {username}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Sleeper user {username}: {e}")
            return None
    
    async def validate_sleeper_username(self, username: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate if a Sleeper username exists and is active.
        
        Args:
            username: Sleeper username to validate
            
        Returns:
            Tuple: (is_valid, user_id, error_message)
        """
        try:
            user_data = await self.get_user_by_username(username)
            
            if user_data is None:
                return False, None, f"Sleeper user '{username}' not found"
            
            user_id = user_data.get("user_id")
            if not user_id:
                return False, None, f"Invalid user data for '{username}'"
            
            # Check if user appears to be active (has display_name or recent activity)
            display_name = user_data.get("display_name") or user_data.get("username")
            if not display_name:
                return False, None, f"User '{username}' appears to be inactive"
            
            logger.info(f"Validated Sleeper user {username} with ID {user_id}")
            return True, user_id, None
            
        except Exception as e:
            error_msg = f"Error validating Sleeper username '{username}': {e}"
            logger.error(error_msg)
            return False, None, error_msg
    
    async def get_nba_players(self) -> Optional[Dict[str, Dict]]:
        """
        Get all NBA players from Sleeper API.
        
        Returns:
            Dict: Dictionary of {player_id: player_data} or None on error
        """
        import time
        
        try:
            logger.info("Fetching NBA players from Sleeper API (this may take 30+ seconds)")
            start_time = time.time()
            
            # Increase timeout for large response (~5MB)
            async with httpx.AsyncClient(
                base_url=self.base_url,
                timeout=30.0,  # Increased timeout for large payload
                headers={"User-Agent": "Fantasy Basketball League App"}
            ) as client:
                response = await client.get("/players/nba")
                
                if response.status_code == 404:
                    logger.warning("NBA players endpoint not found")
                    return None
                
                response.raise_for_status()
                players_data = response.json()
                
                fetch_duration = time.time() - start_time
                response_size = len(response.content) / (1024 * 1024)  # MB
                player_count = len(players_data) if isinstance(players_data, dict) else 0
                
                logger.info(f"Retrieved {player_count} NBA players from Sleeper API")
                logger.info(f"Response size: {response_size:.2f}MB, Duration: {fetch_duration:.2f}s")
                
                return players_data
                
        except httpx.TimeoutException:
            logger.error("Timeout fetching NBA players from Sleeper API (response too large)")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching NBA players: {e}")
            return None
        except (ValueError, TypeError) as e:
            logger.error(f"JSON decode error fetching NBA players: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching NBA players: {e}")
            return None
    
    async def get_player_by_id(self, player_id: str) -> Optional[Dict]:
        """
        Get single player data by player ID.
        
        NOTE: This endpoint is not officially supported by Sleeper API and may not work.
        Currently unused in the application. Individual player data should be retrieved
        from the cached get_nba_players() data via PlayerCacheService instead.
        
        Args:
            player_id: Sleeper player ID
            
        Returns:
            Dict: Player data or None if not found
        """
        try:
            logger.info(f"Fetching Sleeper player: {player_id}")
            
            response = await self.client.get(f"/players/nba/{player_id}")
            
            if response.status_code == 404:
                logger.warning(f"Sleeper player not found: {player_id}")
                return None
            
            response.raise_for_status()
            player_data = response.json()
            
            logger.info(f"Retrieved Sleeper player {player_id}")
            return player_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching Sleeper player {player_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching Sleeper player {player_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching Sleeper player {player_id}: {e}")
            return None

    async def get_user_leagues(self, user_id: str, sport: str = "nba", season: str = "2025") -> Optional[List[Dict]]:
        """
        Get leagues for a user by user ID, sport, and season.
        
        Args:
            user_id: Sleeper user ID
            sport: Sport type (default: "nba")
            season: Season year (default: "2025")
            
        Returns:
            List[Dict]: List of league data or None if not found/error
        """
        try:
            logger.info(f"Fetching Sleeper leagues for user {user_id}, sport {sport}, season {season}")
            
            response = await self.client.get(f"/user/{user_id}/leagues/{sport}/{season}")
            
            if response.status_code == 404:
                logger.warning(f"No leagues found for Sleeper user {user_id} in {sport} {season}")
                return []
            
            response.raise_for_status()
            leagues_data = response.json()
            
            logger.info(f"Retrieved {len(leagues_data)} leagues for Sleeper user {user_id}")
            return leagues_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching leagues for Sleeper user {user_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching leagues for Sleeper user {user_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching leagues for Sleeper user {user_id}: {e}")
            return None

    async def get_league_rosters(self, league_id: str) -> Optional[List[Dict]]:
        """
        Get rosters for a league by league ID.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            List[Dict]: List of roster data or None if not found/error
        """
        try:
            logger.info(f"Fetching Sleeper rosters for league {league_id}")
            
            response = await self.client.get(f"/league/{league_id}/rosters")
            
            logger.info(f"Sleeper API response status: {response.status_code}")
            
            if response.status_code == 404:
                logger.warning(f"League not found: {league_id} (404 response)")
                return None
            
            if response.status_code != 200:
                logger.error(f"Unexpected status code {response.status_code} for league {league_id}")
                logger.error(f"Response body: {response.text[:500]}")
                return None
            
            response.raise_for_status()
            rosters_data = response.json()
            
            if not rosters_data:
                logger.warning(f"Empty rosters list returned for league {league_id}")
            else:
                logger.info(f"Retrieved {len(rosters_data)} rosters for league {league_id}")
            
            return rosters_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching rosters for league {league_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching rosters for league {league_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching rosters for league {league_id}: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return None

    async def get_current_nba_season(self) -> str:
        """
        Get current NBA season from Sleeper API.
        
        Returns:
            str: Current season year (e.g., "2025") or default "2025"
        """
        try:
            logger.info("Fetching current NBA season from Sleeper")
            
            response = await self.client.get("/state/nba")
            
            if response.status_code == 404:
                logger.warning("NBA state not found, using default season 2025")
                return "2025"
            
            response.raise_for_status()
            state_data = response.json()
            
            # Extract season from state data
            season = state_data.get("season", "2025")
            logger.info(f"Current NBA season: {season}")
            return season
            
        except httpx.TimeoutException:
            logger.error("Timeout fetching NBA season, using default 2025")
            return "2025"
        except httpx.RequestError as e:
            logger.error(f"Request error fetching NBA season: {e}, using default 2025")
            return "2025"
        except Exception as e:
            logger.error(f"Unexpected error fetching NBA season: {e}, using default 2024")
            return "2024"

    async def get_nba_state(self) -> Optional[Dict]:
        """
        Get current NBA state from Sleeper API including week/leg information.
        
        Returns:
            Dict: NBA state data with season, week, leg, etc. or None on error
        """
        try:
            self._ensure_client()
            logger.info("Fetching NBA state from Sleeper")
            
            response = await self.client.get("/state/nba")
            
            if response.status_code == 404:
                logger.warning("NBA state not found")
                return None
            
            response.raise_for_status()
            state_data = response.json()
            
            logger.info(f"Current NBA state: season={state_data.get('season')}, week={state_data.get('week')}, leg={state_data.get('leg')}")
            return state_data
            
        except httpx.TimeoutException:
            logger.error("Timeout fetching NBA state")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching NBA state: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching NBA state: {e}")
            return None

    async def get_league_transactions(self, league_id: str, round: int) -> Optional[List[Dict]]:
        """
        Get transactions for a league by league ID and round.
        
        Args:
            league_id: Sleeper league ID
            round: Transaction round number
            
        Returns:
            List[Dict]: List of transaction data or empty list if not found
        """
        try:
            self._ensure_client()
            logger.info(f"Fetching Sleeper transactions for league {league_id}, round {round}")
            
            response = await self.client.get(f"/league/{league_id}/transactions/{round}")
            
            if response.status_code == 404:
                logger.info(f"No transactions found for league {league_id}, round {round}")
                return []
            
            response.raise_for_status()
            transactions_data = response.json()
            
            logger.info(f"Retrieved {len(transactions_data)} transactions for league {league_id}, round {round}")
            return transactions_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching transactions for league {league_id}, round {round}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching transactions for league {league_id}, round {round}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching transactions for league {league_id}, round {round}: {e}")
            return None

    async def get_league_matchups(self, league_id: str, week: int) -> Optional[List[Dict]]:
        """
        Get matchups for a league by league ID and week.
        
        Args:
            league_id: Sleeper league ID
            week: Matchup week number
            
        Returns:
            List[Dict]: List of matchup data or empty list if not found
        """
        try:
            logger.info(f"Fetching Sleeper matchups for league {league_id}, week {week}")
            
            response = await self.client.get(f"/league/{league_id}/matchups/{week}")
            
            if response.status_code == 404:
                logger.info(f"No matchups found for league {league_id}, week {week}")
                return []
            
            response.raise_for_status()
            matchups_data = response.json()
            
            logger.info(f"Retrieved {len(matchups_data)} matchups for league {league_id}, week {week}")
            return matchups_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching matchups for league {league_id}, week {week}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching matchups for league {league_id}, week {week}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching matchups for league {league_id}, week {week}: {e}")
            return None

    async def get_league_transactions_bulk(self, league_id: str, rounds: List[int]) -> Dict[int, List[Dict]]:
        """
        Fetch transactions for multiple rounds in sequence.
        
        Args:
            league_id: Sleeper league ID
            rounds: List of round numbers to fetch
            
        Returns:
            Dict: Dictionary mapping round number to transaction list
        """
        try:
            logger.info(f"Fetching bulk transactions for league {league_id}, rounds {rounds}")
            
            result = {}
            for round_num in rounds:
                transactions = await self.get_league_transactions(league_id, round_num)
                if transactions is not None:
                    result[round_num] = transactions
            
            logger.info(f"Retrieved transactions for {len(result)} rounds for league {league_id}")
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in bulk transaction fetch for league {league_id}: {e}")
            return {}

    async def get_league_matchups_bulk(self, league_id: str, weeks: List[int]) -> Dict[int, List[Dict]]:
        """
        Fetch matchups for multiple weeks in sequence.
        
        Args:
            league_id: Sleeper league ID
            weeks: List of week numbers to fetch
            
        Returns:
            Dict: Dictionary mapping week number to matchup list
        """
        try:
            logger.info(f"Fetching bulk matchups for league {league_id}, weeks {weeks}")
            
            result = {}
            for week_num in weeks:
                matchups = await self.get_league_matchups(league_id, week_num)
                if matchups is not None:
                    result[week_num] = matchups
            
            logger.info(f"Retrieved matchups for {len(result)} weeks for league {league_id}")
            return result
            
        except Exception as e:
            logger.error(f"Unexpected error in bulk matchup fetch for league {league_id}: {e}")
            return {}
    
    async def get_league_details(self, league_id: str) -> Optional[Dict]:
        """
        Get full league details including settings and metadata.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            Dict: Full league object including scoring_settings, roster_positions, settings, metadata
                  or None if not found
        """
        try:
            logger.info(f"Fetching league details for league {league_id}")
            
            response = await self.client.get(f"/league/{league_id}")
            
            if response.status_code == 404:
                logger.warning(f"League not found: {league_id}")
                return None
            
            response.raise_for_status()
            league_data = response.json()
            
            if not league_data:
                logger.warning(f"Empty league data for {league_id}")
                return None
            
            logger.info(f"Retrieved league details for {league_id}: {league_data.get('name', 'Unknown')}")
            return league_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching league details for {league_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching league details for {league_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching league details for {league_id}: {e}")
            return None
    
    async def get_league_users(self, league_id: str) -> Optional[List[Dict]]:
        """
        Get all users in a league with their display names and metadata.
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            List[Dict]: List of user objects with user_id, display_name, username, avatar, etc.
                       or None if not found
        """
        try:
            self._ensure_client()
            logger.info(f"Fetching league users for league {league_id}")
            
            response = await self.client.get(f"/league/{league_id}/users")
            
            if response.status_code == 404:
                logger.warning(f"League users not found: {league_id}")
                return None
            
            response.raise_for_status()
            users_data = response.json()
            
            logger.info(f"Retrieved {len(users_data)} users for league {league_id}")
            return users_data
            
        except httpx.TimeoutException:
            logger.error(f"Timeout fetching league users for {league_id}")
            return None
        except httpx.RequestError as e:
            logger.error(f"Request error fetching league users for {league_id}: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error fetching league users for {league_id}: {e}")
            return None
    
    async def get_league_info(self, league_id: str) -> Optional[Dict]:
        """
        Get league information (alias for get_league_details).
        
        Args:
            league_id: Sleeper league ID
            
        Returns:
            Dict with league settings, scoring, roster positions, etc.
        """
        return await self.get_league_details(league_id)
    
    async def get_roster(self, league_id: str, roster_id: int) -> Optional[Dict]:
        """
        Get a specific roster by ID.
        
        Args:
            league_id: Sleeper league ID
            roster_id: Roster ID to fetch
            
        Returns:
            Dict with roster data (players, settings, owner, etc.)
        """
        try:
            rosters = await self.get_league_rosters(league_id)
            if not rosters:
                return None
            
            for roster in rosters:
                if roster.get("roster_id") == roster_id:
                    return roster
            
            logger.warning(f"Roster {roster_id} not found in league {league_id}")
            return None
            
        except Exception as e:
            logger.error(f"Error fetching roster {roster_id} in league {league_id}: {e}")
            return None
    
    async def get_all_players(self) -> Dict[str, Dict]:
        """
        Get all NBA players (alias for get_nba_players).
        
        Returns:
            Dict mapping player_id to player data
        """
        return await self.get_nba_players() or {}
    
    async def get_transactions(self, league_id: str, round: Optional[int] = None) -> List[Dict]:
        """
        Get league transactions (alias for get_league_transactions).
        
        Args:
            league_id: Sleeper league ID
            round: Specific round/week (None for all recent transactions)
            
        Returns:
            List of transaction dicts
        """
        # If round not specified, get current week's transactions
        if round is None:
            # Get current NBA state to determine week
            try:
                nba_state = await self.get_nba_state()
                if nba_state:
                    round = nba_state.get("week", 1)
                else:
                    round = 1
            except:
                round = 1
        
        result = await self.get_league_transactions(league_id, round)
        return result if result is not None else []


# Singleton instance for dependency injection
sleeper_service = SleeperService()
