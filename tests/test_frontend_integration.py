#!/usr/bin/env python3
"""
Frontend Integration Test Script
Tests the Roster Chat frontend integration
"""

import sys
import os

print("=" * 80)
print("ROSTER CHAT FRONTEND INTEGRATION TEST")
print("=" * 80)
print()

# Test 1: Check if RosterChat component exists
print("Test 1: Checking RosterChat component...")
chat_component_path = "frontend/src/components/RosterChat.jsx"
if os.path.exists(chat_component_path):
    print(f"✓ {chat_component_path} exists")
    with open(chat_component_path, 'r') as f:
        content = f.read()
        if 'const RosterChat' in content:
            print("✓ RosterChat component is defined")
        if 'startRosterChat' in content:
            print("✓ Uses startRosterChat API function")
        if 'createChatWebSocketConnection' in content:
            print("✓ Uses WebSocket connection")
else:
    print(f"✗ {chat_component_path} not found")

print()

# Test 2: Check if routes are configured
print("Test 2: Checking App.jsx routes...")
app_path = "frontend/src/App.jsx"
if os.path.exists(app_path):
    with open(app_path, 'r') as f:
        content = f.read()
        if "import RosterChat from './components/RosterChat.jsx'" in content:
            print("✓ RosterChat is imported in App.jsx")
        if 'path="/roster/chat"' in content:
            print("✓ Route /roster/chat is defined")
        if 'path="/roster/chat/:sessionId"' in content:
            print("✓ Route /roster/chat/:sessionId is defined")
        if '<RosterChat />' in content:
            print("✓ RosterChat component is used in routes")
else:
    print(f"✗ {app_path} not found")

print()

# Test 3: Check if RosterDisplay navigation is updated
print("Test 3: Checking RosterDisplay navigation...")
roster_display_path = "frontend/src/components/RosterDisplay.jsx"
if os.path.exists(roster_display_path):
    with open(roster_display_path, 'r') as f:
        content = f.read()
        if "navigate('/roster/chat')" in content:
            print("✓ Navigation to /roster/chat is configured")
        if 'handleRosterAssistant' in content:
            print("✓ handleRosterAssistant handler exists")
        if 'onClick={handleRosterAssistant}' in content:
            print("✓ Button uses handleRosterAssistant handler")
        if 'import RosterAssistant' in content:
            print("⚠ WARNING: Old RosterAssistant import still present")
        if 'showRosterAssistant' in content:
            print("⚠ WARNING: showRosterAssistant state still present")
else:
    print(f"✗ {roster_display_path} not found")

print()

# Test 4: Check API functions
print("Test 4: Checking API service functions...")
api_path = "frontend/src/services/api.js"
if os.path.exists(api_path):
    with open(api_path, 'r') as f:
        content = f.read()
        functions = [
            'startRosterChat',
            'sendChatMessage',
            'getChatHistory',
            'getUserChatSessions',
            'archiveChatSession'
        ]
        for func in functions:
            if f'export const {func}' in content or f'export async function {func}' in content:
                print(f"✓ {func} function is exported")
            else:
                print(f"✗ {func} function not found")
else:
    print(f"✗ {api_path} not found")

print()

# Test 5: Check WebSocket service
print("Test 5: Checking WebSocket service...")
ws_path = "frontend/src/services/websocket.js"
if os.path.exists(ws_path):
    with open(ws_path, 'r') as f:
        content = f.read()
        if 'createChatWebSocketConnection' in content:
            print("✓ createChatWebSocketConnection function exists")
        if 'chat_message' in content:
            print("✓ Handles 'chat_message' event")
        if 'chatSessionId' in content:
            print("✓ Supports chatSessionId parameter")
else:
    print(f"✗ {ws_path} not found")

print()

# Test 6: Check backend endpoints
print("Test 6: Checking backend endpoints...")
main_path = "backend/main.py"
if os.path.exists(main_path):
    with open(main_path, 'r') as f:
        content = f.read()
        endpoints = [
            ('/api/roster-chat/start', 'start_roster_chat'),
            ('/api/roster-chat/{session_id}/message', 'send_chat_message'),
            ('/api/roster-chat/{session_id}/history', 'get_chat_history'),
            ('/api/roster-chat/sessions', 'get_user_chat_sessions'),
            ('/ws/roster-chat/{session_id}', 'roster_chat_websocket')
        ]
        for path, func_name in endpoints:
            if path in content:
                print(f"✓ Endpoint {path} is defined")
            else:
                print(f"✗ Endpoint {path} not found")
else:
    print(f"✗ {main_path} not found")

print()

# Test 7: Detailed error analysis
print("Test 7: Analyzing potential error sources...")
print()

print("Common issues that cause 'Not Found' errors:")
print("1. Backend not running on port 3002")
print("2. Frontend API base URL misconfigured")
print("3. CORS issues between frontend and backend")
print("4. Route mismatch between frontend and backend")
print("5. Missing Sleeper session data")
print()

# Check API base URL configuration
print("Checking API configuration...")
if os.path.exists(api_path):
    with open(api_path, 'r') as f:
        content = f.read()
        if 'localhost:3002' in content or 'API_URL' in content or 'BASE_URL' in content:
            print("✓ API base URL is configured")
            # Extract base URL
            for line in content.split('\n'):
                if 'const' in line and ('API_URL' in line or 'BASE_URL' in line or 'localhost' in line):
                    print(f"  Found: {line.strip()}")
        else:
            print("⚠ WARNING: Could not find API base URL configuration")

print()

# Test 8: Check for error handling
print("Test 8: Checking error handling in RosterChat...")
if os.path.exists(chat_component_path):
    with open(chat_component_path, 'r') as f:
        content = f.read()
        if 'catch' in content:
            print("✓ Has error handling (try/catch blocks)")
        if 'setError' in content:
            print("✓ Has error state management")
        if '<ErrorMessage' in content:
            print("✓ Displays ErrorMessage component")
        if 'console.error' in content:
            print("✓ Logs errors to console")

print()
print("=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print()
print("To diagnose the 'Not Found' error:")
print()
print("1. Check browser console (F12) for detailed error messages")
print("2. Verify backend is running: curl http://localhost:3002/health")
print("3. Check frontend API calls in Network tab")
print("4. Verify you're logged in to Sleeper and have selected a league")
print("5. Check that userRoster exists in SleeperContext")
print()
print("Quick debugging steps:")
print("  • Open browser DevTools (F12)")
print("  • Go to Console tab")
print("  • Click 'Roster Assistant' button")
print("  • Look for the actual error message")
print("  • Check Network tab for failed API calls")
print()
print("If you see a 404 error on /api/roster-chat/start:")
print("  • Backend may not be running")
print("  • Endpoint may not be properly registered")
print("  • CORS may be blocking the request")
print()
print("If error says 'Missing required data':")
print("  • Check that selectedLeague exists")
print("  • Check that userRoster exists")
print("  • Navigate to /roster first, then click Roster Assistant")
print()
