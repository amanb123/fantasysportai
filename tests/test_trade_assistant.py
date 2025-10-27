"""
Quick test script for Trade Assistant backend endpoints.

Run this after starting the backend server to verify all endpoints are working.
"""

import requests
import json
import time

BASE_URL = "http://localhost:3002"

def test_recent_trades():
    """Test getting recent trades"""
    print("\n1. Testing GET /api/trade-assistant/recent-trades/{league_id}")
    
    # Replace with your actual league ID
    league_id = "1265480188934750208"
    
    response = requests.get(f"{BASE_URL}/api/trade-assistant/recent-trades/{league_id}?limit=5")
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        trades = response.json()
        print(f"Found {len(trades)} recent trades")
        if trades:
            print(f"Example trade: {trades[0]}")
    else:
        print(f"Error: {response.text}")

def test_start_analysis():
    """Test starting trade analysis"""
    print("\n2. Testing POST /api/trade-assistant/analyze")
    
    # Replace with your actual data
    request_data = {
        "league_id": "1265480188934750208",
        "sleeper_user_id": "730568793184653312",
        "user_roster_id": 1,
        "opponent_roster_id": 2,
        "user_players_out": ["1054"],  # Luka Doncic
        "user_players_in": ["1308"]    # Kawhi Leonard
    }
    
    response = requests.post(
        f"{BASE_URL}/api/trade-assistant/analyze",
        json=request_data
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Session ID: {result['session_id']}")
        print(f"Status: {result['status']}")
        return result['session_id']
    else:
        print(f"Error: {response.text}")
        return None

def test_get_analysis(session_id):
    """Test getting analysis result"""
    print(f"\n3. Testing GET /api/trade-assistant/analysis/{session_id}")
    
    # Poll for result (analysis runs in background)
    max_attempts = 10
    for i in range(max_attempts):
        response = requests.get(f"{BASE_URL}/api/trade-assistant/analysis/{session_id}")
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Analysis status: {result['status']}")
            
            if result['status'] == 'completed':
                print(f"Favorability score: {result['favorability_score']}")
                if result['analysis_result']:
                    analysis = result['analysis_result']
                    print(f"Pros: {len(analysis.get('pros', []))} items")
                    print(f"Cons: {len(analysis.get('cons', []))} items")
                    print(f"Recommendation: {analysis.get('recommendation', 'N/A')}")
                return session_id
            elif result['status'] == 'failed':
                print("Analysis failed!")
                return None
            else:
                print(f"Still analyzing... (attempt {i+1}/{max_attempts})")
                time.sleep(3)
        else:
            print(f"Error: {response.text}")
            return None
    
    print("Timeout waiting for analysis")
    return None

def test_start_simulation(session_id):
    """Test starting matchup simulation"""
    print(f"\n4. Testing POST /api/trade-assistant/simulate")
    
    request_data = {
        "session_id": session_id,
        "weeks": 3
    }
    
    response = requests.post(
        f"{BASE_URL}/api/trade-assistant/simulate",
        json=request_data
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Simulation started for session: {result['session_id']}")
        return True
    else:
        print(f"Error: {response.text}")
        return False

def test_get_sessions():
    """Test getting user's analysis history"""
    print("\n5. Testing GET /api/trade-assistant/sessions")
    
    # Replace with your actual user ID
    sleeper_user_id = "730568793184653312"
    
    response = requests.get(
        f"{BASE_URL}/api/trade-assistant/sessions?sleeper_user_id={sleeper_user_id}&limit=10"
    )
    print(f"Status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print(f"Found {result['total_count']} sessions")
        if result['sessions']:
            print(f"Latest session: {result['sessions'][0]}")
    else:
        print(f"Error: {response.text}")

def main():
    """Run all tests"""
    print("=" * 60)
    print("Trade Assistant Backend Test Suite")
    print("=" * 60)
    print("\nNOTE: Update this script with your actual league_id, user_id, and player_ids")
    print("Make sure the backend server is running on http://localhost:8000\n")
    
    # Test 1: Recent trades
    test_recent_trades()
    
    # Test 2-3: Start analysis and get result
    session_id = test_start_analysis()
    if session_id:
        test_get_analysis(session_id)
        test_start_simulation(session_id)
    
    # Test 5: Get user sessions
    test_get_sessions()
    
    print("\n" + "=" * 60)
    print("Tests complete!")
    print("=" * 60)

if __name__ == "__main__":
    main()
