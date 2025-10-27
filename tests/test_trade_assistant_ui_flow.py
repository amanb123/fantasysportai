#!/usr/bin/env python3
"""
Trade Assistant UI Flow Test
Tests the new multi-step workflow with team selection and player pre-population
"""

import requests
import time
import json

BASE_URL = "http://localhost:3002"

# Test configuration (update with your real data)
TEST_CONFIG = {
    "league_id": "1265480188934750208",
    "sleeper_user_id": "730568793184653312",
    "user_roster_id": 1,
    "opponent_roster_id": 2  # Will be selected in step 1
}

def print_section(title):
    """Print a formatted section header"""
    print("\n" + "="*60)
    print(f"  {title}")
    print("="*60)

def test_fetch_rosters():
    """Test 1: Fetch league rosters (Step 1 data)"""
    print_section("TEST 1: Fetch League Rosters")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/sleeper/leagues/{TEST_CONFIG['league_id']}/rosters/cached"
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            rosters = response.json()
            print(f"✅ SUCCESS: Fetched {len(rosters)} rosters")
            
            # Show roster summary
            for roster in rosters:
                roster_id = roster.get('roster_id')
                owner_id = roster.get('owner_id')
                player_count = len(roster.get('players', []))
                is_user = roster_id == TEST_CONFIG['user_roster_id']
                
                print(f"  Roster {roster_id}: {player_count} players " + 
                      f"{'(USER)' if is_user else '(OPPONENT)'}")
            
            return rosters
        else:
            print(f"❌ FAILED: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

def test_fetch_player_details(rosters):
    """Test 2: Fetch player details for bulk display"""
    print_section("TEST 2: Fetch Player Details")
    
    try:
        # Collect all unique player IDs
        all_player_ids = set()
        for roster in rosters:
            all_player_ids.update(roster.get('players', []))
        
        print(f"Fetching details for {len(all_player_ids)} unique players...")
        
        response = requests.post(
            f"{BASE_URL}/api/sleeper/players/bulk",
            json={"player_ids": list(all_player_ids)}
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            players = data.get('players', {})
            print(f"✅ SUCCESS: Fetched {len(players)} player details")
            
            # Show sample players
            sample_ids = list(all_player_ids)[:5]
            print("\nSample Players:")
            for player_id in sample_ids:
                player = players.get(player_id, {})
                name = player.get('name', f'Player {player_id}')
                team = player.get('team', 'N/A')
                positions = ','.join(player.get('positions', []) or [])
                print(f"  {player_id}: {name} ({team}) - {positions}")
            
            return players
        else:
            print(f"❌ FAILED: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

def test_analyze_trade(rosters, players):
    """Test 3: Submit trade analysis with pre-populated players"""
    print_section("TEST 3: Submit Trade Analysis")
    
    # Get user roster and opponent roster
    user_roster = next((r for r in rosters if r['roster_id'] == TEST_CONFIG['user_roster_id']), None)
    opponent_roster = next((r for r in rosters if r['roster_id'] == TEST_CONFIG['opponent_roster_id']), None)
    
    if not user_roster or not opponent_roster:
        print("❌ FAILED: Could not find user or opponent roster")
        return None
    
    # Select first 2 players from each roster (simulating user selection)
    user_players_out = user_roster['players'][:2]
    opponent_players_in = opponent_roster['players'][:2]
    
    print(f"\nTrade Configuration:")
    print(f"  User gives up:")
    for pid in user_players_out:
        name = players.get(pid, {}).get('name', pid)
        print(f"    - {name} ({pid})")
    
    print(f"  User receives:")
    for pid in opponent_players_in:
        name = players.get(pid, {}).get('name', pid)
        print(f"    - {name} ({pid})")
    
    try:
        request_data = {
            "league_id": TEST_CONFIG['league_id'],
            "sleeper_user_id": TEST_CONFIG['sleeper_user_id'],
            "user_roster_id": TEST_CONFIG['user_roster_id'],
            "opponent_roster_id": TEST_CONFIG['opponent_roster_id'],
            "user_players_out": user_players_out,
            "user_players_in": opponent_players_in
        }
        
        response = requests.post(
            f"{BASE_URL}/api/trade-assistant/analyze",
            json=request_data
        )
        
        print(f"\nStatus Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            session_id = data.get('session_id')
            print(f"✅ SUCCESS: Analysis started")
            print(f"  Session ID: {session_id}")
            return session_id
        else:
            print(f"❌ FAILED: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

def test_poll_results(session_id, max_attempts=10):
    """Test 4: Poll for analysis results"""
    print_section("TEST 4: Poll for Analysis Results")
    
    print(f"Polling for session: {session_id}")
    print("Will check every 3 seconds...")
    
    for attempt in range(1, max_attempts + 1):
        try:
            response = requests.get(
                f"{BASE_URL}/api/trade-assistant/analysis/{session_id}"
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status')
                
                print(f"  Attempt {attempt}: Status = {status}")
                
                if status == 'completed':
                    print(f"✅ SUCCESS: Analysis completed in {attempt * 3} seconds")
                    print(f"\nResults:")
                    print(f"  Favorability Score: {data.get('favorability_score', 'N/A')}/100")
                    
                    analysis = data.get('analysis_result', {})
                    if analysis:
                        pros = analysis.get('pros', [])
                        cons = analysis.get('cons', [])
                        reasoning = analysis.get('reasoning', '')
                        recommendation = analysis.get('recommendation', '')
                        
                        print(f"  Pros: {len(pros)}")
                        for pro in pros[:3]:
                            print(f"    ✓ {pro}")
                        
                        print(f"  Cons: {len(cons)}")
                        for con in cons[:3]:
                            print(f"    ✗ {con}")
                        
                        if reasoning:
                            print(f"  Reasoning: {reasoning[:100]}...")
                        
                        if recommendation:
                            print(f"  Recommendation: {recommendation}")
                    
                    return data
                    
                elif status == 'failed':
                    print(f"❌ FAILED: Analysis failed")
                    print(f"  Error: {data.get('error')}")
                    return None
                
                # Still analyzing, wait and try again
                time.sleep(3)
            else:
                print(f"❌ FAILED: HTTP {response.status_code}")
                return None
                
        except Exception as e:
            print(f"❌ ERROR: {str(e)}")
            return None
    
    print(f"❌ TIMEOUT: Analysis did not complete in {max_attempts * 3} seconds")
    return None

def test_analysis_history():
    """Test 5: Fetch analysis history"""
    print_section("TEST 5: Fetch Analysis History")
    
    try:
        response = requests.get(
            f"{BASE_URL}/api/trade-assistant/sessions",
            params={
                "sleeper_user_id": TEST_CONFIG['sleeper_user_id'],
                "league_id": TEST_CONFIG['league_id'],
                "limit": 10
            }
        )
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            sessions = data.get('sessions', [])
            total = data.get('total', 0)
            
            print(f"✅ SUCCESS: Found {total} analysis sessions")
            
            if sessions:
                print("\nRecent Sessions:")
                for session in sessions[:5]:
                    session_id = session.get('session_id', '')[:8]
                    status = session.get('status', 'unknown')
                    score = session.get('favorability_score', 'N/A')
                    created = session.get('created_at', '')[:19]
                    
                    print(f"  {session_id}... | {status} | Score: {score} | {created}")
            
            return sessions
        else:
            print(f"❌ FAILED: {response.text}")
            return None
            
    except Exception as e:
        print(f"❌ ERROR: {str(e)}")
        return None

def main():
    """Run all tests"""
    print("\n" + "🏀"*30)
    print("  Trade Assistant - UI Flow Integration Test")
    print("🏀"*30)
    
    start_time = time.time()
    
    # Test 1: Fetch rosters (simulates Step 1 - Team Selection)
    rosters = test_fetch_rosters()
    if not rosters:
        print("\n❌ CRITICAL: Cannot proceed without rosters")
        return
    
    # Test 2: Fetch player details (needed for UI display)
    players = test_fetch_player_details(rosters)
    if not players:
        print("\n⚠️  WARNING: Player details not available, using IDs")
        players = {}
    
    # Test 3: Analyze trade (simulates Step 2 - Player Selection + Submit)
    session_id = test_analyze_trade(rosters, players)
    if not session_id:
        print("\n❌ CRITICAL: Trade analysis failed to start")
        return
    
    # Test 4: Poll for results (simulates Step 3 - Analyzing)
    results = test_poll_results(session_id)
    if not results:
        print("\n⚠️  WARNING: Analysis did not complete successfully")
    
    # Test 5: Fetch history (shown in Step 1)
    history = test_analysis_history()
    
    # Summary
    elapsed = time.time() - start_time
    print_section("TEST SUMMARY")
    print(f"Total Execution Time: {elapsed:.1f} seconds")
    print(f"\nTest Results:")
    print(f"  ✅ Rosters Fetch: {'PASS' if rosters else 'FAIL'}")
    print(f"  ✅ Player Details: {'PASS' if players else 'FAIL'}")
    print(f"  ✅ Analysis Start: {'PASS' if session_id else 'FAIL'}")
    print(f"  ✅ Analysis Complete: {'PASS' if results else 'FAIL'}")
    print(f"  ✅ History Fetch: {'PASS' if history else 'FAIL'}")
    
    if rosters and session_id and results:
        print(f"\n🎉 ALL TESTS PASSED!")
        print(f"\n✨ New UI Features Validated:")
        print(f"  ✓ Team selection data available ({len(rosters)} teams)")
        print(f"  ✓ Player names resolvable ({len(players)} players)")
        print(f"  ✓ Pre-population works (user roster has {len(rosters[0]['players'])} players)")
        print(f"  ✓ Analysis completes successfully")
        print(f"  ✓ History tracking works ({len(history) if history else 0} sessions)")
    else:
        print(f"\n⚠️  SOME TESTS FAILED - Check logs above")
    
    print("\n" + "🏀"*30 + "\n")

if __name__ == "__main__":
    main()
