import React from 'react'

function TeamRoster({ team, players = [] }) {
  const getPositionBadgeColor = (position) => {
    const colors = {
      'PG': 'bg-blue-100 text-blue-800 border-blue-200',
      'SG': 'bg-purple-100 text-purple-800 border-purple-200',
      'SF': 'bg-green-100 text-green-800 border-green-200',
      'PF': 'bg-orange-100 text-orange-800 border-orange-200',
      'C': 'bg-red-100 text-red-800 border-red-200'
    }
    return colors[position] || 'bg-gray-100 text-gray-800 border-gray-200'
  }

  const formatSalary = (salary) => {
    if (salary >= 1000000) {
      return `$${(salary / 1000000).toFixed(1)}M`
    }
    return `$${salary.toLocaleString()}`
  }

  const formatStat = (stat) => {
    return typeof stat === 'number' ? stat.toFixed(1) : '0.0'
  }

  const formatPercentage = (percentage) => {
    return (typeof percentage === 'number' && !isNaN(percentage)) 
      ? (percentage * 100).toFixed(1) + '%'
      : '—'
  }

  if (!team) {
    return (
      <div className="card">
        <p className="text-gray-500 text-center">No team selected</p>
      </div>
    )
  }

  return (
    <div className="card">
      {/* Team Header */}
      <div className="mb-6 pb-4 border-b border-gray-200">
        <h3 className="text-xl font-bold text-gray-900 mb-2">
          {team.name} Roster
        </h3>
        <div className="flex items-center space-x-6 text-sm text-gray-600">
          <div>
            <span className="font-medium">Total Salary:</span> {formatSalary(team.total_salary)}
          </div>
          <div>
            <span className="font-medium">Players:</span> {team.player_count}
          </div>
        </div>
      </div>

      {/* Players Grid */}
      {players.length === 0 ? (
        <div className="text-center text-gray-500 py-8">
          <div className="text-4xl mb-2">🏀</div>
          <p>No players found for this team</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {players.map((player) => (
            <div 
              key={player.id} 
              className="bg-gray-50 rounded-lg p-4 border border-gray-200 hover:shadow-lg hover:scale-[1.02] transition-all duration-200"
            >
              {/* Player Header */}
              <div className="flex items-start justify-between mb-3">
                <div className="flex-1">
                  <div className="flex items-center space-x-2 mb-1">
                    <span className={`px-2 py-1 rounded-full text-xs font-medium border ${getPositionBadgeColor(player.position)}`}>
                      {player.position}
                    </span>
                  </div>
                  <h4 className="font-semibold text-gray-900 text-sm">
                    {player.name}
                  </h4>
                  <p className="text-xs text-gray-600">
                    {formatSalary(player.salary)}
                  </p>
                </div>
              </div>

              {/* Stats Grid */}
              {player.stats && (
                <div className="grid grid-cols-2 gap-2 text-xs">
                  <div className="flex justify-between">
                    <span className="text-gray-500">PPG:</span>
                    <span className="font-medium">{formatStat(player.stats.points_per_game)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">RPG:</span>
                    <span className="font-medium">{formatStat(player.stats.rebounds_per_game)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">APG:</span>
                    <span className="font-medium">{formatStat(player.stats.assists_per_game)}</span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-500">FG%:</span>
                    <span className="font-medium">{formatPercentage(player.stats.field_goal_percentage)}</span>
                  </div>
                  <div className="flex justify-between col-span-2">
                    <span className="text-gray-500">3PT%:</span>
                    <span className="font-medium">{formatPercentage(player.stats.three_point_percentage)}</span>
                  </div>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

export default TeamRoster