#!/usr/bin/env python3
"""Test simulation win calculation"""

import asyncio
import sys
import json
sys.path.insert(0, '/Users/aman.buddaraju/fantasy-basketball-league')

from backend.services.sleeper_service import SleeperService
from backend.services.nba_mcp_service import get_nba_mcp_service
from backend.services.nba_stats_service import NBAStatsService
from backend.services.matchup_simulation_service import MatchupSimulationService
from backend.config import settings

async def test_simulation():
    """Test simulation with real data"""
    
    # Initialize services
    sleeper = SleeperService()
    nba_mcp = get_nba_mcp_service()  # Use singleton
    nba_stats = NBAStatsService()
    
    if nba_mcp:
        await nba_mcp.initialize()
    
    simulation_service = MatchupSimulationService(
        nba_mcp_service=nba_mcp,
        sleeper_service=sleeper,
        nba_stats_service=nba_stats
    )
    
    # Test with the trade from earlier
    league_id = "1265480188934750208"
    user_roster_id = 1
    opponent_roster_id = 2  # This will be ignored, real matchups will be used
    
    # Kyrie + Westbrook -> Anthony Davis + Kawhi
    user_players_out = ["1054", "1434"]
    user_players_in = ["1272", "1308"]
    
    print("Running simulation...")
    print(f"League: {league_id}")
    print(f"User roster: {user_roster_id}")
    print(f"Trading away: {user_players_out}")
    print(f"Receiving: {user_players_in}")
    print()
    
    result = await simulation_service.simulate_next_weeks(
        league_id=league_id,
        user_roster_id=user_roster_id,
        opponent_roster_id=opponent_roster_id,
        user_players_out=user_players_out,
        user_players_in=user_players_in,
        weeks=3
    )
    
    print("=" * 60)
    print("SIMULATION RESULTS")
    print("=" * 60)
    
    for week_data in result["weeks"]:
        week_num = week_data["week"]
        opponent = week_data["opponent_team_name"]
        
        without = week_data["without_trade"]
        with_trade = week_data["with_trade"]
        
        print(f"\nWeek {week_num} vs {opponent}:")
        print(f"  Without Trade:")
        print(f"    Your points: {without['projected_points']}")
        print(f"    Opp points:  {without['opponent_projected_points']}")
        print(f"    Wins: {without['wins']} (win prob: {without['win_probability']}%)")
        print(f"  With Trade:")
        print(f"    Your points: {with_trade['projected_points']}")
        print(f"    Opp points:  {with_trade['opponent_projected_points']}")
        print(f"    Wins: {with_trade['wins']} (win prob: {with_trade['win_probability']}%)")
        print(f"  Point diff: {week_data['point_differential']:+.2f}")
    
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    summary = result["summary"]
    print(f"Total wins WITHOUT trade: {summary['total_wins_without']}")
    print(f"Total wins WITH trade:    {summary['total_wins_with']}")
    print(f"Wins improvement:         {summary['wins_improvement']:+d}")
    print(f"Weeks simulated:          {summary['weeks_simulated']}")
    
    print("\n" + "=" * 60)
    print("VERIFICATION")
    print("=" * 60)
    
    # Manual calculation
    manual_wins_without = sum(1 for w in result["weeks"] if w["without_trade"]["wins"] == 1)
    manual_wins_with = sum(1 for w in result["weeks"] if w["with_trade"]["wins"] == 1)
    
    print(f"Manual count - wins without: {manual_wins_without}")
    print(f"Manual count - wins with:    {manual_wins_with}")
    print(f"Manual count - improvement:  {manual_wins_with - manual_wins_without:+d}")
    
    if manual_wins_without != summary['total_wins_without']:
        print(f"\n❌ ERROR: Summary shows {summary['total_wins_without']} wins without, but should be {manual_wins_without}")
    if manual_wins_with != summary['total_wins_with']:
        print(f"\n❌ ERROR: Summary shows {summary['total_wins_with']} wins with, but should be {manual_wins_with}")
    
    if manual_wins_without == summary['total_wins_without'] and manual_wins_with == summary['total_wins_with']:
        print(f"\n✅ Summary calculations are CORRECT")

if __name__ == "__main__":
    asyncio.run(test_simulation())
