import axios from 'axios'

// Create axios instance with default configuration
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Request interceptor for logging in development
api.interceptors.request.use(
  (config) => {
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

// Response interceptor for logging and error handling
api.interceptors.response.use(
  (response) => {
    if (import.meta.env.DEV) {
      console.log(`API Response: ${response.status} ${response.config.url}`)
    }
    return response
  },
  (error) => {
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
    return response.data
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
    const response = await api.post('/api/trade/start', tradePreference)
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

// Export the axios instance as default for direct use if needed
export default api