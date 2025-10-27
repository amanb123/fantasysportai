# ===== Imports =====
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from shared.models import RosterRankingItem
# ===== Roster Ranking API Models =====

class RosterRankingResponse(BaseModel):
    league_id: str = Field(..., description="Sleeper league ID")
    league_name: str = Field(..., description="League name")
    rankings: List[RosterRankingItem] = Field(..., description="Ranked rosters (sorted by total_fantasy_points descending)")
    total_rosters: int = Field(..., description="Total number of rosters in league")
    scoring_settings: Dict[str, float] = Field(..., description="League scoring settings for reference")
    last_updated: str = Field(..., description="ISO timestamp of when rankings were calculated")
    cached: bool = Field(..., description="Whether result came from cache")

class RosterRankingCacheStatus(BaseModel):
    league_id: str = Field(..., description="League identifier")
    cached: bool = Field(..., description="Whether rankings are cached")
    ttl_remaining: Optional[int] = Field(None, description="Remaining TTL in seconds")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last calculation")
"""
FastAPI request/response models for the Fantasy Basketball League API.
"""

from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field
from shared.models import TeamResponse, PlayerResponse, TradePreferenceRequest, TradeDecision, AgentMessage


class ErrorResponse(BaseModel):
    """Standard error response model."""
    
    error: str = Field(..., description="Error type or code")
    message: str = Field(..., description="Human-readable error message")
    details: Dict[str, Any] = Field(default_factory=dict, description="Additional error details")


class TeamListResponse(BaseModel):
    """Response model for team list endpoints."""
    
    teams: List[TeamResponse] = Field(..., description="List of teams")
    total_count: int = Field(..., description="Total number of teams")


class PlayerListResponse(BaseModel):
    """Response model for player list endpoints."""
    
    players: List[PlayerResponse] = Field(..., description="List of players")
    team_name: str = Field(..., description="Name of the team")


class HealthResponse(BaseModel):
    """Health check response model."""
    
    status: str = Field(..., description="Service status")
    database_connected: bool = Field(..., description="Database connection status")
    timestamp: str = Field(..., description="Current timestamp")
    version: str = Field(..., description="API version")


class TradeStartRequest(BaseModel):
    """Request to start trade negotiation."""
    
    trade_preference: TradePreferenceRequest = Field(..., description="Trade preferences for initiating team")


class TradeStartResponse(BaseModel):
    """Response from trade start endpoint."""
    
    session_id: str = Field(..., description="Unique trade session identifier")
    status: str = Field(..., description="Initial session status")
    message: str = Field(..., description="Status message")


class TradeNegotiationStatus(BaseModel):
    """Trade negotiation status response."""
    
    session_id: str = Field(..., description="Trade session identifier")
    status: str = Field(..., description="Current status (pending/in_progress/completed/failed)")
    progress: float = Field(..., description="Progress percentage (0-100)")
    current_turn: int = Field(..., description="Current negotiation turn")
    max_turns: int = Field(..., description="Maximum allowed turns")
    message: str = Field(..., description="Current status message")
    started_at: datetime = Field(..., description="When negotiation started")
    completed_at: Optional[datetime] = Field(None, description="When negotiation completed")


class TradeResultResponse(BaseModel):
    """Trade negotiation result response."""
    
    session_id: str = Field(..., description="Trade session identifier")
    status: str = Field(..., description="Final session status")
    trade_decision: Optional[TradeDecision] = Field(None, description="Final trade decision")
    conversation: List[AgentMessage] = Field(..., description="Full conversation history")
    total_turns: int = Field(..., description="Number of negotiation turns")
    consensus_reached: bool = Field(..., description="Whether agents reached consensus")
    error: Optional[str] = Field(None, description="Error message if failed")


class SleeperSyncResponse(BaseModel):
    """Response for Sleeper player sync operation."""
    
    success: bool = Field(..., description="Whether sync succeeded")
    message: str = Field(..., description="Status message")
    player_count: Optional[int] = Field(None, description="Number of players cached")
    cache_ttl: Optional[int] = Field(None, description="Cache TTL in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")


class SleeperCacheStatus(BaseModel):
    """Cache status response for Sleeper player data."""
    
    exists: bool = Field(..., description="Whether cache exists")
    ttl_remaining: Optional[int] = Field(None, description="Remaining TTL in seconds")
    player_count: Optional[int] = Field(None, description="Number of cached players")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last update")
    is_valid: bool = Field(..., description="Whether cache is fresh and valid")


