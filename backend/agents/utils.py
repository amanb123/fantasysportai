"""
Utility functions for agent operations and response parsing.
"""

from typing import Dict, Any, Optional, List
import json
import re
from datetime import datetime
import logging

from shared.models import TradeProposal, AgentMessage

logger = logging.getLogger(__name__)


def get_league_rules_text() -> str:
    """
    Get centralized league rules text using settings and 13-slot composition.
    
    Returns:
        Formatted league rules text
    """
    from backend.config import settings
    
    rules_text = f"""
## League Rules & Regulations

**Salary Cap:** ${settings.salary_cap:,} per team
- Teams cannot exceed the salary cap in any trade
- Current salary counts toward cap limit

**Roster Composition (13-Slot System):**
- 2 Point Guards (PG) 
- 2 Shooting Guards (SG)
- 2 Small Forwards (SF) 
- 2 Power Forwards (PF)
- 2 Centers (C)
- 3 Flexible positions (UTIL) - can be any position
- Total: 13 players per team

**Trade Requirements:**
- All trades must maintain salary cap compliance for both teams
- All trades must maintain valid 13-slot roster composition
- Players must be properly assigned to available roster slots
- Both teams must remain competitive and balanced

**Consensus & Approval:**
- Use "{settings.agent_consensus_keyword}" to signal final agreement
- Commissioner must approve all trades for league balance
- Detailed reasoning required for all trade decisions
"""
    return rules_text.strip()


def parse_agent_response(content: str) -> Optional[Dict[str, Any]]:
    """
    Parse agent response to extract full TradeDecision dict conforming to shared.models.TradeDecision.
    
    Args:
        content: Raw agent response content
        
    Returns:
        Dict that can be passed into TradeDecision(**data) or None if no structured data found
    """
    try:
        # Look for JSON blocks in the response
        json_pattern = r'```json\s*(.*?)\s*```'
        json_matches = re.findall(json_pattern, content, re.DOTALL)
        
        for match in json_matches:
            try:
                parsed = json.loads(match)
                if isinstance(parsed, dict):
                    # Check if it has TradeDecision fields (including approved)
                    required_fields = ["approved", "offering_team_id", "receiving_team_id", "traded_players_out", "traded_players_in", "consensus_reached"]
                    has_core_fields = all(field in parsed for field in ["offering_team_id", "receiving_team_id", "traded_players_out", "traded_players_in"])
                    
                    if has_core_fields:
                        # Ensure 'approved' field exists - derive from consensus_reached if missing
                        if "approved" not in parsed and "consensus_reached" in parsed:
                            parsed["approved"] = parsed["consensus_reached"]
                        elif "approved" not in parsed:
                            parsed["approved"] = False
                        
                        # Ensure all required fields have defaults
                        parsed.setdefault("consensus_reached", parsed.get("approved", False))
                        parsed.setdefault("rejection_reasons", [])
                        parsed.setdefault("commissioner_notes", "")
                        
                        from shared.models import TradeDecision
                        try:
                            # Validate it matches TradeDecision schema
                            trade_decision = TradeDecision(**parsed)
                            return {"type": "trade_decision", "data": parsed}
                        except Exception as e:
                            logger.warning(f"TradeDecision validation failed: {e}")
                            # Return partial data with fallback including approved field
                            fallback_data = {
                                "approved": False,
                                "offering_team_id": parsed.get("offering_team_id", 0),
                                "receiving_team_id": parsed.get("receiving_team_id", 0),
                                "traded_players_out": parsed.get("traded_players_out", []),
                                "traded_players_in": parsed.get("traded_players_in", []),
                                "consensus_reached": False,
                                "rejection_reasons": [f"Parse error: {str(e)}"],
                                "commissioner_notes": "Failed to parse complete trade decision"
                            }
                            return {"type": "trade_decision", "data": fallback_data}
                    
                    # Legacy format compatibility - handle old formats that may have partial fields
                    if "approved" in parsed and not has_core_fields:
                        # Convert legacy format to new schema with all required fields
                        return {"type": "trade_decision", "data": {
                            "approved": parsed.get("approved", False),
                            "offering_team_id": parsed.get("offering_team_id", 0),
                            "receiving_team_id": parsed.get("receiving_team_id", 0), 
                            "traded_players_out": parsed.get("traded_players_out", []),
                            "traded_players_in": parsed.get("traded_players_in", []),
                            "consensus_reached": parsed.get("approved", False),
                            "rejection_reasons": parsed.get("rejection_reasons", []),
                            "commissioner_notes": parsed.get("commissioner_notes", "")
                        }}
                        
                    return {"type": "general", "data": parsed}
            except json.JSONDecodeError:
                continue
        
        # Look for structured decision indicators with full schema extraction
        if "TRADE_DECISION:" in content.upper() or "CONSENSUS_REACHED" in content.upper():
            # Extract basic decision data with all required fields
            decision_data = {
                "approved": False,
                "offering_team_id": 0,
                "receiving_team_id": 0,
                "traded_players_out": [],
                "traded_players_in": [],
                "consensus_reached": False,
                "rejection_reasons": [],
                "commissioner_notes": ""
            }
            
            # Check for consensus/approval
            if any(keyword in content.upper() for keyword in ["APPROVED", "ACCEPT", "CONSENSUS_REACHED"]):
                decision_data["approved"] = True
                decision_data["consensus_reached"] = True
            elif any(keyword in content.upper() for keyword in ["REJECTED", "DECLINE", "DENIED"]):
                decision_data["approved"] = False
                decision_data["consensus_reached"] = False
                decision_data["rejection_reasons"] = ["Trade rejected in negotiation"]
            
            # Extract commissioner notes if present
            notes_patterns = [
                r'NOTES?:\s*(.*?)(?:\n|$)',
                r'COMMISSIONER.*?:\s*(.*?)(?:\n|$)',
                r'REASON.*?:\s*(.*?)(?:\n|$)'
            ]
            for pattern in notes_patterns:
                notes_match = re.search(pattern, content, re.IGNORECASE)
                if notes_match:
                    decision_data["commissioner_notes"] = notes_match.group(1).strip()
                    break
            
            return {"type": "trade_decision", "data": decision_data}
        
        return None
        
    except Exception as e:
        logger.error(f"Error parsing agent response: {e}")
        return None


