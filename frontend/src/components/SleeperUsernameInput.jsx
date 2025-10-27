import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useSleeper } from '../contexts/SleeperContext'
import ErrorMessage from './ErrorMessage'
import LoadingSpinner from './LoadingSpinner'

const SleeperUsernameInput = () => {
  const navigate = useNavigate()
  const { startSession, loading, error, clearError } = useSleeper()
  
  const [username, setUsername] = useState('')
  const [localError, setLocalError] = useState('')

  const handleSubmit = async (e) => {
    e.preventDefault()
    
    if (!username.trim()) {
      setLocalError('Please enter your Sleeper username')
      return
    }

    // Clear any existing errors
    clearError()
    setLocalError('')

    try {
      await startSession(username.trim())
      navigate('/leagues')
    } catch (err) {
      // Error is handled by context, but we can show local feedback too
      setLocalError('Username not found. Please check your Sleeper username and try again.')
    }
  }

  const displayError = error || localError

  return (
    <div className="min-h-screen bg-gradient-to-br from-orange-400 via-red-500 to-purple-600 flex items-center justify-center p-4">
      <div className="max-w-md w-full">
        <div className="card bg-white shadow-2xl">
          <div className="card-body p-8">
            {/* Header */}
            <div className="text-center mb-8">
              <div className="w-16 h-16 bg-gradient-to-r from-orange-500 to-red-500 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-2xl">🏀</span>
              </div>
              <h1 className="text-3xl font-bold text-gray-900 mb-2">
                Fantasy Basketball League AI Assistant
              </h1>
              <p className="text-gray-600">
                Enter your Sleeper username to view your fantasy leagues and rosters
              </p>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="username" className="block text-sm font-medium text-gray-700 mb-2">
                  Sleeper Username
                </label>
                <input
                  type="text"
                  id="username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Enter your Sleeper username"
                  className="input-field"
                  disabled={loading}
                  autoFocus
                />
              </div>

              {/* Error Message */}
              {displayError && (
                <ErrorMessage message={displayError} />
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={loading || !username.trim()}
                className="btn-primary w-full"
              >
                {loading ? (
                  <div className="flex items-center justify-center">
                    <LoadingSpinner size="sm" />
                    <span className="ml-2">Checking username...</span>
                  </div>
                ) : (
                  'Get My Leagues'
                )}
              </button>
            </form>

            {/* Help Text */}
            <div className="mt-6 pt-6 border-t border-gray-200">
              <p className="text-sm text-gray-500 text-center">
                Don't have a Sleeper account?{' '}
                <a
                  href="https://sleeper.app"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-blue-600 hover:text-blue-800 underline"
                >
                  Create one on Sleeper.app
                </a>
              </p>
              <p className="text-xs text-gray-400 text-center mt-2">
                Your username is what appears in your Sleeper profile, not your email address
              </p>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="mt-8 text-center text-white">
          <h3 className="text-lg font-semibold mb-4">What you can do:</h3>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 text-sm">
            <div className="bg-white bg-opacity-20 rounded-lg p-3">
              <div className="text-2xl mb-2">🏆</div>
              <div>View Your Leagues</div>
            </div>
            <div className="bg-white bg-opacity-20 rounded-lg p-3">
              <div className="text-2xl mb-2">👥</div>
              <div>See Team Rosters</div>
            </div>
            <div className="bg-white bg-opacity-20 rounded-lg p-3">
              <div className="text-2xl mb-2">🔄</div>
              <div>Start Trade Talks</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

export default SleeperUsernameInput