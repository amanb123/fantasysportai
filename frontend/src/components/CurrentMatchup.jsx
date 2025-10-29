import React, { useState, useEffect } from 'react'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'
import RosterRankingDashboard from './RosterRankingDashboard'
import { getSleeperPlayersBulk } from '../services/api'

const CurrentMatchup = ({ leagueId, rosterId, playerDetails: initialPlayerDetails }) => {
  const [matchups, setMatchups] = useState([])
  const [rosters, setRosters] = useState([])
  const [users, setUsers] = useState([])
  const [playerDetails, setPlayerDetails] = useState(initialPlayerDetails || {})
  const [currentWeek, setCurrentWeek] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [userMatchup, setUserMatchup] = useState(null)
  const [opponentMatchup, setOpponentMatchup] = useState(null)
  const [userRosterData, setUserRosterData] = useState(null)
  const [opponentRosterData, setOpponentRosterData] = useState(null)
  const [userLineupExpanded, setUserLineupExpanded] = useState(false)
  const [opponentLineupExpanded, setOpponentLineupExpanded] = useState(false)
  const [rankings, setRankings] = useState(null)

  useEffect(() => {
    const fetchMatchups = async () => {
      try {
        setLoading(true)
        setError(null)

        // Fetch league info to get current week
        const leagueResponse = await fetch(`https://api.sleeper.app/v1/league/${leagueId}`)
        if (!leagueResponse.ok) throw new Error('Failed to fetch league info')
        const leagueData = await leagueResponse.json()
        
        // Use the current leg or default to week 1
        const week = leagueData.settings?.leg || 1
        setCurrentWeek(week)

        // Fetch all data in parallel
        const [matchupsResponse, rostersResponse, usersResponse] = await Promise.all([
          fetch(`https://api.sleeper.app/v1/league/${leagueId}/matchups/${week}`),
          fetch(`https://api.sleeper.app/v1/league/${leagueId}/rosters`),
          fetch(`https://api.sleeper.app/v1/league/${leagueId}/users`)
        ])

        if (!matchupsResponse.ok) throw new Error('Failed to fetch matchups')
        if (!rostersResponse.ok) throw new Error('Failed to fetch rosters')
        if (!usersResponse.ok) throw new Error('Failed to fetch users')

        const matchupsData = await matchupsResponse.json()
        const rostersData = await rostersResponse.json()
        const usersData = await usersResponse.json()
        
        setMatchups(matchupsData)
        setRosters(rostersData)
        setUsers(usersData)

        // Find user's matchup
        const userMatch = matchupsData.find(m => m.roster_id === rosterId)
        setUserMatchup(userMatch)

        // Find opponent's matchup (same matchup_id but different roster_id)
        if (userMatch) {
          const opponentMatch = matchupsData.find(
            m => m.matchup_id === userMatch.matchup_id && m.roster_id !== rosterId
          )
          setOpponentMatchup(opponentMatch)

          // Find roster data for both teams
          const userRoster = rostersData.find(r => r.roster_id === rosterId)
          const opponentRoster = opponentMatch 
            ? rostersData.find(r => r.roster_id === opponentMatch.roster_id)
            : null

          setUserRosterData(userRoster)
          setOpponentRosterData(opponentRoster)

          // Fetch player details for all players in both rosters
          if (userRoster && opponentRoster) {
            const allPlayerIds = [...new Set([
              ...(userRoster.players || []),
              ...(opponentRoster.players || [])
            ])]

            if (allPlayerIds.length > 0) {
              try {
                const response = await getSleeperPlayersBulk(allPlayerIds)
                setPlayerDetails(response.players || {})
              } catch (err) {
                console.error('Error fetching player details:', err)
                // Keep existing player details if fetch fails
              }
            }
          }
        }

      } catch (err) {
        console.error('Error fetching matchups:', err)
        setError(err.message)
      } finally {
        setLoading(false)
      }
    }

    if (leagueId && rosterId) {
      fetchMatchups()
    }
  }, [leagueId, rosterId])

  const getUserName = (ownerId) => {
    if (!ownerId) return 'Unknown'
    const user = users.find(u => u.user_id === ownerId)
    return user?.display_name || user?.username || `User ${ownerId}`
  }

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

  const renderRosterSide = (matchup, rosterData, title, isUser = false) => {
    if (!matchup || !rosterData) return null

    const starters = matchup.starters || []
    const allPlayers = rosterData.players || []
    const ownerName = getUserName(rosterData.owner_id)
    
    // Get wins and losses from roster settings
    const wins = rosterData.settings?.wins || 0
    const losses = rosterData.settings?.losses || 0
    const record = `${wins}-${losses}`

    // Separate bench players (not in starters)
    const benchPlayers = allPlayers.filter(playerId => !starters.includes(playerId))

    return (
      <div className={`flex-1 ${isUser ? 'bg-blue-50' : 'bg-red-50'} rounded-lg p-4`}>
        <div className="text-center mb-4">
          <h3 className={`text-lg font-bold ${isUser ? 'text-blue-900' : 'text-red-900'}`}>
            {ownerName}
          </h3>
          <div className="text-sm text-gray-600 mt-1">{record}</div>
        </div>

        {/* Player Cards */}
        <div className="space-y-3">
          {/* Starters */}
          {starters.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Starters</h4>
              <div className="grid grid-cols-3 gap-1.5">
                {starters.map((playerId, idx) => (
                  <div 
                    key={`starter-${playerId}-${idx}`}
                    className={`${isUser ? 'bg-blue-600' : 'bg-red-600'} text-white rounded px-2 py-1.5 shadow-sm`}
                  >
                    <div className="flex flex-col">
                      <span className="font-medium text-xs truncate">{getPlayerName(playerId)}</span>
                      <span className="text-[10px] opacity-75">{getPlayerPosition(playerId)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Bench */}
          {benchPlayers.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold text-gray-500 mb-2 uppercase tracking-wide">Bench</h4>
              <div className="grid grid-cols-3 gap-1.5">
                {benchPlayers.map((playerId, idx) => (
                  <div 
                    key={`bench-${playerId}-${idx}`}
                    className="bg-gray-300 text-gray-700 rounded px-2 py-1.5 shadow-sm"
                  >
                    <div className="flex flex-col">
                      <span className="font-medium text-xs truncate">{getPlayerName(playerId)}</span>
                      <span className="text-[10px] opacity-75">{getPlayerPosition(playerId)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="bg-white rounded-lg p-6 mt-4">
        <div className="flex items-center justify-center">
          <LoadingSpinner />
          <span className="ml-3 text-gray-600">Loading matchup...</span>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="mt-4">
        <ErrorMessage message={`Error loading matchup: ${error}`} />
      </div>
    )
  }

  if (!userMatchup) {
    return (
      <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 mt-4">
        <div className="flex items-center justify-center text-yellow-800">
          <svg className="w-5 h-5 mr-2" fill="currentColor" viewBox="0 0 20 20">
            <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
          </svg>
          <span>No matchup scheduled for Week {currentWeek}</span>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Section 1: Current Week Matchup */}
      <div>
        <h2 className="text-xl font-bold text-gray-900 mb-4">
          Week {currentWeek} Matchup
        </h2>
        <div className="bg-white rounded-lg shadow-sm p-6">
          {opponentMatchup && opponentRosterData ? (
            <div className="flex gap-4">
              {renderRosterSide(userMatchup, userRosterData, 'Your Team', true)}
              
              <div className="flex flex-col items-center justify-center px-4">
                <div className="text-2xl font-bold text-gray-400">VS</div>
                {userMatchup.points > (opponentMatchup?.points || 0) && (
                  <div className="text-green-600 text-sm mt-2 font-bold">Leading</div>
                )}
              </div>
              
              {renderRosterSide(opponentMatchup, opponentRosterData, 'Opponent', false)}
            </div>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-600">Waiting for opponent...</p>
            </div>
          )}
        </div>
      </div>

      {/* Section 2: Power Rankings */}
      <div>
        <RosterRankingDashboard leagueId={leagueId} />
      </div>
    </div>
  )
}

export default CurrentMatchup
