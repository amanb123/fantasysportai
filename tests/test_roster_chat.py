import pytest
#!/usr/bin/env python3
"""
Test script for Roster Chat functionality
Tests all context building methods and chat response generation
"""

import asyncio
import sys
import os
from datetime import datetime
from uuid import uuid4

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.config import settings
from backend.services.nba_stats_service import NBAStatsService
from backend.services.sleeper_service import SleeperService
from backend.services.league_data_cache_service import LeagueDataCacheService
from backend.services.redis_service import RedisService
from backend.services.roster_context_builder import RosterContextBuilder
from backend.agents.agent_factory import AgentFactory
from backend.session.database import get_engine, get_repository
from backend.session.repository import BasketballRepository
from sqlmodel import select
from backend.session.models import UserModel


class Colors:
    """Terminal colors for better output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_header(text):
    """Print formatted header"""
    print(f"\n{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{text.center(80)}{Colors.ENDC}")
    print(f"{Colors.HEADER}{Colors.BOLD}{'='*80}{Colors.ENDC}\n")


def print_success(text):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {text}{Colors.ENDC}")


def print_error(text):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {text}{Colors.ENDC}")


def print_info(text):
    """Print info message"""
    print(f"{Colors.OKCYAN}→ {text}{Colors.ENDC}")


def print_warning(text):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {text}{Colors.ENDC}")


@pytest.mark.asyncio
async def test_nba_stats_service():
    """Test NBAStatsService historical stats methods"""
    print_header("Testing NBAStatsService")
    
    service = NBAStatsService()
    test_player = "LeBron James"
    
    try:
        # Test 1: Search player by name
        print_info(f"Testing search_player_by_name('{test_player}')...")
        player_id = await service.search_player_by_name(test_player)
        if player_id:
            print_success(f"Found player ID: {player_id}")
        else:
            print_error(f"Could not find player: {test_player}")
            return False
        
        # Test 2: Fetch career stats
        print_info(f"Testing fetch_player_career_stats({player_id})...")
        career_stats = await service.fetch_player_career_stats(player_id)
        if career_stats and 'career_totals' in career_stats:
            print_success(f"Retrieved career stats: {len(career_stats.get('seasons', []))} seasons")
            print(f"  Career totals: {career_stats['career_totals'].get('PTS', 0)} PTS, "
                  f"{career_stats['career_totals'].get('REB', 0)} REB, "
                  f"{career_stats['career_totals'].get('AST', 0)} AST")
        else:
            print_error("Failed to retrieve career stats")
            return False
        
        # Test 3: Fetch season averages
        print_info(f"Testing fetch_player_season_averages({player_id}, '2023-24')...")
        season_avg = await service.fetch_player_season_averages(player_id, "2023-24")
        if season_avg:
            print_success(f"Retrieved 2023-24 averages: {season_avg.get('PTS', 0):.1f} PPG, "
                         f"{season_avg.get('REB', 0):.1f} RPG, {season_avg.get('AST', 0):.1f} APG")
        else:
            print_warning("Could not retrieve season averages (player may not have played that season)")
        
        # Test 4: Fetch game log
        print_info(f"Testing fetch_player_game_log({player_id}, '2023-24')...")
        game_log = await service.fetch_player_game_log(player_id, "2023-24")
        if game_log:
            print_success(f"Retrieved game log: {len(game_log)} games")
            if game_log:
                print(f"  First game: {game_log[0].get('PTS', 0)} PTS on {game_log[0].get('GAME_DATE', 'N/A')}")
        else:
            print_warning("Could not retrieve game log")
        
        return True
        
    except Exception as e:
        print_error(f"NBAStatsService test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_sleeper_service():
    """Test SleeperService league details method"""
    print_header("Testing SleeperService")
    
    service = SleeperService()
    
    # Use a real league ID from your environment or a test league
    test_league_id = os.getenv("TEST_LEAGUE_ID", "1126851596966465536")
    
    try:
        print_info(f"Testing get_league_details('{test_league_id}')...")
        league_details = await service.get_league_details(test_league_id)
        
        if league_details:
            print_success(f"Retrieved league details for: {league_details.get('name', 'Unknown')}")
            print(f"  Total rosters: {league_details.get('total_rosters', 0)}")
            print(f"  Sport: {league_details.get('sport', 'N/A')}")
            print(f"  Season: {league_details.get('season', 'N/A')}")
            
            # Check scoring settings
            scoring = league_details.get('scoring_settings', {})
            if scoring:
                print_success(f"Retrieved scoring settings: {len(scoring)} stat categories")
                sample_stats = list(scoring.items())[:3]
                for stat, value in sample_stats:
                    print(f"    {stat}: {value}")
            
            # Check roster positions
            positions = league_details.get('roster_positions', [])
            if positions:
                print_success(f"Retrieved roster positions: {len(positions)} slots")
                print(f"    Positions: {', '.join(positions[:10])}")
            
            return True
        else:
            print_error(f"Could not retrieve league details for {test_league_id}")
            return False
            
    except Exception as e:
        print_error(f"SleeperService test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_league_data_cache_service():
    """Test LeagueDataCacheService methods"""
    print_header("Testing LeagueDataCacheService")
    
    sleeper_service = SleeperService()
    redis_service = RedisService()
    service = LeagueDataCacheService(redis_service, sleeper_service)
    
    test_league_id = os.getenv("TEST_LEAGUE_ID", "1126851596966465536")
    
    try:
        print_info(f"Testing get_cached_league_details('{test_league_id}')...")
        league_details = await service.get_cached_league_details(test_league_id)
        
        if league_details:
            print_success(f"Retrieved cached league details")
            
            # Test get_league_scoring_settings
            print_info("Testing get_league_scoring_settings()...")
            scoring = await service.get_league_scoring_settings(test_league_id)
            if scoring:
                print_success(f"Retrieved scoring settings: {len(scoring)} categories")
            else:
                print_warning("No scoring settings found")
            
            # Test get_league_roster_positions
            print_info("Testing get_league_roster_positions()...")
            positions = await service.get_league_roster_positions(test_league_id)
            if positions:
                print_success(f"Retrieved roster positions: {len(positions)} slots")
            else:
                print_warning("No roster positions found")
            
            return True
        else:
            print_error("Could not retrieve cached league details")
            return False
            
    except Exception as e:
        print_error(f"LeagueDataCacheService test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


@pytest.mark.asyncio
async def test_roster_context_builder():
    """Test RosterContextBuilder comprehensive context generation"""
    print_header("Testing RosterContextBuilder")
    
    # Initialize services
    nba_service = NBAStatsService()
    sleeper_service = SleeperService()
    redis_service = RedisService()
    cache_service = LeagueDataCacheService(redis_service, sleeper_service)
    context_builder = RosterContextBuilder(nba_service, sleeper_service, cache_service)
    
    test_league_id = os.getenv("TEST_LEAGUE_ID", "1126851596966465536")
    test_roster_id = 1  # Use first roster
    
    try:
        # Test 1: Build context without historical stats
        print_info(f"Testing build_roster_context() without historical stats...")
        context = await context_builder.build_roster_context(
            league_id=test_league_id,
            roster_id=test_roster_id,
            user_message="Who should I start this week?",
            include_historical=False
        )
        
        if context:
            print_success(f"Generated context: {len(context)} characters")
            
            # Check for key sections
            sections = [
                ("League Rules", "## League Rules and Scoring"),
                ("Current Roster", "## Current Roster"),
                ("Upcoming Schedule", "## Upcoming Schedule"),
                ("Injury Report", "## Injury Report"),
                ("Recent Performance", "## Recent Performance")
            ]
            
            for section_name, section_marker in sections:
                if section_marker in context:
                    print_success(f"  Contains {section_name} section")
                else:
                    print_warning(f"  Missing {section_name} section")
            
            # Show context preview
            print(f"\n{Colors.BOLD}Context Preview (first 500 chars):{Colors.ENDC}")
            print(f"{context[:500]}...\n")
        else:
            print_error("Failed to generate context")
            return False
        
        # Test 2: Build context with historical stats query
        print_info(f"Testing build_roster_context() with historical query...")
        historical_context = await context_builder.build_roster_context(
            league_id=test_league_id,
            roster_id=test_roster_id,
            user_message="What was LeBron James scoring average in 2022?",
            include_historical=True
        )
        
        if historical_context:
            print_success(f"Generated context with historical data: {len(historical_context)} characters")
            if "Historical Stats" in historical_context or "Career Stats" in historical_context:
                print_success("  Contains historical stats section")
            else:
                print_warning("  Historical stats not found (player may not be on roster)")
        else:
            print_error("Failed to generate context with historical data")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"RosterContextBuilder test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_factory():
    """Test AgentFactory roster advisor creation"""
    print_header("Testing AgentFactory")
    
    factory = AgentFactory()
    
    test_context = """
    ## League Rules
    - Points: 1.0 per point
    - Rebounds: 1.2 per rebound
    - Assists: 1.5 per assist
    
    ## Current Roster
    - Starters: LeBron James (PF), Stephen Curry (PG)
    - Bench: Anthony Davis (C)
    """
    
    try:
        print_info("Testing create_roster_advisor_agent()...")
        agent = factory.create_roster_advisor_agent(roster_context=test_context)
        
        if agent:
            print_success("Created roster advisor agent")
            print(f"  Agent name: {agent.name}")
            print(f"  System message length: {len(agent.system_message)} characters")
            
            # Check system message contains key elements
            if test_context in agent.system_message:
                print_success("  System message contains roster context")
            else:
                print_warning("  System message may not contain full context")
            
            return True
        else:
            print_error("Failed to create roster advisor agent")
            return False
            
    except Exception as e:
        print_error(f"AgentFactory test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def test_chat_repository():
    """Test Repository chat methods"""
    print_header("Testing Repository Chat Methods")
    
    # Initialize repository
    engine = get_engine()
    repository = BasketballRepository(engine)
    test_user_id = None
    test_session_id = None
    
    try:
        # Get or create a test user
        print_info("Getting test user...")
        with repository.get_session() as session:
            result = session.exec(
                select(UserModel).where(UserModel.sleeper_user_id == "test_user_roster_chat")
            )
            user = result.first()
            
            if not user:
                print_info("Creating test user...")
                user = UserModel(
                    sleeper_user_id="test_user_roster_chat",
                    display_name="Test User",
                    avatar="test_avatar"
                )
                session.add(user)
                session.commit()
                session.refresh(user)
            
            test_user_id = user.id
            print_success(f"Using test user ID: {test_user_id}")
        
        # Test 1: Create roster chat session
        print_info("Testing create_roster_chat_session()...")
        session_id = repository.create_roster_chat_session(
            user_id=test_user_id,
            sleeper_user_id="test_user_roster_chat",
            league_id="test_league_123",
            roster_id=1
        )
        
        if session_id:
            print_success(f"Created chat session: {session_id}")
            test_session_id = session_id
        else:
            print_error("Failed to create chat session")
            return False
        
        # Test 2: Get roster chat session
        print_info("Testing get_roster_chat_session()...")
        session = repository.get_roster_chat_session(session_id)
        
        if session:
            print_success(f"Retrieved session: {session.session_id}")
            print(f"  League ID: {session.league_id}")
            print(f"  Roster ID: {session.roster_id}")
            print(f"  Status: {session.status}")
        else:
            print_error("Failed to retrieve chat session")
            return False
        
        # Test 3: Add chat messages
        print_info("Testing add_roster_chat_message()...")
        
        # Add user message
        user_msg = repository.add_roster_chat_message(
            session_id=session_id,
            role="user",
            content="Who should I start this week?",
            metadata={"test": True}
        )
        
        if user_msg:
            print_success(f"Added user message: {user_msg.id}")
        else:
            print_error("Failed to add user message")
            return False
        
        # Add assistant message
        assistant_msg = repository.add_roster_chat_message(
            session_id=session_id,
            role="assistant",
            content="Based on your roster and upcoming schedule, I recommend...",
            metadata={"test": True}
        )
        
        if assistant_msg:
            print_success(f"Added assistant message: {assistant_msg.id}")
        else:
            print_error("Failed to add assistant message")
            return False
        
        # Test 4: Get chat messages
        print_info("Testing get_chat_messages()...")
        messages = repository.get_chat_messages(session_id)
        
        if messages and len(messages) == 2:
            print_success(f"Retrieved {len(messages)} messages")
            for msg in messages:
                print(f"  {msg.role}: {msg.content[:50]}...")
        else:
            print_error(f"Expected 2 messages, got {len(messages) if messages else 0}")
            return False
        
        # Test 5: Get chat history for context
        print_info("Testing get_chat_history_for_context()...")
        history = repository.get_chat_history_for_context(session_id, max_messages=10)
        
        if history and len(history) == 2:
            print_success(f"Retrieved history with {len(history)} messages")
            for msg in history:
                print(f"  {msg['role']}: {msg['content'][:50]}...")
        else:
            print_error("Failed to retrieve chat history for context")
            return False
        
        # Test 6: Get user roster chat sessions
        print_info("Testing get_user_roster_chat_sessions()...")
        sessions = repository.get_user_roster_chat_sessions("test_user_roster_chat")
        
        if sessions and len(sessions) >= 1:
            print_success(f"Retrieved {len(sessions)} sessions for user")
            for s in sessions:
                print(f"  Session: {s.session_id} - {s.status}")
        else:
            print_error("Failed to retrieve user sessions")
            return False
        
        # Test 7: Update session last message
        print_info("Testing update_chat_session_last_message()...")
        updated = repository.update_chat_session_last_message(session_id)
        
        if updated:
            print_success("Updated session last_message_at timestamp")
        else:
            print_error("Failed to update session timestamp")
            return False
        
        # Test 8: Archive session
        print_info("Testing archive_chat_session()...")
        archived = repository.archive_chat_session(session_id)
        
        if archived:
            print_success("Archived chat session")
            
            # Verify status changed
            archived_session = repository.get_roster_chat_session(session_id)
            if archived_session and archived_session.status == "archived":
                print_success("  Status changed to 'archived'")
            else:
                print_warning("  Status may not have changed")
        else:
            print_error("Failed to archive session")
            return False
        
        return True
        
    except Exception as e:
        print_error(f"Repository test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def test_end_to_end_chat():
    """Test complete chat flow with response generation"""
    print_header("Testing End-to-End Chat Flow")
    
    # Initialize all services
    nba_service = NBAStatsService()
    sleeper_service = SleeperService()
    redis_service = RedisService()
    cache_service = LeagueDataCacheService(redis_service, sleeper_service)
    context_builder = RosterContextBuilder(nba_service, sleeper_service, cache_service)
    agent_factory = AgentFactory()
    engine = get_engine()
    repository = BasketballRepository(engine)
    
    test_league_id = os.getenv("TEST_LEAGUE_ID", "1126851596966465536")
    test_roster_id = 1
    
    try:
        # Step 1: Create session
        print_info("Step 1: Creating chat session...")
        session_id = repository.create_roster_chat_session(
            user_id=1,  # Assume test user ID 1
            sleeper_user_id="test_e2e_user",
            league_id=test_league_id,
            roster_id=test_roster_id
        )
        
        if not session_id:
            print_error("Failed to create session")
            return False
        
        print_success(f"Created session: {session_id}")
        
        # Step 2: Add user message
        user_message = "Who should I start this week? Also, what was LeBron's average last season?"
        print_info(f"Step 2: Adding user message: '{user_message}'")
        
        user_msg = repository.add_roster_chat_message(
            session_id=session_id,
            role="user",
            content=user_message,
            metadata={}
        )
        
        if not user_msg:
            print_error("Failed to add user message")
            return False
        
        print_success("Added user message")
        
        # Step 3: Build context (with historical stats)
        print_info("Step 3: Building roster context with historical stats...")
        context = await context_builder.build_roster_context(
            league_id=test_league_id,
            roster_id=test_roster_id,
            user_message=user_message,
            include_historical=True
        )
        
        if not context:
            print_error("Failed to build context")
            return False
        
        print_success(f"Built context: {len(context)} characters")
        print(f"\n{Colors.BOLD}Context sections found:{Colors.ENDC}")
        
        sections = [
            "League Rules",
            "Current Roster",
            "Upcoming Schedule",
            "Injury Report",
            "Recent Performance",
            "Historical Stats"
        ]
        
        for section in sections:
            if section in context:
                print_success(f"  ✓ {section}")
            else:
                print_warning(f"  ✗ {section}")
        
        # Step 4: Create agent with context
        print_info("Step 4: Creating roster advisor agent...")
        agent = agent_factory.create_roster_advisor_agent(roster_context=context)
        
        if not agent:
            print_error("Failed to create agent")
            return False
        
        print_success("Created roster advisor agent")
        
        # Step 5: Generate response (simulated - would normally call LLM)
        print_info("Step 5: Generating response...")
        
        # Get chat history for context
        history = repository.get_chat_history_for_context(session_id, max_messages=10)
        
        print_success(f"Retrieved chat history: {len(history)} previous messages")
        
        # Simulate LLM response (in real implementation, this would call agent.generate_reply)
        simulated_response = f"""Based on your roster analysis and league rules:

