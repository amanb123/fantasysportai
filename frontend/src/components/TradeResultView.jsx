import React, { useState, useEffect } from 'react'
import { useParams, useNavigate, Link } from 'react-router-dom'
import { getTradeResult } from '../services/api.js'
import LoadingSpinner from './LoadingSpinner.jsx'
import ErrorMessage from './ErrorMessage.jsx'
import ConversationHistory from './ConversationHistory.jsx'

function TradeResultView() {
  const { sessionId } = useParams()
  const navigate = useNavigate()
  
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [showConversation, setShowConversation] = useState(false)

  useEffect(() => {
    const fetchResult = async () => {
      try {
        setLoading(true)
        const resultData = await getTradeResult(sessionId)
        setResult(resultData)
      } catch (err) {
        setError(err.message || 'Failed to fetch trade results')
      } finally {
        setLoading(false)
      }
    }

    fetchResult()
  }, [sessionId])

  if (loading) {
    return <LoadingSpinner size="large" message="Loading trade results..." />
  }

  if (error) {
    return <ErrorMessage message={error} onRetry={() => window.location.reload()} />
  }

  if (!result) {
    return <ErrorMessage message="No trade results found for this session." />
  }

  const { trade_decision } = result
  const hasValidDecision = trade_decision && (trade_decision.approved !== undefined)
  const isApproved = hasValidDecision && trade_decision.approved
  const hasConsensus = hasValidDecision && trade_decision.consensus_reached

  const formatSalary = (salary) => {
    if (salary >= 1000000) {
      return `$${(salary / 1000000).toFixed(1)}M`
    }
    return `$${salary.toLocaleString()}`
  }

  const renderPlayersList = (players, title) => {
    if (!players || players.length === 0) {
      return (
        <div className="text-center text-gray-500 py-4">
          <p>No players in this part of the trade</p>
        </div>
      )
    }

    return (
      <div>
        <h4 className="font-semibold text-gray-900 mb-3">{title}</h4>
        <div className="space-y-2">
          {players.map((player, index) => (
            <div key={index} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <div className="font-medium text-gray-900">{player.name}</div>
                <div className="text-sm text-gray-600">{player.position}</div>
              </div>
              <div className="text-sm font-medium text-gray-700">
                {formatSalary(player.salary)}
              </div>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header Section */}
      <div className="text-center">
        <div className="text-6xl mb-4">
          {hasConsensus ? '✅' : '⚠️'}
        </div>
        <h1 className="text-3xl font-bold text-gray-900 mb-2">
          Trade Negotiation Complete
        </h1>
        <p className="text-lg text-gray-600">
          {hasConsensus 
            ? (isApproved ? 'The agents reached a consensus and approved a trade!' : 'The agents reached consensus but decided against the trade.')
            : 'The agents were unable to reach consensus on a trade.'
          }
        </p>
      </div>

      {/* Trade Details */}
      {hasValidDecision && isApproved && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            📋 Trade Details
          </h2>
          
          <div className="grid md:grid-cols-2 gap-8">
            {/* Players Traded Out */}
            <div>
              {renderPlayersList(
                trade_decision.traded_players_out, 
                `Team ${trade_decision.offering_team_id} Trades Away:`
              )}
            </div>

            {/* Players Traded In */}
            <div>
              {renderPlayersList(
                trade_decision.traded_players_in, 
                `Team ${trade_decision.offering_team_id} Receives:`
              )}
            </div>
          </div>

          {/* Commissioner Notes */}
          {trade_decision.commissioner_notes && (
            <div className="mt-6 p-4 bg-orange-50 border border-orange-200 rounded-lg">
              <h4 className="font-semibold text-orange-900 mb-2">
                🏁 Commissioner Notes
              </h4>
              <p className="text-orange-800">{trade_decision.commissioner_notes}</p>
            </div>
          )}
        </div>
      )}

      {/* Rejection Reasons */}
      {hasValidDecision && !isApproved && trade_decision.rejection_reasons && trade_decision.rejection_reasons.length > 0 && (
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            ❌ Rejection Reasons
          </h2>
          <ul className="space-y-2">
            {trade_decision.rejection_reasons.map((reason, index) => (
              <li key={index} className="flex items-start space-x-2">
                <span className="text-red-500 mt-1">•</span>
                <span className="text-gray-700">{reason}</span>
              </li>
            ))}
          </ul>

          {trade_decision.commissioner_notes && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg">
              <h4 className="font-semibold text-red-900 mb-2">
                🏁 Commissioner Notes
              </h4>
              <p className="text-red-800">{trade_decision.commissioner_notes}</p>
            </div>
          )}
        </div>
      )}

      {/* Conversation History Section */}
      <div className="card">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold text-gray-900">
            💬 Negotiation Conversation
          </h2>
          <button
            onClick={() => setShowConversation(!showConversation)}
            className="btn-secondary text-sm"
          >
            {showConversation ? 'Hide' : 'Show'} Conversation
          </button>
        </div>
        
        {showConversation && (
          <div className="h-96 border border-gray-200 rounded-lg">
            <ConversationHistory 
              messages={result.conversation || []} 
              isLoading={false}
            />
          </div>
        )}
        
        {!showConversation && (
          <div className="text-center text-gray-500 py-8">
            <p>Click "Show Conversation" to see the full agent negotiation</p>
          </div>
        )}
      </div>

      {/* Action Buttons */}
      <div className="flex items-center justify-center space-x-4">
        <Link 
          to="/" 
          className="btn-primary"
        >
          Start New Trade
        </Link>
        
        {hasValidDecision && isApproved && (
          <button 
            className="btn-secondary"
            onClick={() => alert('Trade execution will be implemented in the next phase')}
          >
            Execute Trade
          </button>
        )}
      </div>

      {/* Session Info */}
      <div className="text-center text-sm text-gray-500">
        <p>Session ID: {sessionId}</p>
        <p>Total Turns: {result.total_turns || 'Unknown'}</p>
      </div>
    </div>
  )
}

export default TradeResultView