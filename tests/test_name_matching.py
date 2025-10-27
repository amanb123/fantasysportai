import pytest
#!/usr/bin/env python3
"""Test name-based NBA ID matching and PPG calculation"""

import asyncio
import sys
sys.path.insert(0, '/Users/aman.buddaraju/fantasy-basketball-league')

from backend.services.sleeper_service import SleeperService
from backend.services.nba_stats_service import NBAStatsService

@pytest.mark.asyncio
async def test_name_matching():
    """Test using name-based NBA ID matching"""
    
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
        
        # Try name-based matching
        nba_person_id = nba_stats.match_sleeper_to_nba_id(player)
        
        if not nba_person_id:
            print(f"  ❌ Could not match to NBA ID")
            continue
        
        print(f"  ✅ Matched to NBA ID: {nba_person_id}")
        
        # Fetch career stats
        try:
            career_stats = await nba_stats.fetch_player_career_stats(nba_person_id)
            
            if not career_stats or not career_stats.get("regular_season"):
                print(f"  ❌ No career stats found")
                continue
            
            print(f"  ✅ Career stats found!")
            
            # Look for current and last season
            regular_season = career_stats["regular_season"]
            
            current_season_stats = None
            last_season_stats = None
            
            for season_stats in regular_season:
                season_id = season_stats.get("SEASON_ID", "")
                gp = season_stats.get("GP", 0)
                pts = season_stats.get("PTS", 0)
                reb = season_stats.get("REB", 0)
                ast = season_stats.get("AST", 0)
                stl = season_stats.get("STL", 0)
                blk = season_stats.get("BLK", 0)
                tov = season_stats.get("TOV", 0)
                
                fantasy_ppg = pts + (1.2 * reb) + (1.5 * ast) + (3 * stl) + (3 * blk) - tov
                
                if "2025-26" in season_id:
                    current_season_stats = season_stats
                    print(f"  📊 2025-26: {gp} GP, Fantasy PPG: {fantasy_ppg:.2f}")
                elif "2024-25" in season_id:
                    last_season_stats = season_stats
                    print(f"  📊 2024-25: {gp} GP, Fantasy PPG: {fantasy_ppg:.2f}")
            
            # Determine which season to use
            selected = None
            season_used = None
            
            if current_season_stats and current_season_stats.get("GP", 0) >= 25:
                selected = current_season_stats
                season_used = "current (2025-26)"
            elif last_season_stats:
                selected = last_season_stats
                season_used = "last (2024-25)"
            
            if selected:
                pts = selected.get("PTS", 0)
                reb = selected.get("REB", 0)
                ast = selected.get("AST", 0)
                stl = selected.get("STL", 0)
                blk = selected.get("BLK", 0)
                tov = selected.get("TOV", 0)
                
                fantasy_ppg = pts + (1.2 * reb) + (1.5 * ast) + (3 * stl) + (3 * blk) - tov
                
                print(f"\n  ✅ USING {season_used}: {fantasy_ppg:.2f} fantasy PPG")
            else:
                print(f"\n  ⚠️  No suitable season data, would use default 25.0 PPG")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_name_matching())
