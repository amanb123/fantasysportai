"""
Test script to verify NBA schedule cache is working correctly
"""

import asyncio
import sys
from datetime import datetime, timedelta

sys.path.insert(0, '/Users/aman.buddaraju/fantasy-basketball-league')

from backend.dependencies import get_redis_service
from backend.services.nba_schedule_cache_service import get_schedule_cache_service
from backend.services.nba_mcp_service import get_nba_mcp_service
from backend.config import settings


async def test_schedule_cache():
    """Test schedule cache functionality"""
    
    print("\n=== Testing NBA Schedule Cache ===\n")
    
    # Initialize services
    redis_service = get_redis_service()
    nba_mcp_service = get_nba_mcp_service(settings.nba_mcp_server_path)
    schedule_cache = get_schedule_cache_service(redis_service, nba_mcp_service)
    
    # Test 1: Get full season schedule
    print("Test 1: Getting full season schedule...")
    full_schedule = await schedule_cache.get_full_season_schedule()
    print(f"✅ Retrieved {len(full_schedule)} total games")
    
    if full_schedule:
        sample_game = full_schedule[0]
        print(f"📋 Sample game structure: {sample_game}")
    
    # Test 2: Get games for next 7 days
    print("\nTest 2: Getting games for next 7 days...")
    today = datetime.now().date()
    end_date = today + timedelta(days=7)
    
    upcoming_games = await schedule_cache.get_games_for_date_range(
        start_date=today,
        end_date=end_date
    )
    
    print(f"✅ Found {len(upcoming_games)} games in next 7 days")
    
    # Test 3: Get games for specific team (Lakers)
    print("\nTest 3: Getting Lakers games in next 7 days...")
    lakers_games = [
        game for game in upcoming_games
        if game.get("home_team_tricode") == "LAL"
        or game.get("away_team_tricode") == "LAL"
    ]
    
    print(f"✅ Lakers have {len(lakers_games)} games in next 7 days")
    for game in lakers_games:
        home = game.get("home_team_tricode", "?")
        away = game.get("away_team_tricode", "?")
        game_date = game.get("game_date", "?")
        print(f"   📅 {game_date}: {away} @ {home}")
    
    # Test 4: Get games for specific team (Warriors)
    print("\nTest 4: Getting Warriors games in next 7 days...")
    warriors_games = [
        game for game in upcoming_games
        if game.get("home_team_tricode") == "GSW"
        or game.get("away_team_tricode") == "GSW"
    ]
    
    print(f"✅ Warriors have {len(warriors_games)} games in next 7 days")
    for game in warriors_games:
        home = game.get("home_team_tricode", "?")
        away = game.get("away_team_tricode", "?")
        game_date = game.get("game_date", "?")
        print(f"   📅 {game_date}: {away} @ {home}")
    
    print("\n=== All Tests Complete ===\n")


if __name__ == "__main__":
    asyncio.run(test_schedule_cache())
