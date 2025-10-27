#!/usr/bin/env python3
"""
Trade Assistant Simulation Test
Tests the matchup simulation feature
"""

import requests
import time
import json

BASE_URL = "http://localhost:3002"

# Test configuration
TEST_CONFIG = {
    "league_id": "1265480188934750208",
    "sleeper_user_id": "730568793184653312",
    "user_roster_id": 1,
    "opponent_roster_id": 2,
    "user_players_out": ["1054", "1434"],  # Luka, Alex Caruso
    "user_players_in": ["1272", "1308"]    # Kawhi, Tobias Harris
}

def print_section(title):
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)

def test_full_workflow_with_simulation():
    """Complete workflow: Analyze trade → Get results → Run simulation"""
    print_section("TRADE ASSISTANT SIMULATION WORKFLOW TEST")
    
    print("\n📋 Step 1: Submit Trade Analysis")
    print(f"  League: {TEST_CONFIG['league_id']}")
    print(f"  Trading away: {TEST_CONFIG['user_players_out']}")
    print(f"  Receiving: {TEST_CONFIG['user_players_in']}")
    
    # Step 1: Start analysis
    try:
        response = requests.post(
            f"{BASE_URL}/api/trade-assistant/analyze",
            json=TEST_CONFIG
        )
        
        if response.status_code != 200:
            print(f"❌ FAILED: {response.text}")
            return
        
        data = response.json()
        session_id = data.get('session_id')
        print(f"✅ Analysis started: {session_id}")
        
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return
    
    # Step 2: Wait for analysis to complete
    print("\n⏳ Step 2: Waiting for Analysis to Complete...")
    
    max_attempts = 15
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                f"{BASE_URL}/api/trade-assistant/analysis/{session_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                print(f"  Attempt {attempt}: {status}")
                
                if status == 'completed':
                    print(f"✅ Analysis completed!")
                    print(f"  Favorability Score: {data.get('favorability_score', 'N/A')}/100")
                    analysis_result = data
                    break
                elif status == 'failed':
                    print(f"❌ Analysis failed")
                    return
                
                time.sleep(2)
            else:
                print(f"❌ HTTP {response.status_code}")
                return
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return
    else:
        print("❌ TIMEOUT: Analysis did not complete")
        return
    
    # Step 3: Run simulation
    print("\n🎮 Step 3: Running Matchup Simulation...")
    print("  Projecting next 3 weeks with/without trade...")
    
    try:
        response = requests.post(
            f"{BASE_URL}/api/trade-assistant/simulate",
            json={
                "session_id": session_id,
                "weeks_ahead": 3
            }
        )
        
        print(f"  Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Simulation started!")
            print(f"  Message: {data.get('message', 'N/A')}")
            
            # Wait a bit for background task
            print("\n⏳ Waiting for simulation to complete...")
            time.sleep(5)
            
        else:
            print(f"❌ FAILED: {response.text}")
            return
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return
    
    # Step 4: Fetch updated analysis with simulation results
    print("\n📊 Step 4: Fetching Simulation Results...")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/trade-assistant/analysis/{session_id}"
        )
        
        if response.status_code == 200:
            data = response.json()
            simulation = data.get('simulation_result')
            
            if simulation:
                print(f"✅ Simulation results retrieved!")
                print("\n" + "-"*70)
                print("  MATCHUP PROJECTION (Next 3 Weeks)")
                print("-"*70)
                
                # Without trade
                without = simulation.get('without_trade', {})
                print(f"\n  📉 WITHOUT Trade:")
                print(f"     Projected Points: {without.get('projected_points', 'N/A')}")
                print(f"     Win Probability: {without.get('win_probability', 0) * 100:.1f}%")
                
                # With trade
                with_trade = simulation.get('with_trade', {})
                print(f"\n  📈 WITH Trade:")
                print(f"     Projected Points: {with_trade.get('projected_points', 'N/A')}")
                print(f"     Win Probability: {with_trade.get('win_probability', 0) * 100:.1f}%")
                
                # Differential
                diff = simulation.get('point_differential', 0)
                print(f"\n  ⚖️  Impact:")
                print(f"     Point Differential: {'+' if diff > 0 else ''}{diff:.1f}")
                
                if diff > 0:
                    print(f"     ✅ Trade IMPROVES your projected score by {diff:.1f} points")
                elif diff < 0:
                    print(f"     ❌ Trade DECREASES your projected score by {abs(diff):.1f} points")
                else:
                    print(f"     ➖ Trade has NEUTRAL impact on projected score")
                
                print("\n" + "-"*70)
                
                # Summary
                print("\n📋 RECOMMENDATION SUMMARY:")
                print(f"  Analysis Score: {data.get('favorability_score', 'N/A')}/100")
                
                analysis = data.get('analysis_result', {})
                if analysis.get('recommendation'):
                    print(f"  AI Recommendation: {analysis['recommendation']}")
                
                if diff > 5:
                    print(f"  Simulation: STRONGLY SUPPORTS trade (+{diff:.1f} pts)")
                elif diff > 0:
                    print(f"  Simulation: SUPPORTS trade (+{diff:.1f} pts)")
                elif diff > -5:
                    print(f"  Simulation: NEUTRAL on trade ({diff:.1f} pts)")
                else:
                    print(f"  Simulation: DISCOURAGES trade ({diff:.1f} pts)")
                
                return True
            else:
                print("⚠️  No simulation results found yet")
                print("   (Background task may still be running)")
                return False
                
        else:
            print(f"❌ FAILED: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return False

def main():
    print("\n" + "🏀"*35)
    print("  Trade Assistant - Simulation Feature Test")
    print("🏀"*35)
    
    start_time = time.time()
    
    success = test_full_workflow_with_simulation()
    
    elapsed = time.time() - start_time
    
    print_section("TEST SUMMARY")
    print(f"Total Execution Time: {elapsed:.1f} seconds")
    print(f"Result: {'✅ SUCCESS' if success else '❌ FAILED'}")
    
    if success:
        print("\n🎉 Simulation feature is working correctly!")
        print("\n✨ How to use in UI:")
        print("  1. Navigate to Trade Assistant")
        print("  2. Select teams and players")
        print("  3. Wait for AI analysis")
        print("  4. Click 'Run Simulation' button")
        print("  5. View projected matchup outcomes")
        print("     - Points without trade")
        print("     - Points with trade")
        print("     - Win probability changes")
        print("     - Point differential")
    else:
        print("\n⚠️  Simulation may not be fully complete")
        print("   Try waiting a few more seconds and refreshing")
    
    print("\n" + "🏀"*35 + "\n")

if __name__ == "__main__":
    main()
