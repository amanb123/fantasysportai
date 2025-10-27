import React, { createContext, useContext, useReducer, useEffect, useCallback, useMemo } from 'react'
import { 
  getSleeperSession, 
  setSleeperSession, 
  removeSleeperSession,
  startSleeperSession,
  getSleeperLeagues,
  getSleeperRostersCached
} from '../services/api'
import { createLeagueWebSocketConnection } from '../services/websocket'

// Initial state
const initialState = {
  sleeperSession: null,
  selectedLeague: null,
  userRoster: null,
  leagueWebSocket: null,
  loading: false,
  error: null
}

// Action types
const SLEEPER_ACTIONS = {
  SET_LOADING: 'SET_LOADING',
  SET_ERROR: 'SET_ERROR',
  SET_SESSION: 'SET_SESSION',
  SET_SELECTED_LEAGUE: 'SET_SELECTED_LEAGUE',
  SET_USER_ROSTER: 'SET_USER_ROSTER',
  SET_LEAGUE_WEBSOCKET: 'SET_LEAGUE_WEBSOCKET',
  CLEAR_SESSION: 'CLEAR_SESSION',
  CLEAR_ERROR: 'CLEAR_ERROR'
}

// Reducer
const sleeperReducer = (state, action) => {
  switch (action.type) {
    case SLEEPER_ACTIONS.SET_LOADING:
      return { ...state, loading: action.payload, error: null }
    
    case SLEEPER_ACTIONS.SET_ERROR:
      return { ...state, error: action.payload, loading: false }
    
    case SLEEPER_ACTIONS.SET_SESSION:
      return { ...state, sleeperSession: action.payload, error: null }
    
    case SLEEPER_ACTIONS.SET_SELECTED_LEAGUE:
      return { ...state, selectedLeague: action.payload }
    
    case SLEEPER_ACTIONS.SET_USER_ROSTER:
      return { ...state, userRoster: action.payload }
    
    case SLEEPER_ACTIONS.SET_LEAGUE_WEBSOCKET:
      return { ...state, leagueWebSocket: action.payload }
    
    case SLEEPER_ACTIONS.CLEAR_SESSION:
      return { 
        ...initialState,
        loading: false 
      }
    
    case SLEEPER_ACTIONS.CLEAR_ERROR:
      return { ...state, error: null }
    
    default:
      return state
  }
}

// Create context
const SleeperContext = createContext(null)

