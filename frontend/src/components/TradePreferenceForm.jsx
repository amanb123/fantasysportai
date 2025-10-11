import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { startTradeNegotiation, getTeams, getTeamPlayers } from '../services/api.js'
import LoadingSpinner from './LoadingSpinner.jsx'
import ErrorMessage from './ErrorMessage.jsx'
import TeamRoster from './TeamRoster.jsx'

function TradePreferenceForm() {
  const navigate = useNavigate()
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [teams, setTeams] = useState([])
  const [selectedTeamId, setSelectedTeamId] = useState('')
  const [tradePreferences, setTradePreferences] = useState({
    improve_rebounds: false,
    improve_assists: false,
    improve_scoring: false,
    reduce_turnovers: false,
    notes: ''
  })
  const [teamPlayers, setTeamPlayers] = useState([])
  const [submitting, setSubmitting] = useState(false)

  // Fetch teams on mount
  useEffect(() => {
    const fetchTeams = async () => {
      try {
        setLoading(true)
        console.log('Fetching teams...')
        const teamsData = await getTeams()
        console.log('Teams data received:', teamsData)
        setTeams(teamsData)
      } catch (err) {
        console.error('Error fetching teams:', err)
        setError(err.message || 'Failed to load teams')
      } finally {
        setLoading(false)
      }
    }

    fetchTeams()
  }, [])

  // Fetch team players when team is selected
  const handleTeamSelect = async (teamId) => {
    setSelectedTeamId(teamId)
    setTeamPlayers([])
    
    if (!teamId) return

    try {
      const players = await getTeamPlayers(teamId)
      setTeamPlayers(players)
    } catch (err) {
      console.error('Failed to load team players:', err)
      setError(err.message || 'Failed to load team players')
    }
  }

  const togglePreference = (preference) => {
    setTradePreferences(prev => ({
      ...prev,
      [preference]: !prev[preference]
    }))
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!selectedTeamId) {
      setError('Please select a team')
      return
    }

    try {
      setSubmitting(true)
      setError('')

      // Get other team IDs for target_team_ids
      const targetTeamIds = teams
        .filter(team => team.id !== parseInt(selectedTeamId))
        .map(team => team.id)

      const requestPayload = {
        team_id: parseInt(selectedTeamId),
        target_team_ids: targetTeamIds,
        improve_rebounds: tradePreferences.improve_rebounds,
        improve_assists: tradePreferences.improve_assists,
        improve_scoring: tradePreferences.improve_scoring,
        reduce_turnovers: tradePreferences.reduce_turnovers,
        notes: tradePreferences.notes
      }

      const response = await startTradeNegotiation(requestPayload)
      navigate(`/negotiation/${response.session_id}`)
    } catch (err) {
      setError(err.message || 'Failed to start trade negotiation')
    } finally {
      setSubmitting(false)
    }
  }

  const selectedTeam = teams.find(team => team.id === parseInt(selectedTeamId))

  if (loading) {
    return <LoadingSpinner size="large" message="Loading teams..." />
  }

  if (error && teams.length === 0) {
    return <ErrorMessage message={error} onRetry={() => window.location.reload()} />
  }

  // Show helpful message when no teams are available
  if (!loading && teams.length === 0) {
    return (
      <div className="max-w-4xl mx-auto text-center py-12">
        <div className="card">
          <h2 className="text-2xl font-bold text-gray-900 mb-4">
            🏀 No Teams Available
          </h2>
          <p className="text-gray-600 mb-6">
            The database doesn't have any teams set up yet. This is normal for a fresh installation.
          </p>
          <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
            <h3 className="font-medium text-blue-900 mb-2">Quick Setup:</h3>
            <p className="text-blue-800 text-sm">
              Run the seeding script to add sample teams: <br />
              <code className="bg-blue-100 px-2 py-1 rounded mt-2 inline-block">
                cd backend && python seed_data.py
              </code>
            </p>
          </div>
          <button 
            onClick={() => window.location.reload()} 
            className="btn-primary"
          >
            Refresh Page
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="max-w-4xl mx-auto space-y-8">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold text-gray-900 mb-4">
          Start a Trade Negotiation
        </h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          Select your team and set your trade preferences. Our AI agents will negotiate 
          with other teams to find the best possible trades for your roster.
        </p>
      </div>

      {error && <ErrorMessage message={error} />}

      <form onSubmit={handleSubmit} className="space-y-8">
        {/* Team Selection */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Select Your Team
          </h2>
          <select
            value={selectedTeamId}
            onChange={(e) => handleTeamSelect(e.target.value)}
            className="select-field"
            required
          >
            <option value="">Choose a team...</option>
            {teams.map(team => (
              <option key={team.id} value={team.id}>
                {team.name} ({team.player_count} players, ${(team.total_salary / 1000000).toFixed(1)}M)
              </option>
            ))}
          </select>
        </div>

        {/* Team Roster Display */}
        {selectedTeam && (
          <TeamRoster team={selectedTeam} players={teamPlayers} />
        )}

        {/* Trade Preferences */}
        <div className="card">
          <h2 className="text-xl font-semibold text-gray-900 mb-4">
            Trade Preferences
          </h2>
          <p className="text-gray-600 mb-6">
            Select the areas you'd like to improve through trades:
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            {[
              { key: 'improve_rebounds', label: 'Improve Rebounding', icon: '🏀' },
              { key: 'improve_assists', label: 'Improve Assists', icon: '🤝' },
              { key: 'improve_scoring', label: 'Improve Scoring', icon: '🎯' },
              { key: 'reduce_turnovers', label: 'Reduce Turnovers', icon: '🛡️' }
            ].map(preference => (
              <button
                key={preference.key}
                type="button"
                onClick={() => togglePreference(preference.key)}
                className={`p-4 rounded-lg border-2 transition-all duration-200 text-left ${
                  tradePreferences[preference.key]
                    ? 'border-primary-500 bg-primary-50 text-primary-900'
                    : 'border-gray-200 bg-white text-gray-700 hover:border-gray-300'
                }`}
              >
                <div className="flex items-center space-x-3">
                  <span className="text-2xl">{preference.icon}</span>
                  <div>
                    <div className="font-medium">{preference.label}</div>
                    <div className="text-sm opacity-75">
                      {tradePreferences[preference.key] ? 'Priority focus' : 'Click to prioritize'}
                    </div>
                  </div>
                </div>
              </button>
            ))}
          </div>

          {/* Additional Notes */}
          <div>
            <label htmlFor="notes" className="block text-sm font-medium text-gray-700 mb-2">
              Additional Notes (Optional)
            </label>
            <textarea
              id="notes"
              value={tradePreferences.notes}
              onChange={(e) => setTradePreferences(prev => ({ ...prev, notes: e.target.value }))}
              className="input-field"
              rows="3"
              placeholder="Any specific players you're looking to trade or acquire, or other preferences..."
            />
          </div>
        </div>

        {/* Submit Button */}
        <div className="text-center">
          <button
            type="submit"
            disabled={!selectedTeamId || submitting}
            className={`btn-primary text-lg px-8 py-3 ${
              (!selectedTeamId || submitting) ? 'opacity-50 cursor-not-allowed' : ''
            }`}
          >
            {submitting ? (
              <div className="flex items-center space-x-2">
                <div className="animate-spin w-4 h-4 border-2 border-white border-t-transparent rounded-full"></div>
                <span>Starting Negotiation...</span>
              </div>
            ) : (
              'Start Trade Negotiation 🏀'
            )}
          </button>
        </div>
      </form>
    </div>
  )
}

export default TradePreferenceForm