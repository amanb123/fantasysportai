import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSleeper } from '../contexts/SleeperContext'
import { getSleeperPlayersBulk, refreshLeagueData } from '../services/api'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'
import CurrentMatchup from './CurrentMatchup'

const RosterDisplay = () => {
  const navigate = useNavigate()
  const { 
    sleeperSession, 
    selectedLeague, 
    userRoster,
    leagueWebSocket,
    clearSession,
    fetchRosters,
    loading,
    error
  } = useSleeper()
  
  const [playerDetails, setPlayerDetails] = useState({})
  const [loadingPlayers, setLoadingPlayers] = useState(false)
  const [cacheWarning, setCacheWarning] = useState(null)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)

  // Redirect if no session or league
  useEffect(() => {
    if (!sleeperSession) {
      navigate('/')
      return
    }
    
    if (!selectedLeague) {
      navigate('/leagues')
      return
    }
  }, [sleeperSession, selectedLeague, navigate])

  // Fetch roster if not available
  useEffect(() => {
    if (selectedLeague && !userRoster && !loading) {
      fetchRosters(selectedLeague.league_id).catch(console.error)
    }
  }, [selectedLeague, userRoster, loading, fetchRosters])

  // Fetch player details when roster is available
  useEffect(() => {
    if (userRoster && userRoster.players && userRoster.players.length > 0) {
      const fetchPlayerDetails = async () => {
        setLoadingPlayers(true)
        setCacheWarning(null)
        
        try {
          // Fetch all players in a single bulk request
          const response = await getSleeperPlayersBulk(userRoster.players)
          
          // Check cache status
          if (response.cache_status && !response.cache_status.is_valid) {
            setCacheWarning(response.cache_status.message || 'Player data may be unavailable')
          }
          
          // Set player details from bulk response
          setPlayerDetails(response.players || {})
          
        } catch (error) {
          console.error('Error fetching player details:', error)
          // Create fallback player data
          const fallbackCache = {}
          userRoster.players.forEach(playerId => {
            fallbackCache[playerId] = {
              name: `Player ${playerId}`,
              team: null,
              positions: [],
              status: null,
              injury_status: null
            }
          })
          setPlayerDetails(fallbackCache)
          setCacheWarning('Failed to load player details. Showing player IDs only.')
        } finally {
          setLoadingPlayers(false)
        }
      }
      
      fetchPlayerDetails()
      setLastUpdated(new Date())
    }
  }, [userRoster])

  // Manual refresh handler
  const handleRefreshRoster = async () => {
    if (!selectedLeague) return
    
    setRefreshing(true)
    try {
      console.log('Manually refreshing roster data...')
      await refreshLeagueData(selectedLeague.league_id)
      
      // Don't fetch rosters here - rely on WebSocket roster_update message
      // The backend will broadcast the update after refreshing the cache
      
      setLastUpdated(new Date())
      console.log('Roster refresh complete')
      
    } catch (error) {
      console.error('Failed to refresh roster:', error)
      setCacheWarning('Failed to refresh roster data. Please try again.')
    } finally {
      setRefreshing(false)
    }
  }

  const handleBackToLeagues = () => {
    navigate('/leagues')
  }

  const handleChangeUser = () => {
    clearSession()
    navigate('/')
  }

  const getPlayerName = (playerId) => {
    const player = playerDetails[playerId]
    return player?.name || `Player ${playerId}`
  }

  const getPlayerPosition = (playerId) => {
    const player = playerDetails[playerId]
    if (player?.positions && player.positions.length > 0) {
      return player.positions.join('/')
    }
    return 'N/A'
  }

  const getPlayerTeam = (playerId) => {
    return playerDetails[playerId]?.team || 'N/A'
  }

  const handleRosterAssistant = () => {
    // Ensure we have the required data before navigating
    if (!userRoster) {
      console.error('Cannot start chat: user roster not loaded')
      return
    }
    navigate('/roster/chat')
  }

  const handleTradeAssistant = () => {
    // Ensure we have the required data before navigating
    if (!userRoster) {
      console.error('Cannot start trade assistant: user roster not loaded')
      return
    }
    navigate('/trade-assistant')
  }

  if (!sleeperSession || !selectedLeague) {
    return <LoadingSpinner />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-purple-600 p-4">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center space-x-4">
              <button
                onClick={handleBackToLeagues}
                className="text-gray-600 hover:text-gray-900 transition-colors"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-3xl font-bold text-gray-900">
                  {selectedLeague.name}
                </h1>
                <p className="text-gray-600">
                  {sleeperSession.display_name || sleeperSession.username}'s Roster
                </p>
              </div>
            </div>
            <div className="flex items-center space-x-3">
              <div className="flex flex-col items-center">
                <button
                  onClick={handleRefreshRoster}
                  disabled={refreshing}
                  className="btn-secondary flex items-center space-x-2"
                  title="Refresh roster data"
                >
                  <svg 
                    className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} 
                    fill="none" 
                    stroke="currentColor" 
                    viewBox="0 0 24 24"
                  >
                    <path 
                      strokeLinecap="round" 
                      strokeLinejoin="round" 
                      strokeWidth={2} 
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" 
                    />
                  </svg>
                  <span>{refreshing ? 'Refreshing...' : 'Refresh'}</span>
                </button>
                {lastUpdated && (
                  <span className="text-xs text-gray-400 mt-1">
                    Updated: {new Date(lastUpdated).toLocaleTimeString()}
                  </span>
                )}
              </div>
              <button
                onClick={handleBackToLeagues}
                className="btn-secondary"
              >
                Back to Leagues
              </button>
              <button
                onClick={handleChangeUser}
                className="btn-secondary"
              >
                Change User
              </button>
            </div>
          </div>

          {/* Assistant Buttons Panel */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-4 bg-gray-50 rounded-lg mt-4">
            <button
              onClick={handleRosterAssistant}
              className="flex items-center justify-center space-x-2 px-4 py-3 bg-white border-2 border-blue-200 text-blue-700 rounded-lg hover:bg-blue-50 hover:border-blue-300 transition-colors"
              title="Get AI assistance with player insights and view roster rankings"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
              </svg>
              <span className="font-semibold">Roster Assistant</span>
            </button>
            <button
              onClick={handleTradeAssistant}
              className="flex items-center justify-center space-x-2 px-4 py-3 bg-white border-2 border-green-200 text-green-700 rounded-lg hover:bg-green-50 hover:border-green-300 transition-colors"
              title="Get AI assistance with trade decisions"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4" />
              </svg>
              <span className="font-semibold">Trade Assistant</span>
            </button>
            <button
              className="flex items-center justify-center space-x-2 px-4 py-3 bg-white border-2 border-purple-200 text-purple-700 rounded-lg hover:bg-purple-50 hover:border-purple-300 transition-colors"
              title="Get AI assistance with matchup analysis"
            >
              <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              <span className="font-semibold">Matchup Assistant</span>
            </button>
          </div>
          <div className="text-xs text-gray-500 text-center mt-2">
            💡 Tip: Click Roster Assistant to view league rankings and get AI insights
          </div>

          {/* Current Matchup */}
          <CurrentMatchup 
            leagueId={selectedLeague.league_id}
            rosterId={userRoster?.roster_id}
            playerDetails={playerDetails}
          />
        </div>

        {/* Loading State */}
        {loading && (
          <div className="bg-white rounded-lg shadow-lg p-12">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="text-gray-600 mt-4">Loading your roster...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <ErrorMessage message={error} />
          </div>
        )}

        {/* Cache Warning */}
        {cacheWarning && (
          <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4 mb-6 rounded">
            <div className="flex">
              <div className="flex-shrink-0">
                <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                </svg>
              </div>
              <div className="ml-3">
                <p className="text-sm text-yellow-700">{cacheWarning}</p>
              </div>
            </div>
          </div>
        )}

        {/* No Roster Found */}
        {!loading && !error && !userRoster && (
          <div className="bg-white rounded-lg shadow-lg p-12">
            <div className="text-center">
              <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl text-gray-500">👥</span>
              </div>
              <h3 className="text-xl font-semibold text-gray-900 mb-2">
                No Roster Found
              </h3>
              <p className="text-gray-600">
                You don't appear to have a roster in this league, or there was an error loading it.
              </p>
            </div>
          </div>
        )}

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

export default RosterDisplay