import { useState, useEffect } from 'react'
import { getRosterRankings, getRosterRankingCacheStatus, clearRosterRankingCache } from '../services/api'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'

const RosterRankingView = ({ leagueId }) => {
  const [rankings, setRankings] = useState(null)
  const [cacheStatus, setCacheStatus] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [sortBy, setSortBy] = useState('rank') // rank, points, wins, losses
  const [sortOrder, setSortOrder] = useState('asc') // asc, desc
  const [filterText, setFilterText] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  // Fetch roster rankings
  const fetchRankings = async (forceRefresh = false) => {
    if (!leagueId) {
      setError('Please select a league first')
      return
    }

    try {
      setLoading(true)
      setError(null)
      
      if (forceRefresh) {
        setRefreshing(true)
      }

      const data = await getRosterRankings(leagueId, forceRefresh)
      setRankings(data)

      // Fetch cache status
      const status = await getRosterRankingCacheStatus(leagueId)
      setCacheStatus(status)
    } catch (err) {
      setError(err.message || 'Failed to fetch roster rankings')
      console.error('Error fetching rankings:', err)
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  // Clear cache and refetch
  const handleClearCache = async () => {
    if (!leagueId) return

    try {
      setLoading(true)
      setError(null)
      
      await clearRosterRankingCache(leagueId)
      
      // Refetch after clearing cache
      await fetchRankings(true)
    } catch (err) {
      setError(err.message || 'Failed to clear cache')
      console.error('Error clearing cache:', err)
    } finally {
      setLoading(false)
    }
  }

  // Load rankings on mount or league change
  useEffect(() => {
    fetchRankings()
  }, [leagueId])

  // Sort rankings based on current sort settings
  const getSortedRankings = () => {
    if (!rankings || !rankings.rankings) return []

    let sorted = [...rankings.rankings]

    // Apply filter
    if (filterText) {
      const searchText = filterText.toLowerCase()
      sorted = sorted.filter(r => 
        r.owner_name?.toLowerCase().includes(searchText) ||
        r.roster_id?.toString().includes(searchText)
      )
    }

    // Apply sort
    sorted.sort((a, b) => {
      let aVal, bVal

      switch (sortBy) {
        case 'rank':
          aVal = a.rank
          bVal = b.rank
          break
        case 'points':
          aVal = a.total_fantasy_points
          bVal = b.total_fantasy_points
          break
        case 'wins':
          aVal = a.wins
          bVal = b.wins
          break
        case 'losses':
          aVal = a.losses
          bVal = b.losses
          break
        case 'name':
          aVal = a.owner_name?.toLowerCase() || ''
          bVal = b.owner_name?.toLowerCase() || ''
          break
        default:
          return 0
      }

      if (sortOrder === 'asc') {
        return aVal > bVal ? 1 : aVal < bVal ? -1 : 0
      } else {
        return aVal < bVal ? 1 : aVal > bVal ? -1 : 0
      }
    })

    return sorted
  }

  // Toggle sort
  const handleSort = (field) => {
    if (sortBy === field) {
      setSortOrder(sortOrder === 'asc' ? 'desc' : 'asc')
    } else {
      setSortBy(field)
      setSortOrder(field === 'rank' ? 'asc' : 'desc')
    }
  }

  // Get sort icon
  const getSortIcon = (field) => {
    if (sortBy !== field) return '⇅'
    return sortOrder === 'asc' ? '↑' : '↓'
  }

  // Format TTL
  const formatTTL = (seconds) => {
    if (seconds < 0) return 'Not cached'
    if (seconds < 60) return `${seconds}s`
    if (seconds < 3600) return `${Math.floor(seconds / 60)}m`
    return `${Math.floor(seconds / 3600)}h ${Math.floor((seconds % 3600) / 60)}m`
  }

  // Get rank badge color
  const getRankBadgeColor = (rank) => {
    if (rank === 1) return 'bg-yellow-500 text-white'
    if (rank === 2) return 'bg-gray-400 text-white'
    if (rank === 3) return 'bg-amber-600 text-white'
    if (rank <= 5) return 'bg-green-600 text-white'
    if (rank <= 8) return 'bg-blue-600 text-white'
    return 'bg-gray-600 text-white'
  }

  const sortedRankings = getSortedRankings()

  if (!leagueId) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-gray-500 text-lg">Please select a league to view roster rankings</p>
        </div>
      </div>
    )
  }

  if (loading && !rankings) {
    return <LoadingSpinner message="Loading roster rankings..." />
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">🏆 Roster Rankings</h1>
            {rankings && (
              <p className="text-gray-600 mt-1">
                {rankings.league_name} • {rankings.total_rosters} Teams
              </p>
            )}
          </div>
          
          <div className="flex gap-3">
            <button
              onClick={() => fetchRankings(true)}
              disabled={loading || refreshing}
              className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
            >
              <span>{refreshing ? '🔄' : '♻️'}</span>
              {refreshing ? 'Refreshing...' : 'Refresh Rankings'}
            </button>
            
            {cacheStatus?.cached && (
              <button
                onClick={handleClearCache}
                disabled={loading}
                className="px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
              >
                <span>🗑️</span>
                Clear Cache
              </button>
            )}
          </div>
        </div>

        {/* Cache Status Bar */}
        {cacheStatus && (
          <div className={`p-3 rounded-lg ${cacheStatus.cached ? 'bg-green-50 border border-green-200' : 'bg-gray-50 border border-gray-200'}`}>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-4">
                <span className="font-medium">
                  {cacheStatus.cached ? '✅ Cached' : '❌ Not Cached'}
                </span>
                {cacheStatus.cached && (
                  <>
                    <span className="text-gray-600">
                      TTL: {formatTTL(cacheStatus.ttl_remaining)}
                    </span>
                    {cacheStatus.last_updated && (
                      <span className="text-gray-600">
                        Updated: {new Date(cacheStatus.last_updated).toLocaleString()}
                      </span>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Search and Filter */}
        <div className="mt-4">
          <input
            type="text"
            placeholder="Search by team name or roster ID..."
            value={filterText}
            onChange={(e) => setFilterText(e.target.value)}
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          />
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {/* Warning for missing stats */}
      {rankings && rankings.rankings && rankings.rankings.every(r => r.total_fantasy_points === 0) && (
        <div className="mb-6 bg-yellow-50 border-l-4 border-yellow-400 p-4 rounded-lg">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-yellow-400" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <h3 className="text-sm font-medium text-yellow-800">NBA Stats Not Available</h3>
              <div className="mt-2 text-sm text-yellow-700">
                <p>
                  Player statistics are currently unavailable. This could be because:
                </p>
                <ul className="list-disc list-inside mt-2 space-y-1">
                  <li>The NBA MCP service isn't configured or running</li>
                  <li>Player names don't match between Sleeper and NBA data</li>
                  <li>The season hasn't started yet or stats haven't been populated</li>
                </ul>
                <p className="mt-2">
                  The ranking structure is working correctly - it just needs player data to calculate points.
                </p>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Rankings Table */}
      {rankings && (
        <div className="bg-white rounded-lg shadow-md overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th
                    onClick={() => handleSort('rank')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Rank {getSortIcon('rank')}
                  </th>
                  <th
                    onClick={() => handleSort('name')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Team {getSortIcon('name')}
                  </th>
                  <th
                    onClick={() => handleSort('points')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Fantasy Points {getSortIcon('points')}
                  </th>
                  <th
                    onClick={() => handleSort('wins')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Wins {getSortIcon('wins')}
                  </th>
                  <th
                    onClick={() => handleSort('losses')}
                    className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider cursor-pointer hover:bg-gray-100"
                  >
                    Losses {getSortIcon('losses')}
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Record
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                    Category Scores
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {sortedRankings.length === 0 ? (
                  <tr>
                    <td colSpan="7" className="px-6 py-8 text-center text-gray-500">
                      {filterText ? 'No teams match your search' : 'No rankings available'}
                    </td>
                  </tr>
                ) : (
                  sortedRankings.map((ranking) => (
                    <tr key={ranking.roster_id} className="hover:bg-gray-50 transition-colors">
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className={`inline-flex items-center justify-center w-8 h-8 rounded-full text-sm font-bold ${getRankBadgeColor(ranking.rank)}`}>
                          {ranking.rank}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div>
                            <div className="text-sm font-medium text-gray-900">
                              {ranking.owner_name || `Team ${ranking.roster_id}`}
                            </div>
                            <div className="text-sm text-gray-500">
                              Roster #{ranking.roster_id}
                            </div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="text-sm font-semibold text-gray-900">
                          {ranking.total_fantasy_points.toFixed(2)}
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-green-600 font-medium">
                          {ranking.wins}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-red-600 font-medium">
                          {ranking.losses}
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span className="text-sm text-gray-900">
                          {ranking.wins}-{ranking.losses}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-xs text-gray-600 max-w-xs">
                          {Object.entries(ranking.category_scores || {}).length > 0 ? (
                            (() => {
                              const nonZeroScores = Object.entries(ranking.category_scores)
                                .filter(([_, score]) => Math.abs(score) > 0.01)
                              
                              if (nonZeroScores.length === 0) {
                                return (
                                  <div className="text-yellow-600 text-xs">
                                    ⚠️ No stats available
                                  </div>
                                )
                              }
                              
                              return (
                                <div className="space-y-1">
                                  {nonZeroScores
                                    .slice(0, 3)
                                    .map(([cat, score]) => (
                                      <div key={cat} className="flex justify-between">
                                        <span className="font-medium">{cat}:</span>
                                        <span>{score.toFixed(1)}</span>
                                      </div>
                                    ))}
                                  {nonZeroScores.length > 3 && (
                                    <div className="text-gray-400 text-center">
                                      +{nonZeroScores.length - 3} more
                                    </div>
                                  )}
                                </div>
                              )
                            })()
                          ) : (
                            <span className="text-gray-400">No data</span>
                          )}
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Summary Stats */}
      {rankings && sortedRankings.length > 0 && (
        <div className="mt-6 grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Average Points</div>
            <div className="text-2xl font-bold text-gray-900">
              {(sortedRankings.reduce((sum, r) => sum + r.total_fantasy_points, 0) / sortedRankings.length).toFixed(2)}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Highest Points</div>
            <div className="text-2xl font-bold text-green-600">
              {Math.max(...sortedRankings.map(r => r.total_fantasy_points)).toFixed(2)}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Lowest Points</div>
            <div className="text-2xl font-bold text-red-600">
              {Math.min(...sortedRankings.map(r => r.total_fantasy_points)).toFixed(2)}
            </div>
          </div>
          <div className="bg-white rounded-lg shadow p-4">
            <div className="text-sm text-gray-500">Point Spread</div>
            <div className="text-2xl font-bold text-blue-600">
              {(Math.max(...sortedRankings.map(r => r.total_fantasy_points)) - 
                Math.min(...sortedRankings.map(r => r.total_fantasy_points))).toFixed(2)}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default RosterRankingView
