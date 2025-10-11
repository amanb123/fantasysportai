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
from .models import TeamModel, PlayerModel, TradePreferenceModel, TradeSessionModel, ConversationMessageModel, TradeResultModel, TradeSessionStatus
from shared.models import TradeProposal, TeamResponse, PlayerResponse

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
                    player_response = PlayerResponse(
                        id=player.id,
                        name=player.name,
                        position=player.position.value,
                        salary=player.salary,
                        stats={
                            'ppg': player.points_per_game,
                            'rpg': player.rebounds_per_game,
                            'apg': player.assists_per_game,
                            'spg': player.steals_per_game,
                            'bpg': player.blocks_per_game,
                            'tov': player.turnovers_per_game,
                            'fg%': player.field_goal_percentage,
                            '3pt%': player.three_point_percentage
                        }
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
    
    def create_trade_session(self, session_id: str, initiating_team_id: int, target_team_ids: List[int], max_turns: int = 10) -> TradeSessionModel:
        """
        Create a new trade session for multi-agent negotiation.
        
        Args:
            session_id: Unique session identifier
            initiating_team_id: ID of team starting the trade
            target_team_ids: List of target team IDs for the trade
            max_turns: Maximum negotiation turns allowed
            
        Returns:
            Created trade session model
        """
        import json
        
        try:
            with self.get_session() as session:
                trade_session = TradeSessionModel(
                    session_id=session_id,
                    status=TradeSessionStatus.PENDING,
                    initiating_team_id=initiating_team_id,
                    target_team_ids=json.dumps(target_team_ids),
                    max_turns=max_turns
                )
                
                session.add(trade_session)
                session.commit()
                session.refresh(trade_session)
                
                logger.info(f"Created trade session {session_id} for team {initiating_team_id} -> {target_team_ids}")
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