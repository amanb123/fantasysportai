"""
Agent factory for creating AutoGen agents for trade negotiations.
"""

from typing import List, Dict, Any
from autogen import AssistantAgent, UserProxyAgent
import logging

from backend.config import settings
from .personas import TEAM_AGENT_PERSONAS, COMMISSIONER_PERSONA

logger = logging.getLogger(__name__)


class AgentFactory:
    """Factory for creating AutoGen agents with appropriate configurations."""
    
    def __init__(self):
        """Initialize agent factory with configuration."""
        pass  # Configuration is now handled by get_llm_config() method
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration for older AutoGen version.
        
        Returns:
            LLM configuration dict
        """
        try:
            # Try Ollama first (if available)
            if hasattr(settings, 'ollama_model') and settings.ollama_model:
                logger.info(f"✅ Attempting to use Ollama with model {settings.ollama_model}")
                # For older AutoGen, we can try using custom config for Ollama
                return {
                    "config_list": [
                        {
                            "model": settings.ollama_model,
                            "api_key": "not-needed-for-ollama",
                            "base_url": f"{settings.ollama_host}/v1" if hasattr(settings, 'ollama_host') else "http://localhost:11434/v1"
                        }
                    ],
                    "temperature": settings.AGENT_TEMPERATURE,
                    "timeout": settings.AGENT_TIMEOUT,
                    "seed": settings.AGENT_SEED
                }
        except Exception as e:
            logger.warning(f"Ollama configuration failed: {e}")
            
        # Fallback to OpenAI
        if not settings.OPENAI_API_KEY:
            logger.warning("No OpenAI API key configured, using placeholder config")
            return {
                "config_list": [
                    {
                        "model": "gpt-3.5-turbo",
                        "api_key": "placeholder-key"
                    }
                ],
                "temperature": 0.7
            }
            
        logger.info(f"🔄 Using OpenAI backend with model {settings.OPENAI_MODEL}")
        return {
            "config_list": [
                {
                    "model": settings.OPENAI_MODEL,
                    "api_key": settings.OPENAI_API_KEY,
                    "base_url": settings.OPENAI_BASE_URL
                }
            ],
            "temperature": settings.AGENT_TEMPERATURE,
            "timeout": settings.AGENT_TIMEOUT,
            "seed": settings.AGENT_SEED
        }
    
    def create_team_agent(self, team_name: str, team_id: int, roster_info: Dict[str, Any], trade_preference: Dict[str, Any]) -> AssistantAgent:
        """
        Create a team negotiation agent.
        
        Args:
            team_name: Name of the team
            team_id: Team identifier
            roster_info: Current team roster and salary information
            
        Returns:
            Configured AutoGen AssistantAgent for the team
        """
        try:
            # Use personalized system message from personas module
            from .personas import get_team_agent_system_message
            from backend.config import settings
            
            system_message = get_team_agent_system_message(
                team_name=team_name,
                roster_data=roster_info,
                trade_preference=trade_preference,
                consensus_keyword=settings.agent_consensus_keyword
            )
            
            agent = AssistantAgent(
                name=f"{team_name}_Agent",
                system_message=system_message,
                llm_config=self.get_llm_config(),
                description=f"NBA team agent representing {team_name} in trade negotiations"
            )
            
            logger.info(f"Created team agent for {team_name} (ID: {team_id})")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating team agent for {team_name}: {e}")
            raise
    
    def create_commissioner_agent(self) -> AssistantAgent:
        """
        Create the league commissioner agent for trade approval.
        
        Returns:
            Configured AutoGen AssistantAgent for commissioner
        """
        try:
            # Use personalized system message from personas module
            from .personas import get_commissioner_system_message
            from backend.config import settings
            
            # Get all teams data (simplified for now)
            all_teams_data = {}  # Will be populated by caller with actual team data
            
            system_message = get_commissioner_system_message(
                all_teams_data=all_teams_data,
                salary_cap=settings.salary_cap,
                consensus_keyword=settings.agent_consensus_keyword
            )
            
            agent = AssistantAgent(
                name="Commissioner_Agent",
                system_message=system_message,
                llm_config=self.get_llm_config(),
                description="NBA league commissioner agent for trade validation and approval"
            )
            
            logger.info("Created commissioner agent")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating commissioner agent: {e}")
            raise
    
    def create_extractor_agent(self) -> AssistantAgent:
        """
        Create a lightweight reporter/extractor agent for trade decision conversion.
        
        Returns:
            Configured AutoGen AssistantAgent for extraction
        """
        try:
            system_message = """You are a Trade Decision Extractor responsible for converting trade negotiations into structured TradeDecision objects.

