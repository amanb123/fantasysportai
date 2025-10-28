import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSleeper } from '../contexts/SleeperContext'
import { startRosterChat, sendChatMessage, getChatHistory } from '../services/api'
import { createChatWebSocketConnection } from '../services/websocket'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'
import RosterRankingDashboard from './RosterRankingDashboard'

const RosterChat = () => {
  const { sessionId: routeSessionId } = useParams()
  const navigate = useNavigate()
  const { sleeperSession, selectedLeague, userRoster } = useSleeper()
  
  const [messages, setMessages] = useState([])
  const [inputMessage, setInputMessage] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sessionId, setSessionId] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [isInitializing, setIsInitializing] = useState(true)
  const [activeTab, setActiveTab] = useState('chat') // 'chat' or 'rankings'
  
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)

  // Initialize chat session
  useEffect(() => {
    const initializeChat = async () => {
      try {
        setError(null)
        
        // Check for required context data
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
        
        if (routeSessionId) {
          // Load existing chat
          const history = await getChatHistory(routeSessionId)
          setMessages(history.messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            metadata: msg.metadata
          })))
          setSessionId(routeSessionId)
        } else {
          // Create new chat session
          const response = await startRosterChat(
            selectedLeague.league_id,
            userRoster.roster_id,
            sleeperSession.user_id,
            null
          )
          
          setSessionId(response.session_id)
          
          if (response.initial_response) {
            setMessages([{
              role: 'assistant',
              content: response.initial_response,
              timestamp: new Date().toISOString()
            }])
          }
        }
        
        setIsInitializing(false)
      } catch (err) {
        console.error('Error initializing chat:', err)
        setError(err.message || 'Failed to initialize chat')
        setIsInitializing(false)
      }
    }
    
    initializeChat()
  }, [routeSessionId, sleeperSession, selectedLeague, userRoster, navigate])

  // Connect WebSocket when session ID is available
  useEffect(() => {
    if (!sessionId) return
    
    const ws = createChatWebSocketConnection(sessionId, {
      onConnect: () => {
        console.log('Chat WebSocket connected')
        setWsConnected(true)
      },
      onChatMessage: (data) => {
        console.log('Received chat message:', data)
        handleIncomingMessage(data)
      },
      onError: (error) => {
        console.error('WebSocket error:', error)
        setWsConnected(false)
      },
      onDisconnect: () => {
        console.log('Chat WebSocket disconnected')
        setWsConnected(false)
      }
    })
    
    ws.connect()
    wsRef.current = ws
    
    return () => {
      if (wsRef.current) {
        wsRef.current.disconnect()
      }
    }
  }, [sessionId])

  // Auto-scroll to bottom when messages change
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleIncomingMessage = (messageData) => {
    const { role, content, timestamp, metadata } = messageData
    
    // Check for duplicate
    const isDuplicate = messages.some(msg => 
      msg.content === content && 
      Math.abs(new Date(msg.timestamp) - new Date(timestamp)) < 1000
    )
    
    if (!isDuplicate) {
      setMessages(prev => [...prev, { role, content, timestamp, metadata }])
    }
  }

  const handleSendMessage = async (e) => {
    e.preventDefault()
    
    const trimmedMessage = inputMessage.trim()
    if (!trimmedMessage || loading) return
    
    // Add user message optimistically
    const userMessage = {
      role: 'user',
      content: trimmedMessage,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    setInputMessage('')
    setLoading(true)
    
    try {
      // Send message to API
      const response = await sendChatMessage(sessionId, trimmedMessage)
      
      // Response comes via WebSocket, but add fallback
      if (!wsConnected) {
        setMessages(prev => [...prev, {
          role: response.role,
          content: response.content,
          timestamp: response.timestamp,
          metadata: response.metadata
        }])
      }
      
    } catch (err) {
      console.error('Error sending message:', err)
      // Remove optimistic message on error
      setMessages(prev => prev.filter(msg => msg !== userMessage))
      setError(err.message || 'Failed to send message')
      setInputMessage(trimmedMessage) // Restore input
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSendMessage(e)
    }
  }

  // Handle quick action button clicks
  const handleQuickAction = async (message) => {
    if (loading) return
    
    setInputMessage(message)
    setLoading(true)
    
    // Add user message optimistically
    const userMessage = {
      role: 'user',
      content: message,
      timestamp: new Date().toISOString()
    }
    setMessages(prev => [...prev, userMessage])
    
    try {
      // Send message to API
      const response = await sendChatMessage(sessionId, message)
      
      // Response comes via WebSocket, but add fallback
      if (!wsConnected) {
        setMessages(prev => [...prev, {
          role: response.role,
          content: response.content,
          timestamp: response.timestamp,
          metadata: response.metadata
        }])
      }
      
      // Clear input after successful send
      setInputMessage('')
      
    } catch (err) {
      console.error('Error sending message:', err)
      // Remove optimistic message on error
      setMessages(prev => prev.filter(msg => msg !== userMessage))
      setError(err.message || 'Failed to send message')
      // Keep the message in input on error
    } finally {
      setLoading(false)
    }
  }

  if (isInitializing) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <LoadingSpinner />
      </div>
    )
  }

  if (error && !sessionId) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <ErrorMessage message={error} />
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between mb-3">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
                <span>🏀</span>
                <span>Roster Assistant</span>
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                {selectedLeague?.name} - {sleeperSession?.display_name || sleeperSession?.username}
              </p>
            </div>
            <div className="flex items-center space-x-3">
              {activeTab === 'chat' && (
                <div className="flex items-center space-x-2">
                  <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
                  <span className="text-xs text-gray-600">
                    {wsConnected ? 'Connected' : 'Disconnected'}
                  </span>
                </div>
              )}
              <button
                onClick={() => navigate('/roster')}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Close
              </button>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex space-x-1 border-b border-gray-200">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'chat'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              💬 Chat
            </button>
            <button
              onClick={() => setActiveTab('rankings')}
              className={`px-4 py-2 text-sm font-medium transition-colors ${
                activeTab === 'rankings'
                  ? 'text-blue-600 border-b-2 border-blue-600'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              🏆 Rankings
            </button>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'chat' ? (
          <div className="max-w-5xl mx-auto px-6 py-6 space-y-4">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 mt-12">
                <div className="text-6xl mb-4">💬</div>
                <p className="text-lg font-medium">Ask me anything about your roster!</p>
                <p className="text-sm mt-2">
                  I can help with player insights, lineup advice, waiver wire suggestions, and more.
                </p>
              </div>
            ) : (
              messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                  <div className={`max-w-2xl px-4 py-3 rounded-lg ${
                    msg.role === 'user'
                      ? 'bg-blue-500 text-white'
                      : 'bg-white text-gray-900 border border-gray-200 shadow-sm'
                  }`}>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                    <div className="flex items-center justify-between mt-2 text-xs opacity-75">
                      <span>
                        {new Date(msg.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                      </span>
                      {msg.metadata?.historical_stats_fetched && (
                        <span className="ml-2 bg-blue-100 text-blue-800 px-2 py-0.5 rounded">
                          📊 Historical data
                        </span>
                      )}
                    </div>
                  </div>
                </div>
              ))
            )}
            
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white px-4 py-3 rounded-lg border border-gray-200 shadow-sm">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0ms'}} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '150ms'}} />
                    <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '300ms'}} />
                  </div>
                </div>
              </div>
            )}
            
            <div ref={messagesEndRef} />
          </div>
        ) : (
          <div className="max-w-7xl mx-auto px-6 py-6">
            <RosterRankingDashboard leagueId={selectedLeague?.league_id} />
          </div>
        )}
      </div>

      {/* Quick Action Buttons - Only show for chat tab and when not loading */}
      {activeTab === 'chat' && !loading && (
        <div className="bg-gray-50 border-t border-gray-200 px-6 py-3">
          <div className="max-w-5xl mx-auto">
            <div className="flex items-center space-x-2 overflow-x-auto pb-1">
              <span className="text-xs font-medium text-gray-600 whitespace-nowrap">Quick Actions:</span>
              <button
                onClick={() => handleQuickAction('Show me the best available free agents')}
                className="px-3 py-1.5 text-xs font-medium text-blue-700 bg-blue-50 border border-blue-200 rounded-lg hover:bg-blue-100 transition-colors whitespace-nowrap"
              >
                🔍 Find Free Agents
              </button>
              <button
                onClick={() => handleQuickAction('What players should I start this week?')}
                className="px-3 py-1.5 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-lg hover:bg-green-100 transition-colors whitespace-nowrap"
              >
                ⭐ Lineup Advice
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Input Area - Only show for chat tab */}
      {activeTab === 'chat' && (
        <div className="bg-white border-t border-gray-200 shadow-lg">
          <div className="max-w-5xl mx-auto px-6 py-4">
            {error && (
              <div className="mb-3">
                <ErrorMessage message={error} onClose={() => setError(null)} />
              </div>
            )}
            
            <form onSubmit={handleSendMessage} className="flex items-end space-x-3">
              <textarea
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Ask about your roster, player stats, lineup advice..."
                className="flex-1 resize-none rounded-lg border border-gray-300 px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                rows={3}
                maxLength={1000}
                disabled={loading}
              />
              <button
                type="submit"
                disabled={loading || !inputMessage.trim()}
                className="px-6 py-3 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
              >
                {loading ? (
                  <div className="animate-spin w-5 h-5 border-2 border-white border-t-transparent rounded-full" />
                ) : (
                  <>
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                    </svg>
                    <span>Send</span>
                  </>
                )}
              </button>
            </form>
            
            <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
              <span>Press Enter to send, Shift+Enter for new line</span>
              <span>{inputMessage.length}/1000</span>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default RosterChat