class SleeperPlayerResponse(BaseModel):
    """Single player response from Sleeper cache."""
    
    player_id: str = Field(..., description="Sleeper player ID")
    name: str = Field(..., description="Full player name")
    team: Optional[str] = Field(None, description="NBA team code")
    positions: List[str] = Field(..., description="Fantasy positions")
    status: Optional[str] = Field(None, description="Player status")
    injury_status: Optional[str] = Field(None, description="Injury status")


class SleeperLeagueResponse(BaseModel):
    """League data from Sleeper."""
    
    league_id: str = Field(..., description="Sleeper league ID")
    name: str = Field(..., description="League name")
    season: str = Field(..., description="Season year")
    total_rosters: int = Field(..., description="Number of teams")
    sport: str = Field(..., description="Sport type (nba)")
    status: Optional[str] = Field(None, description="League status")
    settings: Optional[Dict[str, Any]] = Field(None, description="League settings")


class SleeperRosterResponse(BaseModel):
    """Roster data from Sleeper."""
    
    roster_id: int = Field(..., description="Roster ID")
    owner_id: Optional[str] = Field(None, description="Sleeper user ID who owns this roster (can be None for orphaned teams)")
    league_id: str = Field(..., description="League ID")
    players: List[str] = Field(..., description="Array of player IDs on roster")
    starters: Optional[List[str]] = Field(None, description="Starting lineup player IDs")
    settings: Optional[Dict[str, Any]] = Field(None, description="Roster settings (wins, losses, fpts, etc.)")


class SleeperUserSessionRequest(BaseModel):
    """Request to start Sleeper session."""
    
    sleeper_username: str = Field(..., description="Sleeper username to look up")


class SleeperUserSessionResponse(BaseModel):
    """Response with user session data."""
    
    user_id: str = Field(..., description="Sleeper user ID")
    username: str = Field(..., description="Sleeper username")
    display_name: Optional[str] = Field(None, description="Display name")
    avatar: Optional[str] = Field(None, description="Avatar URL")


class SleeperTransactionResponse(BaseModel):
    """Transaction data from Sleeper."""
    
    type: str = Field(..., description="Transaction type (trade, waiver, free_agent)")
    status: str = Field(..., description="Transaction status (complete, pending)")
    roster_ids: List[int] = Field(..., description="Rosters involved in transaction")
    players: Optional[Dict[str, Any]] = Field(None, description="Player movements")
    draft_picks: Optional[List[Dict]] = Field(None, description="Draft picks involved")
    created: int = Field(..., description="Unix timestamp of creation")
    settings: Optional[Dict[str, Any]] = Field(None, description="Transaction settings")


class SleeperMatchupResponse(BaseModel):
    """Matchup data from Sleeper."""
    
    roster_id: int = Field(..., description="Roster ID")
    matchup_id: int = Field(..., description="Matchup identifier")
    points: Optional[float] = Field(None, description="Points scored")
    starters: Optional[List[str]] = Field(None, description="Starting player IDs")
    players: Optional[List[str]] = Field(None, description="All player IDs in lineup")
    custom_points: Optional[float] = Field(None, description="Custom scoring points")


class LeagueDataCacheStatus(BaseModel):
    """Cache status for league data."""
    
    league_id: str = Field(..., description="League identifier")
    rosters_cached: bool = Field(..., description="Whether rosters are cached")
    rosters_ttl: Optional[int] = Field(None, description="Remaining TTL for rosters in seconds")
    transactions_cached: bool = Field(..., description="Whether transactions are cached")
    transactions_rounds: Optional[List[int]] = Field(None, description="Cached round numbers")
    matchups_cached: bool = Field(..., description="Whether matchups are cached")
    matchups_weeks: Optional[List[int]] = Field(None, description="Cached week numbers")
    last_updated: Optional[str] = Field(None, description="ISO timestamp of last update")


class LeagueDataRefreshResponse(BaseModel):
    """Response for refresh operations."""
    
    success: bool = Field(..., description="Overall success status")
    league_id: str = Field(..., description="League identifier")
    rosters_updated: bool = Field(..., description="Whether rosters were updated")
    transactions_updated: bool = Field(..., description="Whether transactions were updated")
    matchups_updated: bool = Field(..., description="Whether matchups were updated")
    message: str = Field(..., description="Status message")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")


# ===== NBA Stats API Models =====

