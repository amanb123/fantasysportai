import { useState, useEffect } from 'react'
import { getRosterAnalysis, getRosterRankingCacheStatus, clearRosterRankingCache } from '../services/api'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'

const RosterRankingView = ({ leagueId }) => {
  const [analyses, setAnalyses] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [refreshing, setRefreshing] = useState(false)

  // Load analyses on mount or league change
  useEffect(() => {
    const fetchAnalyses = async () => {
      if (!leagueId) {
        setError('Please select a league first')
        setLoading(false)
        return
      }

      try {
        setLoading(true)
        setError(null)

        const data = await getRosterAnalysis(leagueId, false)
        setAnalyses(data)
      } catch (err) {
        setError(err.message || 'Failed to fetch roster analysis')
        console.error('Error fetching analysis:', err)
      } finally {
        setLoading(false)
      }
    }
    
    fetchAnalyses()
  }, [leagueId])

  // Separate function for manual refresh
  const handleRefresh = async () => {
    if (!leagueId) return
    
    try {
      setRefreshing(true)
      setError(null)

      const data = await getRosterAnalysis(leagueId, true)
      setAnalyses(data)
    } catch (err) {
      setError(err.message || 'Failed to fetch roster analysis')
      console.error('Error fetching analysis:', err)
    } finally {
      setRefreshing(false)
    }
  }

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
    return 'bg-blue-600 text-white'
  }

  if (!leagueId) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-center">
          <p className="text-gray-500 text-lg">Please select a league to view roster analysis</p>
        </div>
      </div>
    )
  }

  if (loading && !analyses) {
    return <LoadingSpinner message="Loading roster analysis..." />
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-6">
      {/* Header */}
      <div className="mb-6">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-3xl font-bold text-gray-900">📊 Roster Analysis</h1>
            {analyses && (
              <p className="text-gray-600 mt-1">
                {analyses.league_name} • {analyses.total_rosters} Teams
              </p>
            )}
          </div>
          
          <button
            onClick={handleRefresh}
            disabled={loading || refreshing}
            className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors flex items-center gap-2"
          >
            <span>{refreshing ? '🔄' : '♻️'}</span>
            {refreshing ? 'Refreshing...' : 'Refresh Analysis'}
          </button>
        </div>
      </div>

      {error && <ErrorMessage message={error} />}

      {/* Analysis Cards */}
      {analyses && analyses.analyses && (
        <div className="space-y-6">
          {analyses.analyses.map((analysis) => (
            <div 
              key={analysis.owner_name} 
              className="bg-white rounded-lg shadow-md p-6 border-l-4 border-blue-500"
            >
              {/* Header */}
              <div className="flex items-start justify-between mb-4">
                <div className="flex items-center gap-3">
                  <span className={`inline-flex items-center justify-center w-10 h-10 rounded-full text-lg font-bold ${getRankBadgeColor(analysis.rank)}`}>
                    #{analysis.rank}
                  </span>
                  <div>
                    <h2 className="text-xl font-bold text-gray-900">{analysis.owner_name}</h2>
                    <p className="text-sm text-gray-600">{analysis.total_points.toFixed(2)} points</p>
                  </div>
                </div>
              </div>

              {/* Strengths */}
              {analysis.strengths && analysis.strengths.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-bold text-green-700 uppercase mb-2">Key Strengths:</h3>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                    {analysis.strengths.map((strength, idx) => (
                      <li key={idx}>{strength}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Weaknesses */}
              {analysis.weaknesses && analysis.weaknesses.length > 0 && (
                <div className="mb-4">
                  <h3 className="text-sm font-bold text-red-700 uppercase mb-2">Weaknesses:</h3>
                  <ul className="list-disc list-inside space-y-1 text-sm text-gray-700">
                    {analysis.weaknesses.map((weakness, idx) => (
                      <li key={idx}>{weakness}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Analysis */}
              {analysis.analysis && (
                <div className="mt-4 p-4 bg-blue-50 rounded-lg border border-blue-200">
                  <h3 className="text-sm font-bold text-blue-900 uppercase mb-2">Analysis:</h3>
                  <p className="text-sm text-gray-800 leading-relaxed">{analysis.analysis}</p>
                </div>
              )}

              {/* Top Players & Injuries (if available) */}
              <div className="mt-4 flex gap-6 text-xs text-gray-600">
                {analysis.top_players && analysis.top_players.length > 0 && (
                  <div>
                    <span className="font-semibold">Top Players:</span> {analysis.top_players.join(', ')}
                  </div>
                )}
                {analysis.injured_count > 0 && (
                  <div className="text-red-600">
                    <span className="font-semibold">Injured:</span> {analysis.injured_players.join(', ')}
                    {analysis.injured_count > analysis.injured_players.length && ` +${analysis.injured_count - analysis.injured_players.length} more`}
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}

      {!analyses && !loading && (
        <div className="text-center py-12">
          <p className="text-gray-500">No analysis available</p>
        </div>
      )}
    </div>
  )
}

export default RosterRankingView
