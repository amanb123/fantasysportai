import React, { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getTradeStatus, getTradeResult } from '../services/api.js'
import { createWebSocketConnection } from '../services/websocket.js'
import LoadingSpinner from './LoadingSpinner.jsx'
import ErrorMessage from './ErrorMessage.jsx'
import ConversationHistory from './ConversationHistory.jsx'

function TradeNegotiationView() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  
  const [status, setStatus] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [messages, setMessages] = useState([])
  const [wsConnected, setWsConnected] = useState(false)
  const [reconnecting, setReconnecting] = useState(false)
  const [wsError, setWsError] = useState('')
  const [wsHardFailed, setWsHardFailed] = useState(false)

  // Fetch current status
  const fetchStatus = async () => {
    try {
      const statusData = await getTradeStatus(sessionId)
      setStatus(statusData)
      
      // Navigate to results if completed
      if (statusData.status === 'completed') {
        navigate(`/result/${sessionId}`)
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch negotiation status')
    }
  }

  // Initialize WebSocket and fetch initial data
  useEffect(() => {
    // Hoist wsService outside the async function
    let wsService = null
    
    const init = async () => {
      try {
        setLoading(true)
        
        // Fetch initial status
        await fetchStatus()
        
        // Try to fetch existing conversation for faster initial load
        try {
          const existingResult = await getTradeResult(sessionId)
          if (existingResult.conversation) {
            setMessages(existingResult.conversation)
          }
        } catch (err) {
          // Ignore error - conversation might not exist yet
          console.log('No existing conversation found, starting fresh')
        }

        // Create WebSocket connection
        wsService = createWebSocketConnection(sessionId, {
          onConnect: () => {
            setWsConnected(true)
            setReconnecting(false)
            setWsError('')
            setWsHardFailed(false)
          },
          onDisconnect: () => {
            setWsConnected(false)
            setReconnecting(true)
          },
          onStatusUpdate: (data) => {
            setStatus(prev => ({ ...(prev || {}), ...data }))
            if (data.status === 'completed') {
              navigate(`/result/${sessionId}`)
            }
          },
          onAgentMessage: (message) => {
            setMessages(prev => {
              // Prevent duplicates and maintain order
              const exists = prev.some(msg => 
                msg.agent_name === message.agent_name && 
                msg.content === message.content &&
                Math.abs(new Date(msg.timestamp) - new Date(message.timestamp)) < 1000
              )
              
              if (exists) return prev
              
              const newMessages = [...prev, message]
              // Sort by timestamp to maintain correct order
              return newMessages.sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
            })
          },
          onError: (error) => {
            setWsError(error)
            if (error.includes('hard failure') || error.includes('max attempts')) {
              setWsHardFailed(true)
              setReconnecting(false)
            }
          }
        })

        // Connect WebSocket
        wsService.connect()
      } catch (err) {
        setError(err.message || 'Failed to initialize negotiation view')
      } finally {
        setLoading(false)
      }
    }

    init()
    
    // Return cleanup function from the effect
    return () => {
      if (wsService) {
        wsService.disconnect()
      }
    }
  }, [sessionId, navigate])

  // Polling fallback when WebSocket fails
  useEffect(() => {
    if (!wsHardFailed) return

    const pollInterval = setInterval(async () => {
      try {
        await fetchStatus()
        // Also try to fetch updated conversation
        const result = await getTradeResult(sessionId)
        if (result.conversation) {
          setMessages(result.conversation)
        }
      } catch (err) {
        console.error('Polling error:', err)
      }
    }, parseInt(import.meta.env.VITE_POLLING_INTERVAL || '2000'))

    return () => clearInterval(pollInterval)
  }, [wsHardFailed, sessionId])

  if (loading) {
    return <LoadingSpinner size="large" message="Connecting to negotiation..." />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={() => window.location.reload()} />
  }

  if (status?.status === 'failed') {
    return (
      <div className="max-w-4xl mx-auto">
        <ErrorMessage 
          message="The trade negotiation has failed. Please try starting a new negotiation."
          onRetry={() => navigate('/')}
        />
      </div>
    )
  }

  const getConnectionStatus = () => {
    if (wsConnected) {
      return { color: 'green', text: 'Connected', icon: '🟢' }
    } else if (reconnecting) {
      return { color: 'yellow', text: 'Reconnecting...', icon: '🟡' }
    } else if (wsHardFailed) {
      return { color: 'blue', text: 'Polling Mode', icon: '🔵' }
    } else {
      return { color: 'red', text: 'Disconnected', icon: '🔴' }
    }
  }

  const connectionStatus = getConnectionStatus()
  
  // Explicit class mapping to avoid dynamic Tailwind class generation
  const colorClassMap = {
    green: 'text-green-600',
    yellow: 'text-yellow-600',
    blue: 'text-blue-600',
    red: 'text-red-600'
  }

  return (
    <div className="max-w-6xl mx-auto h-screen flex flex-col">
      {/* Compact Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 flex-shrink-0">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-xl font-semibold text-gray-900">
              Agent Negotiation
            </h1>
            <p className="text-sm text-gray-500">
              Session: {sessionId}
            </p>
          </div>
          
          {/* Connection Status */}
          <div className="flex items-center space-x-2 text-sm">
            <span>{connectionStatus.icon}</span>
            <span className={colorClassMap[connectionStatus.color] || 'text-gray-600'}>
              {connectionStatus.text}
            </span>
          </div>
        </div>

        {/* WebSocket Error Banner */}
        {wsError && (
          <div className="mt-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <span className="text-yellow-600">⚠️</span>
                <span className="text-sm text-yellow-800">
                  Connection issue: {wsError}
                </span>
              </div>
              <button
                onClick={() => window.location.reload()}
                className="text-xs bg-yellow-600 text-white px-2 py-1 rounded hover:bg-yellow-700"
              >
                Retry
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Full-height Conversation */}
      <div className="flex-1 p-6 overflow-hidden">
        <ConversationHistory 
          messages={messages} 
          isLoading={status?.status === 'in_progress'} 
        />
      </div>
    </div>
  )
}

export default TradeNegotiationView