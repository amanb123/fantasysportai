"""
Utility functions to map Sleeper player data to internal PlayerModel.
"""

import random
import logging
from typing import Dict

from backend.session.models import PlayerModel, PositionEnum

logger = logging.getLogger(__name__)


def map_sleeper_to_player_model(sleeper_player: Dict, team_id: int) -> PlayerModel:
    """
    Map Sleeper player schema to PlayerModel.
    
    Args:
        sleeper_player: Sleeper player data dictionary
        team_id: Internal team ID
        
    Returns:
        PlayerModel: Mapped player model instance
    """
    try:
        # Extract name
        name = sleeper_player.get("name", "Unknown Player")
        
        # Map position
        positions = sleeper_player.get("positions", [])
        if not positions:
            positions = ["PG"]  # Default fallback
        
        position_enum = map_position_to_enum(positions[0])
        
        # Generate placeholder salary
        salary = generate_placeholder_salary(position_enum)
        
        # Create PlayerModel with placeholder stats (will be updated in Phase 3)
        player = PlayerModel(
            name=name,
            team_id=team_id,
            position=position_enum,
            salary=salary,
            # Placeholder stats - will be replaced with real NBA stats in Phase 3
            points_per_game=0.0,
            rebounds_per_game=0.0,
            assists_per_game=0.0,
            steals_per_game=0.0,
            blocks_per_game=0.0,
            turnovers_per_game=0.0,
            field_goal_percentage=0.0,
            three_point_percentage=0.0,
        )
        
        return player
        
    except Exception as e:
        logger.error(f"Error mapping Sleeper player to PlayerModel: {e}")
        # Return a fallback player
        return PlayerModel(
            name="Unknown Player",
            team_id=team_id,
            position=PositionEnum.PG,
            salary=5000000,
            points_per_game=0.0,
            rebounds_per_game=0.0,
            assists_per_game=0.0,
            steals_per_game=0.0,
            blocks_per_game=0.0,
            turnovers_per_game=0.0,
            field_goal_percentage=0.0,
            three_point_percentage=0.0,
        )


def map_position_to_enum(sleeper_position: str) -> PositionEnum:
    """
    Map Sleeper position to internal PositionEnum.
    
    Args:
        sleeper_position: Sleeper position string
        
    Returns:
        PositionEnum: Mapped position enum
        
    Raises:
        ValueError: If position is invalid
    """
    # Create mapping for Sleeper positions to internal enum
    position_mapping = {
        "PG": PositionEnum.PG,
        "SG": PositionEnum.SG,
        "SF": PositionEnum.SF,
        "PF": PositionEnum.PF,
        "C": PositionEnum.C,
        # Handle multi-position players
        "G": PositionEnum.PG,  # Generic guard -> Point Guard
        "F": PositionEnum.SF,  # Generic forward -> Small Forward
    }
    
    # Normalize input
    position = sleeper_position.upper().strip()
    
    if position in position_mapping:
        return position_mapping[position]
    
    # If position not found, try to handle combined positions (e.g., "PG/SG")
    if "/" in position:
        # Take the first position
        first_position = position.split("/")[0].strip()
        if first_position in position_mapping:
            logger.info(f"Multi-position player {sleeper_position}, using primary position {first_position}")
            return position_mapping[first_position]
    
    # Default fallback to PG for unknown positions
    logger.warning(f"Unknown position '{sleeper_position}', defaulting to PG")
    return PositionEnum.PG


def generate_placeholder_salary(position: PositionEnum) -> int:
    """
    Generate realistic placeholder salaries based on position.
    
    Args:
        position: Player position enum
        
    Returns:
        int: Salary as integer
    """
    # Define salary ranges by position (in dollars)
    salary_ranges = {
        PositionEnum.PG: (5_000_000, 15_000_000),  # Point Guards
        PositionEnum.SG: (5_000_000, 15_000_000),  # Shooting Guards  
        PositionEnum.SF: (8_000_000, 18_000_000),  # Small Forwards
        PositionEnum.PF: (8_000_000, 18_000_000),  # Power Forwards
        PositionEnum.C: (6_000_000, 16_000_000),   # Centers
    }
    
    min_salary, max_salary = salary_ranges.get(position, (5_000_000, 15_000_000))
    
    # Generate random salary within range, rounded to nearest 100k
    salary = random.randint(min_salary, max_salary)
    salary = round(salary / 100_000) * 100_000  # Round to nearest 100k
    
    return salary


def filter_active_players(players: Dict[str, Dict]) -> Dict[str, Dict]:
    """
    Filter out inactive players based on status field.
    
    Args:
        players: Dictionary of player data
        
    Returns:
        Dict: Filtered player dictionary with only active players
    """
    active_players = {}
    
    for player_id, player_data in players.items():
        status = player_data.get("status", "").lower()
        
        # Consider player active if status is "Active" or similar
        if status in ["active", ""]:  # Empty status often means active
            active_players[player_id] = player_data
        else:
            logger.debug(f"Filtering out inactive player {player_id}: status={status}")
    
    logger.info(f"Filtered {len(active_players)} active players from {len(players)} total players")
    return active_players


def validate_player_data(sleeper_player: Dict) -> bool:
    """
    Validate required fields exist in Sleeper player data.
    
    Args:
        sleeper_player: Sleeper player data dictionary
        
    Returns:
        bool: True if valid, False otherwise
    """
    required_fields = ["name", "positions"]
    
    for field in required_fields:
        if field not in sleeper_player or sleeper_player[field] is None:
            return False
    
    # Check if positions is a non-empty list
    positions = sleeper_player.get("positions", [])
    if not isinstance(positions, list) or len(positions) == 0:
        return False
    
    # Check if name is non-empty string
    name = sleeper_player.get("name", "")
    if not isinstance(name, str) or len(name.strip()) == 0:
        return False
    
    return True