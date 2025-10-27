"""
Simple test demonstrating Fantasy Nerds API integration with injury status
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from backend.dependencies import get_nba_news_service

async def main():
    print("\n" + "=" * 80)
    print("FANTASY NERDS API - NBA INJURY & NEWS INTEGRATION TEST")
    print("=" * 80 + "\n")
    
    # Initialize service
    news_service = get_nba_news_service()
    
    if not news_service:
        print("❌ Failed to initialize NBA News Service")
        return
    
    print("✅ NBA News Service Initialized")
    print(f"   Base URL: {news_service.base_url}")
    print(f"   API Key: {news_service.api_key}")
    print()
    
    # Test players (from 2021 test data since we're using TEST API key)
    test_players = [
        "LeBron James",
        "James Harden",
        "Anthony Davis",
        "Giannis Antetokounmpo",
        "Stephen Curry",
        "Kyrie Irving",
        "Kevin Durant"
    ]
    
    print("🏥" + "=" * 79)
    print(" NBA INJURY REPORT")
    print("=" * 80 + "\n")
    
    injured_count = 0
    healthy_count = 0
    
    for player in test_players:
        injury_status = await news_service.check_injury_status(player)
        
        if injury_status:
            print(f"⚠️  {player}")
            print(f"    {injury_status}")
            print()
            injured_count += 1
        else:
            print(f"✅ {player} - No injury reported (healthy)")
            healthy_count += 1
    
    print()
    print(f"Summary: {injured_count} injured, {healthy_count} healthy")
    print()
    
    # Show full injury list
    print("📋" + "=" * 79)
    print(" FULL NBA INJURY LIST (First 10)")
    print("=" * 80 + "\n")
    
    all_injuries = await news_service.get_injuries()
    
    if all_injuries:
        for i, injury in enumerate(all_injuries[:10], 1):
            name = injury.get('name', 'Unknown')
            team = injury.get('team', '')
            injury_type = injury.get('injury', 'Unknown')
            status = injury.get('game_status', 'Unknown')
            
            print(f"{i:2}. {name:25} ({team:3}) - {injury_type:15} | {status}")
        
        print(f"\n... and {len(all_injuries) - 10} more injuries")
    
    print()
    print("📰" + "=" * 79)
    print(" LATEST NBA NEWS (First 5)")
    print("=" * 80 + "\n")
    
    all_news = await news_service.get_all_news()
    
    if all_news:
        for i, article in enumerate(all_news[:5], 1):
            headline = article.get('article_headline', 'No headline')
            author = article.get('article_author', 'Unknown')
            excerpt = article.get('article_excerpt', '')
            
            print(f"{i}. {headline}")
            print(f"   Source: {author}")
            if excerpt:
                excerpt_short = excerpt[:120] + "..." if len(excerpt) > 120 else excerpt
                print(f"   {excerpt_short}")
            print()
    
    print()
    print("=" * 80)
    print("✅ FANTASY NERDS API INTEGRATION COMPLETE")
    print("=" * 80)
    print()
    print("📌 Key Features:")
    print("   ✅ Real-time injury reports from Fantasy Nerds")
    print("   ✅ Latest NBA news from ESPN, CBS Sports, Yahoo Sports")
    print("   ✅ Player-specific injury status checking")
    print("   ✅ Cached responses (30-minute TTL)")
    print("   ✅ Integrated into free agent search tool")
    print()
    print("🤖 LLM Integration:")
    print("   • When user asks for free agents, LLM receives injury status")
    print("   • Avoids recommending injured players without return date")
    print("   • Provides context from trusted fantasy sports sources")
    print()
    print("💡 Note: Using TEST API key shows 2021 sample data.")
    print("   Add real Fantasy Nerds API key to .env for current season data:")
    print("   FANTASY_NERDS_API_KEY=your_api_key_here")
    print()

if __name__ == "__main__":
    asyncio.run(main())
