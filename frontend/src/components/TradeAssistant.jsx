import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useSleeper } from '../contexts/SleeperContext';
import { 
  startTradeAnalysis, 
  getTradeAnalysisResult, 
  getRecentTrades,
  getUserTradeAnalyses,
  getSleeperRostersCached,
  getSleeperPlayersBulk,
  getSleeperLeagueUsers,
  simulateMatchup
} from '../services/api';

export default function TradeAssistant() {
  const navigate = useNavigate();
  const { sleeperSession, selectedLeague, userRoster } = useSleeper();

  // Redirect if no session
  useEffect(() => {
    if (!sleeperSession || !selectedLeague || !userRoster) {
      navigate('/');
    }
  }, [sleeperSession?.user_id, selectedLeague?.league_id, userRoster?.roster_id, navigate]);

  if (!sleeperSession || !selectedLeague || !userRoster) {
    return null;
  }

  const leagueId = selectedLeague.league_id;
  const sleeperUserId = sleeperSession.user_id;
  const userRosterId = userRoster.roster_id;

  const [step, setStep] = useState(1); // 1: Team Selection, 2: Player Selection, 3: Analyzing, 4: Results
  const [loading, setLoading] = useState(false);
  const [loadingRosters, setLoadingRosters] = useState(false);
  const [error, setError] = useState(null);
  
  // League data
  const [allRosters, setAllRosters] = useState([]);
  const [leagueUsers, setLeagueUsers] = useState([]);
  const [playerDetails, setPlayerDetails] = useState({});
  
  // Form state
  const [selectedOpponentRosters, setSelectedOpponentRosters] = useState([]);
  const [playersOut, setPlayersOut] = useState([]);
  const [playersIn, setPlayersIn] = useState([]);
  
  // Analysis state
  const [sessionId, setSessionId] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [pollingInterval, setPollingInterval] = useState(null);
  
  // Simulation state
  const [simulationLoading, setSimulationLoading] = useState(false);
  const [simulationResult, setSimulationResult] = useState(null);
  
  // Reference data
  const [recentTrades, setRecentTrades] = useState([]);
  const [analysisHistory, setAnalysisHistory] = useState([]);

  // Load rosters and reference data on mount
  useEffect(() => {
    loadLeagueRosters();
    loadRecentTrades();
    loadAnalysisHistory();
  }, [leagueId, sleeperUserId]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      if (pollingInterval) {
        clearInterval(pollingInterval);
      }
    };
  }, [pollingInterval]);

  const loadLeagueRosters = async () => {
    setLoadingRosters(true);
    try {
      // Fetch rosters and users in parallel
      const [rosters, users] = await Promise.all([
        getSleeperRostersCached(leagueId, false),
        getSleeperLeagueUsers(leagueId)
      ]);
      
      setAllRosters(rosters);
      setLeagueUsers(users || []);
      
      // Get all unique player IDs from all rosters
      const allPlayerIds = new Set();
      rosters.forEach(roster => {
        if (roster.players) {
          roster.players.forEach(playerId => allPlayerIds.add(playerId));
        }
      });
      
      // Fetch player details for all players
      if (allPlayerIds.size > 0) {
        const playerData = await getSleeperPlayersBulk(Array.from(allPlayerIds));
        setPlayerDetails(playerData.players || {});
      }
    } catch (err) {
      console.error('Error loading rosters:', err);
      setError('Failed to load league rosters');
    } finally {
      setLoadingRosters(false);
    }
  };

  const loadRecentTrades = async () => {
    try {
      const trades = await getRecentTrades(leagueId, 5);
      setRecentTrades(trades);
    } catch (err) {
      console.error('Error loading recent trades:', err);
    }
  };

  const loadAnalysisHistory = async () => {
    try {
      const history = await getUserTradeAnalyses(sleeperUserId, leagueId, 10);
      setAnalysisHistory(history.sessions || []);
    } catch (err) {
      console.error('Error loading analysis history:', err);
    }
  };

  const getOpponentRosters = () => {
    return allRosters.filter(roster => roster.roster_id !== userRosterId);
  };

  const getRosterDisplayName = (roster) => {
    // Find the user/owner for this roster
    const user = leagueUsers.find(u => u.user_id === roster.owner_id);
    
    if (user) {
      // Priority: team_name > display_name > username
      return user.metadata?.team_name || 
             user.display_name || 
             user.username ||
             `Team ${roster.roster_id}`;
    }
    
    // Fallback to roster metadata or ID
    return roster.metadata?.team_name || 
           roster.display_name || 
           `Team ${roster.roster_id}`;
  };

  const getPlayerName = (playerId) => {
    const player = playerDetails[playerId];
    return player?.name || `Player ${playerId}`;
  };

  const toggleOpponentRoster = (rosterId) => {
    // Allow multiple opponent selection
    setSelectedOpponentRosters(prev => {
      if (prev.includes(rosterId)) {
        return prev.filter(id => id !== rosterId); // Deselect this one
      } else {
        return [...prev, rosterId]; // Add this one to selection
      }
    });
  };

  const handleContinueToPlayers = () => {
    if (selectedOpponentRosters.length === 0) {
      setError('Please select at least one team to trade with');
      return;
    }
    
    // Do NOT pre-populate - let users select manually
    setPlayersOut([]);
    setPlayersIn([]);
    
    setError(null);
    setStep(2);
  };

  const togglePlayerSelection = (playerId, type) => {
    const MAX_PLAYERS_PER_SIDE = 5;
    
    if (type === 'out') {
      setPlayersOut(prev => {
        if (prev.includes(playerId)) {
          return prev.filter(id => id !== playerId);
        } else {
          if (prev.length >= MAX_PLAYERS_PER_SIDE) {
            setError(`Maximum ${MAX_PLAYERS_PER_SIDE} players per side allowed`);
            return prev;
          }
          setError(null);
          return [...prev, playerId];
        }
      });
    } else {
      setPlayersIn(prev => {
        if (prev.includes(playerId)) {
          return prev.filter(id => id !== playerId);
        } else {
          if (prev.length >= MAX_PLAYERS_PER_SIDE) {
            setError(`Maximum ${MAX_PLAYERS_PER_SIDE} players per side allowed`);
            return prev;
          }
          setError(null);
          return [...prev, playerId];
        }
      });
    }
  };

  const handleStartAnalysis = async () => {
    setError(null);
    
    // Validation
    if (playersOut.length === 0 || playersIn.length === 0) {
      setError('Please select at least one player in each section');
      return;
    }

    if (selectedOpponentRosters.length === 0) {
      setError('Please select an opponent team');
      return;
    }

    setLoading(true);
    setStep(3);

    try {
      // Use the first selected opponent roster for analysis
      // Note: Backend currently supports single opponent per analysis
      // Multi-team UI allows selecting players from multiple rosters
      const opponentRosterId = selectedOpponentRosters[0];
      
      const response = await startTradeAnalysis({
        league_id: leagueId,
        sleeper_user_id: sleeperUserId,
        user_roster_id: parseInt(userRosterId),
        opponent_roster_id: parseInt(opponentRosterId),
        user_players_out: playersOut,
        user_players_in: playersIn
      });

      setSessionId(response.session_id);
      
      // Start polling for results
      const interval = setInterval(async () => {
        try {
          const result = await getTradeAnalysisResult(response.session_id);
          
          if (result.status === 'completed' || result.status === 'failed') {
            clearInterval(interval);
            setPollingInterval(null);
            setAnalysisResult(result);
            setStep(4);
            setLoading(false);
          }
        } catch (err) {
          console.error('Polling error:', err);
        }
      }, 2000); // Poll every 2 seconds

      setPollingInterval(interval);
      
    } catch (err) {
      setError(err.message || 'Failed to start analysis');
      setLoading(false);
      setStep(2);
    }
  };

  const handleReset = () => {
    setStep(1);
    setSessionId(null);
    setAnalysisResult(null);
    setSimulationResult(null);
    setError(null);
    setSelectedOpponentRosters([]);
    setPlayersOut([]);
    setPlayersIn([]);
    loadAnalysisHistory();
  };

  const handleRunSimulation = async () => {
    if (!sessionId) {
      setError('No analysis session available');
      return;
    }

    setSimulationLoading(true);
    setError(null);

    try {
      // Start the simulation
      await simulateMatchup(sessionId, 3); // 3 weeks ahead
      
      // Poll for simulation results (runs in background)
      const maxAttempts = 10;
      const pollInterval = 2000; // 2 seconds
      
      for (let attempt = 0; attempt < maxAttempts; attempt++) {
        await new Promise(resolve => setTimeout(resolve, pollInterval));
        
        const updatedAnalysis = await getTradeAnalysisResult(sessionId);
        
        if (updatedAnalysis.simulation_result) {
          setSimulationResult(updatedAnalysis.simulation_result);
          setAnalysisResult(updatedAnalysis);
          break;
        }
        
        // If last attempt, set a message
        if (attempt === maxAttempts - 1) {
          setError('Simulation is taking longer than expected. Please refresh to see results.');
        }
      }
    } catch (err) {
      setError(err.message || 'Failed to run simulation');
    } finally {
      setSimulationLoading(false);
    }
  };

  const getFavorabilityColor = (score) => {
    if (score === null || score === undefined) return 'text-gray-500';
    if (score >= 70) return 'text-green-600';
    if (score >= 55) return 'text-green-500';
    if (score >= 46) return 'text-yellow-500';
    if (score >= 31) return 'text-orange-500';
    return 'text-red-600';
  };

  const getFavorabilityLabel = (score) => {
    if (score === null || score === undefined) return 'Unknown';
    if (score >= 70) return 'Strongly Favorable';
    if (score >= 55) return 'Favorable';
    if (score >= 46) return 'Fair Trade';
    if (score >= 31) return 'Unfavorable';
    return 'Strongly Unfavorable';
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto px-4">
        <div className="bg-white rounded-lg shadow-lg p-6">
          {/* Header */}
          <div className="mb-8">
            <h1 className="text-3xl font-bold text-gray-900 mb-2">
              🤖 AI Trade Assistant
            </h1>
            <p className="text-gray-600">
              Get AI-powered analysis of your proposed trades with detailed insights and recommendations
            </p>
          </div>

          {/* Error Display */}
          {error && (
            <div className="mb-6 bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
              {error}
            </div>
          )}

          {/* Recent Trades Reference - Top of Page */}
          {recentTrades.length > 0 && (
            <div className="mb-8 border border-blue-200 bg-blue-50 rounded-lg p-4">
              <h3 className="text-lg font-semibold text-blue-900 mb-3 flex items-center">
                <span className="mr-2">📊</span>
                Recent Trades in Your League
              </h3>
              <div className="space-y-2">
                {recentTrades.map((trade, idx) => (
                  <div key={idx} className="text-sm text-blue-800 bg-white p-3 rounded">
                    {trade.description}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Step 1: Team Selection */}
          {step === 1 && (
            <div className="space-y-6">
              <div>
                <h2 className="text-xl font-semibold text-gray-900 mb-4">
                  Who are you looking to trade with?
                </h2>
                <p className="text-sm text-gray-600 mb-4">
                  Select one or more teams you'd like to analyze a trade with
                </p>
                
                {loadingRosters ? (
                  <div className="text-center py-8">
                    <div className="inline-block animate-spin rounded-full h-8 w-8 border-4 border-blue-500 border-t-transparent"></div>
                    <p className="text-gray-600 mt-2">Loading teams...</p>
                  </div>
                ) : (
                  <div className="grid md:grid-cols-2 gap-4">
                    {getOpponentRosters().map(roster => (
                      <button
                        key={roster.roster_id}
                        onClick={() => toggleOpponentRoster(roster.roster_id)}
                        className={`p-4 rounded-lg border-2 transition-all text-left ${
                          selectedOpponentRosters.includes(roster.roster_id)
                            ? 'border-blue-500 bg-blue-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <div>
                            <h3 className="font-semibold text-gray-900">
                              {getRosterDisplayName(roster)}
                            </h3>
                            <p className="text-sm text-gray-600">
                              {roster.players?.length || 0} players
                            </p>
                          </div>
                          <div className={`w-6 h-6 rounded-full border-2 flex items-center justify-center ${
                            selectedOpponentRosters.includes(roster.roster_id)
                              ? 'border-blue-500 bg-blue-500'
                              : 'border-gray-300'
                          }`}>
                            {selectedOpponentRosters.includes(roster.roster_id) && (
                              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                              </svg>
                            )}
                          </div>
                        </div>
                      </button>
                    ))}
                  </div>
                )}
              </div>

              <button
                onClick={handleContinueToPlayers}
                disabled={selectedOpponentRosters.length === 0 || loadingRosters}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-medium text-lg"
              >
                Continue to Player Selection
                {selectedOpponentRosters.length > 0 && (
                  <span className="ml-2 text-sm">({selectedOpponentRosters.length} team{selectedOpponentRosters.length > 1 ? 's' : ''} selected)</span>
                )}
              </button>
            </div>
          )}

          {/* Step 2: Player Selection */}
          {step === 2 && (
            <div className="space-y-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-xl font-semibold text-gray-900">
                  Select Players for Trade
                </h2>
                <button
                  onClick={() => setStep(1)}
                  className="text-gray-600 hover:text-gray-900"
                >
                  ← Back to Teams
                </button>
              </div>

              {/* Selected Teams Info */}
              {selectedOpponentRosters.length > 0 && (
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
                  <p className="text-sm text-blue-800">
                    <span className="font-semibold">Trading with: </span>
                    {selectedOpponentRosters.map((rosterId, idx) => {
                      const roster = allRosters.find(r => r.roster_id === rosterId);
                      return (
                        <span key={rosterId}>
                          {idx > 0 && ', '}
                          {getRosterDisplayName(roster)}
                        </span>
                      );
                    })}
                    {selectedOpponentRosters.length > 1 && (
                      <span className="ml-2 text-xs">({selectedOpponentRosters.length} teams)</span>
                    )}
                  </p>
                </div>
              )}

              <div className="grid md:grid-cols-2 gap-6">
                {/* Players Trading Away */}
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900">
                      Players You're Trading Away
                    </h3>
                    {playersOut.length > 0 && (
                      <button
                        onClick={() => setPlayersOut([])}
                        className="text-xs text-red-600 hover:text-red-700 font-medium"
                      >
                        Clear All
                      </button>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Your roster - select players to give up
                  </p>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {(userRoster.players || []).map(playerId => (
                      <button
                        key={playerId}
                        onClick={() => togglePlayerSelection(playerId, 'out')}
                        className={`w-full p-3 rounded border text-left ${
                          playersOut.includes(playerId)
                            ? 'border-red-500 bg-red-50'
                            : 'border-gray-200 hover:border-gray-300'
                        }`}
                      >
                        <div className="flex items-center justify-between">
                          <span className="font-medium text-gray-900">
                            {getPlayerName(playerId)}
                          </span>
                          {playersOut.includes(playerId) && (
                            <span className="text-red-600">✓</span>
                          )}
                        </div>
                      </button>
                    ))}
                  </div>
                  <p className="text-sm text-gray-500 mt-3">
                    Selected: {playersOut.length} players
                  </p>
                </div>

                {/* Players Receiving */}
                <div className="border rounded-lg p-4">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="font-semibold text-gray-900">
                      Players You're Receiving
                    </h3>
                    {playersIn.length > 0 && (
                      <button
                        onClick={() => setPlayersIn([])}
                        className="text-xs text-green-600 hover:text-green-700 font-medium"
                      >
                        Clear All
                      </button>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mb-3">
                    Opponent roster{selectedOpponentRosters.length > 1 ? 's' : ''} - select players to receive
                  </p>
                  <div className="space-y-2 max-h-96 overflow-y-auto">
                    {selectedOpponentRosters.map(rosterId => {
                      const roster = allRosters.find(r => r.roster_id === rosterId);
                      return (
                        <div key={rosterId}>
                          <div className="text-xs font-semibold text-gray-500 mb-2 sticky top-0 bg-white py-1">
                            {getRosterDisplayName(roster)}
                          </div>
                          {(roster?.players || []).map(playerId => (
                            <button
                              key={playerId}
                              onClick={() => togglePlayerSelection(playerId, 'in')}
                              className={`w-full p-3 rounded border text-left mb-2 ${
                                playersIn.includes(playerId)
                                  ? 'border-green-500 bg-green-50'
                                  : 'border-gray-200 hover:border-gray-300'
                              }`}
                            >
                              <div className="flex items-center justify-between">
                                <span className="font-medium text-gray-900">
                                  {getPlayerName(playerId)}
                                </span>
                                {playersIn.includes(playerId) && (
                                  <span className="text-green-600">✓</span>
                                )}
                              </div>
                            </button>
                          ))}
                        </div>
                      );
                    })}
                  </div>
                  <p className="text-sm text-gray-500 mt-3">
                    Selected: {playersIn.length} players
                  </p>
                </div>
              </div>

              <button
                onClick={handleStartAnalysis}
                disabled={loading || playersOut.length === 0 || playersIn.length === 0}
                className="w-full bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 disabled:bg-gray-400 font-medium text-lg"
              >
                {loading ? 'Analyzing...' : 'Analyze Trade'}
              </button>
            </div>
          )}

          {/* Step 3: Analyzing */}
          {step === 3 && (
            <div className="space-y-6">
              <div className="flex justify-end mb-4">
                <button
                  onClick={() => setStep(2)}
                  className="text-gray-600 hover:text-gray-900 flex items-center"
                  disabled={loading}
                >
                  ← Back to Player Selection
                </button>
              </div>
              <div className="text-center py-12">
                <div className="inline-block animate-spin rounded-full h-16 w-16 border-4 border-blue-500 border-t-transparent"></div>
                <h2 className="text-xl font-semibold text-gray-900 mt-4">
                  Analyzing Your Trade...
                </h2>
                <p className="text-gray-600 mt-2">
                  Fetching player stats, league settings, and upcoming schedules
                </p>
                <p className="text-sm text-gray-500 mt-1">
                  This usually takes 10-15 seconds
                </p>
              </div>
            </div>
          )}

          {/* Step 4: Results */}
          {step === 4 && analysisResult && (
            <div className="space-y-6">
              {/* Back and Close buttons */}
              <div className="flex justify-between items-center mb-4">
                <button
                  onClick={() => setStep(2)}
                  className="text-gray-600 hover:text-gray-900 flex items-center"
                >
                  ← Back to Player Selection
                </button>
                <button
                  onClick={() => navigate('/roster')}
                  className="text-gray-600 hover:text-gray-900 flex items-center"
                >
                  ✕ Close
                </button>
              </div>

              {/* Trade Summary */}
              <div className="bg-gray-50 border border-gray-200 rounded-lg p-4">
                <h3 className="font-semibold text-gray-900 mb-3 flex items-center">
                  <span className="mr-2">📋</span>
                  Trade Summary
                </h3>
                <div className="grid md:grid-cols-2 gap-4">
                  {/* Players Trading Away */}
                  <div className="bg-white rounded-lg p-3">
                    <h4 className="text-sm font-medium text-red-700 mb-2">Trading Away</h4>
                    <div className="space-y-1">
                      {playersOut.map(playerId => {
                        const player = playerDetails[playerId];
                        return (
                          <div key={playerId} className="text-sm text-gray-700 flex items-center">
                            <span className="mr-2">→</span>
                            {player?.name || `Player ${playerId}`}
                            {player?.team && <span className="ml-1 text-xs text-gray-500">({player.team})</span>}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Players Receiving */}
                  <div className="bg-white rounded-lg p-3">
                    <h4 className="text-sm font-medium text-green-700 mb-2">Receiving</h4>
                    <div className="space-y-1">
                      {playersIn.map(playerId => {
                        const player = playerDetails[playerId];
                        return (
                          <div key={playerId} className="text-sm text-gray-700 flex items-center">
                            <span className="mr-2">←</span>
                            {player?.name || `Player ${playerId}`}
                            {player?.team && <span className="ml-1 text-xs text-gray-500">({player.team})</span>}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Favorability Score */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg p-6 text-center">
                <div className="text-sm text-gray-600 mb-2">Trade Favorability Score</div>
                <div className={`text-6xl font-bold ${getFavorabilityColor(analysisResult.favorability_score)}`}>
                  {analysisResult.favorability_score !== null ? analysisResult.favorability_score : 'N/A'}
                  <span className="text-2xl">/100</span>
                </div>
                <div className={`text-lg font-medium mt-2 ${getFavorabilityColor(analysisResult.favorability_score)}`}>
                  {getFavorabilityLabel(analysisResult.favorability_score)}
                </div>
              </div>

              {/* Recommendation */}
              {analysisResult.analysis_result?.recommendation && (
                <div className="bg-yellow-50 border-l-4 border-yellow-400 p-4">
                  <div className="flex">
                    <div className="flex-shrink-0">
                      <span className="text-2xl">💡</span>
                    </div>
                    <div className="ml-3">
                      <h3 className="text-sm font-medium text-yellow-800">Recommendation</h3>
                      <p className="mt-1 text-sm text-yellow-700">
                        {analysisResult.analysis_result.recommendation}
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Reasoning */}
              {analysisResult.analysis_result?.reasoning && (
                <div className="bg-blue-50 rounded-lg p-4">
                  <h3 className="font-semibold text-gray-900 mb-2">Analysis Reasoning</h3>
                  <p className="text-gray-700">{analysisResult.analysis_result.reasoning}</p>
                </div>
              )}

              {/* Pros and Cons */}
              <div className="grid md:grid-cols-2 gap-6">
                {/* Pros */}
                <div className="bg-green-50 rounded-lg p-4">
                  <h3 className="font-semibold text-green-900 mb-3 flex items-center">
                    <span className="text-xl mr-2">✅</span>
                    Pros ({analysisResult.analysis_result?.pros?.length || 0})
                  </h3>
                  <ul className="space-y-2">
                    {analysisResult.analysis_result?.pros?.map((pro, idx) => (
                      <li key={idx} className="text-sm text-green-800 flex">
                        <span className="mr-2">•</span>
                        <span>{pro}</span>
                      </li>
                    )) || <li className="text-sm text-green-600 italic">No pros listed</li>}
                  </ul>
                </div>

                {/* Cons */}
                <div className="bg-red-50 rounded-lg p-4">
                  <h3 className="font-semibold text-red-900 mb-3 flex items-center">
                    <span className="text-xl mr-2">❌</span>
                    Cons ({analysisResult.analysis_result?.cons?.length || 0})
                  </h3>
                  <ul className="space-y-2">
                    {analysisResult.analysis_result?.cons?.map((con, idx) => (
                      <li key={idx} className="text-sm text-red-800 flex">
                        <span className="mr-2">•</span>
                        <span>{con}</span>
                      </li>
                    )) || <li className="text-sm text-red-600 italic">No cons listed</li>}
                  </ul>
                </div>
              </div>

              {/* Simulation Section */}
              <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg p-6 border-2 border-purple-200">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h3 className="text-lg font-semibold text-purple-900 flex items-center">
                      <span className="text-2xl mr-2">📊</span>
                      Matchup Simulation
                    </h3>
                    <p className="text-sm text-purple-700 mt-1">
                      See how this trade affects your matchup projections for the next 3 weeks
                    </p>
                  </div>
                  {!simulationResult && !analysisResult.simulation_result && (
                    <button
                      onClick={handleRunSimulation}
                      disabled={simulationLoading}
                      className="bg-purple-600 text-white py-2 px-4 rounded-lg hover:bg-purple-700 disabled:bg-gray-400 font-medium flex items-center"
                    >
                      {simulationLoading ? (
                        <>
                          <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent mr-2"></div>
                          Running...
                        </>
                      ) : (
                        <>
                          <span className="mr-2">▶️</span>
                          Run Simulation
                        </>
                      )}
                    </button>
                  )}
                </div>

                {(simulationResult || analysisResult.simulation_result) && (
                  <div className="space-y-6 mt-4">
                    {/* Week-by-week matchup results */}
                    {((simulationResult || analysisResult.simulation_result)?.weeks || []).map((week, idx) => (
                      <div key={week.week} className="bg-white rounded-lg border-2 border-gray-200 p-4">
                        <div className="flex items-center justify-between mb-4">
                          <h4 className="font-bold text-lg text-gray-900">
                            Week {week.week}
                          </h4>
                          <div className="text-sm text-gray-600">
                            vs <span className="font-semibold">{week.opponent_team_name}</span>
                          </div>
                        </div>
                        
                        <div className="grid md:grid-cols-2 gap-4">
                          {/* Without Trade */}
                          <div className="bg-gray-50 rounded-lg p-4">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium text-gray-700">Without Trade</span>
                              {week.without_trade.wins === 1 ? (
                                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">WIN</span>
                              ) : (
                                <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded">LOSS</span>
                              )}
                            </div>
                            <div className="space-y-1">
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Your Points:</span>
                                <span className="font-semibold text-gray-900">{week.without_trade.projected_points.toFixed(1)}</span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-gray-600">Opponent:</span>
                                <span className="font-semibold text-gray-900">{week.without_trade.opponent_projected_points.toFixed(1)}</span>
                              </div>
                              <div className="flex justify-between text-sm pt-1 border-t border-gray-200">
                                <span className="text-gray-600">Win Prob:</span>
                                <span className="font-semibold text-gray-900">{week.without_trade.win_probability.toFixed(0)}%</span>
                              </div>
                            </div>
                          </div>

                          {/* With Trade */}
                          <div className="bg-purple-50 rounded-lg p-4 border-2 border-purple-200">
                            <div className="flex items-center justify-between mb-2">
                              <span className="text-sm font-medium text-purple-700">With Trade</span>
                              {week.with_trade.wins === 1 ? (
                                <span className="px-2 py-1 bg-green-100 text-green-800 text-xs font-semibold rounded">WIN</span>
                              ) : (
                                <span className="px-2 py-1 bg-red-100 text-red-800 text-xs font-semibold rounded">LOSS</span>
                              )}
                            </div>
                            <div className="space-y-1">
                              <div className="flex justify-between text-sm">
                                <span className="text-purple-600">Your Points:</span>
                                <span className="font-semibold text-purple-900">{week.with_trade.projected_points.toFixed(1)}</span>
                              </div>
                              <div className="flex justify-between text-sm">
                                <span className="text-purple-600">Opponent:</span>
                                <span className="font-semibold text-purple-900">{week.with_trade.opponent_projected_points.toFixed(1)}</span>
                              </div>
                              <div className="flex justify-between text-sm pt-1 border-t border-purple-200">
                                <span className="text-purple-600">Win Prob:</span>
                                <span className="font-semibold text-purple-900">{week.with_trade.win_probability.toFixed(0)}%</span>
                              </div>
                            </div>
                          </div>
                        </div>
                        
                        {/* Point differential for this week */}
                        <div className={`mt-3 p-2 rounded text-center text-sm font-medium ${
                          week.point_differential > 0 
                            ? 'bg-green-50 text-green-700' 
                            : week.point_differential < 0
                            ? 'bg-red-50 text-red-700'
                            : 'bg-gray-50 text-gray-700'
                        }`}>
                          {week.point_differential > 0 ? '+' : ''}{week.point_differential.toFixed(1)} points with trade
                        </div>
                      </div>
                    ))}

                    {/* Summary Section */}
                    {(simulationResult || analysisResult.simulation_result)?.summary && (
                      <div className="bg-gradient-to-r from-purple-50 to-blue-50 rounded-lg border-2 border-purple-300 p-6">
                        <h4 className="font-bold text-xl text-gray-900 mb-4 text-center">
                          📊 Simulation Summary
                        </h4>
                        
                        <div className="grid md:grid-cols-3 gap-4 mb-4">
                          <div className="bg-white rounded-lg p-4 text-center">
                            <div className="text-sm text-gray-600 mb-1 font-medium">Without Trade</div>
                            <div className="text-2xl font-bold text-green-600">
                              {(simulationResult || analysisResult.simulation_result).summary.total_wins_without}W
                            </div>
                            <div className="text-2xl font-bold text-red-600">
                              {(simulationResult || analysisResult.simulation_result).summary.total_losses_without}L
                            </div>
                            <div className="text-xs text-gray-500 mt-1">
                              {(simulationResult || analysisResult.simulation_result).summary.total_wins_without}-
                              {(simulationResult || analysisResult.simulation_result).summary.total_losses_without} record
                            </div>
                          </div>
                          
                          <div className="bg-white rounded-lg p-4 text-center border-2 border-purple-300">
                            <div className="text-sm text-purple-600 mb-1 font-medium">With Trade</div>
                            <div className="text-2xl font-bold text-green-600">
                              {(simulationResult || analysisResult.simulation_result).summary.total_wins_with}W
                            </div>
                            <div className="text-2xl font-bold text-red-600">
                              {(simulationResult || analysisResult.simulation_result).summary.total_losses_with}L
                            </div>
                            <div className="text-xs text-purple-500 mt-1">
                              {(simulationResult || analysisResult.simulation_result).summary.total_wins_with}-
                              {(simulationResult || analysisResult.simulation_result).summary.total_losses_with} record
                            </div>
                          </div>
                          
                          <div className={`bg-white rounded-lg p-4 text-center ${
                            (simulationResult || analysisResult.simulation_result).summary.wins_improvement > 0 
                              ? 'border-2 border-green-400' 
                              : (simulationResult || analysisResult.simulation_result).summary.wins_improvement < 0
                              ? 'border-2 border-red-400'
                              : ''
                          }`}>
                            <div className="text-sm text-gray-600 mb-1">Impact</div>
                            <div className={`text-3xl font-bold ${
                              (simulationResult || analysisResult.simulation_result).summary.wins_improvement > 0 
                                ? 'text-green-600' 
                                : (simulationResult || analysisResult.simulation_result).summary.wins_improvement < 0
                                ? 'text-red-600'
                                : 'text-gray-600'
                            }`}>
                              {(simulationResult || analysisResult.simulation_result).summary.wins_improvement > 0 ? '+' : ''}
                              {(simulationResult || analysisResult.simulation_result).summary.wins_improvement}
                            </div>
                            <div className="text-sm text-gray-500">
                              {(simulationResult || analysisResult.simulation_result).summary.wins_improvement > 0 
                                ? 'more wins' 
                                : (simulationResult || analysisResult.simulation_result).summary.wins_improvement < 0
                                ? 'fewer wins'
                                : 'same wins'}
                            </div>
                          </div>
                        </div>
                        
                        <div className={`text-center text-lg font-semibold p-3 rounded ${
                          (simulationResult || analysisResult.simulation_result).summary.wins_improvement > 0 
                            ? 'bg-green-100 text-green-800' 
                            : (simulationResult || analysisResult.simulation_result).summary.wins_improvement < 0
                            ? 'bg-red-100 text-red-800'
                            : 'bg-gray-100 text-gray-800'
                        }`}>
                          {(simulationResult || analysisResult.simulation_result).summary.wins_improvement > 0 
                            ? `✓ Trade improves your record by ${(simulationResult || analysisResult.simulation_result).summary.wins_improvement} win${(simulationResult || analysisResult.simulation_result).summary.wins_improvement > 1 ? 's' : ''}` 
                            : (simulationResult || analysisResult.simulation_result).summary.wins_improvement < 0
                            ? `✗ Trade costs you ${Math.abs((simulationResult || analysisResult.simulation_result).summary.wins_improvement)} win${Math.abs((simulationResult || analysisResult.simulation_result).summary.wins_improvement) > 1 ? 's' : ''}`
                            : '→ Trade has neutral impact on wins'}
                        </div>
                      </div>
                    )}

                    {/* Disclaimer */}
                    {(simulationResult || analysisResult.simulation_result)?.disclaimer && (
                      <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
                        <div className="flex items-start">
                          <span className="text-amber-600 mr-2 mt-0.5">⚠️</span>
                          <div>
                            <h4 className="font-semibold text-amber-900 mb-1">Data Notice</h4>
                            <p className="text-sm text-amber-800">
                              {(simulationResult || analysisResult.simulation_result).disclaimer}
                            </p>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {!simulationResult && !analysisResult.simulation_result && !simulationLoading && (
                  <p className="text-purple-700 text-center py-4">
                    Click "Run Simulation" to see projected matchup outcomes
                  </p>
                )}
              </div>

              {/* Actions */}
              <div className="flex gap-4">
                <button
                  onClick={handleReset}
                  className="flex-1 bg-gray-200 text-gray-800 py-3 px-6 rounded-lg hover:bg-gray-300 font-medium"
                >
                  Analyze Another Trade
                </button>
                <button
                  onClick={() => window.print()}
                  className="bg-blue-600 text-white py-3 px-6 rounded-lg hover:bg-blue-700 font-medium"
                >
                  📄 Save/Print
                </button>
              </div>

              {/* Metadata */}
              <div className="text-xs text-gray-500 text-center pt-4 border-t">
                Analysis completed at {new Date(analysisResult.completed_at || analysisResult.created_at).toLocaleString()}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
