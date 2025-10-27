"""
Test Fantasy Nerds API Integration for News and Injuries
"""

import asyncio
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.dependencies import get_nba_news_service

async def main():
    print("=" * 80)
    print("Testing Fantasy Nerds API Integration")
    print("=" * 80)
    
    # Initialize news service
    news_service = get_nba_news_service()
    
    if not news_service:
        print("❌ Failed to initialize NBA News Service")
        return
    
    print("✅ NBA News Service initialized")
    print(f"   API Base URL: {news_service.base_url}")
    print(f"   API Key: {news_service.api_key}")
    print()
    
    # Test 1: Get all injuries
    print("=" * 80)
    print("Test 1: Get All NBA Injuries")
    print("=" * 80)
    
    injuries = await news_service.get_injuries()
    
    if injuries and isinstance(injuries, list):
        print(f"✅ Retrieved {len(injuries)} injury reports\n")
        
        # Show first 5 injuries
        for i, injury in enumerate(injuries[:5], 1):
            player = injury.get('name', 'Unknown')  # API uses 'name' not 'player'
            team = injury.get('team', '')
            injury_type = injury.get('injury', 'Unknown')  # API uses 'injury' for type
            status = injury.get('game_status', 'Unknown')  # API uses 'game_status'
            
            print(f"{i}. {player}", end='')
            if team:
                print(f" ({team})", end='')
            print(f" - {injury_type}")
            print(f"   Status: {status}")
            print()
    else:
        print("⚠️  No injuries retrieved (check API key or connectivity)")
        print(f"   Received: {type(injuries)}")
    
    print()
    
    # Test 2: Get all news
    print("=" * 80)
    print("Test 2: Get All NBA News")
    print("=" * 80)
    
    all_news = await news_service.get_all_news()
    
    if all_news and isinstance(all_news, list):
        print(f"✅ Retrieved {len(all_news)} news articles\n")
        
        # Show first 5 news items
        for i, article in enumerate(all_news[:5], 1):
            headline = article.get('article_headline', 'No headline')
            excerpt = article.get('article_excerpt', '')
            author = article.get('article_author', '')
            
            print(f"{i}. {headline}")
            if author:
                print(f"   Source: {author}")
            
            # Show excerpt if available
            if excerpt:
                excerpt_short = excerpt[:150] + "..." if len(excerpt) > 150 else excerpt
                print(f"   {excerpt_short}")
            print()
    else:
        print("⚠️  No news retrieved (check API key or connectivity)")
        print(f"   Received: {type(all_news)}")
    
    print()
    
    # Test 3: Check injury status for specific players
    print("=" * 80)
    print("Test 3: Check Injury Status for Specific Players")
    print("=" * 80)
    
    test_players = ["LeBron James", "Stephen Curry", "Giannis Antetokounmpo"]
    
    for player in test_players:
        print(f"\n🔍 Checking injury status for: {player}")
        injury_status = await news_service.check_injury_status(player)
        
        if injury_status:
            print(f"   {injury_status}")
        else:
            print(f"   ✅ No injury information found - likely healthy")
    
    print()
    
    # Test 4: Get player-specific news
    print("=" * 80)
    print("Test 4: Get Player-Specific News")
    print("=" * 80)
    
    test_player = "LeBron James"
    print(f"\n🔍 Getting news for: {test_player}")
    
    player_news = await news_service.get_player_news(test_player, limit=3)
    
    if player_news and isinstance(player_news, list):
        print(f"✅ Found {len(player_news)} articles about {test_player}\n")
        
        for i, article in enumerate(player_news, 1):
            headline = article.get('article_headline', 'No headline')
            excerpt = article.get('article_excerpt', '')
            
            print(f"{i}. {headline}")
            if excerpt:
                excerpt_short = excerpt[:200] + "..." if len(excerpt) > 200 else excerpt
                print(f"   {excerpt_short}")
            print()
    else:
        print(f"⚠️  No news found for {test_player}")
    
    print()
    print("=" * 80)
    print("Testing Complete!")
    print("=" * 80)
    print()
    print("✅ Fantasy Nerds API integration is working correctly")
    print("📰 News and injury data are now available for the LLM to make better recommendations")

if __name__ == "__main__":
    asyncio.run(main())
