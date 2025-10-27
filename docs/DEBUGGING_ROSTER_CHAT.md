# Roster Chat "Not Found" Error - Debugging Guide

## Issue Description
When clicking "Roster Assistant" button, user gets error: "Something went wrong" with "Not Found" message.

## Root Cause Analysis

The error occurs when the RosterChat component tries to initialize but required Sleeper context data is missing. This can happen if:

1. **User roster not loaded** - Most common cause
2. **League not selected** - User didn't complete league selection flow
3. **Sleeper session expired** - User session timed out
4. **Backend not responding** - API endpoint returns 404

## Fixes Applied

### 1. Improved RosterChat Error Handling ✅
**File:** `frontend/src/components/RosterChat.jsx`

Added explicit checks with redirects:
- No Sleeper session → redirect to `/` (username input)
- No league selected → redirect to `/leagues`
- No user roster → redirect to `/roster`

```javascript
if (!sleeperSession) {
  console.error('No Sleeper session found')
  navigate('/')
  return
}

if (!selectedLeague) {
  console.error('No league selected')
  navigate('/leagues')
  return
}

if (!userRoster) {
  console.error('No user roster found')
  navigate('/roster')
  return
}
```

### 2. Added Roster Check in Navigation Handler ✅
**File:** `frontend/src/components/RosterDisplay.jsx`

Button now checks if roster is loaded before navigating:
```javascript
const handleRosterAssistant = () => {
  if (!userRoster) {
    console.error('Cannot start chat: user roster not loaded')
    return
  }
  navigate('/roster/chat')
}
```

## Testing Steps

### Step 1: Verify Backend is Running
```bash
# Check backend health
curl http://localhost:3002/health

# Expected response: {"status":"healthy"}
```

### Step 2: Check Frontend is Running
```bash
cd frontend
npm run dev

# Should start on http://localhost:5173
```

### Step 3: Complete Full Flow
1. **Open browser** to `http://localhost:5173`
2. **Enter Sleeper username** on home page
3. **Select a league** from the leagues list
4. **Wait for roster to load** on roster page
   - ✅ Check that you see player names (not just IDs)
   - ✅ Check browser console for any errors
5. **Click "Roster Assistant" button**
   - Should navigate to `/roster/chat`
   - Chat interface should load
   - May see initial greeting message

### Step 4: Check Browser Console
Open DevTools (F12) and check:

**Console Tab:**
- Look for error messages
- Check for failed API calls
- Verify WebSocket connection

**Network Tab:**
- Look for `POST /api/roster-chat/start`
- Check response status (should be 200)
- If 404: Backend endpoint not registered
- If 500: Server error, check backend logs

## Common Error Patterns

### Error: "Missing required data to start chat"
**Cause:** Context data not available
**Solution:** 
1. Refresh the page
2. Navigate through full flow: Home → Leagues → Roster → Chat
3. Wait for roster to fully load before clicking button

### Error: 404 on /api/roster-chat/start
**Cause:** Backend not running or endpoint not registered
**Solution:**
```bash
# Kill any existing backend
lsof -ti:3002 | xargs kill -9

# Start backend
python3 run_backend.py

# Check logs
cat backend.log
```

### Error: Network error / CORS
**Cause:** Backend and frontend URLs mismatch
**Solution:**
1. Check `frontend/src/services/api.js` for base URL
2. Verify backend is on port 3002
3. Check CORS settings in `backend/main.py`

### Error: "Chat WebSocket disconnected"
**Cause:** WebSocket endpoint not accessible
**Solution:**
1. Check backend logs for WebSocket errors
2. Verify WebSocket URL format: `ws://localhost:3002/ws/roster-chat/{session_id}`
3. Check browser console for connection errors

## Quick Diagnostic Commands

### Check if all required data is loaded
Open browser console and run:
```javascript
// In browser console on roster page
console.log('Session:', window.sleeperSession)
console.log('League:', window.selectedLeague)
console.log('Roster:', window.userRoster)
```

### Check API endpoint availability
```bash
# List all available endpoints
curl http://localhost:3002/docs

# Should see OpenAPI documentation with /api/roster-chat/* endpoints
```

### Test API manually
```bash
# Test start chat endpoint (replace with real values)
curl -X POST http://localhost:3002/api/roster-chat/start \
  -H "Content-Type: application/json" \
  -d '{
    "league_id": "YOUR_LEAGUE_ID",
    "roster_id": 1,
    "sleeper_user_id": "YOUR_USER_ID",
    "initial_message": null
  }'

# Expected: JSON with session_id
```

## Debug Mode

To enable verbose logging, add to `frontend/src/components/RosterChat.jsx`:

```javascript
// At the top of initializeChat function
console.log('=== ROSTER CHAT DEBUG ===')
console.log('Route Session ID:', routeSessionId)
console.log('Sleeper Session:', sleeperSession)
console.log('Selected League:', selectedLeague)
console.log('User Roster:', userRoster)
console.log('========================')
```

## Verification Checklist

Before testing, verify:

- [x] Backend running on port 3002
- [x] Frontend running on port 5173
- [x] Database initialized (check backend.log)
- [x] Redis running (if required)
- [ ] Logged in to Sleeper
- [ ] League selected
- [ ] Roster loaded (see player names, not IDs)
- [ ] Browser console shows no errors
- [ ] Network tab shows successful API calls

## Success Indicators

When working correctly, you should see:

1. **On Roster Page:**
   - Player names displayed (not just IDs)
   - Team abbreviations shown
   - No error messages in console

2. **After Clicking Button:**
   - URL changes to `/roster/chat`
   - Chat interface loads
   - May see "Hello! I'm your roster advisor..." message
   - Console shows "Chat WebSocket connected"

3. **In Network Tab:**
   - `POST /api/roster-chat/start` returns 200
   - Response includes `session_id`
   - WebSocket connection established

## If Still Not Working

1. **Clear browser cache and reload**
   - Cmd+Shift+R (Mac) or Ctrl+Shift+R (Windows)

2. **Check backend logs**
   ```bash
   tail -f backend.log
   ```

3. **Restart both services**
   ```bash
   # Terminal 1: Stop and restart backend
   lsof -ti:3002 | xargs kill -9
   python3 run_backend.py

   # Terminal 2: Stop and restart frontend
   cd frontend
   npm run dev
   ```

4. **Verify all dependencies installed**
   ```bash
   # Backend
   pip install -r backend/requirements.txt

   # Frontend
   cd frontend
   npm install
   ```

5. **Check for TypeScript/Build errors**
   ```bash
   cd frontend
   npm run build
   ```

## Support Information

If the issue persists:
1. Copy browser console output
2. Copy Network tab errors
3. Copy backend.log last 50 lines
4. Note the exact steps that trigger the error
5. Check which data is missing (session/league/roster)

## Related Files

- `frontend/src/components/RosterChat.jsx` - Main chat component
- `frontend/src/components/RosterDisplay.jsx` - Navigation handler
- `frontend/src/services/api.js` - API functions
- `backend/main.py` - Chat endpoints
- `backend/session/repository.py` - Chat database operations
