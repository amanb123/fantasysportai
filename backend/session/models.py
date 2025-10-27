"""
SQLModel database table definitions for the Fantasy Basketball League.
"""

from datetime import datetime, date
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


class UserModel(SQLModel, table=True):
    """User database model."""
    
    __tablename__ = "users"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, description="User email for login")
    hashed_password: str = Field(description="Bcrypt hashed password")
    sleeper_username: Optional[str] = Field(default=None, description="Sleeper username")
    sleeper_user_id: Optional[str] = Field(default=None, index=True, description="Sleeper user ID")
    is_active: bool = Field(default=True, description="Account active status")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Account creation timestamp")
    last_login: Optional[datetime] = Field(default=None, description="Last login timestamp")
    
    # Refresh token fields
    hashed_refresh_token: Optional[str] = Field(default=None, description="Hashed refresh token")
    refresh_token_expires_at: Optional[datetime] = Field(default=None, description="Refresh token expiry")
    
    # Relationships
    trade_sessions: List["TradeSessionModel"] = Relationship(back_populates="user")
    roster_chat_sessions: List["RosterChatSessionModel"] = Relationship(back_populates="user")
    
    def to_pydantic(self):
        """Convert to safe user response (excluding password)."""
        return {
            "id": self.id,
            "email": self.email,
            "sleeper_username": self.sleeper_username,
            "sleeper_user_id": self.sleeper_user_id,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "last_login": self.last_login
        }


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
    user_id: int = Field(foreign_key="users.id", description="User who created the session")
    
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
    user: Optional["UserModel"] = Relationship(back_populates="trade_sessions")
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
UserModel.__table_args__ = (
    Index("ix_users_email", "email"),
    Index("ix_users_sleeper_user_id", "sleeper_user_id"),
)

PlayerModel.__table_args__ = (
    Index("ix_players_team_id", "team_id"),
    Index("ix_players_position", "position"),
)

TradeSessionModel.__table_args__ = (
    Index("ix_trade_sessions_session_id", "session_id"),
    Index("ix_trade_sessions_status", "status"),
    Index("ix_trade_sessions_started_at", "started_at"),
    Index("ix_trade_sessions_user_id", "user_id"),
)

ConversationMessageModel.__table_args__ = (
    Index("ix_conversation_messages_session_id", "session_id"),
    Index("ix_conversation_messages_timestamp", "timestamp"),
)


class GameScheduleModel(SQLModel, table=True):
    """NBA game schedule database model."""
    
    __tablename__ = "game_schedules"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: str = Field(unique=True, index=True, description="NBA game ID (e.g., '0022400001')")
    game_date: date = Field(index=True, description="Date of the game")
    game_time_utc: datetime = Field(description="Game start time in UTC")
    home_team_id: str = Field(description="NBA team ID for home team")
    home_team_name: str = Field(description="Home team name")
    home_team_tricode: str = Field(description="Home team abbreviation (e.g., 'LAL')")
    away_team_id: str = Field(description="NBA team ID for away team")
    away_team_name: str = Field(description="Away team name")
    away_team_tricode: str = Field(description="Away team abbreviation")
    game_status: str = Field(description="Game status (scheduled, in_progress, final)")
    home_score: Optional[int] = Field(default=None, description="Home team score (null if not started)")
    away_score: Optional[int] = Field(default=None, description="Away team score (null if not started)")
    season: str = Field(index=True, description="Season year (e.g., '2024')")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Last update timestamp")
    
    def to_pydantic(self):
        """Convert to API response format (flat structure for GameScheduleResponse)."""
        return {
            "game_id": self.game_id,
            "season": self.season,
            "game_date": self.game_date.isoformat() if isinstance(self.game_date, date) else self.game_date,
            "game_time_utc": self.game_time_utc.strftime("%H:%M:%S") if isinstance(self.game_time_utc, datetime) else self.game_time_utc,
            "home_team_id": int(self.home_team_id) if self.home_team_id else 0,
            "home_team_tricode": self.home_team_tricode,
            "home_team_score": self.home_score,
            "away_team_id": int(self.away_team_id) if self.away_team_id else 0,
            "away_team_tricode": self.away_team_tricode,
            "away_team_score": self.away_score,
            "game_status": self.game_status
        }


