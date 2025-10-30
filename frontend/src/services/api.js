import axios from 'axios'

// Token management constants
const TOKEN_STORAGE_KEY = import.meta.env.VITE_TOKEN_STORAGE_KEY || 'fantasy_bb_token'
const REFRESH_TOKEN_STORAGE_KEY = 'fantasy_bb_refresh_token'

// Token management functions
export const getToken = () => {
  return localStorage.getItem(TOKEN_STORAGE_KEY)
}

export const setToken = (token) => {
  localStorage.setItem(TOKEN_STORAGE_KEY, token)
}

export const removeToken = () => {
  localStorage.removeItem(TOKEN_STORAGE_KEY)
}

export const getRefreshToken = () => {
  return localStorage.getItem(REFRESH_TOKEN_STORAGE_KEY)
}

export const setRefreshToken = (token) => {
  localStorage.setItem(REFRESH_TOKEN_STORAGE_KEY, token)
}

export const removeRefreshToken = () => {
  localStorage.removeItem(REFRESH_TOKEN_STORAGE_KEY)
}

export const clearAllTokens = () => {
  removeToken()
  removeRefreshToken()
}

// Sleeper session management
const SLEEPER_SESSION_KEY = 'sleeper_session'

export const getSleeperSession = () => {
  const sessionData = localStorage.getItem(SLEEPER_SESSION_KEY)
  return sessionData ? JSON.parse(sessionData) : null
}

export const setSleeperSession = (sessionData) => {
  localStorage.setItem(SLEEPER_SESSION_KEY, JSON.stringify(sessionData))
}

export const removeSleeperSession = () => {
  localStorage.removeItem(SLEEPER_SESSION_KEY)
}

// Create axios instance with default configuration
// Use longer timeout for production since roster ranking calculation can take 60-90 seconds
const isDevelopment = import.meta.env.DEV
const API_TIMEOUT = isDevelopment ? 30000 : 90000 // 30s dev, 90s prod

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:3002',
  timeout: API_TIMEOUT,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for authentication and logging
api.interceptors.request.use(
  (config) => {
    // Add authorization header if token exists (conditional for backward compatibility)
    const token = getToken()
    if (token && !config.skipAuth) {
      config.headers.Authorization = `Bearer ${token}`
    }
    
    if (import.meta.env.DEV) {
      console.log(`API Request: ${config.method?.toUpperCase()} ${config.url}`)
    }
    return config
  },
  (error) => {
    console.error('API Request Error:', error)
    return Promise.reject(error)
  }
)

// Refresh token state management
let isRefreshing = false
let refreshPromise = null
let requestQueue = []

// Refresh access token using refresh token
export const refreshAccessToken = async () => {
  const refreshToken = getRefreshToken()
  
  if (!refreshToken) {
    throw new Error('No refresh token available')
  }

  try {
    const response = await axios.post(
      `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:3002'}/api/auth/refresh`,
      { refresh_token: refreshToken },
      {
        headers: { 'Content-Type': 'application/json' },
        timeout: 10000
      }
    )

    const { access_token, refresh_token: new_refresh_token } = response.data
    
    // Update both tokens (token rotation)
    setToken(access_token)
    setRefreshToken(new_refresh_token)
    
    return access_token
  } catch (error) {
    // Refresh failed, clear tokens
    clearAllTokens()
    throw error
  }
}

// Process queued requests with new token
const processQueue = (error, token = null) => {
  requestQueue.forEach(({ resolve, reject, config }) => {
    if (error) {
      reject(error)
    } else {
      config.headers.Authorization = `Bearer ${token}`
      resolve(axios.request(config))
    }
  })
  
  requestQueue = []
}

