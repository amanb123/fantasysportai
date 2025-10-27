"""
Database seeding script to populate the Fantasy Basketball League with initial data.
"""

import logging
import argparse
from typing import Optional, Dict, List
from sqlmodel import select
from session.models import TeamModel, PlayerModel, PositionEnum
from session.database import init_database, get_repository
from config import settings
from services.redis_service import RedisService
from services.player_cache_service import PlayerCacheService
from services.sleeper_service import sleeper_service
from services.player_mapper import map_sleeper_to_player_model, filter_active_players

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def load_players_from_sleeper_cache() -> Optional[Dict[str, Dict]]:
    """
    Load players from Sleeper cache if available.
    
    Returns:
        Dict: Player dictionary or None if cache unavailable
    """
    try:
        # Initialize Redis and cache services
        redis_service = RedisService()
        if not redis_service.is_connected():
            logger.warning("Redis connection failed, cannot load Sleeper cache")
            return None
        
        player_cache_service = PlayerCacheService(redis_service, sleeper_service)
        
        # Try to get cached players
        cached_players = player_cache_service.get_cached_players()
        if cached_players is None:
            logger.warning("Sleeper player cache is empty")
            return None
        
        # Filter for active players only
        active_players = filter_active_players(cached_players)
        
        logger.info(f"Loaded {len(active_players)} active players from Sleeper cache")
        return active_players
        
    except Exception as e:
        logger.error(f"Error loading players from Sleeper cache: {e}")
        return None


def create_players_from_sleeper_data(sleeper_players: Dict[str, Dict], team_info: List[Dict]) -> Dict[str, List[PlayerModel]]:
    """
    Create PlayerModel instances from Sleeper data for each team.
    
    Args:
        sleeper_players: Dictionary of Sleeper player data
        team_info: List of team information dictionaries
        
    Returns:
        Dict: Team name -> List of PlayerModel instances
    """
    # Team-to-Sleeper mapping
    team_sleeper_mapping = {
        "Lakers": "LAL",
        "Warriors": "GSW", 
        "Celtics": "BOS"
    }
    
    team_players = {}
    
    for team in team_info:
        team_name = team["name"]
        team_id = team["id"]
        sleeper_team_code = team_sleeper_mapping.get(team_name)
        
        if not sleeper_team_code:
            logger.warning(f"No Sleeper mapping for team {team_name}")
            continue
        
        # Filter players by team
        team_sleeper_players = []
        for player_id, player_data in sleeper_players.items():
            if player_data.get("team") == sleeper_team_code:
                team_sleeper_players.append(player_data)
        
        logger.info(f"Found {len(team_sleeper_players)} {team_name} players in Sleeper cache")
        
        # Sort players by name and take first 13
        team_sleeper_players.sort(key=lambda p: p.get("name", ""))
        selected_players = team_sleeper_players[:13]
        
        # Convert to PlayerModel instances
        player_models = []
        for sleeper_player in selected_players:
            try:
                player_model = map_sleeper_to_player_model(sleeper_player, team_id)
                player_models.append(player_model)
            except Exception as e:
                logger.error(f"Error mapping player {sleeper_player.get('name')}: {e}")
        
        logger.info(f"Created {len(player_models)} PlayerModel instances for {team_name}")
        team_players[team_name] = player_models
        
        # If we don't have enough players, we'll fall back to hardcoded later
        if len(player_models) < 13:
            logger.warning(f"{team_name} only has {len(player_models)} players from Sleeper, will supplement with hardcoded data")
    
    return team_players


