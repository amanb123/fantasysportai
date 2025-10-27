import React, { useState, useEffect } from 'react'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'
import { getSleeperPlayersBulk } from '../services/api'

const RosterAssistant = ({ leagueId, rosterId, onBack }) => {
  const [userRoster, setUserRoster] = useState(null)
  const [playerDetails, setPlayerDetails] = useState({})
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    const fetchRosterData = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch rosters
        const rostersResponse = await fetch(`https://api.sleeper.app/v1/league/${leagueId}/rosters`)
        if (!rostersResponse.ok) throw new Error('Failed to fetch rosters')
        const rostersData = await rostersResponse.json()

        // Find user's roster
        const roster = rostersData.find(r => r.roster_id === rosterId)
        if (!roster) throw new Error('Roster not found')

        // Fetch current week matchup to get starters
        const leagueResponse = await fetch(`https://api.sleeper.app/v1/league/${leagueId}`)
        if (!leagueResponse.ok) throw new Error('Failed to fetch league info')
        const leagueData = await leagueResponse.json()
        const week = leagueData.settings?.leg || 1

        const matchupsResponse = await fetch(`https://api.sleeper.app/v1/league/${leagueId}/matchups/${week}`)
        if (!matchupsResponse.ok) throw new Error('Failed to fetch matchups')
        const matchupsData = await matchupsResponse.json()

        const userMatchup = matchupsData.find(m => m.roster_id === rosterId)
        
        setUserRoster({
          ...roster,
          starters: userMatchup?.starters || []
        })

        // Fetch player details
        if (roster.players && roster.players.length > 0) {
          try {
            const response = await getSleeperPlayersBulk(roster.players)
            setPlayerDetails(response.players || {})
          } catch (err) {
            console.error('Error fetching player details:', err)
          }
        }
      } catch (err) {
        console.error('Error fetching roster:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    if (leagueId && rosterId) {
      fetchRosterData()
    }
  }, [leagueId, rosterId])

  const getPlayerName = (playerId) => {
    const player = playerDetails?.[playerId]
    return player?.name || `Player ${playerId}`
  }

  const getPlayerPosition = (playerId) => {
    const player = playerDetails?.[playerId]
    if (player?.positions && player.positions.length > 0) {
      return player.positions.join('/')
    }
    return 'N/A'
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-purple-600 p-4">
        <div className="mx-auto max-w-6xl">
          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <button
              onClick={onBack}
              className="flex items-center space-x-2 text-white hover:text-orange-200 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="font-semibold">Back to Overview</span>
            </button>
            <h1 className="text-3xl font-bold text-white">Roster Assistant</h1>
            <div className="w-32"></div> {/* Spacer for centering */}
          </div>

          <div className="bg-white rounded-lg shadow-lg p-12">
            <div className="flex items-center justify-center">
              <LoadingSpinner />
              <span className="ml-3 text-gray-600">Loading roster...</span>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-purple-600 p-4">
        <div className="mx-auto max-w-6xl">
          {/* Header */}
          <div className="mb-6 flex items-center justify-between">
            <button
              onClick={onBack}
              className="flex items-center space-x-2 text-white hover:text-orange-200 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
              </svg>
              <span className="font-semibold">Back to Overview</span>
            </button>
            <h1 className="text-3xl font-bold text-white">Roster Assistant</h1>
            <div className="w-32"></div>
          </div>

          <div className="bg-white rounded-lg shadow-lg p-6">
            <ErrorMessage message={`Error loading roster: ${error}`} />
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-purple-600 p-4">
      <div className="mx-auto max-w-6xl">
        {/* Header */}
        <div className="mb-6 flex items-center justify-between">
          <button
            onClick={onBack}
            className="flex items-center space-x-2 text-white hover:text-orange-200 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
            </svg>
            <span className="font-semibold">Back to Overview</span>
          </button>
          <h1 className="text-3xl font-bold text-white">Roster Assistant</h1>
          <div className="w-32"></div>
        </div>

        {/* Current Roster Panel */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h2 className="text-xl font-semibold text-gray-900 mb-6">
            Current Roster ({userRoster?.players?.length || 0} players)
          </h2>
          
          {/* Starting Lineup */}
          {userRoster?.starters && userRoster.starters.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-medium text-gray-700 mb-3">
                Starting Lineup ({userRoster.starters.length})
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {userRoster.starters.map((playerId, index) => (
                  <div key={`starter-${playerId}-${index}`} className="p-4 border border-green-200 rounded-lg bg-green-50">
                    <div className="flex items-center justify-between">
                      <div>
                        <div className="font-semibold text-gray-900">
                          {getPlayerName(playerId)}
                        </div>
                        <div className="text-sm text-gray-600">
                          {getPlayerPosition(playerId)}
                        </div>
                      </div>
                      <div className="w-8 h-8 bg-green-600 rounded-full flex items-center justify-center">
                        <span className="text-white text-xs font-bold">S</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bench Players */}
          {userRoster?.players && (() => {
            const benchPlayers = userRoster.players.filter(
              playerId => !userRoster.starters?.includes(playerId)
            )
            
            return benchPlayers.length > 0 && (
              <div>
                <h3 className="text-lg font-medium text-gray-700 mb-3">
                  Bench ({benchPlayers.length})
                </h3>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {benchPlayers.map((playerId, index) => (
                    <div key={`bench-${playerId}-${index}`} className="p-4 border border-gray-200 rounded-lg">
                      <div className="flex items-center justify-between">
                        <div>
                          <div className="font-semibold text-gray-900">
                            {getPlayerName(playerId)}
                          </div>
                          <div className="text-sm text-gray-600">
                            {getPlayerPosition(playerId)}
                          </div>
                        </div>
                        <div className="w-8 h-8 bg-gray-400 rounded-full flex items-center justify-center">
                          <span className="text-white text-xs font-bold">B</span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )
          })()}
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-white text-sm">
          <p>
            Roster data from{' '}
            <a
              href="https://sleeper.app"
              target="_blank"
              rel="noopener noreferrer"
              className="underline hover:text-orange-200"
            >
              Sleeper.app
            </a>
          </p>
        </div>
      </div>
    </div>
  )
}

export default RosterAssistant
