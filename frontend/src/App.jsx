import React from 'react'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import Header from './components/Header.jsx'
import TradePreferenceForm from './components/TradePreferenceForm.jsx'
import TradeNegotiationView from './components/TradeNegotiationView.jsx'
import TradeResultView from './components/TradeResultView.jsx'

function App() {
  return (
    <BrowserRouter>
      <div className="min-h-screen bg-gray-50">
        <Header />
        <main className="container mx-auto px-4 py-8 max-w-7xl">
          <Routes>
            <Route path="/" element={<TradePreferenceForm />} />
            <Route path="/negotiation/:sessionId" element={<TradeNegotiationView />} />
            <Route path="/result/:sessionId" element={<TradeResultView />} />
          </Routes>
        </main>
      </div>
    </BrowserRouter>
  )
}

export default App