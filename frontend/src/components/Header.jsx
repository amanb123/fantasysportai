import React from 'react'
import { Link, useLocation } from 'react-router-dom'

function Header() {
  const location = useLocation()

  return (
    <header className="sticky top-0 z-50 bg-gradient-to-r from-primary-600 to-court shadow-lg">
      <div className="container mx-auto px-4 py-4">
        <div className="flex items-center justify-between">
          {/* Logo Section */}
          <div className="flex items-center space-x-3">
            <div className="text-3xl">🏀</div>
            <div>
              <h1 className="text-xl font-bold text-white">Fantasy Basketball League</h1>
              <p className="text-sm text-blue-100">AI-Powered Trade Manager</p>
            </div>
          </div>

          {/* Navigation Section */}
          <nav className="hidden md:flex items-center space-x-6">
            <Link 
              to="/"
              className={`px-4 py-2 rounded-lg transition duration-200 ${
                location.pathname === '/' 
                  ? 'bg-white text-primary-600 font-medium'
                  : 'text-blue-100 hover:text-white hover:bg-white hover:bg-opacity-10'
              }`}
            >
              Start Trade
            </Link>
            <div className="text-blue-100 text-sm">
              🤖 Powered by AutoGen AI Agents
            </div>
          </nav>

          {/* Mobile Menu (placeholder for future implementation) */}
          <div className="md:hidden">
            <button className="text-white p-2">
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              </svg>
            </button>
          </div>
        </div>
      </div>
    </header>
  )
}

export default Header