Your Role:
- Analyze completed trade negotiations
- Extract final trade proposals and decisions
- Convert conversations into structured JSON format matching shared.models.TradeDecision exactly
- Handle cases where extraction fails gracefully

Instructions:
- Review the conversation history carefully
- Identify the final agreed-upon trade proposal
- Format the output as a valid TradeDecision JSON object
- Include ALL required fields: approved, offering_team_id, receiving_team_id, traded_players_out, traded_players_in, consensus_reached, rejection_reasons, commissioner_notes
- If extraction fails, create a fallback with approved=false, consensus_reached=false and detailed rejection_reasons

Output Format (must match shared.models.TradeDecision exactly):
```json
{
  "approved": true,
  "offering_team_id": 1,
  "receiving_team_id": 2,
  "traded_players_out": [
    {
      "id": 101,
      "name": "LeBron James",
      "team_id": 1,
      "position": "SF",
      "salary": 44500000,
      "stats": {
        "points_per_game": 25.3,
        "rebounds_per_game": 7.3,
        "assists_per_game": 7.4,
        "steals_per_game": 1.3,
        "blocks_per_game": 0.6,
        "turnovers_per_game": 3.5,
        "field_goal_percentage": 0.501,
        "three_point_percentage": 0.325
      }
    }
  ],
  "traded_players_in": [
    {
      "id": 201,
      "name": "Stephen Curry",
      "team_id": 2,
      "position": "PG",
      "salary": 51900000,
      "stats": {
        "points_per_game": 26.4,
        "rebounds_per_game": 4.5,
        "assists_per_game": 5.1,
        "steals_per_game": 0.9,
        "blocks_per_game": 0.4,
        "turnovers_per_game": 3.2,
        "field_goal_percentage": 0.427,
        "three_point_percentage": 0.408
      }
    }
  ],
  "consensus_reached": true,
  "rejection_reasons": [],
  "commissioner_notes": "Approved trade benefiting both teams"
}
```

CRITICAL: Always include the 'approved' field and complete PlayerResponse objects with full stats. Use realistic stat values."""
            
            agent = AssistantAgent(
                name="TradeExtractor_Agent",
                system_message=system_message,
                llm_config=self.get_llm_config(),
                description="Trade decision extractor for converting conversations to structured data"
            )
            
            logger.info("Created trade extractor agent")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating extractor agent: {e}")
            raise
    
    def create_user_proxy(self, session_id: str) -> UserProxyAgent:
        """
        Create a user proxy agent for orchestrating the negotiation.
        
        Args:
            session_id: Trade session identifier
            
        Returns:
            Configured AutoGen UserProxyAgent
        """
        try:
            agent = UserProxyAgent(
                name="TradeOrchestrator",
                human_input_mode="NEVER",
                max_consecutive_auto_reply=0,
                code_execution_config=False,
                description=f"Trade negotiation orchestrator for session {session_id}"
            )
            
            logger.info(f"Created user proxy for session {session_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating user proxy: {e}")
            raise
    
    def _build_team_context(self, team_name: str, roster_info: Dict[str, Any]) -> str:
        """
        Build context information for team agent.
        
        Args:
            team_name: Name of the team
            roster_info: Current roster and salary information
            
        Returns:
            Formatted context string
        """
        context_parts = [
            f"## {team_name} Current Situation",
            f"Total Salary: ${roster_info.get('total_salary', 0):,}",
            f"Salary Cap Space: ${settings.salary_cap - roster_info.get('total_salary', 0):,}",
            f"Roster Size: {len(roster_info.get('players', []))} players"
        ]
        
        # Add position breakdown
        players = roster_info.get('players', [])
        if players:
            positions = {}
            for player in players:
                pos = player.get('position', 'Unknown')
                positions[pos] = positions.get(pos, 0) + 1
            
            context_parts.append("Position Distribution:")
            for pos, count in sorted(positions.items()):
                context_parts.append(f"  {pos}: {count}")
        
        # Add top players by salary
        if players:
            sorted_players = sorted(players, key=lambda p: p.get('salary', 0), reverse=True)[:5]
            context_parts.append("Top Players by Salary:")
            for player in sorted_players:
                name = player.get('name', 'Unknown')
                salary = player.get('salary', 0)
                position = player.get('position', 'Unknown')
                context_parts.append(f"  {name} ({position}): ${salary:,}")
        
        # Add trade constraints using settings
        from backend.config import settings
        context_parts.extend([
            "",
            "## Trade Constraints",
            f"- Salary cap: ${settings.salary_cap:,}",
            "- Roster size: Exactly 13 players",
            "- Position requirements: PG, SG, G, SF, PF, F, C, 2×UTIL, 3×BENCH",
            "- Consider team chemistry and future performance", 
            "- Evaluate player contracts and value"
        ])
        
        return "\n".join(context_parts)