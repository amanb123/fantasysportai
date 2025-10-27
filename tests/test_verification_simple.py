#!/usr/bin/env python3
"""
Simple file-based validation for verification comments.
"""

def test_comment_5_single_singleton():
    """Test that sleeper_service.py has only one singleton."""
    with open('backend/services/sleeper_service.py', 'r') as f:
        content = f.read()
    
    count = content.count('sleeper_service = SleeperService()')
    print(f"✓ Comment 5: Found {count} SleeperService singleton declaration(s)")
    assert count == 1, f"Should have exactly 1 singleton declaration, found {count}"
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

def test_comment_1_no_await_on_sync():
    """Test that get_cached_league_details calls don't have await."""
    with open('backend/main.py', 'r') as f:
        content = f.read()
    
    # Should NOT have await before get_cached_league_details
    bad_pattern_count = content.count('await league_cache.get_cached_league_details')
    
    # Should have sync calls
    good_pattern_count = content.count('league_cache.get_cached_league_details')
    
    print(f"✓ Comment 1: Cache method calls:")
    print(f"  - Calls with 'await': {bad_pattern_count}")
    print(f"  - Total calls: {good_pattern_count}")
    
    assert bad_pattern_count == 0, f"Found {bad_pattern_count} calls with await (should be 0)"
    assert good_pattern_count >= 2, f"Expected at least 2 calls, found {good_pattern_count}"
    
    return True

def test_comment_2_mock_has_method():
    """Test that mock AssistantAgent has a_generate_reply."""
    with open('backend/agents/agent_factory.py', 'r') as f:
        content = f.read()
    
    # Check mock class has the method
    has_method = 'async def a_generate_reply' in content or 'def a_generate_reply' in content
    
    print(f"✓ Comment 2: Mock AssistantAgent {'has' if has_method else 'lacks'} a_generate_reply()")
    assert has_method, "Mock should have a_generate_reply method"
    
    return True

def test_comment_3_redis_param():
    """Test that NBAStatsService accepts redis_service parameter."""
    with open('backend/services/nba_stats_service.py', 'r') as f:
        content = f.read()
    
    # Check __init__ has redis_service parameter
    has_param = 'def __init__(self, redis_service' in content
    
    # Check cache attributes are set
    has_cache_ttl = 'self.historical_cache_ttl' in content
    has_cache_prefix = 'self.historical_cache_prefix' in content
    
    print(f"✓ Comment 3: NBAStatsService Redis integration:")
    print(f"  - __init__ has redis_service param: {has_param}")
    print(f"  - Sets historical_cache_ttl: {has_cache_ttl}")
    print(f"  - Sets historical_cache_prefix: {has_cache_prefix}")
    
    assert has_param, "Should accept redis_service parameter"
    assert has_cache_ttl and has_cache_prefix, "Should set cache configuration"
    
    return True

def test_comment_4_date_range_logic():
    """Test that _fetch_historical_stats_if_needed has date range logic."""
    with open('backend/services/roster_context_builder.py', 'r') as f:
        content = f.read()
    
    # Check for "around this time" handling
    has_around_this_time = 'if "around this time"' in content.lower()
    has_date_range_call = 'fetch_player_stats_by_date_range' in content
    has_timedelta = 'timedelta' in content
    
    print(f"✓ Comment 4: Date range logic for 'around this time':")
    print(f"  - Detects 'around this time': {has_around_this_time}")
    print(f"  - Calls fetch_player_stats_by_date_range: {has_date_range_call}")
    print(f"  - Uses timedelta for ±14 days: {has_timedelta}")
    
    assert has_around_this_time, "Should detect 'around this time'"
    assert has_date_range_call, "Should call fetch_player_stats_by_date_range"
    
    return True

def test_comment_6_metadata_field():
    """Test that to_pydantic uses message_metadata field."""
    with open('backend/session/models.py', 'r') as f:
        content = f.read()
    
    # Find the RosterChatMessageModel.to_pydantic method
    lines = content.split('\n')
    in_method = False
    method_lines = []
    
    for i, line in enumerate(lines):
        if 'class RosterChatMessageModel' in line:
            in_method = False
            method_lines = []
        elif 'def to_pydantic(self):' in line and method_lines == []:
            in_method = True
            method_lines.append(line)
        elif in_method:
            method_lines.append(line)
            if line.strip().startswith('def ') and 'to_pydantic' not in line:
                break
            if line.strip().startswith('class '):
                break
    
    method_content = '\n'.join(method_lines)
    
    has_message_metadata = 'message_metadata' in method_content.lower()
    returns_metadata = '"metadata"' in method_content or "'metadata'" in method_content
    no_session_id_in_return = '"session_id": self.session_id' not in method_content
    
    print(f"✓ Comment 6: to_pydantic() implementation:")
    print(f"  - Reads from message_metadata: {has_message_metadata}")
    print(f"  - Returns 'metadata' field: {returns_metadata}")
    print(f"  - Does not expose session_id FK: {no_session_id_in_return}")
    
    assert has_message_metadata, "Should read from message_metadata"
    assert returns_metadata, "Should return metadata field"
    assert no_session_id_in_return, "Should not expose session_id"
    
    return True

def main():
    """Run all validation tests."""
    print("=" * 60)
    print("Verification Comments - Simple File Validation")
    print("=" * 60)
    print()
    
    tests = [
        ("Comment 1: No await on sync cache", test_comment_1_no_await_on_sync),
        ("Comment 2: Mock a_generate_reply", test_comment_2_mock_has_method),
        ("Comment 3: Redis integration", test_comment_3_redis_param),
        ("Comment 4: Date range logic", test_comment_4_date_range_logic),
        ("Comment 5: Single singleton", test_comment_5_single_singleton),
        ("Comment 6: Metadata field", test_comment_6_metadata_field),
        ("Comment 7: Lazy imports", test_comment_7_lazy_imports),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            print(f"{name}:")
            test_func()
            passed += 1
            print()
        except AssertionError as e:
            print(f"  ❌ FAILED: {e}")
            print()
            failed += 1
        except Exception as e:
            print(f"  ❌ ERROR: {e}")
            print()
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
    import sys
    sys.exit(main())
