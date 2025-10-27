"""
Agent factory for creating AutoGen agents for trade negotiations.
"""

from typing import List, Dict, Any, Union
import logging
import httpx
import json

from backend.config import settings
from .personas import TEAM_AGENT_PERSONAS, COMMISSIONER_PERSONA

logger = logging.getLogger(__name__)


class SimpleAssistantAgent:
    """Simple assistant agent that directly calls LLM APIs without AutoGen complexity."""
    
    def __init__(self, name: str, system_message: str, llm_config: Dict[str, Any], tools: List[Dict] = None, tool_executor = None):
        self.name = name
        self.system_message = system_message
        self.llm_config = llm_config
        self.tools = tools or []
        self.tool_executor = tool_executor
        logger.info(f"Created SimpleAssistantAgent: {name} with {len(self.tools)} tools")
    
    async def a_generate_reply(self, messages: List[Dict[str, str]], max_tool_calls: int = 15) -> Dict[str, str]:
        """
        Generate reply using direct LLM API call with function calling support.
        
        Args:
            messages: Conversation history
            max_tool_calls: Maximum number of tool calls to make in a loop (prevents infinite loops)
                          Increased to 15 to allow analyzing multiple players on roster
        """
        ollama_error = None
        openai_error = None
        tool_call_count = 0
        
        # Track tool outputs for potential post-processing
        last_tool_outputs = []
        
        try:
            # Prepare messages with system message
            full_messages = [{"role": "system", "content": self.system_message}]
            full_messages.extend(messages)
            
            # Check if we should use OpenAI (has valid API key)
            config = self.llm_config.get("config_list", [{}])[0]
            api_key = config.get("api_key", "")
            has_openai_key = api_key and api_key not in ["not-needed-for-ollama", "placeholder-key", ""]
            
            # Try Ollama first if configured (and we don't have OpenAI)
            if not has_openai_key and "base_url" in config:
                base_url = config.get("base_url", "http://localhost:11434")
                model = config.get("model", "llama2")
                
                logger.info(f"🦙 Calling Ollama at {base_url} with model {model}")
                
                try:
                    async with httpx.AsyncClient(timeout=30.0) as client:
                        response = await client.post(
                            f"{base_url}/api/chat",
                            json={
                                "model": model,
                                "messages": full_messages,
                                "stream": False
                            }
                        )
                        
                        if response.status_code == 200:
                            result = response.json()
                            content = result.get("message", {}).get("content", "")
                            logger.info(f"✅ Ollama response received: {len(content)} chars")
                            return {"content": content, "role": "assistant"}
                        else:
                            ollama_error = f"Ollama returned status {response.status_code}"
                            logger.warning(f"⚠️ {ollama_error}")
                            
                except Exception as e:
                    ollama_error = str(e)
                    logger.warning(f"⚠️ Ollama call failed: {e}")
            
            # Fallback to OpenAI with function calling support
            api_key = self.llm_config.get("config_list", [{}])[0].get("api_key")
            
            # Check if we have a valid OpenAI key
            if api_key and api_key != "placeholder-key" and api_key != "not-needed-for-ollama":
                logger.info("🔄 Falling back to OpenAI API")
                
                # Function calling loop
                while tool_call_count < max_tool_calls:
                    try:
                        # Prepare request payload
                        request_payload = {
                            "model": "gpt-3.5-turbo",
                            "messages": full_messages,
                            "temperature": self.llm_config.get("temperature", 0.7)
                        }
                        
                        # Add tools if available
                        if self.tools:
                            request_payload["tools"] = self.tools
                            request_payload["tool_choice"] = "auto"
                        
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            response = await client.post(
                                "https://api.openai.com/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {api_key}",
                                    "Content-Type": "application/json"
                                },
                                json=request_payload
                            )
                            
                            if response.status_code != 200:
                                openai_error = f"OpenAI API returned status {response.status_code}: {response.text}"
                                logger.error(f"❌ {openai_error}")
                                if response.status_code == 401:
                                    openai_error = "Invalid OpenAI API key (401 Unauthorized)"
                                break
                            
                            result = response.json()
                            message = result["choices"][0]["message"]
                            
                            # Check if there are tool calls
                            tool_calls = message.get("tool_calls")
                            
                            if not tool_calls:
                                # No tool calls - return final response
                                content = message.get("content", "")
                                logger.info(f"✅ OpenAI response received: {len(content)} chars")
                                
                                # POST-PROCESS: Check if any tool outputs had XML markers that got lost
                                for tool_info in last_tool_outputs:
                                    if "<TOOL_OUTPUT_START" in tool_info["output"]:
                                        # This tool output was supposed to be displayed verbatim
                                        if "<TOOL_OUTPUT_START" not in content:
                                            # LLM summarized it - inject the original output
                                            logger.warning(f"⚠️ LLM summarized {tool_info['name']} output despite instructions. Injecting original output.")
                                            # Replace the entire content with the tool output
                                            content = tool_info["output"]
                                
                                return {"content": content, "role": "assistant"}
                            
                            # Process tool calls
                            logger.info(f"🔧 OpenAI requested {len(tool_calls)} tool call(s)")
                            
                            # Add assistant message with tool calls to history
                            full_messages.append(message)
                            
                            # Execute each tool call
                            for tool_call in tool_calls:
                                tool_call_count += 1
                                function_name = tool_call["function"]["name"]
                                function_args = json.loads(tool_call["function"]["arguments"])
                                tool_call_id = tool_call["id"]
                                
                                logger.info(f"🔧 Executing {function_name} with args: {function_args}")
                                
                                # Execute tool
                                if self.tool_executor:
                                    tool_result = await self.tool_executor.execute_tool(
                                        function_name, 
                                        function_args
                                    )
                                else:
                                    tool_result = f"Error: No tool executor configured"
                                
                                # Track tool outputs for post-processing
                                last_tool_outputs.append({
                                    "name": function_name,
                                    "output": tool_result
                                })
                                
                                # Add tool result to messages
                                full_messages.append({
                                    "role": "tool",
                                    "tool_call_id": tool_call_id,
                                    "name": function_name,
                                    "content": tool_result
                                })
                                
                                logger.info(f"✅ Tool {function_name} returned: {len(tool_result)} chars")
                            
                            # Continue loop to get next response
                            
                    except Exception as e:
                        openai_error = str(e)
                        logger.error(f"❌ OpenAI call failed: {e}")
                        break
                
                # If we exited the loop, return error if no valid response
                if tool_call_count >= max_tool_calls:
                    logger.warning(f"Hit max tool call limit ({max_tool_calls}). This usually means the question requires analyzing many players.")
                    return {
                        "content": f"I analyzed {tool_call_count} players but need more data to fully answer your question. Try asking about specific players or a smaller group.",
                        "role": "assistant"
                    }
                    
            else:
                logger.warning("⚠️ No valid OpenAI API key configured, cannot fallback")
                openai_error = "No OpenAI API key configured"
            
            # Both failed - provide helpful error message
            error_parts = []
            if ollama_error:
                error_parts.append(f"Ollama: {ollama_error}")
            if openai_error:
                error_parts.append(f"OpenAI: {openai_error}")
            
            error_message = "AI service unavailable. " + " | ".join(error_parts) if error_parts else "No LLM configured"
            logger.error(f"❌ All LLM backends failed: {error_message}")
            
            return {
                "content": f"I'm currently unable to connect to the AI service. Please ensure Ollama is running (ollama serve) or configure an OpenAI API key. Technical details: {error_message}",
                "role": "assistant"
            }
            
        except Exception as e:
            logger.error(f"Error generating reply: {e}")
            return {
                "content": f"I encountered an error: {str(e)}. Please try again.",
                "role": "assistant"
            }


