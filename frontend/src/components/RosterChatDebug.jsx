import React, { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useSleeper } from '../contexts/SleeperContext'
import { startRosterChat, sendChatMessage, getChatHistory, getRosterAnalysis } from '../services/api'
import { createChatWebSocketConnection } from '../services/websocket'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'

const RosterChatDebug = () => {
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
  const [rosterAnalysis, setRosterAnalysis] = useState(null)
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [debugInfo, setDebugInfo] = useState([])
  
  const messagesEndRef = useRef(null)
  const wsRef = useRef(null)

  const addDebug = (msg) => {
    console.log('[DEBUG]', msg)
    setDebugInfo(prev => [...prev, `${new Date().toLocaleTimeString()}: ${msg}`])
  }

  // Initialize chat session
  useEffect(() => {
    const initializeChat = async () => {
      try {
        addDebug('Initializing chat...')
        setError(null)
        
        // Check for required context data
        if (!sleeperSession) {
          addDebug('ERROR: No Sleeper session found')
          console.error('No Sleeper session found')
          // Don't navigate in debug mode
          // navigate('/')
          setIsInitializing(false)
          setError('No Sleeper session found - this is expected in debug mode')
          return
        }
        
        addDebug(`Sleeper session found: ${sleeperSession.user_id}`)
        
        if (!selectedLeague) {
          addDebug('ERROR: No league selected')
          console.error('No league selected')
          setIsInitializing(false)
          setError('No league selected')
          return
        }
        
        addDebug(`League selected: ${selectedLeague.league_id}`)
        
        if (!userRoster) {
          addDebug('ERROR: No user roster found')
          console.error('No user roster found')
          setIsInitializing(false)
          setError('No user roster found')
          return
        }
        
        addDebug(`User roster found: ${userRoster.roster_id}`)
        
        if (routeSessionId) {
          // Load existing chat
          addDebug(`Loading existing chat session: ${routeSessionId}`)
          const history = await getChatHistory(routeSessionId)
          setMessages(history.messages.map(msg => ({
            role: msg.role,
            content: msg.content,
            timestamp: msg.timestamp,
            metadata: msg.metadata
          })))
          setSessionId(routeSessionId)
          addDebug(`Loaded ${history.messages.length} messages`)
        } else {
          // Create new chat session
          addDebug('Creating new chat session...')
          const response = await startRosterChat(
            selectedLeague.league_id,
            userRoster.roster_id,
            sleeperSession.user_id,
            null
          )
          
          setSessionId(response.session_id)
          addDebug(`Chat session created: ${response.session_id}`)
          
          if (response.initial_response) {
            setMessages([{
              role: 'assistant',
              content: response.initial_response,
              timestamp: new Date().toISOString()
            }])
            addDebug('Initial response received')
          }
        }
        
        addDebug('Chat initialization complete')
        setIsInitializing(false)
      } catch (err) {
        addDebug(`ERROR initializing chat: ${err.message}`)
        console.error('Error initializing chat:', err)
        setError(err.message || 'Failed to initialize chat')
        setIsInitializing(false)
      }
    }
    
    initializeChat()
  }, [routeSessionId, sleeperSession?.user_id, selectedLeague?.league_id, userRoster?.roster_id, navigate])

  // Fetch roster analysis
  useEffect(() => {
    const fetchAnalysis = async () => {
      if (!selectedLeague?.league_id || !userRoster?.roster_id) {
        addDebug('Skipping analysis fetch - missing league or roster')
        return
      }
      
      try {
        addDebug(`Fetching roster analysis for league ${selectedLeague.league_id}, roster ${userRoster.roster_id}`)
        setAnalysisLoading(true)
        const data = await getRosterAnalysis(selectedLeague.league_id, userRoster.roster_id)
        setRosterAnalysis(data)
        addDebug(`Analysis loaded: ${data.analysis?.owner_name}`)
      } catch (err) {
        addDebug(`ERROR fetching analysis: ${err.message}`)
        console.error('Error fetching roster analysis:', err)
        // Don't set error state - analysis is optional
      } finally {
        setAnalysisLoading(false)
      }
    }
    
    fetchAnalysis()
  }, [selectedLeague?.league_id, userRoster?.roster_id])

  // Connect WebSocket when session ID is available
  useEffect(() => {
    if (!sessionId) return
    
    addDebug(`Connecting WebSocket for session: ${sessionId}`)
    const ws = createChatWebSocketConnection(sessionId, {
      onConnect: () => {
        addDebug('WebSocket connected')
        console.log('Chat WebSocket connected')
        setWsConnected(true)
      },
      onChatMessage: (data) => {
        addDebug(`WebSocket message received: ${data.role}`)
        console.log('Received chat message:', data)
        handleIncomingMessage(data)
      },
      onError: (error) => {
        addDebug(`WebSocket error: ${error}`)
        console.error('WebSocket error:', error)
        setWsConnected(false)
      },
      onDisconnect: () => {
        addDebug('WebSocket disconnected')
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
    
    addDebug(`Sending message: ${trimmedMessage.substring(0, 50)}...`)
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
      addDebug('Message sent successfully')
      
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
      addDebug(`ERROR sending message: ${err.message}`)
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

  const getRankBadgeColor = (rank) => {
    if (rank === 1) return 'bg-yellow-500 text-white'
    if (rank === 2) return 'bg-gray-400 text-white'
    if (rank === 3) return 'bg-amber-600 text-white'
    if (rank <= 5) return 'bg-green-600 text-white'
    return 'bg-blue-600 text-white'
  }

  addDebug(`Render: isInitializing=${isInitializing}, error=${!!error}, sessionId=${!!sessionId}`)

  if (isInitializing) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
        <LoadingSpinner />
        <div className="mt-4 text-sm text-gray-600">
          <h3 className="font-bold mb-2">Debug Info:</h3>
          <div className="bg-white rounded p-2 max-h-40 overflow-y-auto">
            {debugInfo.map((info, idx) => (
              <div key={idx} className="text-xs">{info}</div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (error && !sessionId) {
    return (
      <div className="min-h-screen flex flex-col items-center justify-center bg-gray-50 p-4">
        <ErrorMessage message={error} />
        <div className="mt-4 text-sm text-gray-600 max-w-2xl">
          <h3 className="font-bold mb-2">Debug Info:</h3>
          <div className="bg-white rounded p-4 max-h-60 overflow-y-auto">
            {debugInfo.map((info, idx) => (
              <div key={idx} className="text-xs mb-1">{info}</div>
            ))}
          </div>
          <div className="mt-4 bg-yellow-50 border border-yellow-200 rounded p-3">
            <h4 className="font-bold text-yellow-800">Context Status:</h4>
            <div className="text-xs mt-2">
              <div>Sleeper Session: {sleeperSession ? '✅' : '❌'}</div>
              <div>Selected League: {selectedLeague ? '✅' : '❌'}</div>
              <div>User Roster: {userRoster ? '✅' : '❌'}</div>
            </div>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* Debug Panel */}
      <div className="bg-yellow-50 border-b border-yellow-200 px-4 py-2">
        <details className="text-xs">
          <summary className="cursor-pointer font-bold">🐛 Debug Info (click to expand)</summary>
          <div className="mt-2 max-h-40 overflow-y-auto bg-white p-2 rounded">
            {debugInfo.map((info, idx) => (
              <div key={idx}>{info}</div>
            ))}
          </div>
        </details>
      </div>

      {/* Header */}
      <div className="bg-white border-b border-gray-200 px-6 py-4 shadow-sm">
        <div className="max-w-5xl mx-auto">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold text-gray-900 flex items-center space-x-2">
                <span>🏀</span>
                <span>Roster Assistant (DEBUG MODE)</span>
              </h1>
              <p className="text-sm text-gray-600 mt-1">
                {selectedLeague?.name} - {sleeperSession?.display_name || sleeperSession?.username}
              </p>
            </div>
            <div className="flex items-center space-x-3">
              <div className="flex items-center space-x-2">
                <div className={`w-2 h-2 rounded-full ${wsConnected ? 'bg-green-500' : 'bg-gray-400'}`} />
                <span className="text-xs text-gray-600">
                  {wsConnected ? 'Connected' : 'Disconnected'}
                </span>
              </div>
              <button
                onClick={() => navigate('/roster')}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content Area */}
      <div className="flex-1 overflow-y-auto">
        <div className="max-w-5xl mx-auto px-6 py-6 space-y-6">
          
          {/* Section 1: Roster Analysis */}
          {analysisLoading ? (
            <div className="bg-white rounded-lg shadow-sm p-6">
              <LoadingSpinner message="Loading roster analysis..." />
            </div>
          ) : rosterAnalysis?.analysis ? (
            <div className="bg-white rounded-lg shadow-sm border border-gray-200">
              {/* Analysis Header */}
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <div className={`inline-flex items-center justify-center w-10 h-10 rounded-full ${getRankBadgeColor(rosterAnalysis.analysis.rank)}`}>
                    <span className="text-sm font-bold">#{rosterAnalysis.analysis.rank}</span>
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{rosterAnalysis.analysis.owner_name}</h2>
                    <p className="text-sm text-gray-600">{rosterAnalysis.analysis.total_fantasy_points.toFixed(1)} points</p>
                  </div>
                </div>
              </div>

              {/* Analysis Content */}
              <div className="px-6 py-4 space-y-4">
                {/* Key Strengths */}
                {rosterAnalysis.analysis.strengths && rosterAnalysis.analysis.strengths.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-green-700 mb-2">Key Strengths</h3>
                    <ul className="space-y-1">
                      {rosterAnalysis.analysis.strengths.map((strength, idx) => (
                        <li key={idx} className="text-sm text-gray-700 flex items-start">
                          <span className="text-green-600 mr-2">•</span>
                          <span>{strength}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Weaknesses */}
                {rosterAnalysis.analysis.weaknesses && rosterAnalysis.analysis.weaknesses.length > 0 && (
                  <div>
                    <h3 className="text-sm font-semibold text-red-700 mb-2">Weaknesses</h3>
                    <ul className="space-y-1">
                      {rosterAnalysis.analysis.weaknesses.map((weakness, idx) => (
                        <li key={idx} className="text-sm text-gray-700 flex items-start">
                          <span className="text-red-600 mr-2">•</span>
                          <span>{weakness}</span>
                        </li>
                      ))}
                    </ul>
                  </div>
                )}

                {/* Analysis Text */}
                {rosterAnalysis.analysis.analysis && (
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-blue-900 mb-2">Analysis</h3>
                    <p className="text-sm text-blue-800 leading-relaxed">{rosterAnalysis.analysis.analysis}</p>
                  </div>
                )}

                {/* Top Players & Injuries */}
                <div className="flex items-center justify-between text-xs text-gray-600 pt-2 border-t border-gray-100">
                  {rosterAnalysis.analysis.top_players && rosterAnalysis.analysis.top_players.length > 0 && (
                    <div>
                      <span className="font-medium">Top performers:</span> {rosterAnalysis.analysis.top_players.join(', ')}
                    </div>
                  )}
                  {rosterAnalysis.analysis.injured_count > 0 && (
                    <div className="text-red-600">
                      🏥 {rosterAnalysis.analysis.injured_count} injured
                    </div>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4 text-sm">
              No roster analysis available
            </div>
          )}

          {/* Section 2: Chat Messages */}
          <div className="space-y-4">
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
        </div>
      </div>

      {/* Input Area */}
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
    </div>
  )
}

export default RosterChatDebug
