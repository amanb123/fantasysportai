import React, { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSleeper } from '../contexts/SleeperContext'
import LoadingSpinner from './LoadingSpinner'
import ErrorMessage from './ErrorMessage'

const LeagueSelection = () => {
  const navigate = useNavigate()
  const { 
    sleeperSession, 
    selectLeague, 
    clearSession, 
    fetchLeagues, 
    loading, 
    error,
    clearError
  } = useSleeper()
  
  const [leagues, setLeagues] = useState([])
  const [isLoadingLeagues, setIsLoadingLeagues] = useState(true) // Local loading state
  const [hasAttemptedFetch, setHasAttemptedFetch] = useState(false) // Track if we've tried fetching
  const hasFetchedRef = useRef(false) // Track if we've already fetched leagues
  const userIdRef = useRef(null) // Store the user ID we're currently viewing

  // Redirect if no session
  useEffect(() => {
    if (!sleeperSession) {
      navigate('/')
      return
    }
  }, [sleeperSession?.user_id, navigate])

  // Fetch leagues ONLY ONCE when component mounts with a session
  useEffect(() => {
    const loadLeagues = async () => {
      // Check if we have a session
      if (!sleeperSession) {
        console.log('LeagueSelection: No sleeperSession found')
        setIsLoadingLeagues(false)
        setHasAttemptedFetch(true)
        return
      }
      
      const currentUserId = sleeperSession.user_id
      
      // Check if we've already fetched for this exact user
      if (hasFetchedRef.current && userIdRef.current === currentUserId) {
        console.log('LeagueSelection: Already fetched - SKIPPING')
        setIsLoadingLeagues(false)
        setHasAttemptedFetch(true)
        return
      }
      
      // Mark as fetching for this user
      hasFetchedRef.current = true
      userIdRef.current = currentUserId
      setIsLoadingLeagues(true)
      
      console.log('LeagueSelection: FETCHING leagues for user:', currentUserId)
      
      try {
        // Start both the API call and a minimum delay timer
        const [userLeagues] = await Promise.all([
          fetchLeagues(),
          new Promise(resolve => setTimeout(resolve, 800)) // Minimum 800ms loading time
        ])
        console.log('LeagueSelection: Successfully fetched', userLeagues.length, 'leagues')
        setLeagues(userLeagues)
      } catch (err) {
        console.error('LeagueSelection: Failed to fetch leagues:', err)
        // Reset on error so we can retry
        hasFetchedRef.current = false
        userIdRef.current = null
      } finally {
        setIsLoadingLeagues(false)
        setHasAttemptedFetch(true)
      }
    }

    loadLeagues()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []) // Empty deps - only run on mount

  const handleLeagueSelect = async (league) => {
    try {
      await selectLeague(league)
      navigate('/roster')
    } catch (err) {
      console.error('Failed to select league:', err)
    }
  }

  const handleChangeUser = () => {
    clearSession()
    navigate('/')
  }

  const handleRetry = () => {
    clearError()
    hasFetchedRef.current = false // Reset fetch flag
    setIsLoadingLeagues(true)
    setHasAttemptedFetch(false)
    if (sleeperSession) {
      Promise.all([
        fetchLeagues(),
        new Promise(resolve => setTimeout(resolve, 800)) // Minimum 800ms loading time
      ])
        .then(([leagues]) => setLeagues(leagues))
        .catch(console.error)
        .finally(() => {
          setIsLoadingLeagues(false)
          setHasAttemptedFetch(true)
        })
    }
  }

  if (!sleeperSession) {
    return <LoadingSpinner />
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-purple-600 p-4">
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-lg p-6 mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Your Fantasy Leagues
              </h1>
              <p className="text-gray-600">
                Welcome, <span className="font-semibold">{sleeperSession.display_name || sleeperSession.username}</span>
              </p>
            </div>
            <button
              onClick={handleChangeUser}
              className="btn-secondary"
            >
              Change User
            </button>
          </div>
        </div>

        {/* Loading State */}
        {(loading || isLoadingLeagues) && (
          <div className="bg-white rounded-lg shadow-lg p-12">
            <div className="text-center">
              <LoadingSpinner size="lg" />
              <p className="text-gray-600 mt-4">Loading your leagues...</p>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && !loading && !isLoadingLeagues && (
          <div className="bg-white rounded-lg shadow-lg p-6">
            <ErrorMessage message={error} />
            <div className="text-center mt-4">
              <button onClick={handleRetry} className="btn-primary">
                Try Again
              </button>
            </div>
          </div>
        )}

        {/* Empty State */}
        {!loading && !isLoadingLeagues && !error && hasAttemptedFetch && leagues.length === 0 && (
                      <div className="text-center py-12">
              <p className="text-gray-400 text-lg mb-2">No Leagues Found</p>
              <p className="text-gray-500">You don't have any NBA fantasy leagues on Sleeper for the current or past two seasons.</p>
              <p className="text-gray-500 text-sm mt-4">
                Make sure you've connected your Sleeper account and have active leagues.
              </p>
            </div>
        )}

        {/* Leagues Grid */}
        {!loading && !isLoadingLeagues && !error && leagues.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {leagues.map((league) => (
              <div
                key={league.league_id}
                onClick={() => handleLeagueSelect(league)}
                className="bg-white rounded-lg shadow-lg p-6 cursor-pointer hover:shadow-xl transform hover:scale-105 transition-all duration-200"
              >
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <h3 className="text-xl font-semibold text-gray-900 mb-2 line-clamp-2">
                      {league.name}
                    </h3>
                    <div className="space-y-1 text-sm text-gray-600">
                      <p>Season: {league.season}</p>
                      <p>Teams: {league.total_rosters}</p>
                      {league.status && (
                        <p>Status: <span className="capitalize">{league.status}</span></p>
                      )}
                    </div>
                  </div>
                  <div className="w-12 h-12 bg-gradient-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center flex-shrink-0">
                    <span className="text-white text-xl">🏀</span>
                  </div>
                </div>

                <div className="flex items-center justify-between">
                  <div className="text-xs text-gray-500">
                    Click to view roster
                  </div>
                  <div className="text-orange-600">
                    <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                    </svg>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Footer */}
        <div className="text-center mt-8 text-white text-sm">
          <p>
            Data from{' '}
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

export default LeagueSelection