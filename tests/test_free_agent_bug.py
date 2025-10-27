import pytest
"""
Test the free agent search bug fix.
Simulates asking the roster assistant: "what are some good free agents to pick up this week"
"""
import asyncio
import sys
from backend.agents.tools import RosterAdvisorTools
from backend.dependencies import get_sleeper_service, get_nba_stats_service, get_league_data_cache_service, get_player_cache_service


@pytest.mark.asyncio
async def test_free_agent_bug_fix():
    """Test that free agent search returns data-oriented answers."""
    print("🧪 Testing Free Agent Search Bug Fix")
    print("=" * 80)
    print("\n📋 Original Issue:")
    print("   User asked: 'what are some good free agents to pick up this week'")
    print("   LLM returned: Just names alphabetically (AJ Green, AJ Johnson, etc.)")
    print("   Problem: No stats, no rationale, no comparison with roster\n")
    print("=" * 80)
    print("\n🔧 Fix Applied:")
    print("   1. Enhanced search_available_players to fetch player stats")
    print("   2. Implemented fallback: If <25 games in 2025-26, use 2024-25 stats")
    print("   3. Sort by fantasy value (not alphabetically)")
    print("   4. Updated LLM prompt to compare with user's roster gaps\n")
    print("=" * 80)
    
    # Initialize services
    sleeper_service = get_sleeper_service()
    nba_stats_service = get_nba_stats_service()
    league_cache = get_league_data_cache_service()
    player_cache = get_player_cache_service()
    
    # Use real league data
    league_id = "1265480188934750208"
    roster_id = 1
    sleeper_user_id = "1145917800104538112"
    
    print("\n📦 Caching league data...")
    await league_cache.cache_league_data(league_id)
    await league_cache.cache_rosters(league_id)
    print("✅ League data cached\n")
    
    # Create tools executor
    tools = RosterAdvisorTools(
        league_id=league_id,
        roster_id=roster_id,
        sleeper_user_id=sleeper_user_id,
        league_cache_service=league_cache,
        player_cache_service=player_cache,
        sleeper_service=sleeper_service,
        nba_stats_service=nba_stats_service
    )
    
    print("=" * 80)
    print("\n🔍 TESTING: search_available_players tool")
    print("   (This is what the LLM calls when you ask about free agents)\n")
    
    # Test the actual tool call
    result = await tools.execute_tool("search_available_players", {"limit": 5})
    
    print(result)
    print("\n" + "=" * 80)
    
    # Analyze the result
    print("\n✅ VERIFICATION:")
    
    checks = {
        "Has player names": "**" in result,
        "Has PPG stats": "PPG" in result,
        "Has RPG stats": "RPG" in result,
        "Has APG stats": "APG" in result,
        "Has fantasy scores": "Fantasy Score:" in result or "Fantasy:" in result,
        "Shows season used": "2024-25" in result or "2025-26" in result,
        "Sorted by value (not alphabetical)": "Ranked by fantasy value" in result.lower() or "sorted" in result.lower(),
        "Has formula explanation": "Fantasy Score Formula" in result or "PTS + 1.2" in result
    }
    
    all_passed = True
    for check, passed in checks.items():
        status = "✓" if passed else "✗"
        print(f"   {status} {check}: {'PASS' if passed else 'FAIL'}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 80)
    
    if all_passed:
        print("\n🎉 SUCCESS! The bug is FIXED!")
        print("\n✅ The LLM now receives:")
        print("   • Actual player statistics (PPG, RPG, APG)")
        print("   • Fantasy value scores")
        print("   • Players ranked by performance (not alphabetically)")
        print("   • Season context (2024-25 fallback when 2025-26 insufficient)")
        print("\n✅ The LLM can now:")
        print("   • Make data-driven recommendations")
        print("   • Compare free agents with user's roster")
        print("   • Provide specific rationale with numbers")
        print("   • Identify positional gaps and statistical needs")
    else:
        print("\n❌ FAILED - Some checks did not pass")
        return 1
    
    print("\n" + "=" * 80)
    print("\n📝 Expected LLM Behavior (after fix):")
    print("   Instead of: 'Consider adding AJ Green, AJ Johnson...'")
    print("   Now gives: 'Top free agents by fantasy value:")
    print("              1. Player X - 18.5 PPG, 8.2 RPG, 3.1 APG (Fantasy: 32.4)")
    print("              2. Player Y - 15.2 PPG, 4.5 RPG, 6.8 APG (Fantasy: 30.1)")
    print("              Your roster averages X PPG at this position.")
    print("              Adding Player X would improve scoring by +Y PPG.'")
    print("\n" + "=" * 80)
    
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(test_free_agent_bug_fix())
    sys.exit(exit_code)
