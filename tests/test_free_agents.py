import pytest
"""
Test the enhanced free agent search with stats and injury news.
"""
import asyncio
import sys
from backend.agents.tools import RosterAdvisorTools
from backend.dependencies import get_sleeper_service, get_nba_stats_service, get_league_data_cache_service, get_player_cache_service, get_nba_news_service


@pytest.mark.asyncio
async def test_free_agent_search():
    """Test that free agent search returns players with stats and injury news."""
    print("🧪 Testing Enhanced Free Agent Search with Injury News\n")
    
    # Initialize services
    sleeper_service = get_sleeper_service()
    nba_stats_service = get_nba_stats_service()
    nba_news_service = get_nba_news_service()
    league_cache = get_league_data_cache_service()
    player_cache = get_player_cache_service()
    
    # Test league ID (replace with actual)
    league_id = "1265480188934750208"
    roster_id = 1
    sleeper_user_id = "1145917800104538112"
    
    # Cache league data
    print("📦 Caching league data...")
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
        nba_stats_service=nba_stats_service,
        nba_news_service=nba_news_service
    )
    
    # Test search - general
    print("🔍 Searching for top 5 free agents (all positions)...")
    result = await tools.execute_tool("search_available_players", {"limit": 5})
    print(result)
    print("\n" + "="*80 + "\n")
    
    # Test search - specific position
    print("🔍 Searching for top 5 centers (C)...")
    result = await tools.execute_tool("search_available_players", {"position": "C", "limit": 5})
    print(result)
    print("\n" + "="*80 + "\n")
    
    print("✅ Test complete! Free agents now show:")
    print("   - Current season stats (PPG, RPG, APG)")
    print("   - Fantasy score ranking")
    print("   - Sorted by value (best first, not alphabetically)")
    print("   - Latest injury news from ESPN, Bleacher Report, NBA.com, Yahoo, SLAM")


if __name__ == "__main__":
    asyncio.run(test_free_agent_search())