// Response interceptor for authentication, logging and error handling
api.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      console.log(`API Response: ${response.status} ${response.config.url}`)
    }
    return response
  },
  async (error) => {
    const originalRequest = error.config

    // Handle 401 Unauthorized responses
    if (error.response?.status === 401 && !originalRequest._retry && !originalRequest.skipAuth) {
      originalRequest._retry = true

      // Check if we have a refresh token
      const refreshToken = getRefreshToken()
      if (!refreshToken) {
        clearAllTokens()
        if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
          window.location.href = '/'
        }
        return Promise.reject(error)
      }

      // If already refreshing, queue the request
      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          requestQueue.push({ resolve, reject, config: originalRequest })
        })
      }

      // Start refresh process
      isRefreshing = true

      if (!refreshPromise) {
        refreshPromise = refreshAccessToken()
      }

      try {
        const newAccessToken = await refreshPromise
        processQueue(null, newAccessToken)
        
        // Retry original request with new token
        originalRequest.headers.Authorization = `Bearer ${newAccessToken}`
        return axios.request(originalRequest)
        
      } catch (refreshError) {
        processQueue(refreshError, null)
        clearAllTokens()
        
        if (window.location.pathname !== '/' && window.location.pathname !== '/login') {
          window.location.href = '/'
        }
        return Promise.reject(refreshError)
        
      } finally {
        isRefreshing = false
        refreshPromise = null
      }
    }
    
    console.error('API Response Error:', error.response?.status, error.response?.data)
    return Promise.reject(error)
  }
)

// Helper function to extract error message
const getErrorMessage = (error) => {
  if (error.response?.data?.detail?.message) {
    return error.response.data.detail.message
  }
  if (error.response?.data?.message) {
    return error.response.data.message
  }
  if (error.response?.data?.detail) {
    return error.response.data.detail
  }
  if (error.message) {
    return error.message
  }
  return 'An unexpected error occurred'
}

/**
 * Get all teams
 * @returns {Promise<Array>} Array of TeamResponse objects
 */
