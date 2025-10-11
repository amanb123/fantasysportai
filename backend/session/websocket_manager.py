"""
WebSocket connection manager for real-time trade negotiation updates.
"""

from typing import Dict, List, Set
import json
import asyncio
import logging
from datetime import datetime
from fastapi import WebSocket, WebSocketDisconnect

from shared.models import AgentMessage

logger = logging.getLogger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""
    
    def __init__(self):
        """Initialize connection manager."""
        # Map session_id -> set of websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Map websocket -> session_id for cleanup
        self.connection_sessions: Dict[WebSocket, str] = {}
    
    async def connect(self, websocket: WebSocket, session_id: str):
        """
        Accept a WebSocket connection for a trade session.
        
        Args:
            websocket: FastAPI WebSocket instance
            session_id: Trade session identifier
        """
        try:
            await websocket.accept()
            
            # Initialize session connections if needed
            if session_id not in self.active_connections:
                self.active_connections[session_id] = set()
            
            # Add connection to session
            self.active_connections[session_id].add(websocket)
            self.connection_sessions[websocket] = session_id
            
            logger.info(f"WebSocket connected to session {session_id}")
            
            # Send connection confirmation
            await self.send_personal_message({
                "type": "connection_confirmed",
                "session_id": session_id,
                "timestamp": datetime.utcnow().isoformat(),
                "message": "Connected to trade negotiation session"
            }, websocket)
            
        except Exception as e:
            logger.error(f"Error connecting WebSocket to session {session_id}: {e}")
    
    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.
        
        Args:
            websocket: FastAPI WebSocket instance
        """
        try:
            # Get session ID for this connection
            session_id = self.connection_sessions.get(websocket)
            
            if session_id and session_id in self.active_connections:
                # Remove from session connections
                self.active_connections[session_id].discard(websocket)
                
                # Clean up empty session
                if not self.active_connections[session_id]:
                    del self.active_connections[session_id]
            
            # Remove from connection mapping
            if websocket in self.connection_sessions:
                del self.connection_sessions[websocket]
            
            logger.info(f"WebSocket disconnected from session {session_id}")
            
        except Exception as e:
            logger.error(f"Error disconnecting WebSocket: {e}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """
        Send a message to a specific WebSocket connection.
        
        Args:
            message: Message dictionary to send
            websocket: Target WebSocket connection
        """
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast_to_session(self, session_id: str, message: dict):
        """
        Broadcast a message to all connections in a session.
        
        Args:
            session_id: Trade session identifier
            message: Message dictionary to broadcast
        """
        try:
            if session_id not in self.active_connections:
                return
            
            # Get list of connections to avoid modification during iteration
            connections = list(self.active_connections[session_id])
            
            # Send to all connections
            disconnected_connections = []
            for connection in connections:
                try:
                    await connection.send_text(json.dumps(message))
                except Exception as e:
                    logger.warning(f"Failed to send message to connection: {e}")
                    disconnected_connections.append(connection)
            
            # Clean up failed connections
            for connection in disconnected_connections:
                self.disconnect(connection)
            
            logger.debug(f"Broadcasted message to {len(connections) - len(disconnected_connections)} connections in session {session_id}")
            
        except Exception as e:
            logger.error(f"Error broadcasting to session {session_id}: {e}")
    
    async def send_agent_message(self, session_id: str, agent_message: AgentMessage):
        """
        Send an agent message to all session connections.
        
        Args:
            session_id: Trade session identifier
            agent_message: Agent message to send
        """
        try:
            message = {
                "type": "agent_message",
                "session_id": session_id,
                "agent_name": agent_message.agent_name,
                "content": agent_message.content,
                "timestamp": agent_message.timestamp.isoformat() if agent_message.timestamp else datetime.utcnow().isoformat()
            }
            
            await self.broadcast_to_session(session_id, message)
            
        except Exception as e:
            logger.error(f"Error sending agent message to session {session_id}: {e}")
    
    async def send_status_update(self, session_id: str, status: str, current_turn: int, max_turns: int, message: str = ""):
        """
        Send a status update to all session connections.
        
        Args:
            session_id: Trade session identifier
            status: Current session status
            current_turn: Current negotiation turn
            max_turns: Maximum negotiation turns
            message: Status message
        """
        try:
            update = {
                "type": "status_update",
                "session_id": session_id,
                "status": status,
                "current_turn": current_turn,
                "max_turns": max_turns,
                "progress": min((current_turn / max_turns) * 100, 100.0) if max_turns > 0 else 0,
                "message": message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.broadcast_to_session(session_id, update)
            
        except Exception as e:
            logger.error(f"Error sending status update to session {session_id}: {e}")
    
    async def send_negotiation_complete(self, session_id: str, consensus_reached: bool, 
                                       trade_approved: bool, summary: str):
        """
        Send negotiation completion notification.
        
        Args:
            session_id: Trade session identifier
            consensus_reached: Whether agents reached consensus
            trade_approved: Whether trade was approved
            summary: Summary of negotiation results
        """
        try:
            message = {
                "type": "negotiation_complete",
                "session_id": session_id,
                "consensus_reached": consensus_reached,
                "trade_approved": trade_approved,
                "summary": summary,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.broadcast_to_session(session_id, message)
            
        except Exception as e:
            logger.error(f"Error sending completion notification to session {session_id}: {e}")
    
    async def send_error_message(self, session_id: str, error_message: str):
        """
        Send an error message to all session connections.
        
        Args:
            session_id: Trade session identifier
            error_message: Error message to send
        """
        try:
            message = {
                "type": "error",
                "session_id": session_id,
                "error": error_message,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.broadcast_to_session(session_id, message)
            
        except Exception as e:
            logger.error(f"Error sending error message to session {session_id}: {e}")
    
    def get_session_connection_count(self, session_id: str) -> int:
        """
        Get number of active connections for a session.
        
        Args:
            session_id: Trade session identifier
            
        Returns:
            Number of active connections
        """
        return len(self.active_connections.get(session_id, set()))
    
    def get_active_sessions(self) -> List[str]:
        """
        Get list of sessions with active connections.
        
        Returns:
            List of session IDs with active connections
        """
        return list(self.active_connections.keys())
    
    async def ping_connections(self, session_id: str):
        """
        Send ping to all connections in a session to keep alive.
        
        Args:
            session_id: Trade session identifier
        """
        try:
            message = {
                "type": "ping",
                "timestamp": datetime.utcnow().isoformat()
            }
            
            await self.broadcast_to_session(session_id, message)
            
        except Exception as e:
            logger.error(f"Error pinging connections in session {session_id}: {e}")


# Global connection manager instance
websocket_manager = ConnectionManager()


async def handle_websocket_connection(websocket: WebSocket, session_id: str):
    """
    Handle a WebSocket connection for trade negotiation updates.
    
    Args:
        websocket: FastAPI WebSocket instance
        session_id: Trade session identifier
    """
    await websocket_manager.connect(websocket, session_id)
    
    try:
        # Keep connection alive and handle any incoming messages
        while True:
            try:
                # Wait for messages (though we don't expect many from client)
                message = await websocket.receive_text()
                
                # Parse message if needed
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    # Handle different message types
                    if message_type == "ping":
                        # Respond to ping
                        await websocket_manager.send_personal_message({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }, websocket)
                    
                    elif message_type == "subscribe_updates":
                        # Client requesting updates (already subscribed by connection)
                        await websocket_manager.send_personal_message({
                            "type": "subscription_confirmed",
                            "session_id": session_id,
                            "timestamp": datetime.utcnow().isoformat()
                        }, websocket)
                    
                except json.JSONDecodeError:
                    # Ignore invalid JSON messages
                    logger.warning(f"Received invalid JSON from WebSocket in session {session_id}")
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message in session {session_id}: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error in WebSocket connection for session {session_id}: {e}")
    finally:
        websocket_manager.disconnect(websocket)