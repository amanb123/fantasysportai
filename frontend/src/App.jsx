import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { SleeperProvider, useSleeper } from './contexts/SleeperContext'
import Header from './components/Header.jsx'
import TradeNegotiationView from './components/TradeNegotiationView.jsx'
import TradeResultView from './components/TradeResultView.jsx'
import SleeperUsernameInput from './components/SleeperUsernameInput.jsx'
import LeagueSelection from './components/LeagueSelection.jsx'
import RosterDisplay from './components/RosterDisplay.jsx'
import RosterChat from './components/RosterChat.jsx'
import TradeAssistant from './components/TradeAssistant.jsx'
import SleeperRoute from './components/SleeperRoute.jsx'
import UnderConstruction from './components/UnderConstruction.jsx'

// Component to handle Sleeper-based routing
const AppRoutes = () => {
  const { loading } = useSleeper()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-orange-50 to-orange-100">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-orange-600"></div>
      </div>
    )
  }

  return (
    <Routes>
      {/* Public home route - username input */}
      <Route path="/" element={<SleeperUsernameInput />} />

      {/* Sleeper session required routes */}
      <Route 
        path="/leagues" 
        element={
          <SleeperRoute>
            <LeagueSelection />
          </SleeperRoute>
        } 
      />
      <Route 
        path="/roster" 
        element={
          <SleeperRoute>
            <RosterDisplay />
          </SleeperRoute>
        } 
      />
      <Route 
        path="/roster/chat" 
        element={
          <SleeperRoute>
            <RosterChat />
          </SleeperRoute>
        } 
      />
      <Route 
        path="/roster/chat/:sessionId" 
        element={
          <SleeperRoute>
            <RosterChat />
          </SleeperRoute>
        } 
      />
      <Route 
        path="/trade-assistant" 
        element={
          <SleeperRoute>
            <TradeAssistant />
          </SleeperRoute>
        } 
      />

      {/* Trade routes (can work with or without auth) */}
      <Route 
        path="/negotiation/:sessionId" 
        element={
          <div className="min-h-screen bg-gray-50">
            <Header />
            <main className="container mx-auto px-4 py-8 max-w-7xl">
              <TradeNegotiationView />
            </main>
          </div>
        } 
      />
      <Route 
        path="/result/:sessionId" 
        element={
          <div className="min-h-screen bg-gray-50">
            <Header />
            <main className="container mx-auto px-4 py-8 max-w-7xl">
              <TradeResultView />
            </main>
          </div>
        } 
      />

      {/* Under Construction page */}
      <Route path="/under-construction" element={<UnderConstruction />} />

      {/* Default redirect */}
      <Route 
        path="*" 
        element={<Navigate to="/" replace />} 
      />
    </Routes>
  )
}

function App() {
  return (
    <BrowserRouter>
      <SleeperProvider>
        <AppRoutes />
      </SleeperProvider>
    </BrowserRouter>
  )
}

export default App