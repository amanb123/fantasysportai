"""
FastAPI application for the Fantasy Basketball League API.
"""

import logging
from datetime import datetime
from typing import List
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, WebSocket, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.config import settings
from backend.session.database import init_database, get_repository
from backend.session.repository import BasketballRepository
from backend.session.models import TeamModel, PlayerModel
from backend.api_models import ErrorResponse, TeamListResponse, PlayerListResponse, HealthResponse, TradeStartRequest, TradeStartResponse, TradeNegotiationStatus, TradeResultResponse
from shared.models import TeamResponse, PlayerResponse, TradePreferenceRequest, AgentMessage
from backend.session_manager import TradeSessionManager
from backend.websocket_manager import connection_manager, handle_websocket_connection

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup and shutdown events."""
    
    # Startup
    logger.info("🏀 Starting Fantasy Basketball League API")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Log Level: {settings.log_level}")
    logger.info(f"API Port: {settings.api_port}")
    logger.info(f"Database: {settings.database_url[:50]}...")
    
    try:
        # Initialize database
        logger.info("Initializing database connection...")
        init_database(settings.get_database_url(), settings.database_echo)
        
        # Test repository connection
        repository = get_repository()
        logger.info("Database connection established successfully")
        
        # Initialize trade session manager
        global trade_session_manager
        trade_session_manager = TradeSessionManager(repository)
        logger.info("Trade session manager initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Fantasy Basketball League API")
    logger.info("✅ Shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="Fantasy Basketball League API",
    version="1.0.0",
    description="Multi-agent fantasy basketball trade manager with AI-powered negotiations",
    docs_url="/docs",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_basketball_repository() -> BasketballRepository:
    """Dependency to get the basketball repository."""
    return get_repository()


# Initialize trade session manager
trade_session_manager = None

def get_trade_session_manager() -> TradeSessionManager:
    """Dependency to get the trade session manager."""
    global trade_session_manager
    if trade_session_manager is None:
        repository = get_repository()
        trade_session_manager = TradeSessionManager(repository)
    return trade_session_manager


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Fantasy Basketball League API",
        "version": "1.0.0",
        "description": "Multi-agent fantasy basketball trade manager",
        "endpoints": {
            "health": "/health",
            "docs": "/docs",
            "teams": "/api/teams",
            "team_players": "/api/teams/{team_id}/players"
        },
        "timestamp": datetime.utcnow().isoformat()
    }


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check(repository: BasketballRepository = Depends(get_basketball_repository)):
    """Health check endpoint."""
    
    database_connected = False
    
    try:
        # Test database connection by attempting to get teams
        teams = repository.get_all_teams()
        database_connected = True
        logger.info("Health check: Database connection OK")
        
    except Exception as e:
        logger.error(f"Health check: Database connection failed: {e}")
    
    return HealthResponse(
        status="healthy" if database_connected else "unhealthy",
        database_connected=database_connected,
        timestamp=datetime.utcnow().isoformat(),
        version="1.0.0"
    )


@app.get("/api/teams", response_model=TeamListResponse, tags=["Teams"])
async def get_teams(repository: BasketballRepository = Depends(get_basketball_repository)):
    """Get all teams with their basic information."""
    
    try:
        # Get teams with calculated values from repository method that handles sessions properly
        team_responses = repository.get_teams_with_stats()
        
        logger.info(f"Retrieved {len(team_responses)} teams")
        
        return TeamListResponse(
            teams=team_responses,
            total_count=len(team_responses)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving teams: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to retrieve teams",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/teams/{team_id}/players", response_model=PlayerListResponse, tags=["Teams", "Players"])
async def get_team_players(
    team_id: int, 
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Get all players for a specific team."""
    
    try:
        # Get team players with team info (handles sessions properly)
        result = repository.get_team_players_with_team_info(team_id)
        if not result:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="TEAM_NOT_FOUND",
                    message=f"Team with ID {team_id} not found",
                    details={"team_id": team_id}
                ).dict()
            )
        
        logger.info(f"Retrieved {len(result['players'])} players for team {result['team_name']}")
        
        return PlayerListResponse(
            players=result['players'],
            team_name=result['team_name']
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error retrieving players for team {team_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to retrieve team players",
                details={"team_id": team_id, "error": str(e)}
            ).dict()
        )


# Trade Negotiation Endpoints

