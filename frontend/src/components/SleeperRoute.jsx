import React from 'react'
import { Navigate } from 'react-router-dom'
import { useSleeper } from '../contexts/SleeperContext'
import LoadingSpinner from './LoadingSpinner'

const SleeperRoute = ({ children }) => {
  const { sleeperSession, loading } = useSleeper()

  // Show loading spinner while checking session
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <LoadingSpinner size="lg" />
      </div>
    )
  }

  // Redirect to username input if no session
  if (!sleeperSession) {
    return <Navigate to="/" replace />
  }

  // Render children if session exists
  return children
}

export default SleeperRoute