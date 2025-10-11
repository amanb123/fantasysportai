# Fantasy Basketball League Frontend

A React + Vite + Tailwind CSS frontend for AI-powered fantasy basketball trade negotiations using multi-agent systems.

## Project Description

The Fantasy Basketball League frontend provides an intuitive interface for users to initiate and monitor AI-powered trade negotiations between fantasy basketball teams. Built with React 18 and powered by AutoGen AI agents on the backend, this application enables users to set trade preferences and watch as intelligent agents negotiate optimal trades in real-time.

## Prerequisites

- Node.js 18+ 
- npm or yarn
- Running Fantasy Basketball League backend server

## Setup Instructions

1. **Install dependencies:**
   ```bash
   npm install
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env to configure API URLs
   ```

3. **Start development server:**
   ```bash
   npm run dev
   ```
   The application will start on http://localhost:3000

## Available Scripts

- `npm run dev` - Start development server with HMR on port 3000
- `npm run build` - Create production build in dist/
- `npm run preview` - Preview production build locally
- `npm run lint` - Run ESLint to check code quality

## Project Structure

```
src/
├── components/          # React components
│   ├── Header.jsx       # Navigation header
│   ├── TradePreferenceForm.jsx    # Team selection & preferences
│   ├── TradeNegotiationView.jsx   # Real-time negotiation monitor
│   ├── TradeResultView.jsx        # Final results display
│   ├── TeamRoster.jsx             # Team roster with player stats
│   ├── ConversationHistory.jsx    # Agent message display
│   ├── LoadingSpinner.jsx         # Loading states
│   └── ErrorMessage.jsx           # Error handling
├── services/            # API and WebSocket services
│   ├── api.js          # HTTP client for REST API
│   └── websocket.js    # Real-time WebSocket connection
├── App.jsx             # Main application router
├── main.jsx            # React entry point
└── index.css           # Global styles with Tailwind
```

## Key Features

### Trade Preference Form
- **Team Selection**: Choose from available fantasy teams with roster overview
- **Team Roster Display**: View players with positions, salaries, and statistics
- **Trade Preferences**: Set focus areas (rebounding, assists, scoring, turnovers)
- **Additional Notes**: Specify custom trade requirements

### Real-Time Negotiation Monitoring  
- **WebSocket Connection**: Live updates during agent negotiations
- **Fallback Polling**: Automatic fallback when WebSocket fails
- **Connection Status**: Visual indicators for connection health
- **Message Streaming**: Real-time agent conversation display

### Conversation History
- **Agent Messages**: Color-coded messages from team agents and commissioner
- **Auto-scrolling**: Smooth scrolling to latest messages
- **Timestamp Display**: Precise timing for each agent response
- **Animation Effects**: Smooth message transitions

### Responsive Design
- **Mobile Optimized**: Tailwind CSS responsive design
- **Basketball Theme**: Custom color palette for basketball branding
- **Accessibility**: Proper focus states and semantic HTML

## Environment Variables

Create a `.env` file based on `.env.example`:

```bash
# API Configuration
VITE_API_BASE_URL=http://localhost:8000    # Backend API URL
VITE_WS_BASE_URL=ws://localhost:8000       # WebSocket URL

# Polling Configuration  
VITE_POLLING_INTERVAL=2000                 # Fallback polling interval (ms)
```

### Production Configuration
For production deployment:
```bash
VITE_API_BASE_URL=https://your-backend-domain.com
VITE_WS_BASE_URL=wss://your-backend-domain.com
```

## Tech Stack

- **React 18** - Modern React with hooks and concurrent features
- **Vite 5** - Fast build tool with HMR and optimized builds  
- **Tailwind CSS 3** - Utility-first CSS framework
- **React Router 6** - Client-side routing
- **Axios** - HTTP client for API calls
- **WebSocket API** - Real-time communication

## Development Notes

- **Hot Module Replacement (HMR)** enabled for fast development
- **ESLint** configured with React-specific rules
- **Production builds** include sourcemaps for debugging
- **TypeScript support** available via @types packages

## Integration with Backend

This frontend integrates with the Fantasy Basketball League backend:

### API Endpoints
- `GET /api/teams` - Fetch all teams
- `GET /api/teams/{id}/players` - Get team roster
- `POST /api/trade/start` - Initiate trade negotiation  
- `GET /api/trade/status/{sessionId}` - Check negotiation status
- `GET /api/trade/result/{sessionId}` - Get final results

### WebSocket Connection
- `WS /ws/trade/{sessionId}` - Real-time negotiation updates
- Message types: `agent_message`, `status_update`, `completion`
- Automatic reconnection with exponential backoff

### Data Models
- **TeamResponse**: Team info with salary totals
- **PlayerResponse**: Player data with stats
- **TradeDecision**: Final negotiation outcome
- **AgentMessage**: Real-time conversation messages

## Getting Started

1. Ensure the Fantasy Basketball League backend is running
2. Follow setup instructions above  
3. Navigate to http://localhost:3000
4. Select a team and set trade preferences
5. Watch AI agents negotiate in real-time!

For backend setup, see the main project README.