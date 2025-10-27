import React, { useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useSleeper } from '../contexts/SleeperContext'

function Header() {
  const location = useLocation()
  const { sleeperSession, clearSession } = useSleeper()
  const [showUserMenu, setShowUserMenu] = useState(false)

  return (
    <header className="sticky top-0 z-50 bg-gradient-to-r from-primary-600 to-court shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo Section */}
          <div className="flex items-center space-x-3">
            <div className="text-3xl">🏀</div>
            <div>
              <h1 className="text-xl font-bold text-white">Fantasy Basketball League AI Assistant</h1>
              <p className="text-sm text-blue-100">AI-Powered Trade Manager</p>
            </div>
          </div>

          {/* Navigation Section */}
          <nav className="hidden md:flex items-center space-x-6">
            {sleeperSession ? (
              <>
                <Link 
                  to="/leagues"
                  className={`px-4 py-2 rounded-lg transition duration-200 ${
                    location.pathname === '/leagues' 
                      ? 'bg-white text-primary-600 font-medium'
                      : 'text-blue-100 hover:text-white hover:bg-white hover:bg-opacity-10'
                  }`}
                >
                  My Leagues
                </Link>
                
                <Link 
                  to="/roster"
                  className={`px-4 py-2 rounded-lg transition duration-200 ${
                    location.pathname === '/roster' 
                      ? 'bg-white text-primary-600 font-medium'
                      : 'text-blue-100 hover:text-white hover:bg-white hover:bg-opacity-10'
                  }`}
                >
                  My Roster
                </Link>
                
                {/* User Menu */}
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className="flex items-center space-x-2 px-4 py-2 rounded-lg text-blue-100 hover:text-white hover:bg-white hover:bg-opacity-10 transition duration-200"
                  >
                    <span className="text-sm">🎮</span>
                    <span className="text-sm">{sleeperSession.display_name || sleeperSession.username}</span>
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>
                  
                  {showUserMenu && (
                    <div className="absolute right-0 mt-2 w-48 bg-white rounded-lg shadow-lg py-2 z-50">
                      <div className="px-4 py-2 text-sm text-gray-600 border-b">
                        <span className="text-green-600">🎮 {sleeperSession.username}</span>
                      </div>
                      <button
                        onClick={() => {
                          clearSession()
                          setShowUserMenu(false)
                        }}
                        className="block w-full text-left px-4 py-2 text-sm text-gray-700 hover:bg-gray-100 transition duration-200"
                      >
                        Change User
                      </button>
                    </div>
                  )}
                </div>
              </>
            ) : (
              <>
                <Link 
                  to="/"
                  className="px-4 py-2 rounded-lg bg-white text-primary-600 font-medium hover:bg-gray-100 transition duration-200"
                >
                  Get Started
                </Link>
              </>
            )}
            
            <div className="text-blue-100 text-sm">
              🤖 Powered by AutoGen AI Agents
            </div>
          </nav>

          {/* Mobile Menu */}
          <div className="md:hidden">
            {sleeperSession ? (
              <button
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="text-white p-2"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </button>
            ) : (
              <Link 
                to="/"
                className="text-white p-2"
              >
                <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 16l-4-4m0 0l4-4m-4 4h14m-5 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h7a3 3 0 013 3v1" />
                </svg>
              </Link>
            )}
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header