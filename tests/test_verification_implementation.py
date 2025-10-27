#!/usr/bin/env python3
"""
Quick validation test for verification comments implementation.
Tests the core changes without requiring full backend startup.
"""

import sys
import os

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

def test_comment_1_sync_cache_method():
    """Test that get_cached_league_details is not async."""
    from backend.services.league_data_cache_service import LeagueDataCacheService
    import inspect
    
    # Check method is not a coroutine
    method = LeagueDataCacheService.get_cached_league_details
    is_coroutine = inspect.iscoroutinefunction(method)
    
    print(f"✓ Comment 1: get_cached_league_details is {'async' if is_coroutine else 'sync'}")
    assert not is_coroutine, "Method should be synchronous"
    return True

def test_comment_2_mock_agent_method():
    """Test that mock AssistantAgent has a_generate_reply method."""
    import sys
    import importlib
    
    # Import the module
    spec = importlib.util.spec_from_file_location(
        "agent_factory", 
        "backend/agents/agent_factory.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    
    # Check mock AssistantAgent has a_generate_reply
    agent = module.AssistantAgent()
    has_method = hasattr(agent, 'a_generate_reply')
    
    print(f"✓ Comment 2: Mock AssistantAgent {'has' if has_method else 'lacks'} a_generate_reply()")
    assert has_method, "Mock should have a_generate_reply method"
    
    # Test it's callable and async
    import inspect
    is_async = inspect.iscoroutinefunction(agent.a_generate_reply)
    print(f"  - Method is {'async' if is_async else 'sync'}")
    assert is_async, "Method should be async"
    
    return True

def test_comment_3_redis_caching_integration():
    """Test that NBAStatsService accepts redis_service parameter."""
    from backend.services.nba_stats_service import NBAStatsService
    import inspect
    
    # Check __init__ signature
    sig = inspect.signature(NBAStatsService.__init__)
    params = list(sig.parameters.keys())
    
    has_redis = 'redis_service' in params
    print(f"✓ Comment 3: NBAStatsService __init__ {'has' if has_redis else 'lacks'} redis_service parameter")
    assert has_redis, "Should accept redis_service parameter"
    
    # Create instance with None (no redis)
    service = NBAStatsService(redis_service=None)
    has_attrs = hasattr(service, 'historical_cache_ttl') and hasattr(service, 'historical_cache_prefix')
    print(f"  - Service has cache configuration: {has_attrs}")
    assert has_attrs, "Should have cache configuration attributes"
    
    return True

def test_comment_5_single_singleton():
    """Test that sleeper_service.py has only one singleton."""
    with open('backend/services/sleeper_service.py', 'r') as f:
        content = f.read()
    
    count = content.count('sleeper_service = SleeperService()')
    print(f"✓ Comment 5: Found {count} SleeperService singleton declaration(s)")
    assert count == 1, "Should have exactly 1 singleton declaration"
    return True

def test_comment_6_metadata_field():
    """Test that RosterChatMessageModel.to_pydantic uses correct field."""
    from backend.session.models import RosterChatMessageModel
    import inspect
    
    # Check method source
    source = inspect.getsource(RosterChatMessageModel.to_pydantic)
    
    has_message_metadata = 'message_metadata' in source
    has_metadata_return = '"metadata"' in source or "'metadata'" in source
    lacks_session_id_return = '"session_id"' not in source or 'self.session_id' not in source
    
    print(f"✓ Comment 6: to_pydantic() implementation:")
    print(f"  - Reads from message_metadata: {has_message_metadata}")
    print(f"  - Returns 'metadata' field: {has_metadata_return}")
    print(f"  - Does not expose session_id FK: {lacks_session_id_return}")
    
    assert has_message_metadata, "Should read from message_metadata"
    assert has_metadata_return, "Should return metadata field"
    
    return True

def test_comment_7_lazy_imports():
    """Test that nba_api imports are lazy (not at module level)."""
    with open('backend/services/nba_stats_service.py', 'r') as f:
        lines = f.readlines()
    
    # Check top 20 lines for nba_api imports
    top_lines = ''.join(lines[:20])
    
    has_top_level_career = 'from nba_api.stats.endpoints import playercareerstats' in top_lines
    has_top_level_gamelog = 'from nba_api.stats.endpoints import playergamelog' in top_lines
    has_top_level_players = 'from nba_api.stats.static import players' in top_lines
    
    print(f"✓ Comment 7: nba_api imports are lazy:")
    print(f"  - No top-level playercareerstats import: {not has_top_level_career}")
    print(f"  - No top-level playergamelog import: {not has_top_level_gamelog}")
    print(f"  - No top-level players import: {not has_top_level_players}")
    
    assert not has_top_level_career, "playercareerstats should be lazy imported"
    assert not has_top_level_gamelog, "playergamelog should be lazy imported"
    assert not has_top_level_players, "players should be lazy imported"
    
    return True

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Verification Comments Implementation - Validation Tests")
    print("=" * 60)
    print()
    
    tests = [
        ("Comment 1: Sync cache method", test_comment_1_sync_cache_method),
        ("Comment 2: Mock agent a_generate_reply", test_comment_2_mock_agent_method),
        ("Comment 3: Redis caching integration", test_comment_3_redis_caching_integration),
        ("Comment 5: Single singleton", test_comment_5_single_singleton),
        ("Comment 6: Metadata field mapping", test_comment_6_metadata_field),
        ("Comment 7: Lazy imports", test_comment_7_lazy_imports),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"\n{name}:")
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            failed += 1
    
    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed")
    print("=" * 60)
    
    if failed == 0:
        print("✅ All verification comments implemented successfully!")
        return 0
    else:
        print(f"❌ {failed} test(s) failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
