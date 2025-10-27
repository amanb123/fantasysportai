import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import ErrorMessage from './ErrorMessage'

const LinkSleeper = () => {
  const { linkSleeper, user } = useAuth()
  const navigate = useNavigate()
  const [sleeperUsername, setSleeperUsername] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState(false)
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setIsLoading(true)
    setError('')
    setSuccess(false)

    const result = await linkSleeper(sleeperUsername)
    
    if (result.success) {
      setSuccess(true)
      // Navigate to home after a brief delay
      setTimeout(() => {
        navigate('/')
      }, 2000)
    } else {
      setError(result.error)
    }
    
    setIsLoading(false)
  }

  const handleSkip = () => {
    navigate('/')
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 to-orange-100 px-4">
      <div className="card w-full max-w-md">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🏀 Fantasy League
          </h1>
          <h2 className="text-xl font-semibold text-orange-600 mb-2">Link Your Sleeper Account</h2>
          <p className="text-gray-600 text-sm leading-relaxed">
            Connect your Sleeper account to import your fantasy teams and enhance your trading experience.
          </p>
        </div>

        {!success ? (
          <>
            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-6">
              <div className="flex items-start">
                <div className="flex-shrink-0">
                  <svg className="h-5 w-5 text-blue-400 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                    <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                  </svg>
                </div>
                <div className="ml-3">
                  <h3 className="text-sm font-medium text-blue-800">About Sleeper Integration</h3>
                  <div className="mt-2 text-sm text-blue-700">
                    <p>Sleeper is a popular fantasy sports platform. By linking your account, you can:</p>
                    <ul className="list-disc list-inside mt-2 space-y-1">
                      <li>Import your existing fantasy teams</li>
                      <li>Access player data and statistics</li>
                      <li>Enhance trade negotiations</li>
                    </ul>
                    <p className="mt-2">
                      Don't have a Sleeper account?{' '}
                      <a 
                        href="https://sleeper.app" 
                        target="_blank" 
                        rel="noopener noreferrer"
                        className="font-medium text-blue-800 hover:text-blue-900 underline"
                      >
                        Create one here
                      </a>
                    </p>
                  </div>
                </div>
              </div>
            </div>

            <form onSubmit={handleSubmit} className="space-y-6">
              <div>
                <label htmlFor="sleeperUsername" className="block text-sm font-medium text-gray-700 mb-2">
                  Sleeper Username
                </label>
                <input
                  type="text"
                  id="sleeperUsername"
                  name="sleeperUsername"
                  value={sleeperUsername}
                  onChange={(e) => {
                    setSleeperUsername(e.target.value)
                    if (error) setError('')
                  }}
                  className="input-field"
                  placeholder="Enter your Sleeper username"
                />
                <p className="text-xs text-gray-500 mt-1">
                  Your Sleeper username, not your display name or email
                </p>
              </div>

              {error && <ErrorMessage message={error} />}

              <button
                type="submit"
                disabled={isLoading || !sleeperUsername.trim()}
                className="btn-primary w-full"
              >
                {isLoading ? (
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                    Linking Account...
                  </div>
                ) : (
                  'Link Sleeper Account'
                )}
              </button>
            </form>

            <div className="mt-6 text-center">
              <button 
                onClick={handleSkip}
                className="text-sm text-gray-600 hover:text-gray-700 transition-colors underline"
              >
                Skip for now
              </button>
            </div>
          </>
        ) : (
          <div className="text-center">
            <div className="w-16 h-16 mx-auto mb-4 bg-green-100 rounded-full flex items-center justify-center">
              <svg className="w-8 h-8 text-green-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7"></path>
              </svg>
            </div>
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Account Successfully Linked!</h3>
            <p className="text-gray-600 mb-4">
              Your Sleeper account has been connected. Redirecting you to the dashboard...
            </p>
            <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-orange-600 mx-auto"></div>
          </div>
        )}
      </div>
    </div>
  )
}

export default LinkSleeper