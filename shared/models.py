"""
Pydantic models for API data transfer in the Fantasy Basketball League.
"""

from typing import List, Optional, Dict
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