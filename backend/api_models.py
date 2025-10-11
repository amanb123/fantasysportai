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