from datetime import datetime
from typing import List
from typing import Dict
from typing import Optional
from pydantic import Field
from pydantic import BaseModel
# ===== Roster Ranking Shared Models =====

class PlayerBreakdownItem(BaseModel):
    """Individual player contribution breakdown."""
    name: str = Field(..., description="Player name")
    position: str = Field(..., description="Player position")
    team: str = Field(..., description="Player NBA team")
    total_points: float = Field(..., description="Total fantasy points contributed")
    category_contributions: Dict[str, float] = Field(..., description="Points by category")
    games_played: int = Field(..., description="Games played in season")
    season: str = Field(..., description="Season (e.g., '2024-25', '2025-26')")

class ExcludedPlayerItem(BaseModel):
    """Excluded player information."""
    name: str = Field(..., description="Player name")
    reason: str = Field(..., description="Reason for exclusion (e.g., 'Injured', 'No stats')")

class RosterRankingItem(BaseModel):
    """League roster ranking item."""
    rank: int = Field(..., description="Roster rank position")
    roster_id: int = Field(..., description="Sleeper roster ID")
    owner_id: Optional[str] = Field(None, description="Owner's Sleeper user ID")
    owner_name: str = Field(..., description="Owner display name")
    base_fantasy_points: float = Field(..., description="Base fantasy points before win/loss adjustment")
    total_fantasy_points: float = Field(..., description="Total fantasy points (Power Score) after win/loss adjustment")
    wins: int = Field(..., description="Season wins")
    losses: int = Field(..., description="Season losses")
    win_multiplier: float = Field(..., description="Win/loss multiplier applied to base points")
    win_bonus: float = Field(..., description="Points added from wins (base × 10% × wins)")
    loss_penalty: float = Field(..., description="Points removed from losses (base × 5% × losses)")
    category_scores: Dict[str, float] = Field(..., description="Points by category")
    category_percentiles: Dict[str, float] = Field(..., description="Percentile ranks (0-100)")
    player_breakdown: List[PlayerBreakdownItem] = Field(default_factory=list, description="Per-player contribution details")
    active_players: int = Field(0, description="Count of active (non-injured) players")
    excluded_players: List[ExcludedPlayerItem] = Field(default_factory=list, description="Injured/unavailable players")

class LeagueRankings(BaseModel):
    """League-wide roster rankings."""
    league_id: str = Field(..., description="League identifier")
    league_name: str = Field(..., description="League name")
    rankings: List[RosterRankingItem] = Field(..., description="Ranked rosters")
    total_rosters: int = Field(..., description="Total roster count")
    scoring_settings: Dict[str, float] = Field(..., description="League scoring settings")
    last_updated: datetime = Field(..., description="Calculation timestamp")
