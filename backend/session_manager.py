"""
Session manager for handling trade negotiation sessions.
"""

from typing import Dict, List, Optional, Callable
import uuid
import asyncio
import logging
from datetime import datetime

from backend.session.repository import BasketballRepository
from backend.session.models import TradeSessionStatus
from shared.models import TradePreferenceRequest, AgentMessage
from backend.agents.negotiation import TradeNegotiationOrchestrator

logger = logging.getLogger(__name__)


class TradeSessionManager:
    """Manages trade negotiation sessions and their lifecycle."""
    
    def __init__(self, repository: BasketballRepository):
        """Initialize session manager with repository."""
        self.repository = repository
        self.orchestrator = TradeNegotiationOrchestrator(repository)
        self.active_sessions: Dict[str, Dict] = {}
        self.session_callbacks: Dict[str, List[Callable]] = {}
    
    async def create_trade_session(self, user_id: int, trade_preference: TradePreferenceRequest) -> tuple[str, bool]:
        """
        Create a new trade negotiation session.
        
        Args:
            user_id: ID of the user creating the session
            trade_preference: Trade preference request from initiating team
            
        Returns:
            Tuple of (session_id, success_flag)
        """
        try:
            # Generate unique session ID
            session_id = f"trade_{uuid.uuid4().hex[:12]}"
            
            # Validate initiating team exists
            initiating_team = self.repository.get_team_by_id(trade_preference.team_id)
            if not initiating_team:
                logger.error(f"Initiating team {trade_preference.team_id} not found")
                return session_id, False
            
            # Validate target teams exist
            for target_team_id in trade_preference.target_team_ids:
                target_team = self.repository.get_team_by_id(target_team_id)
                if not target_team:
                    logger.error(f"Target team {target_team_id} not found")
                    return session_id, False
            
            # Create the DB session record first to guarantee persistence before any callbacks
            max_turns = trade_preference.max_turns if hasattr(trade_preference, 'max_turns') else 10
            try:
                db_session = self.repository.create_trade_session(
                    session_id, user_id, trade_preference.team_id, 
                    trade_preference.target_team_ids, max_turns
                )
                logger.info(f"Created DB session record for {session_id}")
            except Exception as e:
                logger.error(f"Failed to create DB session record for {session_id}: {e}")
                return session_id, False
            
            # Store session info in memory
            self.active_sessions[session_id] = {
                "initiating_team_id": trade_preference.team_id,
                "target_team_ids": trade_preference.target_team_ids,
                "preferences": trade_preference.dict(),
                "status": TradeSessionStatus.PENDING,
                "created_at": datetime.utcnow(),
                "callbacks": []
            }
            
            # Initialize callback list for this session
            self.session_callbacks[session_id] = []
            
            # Create progress and message callbacks
            def progress_callback(current_turn: int, max_turns: int, status: str):
                # Update session status in DB
                self.repository.update_trade_session_status(
                    session_id, TradeSessionStatus.IN_PROGRESS, current_turn
                )
                # Notify WebSocket connections
                from backend.websocket_manager import connection_manager
                asyncio.create_task(
                    connection_manager.broadcast_status_update(
                        session_id, status, current_turn, max_turns
                    )
                )
            
            def message_callback(agent_message: AgentMessage):
                # Save message to DB
                self.repository.add_conversation_message(
                    session_id, agent_message.agent_name, 
                    agent_message.content, 0  # Turn number will be updated by progress callback
                )
                # Broadcast to WebSocket connections
                from backend.websocket_manager import connection_manager
                asyncio.create_task(
                    connection_manager.broadcast_agent_message(session_id, agent_message)
                )
            
            # Start the negotiation
            success = await self.orchestrator.start_negotiation(
                session_id=session_id,
                user_id=user_id,
                initiating_team_id=trade_preference.team_id,
                target_team_ids=trade_preference.target_team_ids,
                trade_preferences=trade_preference.dict(),
                progress_callback=progress_callback,
                message_callback=message_callback
            )
            
            if success:
                self.active_sessions[session_id]["status"] = TradeSessionStatus.IN_PROGRESS
                logger.info(f"Created trade session {session_id}")
            else:
                self.active_sessions[session_id]["status"] = TradeSessionStatus.FAILED
                logger.error(f"Failed to start negotiation for session {session_id}")
            
            return session_id, success
            
        except Exception as e:
            logger.error(f"Error creating trade session: {e}")
            return session_id, False
    
    def get_session_messages(self, session_id: str) -> List[AgentMessage]:
        """
        Get conversation messages for a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of agent messages
        """
        try:
            trade_session = self.repository.get_trade_session(session_id)
            if not trade_session:
                return []
            
            messages = []
            for msg in trade_session.messages:
                messages.append(msg.to_pydantic())
            
            # Sort by timestamp
            messages.sort(key=lambda x: x.timestamp)
            return messages
            
        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []