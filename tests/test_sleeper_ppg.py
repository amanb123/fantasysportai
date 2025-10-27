#!/usr/bin/env python3
"""Test real player PPG with Sleeper player data"""

import asyncio
import sys
sys.path.insert(0, '/Users/aman.buddaraju/fantasy-basketball-league')

from backend.services.sleeper_service import SleeperService
from backend.services.nba_stats_service import NBAStatsService

async def test_with_sleeper_data():
    """Test using real Sleeper player data"""
    
    sleeper = SleeperService()
    nba_stats = NBAStatsService()
    
    # Get all players from Sleeper
    print("Fetching Sleeper player data...")
    all_players = await sleeper.get_all_players()
    
    # Test with players involved in the trade
    test_player_ids = ["1272", "1308", "1054", "1434"]  # AD, Kawhi, Kyrie, Westbrook
    
    for player_id in test_player_ids:
        player = all_players.get(player_id)
        if not player:
            print(f"\n❌ Player {player_id} not found in Sleeper data")
            continue
        
        full_name = player.get("full_name", "Unknown")
        print(f"\n{'='*60}")
        print(f"{full_name} (Sleeper ID: {player_id})")
        print('='*60)
        
        # Show what IDs are available
        stats_id = player.get("stats_id")
        espn_id = player.get("espn_id")
        yahoo_id = player.get("yahoo_id")
        
        print(f"  stats_id: {stats_id}")
        print(f"  espn_id: {espn_id}")
        print(f"  yahoo_id: {yahoo_id}")
        
        # Try to get NBA ID
        nba_person_id = None
        
        if stats_id:
            try:
                nba_person_id = int(stats_id)
                print(f"  ✅ Using stats_id as NBA ID: {nba_person_id}")
            except (ValueError, TypeError):
                pass
        
        if not nba_person_id and espn_id:
            try:
                nba_person_id = int(espn_id)
                print(f"  ✅ Using espn_id as NBA ID: {nba_person_id}")
            except (ValueError, TypeError):
                pass
        
        if not nba_person_id:
            print(f"  ❌ Could not extract NBA ID")
            continue
        
        # Fetch career stats
        try:
            career_stats = await nba_stats.fetch_player_career_stats(nba_person_id)
            
            if not career_stats or not career_stats.get("regular_season"):
                print(f"  ❌ No career stats found")
                continue
            
            print(f"  ✅ Career stats found!")
            
            # Look for current and last season
            regular_season = career_stats["regular_season"]
            
            for season_stats in regular_season[:3]:  # Show last 3 seasons
                season_id = season_stats.get("SEASON_ID", "")
                gp = season_stats.get("GP", 0)
                pts = season_stats.get("PTS", 0)
                reb = season_stats.get("REB", 0)
                ast = season_stats.get("AST", 0)
                stl = season_stats.get("STL", 0)
                blk = season_stats.get("BLK", 0)
                tov = season_stats.get("TOV", 0)
                
                # Calculate fantasy PPG
                fantasy_ppg = pts + (1.2 * reb) + (1.5 * ast) + (3 * stl) + (3 * blk) - tov
                
                print(f"  {season_id}: {gp} GP, Fantasy PPG: {fantasy_ppg:.2f}")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_with_sleeper_data())