@app.post("/api/trade/start", response_model=TradeStartResponse, tags=["Trades"])
async def start_trade_negotiation(
    request: TradeStartRequest,
    background_tasks: BackgroundTasks,
    session_manager: TradeSessionManager = Depends(get_trade_session_manager)
):
    """
    Start a new multi-agent trade negotiation session.
    
    This endpoint initiates a trade negotiation between multiple NBA teams using
    AI agents. Each team is represented by an agent with distinct negotiation
    styles and preferences.
    """
    try:
        logger.info(f"Starting trade negotiation for team {request.trade_preference.team_id}")
        
        # Create the trade session
        session_id, success = await session_manager.create_trade_session(request.trade_preference)
        
        if not success:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="TRADE_START_FAILED",
                    message="Failed to start trade negotiation session",
                    details={"session_id": session_id}
                ).dict()
            )
        
        return TradeStartResponse(
            session_id=session_id,
            status="started",
            message="Trade negotiation session started successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting trade negotiation: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR", 
                message="Failed to start trade negotiation",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/trade/status/{session_id}", response_model=TradeNegotiationStatus, tags=["Trades"])
async def get_trade_status(
    session_id: str,
    session_manager: TradeSessionManager = Depends(get_trade_session_manager),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Get the current status of a trade negotiation session.
    
    Returns detailed information about the negotiation progress including
    current turn, status, and completion percentage.
    """
    try:
        # Get session from database
        trade_session = repository.get_trade_session(session_id)
        if not trade_session:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="SESSION_NOT_FOUND",
                    message="Trade session not found",
                    details={"session_id": session_id}
                ).dict()
            )
        
        # Return status using the model's conversion method
        return trade_session.to_pydantic_status()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade status for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to retrieve trade status",
                details={"session_id": session_id, "error": str(e)}
            ).dict()
        )


@app.get("/api/trade/result/{session_id}", response_model=TradeResultResponse, tags=["Trades"])
async def get_trade_result(
    session_id: str,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Get the final result of a completed trade negotiation.
    
    Returns the trade decision, conversation history, and negotiation
    outcome for completed sessions only.
    """
    try:
        # Get session and result from database
        trade_session = repository.get_trade_session(session_id)
        if not trade_session:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="SESSION_NOT_FOUND",
                    message="Trade session not found", 
                    details={"session_id": session_id}
                ).dict()
            )
        
        # Check if session is completed
        from backend.session.models import TradeSessionStatus
        if trade_session.status not in [TradeSessionStatus.COMPLETED, TradeSessionStatus.FAILED]:
            raise HTTPException(
                status_code=400,
                detail=ErrorResponse(
                    error="SESSION_NOT_COMPLETED",
                    message="Trade session is not yet completed",
                    details={"session_id": session_id, "status": trade_session.status.value}
                ).dict()
            )
        
        # Get conversation messages
        conversation = [msg.to_pydantic() for msg in trade_session.messages]
        
        # Build response
        trade_decision = None
        error = None
        
        if trade_session.result:
            # Get trade decision from result
            negotiation_result = trade_session.result.to_pydantic()
            trade_decision = negotiation_result.trade_decision
        
        if trade_session.status == TradeSessionStatus.FAILED:
            error = trade_session.error_message
        
        return TradeResultResponse(
            session_id=session_id,
            status=trade_session.status.value,
            trade_decision=trade_decision,
            conversation=conversation,
            total_turns=trade_session.current_turn,
            consensus_reached=trade_session.consensus_reached,
            error=error
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting trade result for session {session_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to retrieve trade result",
                details={"session_id": session_id, "error": str(e)}
            ).dict()
        )


# WebSocket endpoint for real-time updates
@app.websocket("/ws/trade/{session_id}")
async def websocket_trade_updates(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time trade negotiation updates.
    
    Clients can connect to receive live updates including:
    - Agent messages as they are sent
    - Status updates and turn changes  
    - Completion notifications
    - Error messages
    """
    await handle_websocket_connection(websocket, session_id)


# Keep old plural routes temporarily with deprecation warnings
@app.post("/api/trades/start", response_model=TradeStartResponse, tags=["Trades"], deprecated=True)
async def start_trade_negotiation_deprecated(
    request: TradeStartRequest,
    background_tasks: BackgroundTasks,
    session_manager: TradeSessionManager = Depends(get_trade_session_manager)
):
    """Deprecated: Use /api/trade/start instead."""
    logger.warning("Using deprecated endpoint /api/trades/start, use /api/trade/start instead")
    return await start_trade_negotiation(request, background_tasks, session_manager)


@app.get("/api/trades/{session_id}/status", response_model=TradeNegotiationStatus, tags=["Trades"], deprecated=True)  
async def get_trade_status_deprecated(
    session_id: str,
    session_manager: TradeSessionManager = Depends(get_trade_session_manager),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Deprecated: Use /api/trade/status/{session_id} instead."""
    logger.warning("Using deprecated endpoint /api/trades/{session_id}/status")
    return await get_trade_status(session_id, session_manager, repository)


@app.get("/api/trades/{session_id}/result", response_model=TradeResultResponse, tags=["Trades"], deprecated=True)
async def get_trade_result_deprecated(
    session_id: str,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Deprecated: Use /api/trade/result/{session_id} instead."""
    logger.warning("Using deprecated endpoint /api/trades/{session_id}/result")  
    return await get_trade_result(session_id, repository)


@app.websocket("/ws/trades/{session_id}")
async def websocket_trade_updates_deprecated(websocket: WebSocket, session_id: str):
    """Deprecated: Use /ws/trade/{session_id} instead."""
    logger.warning("Using deprecated endpoint /ws/trades/{session_id}")
    await handle_websocket_connection(websocket, session_id)


if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=True,
        log_level=settings.log_level.lower()
    )