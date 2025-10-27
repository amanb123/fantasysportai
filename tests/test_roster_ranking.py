#!/usr/bin/env python3
"""
Test script for Roster Ranking functionality
Tests the backend service and API endpoints
"""

import asyncio
import sys
import requests
from datetime import datetime

# Test configuration
BASE_URL = "http://localhost:3002"
TEST_LEAGUE_ID = "1265480188934750208"

def print_header(title):
    """Print formatted header"""
    print(f"\n{'='*80}")
    print(f"{title.center(80)}")
    print(f"{'='*80}\n")

def print_success(text):
    """Print success message"""
    print(f"✅ {text}")

def print_error(text):
    """Print error message"""
    print(f"❌ {text}")

def print_info(text):
    """Print info message"""
    print(f"ℹ️  {text}")

def test_roster_ranking_endpoint():
    """Test GET /api/roster-ranking/{league_id}"""
    print_header("TEST 1: Get Roster Rankings")
    
    try:
        print_info(f"Fetching roster rankings for league {TEST_LEAGUE_ID}...")
        response = requests.get(
            f"{BASE_URL}/api/roster-ranking/{TEST_LEAGUE_ID}",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Successfully fetched roster rankings!")
            
            # Validate response structure
            assert 'league_id' in data, "Missing league_id"
            assert 'league_name' in data, "Missing league_name"
            assert 'rankings' in data, "Missing rankings"
            assert 'total_rosters' in data, "Missing total_rosters"
            assert 'scoring_settings' in data, "Missing scoring_settings"
            assert 'last_updated' in data, "Missing last_updated"
            assert 'cached' in data, "Missing cached"
            
            print_info(f"League: {data['league_name']}")
            print_info(f"Total Rosters: {data['total_rosters']}")
            print_info(f"Cached: {data['cached']}")
            print_info(f"Last Updated: {data['last_updated']}")
            
            # Display top 5 rankings
            print("\n📊 Top 5 Rankings:")
            print(f"{'Rank':<6} {'Owner Name':<25} {'Fantasy Points':<15} {'W-L':<10}")
            print("-" * 80)
            
            for ranking in data['rankings'][:5]:
                rank = ranking['rank']
                owner = ranking['owner_name'][:24]
                points = f"{ranking['total_fantasy_points']:.2f}"
                wins = ranking.get('wins', 0)
                losses = ranking.get('losses', 0)
                record = f"{wins}-{losses}"
                
                print(f"{rank:<6} {owner:<25} {points:<15} {record:<10}")
            
            # Verify category breakdowns if enabled
            if data['rankings'] and 'category_scores' in data['rankings'][0]:
                print("\n📈 Category Breakdown (Top Roster):")
                top_roster = data['rankings'][0]
                for cat, score in list(top_roster['category_scores'].items())[:5]:
                    print(f"  {cat.upper()}: {score:.2f}")
            
            return True
            
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_roster_ranking_with_refresh():
    """Test GET /api/roster-ranking/{league_id}?refresh=true"""
    print_header("TEST 2: Get Roster Rankings (Force Refresh)")
    
    try:
        print_info(f"Forcing refresh for league {TEST_LEAGUE_ID}...")
        response = requests.get(
            f"{BASE_URL}/api/roster-ranking/{TEST_LEAGUE_ID}",
            params={"refresh": True},
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Successfully fetched roster rankings with refresh!")
            
            # Should not be cached since we forced refresh
            if data.get('cached') == False:
                print_success("✓ Rankings were recalculated (not from cache)")
            else:
                print_info("⚠️  Rankings were still from cache")
            
            print_info(f"Total Rosters: {data['total_rosters']}")
            print_info(f"Last Updated: {data['last_updated']}")
            
            return True
            
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_cache_status():
    """Test GET /api/roster-ranking/{league_id}/cache-status"""
    print_header("TEST 3: Get Cache Status")
    
    try:
        print_info(f"Checking cache status for league {TEST_LEAGUE_ID}...")
        response = requests.get(
            f"{BASE_URL}/api/roster-ranking/{TEST_LEAGUE_ID}/cache-status",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Successfully fetched cache status!")
            
            # Validate response structure
            assert 'league_id' in data, "Missing league_id"
            assert 'cached' in data, "Missing cached"
            
            print_info(f"League ID: {data['league_id']}")
            print_info(f"Cached: {data['cached']}")
            
            if data.get('ttl_remaining'):
                print_info(f"TTL Remaining: {data['ttl_remaining']} seconds")
            
            if data.get('last_updated'):
                print_info(f"Last Updated: {data['last_updated']}")
            
            return True
            
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_clear_cache():
    """Test DELETE /api/roster-ranking/{league_id}/cache"""
    print_header("TEST 4: Clear Rankings Cache")
    
    try:
        print_info(f"Clearing cache for league {TEST_LEAGUE_ID}...")
        response = requests.delete(
            f"{BASE_URL}/api/roster-ranking/{TEST_LEAGUE_ID}/cache",
            timeout=10
        )
        
        if response.status_code == 200:
            data = response.json()
            print_success("Successfully cleared cache!")
            
            if data.get('success'):
                print_success(f"✓ {data.get('message', 'Cache cleared')}")
            
            return True
            
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_rankings_consistency():
    """Test that rankings are consistent and properly sorted"""
    print_header("TEST 5: Rankings Consistency Check")
    
    try:
        print_info("Fetching rankings to verify consistency...")
        response = requests.get(
            f"{BASE_URL}/api/roster-ranking/{TEST_LEAGUE_ID}",
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()
            rankings = data['rankings']
            
            # Check sorting (descending by fantasy points)
            for i in range(len(rankings) - 1):
                if rankings[i]['total_fantasy_points'] < rankings[i + 1]['total_fantasy_points']:
                    print_error(f"Rankings not properly sorted at position {i}")
                    return False
            
            print_success("✓ Rankings are properly sorted")
            
            # Check rank assignment
            for i, ranking in enumerate(rankings):
                expected_rank = i + 1
                if ranking['rank'] != expected_rank:
                    print_error(f"Rank mismatch: expected {expected_rank}, got {ranking['rank']}")
                    return False
            
            print_success("✓ Ranks are properly assigned")
            
            # Check required fields
            required_fields = ['roster_id', 'owner_id', 'owner_name', 'total_fantasy_points', 
                             'wins', 'losses', 'category_scores', 'rank']
            
            for ranking in rankings:
                for field in required_fields:
                    if field not in ranking:
                        print_error(f"Missing required field: {field}")
                        return False
            
            print_success(f"✓ All {len(rankings)} rankings have required fields")
            
            return True
            
        else:
            print_error(f"HTTP {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        print_error(f"Test failed: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print_header("🏀 ROSTER RANKING BACKEND TEST SUITE")
    
    print_info(f"Testing against: {BASE_URL}")
    print_info(f"Test League ID: {TEST_LEAGUE_ID}")
    print_info(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Check if backend is running
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Backend is running")
        else:
            print_error("Backend health check failed")
            return
    except Exception as e:
        print_error(f"Cannot connect to backend: {e}")
        print_info("Make sure the backend is running: python run_backend.py")
        return
    
    # Run tests
    results = []
    
    results.append(("Get Roster Rankings", test_roster_ranking_endpoint()))
    results.append(("Force Refresh Rankings", test_roster_ranking_with_refresh()))
    results.append(("Get Cache Status", test_cache_status()))
    results.append(("Clear Cache", test_clear_cache()))
    results.append(("Rankings Consistency", test_rankings_consistency()))
    
    # Summary
    print_header("📊 TEST SUMMARY")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {name}")
    
    print(f"\n{'='*80}")
    print(f"Results: {passed}/{total} tests passed")
    
    if passed == total:
        print_success("🎉 All tests passed!")
    else:
        print_error(f"❌ {total - passed} test(s) failed")
    
    print(f"{'='*80}\n")

if __name__ == "__main__":
    main()