"""
Pydantic models for API data transfer in the Fantasy Basketball League.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class PlayerStats(BaseModel):
    """Player statistical data."""
    
    points_per_game: float = Field(..., description="Average points per game")
    rebounds_per_game: float = Field(..., description="Average rebounds per game")
    assists_per_game: float = Field(..., description="Average assists per game")
    steals_per_game: float = Field(..., description="Average steals per game")
    blocks_per_game: float = Field(..., description="Average blocks per game")
    turnovers_per_game: float = Field(..., description="Average turnovers per game")
    field_goal_percentage: float = Field(..., description="Field goal percentage (0.0-1.0)")
    three_point_percentage: float = Field(..., description="Three-point percentage (0.0-1.0)")


class PlayerResponse(BaseModel):
    """Player data for API responses."""
    
    id: int = Field(..., description="Unique player identifier")
    name: str = Field(..., description="Player name")
    team_id: int = Field(..., description="Team identifier")
    position: str = Field(..., description="Player position (PG, SG, SF, PF, C)")
    salary: int = Field(..., description="Player salary in dollars")
    stats: PlayerStats = Field(..., description="Player statistical data")


class TeamResponse(BaseModel):
    """Team data for API responses."""
    
    id: int = Field(..., description="Unique team identifier")
    name: str = Field(..., description="Team name")
    total_salary: int = Field(..., description="Total team salary in dollars")
    player_count: int = Field(..., description="Number of players on team")


class UserPublicResponse(BaseModel):
    """Safe user data for API responses (excluding password)."""
    
    id: int = Field(..., description="Unique user identifier")
    email: str = Field(..., description="User email address")
    sleeper_username: Optional[str] = Field(None, description="Sleeper username")
    sleeper_user_id: Optional[str] = Field(None, description="Sleeper user ID")
    is_active: bool = Field(..., description="Account active status")
    created_at: datetime = Field(..., description="Account creation timestamp")


class TradePreferenceRequest(BaseModel):
    """Request model for trade preferences."""
    
    team_id: int = Field(..., description="ID of the team initiating the trade")
    target_team_ids: List[int] = Field(..., description="List of target team IDs for potential trades")
    desired_positions: List[str] = Field(default_factory=list, description="Desired player positions")
    budget_range: Dict[str, int] = Field(default_factory=dict, description="Budget range for trades")
    notes: str = Field(default="", description="Additional trade notes or preferences")


class AgentMessage(BaseModel):
    """Agent message in trade negotiation."""
    
    agent_name: str = Field(..., description="Name of the agent")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")


class TradeProposal(BaseModel):
    """Trade proposal between teams."""
    
    offering_team_id: int = Field(..., description="Team making the offer")
    receiving_team_id: int = Field(..., description="Team receiving the offer")
    offered_player_ids: List[int] = Field(..., description="Players being offered")
    requested_player_ids: List[int] = Field(..., description="Players being requested")


class TradeDecision(BaseModel):
    """Final trade decision from negotiation."""
    
    approved: bool = Field(..., description="Whether the trade was approved")
    offering_team_id: int = Field(..., description="Team making the offer")
    receiving_team_id: int = Field(..., description="Team receiving the offer")
    traded_players_out: List[PlayerResponse] = Field(..., description="Players leaving offering team")
    traded_players_in: List[PlayerResponse] = Field(..., description="Players joining offering team")
    consensus_reached: bool = Field(..., description="Whether agents reached consensus")
    rejection_reasons: List[str] = Field(default_factory=list, description="Reasons for trade rejection")
    commissioner_notes: str = Field(default="", description="Commissioner's notes")


class NegotiationResult(BaseModel):
    """Result of trade negotiation."""
    
    trade_decision: TradeDecision = Field(..., description="Final trade decision")
    conversation_history: List[AgentMessage] = Field(..., description="Full conversation history")
    total_turns: int = Field(..., description="Number of negotiation turns")
    success: bool = Field(..., description="Whether negotiation completed successfully")


# ===== NBA Stats Shared Models =====

class GameSchedulePublicResponse(BaseModel):
    """Public response model for NBA game schedule data (simplified for frontend)."""
    
    game_id: str = Field(..., description="Unique game identifier")
    game_date: str = Field(..., description="Game date (YYYY-MM-DD)")
    game_time_utc: str = Field(..., description="Game time in UTC (HH:MM:SS)")
    home_team_tricode: str = Field(..., description="Home team tricode (e.g., 'LAL')")
    away_team_tricode: str = Field(..., description="Away team tricode (e.g., 'BOS')")
    home_team_score: Optional[int] = Field(None, description="Home team score")
    away_team_score: Optional[int] = Field(None, description="Away team score")
    game_status: str = Field(..., description="Game status (scheduled, in_progress, final)")
    game_status_text: Optional[str] = Field(None, description="Human-readable status")
    arena_name: Optional[str] = Field(None, description="Arena name")


class PlayerBioResponse(BaseModel):
    """Public response model for player biographical information (simplified for frontend)."""
    
    player_id: str = Field(..., description="Sleeper player ID")
    full_name: Optional[str] = Field(None, description="Player full name")
    position: Optional[str] = Field(None, description="Position")
    jersey: Optional[str] = Field(None, description="Jersey number")
    height_inches: Optional[int] = Field(None, description="Height in inches")
    weight_pounds: Optional[int] = Field(None, description="Weight in pounds")
    birthdate: Optional[str] = Field(None, description="Birthdate (YYYY-MM-DD)")
    country: Optional[str] = Field(None, description="Country of birth")
    team_name: Optional[str] = Field(None, description="Current team name")
    team_abbreviation: Optional[str] = Field(None, description="Current team abbreviation")
    draft_year: Optional[int] = Field(None, description="Draft year")
    draft_round: Optional[int] = Field(None, description="Draft round")
    draft_number: Optional[int] = Field(None, description="Draft number")
    injury_status: Optional[str] = Field(None, description="Injury status")
    injury_notes: Optional[str] = Field(None, description="Injury notes")


# ===== Roster Chat Shared Models =====

class RosterChatMessage(BaseModel):
    """Roster chat message model."""
    
    role: str = Field(..., description="Message role (user or assistant)")
    content: str = Field(..., description="Message content")
    timestamp: datetime = Field(..., description="Message timestamp")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Optional metadata (tokens, historical_stats_fetched, etc.)")


class RosterChatSession(BaseModel):
    """Roster chat session model."""
    
    session_id: str = Field(..., description="Unique session identifier (UUID)")
    league_id: str = Field(..., description="Sleeper league ID")
    roster_id: int = Field(..., description="Sleeper roster ID")
    sleeper_user_id: str = Field(..., description="Sleeper user ID")
    created_at: datetime = Field(..., description="Session creation timestamp")
    last_message_at: Optional[datetime] = Field(None, description="Last message timestamp")
    message_count: int = Field(..., description="Number of messages in session")
    status: str = Field(..., description="Session status (active, archived)")