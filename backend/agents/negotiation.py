"""
Trade negotiation orchestration using AutoGen RoundRobinGroupChat.
"""

from typing import List, Dict, Any, Optional, Callable
# Temporarily mock autogen imports for testing
class GroupChat:
    pass

class GroupChatManager:
    pass
import asyncio
import json
import logging

from backend.config import settings
from backend.session.repository import BasketballRepository
from backend.session.models import TradeSessionStatus
from shared.models import TradeProposal, TradeDecision, AgentMessage
from .agent_factory import AgentFactory
from .utils import parse_agent_response, create_trade_summary

logger = logging.getLogger(__name__)


class TradeNegotiationOrchestrator:
    """Orchestrates multi-agent trade negotiations using AutoGen."""
    
    def __init__(self, repository: BasketballRepository):
        """Initialize orchestrator with repository."""
        self.repository = repository
        self.agent_factory = AgentFactory()
        self.active_sessions: Dict[str, GroupChat] = {}
    
    async def start_negotiation(self, session_id: str, user_id: int, initiating_team_id: int, 
                               target_team_ids: List[int], trade_preferences: Dict[str, Any],
                               progress_callback: Optional[Callable[[int, int, str], None]] = None,
                               message_callback: Optional[Callable[[AgentMessage], None]] = None) -> bool:
        """
        Start a multi-agent trade negotiation session.
        
        Args:
            session_id: Unique session identifier
            user_id: ID of the user creating the session
            initiating_team_id: ID of team starting the negotiation
            target_team_ids: List of target team IDs
            trade_preferences: Trade preferences from initiating team
            message_callback: Optional callback for real-time message updates
            
        Returns:
            True if negotiation started successfully, False otherwise
        """
        try:
            # Create trade session in database
            trade_session = self.repository.create_trade_session(
                session_id=session_id,
                user_id=user_id,
                initiating_team_id=initiating_team_id,
                target_team_ids=target_team_ids,
                max_turns=settings.MAX_NEGOTIATION_TURNS
            )
            
            # Get team information for all participating teams
            all_team_ids = [initiating_team_id] + target_team_ids
            team_agents = []
            team_info = {}
            
            for team_id in all_team_ids:
                # Get team data using repository method that handles session correctly
                team_with_stats = self.repository.get_teams_with_stats()
                team_data = next((t for t in team_with_stats if t.id == team_id), None)
                if not team_data:
                    logger.error(f"Team {team_id} not found")
                    return False
                
                # Use method that handles session correctly for players
                team_players_data = self.repository.get_team_players_with_team_info(team_id)
                roster_info = {
                    "total_salary": team_data.total_salary,
                    "players": team_players_data["players"]
                }
                
                # Create team agent with appropriate trade preferences
                if team_id == initiating_team_id:
                    # Use provided trade preferences for initiating team
                    team_trade_preference = trade_preferences
                else:
                    # Create reasonable defaults for other teams based on roster needs
                    team_trade_preference = self._derive_team_preferences(roster_info)
                
                agent = self.agent_factory.create_team_agent(team_data.name, team_id, roster_info, team_trade_preference)
                team_agents.append(agent)
                team_info[team_id] = {"name": team_data.name, "agent": agent}
            
            # Create commissioner agent
            commissioner = self.agent_factory.create_commissioner_agent()
            
            # Create user proxy for orchestration
            user_proxy = self.agent_factory.create_user_proxy(session_id)
            
            # Set up group chat with round-robin pattern
            all_agents = team_agents + [commissioner]
            group_chat = GroupChat(
                agents=all_agents,
                messages=[],
                max_round=settings.agent_max_turns,
                speaker_selection_method="round_robin",
                allow_repeat_speaker=False
            )
            
            # Create group chat manager
            manager = GroupChatManager(
                groupchat=group_chat,
                llm_config=self.agent_factory.llm_config
            )
            
            # Store active session
            self.active_sessions[session_id] = group_chat
            
            # Update session status to in progress
            self.repository.update_trade_session_status(session_id, TradeSessionStatus.IN_PROGRESS)
            
            # Create initial negotiation prompt
            initial_prompt = self._create_initial_prompt(
                initiating_team_id, target_team_ids, trade_preferences, team_info
            )
            
            # Start negotiation in background
            asyncio.create_task(
                self._run_negotiation(
                    session_id, user_proxy, manager, initial_prompt, progress_callback, message_callback
                )
            )
            
            logger.info(f"Started trade negotiation session {session_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting negotiation for session {session_id}: {e}")
            self.repository.update_trade_session_status(
                session_id, TradeSessionStatus.FAILED, error_message=str(e)
            )
            return False
    
    async def _run_negotiation(self, session_id: str, user_proxy, manager, 
                              initial_prompt: str, progress_callback: Optional[Callable] = None,
                              message_callback: Optional[Callable] = None):
        """
        Run the actual negotiation process with real-time streaming.
        
        Args:
            session_id: Session identifier
            user_proxy: AutoGen UserProxyAgent
            manager: AutoGen GroupChatManager
            initial_prompt: Initial negotiation prompt
            progress_callback: Optional callback for progress updates
            message_callback: Optional callback for real-time message updates
        """
        try:
            # Setup real-time message streaming hook
            group_chat = self.active_sessions.get(session_id)
            if group_chat and (progress_callback or message_callback):
                # Add message hook for real-time streaming
                original_append = group_chat.messages.append
                
                def streaming_append(message):
                    # Call original append first
                    result = original_append(message)
                    
                    # Stream message in real-time
                    asyncio.create_task(self._stream_message_realtime(
                        session_id, message, len(group_chat.messages), 
                        progress_callback, message_callback
                    ))
                    
                    return result
                
                group_chat.messages.append = streaming_append
            
            # Create custom termination condition for consensus keyword
            def termination_condition(messages):
                """Check for early consensus termination via keyword detection."""
                if not messages:
                    return False
                
                # Check the latest message for consensus keyword
                latest_message = messages[-1]
                content = latest_message.get("content", "").upper()
                
                if settings.agent_consensus_keyword in content:
                    logger.info(f"Consensus keyword '{settings.agent_consensus_keyword}' detected - terminating negotiation early")
                    return True
                
                return False
            
            # Add termination condition to group chat
            group_chat.termination_condition = termination_condition
            
            # Start the group chat conversation with consensus termination capability  
            await user_proxy.a_initiate_chat(
                manager,
                message=initial_prompt,
                max_turns=settings.agent_max_turns
            )
            
            # Process final conversation results
            if group_chat:
                await self._process_negotiation_results(session_id, group_chat, progress_callback, message_callback)
            
        except Exception as e:
            logger.error(f"Error during negotiation for session {session_id}: {e}")
            self.repository.update_trade_session_status(
                session_id, TradeSessionStatus.FAILED, error_message=str(e)
            )
        finally:
            # Clean up active session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]
    
    async def _stream_message_realtime(self, session_id: str, message: Dict[str, Any], 
                                       turn_number: int, progress_callback: Optional[Callable] = None,
                                       message_callback: Optional[Callable] = None):
        """
        Stream individual message in real-time as it's generated.
        
        Args:
            session_id: Session identifier
            message: AutoGen message dictionary
            turn_number: Current turn number
            progress_callback: Optional progress callback
            message_callback: Optional message callback
        """
        try:
            agent_name = message.get("name", "Unknown")
            content = message.get("content", "")
            
            # Create and stream AgentMessage
            agent_message = AgentMessage(
                agent_name=agent_name,
                content=content,
                timestamp=message.get("timestamp", None)
            )
            
            # Save message to database immediately
            self.repository.add_conversation_message(
                session_id=session_id,
                agent_name=agent_name,
                content=content,
                turn_number=turn_number
            )
            
            # Stream message via callback
            if message_callback:
                message_callback(agent_message)
            
            # Update progress
            if progress_callback:
                progress_callback(turn_number, -1, f"message_from_{agent_name}")
                
            logger.info(f"Streamed real-time message from {agent_name} in session {session_id}, turn {turn_number}")
            
        except Exception as e:
            logger.warning(f"Failed to stream message in real-time for session {session_id}: {e}")
    
    async def _process_negotiation_results(self, session_id: str, group_chat: GroupChat, 
                                          progress_callback: Optional[Callable] = None,
                                          message_callback: Optional[Callable] = None):
        """
        Process the results of a completed negotiation (messages already streamed real-time).
        
        Args:
            session_id: Session identifier
            group_chat: Completed GroupChat instance
            progress_callback: Optional callback for final progress updates
            message_callback: Optional callback for any missing message updates
        """
        try:
            conversation_messages = []
            trade_decision = None
            consensus_reached = False
            
            # Process all messages to extract final trade decision
            # Note: Messages have already been streamed in real-time via _stream_message_realtime
            for i, message in enumerate(group_chat.messages):
                agent_name = message.get("name", "Unknown")
                content = message.get("content", "")
                current_turn = i + 1
                
                # Create agent message for final processing
                agent_message = AgentMessage(
                    agent_name=agent_name,
                    content=content,
                    timestamp=message.get("timestamp", None)
                )
                conversation_messages.append(agent_message)
                
                # Check if this is a final trade decision
                parsed_response = parse_agent_response(content)
                if parsed_response and parsed_response.get("type") == "trade_decision":
                    decision_data = parsed_response.get("data", {})
                    
                    # Build TradeDecision only when all required fields are present
                    if "consensus_reached" in decision_data or "approved" in decision_data:
                        try:
                            # Try to create full TradeDecision
                            trade_decision = TradeDecision(**decision_data)
                            consensus_reached = trade_decision.consensus_reached
                        except Exception as e:
                            logger.warning(f"Failed to create TradeDecision from {decision_data}: {e}")
                            # Create fallback with all required fields including approved=False
                            trade_decision = TradeDecision(
                                approved=False,
                                offering_team_id=0,
                                receiving_team_id=0,
                                traded_players_out=[],
                                traded_players_in=[],
                                consensus_reached=False,
                                rejection_reasons=[f"Failed to parse decision: {str(e)}"],
                                commissioner_notes=f"Parsing error: {str(e)}"
                            )
                            consensus_reached = False
            
            # If no trade decision found, use extractor agent
            if not trade_decision:
                trade_decision = await self._extract_trade_decision_with_agent(session_id, conversation_messages)            # Update session progress and persist final result
            total_turns = len(group_chat.messages)
            self.repository.update_trade_session_status(
                session_id, TradeSessionStatus.COMPLETED, current_turn=total_turns
            )
            
            # Save final results - serialize entire TradeDecision to JSON
            trade_decision_json = None
            if trade_decision:
                trade_decision_json = json.dumps(trade_decision.dict())
            
            self.repository.save_trade_result(
                session_id=session_id,
                consensus_reached=trade_decision.consensus_reached if trade_decision else False,
                trade_decision_json=trade_decision_json,
                commissioner_notes=trade_decision.commissioner_notes if trade_decision else None,
                total_turns=total_turns,
                final_consensus=consensus_reached
            )
            
            # Broadcast completion via progress callback
            if progress_callback:
                progress_callback(total_turns, total_turns, "completed")
            
            logger.info(f"Completed negotiation for session {session_id}: {'Success' if consensus_reached else 'No consensus'}")
            
        except Exception as e:
            logger.error(f"Error processing negotiation results for session {session_id}: {e}")
            self.repository.update_trade_session_status(
                session_id, TradeSessionStatus.FAILED, error_message=str(e)
            )
    
    def get_session_status(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a trade negotiation session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session status dictionary or None if not found
        """
        try:
            trade_session = self.repository.get_trade_session(session_id)
            if not trade_session:
                return None
            
            return {
                "session_id": session_id,
                "status": trade_session.status.value,
                "current_turn": trade_session.current_turn,
                "max_turns": trade_session.max_turns,
                "is_active": session_id in self.active_sessions,
                "started_at": trade_session.started_at,
                "completed_at": trade_session.completed_at
            }
            
        except Exception as e:
            logger.error(f"Error getting session status for {session_id}: {e}")
            return None
    
    def _create_initial_prompt(self, initiating_team_id: int, target_team_ids: List[int], 
                              trade_preferences: Dict[str, Any], team_info: Dict[int, Dict]) -> str:
        """
        Create the initial prompt to start trade negotiations.
        
        Args:
            initiating_team_id: ID of initiating team
            target_team_ids: List of target team IDs
            trade_preferences: Trade preferences
            team_info: Team information dictionary
            
        Returns:
            Formatted initial prompt string
        """
        initiating_team_name = team_info[initiating_team_id]["name"]
        target_team_names = [team_info[tid]["name"] for tid in target_team_ids]
        
        prompt_parts = [
            f"## NBA Trade Negotiation Session",
            f"",
            f"The {initiating_team_name} has initiated a trade negotiation.",
            f"Participating teams: {', '.join([initiating_team_name] + target_team_names)}",
            f"",
            f"## Trade Preferences from {initiating_team_name}:",
        ]
        
        # Add trade preferences details
        if "desired_positions" in trade_preferences:
            positions = ", ".join(trade_preferences["desired_positions"])
            prompt_parts.append(f"- Seeking players at positions: {positions}")
        
        if "salary_range" in trade_preferences:
            salary_range = trade_preferences["salary_range"]
            # Handle both dict and Pydantic object formats for salary_range
            min_salary = salary_range.get('min', 0) if isinstance(salary_range, dict) else getattr(salary_range, 'min', 0) if hasattr(salary_range, 'min') else 0
            max_salary = salary_range.get('max', 0) if isinstance(salary_range, dict) else getattr(salary_range, 'max', 0) if hasattr(salary_range, 'max') else 0
            prompt_parts.append(f"- Salary range: ${min_salary:,} - ${max_salary:,}")
        
        if "players_offered" in trade_preferences:
            offered_players = ", ".join([p["name"] for p in trade_preferences["players_offered"]])
            prompt_parts.append(f"- Players offered: {offered_players}")
        
        # Build prompts dynamically from settings
        prompt_parts.extend([
            f"",
            f"## Negotiation Guidelines:",
            f"1. Each team agent should present their position and trade interests",
            f"2. Discuss player values, team needs, and potential trade scenarios", 
            f"3. Work toward a mutually beneficial trade proposal",
            f"4. The Commissioner will evaluate any final proposals for league approval",
            f"5. Consider salary cap constraints, roster requirements, and competitive balance",
            f"6. Use '{settings.agent_consensus_keyword}' when reaching final consensus",
            f"",
            f"## League Rules:",
            f"- Salary cap: ${settings.salary_cap:,} per team",
            f"- Roster size: Exactly 13 players",
            f"- Position requirements: PG, SG, G, SF, PF, F, C, 2×UTIL, 3×BENCH",
            f"- Maximum negotiation turns: {settings.agent_max_turns}",
            f"",
            f"Let's begin the negotiation. {initiating_team_name}, please start by presenting your trade interests."
        ])
        
        return "\n".join(prompt_parts)
    
    def _derive_team_preferences(self, roster_info: Dict[str, Any]) -> Dict[str, Any]:
        """
        Derive reasonable trade preferences for non-initiating teams based on roster.
        
        Args:
            roster_info: Team roster and salary information
            
        Returns:
            Dictionary of derived trade preferences
        """
        # Handle both dict and Pydantic object formats
        def safe_get(obj, key, default=None):
            if hasattr(obj, key):
                return getattr(obj, key)
            elif isinstance(obj, dict):
                return obj.get(key, default)
            return default
        
        players = safe_get(roster_info, 'players', [])
        total_salary = safe_get(roster_info, 'total_salary', 0)
        
        # Analyze position distribution
        position_counts = {}
        for player in players:
            pos = safe_get(player, 'position', 'Unknown')
            position_counts[pos] = position_counts.get(pos, 0) + 1
        
        # Identify needs based on 13-slot requirements
        desired_positions = []
        if position_counts.get('PG', 0) < 2:
            desired_positions.append('PG')
        if position_counts.get('SG', 0) < 2:
            desired_positions.append('SG')
        if position_counts.get('SF', 0) < 2:
            desired_positions.append('SF')
        if position_counts.get('PF', 0) < 2:
            desired_positions.append('PF')
        if position_counts.get('C', 0) < 2:
            desired_positions.append('C')
        
        # Determine budget range based on cap space
        cap_space = settings.salary_cap - total_salary
        
        return {
            'desired_positions': desired_positions,
            'budget_range': {
                'min': min(1_000_000, cap_space // 4),
                'max': min(cap_space, 15_000_000)
            },
            'notes': f"Looking to improve depth at {', '.join(desired_positions) if desired_positions else 'all positions'}"
        }
    
    async def _extract_trade_decision_with_agent(self, session_id: str, conversation_messages: List[AgentMessage]) -> Optional[TradeDecision]:
        """
        Use extractor agent to convert conversation into TradeDecision.
        
        Args:
            session_id: Session identifier
            conversation_messages: List of conversation messages
            
        Returns:
            Extracted TradeDecision or None if extraction fails
        """
        try:
            # Create extractor agent
            extractor = self.agent_factory.create_extractor_agent()
            
            # Format conversation for extraction
            conversation_text = "\n".join([
                f"{msg.agent_name}: {msg.content}" for msg in conversation_messages
            ])
            
            extraction_prompt = f"""
Please analyze this trade negotiation conversation and extract the final trade decision.

Conversation:
{conversation_text}

Please provide the final trade decision in the specified JSON format. If no clear decision was reached, set approved=false and explain in commissioner_notes.
"""
            
            # Get extraction response
            response = await extractor.a_generate_reply(
                messages=[{"role": "user", "content": extraction_prompt}],
                sender=None
            )
            
            # Parse the response
            if response:
                parsed = parse_agent_response(response)
                if parsed and parsed.get("type") == "trade_decision":
                    decision_data = parsed.get("data", {})
                    return TradeDecision(**decision_data)
            
            # Fallback decision with all required fields
            return TradeDecision(
                approved=False,
                offering_team_id=0,
                receiving_team_id=0,
                traded_players_out=[],
                traded_players_in=[],
                consensus_reached=False,
                rejection_reasons=["Could not extract clear trade decision from conversation"],
                commissioner_notes="Extraction failed - no clear decision found"
            )
            
        except Exception as e:
            logger.error(f"Error extracting trade decision for session {session_id}: {e}")
            return TradeDecision(
                approved=False,
                offering_team_id=0,
                receiving_team_id=0,
                traded_players_out=[],
                traded_players_in=[],
                consensus_reached=False,
                rejection_reasons=[f"Extraction error: {str(e)}"],
                commissioner_notes=f"Extraction failed: {str(e)}"
            )