def create_trade_summary(trade_proposal: TradeProposal, team_names: Dict[int, str]) -> str:
    """
    Create a human-readable summary of a trade proposal.
    
    Args:
        trade_proposal: TradeProposal object
        team_names: Dictionary mapping team IDs to names
        
    Returns:
        Formatted trade summary string
    """
    try:
        team1_name = team_names.get(trade_proposal.team1_id, f"Team {trade_proposal.team1_id}")
        team2_name = team_names.get(trade_proposal.team2_id, f"Team {trade_proposal.team2_id}")
        
        summary_parts = [
            f"## Trade Proposal: {team1_name} ↔ {team2_name}",
            f"",
            f"### {team1_name} Receives:"
        ]
        
        # Team 1 receives
        for player in trade_proposal.team1_receives:
            summary_parts.append(f"- {player.name} ({player.position}) - ${player.salary:,}")
        
        team1_receives_total = sum(p.salary for p in trade_proposal.team1_receives)
        summary_parts.append(f"Total: ${team1_receives_total:,}")
        
        summary_parts.extend([
            f"",
            f"### {team1_name} Gives:"
        ])
        
        # Team 1 gives
        for player in trade_proposal.team1_gives:
            summary_parts.append(f"- {player.name} ({player.position}) - ${player.salary:,}")
        
        team1_gives_total = sum(p.salary for p in trade_proposal.team1_gives)
        summary_parts.append(f"Total: ${team1_gives_total:,}")
        
        summary_parts.extend([
            f"",
            f"### {team2_name} Receives:"
        ])
        
        # Team 2 receives  
        for player in trade_proposal.team2_receives:
            summary_parts.append(f"- {player.name} ({player.position}) - ${player.salary:,}")
        
        team2_receives_total = sum(p.salary for p in trade_proposal.team2_receives)
        summary_parts.append(f"Total: ${team2_receives_total:,}")
        
        summary_parts.extend([
            f"",
            f"### {team2_name} Gives:"
        ])
        
        # Team 2 gives
        for player in trade_proposal.team2_gives:
            summary_parts.append(f"- {player.name} ({player.position}) - ${player.salary:,}")
        
        team2_gives_total = sum(p.salary for p in trade_proposal.team2_gives)
        summary_parts.append(f"Total: ${team2_gives_total:,}")
        
        # Add salary impact analysis
        team1_impact = team1_receives_total - team1_gives_total
        team2_impact = team2_receives_total - team2_gives_total
        
        summary_parts.extend([
            f"",
            f"### Salary Impact:",
            f"- {team1_name}: {'+' if team1_impact >= 0 else ''}${team1_impact:,}",
            f"- {team2_name}: {'+' if team2_impact >= 0 else ''}${team2_impact:,}",
            f"",
            f"### Player Count Change:",
            f"- {team1_name}: {'+' if len(trade_proposal.team1_receives) >= len(trade_proposal.team1_gives) else ''}{len(trade_proposal.team1_receives) - len(trade_proposal.team1_gives)}",
            f"- {team2_name}: {'+' if len(trade_proposal.team2_receives) >= len(trade_proposal.team2_gives) else ''}{len(trade_proposal.team2_receives) - len(trade_proposal.team2_gives)}"
        ])
        
        return "\n".join(summary_parts)
        
    except Exception as e:
        logger.error(f"Error creating trade summary: {e}")
        return f"Trade between {team_names.get(trade_proposal.team1_id, 'Unknown')} and {team_names.get(trade_proposal.team2_id, 'Unknown')}"


