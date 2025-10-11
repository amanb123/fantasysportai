"""
SQLModel database table definitions for the Fantasy Basketball League.
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum
from sqlmodel import SQLModel, Field, Relationship, Index
from sqlalchemy import Enum as SAEnum
from shared.models import PlayerResponse, PlayerStats, TeamResponse, TradeDecision, AgentMessage, NegotiationResult


class PositionEnum(str, Enum):
    """Basketball positions."""
    PG = "PG"  # Point Guard
    SG = "SG"  # Shooting Guard
    SF = "SF"  # Small Forward
    PF = "PF"  # Power Forward
    C = "C"    # Center


class TeamModel(SQLModel, table=True):
    """Team database model."""
    
    __tablename__ = "teams"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True, description="Team name")
    total_salary: int = Field(default=0, description="Total team salary")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    
    # Relationships
    players: List["PlayerModel"] = Relationship(back_populates="team")
    
    def to_pydantic(self) -> TeamResponse:
        """Convert to Pydantic model for API responses."""
        return TeamResponse(
            id=self.id,
            name=self.name,
            total_salary=self.total_salary,
            player_count=len(self.players) if self.players else 0
        )


class PlayerModel(SQLModel, table=True):
    """Player database model."""
    
    __tablename__ = "players"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(description="Player name")
    team_id: int = Field(foreign_key="teams.id", description="Team identifier")
    position: PositionEnum = Field(sa_type=SAEnum(PositionEnum, name="position_enum"), description="Player position")
    salary: int = Field(description="Player salary in dollars")
    
    # Statistical fields
    points_per_game: float = Field(description="Average points per game")
    rebounds_per_game: float = Field(description="Average rebounds per game")
    assists_per_game: float = Field(description="Average assists per game")
    steals_per_game: float = Field(description="Average steals per game")
    blocks_per_game: float = Field(description="Average blocks per game")
    turnovers_per_game: float = Field(description="Average turnovers per game")
    field_goal_percentage: float = Field(description="Field goal percentage")
    three_point_percentage: float = Field(description="Three-point percentage")
    
    # Relationships
    team: Optional[TeamModel] = Relationship(back_populates="players")
    
    def to_pydantic(self) -> PlayerResponse:
        """Convert to Pydantic model for API responses."""
        stats = PlayerStats(
            points_per_game=self.points_per_game,
            rebounds_per_game=self.rebounds_per_game,
            assists_per_game=self.assists_per_game,
            steals_per_game=self.steals_per_game,
            blocks_per_game=self.blocks_per_game,
            turnovers_per_game=self.turnovers_per_game,
            field_goal_percentage=self.field_goal_percentage,
            three_point_percentage=self.three_point_percentage
        )
        
        return PlayerResponse(
            id=self.id,
            name=self.name,
            team_id=self.team_id,
            position=self.position.value,
            salary=self.salary,
            stats=stats
        )


class TradePreferenceModel(SQLModel, table=True):
    """Trade preference database model."""
    
    __tablename__ = "trade_preferences"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    team_id: int = Field(foreign_key="teams.id", description="Team identifier")
    improve_rebounds: bool = Field(description="Focus on improving rebounding")
    improve_assists: bool = Field(description="Focus on improving assists")
    improve_scoring: bool = Field(description="Focus on improving scoring")
    reduce_turnovers: bool = Field(description="Focus on reducing turnovers")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")


class TradeModel(SQLModel, table=True):
    """Trade database model."""
    
    __tablename__ = "trades"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, description="Unique session identifier")
    status: str = Field(description="Trade status")
    team1_id: int = Field(description="First team identifier")
    team2_id: int = Field(description="Second team identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")


# Trade Session Models

class TradeSessionStatus(str, Enum):
    """Trade session status values."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed" 
    FAILED = "failed"