**Lineup Recommendations:**
- Your starters should be set based on their upcoming schedule
- Consider lock-in timing for your league's rules

**Historical Context:**
- LeBron James averaged 25.7 PPG, 7.3 RPG, 8.3 APG in the 2023-24 season
- This is relevant context for your lineup decisions

**Key Considerations:**
- Monitor injury reports before games
- Check opponent defensive rankings
- Consider your league's scoring settings

Would you like me to analyze any specific matchups or players?"""
        
        print_success("Generated response (simulated)")
        print(f"\n{Colors.BOLD}Response:{Colors.ENDC}")
        print(simulated_response[:300] + "...\n")
        
        # Step 6: Add assistant response
        print_info("Step 6: Adding assistant response...")
        
        assistant_msg = repository.add_roster_chat_message(
            session_id=session_id,
            role="assistant",
            content=simulated_response,
            metadata={"model": "test", "tokens": 100}
        )
        
        if not assistant_msg:
            print_error("Failed to add assistant message")
            return False
        
        print_success("Added assistant response")
        
        # Step 7: Verify complete conversation
        print_info("Step 7: Verifying complete conversation...")
        
        messages = repository.get_chat_messages(session_id)
        
        if messages and len(messages) == 2:
            print_success(f"Conversation complete with {len(messages)} messages")
            print(f"\n{Colors.BOLD}Conversation History:{Colors.ENDC}")
            for i, msg in enumerate(messages, 1):
                print(f"\n{Colors.BOLD}{i}. {msg.role.upper()}:{Colors.ENDC}")
                print(f"   {msg.content[:100]}...")
        else:
            print_error(f"Expected 2 messages, found {len(messages) if messages else 0}")
            return False
        
        # Step 8: Clean up - archive session
        print_info("Step 8: Cleaning up - archiving session...")
        repository.archive_chat_session(session_id)
        print_success("Session archived")
        
        return True
        
    except Exception as e:
        print_error(f"End-to-end test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("╔════════════════════════════════════════════════════════════════════════════╗")
    print("║                    ROSTER CHAT BACKEND TEST SUITE                          ║")
    print("║                                                                            ║")
    print(f"║  Testing all context methods and chat functionality                       ║")
    print(f"║  Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}                                               ║")
    print("╚════════════════════════════════════════════════════════════════════════════╝")
    print(f"{Colors.ENDC}\n")
    
    # Configuration check
    print_header("Configuration Check")
    print_info(f"NBA API Request Delay: {settings.NBA_API_REQUEST_DELAY}s")
    print_info(f"NBA Historical Cache TTL: {settings.NBA_HISTORICAL_STATS_CACHE_TTL}s")
    print_info(f"Roster Chat Max History: {settings.ROSTER_CHAT_MAX_HISTORY_MESSAGES}")
    print_info(f"Roster Chat Max Context Tokens: {settings.ROSTER_CHAT_MAX_CONTEXT_TOKENS}")
    print_info(f"Historical Stats Enabled: {settings.ROSTER_CHAT_ENABLE_HISTORICAL_STATS}")
    
    # Run tests
    results = {}
    
    async_tests = [
        ("NBA Stats Service", test_nba_stats_service),
        ("Sleeper Service", test_sleeper_service),
        ("League Data Cache Service", test_league_data_cache_service),
        ("Roster Context Builder", test_roster_context_builder),
        ("Agent Factory", test_agent_factory),
        ("End-to-End Chat Flow", test_end_to_end_chat),
    ]
    
    sync_tests = [
        ("Repository Chat Methods", test_chat_repository),
    ]
    
    # Run async tests
    for test_name, test_func in async_tests:
        try:
            result = await test_func()
            results[test_name] = result
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {str(e)}")
            results[test_name] = False
    
    # Run sync tests
    for test_name, test_func in sync_tests:
        try:
            result = test_func()
            results[test_name] = result
        except Exception as e:
            print_error(f"Test '{test_name}' crashed: {str(e)}")
            results[test_name] = False
    
    # Print summary
    print_header("Test Summary")
    
    total_tests = len(results)
    passed_tests = sum(1 for v in results.values() if v)
    failed_tests = total_tests - passed_tests
    
    for test_name, result in results.items():
        if result:
            print_success(f"{test_name}: PASSED")
        else:
            print_error(f"{test_name}: FAILED")
    
    print(f"\n{Colors.BOLD}Results:{Colors.ENDC}")
    print(f"  Total Tests: {total_tests}")
    print(f"  {Colors.OKGREEN}Passed: {passed_tests}{Colors.ENDC}")
    print(f"  {Colors.FAIL}Failed: {failed_tests}{Colors.ENDC}")
    
    if failed_tests == 0:
        print(f"\n{Colors.OKGREEN}{Colors.BOLD}✓ ALL TESTS PASSED!{Colors.ENDC}\n")
        return 0
    else:
        print(f"\n{Colors.FAIL}{Colors.BOLD}✗ SOME TESTS FAILED{Colors.ENDC}\n")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