export const getTeams = async () => {
  try {
    const response = await api.get('/api/teams')
    return response.data.teams || []
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get players for a specific team
 * @param {number} teamId - Team ID
 * @returns {Promise<Array>} Array of PlayerResponse objects
 */
export const getTeamPlayers = async (teamId) => {
  try {
    const response = await api.get(`/api/teams/${teamId}/players`)
    return response.data.players || []
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Start a new trade negotiation
 * @param {Object} tradePreference - TradePreferenceRequest object
 * @returns {Promise<Object>} TradeStartResponse with session_id
 */
export const startTradeNegotiation = async (tradePreference) => {
  try {
    const requestBody = {
      trade_preference: tradePreference
    }
    const response = await api.post('/api/trade/start', requestBody)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get trade negotiation status
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} TradeNegotiationStatus
 */
export const getTradeStatus = async (sessionId) => {
  try {
    const response = await api.get(`/api/trade/status/${sessionId}`)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get trade negotiation result
 * @param {string} sessionId - Session ID
 * @returns {Promise<Object>} TradeResultResponse
 */
export const getTradeResult = async (sessionId) => {
  try {
    const response = await api.get(`/api/trade/result/${sessionId}`)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Health check endpoint
 * @returns {Promise<Object>} Health status
 */
export const healthCheck = async () => {
  try {
    const response = await api.get('/health')
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Register a new user
 * @param {string} email - User email
 * @param {string} password - User password
 * @param {string} confirmPassword - Password confirmation
 * @returns {Promise<Object>} Token response
 */
export const register = async (email, password, confirmPassword) => {
  try {
    const response = await api.post('/api/auth/register', {
      email,
      password,
      confirm_password: confirmPassword
    })
    
    // Store both tokens automatically
    if (response.data.access_token) {
      setToken(response.data.access_token)
    }
    if (response.data.refresh_token) {
      setRefreshToken(response.data.refresh_token)
    }
    
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Login user
 * @param {string} email - User email
 * @param {string} password - User password
 * @returns {Promise<Object>} Token response
 */
export const login = async (email, password) => {
  try {
    // Create form data for OAuth2 compatibility
    const formData = new FormData()
    formData.append('username', email) // OAuth2 expects 'username' field
    formData.append('password', password)
    
    const response = await api.post('/api/auth/login', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    
    // Store both tokens automatically
    if (response.data.access_token) {
      setToken(response.data.access_token)
    }
    if (response.data.refresh_token) {
      setRefreshToken(response.data.refresh_token)
    }
    
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Logout user
 */
export const logout = () => {
  clearAllTokens()
  window.location.href = '/login'
}

/**
 * Get current user information
 * @returns {Promise<Object>} User response
 */
export const getCurrentUser = async () => {
  try {
    const response = await api.get('/api/auth/me')
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Link Sleeper account to current user
 * @param {string} sleeperUsername - Sleeper username
 * @returns {Promise<Object>} Updated user response
 */
export const linkSleeperAccount = async (sleeperUsername) => {
  try {
    const response = await api.post('/api/auth/link-sleeper', {
      sleeper_username: sleeperUsername
    })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// Sleeper API functions

/**
 * Start Sleeper session by validating username
 * @param {string} sleeperUsername - Sleeper username
 * @returns {Promise<Object>} Sleeper user session data
 */
export const startSleeperSession = async (sleeperUsername) => {
  try {
    const response = await api.post('/api/sleeper/session', {
      sleeper_username: sleeperUsername
    }, { skipAuth: true })
    
    // Store session data automatically
    setSleeperSession(response.data)
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get Sleeper leagues for a user
 * @param {string} userId - Sleeper user ID
 * @returns {Promise<Array>} List of leagues
 */
export const getSleeperLeagues = async (userId) => {
  try {
    const response = await api.get(`/api/sleeper/leagues?user_id=${userId}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get Sleeper rosters for a league
 * @param {string} leagueId - Sleeper league ID
 * @returns {Promise<Array>} List of rosters
 */
export const getSleeperRosters = async (leagueId) => {
  try {
    const response = await api.get(`/api/sleeper/rosters/${leagueId}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get Sleeper player details by ID
 * @param {string} playerId - Sleeper player ID
 * @returns {Promise<Object>} Player details
 */
export const getSleeperPlayer = async (playerId) => {
  try {
    const response = await api.get(`/api/sleeper/players/${playerId}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get multiple Sleeper players in bulk
 * @param {string[]} playerIds - Array of Sleeper player IDs
 * @returns {Promise<Object>} Object containing players data and cache status
 */
export const getSleeperPlayersBulk = async (playerIds) => {
  try {
    const response = await api.post('/api/sleeper/players/bulk', playerIds, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get cached rosters for a Sleeper league
 * @param {string} leagueId - Sleeper league ID
 * @param {boolean} refresh - Force refresh from API
 * @returns {Promise<Array>} Cached roster data
 */
export const getSleeperRostersCached = async (leagueId, refresh = false) => {
  try {
    const response = await api.get(`/api/sleeper/leagues/${leagueId}/rosters/cached?refresh=${refresh}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get transactions for a Sleeper league
 * @param {string} leagueId - Sleeper league ID
 * @param {number|null} round - Specific round (null = all rounds)
 * @param {boolean} refresh - Force refresh from API
 * @returns {Promise<Object>} Transaction data
 */
export const getSleeperTransactions = async (leagueId, round = null, refresh = false) => {
  try {
    const params = new URLSearchParams({ refresh: refresh.toString() })
    if (round !== null) {
      params.append('round', round)
    }
    const response = await api.get(`/api/sleeper/leagues/${leagueId}/transactions?${params}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get matchups for a Sleeper league
 * @param {string} leagueId - Sleeper league ID
 * @param {number|null} week - Specific week (null = all weeks)
 * @param {boolean} refresh - Force refresh from API
 * @returns {Promise<Object>} Matchup data
 */
export const getSleeperMatchups = async (leagueId, week = null, refresh = false) => {
  try {
    const params = new URLSearchParams({ refresh: refresh.toString() })
    if (week !== null) {
      params.append('week', week)
    }
    const response = await api.get(`/api/sleeper/leagues/${leagueId}/matchups?${params}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Refresh all league data
 * @param {string} leagueId - Sleeper league ID
 * @returns {Promise<Object>} Refresh status
 */
export const refreshLeagueData = async (leagueId) => {
  try {
    const response = await api.post(`/api/sleeper/leagues/${leagueId}/refresh`, {}, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get cache status for a league
 * @param {string} leagueId - Sleeper league ID
 * @returns {Promise<Object>} Cache status
 */
export const getLeagueCacheStatus = async (leagueId) => {
  try {
    const response = await api.get(`/api/sleeper/leagues/${leagueId}/cache-status`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// ===== Roster Chat API Functions =====

/**
 * Start a new roster chat session
 * @param {string} leagueId - Sleeper league ID
 * @param {number} rosterId - Sleeper roster ID
 * @param {string} sleeperUserId - Sleeper user ID
 * @param {string|null} initialMessage - Optional initial message
 * @returns {Promise<Object>} Session data with session_id
 */
export const startRosterChat = async (leagueId, rosterId, sleeperUserId, initialMessage = null) => {
  try {
    const response = await api.post('/api/roster-chat/start', {
      league_id: leagueId,
      roster_id: rosterId,
      sleeper_user_id: sleeperUserId,
      initial_message: initialMessage
    }, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Send a message in a roster chat session
 * @param {string} sessionId - Chat session ID
 * @param {string} message - Message content
 * @param {boolean} includeHistorical - Whether to fetch historical stats if needed
 * @returns {Promise<Object>} Assistant response
 */
export const sendChatMessage = async (sessionId, message, includeHistorical = true) => {
  try {
    const response = await api.post(`/api/roster-chat/${sessionId}/message`, {
      message,
      include_historical: includeHistorical
    }, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get chat history for a session
 * @param {string} sessionId - Chat session ID
 * @returns {Promise<Object>} Chat history with messages
 */
export const getChatHistory = async (sessionId) => {
  try {
    const response = await api.get(`/api/roster-chat/${sessionId}/history`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get user's chat sessions
 * @param {string} sleeperUserId - Sleeper user ID
 * @param {string|null} leagueId - Optional league filter
 * @returns {Promise<Object>} List of chat sessions
 */
export const getUserChatSessions = async (sleeperUserId, leagueId = null) => {
  try {
    const params = new URLSearchParams({ sleeper_user_id: sleeperUserId })
    if (leagueId) {
      params.append('league_id', leagueId)
    }
    const response = await api.get(`/api/roster-chat/sessions?${params.toString()}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Archive a chat session
 * @param {string} sessionId - Chat session ID
 * @returns {Promise<Object>} Success status
 */
export const archiveChatSession = async (sessionId) => {
  try {
    const response = await api.delete(`/api/roster-chat/${sessionId}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get users (team owners) in a Sleeper league
 * @param {string} leagueId - Sleeper league ID
 * @returns {Promise<Array>} List of league users/owners
 */
export const getSleeperLeagueUsers = async (leagueId) => {
  try {
    const response = await api.get(`/api/sleeper/leagues/${leagueId}/users`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// ==================== Trade Assistant APIs ====================

/**
 * Get recent trades in a league
 * @param {string} leagueId - Sleeper league ID
 * @param {number} limit - Maximum number of trades to return
 * @returns {Promise<Array>} List of recent trades
 */
export const getRecentTrades = async (leagueId, limit = 10) => {
  try {
    const response = await api.get(`/api/trade-assistant/recent-trades/${leagueId}?limit=${limit}`, { skipAuth: true })
    return response.data || []
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Start a new trade analysis
 * @param {Object} request - Trade analysis request
 * @param {string} request.league_id - Sleeper league ID
 * @param {string} request.sleeper_user_id - Sleeper user ID
 * @param {number} request.user_roster_id - User's roster ID
 * @param {number} request.opponent_roster_id - Opponent's roster ID
 * @param {Array<string>} request.user_players_out - Player IDs user is trading away
 * @param {Array<string>} request.user_players_in - Player IDs user is receiving
 * @returns {Promise<Object>} Analysis session data with session_id
 */
export const startTradeAnalysis = async (request) => {
  try {
    const response = await api.post('/api/trade-assistant/analyze', request, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get trade analysis result
 * @param {string} sessionId - Analysis session ID
 * @returns {Promise<Object>} Analysis result with status
 */
export const getTradeAnalysisResult = async (sessionId) => {
  try {
    const response = await api.get(`/api/trade-assistant/analysis/${sessionId}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Start matchup simulation for a trade analysis
 * @param {string} sessionId - Analysis session ID
 * @param {number} weeksAhead - Number of weeks to simulate
 * @returns {Promise<Object>} Simulation session data
 */
export const simulateMatchup = async (sessionId, weeksAhead = 3) => {
  try {
    const response = await api.post('/api/trade-assistant/simulate', {
      session_id: sessionId,
      weeks_ahead: weeksAhead
    }, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get user's trade analysis history
 * @param {string} sleeperUserId - Sleeper user ID
 * @param {string|null} leagueId - Optional league filter
 * @param {number} limit - Maximum number of sessions to return
 * @returns {Promise<Object>} List of analysis sessions
 */
export const getUserTradeAnalyses = async (sleeperUserId, leagueId = null, limit = 20) => {
  try {
    const params = new URLSearchParams({ sleeper_user_id: sleeperUserId, limit: limit.toString() })
    if (leagueId) {
      params.append('league_id', leagueId)
    }
    const response = await api.get(`/api/trade-assistant/sessions?${params.toString()}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// ============================================================================
// ROSTER RANKING API
// ============================================================================

/**
 * Get roster rankings for a league
 * @param {string} leagueId - Sleeper league ID
 * @param {boolean} forceRefresh - Force recalculation (skip cache)
 * @returns {Promise<Object>} Roster rankings data
 */
export const getRosterRankings = async (leagueId, forceRefresh = false) => {
  try {
    const params = forceRefresh ? '?force_refresh=true' : ''
    const response = await api.get(`/api/roster-ranking/${leagueId}${params}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get cache status for roster rankings
 * @param {string} leagueId - Sleeper league ID
 * @returns {Promise<Object>} Cache status with TTL
 */
export const getRosterRankingCacheStatus = async (leagueId) => {
  try {
    const response = await api.get(`/api/roster-ranking/${leagueId}/cache-status`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Clear roster rankings cache
 * @param {string} leagueId - Sleeper league ID
 * @returns {Promise<Object>} Success message
 */
export const clearRosterRankingCache = async (leagueId) => {
  try {
    const response = await api.delete(`/api/roster-ranking/${leagueId}/cache`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get AI-powered roster analysis for team(s)
 * @param {string} leagueId - Sleeper league ID
 * @param {string} rosterId - (Optional) Specific roster ID to analyze. If not provided, analyzes all rosters
 * @param {boolean} forceRefresh - Force recalculation (skip cache)
 * @returns {Promise<Object>} Roster analysis/analyses with strengths/weaknesses/analysis
 */
export const getRosterAnalysis = async (leagueId, rosterId = null, forceRefresh = false) => {
  try {
    const params = new URLSearchParams()
    if (rosterId) params.append('roster_id', rosterId)
    if (forceRefresh) params.append('refresh', 'true')
    
    const queryString = params.toString() ? `?${params.toString()}` : ''
    const response = await api.get(`/api/roster-ranking/${leagueId}/analysis${queryString}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

/**
 * Get AI-powered roster analysis for a single roster
 * @param {string} leagueId - Sleeper league ID
 * @param {string} rosterId - Roster ID to analyze
 * @param {boolean} forceRefresh - Force recalculation (skip cache)
 * @returns {Promise<Object>} Single roster analysis with strengths/weaknesses/analysis
 */
export const getSingleRosterAnalysis = async (leagueId, rosterId, forceRefresh = false) => {
  try {
    const params = forceRefresh ? '?refresh=true' : ''
    const response = await api.get(`/api/roster-ranking/${leagueId}/roster/${rosterId}/analysis${params}`, { skipAuth: true })
    return response.data
  } catch (error) {
    throw new Error(getErrorMessage(error))
  }
}

// Export the axios instance as default for direct use if needed
export default api