// Provider component
const SleeperProvider = ({ children }) => {
  const [state, dispatch] = useReducer(sleeperReducer, initialState)

  // Load existing session on mount
  useEffect(() => {
    const existingSession = getSleeperSession()
    if (existingSession) {
      dispatch({ type: SLEEPER_ACTIONS.SET_SESSION, payload: existingSession })
    }
  }, [])

  // Start session by validating Sleeper username
  const startSession = useCallback(async (username) => {
    dispatch({ type: SLEEPER_ACTIONS.SET_LOADING, payload: true })
    
    try {
      const sessionData = await startSleeperSession(username)
      dispatch({ type: SLEEPER_ACTIONS.SET_SESSION, payload: sessionData })
      return sessionData
    } catch (error) {
      dispatch({ type: SLEEPER_ACTIONS.SET_ERROR, payload: error.message })
      throw error
    } finally {
      dispatch({ type: SLEEPER_ACTIONS.SET_LOADING, payload: false })
    }
  }, [])

  // Fetch leagues for current user
  const fetchLeagues = useCallback(async () => {
    if (!state.sleeperSession) {
      throw new Error('No Sleeper session found')
    }
    
    try {
      const leagues = await getSleeperLeagues(state.sleeperSession.user_id)
      return leagues
    } catch (error) {
      dispatch({ type: SLEEPER_ACTIONS.SET_ERROR, payload: error.message })
      throw error
    }
  }, [state.sleeperSession]) // Depend on entire session object

  // Fetch rosters and filter to user's roster
  const fetchRosters = useCallback(async (leagueId) => {
    if (!state.sleeperSession) {
      throw new Error('No Sleeper session found')
    }

    try {
      const rosters = await getSleeperRostersCached(leagueId, false)
      
      // Filter to find user's roster
      const userRoster = rosters.find(roster => 
        roster.owner_id === state.sleeperSession.user_id
      )
      
      dispatch({ type: SLEEPER_ACTIONS.SET_USER_ROSTER, payload: userRoster })
      
      return userRoster
    } catch (error) {
      dispatch({ type: SLEEPER_ACTIONS.SET_ERROR, payload: error.message })
      throw error
    }
  }, [state.sleeperSession]) // Depend on entire session object

  // Select a league and prepare for roster display
  const selectLeague = useCallback(async (league) => {
    dispatch({ type: SLEEPER_ACTIONS.SET_LOADING, payload: true })
    
    try {
      // Set selected league
      dispatch({ type: SLEEPER_ACTIONS.SET_SELECTED_LEAGUE, payload: league })
      
      // Fetch rosters for the league
      await fetchRosters(league.league_id)
      
      // Connect to league WebSocket for real-time updates
      connectToLeagueUpdates(league.league_id)
      
    } catch (error) {
      dispatch({ type: SLEEPER_ACTIONS.SET_ERROR, payload: error.message })
      throw error
    } finally {
      dispatch({ type: SLEEPER_ACTIONS.SET_LOADING, payload: false })
    }
  }, [fetchRosters])

  // Connect to league WebSocket for real-time updates
  const connectToLeagueUpdates = useCallback((leagueId) => {
    try {
      console.log('Connecting to league WebSocket:', leagueId)
      
      const ws = createLeagueWebSocketConnection(leagueId, {
        onConnect: () => {
          console.log('League WebSocket connected')
        },
        onRosterUpdate: (message) => {
          console.log('Roster update received:', message)
          handleRosterUpdate(message)
        },
        onError: (error) => {
          console.error('League WebSocket error:', error)
        },
        onDisconnect: () => {
          console.log('League WebSocket disconnected')
        }
      })
      
      ws.connect()
      dispatch({ type: SLEEPER_ACTIONS.SET_LEAGUE_WEBSOCKET, payload: ws })
      
    } catch (error) {
      console.error('Failed to connect to league WebSocket:', error)
    }
  }, [])

  // Handle roster update from WebSocket
  const handleRosterUpdate = useCallback((message) => {
    const { league_id, update_type, data } = message
    
    console.log(`Roster update for league ${league_id}, type: ${update_type}`)
    
    // Skip refresh if this update came from a manual refresh we just did
    if (data?.refreshed) {
      console.log('Skipping fetch - data already refreshed')
      return
    }
    
    // Refresh roster data if it's a roster change
    if (update_type === 'roster_change' && state.selectedLeague?.league_id === league_id) {
      console.log('Refreshing roster data...')
      fetchRosters(league_id).catch(error => {
        console.error('Failed to refresh roster:', error)
      })
    }
  }, [state.selectedLeague, fetchRosters])

  // Disconnect from league WebSocket
  const disconnectFromLeagueUpdates = useCallback(() => {
    if (state.leagueWebSocket) {
      console.log('Disconnecting from league WebSocket')
      state.leagueWebSocket.disconnect()
      dispatch({ type: SLEEPER_ACTIONS.SET_LEAGUE_WEBSOCKET, payload: null })
    }
  }, [state.leagueWebSocket])

  // Clear session and all related data
  const clearSession = useCallback(() => {
    disconnectFromLeagueUpdates()
    removeSleeperSession()
    dispatch({ type: SLEEPER_ACTIONS.CLEAR_SESSION })
  }, [disconnectFromLeagueUpdates])

  // Clear error
  const clearError = useCallback(() => {
    dispatch({ type: SLEEPER_ACTIONS.CLEAR_ERROR })
  }, [])

  // Cleanup effect - disconnect WebSocket on unmount
  useEffect(() => {
    return () => {
      if (state.leagueWebSocket) {
        console.log('Cleaning up league WebSocket on unmount')
        state.leagueWebSocket.disconnect()
      }
    }
  }, [])

  // Context value - memoized to prevent unnecessary re-renders
  const value = useMemo(() => ({
    // State
    sleeperSession: state.sleeperSession,
    selectedLeague: state.selectedLeague,
    userRoster: state.userRoster,
    leagueWebSocket: state.leagueWebSocket,
    loading: state.loading,
    error: state.error,
    
    // Actions
    startSession,
    selectLeague,
    clearSession,
    fetchLeagues,
    fetchRosters,
    clearError,
    connectToLeagueUpdates,
    disconnectFromLeagueUpdates
  }), [
    state.sleeperSession,
    state.selectedLeague,
    state.userRoster,
    state.leagueWebSocket,
    state.loading,
    state.error,
    startSession,
    selectLeague,
    clearSession,
    fetchLeagues,
    fetchRosters,
    clearError,
    connectToLeagueUpdates,
    disconnectFromLeagueUpdates
  ])

  return (
    <SleeperContext.Provider value={value}>
      {children}
    </SleeperContext.Provider>
  )
}

// Custom hook to use Sleeper context
const useSleeper = () => {
  const context = useContext(SleeperContext)
  
  if (!context) {
    throw new Error('useSleeper must be used within a SleeperProvider')
  }
  
  return context
}

export { SleeperProvider, useSleeper }