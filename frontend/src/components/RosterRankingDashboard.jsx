import React, { useState, useEffect } from 'react';
import { getRosterRankings } from '../services/api';
import LoadingSpinner from './LoadingSpinner';
import ErrorMessage from './ErrorMessage';

const RosterRankingDashboard = ({ leagueId, hideHeader = false, onDataLoad }) => {
  const [rankings, setRankings] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [hoveredPlayer, setHoveredPlayer] = useState(null);
  const [loadingMessage, setLoadingMessage] = useState('Initializing...');

  // Function to load rankings (can be called from useEffect or retry button)
  const loadRankings = async () => {
    if (!leagueId) {
      setError('No league ID provided');
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      setError(null);
      
      // Progressive loading messages
      setLoadingMessage('Fetching roster data...');
      setTimeout(() => setLoadingMessage('Loading NBA player stats...'), 2000);
      setTimeout(() => setLoadingMessage('Calculating rankings...'), 5000);
      setTimeout(() => setLoadingMessage('This may take up to 90 seconds...'), 15000);
      
      const data = await getRosterRankings(leagueId);
      
      setRankings(data);
      if (onDataLoad) {
        onDataLoad(data);
      }
      setLoading(false);
      setLoadingMessage('Initializing...');
    } catch (err) {
      console.error('Failed to load rankings:', err);
      
      // User-friendly error messages
      let errorMessage = 'Failed to load roster rankings';
      
      if (err.message?.includes('timeout')) {
        errorMessage = '⏱️ Request timed out. The ranking service is taking longer than expected. This can happen on the first load. Please try again.';
      } else if (err.message?.includes('Network Error') || err.message?.includes('ERR_CONNECTION')) {
        errorMessage = '🔌 Unable to connect to the backend server. Please check your internet connection.';
      } else if (err.response?.status === 503) {
        errorMessage = '🚧 The roster ranking service is temporarily unavailable. Please try again in a moment.';
      } else if (err.response?.status === 500) {
        errorMessage = '⚠️ Server error while calculating rankings. This may be due to missing player data. Please try again.';
      } else if (err.message) {
        errorMessage = err.message;
      }
      
      setError(errorMessage);
      setLoading(false);
      setLoadingMessage('Initializing...');
    }
  };

  useEffect(() => {
    loadRankings();
  }, [leagueId]);

  const getRankBadge = (rank) => {
    if (rank === 1) return { emoji: '🥇', color: 'bg-yellow-100 border-yellow-400 text-yellow-800' };
    if (rank === 2) return { emoji: '🥈', color: 'bg-gray-100 border-gray-400 text-gray-800' };
    if (rank === 3) return { emoji: '🥉', color: 'bg-orange-100 border-orange-400 text-orange-800' };
    return { emoji: `#${rank}`, color: 'bg-blue-50 border-blue-300 text-blue-800' };
  };

  const getRankColorClass = (rank, totalRosters) => {
    const percentile = (rank / totalRosters) * 100;
    if (percentile <= 25) return 'border-green-500 bg-green-50';
    if (percentile <= 50) return 'border-blue-500 bg-blue-50';
    if (percentile <= 75) return 'border-yellow-500 bg-yellow-50';
    return 'border-red-500 bg-red-50';
  };

  if (loading) {
    return (
      <div className="flex flex-col justify-center items-center py-12 space-y-4">
        <LoadingSpinner />
        <div className="text-center">
          <p className="text-gray-700 font-medium">{loadingMessage}</p>
          <p className="text-sm text-gray-500 mt-2">
            First load may take longer as we fetch NBA stats
          </p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
        <div className="text-red-800 mb-4 whitespace-pre-line">{error}</div>
        <button
          onClick={loadRankings}
          className="px-6 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700 transition-colors font-medium"
        >
          🔄 Try Again
        </button>
      </div>
    );
  }

  if (!rankings || !rankings.rankings || rankings.rankings.length === 0) {
    return (
      <div className="text-center py-8 text-gray-500">
        No roster rankings available
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex justify-between items-start">
        <div>
          <h2 className="text-xl font-bold text-gray-900">Power Rankings</h2>
          <p className="text-sm text-gray-600 mt-1">
            {rankings.total_rosters} teams
          </p>
        </div>
        <button
          onClick={loadRankings}
          className="px-4 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
        >
          🔄 Refresh
        </button>
      </div>

      {/* Rankings Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {rankings.rankings.map((roster) => {
          const badge = getRankBadge(roster.rank);
          const colorClass = getRankColorClass(roster.rank, rankings.total_rosters);
          
          return (
            <div
              key={roster.roster_id}
              className={`border-2 rounded-lg p-4 shadow-sm hover:shadow-md transition-shadow ${colorClass}`}
            >
              {/* Rank Badge */}
              <div className="flex items-center justify-between mb-3">
                <div className={`px-3 py-1 rounded-full font-bold text-lg border-2 ${badge.color}`}>
                  {badge.emoji}
                </div>
                <div className="text-right">
                  <div className="text-xs text-gray-500">Record</div>
                  <div className="text-sm font-semibold">
                    {roster.wins}W - {roster.losses}L
                  </div>
                </div>
              </div>

              {/* Owner Name */}
              <h3 className="text-lg font-bold text-gray-900 mb-2">
                {roster.owner_name}
              </h3>

              {/* Stats */}
              <div className="space-y-2 mb-3">
                {/* Power Score - Prominently displayed at top */}
                <div className="text-center mb-2">
                  <div className="text-xs text-gray-500 mb-1">Power Score</div>
                  <div className="text-2xl font-bold text-indigo-600">
                    {roster.total_fantasy_points.toFixed(2)}
                  </div>
                </div>
                
                {/* Divider */}
                <div className="border-t border-gray-300 my-2"></div>
                
                {/* Base Points */}
                <div className="flex justify-between items-center">
                  <span className="text-xs text-gray-600">Base Points (Top 9 Players):</span>
                  <span className="text-sm font-semibold text-gray-700">
                    {roster.base_fantasy_points?.toFixed(2) || roster.total_fantasy_points.toFixed(2)}
                  </span>
                </div>
                
                {/* Win Bonus */}
                {roster.wins > 0 && (
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-green-600">Win Bonus ({roster.wins}W × 10%):</span>
                    <span className="text-sm font-semibold text-green-600">
                      +{roster.win_bonus?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                )}
                
                {/* Loss Penalty */}
                {roster.losses > 0 && (
                  <div className="flex justify-between items-center">
                    <span className="text-xs text-red-600">Loss Penalty ({roster.losses}L × 5%):</span>
                    <span className="text-sm font-semibold text-red-600">
                      -{roster.loss_penalty?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                )}
              </div>

              {/* Player Breakdown - Hover Area */}
              <div className="border-t pt-3 mt-3">
                <div className="text-xs font-semibold text-gray-700 mb-2">
                  Top Contributors:
                </div>
                <div className="space-y-1">
                  {roster.player_breakdown.slice(0, 3).map((player, idx) => (
                    <div
                      key={idx}
                      className="relative group"
                      onMouseEnter={() => setHoveredPlayer(`${roster.roster_id}-${idx}`)}
                      onMouseLeave={() => setHoveredPlayer(null)}
                    >
                      <div className="flex justify-between items-center text-xs bg-white bg-opacity-60 rounded px-2 py-1 hover:bg-opacity-100 cursor-pointer">
                        <span className="font-medium">
                          {player.name} ({player.position})
                        </span>
                        <span className="text-indigo-600 font-semibold">
                          {player.total_points.toFixed(1)}
                        </span>
                      </div>

                      {/* Tooltip */}
                      {hoveredPlayer === `${roster.roster_id}-${idx}` && (
                        <div className="absolute z-10 left-0 right-0 mt-1 p-3 bg-gray-900 text-white rounded-lg shadow-xl text-xs">
                          <div className="font-bold mb-2">
                            {player.name} - {player.team}
                          </div>
                          <div className="space-y-1">
                            <div className="flex justify-between">
                              <span>Games Played:</span>
                              <span className="font-semibold">{player.games_played}</span>
                            </div>
                            <div>
                              <span className="font-semibold">{player.season}</span>
                            </div>
                            <div className="border-t border-gray-700 pt-2 mt-2">
                              <div className="font-semibold mb-1">Category Breakdown:</div>
                              {Object.keys(player.category_contributions).length > 0 ? (
                                Object.entries(player.category_contributions).map(([cat, val]) => (
                                  <div key={cat} className="flex justify-between">
                                    <span className="uppercase">{cat}:</span>
                                    <span className="font-semibold">{val.toFixed(2)}</span>
                                  </div>
                                ))
                              ) : (
                                <div className="text-gray-400 italic">No contributions</div>
                              )}
                            </div>
                            <div className="border-t border-gray-700 pt-2 mt-2">
                              <div className="font-bold">
                                Total: {player.total_points.toFixed(2)} pts
                              </div>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
                
                {roster.player_breakdown.length > 3 && (
                  <div className="text-xs text-gray-500 mt-2 text-center">
                    +{roster.player_breakdown.length - 3} more players
                  </div>
                )}
              </div>

              {/* Excluded Players */}
              {roster.excluded_players && roster.excluded_players.length > 0 && (
                <div className="border-t pt-3 mt-3">
                  <div className="text-xs font-semibold text-red-700 mb-2">
                    ⚠️ Excluded ({roster.excluded_players.length}):
                  </div>
                  <div className="space-y-1">
                    {roster.excluded_players.slice(0, 2).map((player, idx) => (
                      <div
                        key={idx}
                        className="flex justify-between items-center text-xs bg-red-50 rounded px-2 py-1"
                      >
                        <span className="font-medium text-red-800">{player.name}</span>
                        <span className="text-red-600 text-xs">{player.reason}</span>
                      </div>
                    ))}
                    {roster.excluded_players.length > 2 && (
                      <div className="text-xs text-red-500 text-center">
                        +{roster.excluded_players.length - 2} more
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Footer Info */}
      <div className="text-xs text-gray-500 text-center pt-4 border-t">
        Last updated: {new Date(rankings.last_updated).toLocaleString()}
        {rankings.cached && ' (cached)'}
      </div>
    </div>
  );
};

export default RosterRankingDashboard;
