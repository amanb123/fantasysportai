import React, { useEffect, useRef } from 'react'

function ConversationHistory({ messages = [], isLoading = false }) {
  const messagesEndRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const getAgentStyling = (agentName) => {
    const safeName = agentName || ''
    if (safeName.includes('Team_')) {
      return {
        emoji: '🏀',
        className: 'agent-team'
      }
    } else if (safeName.includes('Commissioner')) {
      return {
        emoji: '🏁',
        className: 'agent-commissioner'
      }
    } else {
      return {
        emoji: '🤖',
        className: 'bg-gray-50 border-l-4 border-gray-400 text-gray-900'
      }
    }
  }

  const formatTimestamp = (timestamp) => {
    if (!timestamp) return ''
    return new Date(timestamp).toLocaleTimeString('en-US', {
      hour12: false,
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit'
    })
  }

  return (
    <>
      <style>
        {`
          @keyframes slideIn {
            from {
              opacity: 0;
              transform: translateY(10px);
            }
            to {
              opacity: 1;
              transform: translateY(0);
            }
          }
          .message-enter {
            animation: slideIn 0.3s ease-out;
          }
        `}
      </style>
      
      <div className="h-full flex flex-col bg-white rounded-lg border border-gray-200">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-gray-200">
          <h3 className="text-lg font-semibold text-gray-900">
            💬 Live Conversation
          </h3>
          {isLoading && (
            <div className="flex items-center space-x-2 text-sm text-gray-500">
              <div className="animate-pulse w-2 h-2 bg-primary-500 rounded-full"></div>
              <span>Agents are thinking...</span>
            </div>
          )}
        </div>

        {/* Messages Container */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-500">
              <div className="text-4xl mb-4 animate-bounce-gentle">🏀</div>
              <p className="text-center">
                Waiting for agents to start negotiation...
              </p>
              <div className="flex space-x-1 mt-2">
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
              </div>
            </div>
          ) : (
            messages.map((message, index) => {
              const styling = getAgentStyling(message.agent_name)
              return (
                <div key={index} className={`message-enter p-4 rounded-lg ${styling.className}`}>
                  <div className="flex items-center space-x-2 mb-2">
                    <span className="text-lg">{styling.emoji}</span>
                    <span className="font-semibold">{message.agent_name}</span>
                    <span className="text-xs opacity-75">
                      {formatTimestamp(message.timestamp)}
                    </span>
                  </div>
                  <div className="whitespace-pre-wrap text-sm leading-relaxed">
                    {message.content}
                  </div>
                </div>
              )
            })
          )}
          
          {/* Loading indicator at bottom */}
          {isLoading && messages.length > 0 && (
            <div className="flex items-center justify-center p-4">
              <div className="flex items-center space-x-2 text-sm text-gray-500">
                <div className="animate-spin w-4 h-4 border-2 border-gray-300 border-t-primary-600 rounded-full"></div>
                <span>Generating response...</span>
              </div>
            </div>
          )}
          
          {/* Auto-scroll anchor */}
          <div ref={messagesEndRef} />
        </div>
      </div>
    </>
  )
}

export default ConversationHistory