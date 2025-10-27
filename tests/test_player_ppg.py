import pytest
#!/usr/bin/env python3
"""Test player PPG fetching"""

import asyncio
import sys
sys.path.insert(0, '/Users/aman.buddaraju/fantasy-basketball-league')

from backend.services.nba_stats_service import NBAStatsService

@pytest.mark.asyncio
async def test_player_ppg():
    """Test fetching player stats"""
    
    service = NBAStatsService()
    
    # Test with a few well-known players (using their Sleeper IDs)
    test_players = [
        ("1272", "Anthony Davis"),
        ("1308", "Kawhi Leonard"),
        ("1054", "Kyrie Irving"),
        ("1434", "Russell Westbrook")
    ]
    
    for player_id, player_name in test_players:
        print(f"\n{'='*60}")
        print(f"Testing: {player_name} (ID: {player_id})")
        print('='*60)
        
        try:
            # Fetch career stats
            career_stats = await service.fetch_player_career_stats(int(player_id))
            
            if not career_stats:
                print(f"❌ No career stats found")
                continue
            
            print(f"✅ Career stats found!")
            
            # Look for 2025-26 and 2024-25 seasons
            regular_season = career_stats.get("regular_season", [])
            
            current_season = None
            last_season = None
            
            for season_stats in regular_season:
                season_id = season_stats.get("SEASON_ID", "")
                gp = season_stats.get("GP", 0)
                pts = season_stats.get("PTS", 0)
                reb = season_stats.get("REB", 0)
                ast = season_stats.get("AST", 0)
                
                if "2025-26" in season_id:
                    current_season = season_stats
                    print(f"  2025-26: {gp} GP, {pts:.1f} PTS, {reb:.1f} REB, {ast:.1f} AST")
                elif "2024-25" in season_id:
                    last_season = season_stats
                    print(f"  2024-25: {gp} GP, {pts:.1f} PTS, {reb:.1f} REB, {ast:.1f} AST")
            
            # Calculate fantasy PPG
            selected = current_season if current_season and current_season.get("GP", 0) >= 25 else last_season
            
            if selected:
                pts = selected.get("PTS", 0.0)
                reb = selected.get("REB", 0.0)
                ast = selected.get("AST", 0.0)
                stl = selected.get("STL", 0.0)
                blk = selected.get("BLK", 0.0)
                tov = selected.get("TOV", 0.0)
                
                fantasy_ppg = pts + (1.2 * reb) + (1.5 * ast) + (3 * stl) + (3 * blk) - tov
                
                season_used = "current" if selected == current_season else "last"
                print(f"\n  📊 Fantasy PPG: {fantasy_ppg:.2f} (using {season_used} season)")
            else:
                print(f"\n  ⚠️  No usable season data")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_player_ppg())
