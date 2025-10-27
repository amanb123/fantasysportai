# Trade Assistant Testing Guide

## Test Date: October 21, 2025

## Services Status
- ✅ Backend: Running on http://localhost:3002
- ✅ Frontend: Running on http://localhost:3001
- ✅ Database: Connected
- ✅ Hot Module Reload: Active

## Testing Checklist

### Phase 1: UI/UX Flow Testing

#### Step 1: Team Selection (NEW)
- [ ] Navigate to Trade Assistant from Roster Display
- [ ] Verify "Who are you looking to trade with?" heading displays
- [ ] Verify all opponent teams are listed (excluding user's team)
- [ ] Test team selection:
  - [ ] Click on a team card - should highlight with blue border
  - [ ] Click same team again - should deselect
  - [ ] Select multiple teams - all should highlight
  - [ ] Verify player count shows for each team
- [ ] Test "Continue to Player Selection" button:
  - [ ] Should be disabled when no teams selected
  - [ ] Should be enabled when at least one team selected
  - [ ] Click to proceed to next step

**Expected Behavior:**
- Team cards should toggle selection state with visual feedback
- Button should only activate after team selection
- Smooth transition to player selection

#### Step 2: Player Selection (UPDATED)
- [ ] Verify "Players You're Trading Away" section:
  - [ ] User's roster should be pre-populated
  - [ ] All user's players should be clickable
  - [ ] Selected players should show red highlight and checkmark
  - [ ] Selection count should update dynamically
  - [ ] Should be scrollable if many players
- [ ] Verify "Players You're Receiving" section:
  - [ ] Opponent teams' players should be pre-populated
  - [ ] If multiple teams selected, should show sections per team
  - [ ] Selected players should show green highlight and checkmark
  - [ ] Selection count should update dynamically
  - [ ] Should be scrollable if many players
- [ ] Test player selection:
  - [ ] Click players in both sections
  - [ ] Verify toggle behavior (select/deselect)
  - [ ] Verify visual feedback (border color, checkmark)
- [ ] Test "Back to Teams" button:
  - [ ] Should return to team selection
  - [ ] Previously selected teams should remain selected
- [ ] Test "Analyze Trade" button:
  - [ ] Should be disabled if no players selected in either section
  - [ ] Should be enabled when at least 1 player selected in each section
  - [ ] Click to start analysis

**Expected Behavior:**
- User roster pre-loaded in "Trading Away"
- Opponent rosters pre-loaded in "Receiving"
- Smooth toggle selection with visual feedback
- Player names should display correctly (not just IDs)
- Validation prevents analysis with incomplete selections

#### Step 3: Analysis in Progress
- [ ] Verify loading animation displays
- [ ] Verify "Analyzing Your Trade..." message
- [ ] Verify progress description shows
- [ ] Verify polling happens in background (check network tab)
- [ ] Time the analysis (should complete in 10-15 seconds)

**Expected Behavior:**
- Professional loading state
- No errors in console
- Backend processes in background
- UI remains responsive

#### Step 4: Results Display
- [ ] Verify Favorability Score:
  - [ ] Large number displays (0-100 or N/A)
  - [ ] Color coding matches score:
    - Green (70-100): Strongly Favorable / Favorable
    - Yellow (46-69): Fair Trade
    - Orange (31-45): Unfavorable
    - Red (0-30): Strongly Unfavorable
  - [ ] Label displays under score
- [ ] Verify Recommendation section:
  - [ ] Yellow alert box displays
  - [ ] Lightbulb emoji shows
  - [ ] Recommendation text displays (Accept/Reject/Consider)
- [ ] Verify Analysis Reasoning:
  - [ ] Blue box displays
  - [ ] Detailed reasoning text shows
- [ ] Verify Pros section:
  - [ ] Green box displays
  - [ ] Count shows in header
  - [ ] Bullet points list pros
  - [ ] Checkmark emoji shows
- [ ] Verify Cons section:
  - [ ] Red box displays
  - [ ] Count shows in header
  - [ ] Bullet points list cons
  - [ ] X emoji shows
- [ ] Test "Analyze Another Trade" button:
  - [ ] Should return to team selection (Step 1)
  - [ ] Should clear previous selections
  - [ ] Should reload analysis history
- [ ] Test "Save/Print" button:
  - [ ] Should trigger browser print dialog

**Expected Behavior:**
- All sections render correctly
- No "undefined" or null values displayed
- Colors match favorability
- Actions work as expected

### Phase 2: Data Validation Testing

#### Backend API Tests
- [ ] Test roster fetching:
  ```bash
  curl -s "http://localhost:3002/api/sleeper/leagues/{league_id}/rosters/cached" | jq '.[] | {roster_id, owner_id, players: (.players | length)}'
  ```
- [ ] Test recent trades:
  ```bash
  curl -s "http://localhost:3002/api/trade-assistant/recent-trades/{league_id}?limit=5" | jq
  ```
- [ ] Test analysis submission:
  ```bash
  curl -X POST http://localhost:3002/api/trade-assistant/analyze \
    -H "Content-Type: application/json" \
    -d '{
      "league_id": "YOUR_LEAGUE_ID",
      "sleeper_user_id": "YOUR_USER_ID",
      "user_roster_id": 1,
      "opponent_roster_id": 2,
      "user_players_out": ["1054"],
      "user_players_in": ["1308"]
    }'
  ```

#### Frontend State Management
- [ ] Open browser DevTools
- [ ] Navigate through all steps
- [ ] Verify no console errors
- [ ] Check Network tab for API calls:
  - [ ] GET /rosters/cached (on mount)
  - [ ] GET /recent-trades (on mount)
  - [ ] GET /sessions (on mount)
  - [ ] POST /analyze (on submit)
  - [ ] GET /analysis/{session_id} (polling every 2s)

#### Player Name Resolution
- [ ] Verify player names show (not IDs) in:
  - [ ] "Trading Away" section
  - [ ] "Receiving" section
  - [ ] Results (if shown)
- [ ] Check if player names are fetched via bulk API
- [ ] Verify loading state during player fetch

### Phase 3: Edge Case Testing

#### Team Selection Edge Cases
- [ ] Select 0 teams - button should be disabled
- [ ] Select 1 team - should work normally
- [ ] Select all teams - should work (may be slow with many players)
- [ ] Deselect all teams - button should disable again
- [ ] Navigate away and back - selections should reset

#### Player Selection Edge Cases
- [ ] Select 0 players in "Trading Away" - button disabled
- [ ] Select 0 players in "Receiving" - button disabled
- [ ] Select all players in both sections - should work
- [ ] Select 1 player each - minimum valid trade
- [ ] Rapid clicking on same player - should toggle properly
- [ ] Navigate back to team selection and forward - players should repopulate

#### Analysis Edge Cases
- [ ] Submit analysis with minimal data (1 player each)
- [ ] Submit analysis with maximum data (all players)
- [ ] Submit multiple analyses in succession
- [ ] Close browser during analysis - reopen and check status
- [ ] Network interruption during polling - should handle gracefully

#### Error Handling
- [ ] Backend down during submission - should show error
- [ ] Invalid league ID - should show error
- [ ] Empty roster - should handle gracefully
- [ ] Malformed API response - should show fallback

### Phase 4: Performance Testing

#### Load Times
- [ ] Time to load team selection: _____ seconds
- [ ] Time to fetch all rosters: _____ seconds
- [ ] Time to fetch player details: _____ seconds
- [ ] Time to analyze trade: _____ seconds
- [ ] Time to display results: _____ seconds

#### Memory Usage
- [ ] Open DevTools Performance tab
- [ ] Record during full workflow
- [ ] Check for memory leaks
- [ ] Verify proper cleanup on unmount

#### Network Efficiency
- [ ] Count total API calls for complete workflow: _____
- [ ] Verify caching works (rosters, players)
- [ ] Check payload sizes are reasonable
- [ ] Verify no redundant calls

### Phase 5: Cross-Browser Testing

- [ ] Chrome/Chromium (primary)
- [ ] Safari
- [ ] Firefox
- [ ] Edge
- [ ] Mobile Safari (responsive)
- [ ] Mobile Chrome (responsive)

### Phase 6: Integration Testing

#### Full User Journey
1. [ ] Start from roster display
2. [ ] Click "Trade Assistant" button
3. [ ] Select 2 opponent teams
4. [ ] Continue to player selection
5. [ ] Select 2 players from own roster
6. [ ] Select 2 players from opponent rosters
7. [ ] Analyze trade
8. [ ] Wait for results
9. [ ] Review all sections
10. [ ] Click "Analyze Another Trade"
11. [ ] Verify return to team selection
12. [ ] Complete another analysis
13. [ ] Verify history updates

#### Multi-Team Trade Test
1. [ ] Select 3+ opponent teams
2. [ ] Verify all teams' players show in "Receiving"
3. [ ] Select players from multiple teams
4. [ ] Submit for analysis
5. [ ] Verify backend handles correctly (may use first opponent only)

## Known Issues to Verify Fixed

### From Previous Implementation
- ✅ JSON parsing should handle LLM responses gracefully
- ✅ SQLAlchemy session binding should not cause errors
- ✅ Player IDs should resolve to names
- ✅ Background tasks should complete without hanging

### New Features to Verify
- ✅ Team selection UI works as expected
- ✅ Multi-team selection logic
- ✅ Pre-population of player lists
- ✅ Player names display correctly
- ✅ Visual feedback on selection
- ✅ Back navigation preserves state

## Test Results

### Test Environment
- **Date**: _____
- **Tester**: _____
- **Browser**: _____
- **Backend Version**: 1.0.0
- **Frontend Version**: 1.0.0

### Summary
- **Total Tests**: _____
- **Passed**: _____
- **Failed**: _____
- **Blocked**: _____
- **Issues Found**: _____

### Critical Issues
1. _____
2. _____
3. _____

### Minor Issues
1. _____
2. _____
3. _____

### Recommendations
1. _____
2. _____
3. _____

## Screenshots

### Team Selection Screen
![Team Selection](screenshots/team-selection.png)

### Player Selection Screen
![Player Selection](screenshots/player-selection.png)

### Analysis Results Screen
![Results](screenshots/results.png)

## Notes

- Frontend uses React Context for state management
- Backend uses FastAPI with background tasks
- Polling interval: 2 seconds
- Max analysis time: ~15 seconds
- Database: SQLite with SQLModel
- AI: OpenAI GPT-4

## Next Steps After Testing

1. [ ] Fix any critical bugs found
2. [ ] Address UI/UX feedback
3. [ ] Optimize performance if needed
4. [ ] Update documentation
5. [ ] Prepare for production deployment