class TradeSessionModel(SQLModel, table=True):
    """Trade session database model for multi-agent negotiations."""
    
    __tablename__ = "trade_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True, description="Unique session identifier")
    status: TradeSessionStatus = Field(default=TradeSessionStatus.PENDING, description="Session status")
    
    # Negotiation details
    initiating_team_id: int = Field(foreign_key="teams.id", description="Team that started negotiation")
    target_team_ids: str = Field(description="JSON array of target team IDs")
    current_turn: int = Field(default=0, description="Current negotiation turn")
    max_turns: int = Field(default=10, description="Maximum allowed turns")
    
    # Session timing
    started_at: datetime = Field(default_factory=datetime.utcnow, description="When session started")
    completed_at: Optional[datetime] = Field(None, description="When session completed")
    
    # Results
    consensus_reached: bool = Field(default=False, description="Whether consensus was reached")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    
    # Relationships
    messages: List["ConversationMessageModel"] = Relationship(back_populates="session")
    result: Optional["TradeResultModel"] = Relationship(back_populates="session")
    
    def to_pydantic_status(self):
        """Convert to status response model."""
        from backend.api_models import TradeNegotiationStatus
        
        progress = min((self.current_turn / self.max_turns) * 100, 100.0)
        
        return TradeNegotiationStatus(
            session_id=self.session_id,
            status=self.status.value,
            progress=progress,
            current_turn=self.current_turn,
            max_turns=self.max_turns,
            message=self._get_status_message(),
            started_at=self.started_at,
            completed_at=self.completed_at
        )
    
    def _get_status_message(self) -> str:
        """Generate appropriate status message."""
        if self.status == TradeSessionStatus.PENDING:
            return "Trade negotiation is starting..."
        elif self.status == TradeSessionStatus.IN_PROGRESS:
            return f"Negotiation in progress - turn {self.current_turn}/{self.max_turns}"
        elif self.status == TradeSessionStatus.COMPLETED:
            if self.consensus_reached:
                return "Trade negotiation completed successfully"
            else:
                return "Trade negotiation completed without consensus"
        elif self.status == TradeSessionStatus.FAILED:
            return f"Trade negotiation failed: {self.error_message or 'Unknown error'}"
        return "Unknown status"


class ConversationMessageModel(SQLModel, table=True):
    """Agent conversation message storage."""
    
    __tablename__ = "conversation_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="trade_sessions.id", description="Trade session ID")
    agent_name: str = Field(description="Agent that sent the message")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    turn_number: int = Field(description="Turn number when message was sent")
    
    # Relationships
    session: TradeSessionModel = Relationship(back_populates="messages")
    
    def to_pydantic(self) -> AgentMessage:
        """Convert to Pydantic model."""
        return AgentMessage(
            agent_name=self.agent_name,
            content=self.content,
            timestamp=self.timestamp
        )


class TradeResultModel(SQLModel, table=True):
    """Final trade negotiation result storage."""
    
    __tablename__ = "trade_results"
    
    id: Optional[int] = Field(default=None, primary_key=True) 
    session_id: int = Field(foreign_key="trade_sessions.id", unique=True, description="Trade session ID")
    
    # Trade decision details (JSON serialized)
    approved: bool = Field(description="Whether trade was approved")
    trade_proposal_json: Optional[str] = Field(None, description="JSON serialized trade proposal")
    commissioner_notes: Optional[str] = Field(None, description="Commissioner approval/rejection notes")
    
    # Negotiation summary
    total_turns: int = Field(description="Total number of turns")
    consensus_reached: bool = Field(description="Whether agents reached consensus")
    
    # Timestamps
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Result creation timestamp")
    
    # Relationships
    session: TradeSessionModel = Relationship(back_populates="result")
    
    def to_pydantic(self) -> NegotiationResult:
        """Convert to Pydantic model."""
        import json
        
        # Parse TradeDecision from stored JSON (now uses full TradeDecision schema)
        trade_decision = None
        if self.trade_proposal_json:
            try:
                decision_data = json.loads(self.trade_proposal_json)
                # trade_proposal_json now contains the full TradeDecision, not just trade_proposal
                trade_decision = TradeDecision(**decision_data)
            except (json.JSONDecodeError, TypeError, ValueError):
                pass
        
        # Get conversation messages through session
        conversation_history = [msg.to_pydantic() for msg in self.session.messages] if self.session else []
        
        return NegotiationResult(
            trade_decision=trade_decision,
            conversation_history=conversation_history,
            total_turns=self.total_turns,
            success=self.consensus_reached
        )


# Add indexes for performance
PlayerModel.__table_args__ = (
    Index("ix_players_team_id", "team_id"),
    Index("ix_players_position", "position"),
)

TradeSessionModel.__table_args__ = (
    Index("ix_trade_sessions_session_id", "session_id"),
    Index("ix_trade_sessions_status", "status"),
    Index("ix_trade_sessions_started_at", "started_at"),
)

ConversationMessageModel.__table_args__ = (
    Index("ix_conversation_messages_session_id", "session_id"),
    Index("ix_conversation_messages_timestamp", "timestamp"),
)