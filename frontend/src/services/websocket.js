/**
 * WebSocket Service for real-time trade negotiation updates and league roster updates
 */
class WebSocketService {
  constructor(sessionId, callbacks = {}, connectionType = 'trade', leagueId = null, chatSessionId = null) {
    this.sessionId = sessionId
    this.leagueId = leagueId
    this.chatSessionId = chatSessionId
    this.connectionType = connectionType
    this.callbacks = callbacks
    this.ws = null
    this.reconnectAttempts = 0
    this.maxReconnectAttempts = 10
    this.reconnectDelay = 1000
    this.isIntentionallyClosed = false
    this.pingInterval = null
  }

  connect() {
    try {
      const wsBaseUrl = import.meta.env.VITE_WS_BASE_URL || 'ws://localhost:3002'
      
      // Determine URL based on connection type
      let wsUrl
      if (this.connectionType === 'chat' && this.chatSessionId) {
        wsUrl = `${wsBaseUrl}/ws/roster-chat/${this.chatSessionId}`
      } else if (this.connectionType === 'league' && this.leagueId) {
        wsUrl = `${wsBaseUrl}/ws/league/${this.leagueId}`
      } else {
        wsUrl = `${wsBaseUrl}/ws/trade/${this.sessionId}`
      }
      
      console.log(`Connecting to WebSocket (${this.connectionType}):`, wsUrl)
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.reconnectAttempts = 0
        this.startPingInterval()
        
        if (this.callbacks.onConnect) {
          this.callbacks.onConnect()
        }
      }

      this.ws.onmessage = (event) => {
        try {
          const message = JSON.parse(event.data)
          this.handleMessage(message)
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        
        if (this.callbacks.onError) {
          this.callbacks.onError(`Connection error: ${error.message || 'Unknown error'}`)
        }
      }

      this.ws.onclose = (event) => {
        console.log('WebSocket closed:', event.code, event.reason)
        this.clearPingInterval()
        
        if (this.callbacks.onDisconnect) {
          this.callbacks.onDisconnect()
        }

        // Attempt to reconnect if not intentionally closed
        if (!this.isIntentionallyClosed && event.code !== 1000) {
          this.reconnect()
        }
      }

    } catch (error) {
      console.error('Failed to create WebSocket connection:', error)
      
      if (this.callbacks.onError) {
        this.callbacks.onError(`Failed to connect: ${error.message}`)
      }
    }
  }

  handleMessage(message) {
    console.log('WebSocket message received:', message)

    switch (message.type) {
      case 'status_update':
        if (this.callbacks.onStatusUpdate) {
          this.callbacks.onStatusUpdate(message.data)
        }
        break

      case 'agent_message':
        if (this.callbacks.onAgentMessage) {
          this.callbacks.onAgentMessage(message.data)
        }
        break

      case 'completion':
        if (this.callbacks.onStatusUpdate) {
          this.callbacks.onStatusUpdate({ status: 'completed' })
        }
        break

      case 'error':
        if (this.callbacks.onError) {
          this.callbacks.onError(message.data?.message || 'Server error')
        }
        break

      case 'roster_update':
        if (this.callbacks.onRosterUpdate) {
          this.callbacks.onRosterUpdate(message)
        }
        break

      case 'chat_message':
        if (this.callbacks.onChatMessage) {
          this.callbacks.onChatMessage(message.data)
        }
        break

      case 'pong':
        // Heartbeat response - do nothing
        break

      default:
        console.warn('Unknown message type:', message.type)
    }
  }

  reconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached')
      
      if (this.callbacks.onError) {
        this.callbacks.onError('Connection failed - max attempts reached')
      }
      return
    }

    if (this.isIntentionallyClosed) {
      return
    }

    this.reconnectAttempts++
    const delay = Math.min(this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1), 30000)
    
    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`)
    
    setTimeout(() => {
      if (!this.isIntentionallyClosed) {
        this.connect()
      }
    }, delay)
  }

  startPingInterval() {
    // Send ping every 30 seconds to keep connection alive
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        try {
          this.ws.send(JSON.stringify({ type: 'ping' }))
        } catch (error) {
          console.error('Error sending ping:', error)
        }
      }
    }, 30000)
  }

  clearPingInterval() {
    if (this.pingInterval) {
      clearInterval(this.pingInterval)
      this.pingInterval = null
    }
  }

  disconnect() {
    console.log('Disconnecting WebSocket')
    this.isIntentionallyClosed = true
    this.clearPingInterval()
    
    if (this.ws) {
      this.ws.close(1000, 'Client disconnect')
      this.ws = null
    }
  }

  // Send a message through the WebSocket
  send(message) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      try {
        this.ws.send(JSON.stringify(message))
      } catch (error) {
        console.error('Error sending WebSocket message:', error)
        
        if (this.callbacks.onError) {
          this.callbacks.onError(`Failed to send message: ${error.message}`)
        }
      }
    } else {
      console.warn('Cannot send message - WebSocket not connected')
    }
  }
}

/**
 * Factory function to create WebSocket connection for trade sessions
 * @param {string} sessionId - Session ID for the trade negotiation
 * @param {Object} callbacks - Callback functions for events
 * @returns {WebSocketService} WebSocket service instance
 */
export const createWebSocketConnection = (sessionId, callbacks = {}) => {
  return new WebSocketService(sessionId, callbacks, 'trade')
}

/**
 * Factory function to create WebSocket connection for league updates
 * @param {string} leagueId - Sleeper league ID
 * @param {Object} callbacks - Callback functions for events (onConnect, onRosterUpdate, onError, onDisconnect)
 * @returns {WebSocketService} WebSocket service instance
 */
export const createLeagueWebSocketConnection = (leagueId, callbacks = {}) => {
  return new WebSocketService(null, callbacks, 'league', leagueId)
}

/**
 * Factory function to create WebSocket connection for roster chat
 * @param {string} sessionId - Chat session ID
 * @param {Object} callbacks - Callback functions for events (onConnect, onChatMessage, onError, onDisconnect)
 * @returns {WebSocketService} WebSocket service instance
 */
export const createChatWebSocketConnection = (sessionId, callbacks = {}) => {
  return new WebSocketService(null, callbacks, 'chat', null, sessionId)
}

export default WebSocketService