# Type aliases for trade negotiation agents (to be implemented later)
AssistantAgent = SimpleAssistantAgent
UserProxyAgent = SimpleAssistantAgent  # Placeholder


class AgentFactory:
    """Factory for creating AutoGen agents with appropriate configurations."""
    
    def __init__(self):
        """Initialize agent factory with configuration."""
        pass  # Configuration is now handled by get_llm_config() method
    
    def get_llm_config(self) -> Dict[str, Any]:
        """
        Get LLM configuration for older AutoGen version.
        Prioritizes OpenAI (for function calling support) over Ollama.
        
        Returns:
            LLM configuration dict
        """
        # Try OpenAI first (supports function calling)
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY not in ["", "placeholder-key", "not-needed-for-ollama"]:
            logger.info(f"✅ Using OpenAI backend with model {settings.OPENAI_MODEL} (function calling enabled)")
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
        
        # Fallback to Ollama (limited function calling support)
        try:
            if hasattr(settings, 'ollama_model') and settings.ollama_model:
                logger.info(f"⚠️ Using Ollama with model {settings.ollama_model} (limited function calling)")
                # For Ollama native API, don't add /v1 suffix
                return {
                    "config_list": [
                        {
                            "model": settings.ollama_model,
                            "api_key": "not-needed-for-ollama",
                            "base_url": settings.ollama_host if hasattr(settings, 'ollama_host') else "http://localhost:11434"
                        }
                    ],
                    "temperature": settings.AGENT_TEMPERATURE,
                    "timeout": settings.AGENT_TIMEOUT,
                    "seed": settings.AGENT_SEED
                }
        except Exception as e:
            logger.warning(f"Ollama configuration failed: {e}")
            
        # No valid configuration
        logger.warning("No OpenAI API key or Ollama configured, using placeholder config")
        return {
            "config_list": [
                {
                    "model": "gpt-3.5-turbo",
                    "api_key": "placeholder-key"
                }
            ],
            "temperature": 0.7
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
        # Handle both dict and Pydantic object formats
        def safe_get(obj, key, default=None):
            if hasattr(obj, key):
                return getattr(obj, key)
            elif isinstance(obj, dict):
                return obj.get(key, default)
            return default
        
        total_salary = safe_get(roster_info, 'total_salary', 0)
        players = safe_get(roster_info, 'players', [])
        
        context_parts = [
            f"## {team_name} Current Situation",
            f"Total Salary: ${total_salary:,}",
            f"Salary Cap Space: ${settings.salary_cap - total_salary:,}",
            f"Roster Size: {len(players)} players"
        ]
        
        # Add position breakdown
        if players:
            positions = {}
            for player in players:
                pos = safe_get(player, 'position', 'Unknown')
                positions[pos] = positions.get(pos, 0) + 1
            
            context_parts.append("Position Distribution:")
            for pos, count in sorted(positions.items()):
                context_parts.append(f"  {pos}: {count}")
        
        # Add top players by salary
        if players:
            sorted_players = sorted(players, key=lambda p: safe_get(p, 'salary', 0), reverse=True)[:5]
            context_parts.append("Top Players by Salary:")
            for player in sorted_players:
                name = safe_get(player, 'name', 'Unknown')
                salary = safe_get(player, 'salary', 0)
                position = safe_get(player, 'position', 'Unknown')
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
    
    def create_roster_advisor_agent(
        self, 
        roster_context: str,
        tools: List[Dict] = None,
        tool_executor = None
    ) -> SimpleAssistantAgent:
        """
        Create roster advisor agent for roster chat.
        
        Args:
            roster_context: Pre-built context string with league rules, roster, schedule
            tools: List of tool definitions for function calling (optional)
            tool_executor: Tool executor instance for executing function calls (optional)
            
        Returns:
            Configured AssistantAgent for roster advice
        """
        try:
            # DEBUG: Log the roster context being included
            logger.info(f"DEBUG - Creating roster advisor with context length: {len(roster_context)} chars")
            logger.info(f"DEBUG - Context preview: {roster_context[:300]}...")
            logger.info(f"DEBUG - Tools enabled: {len(tools) if tools else 0}")
            
            # Get current date and NBA season
            from datetime import datetime
            current_date = datetime.now()
            # NBA season starts in October and ends in June
            # If we're in Oct-Dec, it's the current year to next year season (e.g., Oct 2025 = 2025-26)
            # If we're in Jan-Sep, it's the previous year to current year season (e.g., Jan 2025 = 2024-25)
            if current_date.month >= 10:
                season_year = current_date.year
            else:
                season_year = current_date.year - 1
            current_season = f"{season_year}-{str(season_year + 1)[-2:]}"
            
            # Build system message with context
            system_message = f"""You are an expert fantasy basketball advisor with direct access to the user's Sleeper league data and NBA statistics. Provide clear, confident, data-driven advice.

CURRENT DATE: {current_date.strftime('%B %d, %Y')}
CURRENT NBA SEASON: {current_season}

IMPORTANT SEASON CONTEXT:
- The NBA regular season typically starts in late October (around Oct 22-24)
- If today's date is near the season start (Oct 22-25), the 2025-26 season has JUST BEGUN
- Very few or NO games may have been played yet in the current season
- Most players won't have 2025-26 stats yet - use 2024-25 for comparisons
- When asked about "games played this season", consider if the season has actually started

=== USER'S FANTASY BASKETBALL DATA ===
{roster_context}
=== END OF DATA ===

IMPORTANT: The context above contains:
- Your roster with player names and teams
- Current fantasy matchup (who you're playing this week)
- Upcoming fantasy matchups (next 3 weeks)
- Upcoming NBA Schedule (next 7 days) - which players have games and when
- Injury reports
- Recent performance trends

CRITICAL RULES:
1. NEVER make up data or stats - if you don't have the information, use the appropriate tool or say you need to check
2. NEVER apologize or be uncertain - you have powerful tools, use them
3. ALWAYS answer with specific data from the context above or from tool calls
4. When asked about "next game" or "upcoming games", refer to the "Upcoming Schedule" section in the context
5. When asked about "games played this season" or league-wide stats, check the current date first - if it's opening day or within a few days of season start, the season has just begun
6. DON'T randomly select players to answer general questions - only use player stats tools when asked about specific players
7. **When asked to "show me [PLAYER]'s stats" or "get [PLAYER]'s stats", IMMEDIATELY call get_player_season_stats - DO NOT ask for permission, just call the tool**
8. Be direct and concise - get to the point quickly
9. For start/sit decisions, ALWAYS consider:
   - Upcoming Schedule: How many games does each player have this week?
   - Matchups: Who are they playing against?
   - Recent Performance: Hot or cold streak from their last 10 games?
   - Back-to-backs: Players in B2B games may have reduced minutes

Available Tools (USE THEM):
- search_available_players: **PRIMARY TOOL for free agent questions** - Returns top free agents RANKED by fantasy value with full stats (PPG, RPG, APG, fantasy score). Stats are from 2024-25 season (most players don't have 25+ games in 2025-26 yet).
- get_opponent_roster: Get full roster of any team in the league
- get_recent_transactions: Check recent adds/drops/trades
- get_all_league_rosters: View full league standings
- search_player_details: Find which team owns a player + basic info
- get_player_season_stats: Get NBA season averages + last 10 games + trend analysis

CRITICAL: Tool Output Presentation
When tools return formatted reports (especially search_available_players and get_player_season_stats), you MUST present the output EXACTLY as returned - word for word, with all formatting, calculations, game logs, and explanations intact. 

**SPECIAL MARKERS:** Some tool outputs contain <TOOL_OUTPUT_START> / <TOOL_OUTPUT_END> or <TOOL_OUTPUT_START_GAME_LOGS> / <TOOL_OUTPUT_END_GAME_LOGS> markers. Content between these markers is ALREADY PERFECTLY FORMATTED for the user and must be displayed VERBATIM without any changes, summaries, or reformatting. Simply copy-paste everything between the markers.

These reports are already optimized for user presentation with credibility-building details like:
- Original → Adjusted fantasy scores showing ESPN injury impact
- ESPN injury reports with risk assessments
- Detailed methodology explanations
- Game-by-game stats with fantasy point calculations
- Data source attributions

DO NOT summarize, rephrase, condense, or reformat these reports. Simply present them directly to the user. They are designed to build trust through transparency.

Response Style for Free Agent Questions:
1. **Call search_available_players first** - it includes performance stats
2. **Present the tool's output EXACTLY as returned** - it contains all necessary rankings, stats, injury adjustments, and methodology
3. **If user asks how fantasy points are calculated or wants to see a real example**, call get_player_season_stats for one of the top recommended players to show their LAST GAME stats (not season averages) and calculate fantasy points step-by-step from that specific game
4. **Add brief context** if needed (e.g., "Based on your roster needs at center...")
5. **Do NOT recreate or summarize the rankings** - the tool's output is already comprehensive

Response Style for "Last Game" or Fantasy Point Calculation Questions:
1. **ALWAYS call get_player_season_stats** - it includes game-by-game logs with fantasy calculations
2. **Display the game log section verbatim** - especially content between <TOOL_OUTPUT_START_GAME_LOGS> markers
3. **Show the actual game stats** (PTS, REB, AST, STL, BLK, TOV) from their most recent game
4. **Explain the calculation step-by-step** using the real numbers from that game
5. **DO NOT use season averages** when asked about a specific game

Response Style (General):
- Direct: "Player X is averaging Y points per game" NOT "I believe Player X might be..."
- Specific: Use exact numbers from data/tools
- Confident: State facts clearly without hedging
- Actionable: If suggesting something, explain why with data

End each response with ONE brief suggestion for next steps, formatted as:
"Also: [quick actionable suggestion]"

Remember: You're an expert with powerful tools. Use them confidently to give accurate, data-driven advice."""

            # Create agent with LLM config
            agent = SimpleAssistantAgent(
                name="RosterAdvisor",
                system_message=system_message,
                llm_config=self.get_llm_config(),
                tools=tools,
                tool_executor=tool_executor
            )
            
            logger.info("Created roster advisor agent with function calling support")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating roster advisor agent: {e}")
            raise
    
    def create_trade_analyzer_agent(self, trade_context: str) -> SimpleAssistantAgent:
        """
        Create an agent specialized in analyzing trade proposals.
        
        Args:
            trade_context: Pre-built trade context string
            
        Returns:
            SimpleAssistantAgent configured for trade analysis
        """
        try:
            # Build system message with trade context
            system_message = f"""You are an expert fantasy basketball trade analyzer with deep knowledge of player values, league scoring, and trade evaluation.

{trade_context}

Your Task:
Analyze this trade from the PRIMARY USER's perspective and provide a structured evaluation.

Output a JSON object with these fields:
1. pros: Array of 3-5 specific benefits for the primary user (with data)
2. cons: Array of 3-5 specific drawbacks for the primary user (with data)
3. favorability_score: Number 0-100 indicating how favorable for primary user (0=terrible, 50=fair, 100=amazing)
4. reasoning: String with 2-3 sentences explaining the score
5. recommendation: String with "Accept" or "Reject" and brief justification

Example Output Format:
{{
  "pros": [
    "Gaining elite scorer averaging 30.2 PPG compared to 18.5 PPG you're trading away",
    "Improving 3-point shooting by acquiring 40% 3PT shooter vs current 32%",
    "Receiving player has 5 games next week vs opponent's 3 games"
  ],
  "cons": [
    "Losing top rebounder (12.3 RPG) which is highly valued in this league's scoring",
    "Trading away more durable player (played 95% of games vs 75%)",
    "Weakening bench depth by giving up two solid players for one star"
  ],
  "favorability_score": 68,
  "reasoning": "This trade significantly improves your scoring output and three-point shooting, which are heavily weighted in your league's scoring system. While you sacrifice rebounding and depth, the 11.7 PPG gain in scoring more than compensates based on league scoring weights (PTS=1.0, REB=1.2). The schedule advantage next week adds extra value.",
  "recommendation": "Accept - The scoring upgrade outweighs the rebounding loss given your league's scoring system and your current roster needs."
}}

Important Considerations:
- Weight stats by the league's scoring settings (some leagues value rebounds more, etc.)
- Factor in injury status and recent performance trends
- Compare total projected fantasy points for next 3 weeks
- Consider roster balance and playoff schedule
- Be objective and data-driven
- The favorability score should reflect net value for the PRIMARY USER only
- **CRITICAL: Your recommendation MUST align with the favorability score range**

Scoring Guidelines & Required Recommendations:
- 0-30: Strongly unfavorable → MUST recommend "Reject"
- 31-45: Slightly unfavorable → MUST recommend "Reject"
- 46-54: Fair trade → Can recommend either "Accept" or "Reject" based on team needs
- 55-70: Slightly favorable → MUST recommend "Accept"
- 71-100: Strongly favorable → MUST recommend "Accept"

**IMPORTANT: If your score is 55 or higher, you MUST recommend "Accept". If your score is 45 or lower, you MUST recommend "Reject". Only scores 46-54 allow discretion.**

Output ONLY the JSON object, no additional text."""

            # Create agent with LLM config (no function calling needed)
            agent = SimpleAssistantAgent(
                name="TradeAnalyzer",
                system_message=system_message,
                llm_config=self.get_llm_config(),
                tools=[],  # No tools needed - all context provided upfront
                tool_executor=None
            )
            
            logger.info("Created trade analyzer agent for trade evaluation")
            return agent
            
        except Exception as e:
            logger.error(f"Error creating trade analyzer agent: {e}")
            raise