class PlayerInfoModel(SQLModel, table=True):
    """Extended NBA player information database model."""
    
    __tablename__ = "player_info"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    sleeper_player_id: str = Field(unique=True, index=True, description="Sleeper player ID")
    nba_person_id: Optional[str] = Field(default=None, index=True, description="NBA.com person ID")
    full_name: str = Field(description="Player full name")
    first_name: str = Field(description="First name")
    last_name: str = Field(description="Last name")
    jersey_number: Optional[str] = Field(default=None, description="Jersey number")
    position: Optional[str] = Field(default=None, description="Position (from NBA API)")
    height: Optional[str] = Field(default=None, description="Height (e.g., '6-8')")
    weight: Optional[str] = Field(default=None, description="Weight in pounds")
    birthdate: Optional[date] = Field(default=None, description="Date of birth")
    country: Optional[str] = Field(default=None, description="Country of origin")
    school: Optional[str] = Field(default=None, description="College/school")
    draft_year: Optional[int] = Field(default=None, description="Draft year")
    draft_round: Optional[int] = Field(default=None, description="Draft round")
    draft_number: Optional[int] = Field(default=None, description="Draft pick number")
    nba_team_id: Optional[str] = Field(default=None, description="Current NBA team ID")
    nba_team_name: Optional[str] = Field(default=None, description="Current NBA team name")
    years_pro: Optional[int] = Field(default=None, description="Years of professional experience")
    injury_status: Optional[str] = Field(default=None, description="Current injury status (from Sleeper)")
    injury_description: Optional[str] = Field(default=None, description="Injury description")
    last_updated: datetime = Field(default_factory=datetime.utcnow, description="Last data update timestamp")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Record creation timestamp")
    
    def to_pydantic(self):
        """Convert to API response format (matches PlayerInfoResponse)."""
        return {
            "sleeper_player_id": self.sleeper_player_id,
            "nba_person_id": int(self.nba_person_id) if self.nba_person_id else None,
            "display_first_last": self.full_name,
            "first_name": self.first_name,
            "last_name": self.last_name,
            "birthdate": self.birthdate.isoformat() if self.birthdate else None,
            "country": self.country,
            "height_inches": int(self.height.split("-")[0]) * 12 + int(self.height.split("-")[1]) if self.height and "-" in self.height else None,
            "weight_pounds": int(self.weight) if self.weight and self.weight.isdigit() else None,
            "jersey": self.jersey_number,
            "position": self.position,
            "draft_year": self.draft_year,
            "draft_round": self.draft_round,
            "draft_number": self.draft_number,
            "team_id": int(self.nba_team_id) if self.nba_team_id and str(self.nba_team_id).isdigit() else None,
            "team_name": self.nba_team_name,
            "team_abbreviation": self.nba_team_name,  # Will update with proper field later
            "injury_status": self.injury_status,
            "injury_notes": self.injury_description
        }


# Add indexes for new models
GameScheduleModel.__table_args__ = (
    Index("ix_game_schedules_game_id", "game_id"),
    Index("ix_game_schedules_game_date", "game_date"),
    Index("ix_game_schedules_season", "season"),
)

PlayerInfoModel.__table_args__ = (
    Index("ix_player_info_sleeper_player_id", "sleeper_player_id"),
    Index("ix_player_info_nba_person_id", "nba_person_id"),
)


class RosterChatSessionModel(SQLModel, table=True):
    """Roster chat session database model."""
    
    __tablename__ = "roster_chat_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True, description="Unique session identifier (UUID)")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", description="User ID (for future auth)")
    sleeper_user_id: str = Field(index=True, description="Sleeper user ID")
    league_id: str = Field(index=True, description="Sleeper league ID")
    roster_id: int = Field(description="Sleeper roster ID")
    status: str = Field(default="active", description="Session status (active, archived)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation timestamp")
    last_message_at: Optional[datetime] = Field(default=None, description="Last message timestamp")
    
    # Relationships
    user: Optional[UserModel] = Relationship(back_populates="roster_chat_sessions")
    messages: List["RosterChatMessageModel"] = Relationship(back_populates="session")
    
    def to_pydantic(self):
        """Convert to dict for API responses."""
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "sleeper_user_id": self.sleeper_user_id,
            "league_id": self.league_id,
            "roster_id": self.roster_id,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "last_message_at": self.last_message_at.isoformat() if self.last_message_at else None,
        }


class RosterChatMessageModel(SQLModel, table=True):
    """Roster chat message database model."""
    
    __tablename__ = "roster_chat_messages"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: int = Field(foreign_key="roster_chat_sessions.id", description="Chat session ID")
    role: str = Field(description="Message role (user or assistant)")
    content: str = Field(description="Message content")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="Message timestamp")
    message_metadata: Optional[str] = Field(default=None, description="JSON metadata (context_used, tokens, etc.)")
    
    # Relationships
    session: RosterChatSessionModel = Relationship(back_populates="messages")
    
    def to_pydantic(self):
        """Convert to dict for API responses."""
        import json
        
        # Decode JSON metadata if present
        metadata = None
        if self.message_metadata:
            try:
                metadata = json.loads(self.message_metadata)
            except:
                metadata = None
        
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None,
            "metadata": metadata
        }


# Add indexes for roster chat models
RosterChatSessionModel.__table_args__ = (
    Index("ix_roster_chat_sessions_session_id", "session_id"),
    Index("ix_roster_chat_sessions_sleeper_user_id", "sleeper_user_id"),
    Index("ix_roster_chat_sessions_league_id", "league_id"),
    Index("ix_roster_chat_sessions_created_at", "created_at"),
)

RosterChatMessageModel.__table_args__ = (
    Index("ix_roster_chat_messages_session_id", "session_id"),
    Index("ix_roster_chat_messages_timestamp", "timestamp"),
    Index("ix_roster_chat_messages_role", "role"),
)


class TradeAnalysisSessionModel(SQLModel, table=True):
    """Trade analysis session database model."""
    
    __tablename__ = "trade_analysis_sessions"
    
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(unique=True, index=True, description="Unique session identifier (UUID)")
    user_id: Optional[int] = Field(default=None, foreign_key="users.id", description="Foreign key to users table")
    sleeper_user_id: str = Field(index=True, description="Sleeper user ID")
    league_id: str = Field(index=True, description="Sleeper league ID")
    user_roster_id: int = Field(description="User's roster ID")
    opponent_roster_id: int = Field(description="Opponent's roster ID")
    user_players_out: str = Field(description="JSON array of player IDs user is trading away")
    user_players_in: str = Field(description="JSON array of player IDs user is receiving")
    opponent_players_out: str = Field(description="JSON array of player IDs opponent is trading away")
    opponent_players_in: str = Field(description="JSON array of player IDs opponent is receiving")
    analysis_result: Optional[str] = Field(default=None, description="JSON serialized analysis result")
    favorability_score: Optional[float] = Field(default=None, description="Favorability score (0-100)")
    simulation_result: Optional[str] = Field(default=None, description="JSON serialized simulation result")
    status: str = Field(default="analyzing", description="Session status (analyzing, completed, failed)")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Session creation timestamp", index=True)
    completed_at: Optional[datetime] = Field(default=None, description="Completion timestamp")
    
    def to_pydantic(self):
        """Convert to response format with parsed JSON fields."""
        import json
        
        analysis = None
        if self.analysis_result:
            try:
                analysis = json.loads(self.analysis_result)
            except:
                analysis = None
        
        simulation = None
        if self.simulation_result:
            try:
                simulation = json.loads(self.simulation_result)
            except:
                simulation = None
        
        return {
            "id": self.id,
            "session_id": self.session_id,
            "user_id": self.user_id,
            "sleeper_user_id": self.sleeper_user_id,
            "league_id": self.league_id,
            "user_roster_id": self.user_roster_id,
            "opponent_roster_id": self.opponent_roster_id,
            "user_players_out": json.loads(self.user_players_out) if self.user_players_out else [],
            "user_players_in": json.loads(self.user_players_in) if self.user_players_in else [],
            "opponent_players_out": json.loads(self.opponent_players_out) if self.opponent_players_out else [],
            "opponent_players_in": json.loads(self.opponent_players_in) if self.opponent_players_in else [],
            "analysis": analysis,
            "favorability_score": self.favorability_score,
            "simulation": simulation,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


# Add indexes for trade analysis model
TradeAnalysisSessionModel.__table_args__ = (
    Index("ix_trade_analysis_sessions_session_id", "session_id"),
    Index("ix_trade_analysis_sessions_sleeper_user_id", "sleeper_user_id"),
    Index("ix_trade_analysis_sessions_league_id", "league_id"),
    Index("ix_trade_analysis_sessions_created_at", "created_at"),
)