class GameScheduleResponse(BaseModel):
    """Response model for game schedule data."""
    
    game_id: str = Field(..., description="Unique game identifier")
    season: str = Field(..., description="Season year (e.g., '2024')")
    game_date: str = Field(..., description="Game date (YYYY-MM-DD)")
    game_time_utc: str = Field(..., description="Game time in UTC (HH:MM:SS)")
    home_team_id: int = Field(..., description="Home team ID")
    home_team_tricode: str = Field(..., description="Home team tricode (e.g., 'LAL')")
    home_team_score: Optional[int] = Field(None, description="Home team score")
    away_team_id: int = Field(..., description="Away team ID")
    away_team_tricode: str = Field(..., description="Away team tricode (e.g., 'BOS')")
    away_team_score: Optional[int] = Field(None, description="Away team score")
    game_status: str = Field(..., description="Game status (scheduled, in_progress, final)")
    game_status_text: Optional[str] = Field(None, description="Human-readable status")
    period: Optional[int] = Field(None, description="Current period (1-4, 5+ for OT)")
    game_clock: Optional[str] = Field(None, description="Game clock (e.g., 'PT12M34.5S')")
    arena_name: Optional[str] = Field(None, description="Arena name")
    arena_city: Optional[str] = Field(None, description="Arena city")


class PlayerInfoResponse(BaseModel):
    """Response model for player biographical information."""
    
    sleeper_player_id: str = Field(..., description="Sleeper player ID")
    nba_person_id: Optional[int] = Field(None, description="NBA person ID")
    display_first_last: Optional[str] = Field(None, description="Player full name")
    first_name: Optional[str] = Field(None, description="First name")
    last_name: Optional[str] = Field(None, description="Last name")
    birthdate: Optional[str] = Field(None, description="Birthdate (YYYY-MM-DD)")
    country: Optional[str] = Field(None, description="Country of birth")
    height_inches: Optional[int] = Field(None, description="Height in inches")
    weight_pounds: Optional[int] = Field(None, description="Weight in pounds")
    jersey: Optional[str] = Field(None, description="Jersey number")
    position: Optional[str] = Field(None, description="Position")
    draft_year: Optional[int] = Field(None, description="Draft year")
    draft_round: Optional[int] = Field(None, description="Draft round")
    draft_number: Optional[int] = Field(None, description="Draft number")
    team_id: Optional[int] = Field(None, description="Current team ID")
    team_name: Optional[str] = Field(None, description="Current team name")
    team_abbreviation: Optional[str] = Field(None, description="Current team abbreviation")
    injury_status: Optional[str] = Field(None, description="Injury status from Sleeper")
    injury_notes: Optional[str] = Field(None, description="Injury notes from Sleeper")


class NBAScheduleSyncResponse(BaseModel):
    """Response model for schedule sync operations."""
    
    success: bool = Field(..., description="Whether sync was successful")
    games_synced: int = Field(..., description="Number of games synced")
    season: str = Field(..., description="Season year")
    cache_updated: bool = Field(..., description="Whether cache was updated")
    database_updated: bool = Field(..., description="Whether database was updated")
    message: str = Field(..., description="Status message")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")


class NBAPlayerInfoSyncResponse(BaseModel):
    """Response model for player info sync operations."""
    
    success: bool = Field(..., description="Whether sync was successful")
    players_synced: int = Field(..., description="Number of players synced")
    cache_updated: bool = Field(..., description="Whether cache was updated")
    database_updated: bool = Field(..., description="Whether database was updated")
    message: str = Field(..., description="Status message")
    errors: Optional[List[str]] = Field(None, description="Any errors encountered")
    failed_players: Optional[List[str]] = Field(None, description="Player IDs that failed to sync")


class NBACacheStatusResponse(BaseModel):
    """Response model for NBA cache status."""
    
    schedule_cached: bool = Field(..., description="Whether schedule is cached")
    schedule_games_count: int = Field(..., description="Number of games in cache")
    schedule_last_updated: Optional[str] = Field(None, description="Last schedule update")
    player_info_cached: bool = Field(..., description="Whether player info is cached")
    player_info_count: int = Field(..., description="Number of players in cache")
    player_info_last_updated: Optional[str] = Field(None, description="Last player info update")
    cache_stats: Dict[str, Any] = Field(default_factory=dict, description="Additional cache statistics")


# Roster Chat Models

class RosterChatStartRequest(BaseModel):
    """Request to start roster chat session."""
    
    league_id: str = Field(..., description="Sleeper league ID")
    roster_id: int = Field(..., description="Sleeper roster ID")
    sleeper_user_id: str = Field(..., description="Sleeper user ID")
    initial_message: Optional[str] = Field(None, description="Optional first message from user")


class RosterChatStartResponse(BaseModel):
    """Response from roster chat start."""
    
    session_id: str = Field(..., description="Unique chat session identifier (UUID)")
    status: str = Field(..., description="Session status")
    message: str = Field(..., description="Status message")
    initial_response: Optional[str] = Field(None, description="Response to initial_message if provided")


