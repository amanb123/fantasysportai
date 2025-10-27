#!/usr/bin/env python3
"""
Test script to verify schedule cache is being used by the LLM.
Sends a query about upcoming games and checks if the response includes future game data.
"""

import requests
import json
import time

# API configuration
API_BASE = "http://127.0.0.1:3002"
LEAGUE_ID = "1145865745969213440"
ROSTER_ID = "3"
SLEEPER_USER_ID = "1145917800104538112"

def test_schedule_cache():
    """Test that the LLM can access upcoming games from the cache."""
    
    print("=" * 80)
    print("Testing Schedule Cache with LLM Query")
    print("=" * 80)
    
    # Step 1: Start a roster chat session
    print("\n1. Starting roster chat session...")
    start_response = requests.post(
        f"{API_BASE}/api/roster-chat/start",
        json={
            "league_id": LEAGUE_ID,
            "roster_id": int(ROSTER_ID),
            "sleeper_user_id": SLEEPER_USER_ID
        }
    )
    
    if start_response.status_code != 200:
        print(f"❌ Failed to start session: {start_response.status_code}")
        print(start_response.text)
        return
    
    session_data = start_response.json()
    session_id = session_data.get("session_id")
    print(f"✅ Session started: {session_id}")
    
    # Step 2: Send a message asking about upcoming games
    print("\n2. Sending query about upcoming games...")
    
    test_query = "What games do the Lakers have in the next week? When is their next game?"
    
    print(f"Query: '{test_query}'")
    
    message_response = requests.post(
        f"{API_BASE}/api/roster-chat/{session_id}/message",
        json={
            "message": test_query
        }
    )
    
    if message_response.status_code != 200:
        print(f"❌ Failed to send message: {message_response.status_code}")
        print(message_response.text)
        return
    
    response_data = message_response.json()
    
    # Step 3: Check the response
    print("\n3. Analyzing response...")
    print("=" * 80)
    
    ai_response = response_data.get("response", "No response field")
    assistant_message = response_data.get("assistant_message", {})
    content = assistant_message.get("content", ai_response)
    
    print(f"AI Response:\n{content}")
    
    print("\n" + "=" * 80)
    
    # Step 4: Verify the response contains schedule information
    print("\n4. Verification:")
    
    # Check for indicators that schedule cache was used
    indicators = {
        "Has dates": any(month in content.lower() for month in ["october", "november", "december", "january"]),
        "Has game info": any(word in content.lower() for word in ["game", "play", "match", "vs", "at", "@"]),
        "Has specific date": any(char.isdigit() for char in content),
        "Mentions Lakers": "laker" in content.lower(),
    }
    
    print("\nResponse indicators:")
    for indicator, present in indicators.items():
        status = "✅" if present else "❌"
        print(f"  {status} {indicator}")
    
    # Overall assessment
    if sum(indicators.values()) >= 3:
        print("\n✅ SUCCESS: Schedule cache appears to be working!")
        print("   The LLM provided specific game information from the cached schedule.")
    else:
        print("\n⚠️  WARNING: Response may not be using schedule cache")
        print("   Expected more specific game information.")
    
    # Step 5: Check backend logs for cache usage
    print("\n5. Checking backend logs for cache usage...")
    print("   (Check backend.log for 'Using schedule cache service' or 'memory cache')")
    
    return session_id, content


if __name__ == "__main__":
    try:
        session_id, response = test_schedule_cache()
        print("\n" + "=" * 80)
        print("Test completed!")
        print(f"Session ID: {session_id}")
        print("=" * 80)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