def seed_database(reset: bool = False, use_sleeper: bool = False):
    """Seed the database with 3 teams and 13 players each."""
    
    try:
        # Initialize database connection
        logger.info("Initializing database connection...")
        init_database(settings.get_database_url(), settings.database_echo)
        
        # Get repository instance
        repository = get_repository()
        
        # Reset database if requested
        if reset:
            logger.info("Resetting database - truncating all tables...")
            with repository.get_session() as session:
                # Delete in order to respect foreign key constraints
                session.query(PlayerModel).delete()
                session.query(TeamModel).delete()
                session.commit()
                logger.info("Database reset completed")
        
        # Define team data
        teams_data = [
            {"name": "Lakers"},
            {"name": "Warriors"},
            {"name": "Celtics"}
        ]
        
        # Create teams (check for existing teams first)
        logger.info("Creating teams...")
        team_info = []  # Store team info instead of objects
        for team_data in teams_data:
            with repository.get_session() as session:
                # Check if team already exists
                existing_team = session.exec(
                    select(TeamModel).where(TeamModel.name == team_data["name"])
                ).first()
                
                if existing_team:
                    logger.info(f"Team {team_data['name']} already exists, skipping creation")
                    team_info.append({"id": existing_team.id, "name": existing_team.name})
                else:
                    team = TeamModel(**team_data)
                    session.add(team)
                    session.commit()
                    session.refresh(team)
                    team_info.append({"id": team.id, "name": team.name})
                    logger.info(f"Created team: {team.name}")
        
        # Determine player data source
        sleeper_player_models = {}
        if use_sleeper:
            logger.info("Attempting to use Sleeper cached data...")
            sleeper_players = load_players_from_sleeper_cache()
            if sleeper_players:
                sleeper_player_models = create_players_from_sleeper_data(sleeper_players, team_info)
                logger.info(f"Successfully loaded Sleeper data for {len(sleeper_player_models)} teams")
            else:
                logger.warning("Sleeper cache unavailable, falling back to hardcoded data")
        
        # Define hardcoded player data for each team (fallback or default)
        players_data = {
            "Lakers": [
                # Core positions
                {"name": "LeBron James", "position": "PG", "salary": 25000000, "ppg": 28.5, "rpg": 8.2, "apg": 8.8, "spg": 1.3, "bpg": 0.8, "tov": 3.2, "fg": 0.525, "3pt": 0.365},
                {"name": "Russell Westbrook", "position": "SG", "salary": 22000000, "ppg": 18.5, "rpg": 7.4, "apg": 7.1, "spg": 1.0, "bpg": 0.3, "tov": 3.8, "fg": 0.444, "3pt": 0.298},
                {"name": "Anthony Davis", "position": "SF", "salary": 20000000, "ppg": 23.2, "rpg": 9.9, "apg": 3.1, "spg": 1.2, "bpg": 2.3, "tov": 2.4, "fg": 0.519, "3pt": 0.186},
                {"name": "Julius Randle", "position": "PF", "salary": 12000000, "ppg": 20.1, "rpg": 9.9, "apg": 5.1, "spg": 0.9, "bpg": 0.7, "tov": 3.4, "fg": 0.457, "3pt": 0.304},
                {"name": "Dwight Howard", "position": "C", "salary": 4000000, "ppg": 6.2, "rpg": 5.9, "apg": 0.6, "spg": 0.5, "bpg": 1.0, "tov": 1.1, "fg": 0.639, "3pt": 0.0},
                {"name": "DeAndre Jordan", "position": "C", "salary": 3500000, "ppg": 4.1, "rpg": 5.4, "apg": 0.7, "spg": 0.4, "bpg": 0.9, "tov": 0.8, "fg": 0.641, "3pt": 0.0},
                # Bench/utility players
                {"name": "Malik Monk", "position": "SG", "salary": 3000000, "ppg": 13.8, "rpg": 3.4, "apg": 3.4, "spg": 0.8, "bpg": 0.2, "tov": 1.6, "fg": 0.472, "3pt": 0.390},
                {"name": "Kendrick Nunn", "position": "PG", "salary": 2500000, "ppg": 6.7, "rpg": 2.5, "apg": 2.7, "spg": 0.4, "bpg": 0.1, "tov": 1.2, "fg": 0.370, "3pt": 0.317},
                {"name": "Austin Reaves", "position": "SG", "salary": 2000000, "ppg": 7.3, "rpg": 3.2, "apg": 1.8, "spg": 0.9, "bpg": 0.2, "tov": 1.0, "fg": 0.453, "3pt": 0.316},
                {"name": "Troy Brown Jr.", "position": "SF", "salary": 1500000, "ppg": 4.0, "rpg": 2.2, "apg": 0.9, "spg": 0.5, "bpg": 0.2, "tov": 0.5, "fg": 0.403, "3pt": 0.349},
                {"name": "Wenyen Gabriel", "position": "PF", "salary": 1500000, "ppg": 5.5, "rpg": 4.2, "apg": 0.6, "spg": 0.4, "bpg": 0.8, "tov": 0.7, "fg": 0.583, "3pt": 0.375},
                {"name": "Stanley Johnson", "position": "SF", "salary": 1000000, "ppg": 6.7, "rpg": 3.2, "apg": 1.7, "spg": 1.1, "bpg": 0.4, "tov": 1.2, "fg": 0.467, "3pt": 0.460},
                {"name": "Thomas Bryant", "position": "C", "salary": 1000000, "ppg": 7.4, "rpg": 4.0, "apg": 0.9, "spg": 0.4, "bpg": 1.0, "tov": 1.0, "fg": 0.615, "3pt": 0.385}
            ],
            "Warriors": [
                # Core positions (reduced top salaries by ~4% to stay under cap)
                {"name": "Stephen Curry", "position": "PG", "salary": 23000000, "ppg": 29.5, "rpg": 6.1, "apg": 6.3, "spg": 1.3, "bpg": 0.4, "tov": 3.2, "fg": 0.473, "3pt": 0.427},
                {"name": "Klay Thompson", "position": "SG", "salary": 19200000, "ppg": 20.4, "rpg": 3.9, "apg": 2.8, "spg": 0.6, "bpg": 0.4, "tov": 1.9, "fg": 0.433, "3pt": 0.387},
                {"name": "Andrew Wiggins", "position": "SF", "salary": 17300000, "ppg": 17.2, "rpg": 4.5, "apg": 2.3, "spg": 1.3, "bpg": 0.8, "tov": 2.3, "fg": 0.473, "3pt": 0.393},
                {"name": "Draymond Green", "position": "PF", "salary": 14400000, "ppg": 7.5, "rpg": 7.3, "apg": 7.0, "spg": 1.3, "bpg": 1.1, "tov": 3.0, "fg": 0.523, "3pt": 0.313},
                {"name": "Kevon Looney", "position": "C", "salary": 5000000, "ppg": 7.0, "rpg": 9.3, "apg": 2.5, "spg": 0.5, "bpg": 0.6, "tov": 1.5, "fg": 0.640, "3pt": 0.0},
                {"name": "James Wiseman", "position": "C", "salary": 4500000, "ppg": 11.5, "rpg": 5.8, "apg": 0.7, "spg": 0.3, "bpg": 0.9, "tov": 1.9, "fg": 0.630, "3pt": 0.316},
                # Bench/utility players
                {"name": "Jordan Poole", "position": "SG", "salary": 4000000, "ppg": 18.5, "rpg": 3.4, "apg": 4.0, "spg": 0.8, "bpg": 0.3, "tov": 3.0, "fg": 0.448, "3pt": 0.366},
                {"name": "Jonathan Kuminga", "position": "SF", "salary": 3000000, "ppg": 9.3, "rpg": 3.3, "apg": 0.9, "spg": 0.7, "bpg": 0.4, "tov": 1.5, "fg": 0.513, "3pt": 0.338},
                {"name": "Moses Moody", "position": "SG", "salary": 2500000, "ppg": 4.4, "rpg": 2.1, "apg": 0.8, "spg": 0.4, "bpg": 0.2, "tov": 0.6, "fg": 0.429, "3pt": 0.364},
                {"name": "Gary Payton II", "position": "PG", "salary": 2000000, "ppg": 7.1, "rpg": 3.5, "apg": 1.4, "spg": 1.4, "bpg": 0.8, "tov": 0.8, "fg": 0.616, "3pt": 0.358},
                {"name": "Otto Porter Jr.", "position": "SF", "salary": 1500000, "ppg": 8.2, "rpg": 5.7, "apg": 1.5, "spg": 1.1, "bpg": 0.9, "tov": 0.8, "fg": 0.465, "3pt": 0.370},
                {"name": "Nemanja Bjelica", "position": "PF", "salary": 1000000, "ppg": 6.1, "rpg": 4.1, "apg": 2.2, "spg": 0.5, "bpg": 0.4, "tov": 1.7, "fg": 0.387, "3pt": 0.388},
                {"name": "Juan Toscano-Anderson", "position": "SF", "salary": 1000000, "ppg": 4.1, "rpg": 2.0, "apg": 2.4, "spg": 0.6, "bpg": 0.2, "tov": 0.9, "fg": 0.423, "3pt": 0.317}
            ],
            "Celtics": [
                # Core positions (reduced top salaries by ~3-5% to stay under cap)  
                {"name": "Marcus Smart", "position": "PG", "salary": 13500000, "ppg": 12.1, "rpg": 3.8, "apg": 5.9, "spg": 1.7, "bpg": 0.3, "tov": 2.8, "fg": 0.420, "3pt": 0.330},
                {"name": "Jaylen Brown", "position": "SG", "salary": 21000000, "ppg": 23.6, "rpg": 6.1, "apg": 3.5, "spg": 1.1, "bpg": 0.3, "tov": 2.9, "fg": 0.473, "3pt": 0.358},
                {"name": "Jayson Tatum", "position": "SF", "salary": 23000000, "ppg": 26.9, "rpg": 8.0, "apg": 4.4, "spg": 1.0, "bpg": 0.6, "tov": 2.7, "fg": 0.453, "3pt": 0.353},
                {"name": "Al Horford", "position": "PF", "salary": 15500000, "ppg": 10.2, "rpg": 7.7, "apg": 3.4, "spg": 0.8, "bpg": 1.3, "tov": 1.4, "fg": 0.467, "3pt": 0.331},
                {"name": "Robert Williams III", "position": "C", "salary": 7800000, "ppg": 10.0, "rpg": 9.6, "apg": 2.0, "spg": 0.9, "bpg": 2.2, "tov": 1.3, "fg": 0.730, "3pt": 0.0},
                {"name": "Daniel Theis", "position": "C", "salary": 5800000, "ppg": 8.1, "rpg": 4.6, "apg": 1.2, "spg": 0.3, "bpg": 0.7, "tov": 1.0, "fg": 0.569, "3pt": 0.318},
                # Bench/utility players
                {"name": "Derrick White", "position": "PG", "salary": 4300000, "ppg": 11.0, "rpg": 3.4, "apg": 3.5, "spg": 0.8, "bpg": 0.9, "tov": 1.6, "fg": 0.426, "3pt": 0.316},
                {"name": "Grant Williams", "position": "PF", "salary": 2400000, "ppg": 7.8, "rpg": 3.6, "apg": 1.1, "spg": 0.5, "bpg": 0.8, "tov": 0.8, "fg": 0.471, "3pt": 0.417},
                {"name": "Payton Pritchard", "position": "PG", "salary": 1400000, "ppg": 6.2, "rpg": 2.3, "apg": 1.8, "spg": 0.5, "bpg": 0.1, "tov": 0.8, "fg": 0.413, "3pt": 0.414},
                {"name": "Aaron Nesmith", "position": "SF", "salary": 1000000, "ppg": 3.8, "rpg": 2.0, "apg": 0.5, "spg": 0.4, "bpg": 0.2, "tov": 0.5, "fg": 0.370, "3pt": 0.367},
                {"name": "Romeo Langford", "position": "SG", "salary": 1000000, "ppg": 2.8, "rpg": 1.7, "apg": 0.3, "spg": 0.3, "bpg": 0.1, "tov": 0.4, "fg": 0.364, "3pt": 0.290},
                {"name": "Sam Hauser", "position": "SF", "salary": 1000000, "ppg": 2.5, "rpg": 1.1, "apg": 0.2, "spg": 0.2, "bpg": 0.1, "tov": 0.2, "fg": 0.429, "3pt": 0.431},
                {"name": "Luke Kornet", "position": "C", "salary": 1000000, "ppg": 2.1, "rpg": 1.3, "apg": 0.3, "spg": 0.1, "bpg": 0.4, "tov": 0.3, "fg": 0.615, "3pt": 0.375}
            ]
        }
        
        # Create players for each team (check for existing players first)
        logger.info("Creating players...")
        total_players = 0
        
        for team in team_info:
            team_name = team["name"]
            team_salary = 0
            
            # Check if team already has players
            with repository.get_session() as session:
                existing_players = session.exec(
                    select(PlayerModel).where(PlayerModel.team_id == team["id"])
                ).all()
                
                if existing_players:
                    logger.info(f"Team {team_name} already has {len(existing_players)} players, skipping player creation")
                    team_salary = sum(player.salary for player in existing_players)
                    total_players += len(existing_players)
                else:
                    # Determine which player data to use
                    players_to_create = []
                    data_source = "hardcoded"
                    
                    if use_sleeper and team_name in sleeper_player_models:
                        sleeper_players = sleeper_player_models[team_name]
                        if len(sleeper_players) >= 13:
                            players_to_create = sleeper_players
                            data_source = "Sleeper cache"
                        else:
                            # Supplement with hardcoded data
                            players_to_create = sleeper_players
                            hardcoded_needed = 13 - len(sleeper_players)
                            hardcoded_players = players_data[team_name][:hardcoded_needed]
                            
                            # Convert hardcoded data to PlayerModel instances
                            for player_data in hardcoded_players:
                                player = PlayerModel(
                                    name=player_data["name"],
                                    team_id=team["id"],
                                    position=PositionEnum(player_data["position"]),
                                    salary=player_data["salary"],
                                    points_per_game=player_data["ppg"],
                                    rebounds_per_game=player_data["rpg"],
                                    assists_per_game=player_data["apg"],
                                    steals_per_game=player_data["spg"],
                                    blocks_per_game=player_data["bpg"],
                                    turnovers_per_game=player_data["tov"],
                                    field_goal_percentage=player_data["fg"],
                                    three_point_percentage=player_data["3pt"],
                                )
                                players_to_create.append(player)
                            
                            data_source = f"Sleeper cache + hardcoded supplement"
                            logger.info(f"Supplementing {team_name} with {hardcoded_needed} hardcoded players")
                    else:
                        # Use hardcoded data
                        hardcoded_players = players_data[team_name]
                        for player_data in hardcoded_players:
                            player = PlayerModel(
                                name=player_data["name"],
                                team_id=team["id"],
                                position=PositionEnum(player_data["position"]),
                                salary=player_data["salary"],
                                points_per_game=player_data["ppg"],
                                rebounds_per_game=player_data["rpg"],
                                assists_per_game=player_data["apg"],
                                steals_per_game=player_data["spg"],
                                blocks_per_game=player_data["bpg"],
                                turnovers_per_game=player_data["tov"],
                                field_goal_percentage=player_data["fg"],
                                three_point_percentage=player_data["3pt"],
                            )
                            players_to_create.append(player)
                    
                    logger.info(f"Creating {len(players_to_create)} players for {team_name} using {data_source}")
                    
                    # Create players in database
                    for player in players_to_create:
                        with repository.get_session() as session:
                            session.add(player)
                            session.commit()
                            team_salary += player.salary
                            total_players += 1
                            logger.info(f"Created player: {player.name} ({player.position.value}) - ${player.salary:,}")
            
            # Update team total salary and validate salary cap
            with repository.get_session() as session:
                db_team = session.get(TeamModel, team["id"])
                db_team.total_salary = team_salary
                session.commit()
                logger.info(f"Updated {team['name']} total salary: ${team_salary:,}")
                
                # Validate salary cap
                if team_salary > settings.salary_cap:
                    raise ValueError(f"Team {team['name']} salary ${team_salary:,} exceeds salary cap ${settings.salary_cap:,}")
        
        logger.info(f"Database seeding completed successfully!")
        logger.info(f"Created {len(team_info)} teams with {total_players} total players")
        logger.info(f"All teams validated under salary cap of ${settings.salary_cap:,}")
        
        # Validate roster compositions
        logger.info("Validating roster compositions...")
        for team in team_info:
            validation = repository.validate_roster_composition(team["id"])
            if validation['is_valid']:
                logger.info(f"{team['name']}: Roster is VALID")
            else:
                logger.warning(f"{team['name']}: Roster VIOLATIONS: {validation['violations']}")
        
    except Exception as e:
        logger.error(f"Database seeding failed: {e}")
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the Fantasy Basketball League database")
    parser.add_argument("--reset", action="store_true", help="Reset database before seeding")
    parser.add_argument("--use-sleeper", action="store_true", help="Use Sleeper cached data instead of hardcoded players")
    args = parser.parse_args()
    
    seed_database(reset=args.reset, use_sleeper=args.use_sleeper)