class RosterChatMessageRequest(BaseModel):
    """Request to send chat message."""
    
    message: str = Field(..., min_length=1, max_length=1000, description="User's message/question")
    include_historical: Optional[bool] = Field(True, description="Whether to fetch historical stats if needed")


class RosterChatMessageResponse(BaseModel):
    """Response containing chat message."""
    
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: str = Field(..., description="ISO timestamp")
    session_id: str = Field(..., description="Chat session ID")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Metadata (tokens used, historical stats fetched, etc.)")


class RosterChatHistoryResponse(BaseModel):
    """Response containing chat history."""
    
    session_id: str = Field(..., description="Chat session ID")
    messages: List[RosterChatMessageResponse] = Field(..., description="Message history")
    league_id: str = Field(..., description="League ID")
    roster_id: int = Field(..., description="Roster ID")
    created_at: str = Field(..., description="Session creation timestamp")
    last_message_at: Optional[str] = Field(None, description="Last message timestamp")
    message_count: int = Field(..., description="Total message count")


class RosterChatSessionListResponse(BaseModel):
    """Response containing list of chat sessions."""
    
    sessions: List[Dict[str, Any]] = Field(..., description="List of chat sessions with metadata")
    total_count: int = Field(..., description="Total number of sessions")

# ============================================================================
# Trade Assistant API Models
# ============================================================================

class RecentTradeResponse(BaseModel):
    """Response model for recent completed trades."""
    
    transaction_id: str = Field(..., description="Sleeper transaction ID")
    status: str = Field(..., description="Transaction status (complete)")
    created: int = Field(..., description="Unix timestamp of transaction")
    roster_ids: List[int] = Field(..., description="Roster IDs involved in trade")
    adds: Optional[Dict[str, int]] = Field(None, description="Players added: {player_id: roster_id}")
    drops: Optional[Dict[str, int]] = Field(None, description="Players dropped: {player_id: roster_id}")
    description: str = Field(..., description="Human-readable trade description")


class TradeAnalysisStartRequest(BaseModel):
    """Request to start trade analysis."""
    
    league_id: str = Field(..., min_length=1, description="Sleeper league ID")
    user_id: Optional[int] = Field(None, description="User ID from database (optional)")
    sleeper_user_id: str = Field(..., min_length=1, description="Sleeper user ID")
    user_roster_id: int = Field(..., gt=0, description="User's roster ID")
    opponent_roster_id: int = Field(..., gt=0, description="Opponent's roster ID")
    user_players_out: List[str] = Field(..., min_items=1, max_items=5, description="Player IDs user is trading away (max 5)")
    user_players_in: List[str] = Field(..., min_items=1, max_items=5, description="Player IDs user is receiving (max 5)")


class TradeAnalysisStartResponse(BaseModel):
    """Response from starting trade analysis."""
    
    session_id: str = Field(..., description="Trade analysis session UUID")
    status: str = Field(..., description="Analysis status (analyzing)")
    message: str = Field(..., description="Status message")


class TradeAnalysisResultResponse(BaseModel):
    """Response containing trade analysis result."""
    
    session_id: str = Field(..., description="Trade analysis session UUID")
    status: str = Field(..., description="Analysis status")
    analysis_result: Optional[Dict[str, Any]] = Field(None, description="AI analysis result")
    favorability_score: Optional[float] = Field(None, ge=0, le=100, description="Favorability score 0-100")
    simulation_result: Optional[Dict[str, Any]] = Field(None, description="Matchup simulation result")
    created_at: str = Field(..., description="Session creation timestamp")
    completed_at: Optional[str] = Field(None, description="Analysis completion timestamp")


class TradeSimulationRequest(BaseModel):
    """Request to simulate matchup with trade."""
    
    session_id: str = Field(..., min_length=1, description="Trade analysis session UUID")
    weeks: int = Field(3, ge=1, le=10, description="Number of weeks to simulate (default 3)")


class TradeSimulationResponse(BaseModel):
    """Response from matchup simulation."""
    
    session_id: str = Field(..., description="Trade analysis session UUID")
    simulation_result: Dict[str, Any] = Field(..., description="Simulation result with win probabilities")
    message: str = Field(..., description="Status message")


class TradeAnalysisSessionListResponse(BaseModel):
    """Response containing list of user's trade analyses."""
    
    sessions: List[Dict[str, Any]] = Field(..., description="List of trade analysis sessions")
    total_count: int = Field(..., description="Total number of sessions")
