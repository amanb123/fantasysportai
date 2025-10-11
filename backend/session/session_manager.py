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
    
    async def create_trade_session(self, trade_preference: TradePreferenceRequest) -> tuple[str, bool]:
        """
        Create a new trade negotiation session.
        
        Args:
            trade_preference: Trade preference request from initiating team
            
        Returns:
            Tuple of (session_id, success_flag)
        """
        try:
            # Generate unique session ID
            session_id = f"trade_{uuid.uuid4().hex[:12]}"
            
            # Validate initiating team exists
            initiating_team = self.repository.get_team_by_id(trade_preference.initiating_team_id)
            if not initiating_team:
                logger.error(f"Initiating team {trade_preference.initiating_team_id} not found")
                return session_id, False
            
            # Validate target teams exist
            for target_team_id in trade_preference.target_team_ids:
                target_team = self.repository.get_team_by_id(target_team_id)
                if not target_team:
                    logger.error(f"Target team {target_team_id} not found")
                    return session_id, False
            
            # Store session info
            self.active_sessions[session_id] = {
                "initiating_team_id": trade_preference.initiating_team_id,
                "target_team_ids": trade_preference.target_team_ids,
                "preferences": trade_preference.dict(),
                "status": TradeSessionStatus.PENDING,
                "created_at": datetime.utcnow(),
                "callbacks": []
            }
            
            # Initialize callback list for this session
            self.session_callbacks[session_id] = []
            
            # Start the negotiation
            success = await self.orchestrator.start_negotiation(
                session_id=session_id,
                initiating_team_id=trade_preference.initiating_team_id,
                target_team_ids=trade_preference.target_team_ids,
                trade_preferences=trade_preference.dict(),
                message_callback=self._create_message_callback(session_id)
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
    
    def get_session_status(self, session_id: str) -> Optional[Dict]:
        """
        Get current status of a trade session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status dictionary or None if not found
        """
        try:
            # Check active sessions first
            if session_id in self.active_sessions:
                session_info = self.active_sessions[session_id]
                return {
                    "session_id": session_id,
                    "status": session_info["status"].value if hasattr(session_info["status"], "value") else str(session_info["status"]),
                    "is_active": True,
                    "created_at": session_info["created_at"]
                }
            
            # Check database for completed sessions
            orchestrator_status = self.orchestrator.get_session_status(session_id)
            if orchestrator_status:
                return orchestrator_status
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting session status for {session_id}: {e}")
            return None
    
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
    
    def add_message_callback(self, session_id: str, callback: Callable[[AgentMessage], None]):
        """
        Add a callback for real-time message updates.
        
        Args:
            session_id: Session identifier
            callback: Callback function to receive message updates
        """
        try:
            if session_id not in self.session_callbacks:
                self.session_callbacks[session_id] = []
            
            self.session_callbacks[session_id].append(callback)
            logger.info(f"Added message callback for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error adding callback for session {session_id}: {e}")
    
    def remove_message_callback(self, session_id: str, callback: Callable[[AgentMessage], None]):
        """
        Remove a message callback.
        
        Args:
            session_id: Session identifier  
            callback: Callback function to remove
        """
        try:
            if session_id in self.session_callbacks:
                if callback in self.session_callbacks[session_id]:
                    self.session_callbacks[session_id].remove(callback)
                    logger.info(f"Removed message callback for session {session_id}")
            
        except Exception as e:
            logger.error(f"Error removing callback for session {session_id}: {e}")
    
    def cleanup_session(self, session_id: str):
        """
        Clean up resources for a completed session.
        
        Args:
            session_id: Session identifier
        """
        try:
            # Remove from active sessions
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
            
            # Clear callbacks
            if session_id in self.session_callbacks:
                del self.session_callbacks[session_id]
            
            logger.info(f"Cleaned up session {session_id}")
            
        except Exception as e:
            logger.error(f"Error cleaning up session {session_id}: {e}")
    
    def _create_message_callback(self, session_id: str) -> Callable[[AgentMessage], None]:
        """
        Create a message callback for a specific session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Callback function for agent messages
        """
        def callback(message: AgentMessage):
            try:
                # Notify all registered callbacks for this session
                if session_id in self.session_callbacks:
                    for cb in self.session_callbacks[session_id]:
                        try:
                            cb(message)
                        except Exception as e:
                            logger.error(f"Error in message callback for session {session_id}: {e}")
                            
            except Exception as e:
                logger.error(f"Error in message callback wrapper for session {session_id}: {e}")
        
        return callback
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of currently active session IDs.
        
        Returns:
            List of active session identifiers
        """
        return list(self.active_sessions.keys())
    
    def get_session_summary(self, session_id: str) -> Optional[Dict]:
        """
        Get a summary of session information.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session summary dictionary or None if not found
        """
        try:
            trade_session = self.repository.get_trade_session(session_id)
            if not trade_session:
                return None
            
            # Get team names
            initiating_team = self.repository.get_team_by_id(trade_session.initiating_team_id)
            
            import json
            target_team_ids = json.loads(trade_session.target_team_ids)
            target_teams = []
            for tid in target_team_ids:
                team = self.repository.get_team_by_id(tid)
                if team:
                    target_teams.append(team.name)
            
            return {
                "session_id": session_id,
                "initiating_team": initiating_team.name if initiating_team else "Unknown",
                "target_teams": target_teams,
                "status": trade_session.status.value,
                "current_turn": trade_session.current_turn,
                "max_turns": trade_session.max_turns,
                "started_at": trade_session.started_at,
                "completed_at": trade_session.completed_at,
                "consensus_reached": trade_session.consensus_reached,
                "message_count": len(trade_session.messages) if trade_session.messages else 0
            }
            
        except Exception as e:
            logger.error(f"Error getting session summary for {session_id}: {e}")
            return None