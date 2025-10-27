"""
Repository for database operations in the Fantasy Basketball League.
"""

from contextlib import contextmanager
from typing import List, Optional, Dict
from sqlmodel import Session, select, func
from sqlmodel.sql.expression import SelectOfScalar
from sqlalchemy.orm import selectinload
import logging

from backend.config import settings
from .models import UserModel, TeamModel, PlayerModel, TradePreferenceModel, TradeSessionModel, ConversationMessageModel, TradeResultModel, TradeSessionStatus, RosterChatSessionModel, RosterChatMessageModel, TradeAnalysisSessionModel
from shared.models import TradeProposal, TeamResponse, PlayerResponse, PlayerStats

logger = logging.getLogger(__name__)


class BasketballRepository:
    """Repository for basketball-related database operations with singleton pattern."""
    
    _instance = None
    
    def __new__(cls, engine=None):
        """Singleton pattern implementation."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self, engine):
        """Initialize repository with database engine."""
        if not hasattr(self, '_initialized'):
            self.engine = engine
            self._initialized = True
    
    @contextmanager
    def get_session(self):
        """
        Context manager for database sessions with automatic commit/rollback.
        
        Yields:
            Session: SQLModel database session
        """
        session = Session(self.engine)
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    # User Management Methods
    
    def create_user(self, email: str, hashed_password: str) -> UserModel:
        """
        Create a new user with email and hashed password.
        
        Args:
            email: User email address
            hashed_password: Bcrypt hashed password
            
        Returns:
            UserModel: Created user instance
        """
        try:
            with self.get_session() as session:
                user = UserModel(
                    email=email,
                    hashed_password=hashed_password
                )
                session.add(user)
                session.flush()  # Get the ID
                session.refresh(user)
                
                logger.info(f"Created user with ID {user.id} and email {email}")
                return user
                
        except Exception as e:
            logger.error(f"Error creating user {email}: {e}")
            raise
    
    def get_user_by_email(self, email: str) -> Optional[UserModel]:
        """
        Retrieve user by email address for login.
        
        Args:
            email: User email address
            
        Returns:
            UserModel instance or None if not found
        """
        try:
            with self.get_session() as session:
                statement = select(UserModel).where(UserModel.email == email)
                user = session.exec(statement).first()
                
                if user:
                    logger.info(f"Retrieved user {user.id} for email {email}")
                else:
                    logger.info(f"No user found for email {email}")
                    
                return user
                
        except Exception as e:
            logger.error(f"Error retrieving user by email {email}: {e}")
            raise
    
    def get_user_by_id(self, user_id: int) -> Optional[UserModel]:
        """
        Retrieve user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            UserModel instance or None if not found
        """
        try:
            with self.get_session() as session:
                statement = select(UserModel).where(UserModel.id == user_id)
                user = session.exec(statement).first()
                
                if user:
                    logger.info(f"Retrieved user {user.id}")
                else:
                    logger.info(f"No user found with ID {user_id}")
                    
                return user
                
        except Exception as e:
            logger.error(f"Error retrieving user by ID {user_id}: {e}")
            raise
    
    def update_user_sleeper_info(self, user_id: int, sleeper_username: str, sleeper_user_id: str) -> bool:
        """
        Link Sleeper account information to user.
        
        Args:
            user_id: User ID
            sleeper_username: Sleeper username
            sleeper_user_id: Sleeper user ID
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            with self.get_session() as session:
                statement = select(UserModel).where(UserModel.id == user_id)
                user = session.exec(statement).first()
                
                if user:
                    user.sleeper_username = sleeper_username
                    user.sleeper_user_id = sleeper_user_id
                    session.add(user)
                    
                    logger.info(f"Updated Sleeper info for user {user_id}: {sleeper_username}")
                    return True
                else:
                    logger.warning(f"User {user_id} not found for Sleeper update")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating Sleeper info for user {user_id}: {e}")
            raise
    
    def update_last_login(self, user_id: int) -> bool:
        """
        Update last login timestamp for user.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            from datetime import datetime
            
            with self.get_session() as session:
                statement = select(UserModel).where(UserModel.id == user_id)
                user = session.exec(statement).first()
                
                if user:
                    user.last_login = datetime.utcnow()
                    session.add(user)
                    
                    logger.info(f"Updated last login for user {user_id}")
                    return True
                else:
                    logger.warning(f"User {user_id} not found for login update")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {e}")
            return False

    def get_or_create_user_by_sleeper(self, sleeper_username: str, sleeper_user_id: str) -> UserModel:
        """
        Get or create user by Sleeper username for anonymous sessions.
        
        Args:
            sleeper_username: Sleeper username
            sleeper_user_id: Sleeper user ID
            
        Returns:
            UserModel: Existing or newly created user
        """
        try:
            with self.get_session() as session:
                # Check if user exists with given sleeper_user_id
                statement = select(UserModel).where(UserModel.sleeper_user_id == sleeper_user_id)
                existing_user = session.exec(statement).first()
                
                if existing_user:
                    logger.info(f"Found existing user {existing_user.id} for Sleeper user {sleeper_user_id}")
                    return existing_user
                
                # Create new user with generated email and placeholder password
                user = UserModel(
                    email=f"{sleeper_username}@sleeper.local",
                    hashed_password="",  # Empty password for Sleeper-only users
                    sleeper_username=sleeper_username,
                    sleeper_user_id=sleeper_user_id,
                    is_active=True
                )
                
                session.add(user)
                session.flush()  # Get the ID
                session.refresh(user)
                
                logger.info(f"Created new user {user.id} for Sleeper user {sleeper_user_id} ({sleeper_username})")
                return user
                
        except Exception as e:
            logger.error(f"Error getting/creating user for Sleeper {sleeper_username}: {e}")
            raise

    def store_refresh_token(self, user_id: int, hashed_refresh_token: str, expires_at) -> bool:
        """
        Store hashed refresh token in database.
        
        Args:
            user_id: User ID
            hashed_refresh_token: Bcrypt hashed refresh token
            expires_at: Token expiration timestamp
            
        Returns:
            bool: True if storage successful, False otherwise
        """
        try:
            with self.get_session() as session:
                statement = select(UserModel).where(UserModel.id == user_id)
                user = session.exec(statement).first()
                
                if user:
                    user.hashed_refresh_token = hashed_refresh_token
                    user.refresh_token_expires_at = expires_at
                    session.add(user)
                    
                    logger.info(f"Stored refresh token for user {user_id}")
                    return True
                else:
                    logger.warning(f"User {user_id} not found for refresh token storage")
                    return False
                    
        except Exception as e:
            logger.error(f"Error storing refresh token for user {user_id}: {e}")
            return False

    def verify_refresh_token(self, user_id: int, token: str) -> bool:
        """
        Verify refresh token against stored hash.
        
        Args:
            user_id: User ID
            token: Plaintext refresh token to verify
            
        Returns:
            bool: True if token is valid and not expired
        """
        try:
            from datetime import datetime
            from passlib.context import CryptContext
            
            pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
            
            with self.get_session() as session:
                statement = select(UserModel).where(UserModel.id == user_id)
                user = session.exec(statement).first()
                
                if not user or not user.hashed_refresh_token:
                    return False
                    
                # Check if token has expired
                if user.refresh_token_expires_at and user.refresh_token_expires_at < datetime.utcnow():
                    return False
                    
                # Verify token hash
                return pwd_context.verify(token, user.hashed_refresh_token)
                
        except Exception as e:
            logger.error(f"Error verifying refresh token for user {user_id}: {e}")
            return False

    def clear_refresh_token(self, user_id: int) -> bool:
        """
        Clear refresh token from database (for logout).
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if successful
        """
        try:
            with self.get_session() as session:
                statement = select(UserModel).where(UserModel.id == user_id)
                user = session.exec(statement).first()
                
                if user:
                    user.hashed_refresh_token = None
                    user.refresh_token_expires_at = None
                    session.add(user)
                    
                    logger.info(f"Cleared refresh token for user {user_id}")
                    return True
                else:
                    logger.warning(f"User {user_id} not found for refresh token clear")
                    return False
                    
        except Exception as e:
            logger.error(f"Error clearing refresh token for user {user_id}: {e}")
            return False

    
    def get_all_teams(self) -> List[TeamModel]:
        """
        Get all teams with eager-loaded players using selectinload to avoid N+1 queries.
        
        Returns:
            List of TeamModel instances with players
        """
        try:
            with self.get_session() as session:
                statement = select(TeamModel).options(selectinload(TeamModel.players))
                teams = session.exec(statement).all()
                
                logger.info(f"Retrieved {len(teams)} teams")
                return list(teams)
                
        except Exception as e:
            logger.error(f"Error retrieving all teams: {e}")
            raise
    
    def get_teams_with_stats(self) -> List[TeamResponse]:
        """
        Get all teams with calculated stats (salary and player count) within session context.
        
        Returns:
            List of TeamResponse models with computed values
        """
        
        try:
            with self.get_session() as session:
                statement = select(TeamModel).options(selectinload(TeamModel.players))
                teams = session.exec(statement).all()
                
                team_responses = []
                for team in teams:
                    # Calculate values while in session
                    player_count = len(team.players) if team.players else 0
                    total_salary = self.calculate_team_salary(team.id)
                    
                    team_response = TeamResponse(
                        id=team.id,
                        name=team.name,
                        total_salary=total_salary,
                        player_count=player_count
                    )
                    team_responses.append(team_response)
                
                logger.info(f"Retrieved {len(team_responses)} teams with stats")
                return team_responses
                
        except Exception as e:
            logger.error(f"Error retrieving teams with stats: {e}")
            raise
    
    def get_team_players_with_team_info(self, team_id: int) -> Dict:
        """
        Get all players for a team along with team info, handling sessions properly.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Dict with team_name and players list, or None if team not found
        """        
        try:
            with self.get_session() as session:
                # Get team
                team = session.get(TeamModel, team_id)
                if not team:
                    return None
                
                # Get players
                players_statement = select(PlayerModel).where(PlayerModel.team_id == team_id)
                players = session.exec(players_statement).all()
                
                # Convert to response models while in session
                player_responses = []
                for player in players:
                    stats = PlayerStats(
                        points_per_game=player.points_per_game,
                        rebounds_per_game=player.rebounds_per_game,
                        assists_per_game=player.assists_per_game,
                        steals_per_game=player.steals_per_game,
                        blocks_per_game=player.blocks_per_game,
                        turnovers_per_game=player.turnovers_per_game,
                        field_goal_percentage=player.field_goal_percentage,
                        three_point_percentage=player.three_point_percentage
                    )
                    
                    player_response = PlayerResponse(
                        id=player.id,
                        name=player.name,
                        team_id=player.team_id,
                        position=player.position.value,
                        salary=player.salary,
                        stats=stats
                    )
                    player_responses.append(player_response)
                
                result = {
                    'team_name': team.name,
                    'players': player_responses
                }
                
                logger.info(f"Retrieved {len(player_responses)} players for team {team.name}")
                return result
                
        except Exception as e:
            logger.error(f"Error retrieving players for team {team_id}: {e}")
            raise
    
    def get_team_by_id(self, team_id: int) -> Optional[TeamModel]:
        """
        Get team by ID with eager-loaded players.
        
        Args:
            team_id: Team identifier
            
        Returns:
            TeamModel instance or None if not found
        """
        try:
            with self.get_session() as session:
                team = session.get(TeamModel, team_id)
                
                if team:
                    # Load players for the team
                    players_statement = select(PlayerModel).where(PlayerModel.team_id == team_id)
                    team.players = list(session.exec(players_statement))
                    logger.info(f"Retrieved team {team_id} with {len(team.players)} players")
                else:
                    logger.warning(f"Team {team_id} not found")
                
                return team
                
        except Exception as e:
            logger.error(f"Error retrieving team {team_id}: {e}")
            raise
    
    def get_team_players(self, team_id: int) -> List[PlayerModel]:
        """
        Get all players for a specific team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            List of PlayerModel instances
        """
        try:
            with self.get_session() as session:
                statement = select(PlayerModel).where(PlayerModel.team_id == team_id)
                players = session.exec(statement).all()
                
                logger.info(f"Retrieved {len(players)} players for team {team_id}")
                return list(players)
                
        except Exception as e:
            logger.error(f"Error retrieving players for team {team_id}: {e}")
            raise
    
    def get_player_by_id(self, player_id: int) -> Optional[PlayerModel]:
        """
        Get player by ID.
        
        Args:
            player_id: Player identifier
            
        Returns:
            PlayerModel instance or None if not found
        """
        try:
            with self.get_session() as session:
                player = session.get(PlayerModel, player_id)
                
                if player:
                    logger.info(f"Retrieved player {player_id}: {player.name}")
                else:
                    logger.warning(f"Player {player_id} not found")
                
                return player
                
        except Exception as e:
            logger.error(f"Error retrieving player {player_id}: {e}")
            raise
    
    def create_trade_preference(self, preference: TradePreferenceModel) -> TradePreferenceModel:
        """
        Create a new trade preference.
        
        Args:
            preference: TradePreferenceModel instance
            
        Returns:
            Created TradePreferenceModel instance
        """
        try:
            with self.get_session() as session:
                session.add(preference)
                session.commit()
                session.refresh(preference)
                
                logger.info(f"Created trade preference for team {preference.team_id}")
                return preference
                
        except Exception as e:
            logger.error(f"Error creating trade preference: {e}")
            raise
    
    def get_trade_preference(self, team_id: int) -> Optional[TradePreferenceModel]:
        """
        Get the latest trade preference for a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            TradePreferenceModel instance or None if not found
        """
        try:
            with self.get_session() as session:
                statement = (
                    select(TradePreferenceModel)
                    .where(TradePreferenceModel.team_id == team_id)
                    .order_by(TradePreferenceModel.created_at.desc())
                )
                preference = session.exec(statement).first()
                
                if preference:
                    logger.info(f"Retrieved trade preference for team {team_id}")
                else:
                    logger.warning(f"No trade preference found for team {team_id}")
                
                return preference
                
        except Exception as e:
            logger.error(f"Error retrieving trade preference for team {team_id}: {e}")
            raise
    
    def validate_roster_composition(self, team_id: int) -> dict:
        """
        Validate roster composition rules using full 13-slot assignment logic.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Dictionary with validation results: {is_valid, total_players, position_counts, violations}
        """
        try:
            with self.get_session() as session:
                # Get all players for the team
                players_statement = select(PlayerModel).where(PlayerModel.team_id == team_id)
                players = list(session.exec(players_statement))
                
                # Count players by position
                position_counts = {}
                for player in players:
                    pos = player.position.value if hasattr(player.position, 'value') else str(player.position)
                    position_counts[pos] = position_counts.get(pos, 0) + 1
                
                # Use the full 13-slot composition validation
                is_valid, error_message = self._validate_13_slot_composition(players, team_id)
                
                violations = []
                if not is_valid:
                    violations.append(error_message)
                
                # Add salary cap check using settings
                total_salary = self.calculate_team_salary(team_id)
                if total_salary > settings.salary_cap:
                    is_valid = False
                    violations.append(f"Exceeds salary cap: ${total_salary:,} > ${settings.salary_cap:,}")
                
                result = {
                    'is_valid': is_valid,
                    'total_players': len(players),
                    'position_counts': position_counts,
                    'violations': violations
                }
                
                logger.info(f"Roster validation for team {team_id}: {'VALID' if is_valid else 'INVALID'}")
                return result
                
        except Exception as e:
            logger.error(f"Error validating roster for team {team_id}: {e}")
            raise
    
    def calculate_team_salary(self, team_id: int) -> int:
        """
        Calculate total salary for a team.
        
        Args:
            team_id: Team identifier
            
        Returns:
            Total team salary in dollars
        """
        try:
            with self.get_session() as session:
                statement = (
                    select(func.sum(PlayerModel.salary))
                    .where(PlayerModel.team_id == team_id)
                )
                total_salary = session.exec(statement).one() or 0
                
                logger.info(f"Total salary for team {team_id}: ${total_salary:,}")
                return int(total_salary)
                
        except Exception as e:
            logger.error(f"Error calculating salary for team {team_id}: {e}")
            raise
    
    # Trade Session Management Methods
    
    def create_trade_session(self, session_id: str, user_id: Optional[int], initiating_team_id: int, target_team_ids: List[int], max_turns: int = 10) -> TradeSessionModel:
        """
        Create a new trade session for multi-agent negotiation.
        
        Args:
            session_id: Unique session identifier
            user_id: ID of the user creating the session (optional for anonymous sessions)
            initiating_team_id: ID of team starting the trade
            target_team_ids: List of target team IDs for the trade
            max_turns: Maximum negotiation turns allowed
            
        Returns:
            Created trade session model
        """
        import json
        
        try:
            with self.get_session() as session:
                # Check if session already exists to avoid duplication
                existing = session.exec(
                    select(TradeSessionModel).where(TradeSessionModel.session_id == session_id)
                ).first()
                
                if existing:
                    logger.info(f"Trade session {session_id} already exists, returning existing record")
                    return existing
                
                trade_session = TradeSessionModel(
                    session_id=session_id,
                    user_id=user_id,
                    status=TradeSessionStatus.PENDING,
                    initiating_team_id=initiating_team_id,
                    target_team_ids=json.dumps(target_team_ids),
                    max_turns=max_turns
                )
                
                session.add(trade_session)
                session.commit()
                session.refresh(trade_session)
                
                logger.info(f"Created trade session {session_id} for user {user_id or 'anonymous'}, team {initiating_team_id} -> {target_team_ids}")
                return trade_session
                
        except Exception as e:
            logger.error(f"Error creating trade session: {e}")
            raise
    
    def get_trade_session(self, session_id: str) -> Optional[TradeSessionModel]:
        """
        Get trade session by ID.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Trade session model or None if not found
        """
        try:
            with self.get_session() as session:
                statement = (
                    select(TradeSessionModel)
                    .options(
                        selectinload(TradeSessionModel.messages),
                        selectinload(TradeSessionModel.result)
                    )
                    .where(TradeSessionModel.session_id == session_id)
                )
                
                result = session.exec(statement).first()
                logger.info(f"Retrieved trade session {session_id}: {'Found' if result else 'Not found'}")
                return result
                
        except Exception as e:
            logger.error(f"Error retrieving trade session {session_id}: {e}")
            raise
    
    def update_trade_session_status(self, session_id: str, status: TradeSessionStatus, current_turn: Optional[int] = None, error_message: Optional[str] = None) -> bool:
        """
        Update trade session status and progress.
        
        Args:
            session_id: Session identifier
            status: New session status
            current_turn: Current turn number (optional)
            error_message: Error message if status is FAILED (optional)
            
        Returns:
            True if updated successfully, False otherwise
        """
        try:
            with self.get_session() as session:
                statement = select(TradeSessionModel).where(TradeSessionModel.session_id == session_id)
                trade_session = session.exec(statement).first()
                
                if not trade_session:
                    logger.error(f"Trade session {session_id} not found for status update")
                    return False
                
                trade_session.status = status
                if current_turn is not None:
                    trade_session.current_turn = current_turn
                if error_message:
                    trade_session.error_message = error_message
                if status in [TradeSessionStatus.COMPLETED, TradeSessionStatus.FAILED]:
                    from datetime import datetime
                    trade_session.completed_at = datetime.utcnow()
                
                session.add(trade_session)
                session.commit()
                
                logger.info(f"Updated trade session {session_id} status to {status.value}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating trade session {session_id}: {e}")
            raise
    
    def add_conversation_message(self, session_id: str, agent_name: str, content: str, turn_number: int) -> ConversationMessageModel:
        """
        Add a conversation message to trade session.
        
        Args:
            session_id: Session identifier
            agent_name: Name of agent sending message
            content: Message content
            turn_number: Turn number when message was sent
            
        Returns:
            Created conversation message model
        """
        try:
            with self.get_session() as session:
                # Get trade session ID
                trade_session_stmt = select(TradeSessionModel).where(TradeSessionModel.session_id == session_id)
                trade_session = session.exec(trade_session_stmt).first()
                
                if not trade_session:
                    raise ValueError(f"Trade session {session_id} not found")
                
                message = ConversationMessageModel(
                    session_id=trade_session.id,
                    agent_name=agent_name,
                    content=content,
                    turn_number=turn_number
                )
                
                session.add(message)
                session.commit()
                session.refresh(message)
                
                logger.info(f"Added message from {agent_name} to session {session_id}")
                return message
                
        except Exception as e:
            logger.error(f"Error adding conversation message: {e}")
            raise
    
    def save_trade_result(self, session_id: str, consensus_reached: bool, trade_decision_json: Optional[str], 
                         commissioner_notes: Optional[str], total_turns: int, final_consensus: bool) -> TradeResultModel:
        """
        Save final trade negotiation result.
        
        Args:
            session_id: Session identifier
            consensus_reached: Whether individual consensus was reached
            trade_decision_json: JSON serialized TradeDecision
            commissioner_notes: Commissioner notes
            total_turns: Total negotiation turns
            final_consensus: Whether overall final consensus was reached
            
        Returns:
            Created trade result model
        """
        try:
            with self.get_session() as session:
                # Get trade session ID
                trade_session_stmt = select(TradeSessionModel).where(TradeSessionModel.session_id == session_id)
                trade_session = session.exec(trade_session_stmt).first()
                
                if not trade_session:
                    raise ValueError(f"Trade session {session_id} not found")
                
                result = TradeResultModel(
                    session_id=trade_session.id,
                    approved=consensus_reached,
                    trade_proposal_json=trade_decision_json,
                    commissioner_notes=commissioner_notes,
                    total_turns=total_turns,
                    consensus_reached=final_consensus
                )
                
                session.add(result)
                session.commit()
                session.refresh(result)
                
                logger.info(f"Saved trade result for session {session_id}: {'Consensus' if consensus_reached else 'No Consensus'}")
                return result
                
        except Exception as e:
            logger.error(f"Error saving trade result: {e}")
            raise
    
    def get_user_trade_sessions(self, user_id: int) -> List[TradeSessionModel]:
        """
        Get all trade sessions for a specific user.
        
        Args:
            user_id: User ID
            
        Returns:
            List of TradeSessionModel instances owned by the user
        """
        try:
            with self.get_session() as session:
                statement = (
                    select(TradeSessionModel)
                    .where(TradeSessionModel.user_id == user_id)
                    .options(selectinload(TradeSessionModel.messages))
                    .options(selectinload(TradeSessionModel.result))
                    .order_by(TradeSessionModel.started_at.desc())
                )
                sessions = session.exec(statement).all()
                
                logger.info(f"Retrieved {len(sessions)} trade sessions for user {user_id}")
                return list(sessions)
                
        except Exception as e:
            logger.error(f"Error retrieving trade sessions for user {user_id}: {e}")
            raise
    
    def validate_session_ownership(self, session_id: str, user_id: int) -> bool:
        """
        Check if a trade session belongs to a specific user.
        
        Args:
            session_id: Session identifier
            user_id: User ID
            
        Returns:
            bool: True if session belongs to user, False otherwise
        """
        try:
            with self.get_session() as session:
                statement = select(TradeSessionModel).where(
                    TradeSessionModel.session_id == session_id,
                    TradeSessionModel.user_id == user_id
                )
                trade_session = session.exec(statement).first()
                
                result = trade_session is not None
                logger.info(f"Session {session_id} ownership validation for user {user_id}: {result}")
                return result
                
        except Exception as e:
            logger.error(f"Error validating session ownership for {session_id}, user {user_id}: {e}")
            raise
    
    def validate_trade_legality(self, offering_team_id: int, receiving_team_id: int, 
                               offered_player_ids: List[int], requested_player_ids: List[int]) -> tuple[bool, str]:
        """
        Validate if a trade proposal is legal according to league rules.
        
        Args:
            offering_team_id: ID of team making the offer
            receiving_team_id: ID of team receiving the offer
            offered_player_ids: List of player IDs being offered
            requested_player_ids: List of player IDs being requested
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            with self.get_session() as session:
                # Load players by IDs
                offered_players = []
                for player_id in offered_player_ids:
                    player = session.get(PlayerModel, player_id)
                    if not player:
                        return False, f"Offered player {player_id} not found"
                    offered_players.append(player)
                
                requested_players = []
                for player_id in requested_player_ids:
                    player = session.get(PlayerModel, player_id)
                    if not player:
                        return False, f"Requested player {player_id} not found"
                    requested_players.append(player)
                
                # Validate both teams
                for team_id, players_out, players_in in [
                    (offering_team_id, offered_players, requested_players),
                    (receiving_team_id, requested_players, offered_players)
                ]:
                    # Calculate salary changes using settings.salary_cap
                    outgoing_salary = sum(p.salary for p in players_out)
                    incoming_salary = sum(p.salary for p in players_in)
                    salary_change = incoming_salary - outgoing_salary
                    
                    # Get current team salary using calculate_team_salary
                    current_salary = self.calculate_team_salary(team_id)
                    new_salary = current_salary + salary_change
                    
                    # Check salary cap using settings
                    if new_salary > settings.salary_cap:
                        return False, f"Team {team_id} would exceed salary cap: ${new_salary:,} > ${settings.salary_cap:,}"
                
                # Validate 13-slot roster composition for both teams
                for team_id, players_out, players_in in [
                    (offering_team_id, offered_players, requested_players),
                    (receiving_team_id, requested_players, offered_players)
                ]:
                    # Get current roster
                    current_players = self.get_team_players(team_id)
                    
                    # Apply trade changes
                    outgoing_ids = {p.id for p in players_out}
                    remaining_players = [p for p in current_players if p.id not in outgoing_ids]
                    new_roster = remaining_players + list(players_in)
                    
                    # Validate 13-slot composition by simulating assignments
                    is_valid, error_msg = self._validate_13_slot_composition(new_roster, team_id)
                    if not is_valid:
                        return False, error_msg
                
                return True, "Trade proposal is valid"
                
        except Exception as e:
            logger.error(f"Error validating trade legality: {e}")
            return False, f"Validation error: {str(e)}"
    
    def _validate_13_slot_composition(self, roster: List[PlayerModel], team_id: int) -> tuple[bool, str]:
        """
        Validate 13-slot roster composition including flexible slots.
        
        Required slots: PG, SG, G, SF, PF, F, C, 2xUTIL, 3xBENCH
        
        Args:
            roster: List of players to validate
            team_id: Team ID for error messages
            
        Returns:
            Tuple of (is_valid, error_message)
        """
        try:
            if len(roster) != 13:
                return False, f"Team {team_id} would have {len(roster)} players (must be exactly 13)"
            
            # Group players by position
            position_groups = {
                'PG': [],
                'SG': [], 
                'SF': [],
                'PF': [],
                'C': []
            }
            
            for player in roster:
                pos = player.position.value if hasattr(player.position, 'value') else str(player.position)
                if pos in position_groups:
                    position_groups[pos].append(player)
            
            # Simulate slot assignments
            slots = {
                'PG': None,      # Must be PG
                'SG': None,      # Must be SG  
                'G': None,       # PG or SG
                'SF': None,      # Must be SF
                'PF': None,      # Must be PF
                'F': None,       # SF or PF
                'C': None,       # Must be C
                'UTIL1': None,   # Any position
                'UTIL2': None,   # Any position
                'BENCH1': None,  # Any position
                'BENCH2': None,  # Any position
                'BENCH3': None   # Any position
            }
            
            available_players = roster.copy()
            
            # Assign mandatory position slots first
            mandatory_assignments = [
                ('PG', ['PG']),
                ('SG', ['SG']),
                ('SF', ['SF']),  
                ('PF', ['PF']),
                ('C', ['C'])
            ]
            
            for slot, allowed_positions in mandatory_assignments:
                found = False
                for pos in allowed_positions:
                    if position_groups[pos]:
                        player = position_groups[pos].pop(0)
                        slots[slot] = player
                        available_players.remove(player)
                        found = True
                        break
                
                if not found:
                    return False, f"Team {team_id} lacks required {slot} position player"
            
            # Assign flexible G slot (remaining PG or SG)
            for pos in ['PG', 'SG']:
                if position_groups[pos]:
                    player = position_groups[pos].pop(0)
                    slots['G'] = player
                    available_players.remove(player)
                    break
            
            if not slots['G']:
                return False, f"Team {team_id} lacks sufficient guards for G slot"
            
            # Assign flexible F slot (remaining SF or PF)
            for pos in ['SF', 'PF']:
                if position_groups[pos]:
                    player = position_groups[pos].pop(0)
                    slots['F'] = player
                    available_players.remove(player)
                    break
            
            if not slots['F']:
                return False, f"Team {team_id} lacks sufficient forwards for F slot"
            
            # Assign remaining players to UTIL and BENCH slots
            flex_slots = ['UTIL1', 'UTIL2', 'BENCH1', 'BENCH2', 'BENCH3']
            
            for slot in flex_slots:
                if available_players:
                    player = available_players.pop(0)
                    slots[slot] = player
                else:
                    return False, f"Team {team_id} cannot fill all required slots"
            
            # Verify all players are assigned
            if available_players:
                return False, f"Team {team_id} has unassignable players"
            
            return True, "13-slot composition is valid"
            
        except Exception as e:
            logger.error(f"Error validating 13-slot composition: {e}")
            return False, f"Composition validation error: {str(e)}"

    # ===== NBA Stats Repository Methods =====
    
    def upsert_game_schedule(self, game_data: dict) -> bool:
        """
        Insert or update a single game in the schedule.
        
        Args:
            game_data: Dictionary with game data matching GameScheduleModel fields
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from .models import GameScheduleModel
            
            with self.get_session() as session:
                # Check if game exists
                existing_game = session.exec(
                    select(GameScheduleModel).where(GameScheduleModel.game_id == game_data["game_id"])
                ).first()
                
                if existing_game:
                    # Update existing game
                    for key, value in game_data.items():
                        setattr(existing_game, key, value)
                else:
                    # Create new game
                    new_game = GameScheduleModel(**game_data)
                    session.add(new_game)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error upserting game schedule: {e}")
            return False
    
    def bulk_upsert_game_schedules(self, games_data: List[dict]) -> int:
        """
        Bulk insert or update games in the schedule.
        
        Args:
            games_data: List of dictionaries with game data
            
        Returns:
            int: Number of games successfully upserted
        """
        try:
            from .models import GameScheduleModel
            
            with self.get_session() as session:
                count = 0
                
                for game_data in games_data:
                    try:
                        # Check if game exists
                        existing_game = session.exec(
                            select(GameScheduleModel).where(GameScheduleModel.game_id == game_data["game_id"])
                        ).first()
                        
                        if existing_game:
                            # Update existing game
                            for key, value in game_data.items():
                                setattr(existing_game, key, value)
                        else:
                            # Create new game
                            new_game = GameScheduleModel(**game_data)
                            session.add(new_game)
                        
                        count += 1
                        
                    except Exception as e:
                        logger.error(f"Error upserting game {game_data.get('game_id')}: {e}")
                        continue
                
                session.commit()
                return count
                
        except Exception as e:
            logger.error(f"Error in bulk upsert game schedules: {e}")
            return 0
    
    def get_games_by_date_range(self, start_date: str, end_date: str, season: Optional[str] = None) -> List[dict]:
        """
        Get games within a date range.
        
        Args:
            start_date: Start date (YYYY-MM-DD string)
            end_date: End date (YYYY-MM-DD string)
            season: Optional season filter (e.g., "2024")
            
        Returns:
            List[dict]: List of game dictionaries
        """
        try:
            from .models import GameScheduleModel
            from datetime import date as date_type
            
            # Parse string dates to date objects for comparison
            start_date_obj = date_type.fromisoformat(start_date) if start_date else None
            end_date_obj = date_type.fromisoformat(end_date) if end_date else None
            
            with self.get_session() as session:
                query = select(GameScheduleModel)
                
                if start_date_obj:
                    query = query.where(GameScheduleModel.game_date >= start_date_obj)
                if end_date_obj:
                    query = query.where(GameScheduleModel.game_date <= end_date_obj)
                if season:
                    query = query.where(GameScheduleModel.season == season)
                
                query = query.order_by(GameScheduleModel.game_date, GameScheduleModel.game_time_utc)
                
                games = session.exec(query).all()
                return [game.to_pydantic() for game in games]
                
        except Exception as e:
            logger.error(f"Error getting games by date range: {e}")
            return []
    
    def get_games_by_team(self, team_tricode: str, start_date: Optional[str] = None, end_date: Optional[str] = None) -> List[dict]:
        """
        Get games for a specific team.
        
        Args:
            team_tricode: Team tricode (e.g., "LAL", "BOS")
            start_date: Optional start date filter (YYYY-MM-DD string)
            end_date: Optional end date filter (YYYY-MM-DD string)
            
        Returns:
            List[dict]: List of game dictionaries
        """
        try:
            from .models import GameScheduleModel
            from sqlmodel import or_
            from datetime import date as date_type
            
            with self.get_session() as session:
                query = select(GameScheduleModel).where(
                    or_(
                        GameScheduleModel.home_team_tricode == team_tricode,
                        GameScheduleModel.away_team_tricode == team_tricode
                    )
                )
                
                if start_date:
                    start_date_obj = date_type.fromisoformat(start_date)
                    query = query.where(GameScheduleModel.game_date >= start_date_obj)
                if end_date:
                    end_date_obj = date_type.fromisoformat(end_date)
                    query = query.where(GameScheduleModel.game_date <= end_date_obj)
                
                query = query.order_by(GameScheduleModel.game_date, GameScheduleModel.game_time_utc)
                
                games = session.exec(query).all()
                return [game.to_pydantic() for game in games]
                
        except Exception as e:
            logger.error(f"Error getting games by team: {e}")
            return []
    
    def get_todays_games(self) -> List[dict]:
        """
        Get all games scheduled for today.
        
        Returns:
            List[dict]: List of game dictionaries
        """
        try:
            from .models import GameScheduleModel
            from datetime import datetime, date as date_type
            
            today = datetime.utcnow().date()
            
            with self.get_session() as session:
                games = session.exec(
                    select(GameScheduleModel)
                    .where(GameScheduleModel.game_date == today)
                    .order_by(GameScheduleModel.game_time_utc)
                ).all()
                
                return [game.to_pydantic() for game in games]
                
        except Exception as e:
            logger.error(f"Error getting today's games: {e}")
            return []
    
    def delete_old_games(self, before_date: str) -> int:
        """
        Delete games before a specific date.
        
        Args:
            before_date: Date threshold (YYYY-MM-DD)
            
        Returns:
            int: Number of games deleted
        """
        try:
            from .models import GameScheduleModel
            
            with self.get_session() as session:
                games = session.exec(
                    select(GameScheduleModel).where(GameScheduleModel.game_date < before_date)
                ).all()
                
                count = len(games)
                
                for game in games:
                    session.delete(game)
                
                session.commit()
                return count
                
        except Exception as e:
            logger.error(f"Error deleting old games: {e}")
            return 0
    
    def upsert_player_info(self, player_data: dict) -> bool:
        """
        Insert or update a single player's information.
        
        Args:
            player_data: Dictionary with player data matching PlayerInfoModel fields
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            from .models import PlayerInfoModel
            
            with self.get_session() as session:
                # Check if player exists by sleeper_player_id
                existing_player = session.exec(
                    select(PlayerInfoModel).where(
                        PlayerInfoModel.sleeper_player_id == player_data["sleeper_player_id"]
                    )
                ).first()
                
                if existing_player:
                    # Update existing player
                    for key, value in player_data.items():
                        setattr(existing_player, key, value)
                else:
                    # Create new player
                    new_player = PlayerInfoModel(**player_data)
                    session.add(new_player)
                
                session.commit()
                return True
                
        except Exception as e:
            logger.error(f"Error upserting player info: {e}")
            return False
    
    def bulk_upsert_player_info(self, players_data: List[dict]) -> int:
        """
        Bulk insert or update player information.
        
        Args:
            players_data: List of dictionaries with player data
            
        Returns:
            int: Number of players successfully upserted
        """
        try:
            from .models import PlayerInfoModel
            
            with self.get_session() as session:
                count = 0
                
                for player_data in players_data:
                    try:
                        # Check if player exists
                        existing_player = session.exec(
                            select(PlayerInfoModel).where(
                                PlayerInfoModel.sleeper_player_id == player_data["sleeper_player_id"]
                            )
                        ).first()
                        
                        if existing_player:
                            # Update existing player
                            for key, value in player_data.items():
                                setattr(existing_player, key, value)
                        else:
                            # Create new player
                            new_player = PlayerInfoModel(**player_data)
                            session.add(new_player)
                        
                        count += 1
                        
                    except Exception as e:
                        logger.error(f"Error upserting player {player_data.get('sleeper_player_id')}: {e}")
                        continue
                
                session.commit()
                return count
                
        except Exception as e:
            logger.error(f"Error in bulk upsert player info: {e}")
            return 0
    
    def get_player_info_by_sleeper_id(self, sleeper_player_id: str) -> Optional[dict]:
        """
        Get player information by Sleeper player ID.
        
        Args:
            sleeper_player_id: Sleeper player ID
            
        Returns:
            Optional[dict]: Player data dictionary or None
        """
        try:
            from .models import PlayerInfoModel
            
            with self.get_session() as session:
                player = session.exec(
                    select(PlayerInfoModel).where(
                        PlayerInfoModel.sleeper_player_id == sleeper_player_id
                    )
                ).first()
                
                return player.to_pydantic() if player else None
                
        except Exception as e:
            logger.error(f"Error getting player info by sleeper ID: {e}")
            return None
    
    def get_player_info_by_nba_id(self, nba_person_id: int) -> Optional[dict]:
        """
        Get player information by NBA person ID.
        
        Args:
            nba_person_id: NBA person ID
            
        Returns:
            Optional[dict]: Player data dictionary or None
        """
        try:
            from .models import PlayerInfoModel
            
            with self.get_session() as session:
                player = session.exec(
                    select(PlayerInfoModel).where(
                        PlayerInfoModel.nba_person_id == nba_person_id
                    )
                ).first()
                
                return player.to_pydantic() if player else None
                
        except Exception as e:
            logger.error(f"Error getting player info by NBA ID: {e}")
            return None
    
    def get_players_by_team(self, team_abbreviation: str) -> List[dict]:
        """
        Get all players on a specific team.
        
        Args:
            team_abbreviation: Team abbreviation or name (e.g., "LAL", "Lakers")
            
        Returns:
            List[dict]: List of player dictionaries
        """
        try:
            from .models import PlayerInfoModel
            from sqlmodel import or_
            
            with self.get_session() as session:
                # Search by team name (most reliable field we have)
                players = session.exec(
                    select(PlayerInfoModel)
                    .where(
                        or_(
                            PlayerInfoModel.nba_team_name.ilike(f"%{team_abbreviation}%"),
                            PlayerInfoModel.nba_team_id == team_abbreviation
                        )
                    )
                    .order_by(PlayerInfoModel.last_name)
                ).all()
                
                return [player.to_pydantic() for player in players]
                
        except Exception as e:
            logger.error(f"Error getting players by team: {e}")
            return []
    
    def search_players_by_name(self, name_query: str, limit: int = 20) -> List[dict]:
        """
        Search players by name (partial match).
        
        Args:
            name_query: Name to search for (case-insensitive)
            limit: Maximum number of results
            
        Returns:
            List[dict]: List of player dictionaries
        """
        try:
            from .models import PlayerInfoModel
            from sqlalchemy import func
            
            with self.get_session() as session:
                # Case-insensitive partial match on full_name
                search_pattern = f"%{name_query.lower()}%"
                
                players = session.exec(
                    select(PlayerInfoModel)
                    .where(
                        func.lower(PlayerInfoModel.full_name).like(search_pattern)
                    )
                    .order_by(PlayerInfoModel.last_name)
                    .limit(limit)
                ).all()
                
                return [player.to_pydantic() for player in players]
                
        except Exception as e:
            logger.error(f"Error searching players by name: {e}")
            return []
    
    # Roster Chat Session Methods
    
    def create_roster_chat_session(
        self,
        session_id: str,
        sleeper_user_id: str,
        league_id: str,
        roster_id: int,
        user_id: Optional[int] = None
    ) -> RosterChatSessionModel:
        """
        Create new roster chat session.
        
        Args:
            session_id: Unique session identifier (UUID)
            sleeper_user_id: Sleeper user ID
            league_id: Sleeper league ID
            roster_id: Sleeper roster ID
            user_id: Optional user ID for future auth
            
        Returns:
            RosterChatSessionModel: Created session
        """
        try:
            with self.get_session() as session:
                chat_session = RosterChatSessionModel(
                    session_id=session_id,
                    sleeper_user_id=sleeper_user_id,
                    league_id=league_id,
                    roster_id=roster_id,
                    user_id=user_id,
                    status="active"
                )
                session.add(chat_session)
                session.commit()
                session.refresh(chat_session)
                
                logger.info(f"Created roster chat session {session_id} for user {sleeper_user_id}")
                return chat_session
                
        except Exception as e:
            logger.error(f"Error creating roster chat session: {e}")
            raise
    
    def get_roster_chat_session(self, session_id: str) -> Optional[RosterChatSessionModel]:
        """
        Retrieve roster chat session by session_id (UUID).
        
        Args:
            session_id: Session UUID
            
        Returns:
            RosterChatSessionModel or None
        """
        try:
            with self.get_session() as session:
                chat_session = session.exec(
                    select(RosterChatSessionModel)
                    .where(RosterChatSessionModel.session_id == session_id)
                    .options(selectinload(RosterChatSessionModel.messages))
                ).first()
                
                if chat_session:
                    # Make the instance detached but with all attributes loaded
                    session.expunge(chat_session)
                
                return chat_session
                
        except Exception as e:
            logger.error(f"Error retrieving roster chat session {session_id}: {e}")
            return None
    
    def get_user_roster_chat_sessions(
        self,
        sleeper_user_id: str,
        league_id: Optional[str] = None,
        limit: int = 20
    ) -> List[RosterChatSessionModel]:
        """
        Get chat sessions for a Sleeper user.
        
        Args:
            sleeper_user_id: Sleeper user ID
            league_id: Optional league filter
            limit: Max results
            
        Returns:
            List of RosterChatSessionModel
        """
        try:
            with self.get_session() as session:
                query = select(RosterChatSessionModel).where(
                    RosterChatSessionModel.sleeper_user_id == sleeper_user_id
                )
                
                if league_id:
                    query = query.where(RosterChatSessionModel.league_id == league_id)
                
                query = query.order_by(RosterChatSessionModel.last_message_at.desc()).limit(limit)
                
                chat_sessions = session.exec(query).all()
                return list(chat_sessions)
                
        except Exception as e:
            logger.error(f"Error retrieving user roster chat sessions: {e}")
            return []
    
    def update_chat_session_last_message(self, session_id: str) -> bool:
        """
        Update last_message_at timestamp.
        
        Args:
            session_id: Session UUID
            
        Returns:
            bool: Success status
        """
        try:
            with self.get_session() as session:
                chat_session = session.exec(
                    select(RosterChatSessionModel)
                    .where(RosterChatSessionModel.session_id == session_id)
                ).first()
                
                if chat_session:
                    from datetime import datetime
                    chat_session.last_message_at = datetime.utcnow()
                    session.add(chat_session)
                    session.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error updating chat session timestamp: {e}")
            return False
    
    def archive_chat_session(self, session_id: str) -> bool:
        """
        Archive a chat session.
        
        Args:
            session_id: Session UUID
            
        Returns:
            bool: Success status
        """
        try:
            with self.get_session() as session:
                chat_session = session.exec(
                    select(RosterChatSessionModel)
                    .where(RosterChatSessionModel.session_id == session_id)
                ).first()
                
                if chat_session:
                    chat_session.status = "archived"
                    session.add(chat_session)
                    session.commit()
                    return True
                
                return False
                
        except Exception as e:
            logger.error(f"Error archiving chat session: {e}")
            return False
    
    # Roster Chat Message Methods
    
    def add_roster_chat_message(
        self,
        session_id: str,
        role: str,
        content: str,
        metadata: Optional[Dict] = None
    ) -> RosterChatMessageModel:
        """
        Add message to roster chat session.
        
        Args:
            session_id: Session UUID
            role: Message role (user or assistant)
            content: Message content
            metadata: Optional metadata dict
            
        Returns:
            RosterChatMessageModel: Created message
        """
        try:
            with self.get_session() as session:
                # Get session by UUID
                chat_session = session.exec(
                    select(RosterChatSessionModel)
                    .where(RosterChatSessionModel.session_id == session_id)
                ).first()
                
                if not chat_session:
                    raise ValueError(f"Chat session not found: {session_id}")
                
                # Convert metadata to JSON string
                import json
                metadata_str = json.dumps(metadata) if metadata else None
                
                # Create message
                message = RosterChatMessageModel(
                    session_id=chat_session.id,
                    role=role,
                    content=content,
                    message_metadata=metadata_str
                )
                session.add(message)
                
                # Update session last_message_at
                from datetime import datetime
                chat_session.last_message_at = datetime.utcnow()
                session.add(chat_session)
                
                session.commit()
                session.refresh(message)
                
                # Expunge the message to detach it from session with all attributes loaded
                session.expunge(message)
                
                logger.info(f"Added {role} message to chat session {session_id}")
                return message
                
        except Exception as e:
            logger.error(f"Error adding roster chat message: {e}")
            raise
    
    def get_chat_messages(
        self,
        session_id: str,
        limit: Optional[int] = None
    ) -> List[RosterChatMessageModel]:
        """
        Get messages for a chat session.
        
        Args:
            session_id: Session UUID
            limit: Optional limit for recent messages
            
        Returns:
            List of RosterChatMessageModel
        """
        try:
            with self.get_session() as session:
                # Get session by UUID
                chat_session = session.exec(
                    select(RosterChatSessionModel)
                    .where(RosterChatSessionModel.session_id == session_id)
                ).first()
                
                if not chat_session:
                    return []
                
                query = select(RosterChatMessageModel).where(
                    RosterChatMessageModel.session_id == chat_session.id
                ).order_by(RosterChatMessageModel.timestamp.asc())
                
                if limit:
                    query = query.limit(limit)
                
                messages = session.exec(query).all()
                
                # Expunge all messages to detach them from session with attributes loaded
                for msg in messages:
                    session.expunge(msg)
                
                return list(messages)
                
        except Exception as e:
            logger.error(f"Error retrieving chat messages: {e}")
            return []
    
    def get_chat_history_for_context(
        self,
        session_id: str,
        max_messages: int = 10
    ) -> List[Dict]:
        """
        Get recent chat history formatted for LLM context.
        
        Args:
            session_id: Session UUID
            max_messages: Max recent messages to include
            
        Returns:
            List of dicts with role and content
        """
        try:
            messages = self.get_chat_messages(session_id)
            
            # Get last N messages
            recent_messages = messages[-max_messages:] if len(messages) > max_messages else messages
            
            # Format for LLM
            return [
                {"role": msg.role, "content": msg.content}
                for msg in recent_messages
            ]
            
        except Exception as e:
            logger.error(f"Error building chat history for context: {e}")
            return []
    
    # ==========================================
    # Trade Analysis Session Methods
    # ==========================================
    
    def create_trade_analysis_session(
        self,
        session_id: str,
        sleeper_user_id: str,
        league_id: str,
        user_roster_id: int,
        opponent_roster_id: int,
        user_players_out: List[str],
        user_players_in: List[str],
        user_id: Optional[int] = None
    ) -> TradeAnalysisSessionModel:
        """
        Create new trade analysis session.
        
        Args:
            session_id: Unique session identifier (UUID)
            sleeper_user_id: Sleeper user ID
            league_id: Sleeper league ID
            user_roster_id: User's roster ID
            opponent_roster_id: Opponent's roster ID
            user_players_out: Player IDs user is trading away
            user_players_in: Player IDs user is receiving
            user_id: Optional foreign key to users table
            
        Returns:
            Created trade analysis session model
        """
        import json
        
        try:
            with self.get_session() as session:
                trade_session = TradeAnalysisSessionModel(
                    session_id=session_id,
                    user_id=user_id,
                    sleeper_user_id=sleeper_user_id,
                    league_id=league_id,
                    user_roster_id=user_roster_id,
                    opponent_roster_id=opponent_roster_id,
                    user_players_out=json.dumps(user_players_out),
                    user_players_in=json.dumps(user_players_in),
                    opponent_players_out=json.dumps(user_players_in),
                    opponent_players_in=json.dumps(user_players_out),
                    status="analyzing"
                )
                
                session.add(trade_session)
                session.commit()
                session.refresh(trade_session)
                
                logger.info(f"Created trade analysis session: {session_id}")
                return trade_session
                
        except Exception as e:
            logger.error(f"Error creating trade analysis session: {e}")
            raise
    
    def get_trade_analysis_session(
        self,
        session_id: str
    ) -> Optional[TradeAnalysisSessionModel]:
        """
        Retrieve trade analysis session by session_id.
        
        Args:
            session_id: Session UUID
            
        Returns:
            Trade analysis session model or None if not found
        """
        try:
            with self.get_session() as session:
                statement = select(TradeAnalysisSessionModel).where(
                    TradeAnalysisSessionModel.session_id == session_id
                )
                result = session.exec(statement).first()
                
                if result:
                    logger.info(f"Retrieved trade analysis session: {session_id}")
                    # Expunge the object to detach it from session before returning
                    session.expunge(result)
                else:
                    logger.warning(f"Trade analysis session not found: {session_id}")
                
                return result
                
        except Exception as e:
            logger.error(f"Error retrieving trade analysis session: {e}")
            return None
    
    def update_trade_analysis_result(
        self,
        session_id: str,
        analysis_result: Dict,
        favorability_score: float
    ) -> bool:
        """
        Update session with analysis result and favorability score.
        
        Args:
            session_id: Session UUID
            analysis_result: Analysis result dictionary
            favorability_score: Favorability score (0-100)
            
        Returns:
            Success status
        """
        import json
        from datetime import datetime
        
        try:
            with self.get_session() as session:
                statement = select(TradeAnalysisSessionModel).where(
                    TradeAnalysisSessionModel.session_id == session_id
                )
                trade_session = session.exec(statement).first()
                
                if not trade_session:
                    logger.error(f"Trade analysis session not found: {session_id}")
                    return False
                
                trade_session.analysis_result = json.dumps(analysis_result)
                trade_session.favorability_score = favorability_score
                trade_session.status = "completed"
                trade_session.completed_at = datetime.utcnow()
                
                session.add(trade_session)
                session.commit()
                
                logger.info(f"Updated trade analysis result for session: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating trade analysis result: {e}")
            return False
    
    def update_trade_simulation_result(
        self,
        session_id: str,
        simulation_result: Dict
    ) -> bool:
        """
        Update session with simulation result.
        
        Args:
            session_id: Session UUID
            simulation_result: Simulation result dictionary
            
        Returns:
            Success status
        """
        import json
        
        try:
            with self.get_session() as session:
                statement = select(TradeAnalysisSessionModel).where(
                    TradeAnalysisSessionModel.session_id == session_id
                )
                trade_session = session.exec(statement).first()
                
                if not trade_session:
                    logger.error(f"Trade analysis session not found: {session_id}")
                    return False
                
                trade_session.simulation_result = json.dumps(simulation_result)
                
                session.add(trade_session)
                session.commit()
                
                logger.info(f"Updated trade simulation result for session: {session_id}")
                return True
                
        except Exception as e:
            logger.error(f"Error updating trade simulation result: {e}")
            return False
    
    def get_user_trade_analyses(
        self,
        sleeper_user_id: str,
        league_id: Optional[str] = None,
        limit: int = 20
    ) -> List[TradeAnalysisSessionModel]:
        """
        Get trade analysis sessions for a user.
        
        Args:
            sleeper_user_id: Sleeper user ID
            league_id: Optional filter by league ID
            limit: Maximum number of results
            
        Returns:
            List of trade analysis sessions
        """
        try:
            with self.get_session() as session:
                statement = select(TradeAnalysisSessionModel).where(
                    TradeAnalysisSessionModel.sleeper_user_id == sleeper_user_id
                )
                
                if league_id:
                    statement = statement.where(
                        TradeAnalysisSessionModel.league_id == league_id
                    )
                
                statement = statement.order_by(
                    TradeAnalysisSessionModel.created_at.desc()
                ).limit(limit)
                
                results = session.exec(statement).all()
                
                # Expunge all results to detach from session
                for result in results:
                    session.expunge(result)
                
                logger.info(f"Retrieved {len(results)} trade analysis sessions for user: {sleeper_user_id}")
                return results
                
        except Exception as e:
            logger.error(f"Error retrieving user trade analyses: {e}")
            return []
            return []