def validate_agent_message(message: Dict[str, Any]) -> bool:
    """
    Validate that an agent message has required fields.
    
    Args:
        message: Message dictionary to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["name", "content"]
    return all(field in message for field in required_fields)


def format_roster_info(players: List[Dict[str, Any]], total_salary: int) -> str:
    """
    Format roster information for agent context.
    
    Args:
        players: List of player dictionaries
        total_salary: Total team salary
        
    Returns:
        Formatted roster string
    """
    try:
        if not players:
            return f"No players on roster. Total salary: ${total_salary:,}"
        
        # Group by position
        by_position = {}
        for player in players:
            pos = player.get("position", "Unknown")
            if pos not in by_position:
                by_position[pos] = []
            by_position[pos].append(player)
        
        roster_parts = [
            f"Roster ({len(players)} players, ${total_salary:,} total salary):",
            ""
        ]
        
        # Sort positions logically
        position_order = ["PG", "SG", "SF", "PF", "C"]
        sorted_positions = sorted(by_position.keys(), key=lambda x: position_order.index(x) if x in position_order else 999)
        
        for position in sorted_positions:
            roster_parts.append(f"{position}:")
            position_players = sorted(by_position[position], key=lambda p: p.get("salary", 0), reverse=True)
            
            for player in position_players:
                name = player.get("name", "Unknown")
                salary = player.get("salary", 0)
                roster_parts.append(f"  - {name} (${salary:,})")
            
            roster_parts.append("")
        
        return "\n".join(roster_parts)
        
    except Exception as e:
        logger.error(f"Error formatting roster info: {e}")
        return f"Roster with {len(players) if players else 0} players, ${total_salary:,} total salary"


def extract_trade_preferences(content: str) -> Dict[str, Any]:
    """
    Extract trade preferences from natural language input.
    
    Args:
        content: Natural language trade request
        
    Returns:
        Dictionary of extracted preferences
    """
    preferences = {}
    
    try:
        content_upper = content.upper()
        
        # Extract positions
        positions = []
        position_keywords = {
            "POINT GUARD": "PG", "PG": "PG", "POINT": "PG",
            "SHOOTING GUARD": "SG", "SG": "SG", "GUARD": ["PG", "SG"],
            "SMALL FORWARD": "SF", "SF": "SF", "FORWARD": ["SF", "PF"],
            "POWER FORWARD": "PF", "PF": "PF",
            "CENTER": "C", "C": "C", "BIG MAN": "C"
        }
        
        for keyword, pos in position_keywords.items():
            if keyword in content_upper:
                if isinstance(pos, list):
                    positions.extend(pos)
                else:
                    positions.append(pos)
        
        if positions:
            preferences["desired_positions"] = list(set(positions))
        
        # Extract salary mentions (simple regex for dollar amounts)
        salary_pattern = r'\$(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)[KMkm]?'
        salary_matches = re.findall(salary_pattern, content)
        
        if salary_matches:
            # Convert to actual dollar amounts
            salaries = []
            for match in salary_matches:
                amount_str = match.replace(',', '')
                try:
                    amount = float(amount_str)
                    # Handle K/M suffixes if they were in original
                    if 'K' in content.upper() or 'k' in content:
                        amount *= 1000
                    elif 'M' in content.upper() or 'm' in content:
                        amount *= 1000000
                    salaries.append(int(amount))
                except ValueError:
                    continue
            
            if salaries:
                preferences["salary_mentions"] = salaries
        
        return preferences
        
    except Exception as e:
        logger.error(f"Error extracting trade preferences: {e}")
        return {}


def create_agent_context(team_name: str, roster_info: Dict[str, Any], 
                        league_context: Dict[str, Any]) -> str:
    """
    Create comprehensive context for an agent using centralized rules.
    
    Args:
        team_name: Name of the team
        roster_info: Roster and salary information
        league_context: League-wide context and rules
        
    Returns:
        Formatted context string
    """
    try:
        from backend.config import settings
        
        context_parts = [
            f"## Current Status for {team_name}",
            format_roster_info(roster_info.get("players", []), roster_info.get("total_salary", 0)),
            f"## League Context",
            f"Salary Cap: ${settings.salary_cap:,}",
            f"Your Cap Space: ${settings.salary_cap - roster_info.get('total_salary', 0):,}",
            "",
            "## Rules and Constraints",
            "- Roster size: Exactly 13 players (13-slot system)",
            "- Position requirements: 1 PG, 1 SG, 1 G, 1 SF, 1 PF, 1 F, 2 C, 2 UTIL, 3 BENCH", 
            "- All trades must maintain salary cap compliance",
            "- All trades must maintain valid 13-slot roster composition",
            "- Consider team chemistry and competitive balance",
            ""
        ]
        
        # Optionally reuse centralized rules text for consistency
        centralized_rules = get_league_rules_text()
        if centralized_rules:
            context_parts.append("## Detailed League Rules")
            context_parts.append(centralized_rules)
        
        return "\n".join(context_parts)
        
    except Exception as e:
        logger.error(f"Error creating agent context: {e}")
        return f"Context for {team_name} - Error loading details"