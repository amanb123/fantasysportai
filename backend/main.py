

"""
FastAPI application for the Fantasy Basketball League API.
"""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, WebSocket, BackgroundTasks, WebSocketDisconnect, Query, Path, Body
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from backend.config import settings
from backend.session.database import init_database, get_repository, ensure_refresh_token_columns, ensure_trade_sessions_user_id_column, ensure_roster_chat_tables, ensure_trade_analysis_tables
from backend.session.repository import BasketballRepository
from backend.dependencies import (
    get_basketball_repository, get_redis_service, get_player_cache_service, 
    get_league_data_cache_service, get_nba_stats_service, get_nba_cache_service,
    get_roster_context_builder, get_trade_analysis_service, get_matchup_simulation_service,
    get_sleeper_service, get_roster_ranking_service
)
from backend.session.models import TeamModel, PlayerModel, TradeAnalysisSessionModel
from backend.api_models import (
    ErrorResponse, TeamListResponse, PlayerListResponse, HealthResponse, 
    TradeStartRequest, TradeStartResponse, TradeNegotiationStatus, TradeResultResponse, 
    SleeperSyncResponse, SleeperCacheStatus, SleeperPlayerResponse,
    SleeperLeagueResponse, SleeperRosterResponse, SleeperUserSessionRequest, SleeperUserSessionResponse,
    SleeperTransactionResponse, SleeperMatchupResponse, LeagueDataCacheStatus, LeagueDataRefreshResponse,
    GameScheduleResponse, PlayerInfoResponse, NBAScheduleSyncResponse, NBAPlayerInfoSyncResponse, NBACacheStatusResponse,
    RosterChatStartRequest, RosterChatStartResponse, RosterChatMessageRequest, RosterChatMessageResponse,
    RosterChatHistoryResponse, RosterChatSessionListResponse,
    # Trade Assistant models
    RecentTradeResponse, TradeAnalysisStartRequest, TradeAnalysisStartResponse,
    TradeAnalysisResultResponse, TradeSimulationRequest, TradeSimulationResponse,
    TradeAnalysisSessionListResponse,
    # Roster Ranking models
    RosterRankingResponse, RosterRankingCacheStatus
)

from backend.services.player_cache_service import PlayerCacheService
from backend.services.league_data_cache_service import LeagueDataCacheService
from shared.models import TeamResponse, PlayerResponse, TradePreferenceRequest, AgentMessage
from backend.session_manager import TradeSessionManager
from backend.websocket_manager import connection_manager, handle_websocket_connection

# Authentication imports
from backend.auth.models import UserRegisterRequest, UserLoginRequest, TokenResponse, UserResponse, LinkSleeperRequest, RefreshTokenRequest
from backend.auth.security import verify_password, get_password_hash, create_access_token, create_refresh_token, decode_refresh_token
from backend.auth.dependencies import get_current_active_user, get_optional_user
from backend.services.sleeper_service import SleeperService
from backend.session.models import UserModel
from datetime import timedelta
from fastapi.security import OAuth2PasswordRequestForm

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level.upper()),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

async def initialize_player_cache(player_cache_service):
    """Background task to initialize player cache on startup."""
    try:
        logger.info("Starting background player cache initialization...")
        success, error_message = await player_cache_service.fetch_and_cache_players()
        if success:
            cache_stats = player_cache_service.get_cache_stats()
            logger.info(f"✅ Player cache initialized successfully: {cache_stats.get('player_count', 0)} players cached")
        else:
            logger.error(f"❌ Player cache initialization failed: {error_message}")
    except Exception as e:
        logger.error(f"❌ Player cache initialization error: {e}")


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
        
        # Ensure database schema is up to date (migrations)
        logger.info("Checking database schema...")
        ensure_refresh_token_columns()
        ensure_trade_sessions_user_id_column()
        ensure_roster_chat_tables()
        ensure_trade_analysis_tables()
        
        # Test repository connection
        repository = get_repository()
        logger.info("Database connection established successfully")
        
        # Initialize Redis connection
        logger.info("Initializing Redis connection...")
        try:
            redis_service = get_redis_service()
            if redis_service and redis_service.is_connected():
                logger.info("Redis connection established successfully")
                
                # Initialize player cache
                logger.info("Checking Sleeper player cache...")
                player_cache_service = get_player_cache_service()
                if player_cache_service:
                    cache_stats = player_cache_service.get_cache_stats()
                    if cache_stats.get("is_valid", False):
                        logger.info(f"✅ Player cache is valid: {cache_stats.get('player_count', 0)} players, TTL: {cache_stats.get('ttl_remaining', 0)}s")
                    else:
                        logger.info("⏳ Player cache is empty or expired, initializing in background...")
                        # Start background task to fetch players (non-blocking)
                        import asyncio
                        asyncio.create_task(initialize_player_cache(player_cache_service))
                
                # Initialize NBA schedule cache
                logger.info("Checking NBA schedule cache...")
                nba_cache_service = get_nba_cache_service()
                if nba_cache_service:
                    try:
                        # Check if schedule exists in database for current season
                        from datetime import datetime as dt
                        current_date = dt.now()
                        if current_date.month >= 10:
                            season_year = current_date.year
                        else:
                            season_year = current_date.year - 1
                        
                        today = current_date.date()
                        end_date = today + timedelta(days=7)
                        games = repository.get_games_by_date_range(str(today), str(end_date))
                        
                        if games:
                            logger.info(f"✅ NBA schedule cache is valid: {len(games)} games in next 7 days")
                        else:
                            logger.info("⏳ NBA schedule cache is empty, syncing in background...")
                            import asyncio
                            asyncio.create_task(nba_cache_service.fetch_and_cache_schedule(season=str(season_year)))
                    except Exception as nba_error:
                        logger.warning(f"NBA schedule check failed: {nba_error}")
                        logger.info("Will attempt to sync NBA schedule in background...")
            else:
                logger.warning("Redis connection failed - Sleeper caching will be unavailable")
        except Exception as redis_error:
            logger.warning(f"Redis initialization failed: {redis_error}")
            logger.warning("Continuing without Redis - Sleeper caching will be unavailable")
        
        # Initialize trade session manager
        global trade_session_manager
        trade_session_manager = TradeSessionManager(repository)
        logger.info("Trade session manager initialized")
        
    except Exception as e:
        logger.error(f"Failed to initialize application: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down Fantasy Basketball League API")
    
    # Close Redis connection
    try:
        redis_service = get_redis_service()
        if redis_service:
            redis_service.close()
            logger.info("Redis connection closed")
    except Exception as e:
        logger.warning(f"Error closing Redis connection: {e}")
    
    logger.info("✅ Shutdown complete")


# Initialize FastAPI application
app = FastAPI(
    title="Fantasy Basketball League API",
    version="1.0.0",
    description="Multi-agent fantasy basketball trade manager with AI-powered negotiations",
    docs_url="/docs",
    lifespan=lifespan
)

# Determine CORS origins
cors_origins = settings.cors_origins_list
# If CORS_ORIGINS env var is not set or empty, allow all origins (for initial setup)
if not settings.cors_origins or settings.cors_origins == "http://localhost:3000,http://localhost:3001,http://localhost:5173":
    logger.warning("CORS_ORIGINS not configured - allowing all origins. Set CORS_ORIGINS in production!")
    cors_origins = ["*"]

logger.info(f"CORS Origins: {cors_origins}")

# Add CORS middleware with regex support for Vercel preview deployments
# Vercel generates URLs like: fantasysportai-*.vercel.app
# Note: allow_credentials=True cannot be used with allow_origins=["*"]
# So we disable credentials when using wildcard
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",  # Allow all Vercel preview URLs
    allow_credentials=(cors_origins != ["*"]),  # Only allow credentials if not using wildcard
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,  # Cache preflight requests for 1 hour
)


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


# Authentication Endpoints

@app.post("/api/auth/register", response_model=TokenResponse, tags=["Authentication"])
async def register_user(
    user_data: UserRegisterRequest,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Register a new user account."""
    
    # Validate password confirmation
    if user_data.password != user_data.confirm_password:
        raise HTTPException(
            status_code=400,
            detail="Passwords do not match"
        )
    
    # Validate password length
    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long"
        )
    
    # Check if user already exists
    existing_user = repository.get_user_by_email(user_data.email)
    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Email already registered"
        )
    
    try:
        # Hash password and create user
        hashed_password = get_password_hash(user_data.password)
        user = repository.create_user(user_data.email, hashed_password)
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Create refresh token
        refresh_token = create_refresh_token(data={"sub": user.email})
        
        # Store hashed refresh token in database
        from datetime import datetime, timedelta
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_refresh_token = pwd_context.hash(refresh_token)
        refresh_expires_at = datetime.utcnow() + timedelta(days=7)
        
        repository.store_refresh_token(user.id, hashed_refresh_token, refresh_expires_at)
        
        logger.info(f"User registered successfully: {user.email}")
        
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
        
    except Exception as e:
        logger.error(f"Registration error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/auth/login", response_model=TokenResponse, tags=["Authentication"])
async def login_user(
    form_data: OAuth2PasswordRequestForm = Depends(),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """User login (OAuth2 compatible)."""
    
    # Get user by email (username field contains email)
    user = repository.get_user_by_email(form_data.username)
    if not user:
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify password
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=400,
            detail="Inactive user"
        )
    
    try:
        # Update last login
        repository.update_last_login(user.id)
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Create refresh token
        refresh_token = create_refresh_token(data={"sub": user.email})
        
        # Store hashed refresh token in database
        from datetime import datetime, timedelta
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_refresh_token = pwd_context.hash(refresh_token)
        refresh_expires_at = datetime.utcnow() + timedelta(days=7)
        
        repository.store_refresh_token(user.id, hashed_refresh_token, refresh_expires_at)
        
        logger.info(f"User logged in successfully: {user.email}")
        
        return TokenResponse(access_token=access_token, refresh_token=refresh_token)
        
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/auth/refresh", response_model=TokenResponse, tags=["Authentication"])
async def refresh_access_token(
    token_data: RefreshTokenRequest,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Refresh access token using refresh token."""
    
    # Decode refresh token
    payload = decode_refresh_token(token_data.refresh_token)
    if not payload:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    email = payload.get("sub")
    if not email:
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Get user from database
    user = repository.get_user_by_email(email)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=401,
            detail="User not found or inactive",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Verify refresh token against stored hash
    if not repository.verify_refresh_token(user.id, token_data.refresh_token):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    try:
        # Create new access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": user.email}, expires_delta=access_token_expires
        )
        
        # Create new refresh token (token rotation)
        new_refresh_token = create_refresh_token(data={"sub": user.email})
        
        # Store new hashed refresh token in database
        from datetime import datetime, timedelta
        from passlib.context import CryptContext
        
        pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
        hashed_refresh_token = pwd_context.hash(new_refresh_token)
        refresh_expires_at = datetime.utcnow() + timedelta(days=7)
        
        repository.store_refresh_token(user.id, hashed_refresh_token, refresh_expires_at)
        
        logger.info(f"Tokens refreshed successfully for user: {user.email}")
        
        return TokenResponse(access_token=access_token, refresh_token=new_refresh_token)
        
    except Exception as e:
        logger.error(f"Token refresh error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.get("/api/auth/me", response_model=UserResponse, tags=["Authentication"])
async def get_current_user_info(
    current_user: UserModel = Depends(get_current_active_user)
):
    """Get current authenticated user information."""
    
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        sleeper_username=current_user.sleeper_username,
        sleeper_user_id=current_user.sleeper_user_id,
        is_active=current_user.is_active,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )


@app.post("/api/auth/logout", tags=["Authentication"])
async def logout_user(
    current_user: UserModel = Depends(get_current_active_user),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Logout user by clearing their refresh token."""
    
    try:
        # Clear refresh token from database
        repository.clear_refresh_token(current_user.id)
        
        logger.info(f"User logged out successfully: {current_user.email}")
        
        return {"message": "Logout successful"}
        
    except Exception as e:
        logger.error(f"Logout error for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


@app.post("/api/auth/link-sleeper", response_model=UserResponse, tags=["Authentication"])
async def link_sleeper_account(
    sleeper_data: LinkSleeperRequest,
    current_user: UserModel = Depends(get_current_active_user),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Link Sleeper account to current user."""
    
    try:
        # Validate Sleeper username
        async with SleeperService() as sleeper_service:
            is_valid, sleeper_user_id, error_msg = await sleeper_service.validate_sleeper_username(
                sleeper_data.sleeper_username
            )
            
            if not is_valid:
                raise HTTPException(
                    status_code=400,
                    detail=error_msg or f"Invalid Sleeper username: {sleeper_data.sleeper_username}"
                )
            
            # Update user with Sleeper info
            success = repository.update_user_sleeper_info(
                current_user.id, 
                sleeper_data.sleeper_username,
                sleeper_user_id
            )
            
            if not success:
                raise HTTPException(status_code=500, detail="Failed to update Sleeper information")
            
            # Get updated user
            updated_user = repository.get_user_by_id(current_user.id)
            if not updated_user:
                raise HTTPException(status_code=500, detail="Failed to retrieve updated user")
            
            logger.info(f"Sleeper account linked for user {current_user.email}: {sleeper_data.sleeper_username}")
            
            return UserResponse(
                id=updated_user.id,
                email=updated_user.email,
                sleeper_username=updated_user.sleeper_username,
                sleeper_user_id=updated_user.sleeper_user_id,
                is_active=updated_user.is_active,
                created_at=updated_user.created_at,
                last_login=updated_user.last_login
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Sleeper linking error for user {current_user.email}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")


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
    current_user: Optional[UserModel] = Depends(get_optional_user),
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
        user_id = current_user.id if current_user else None
        session_id, success = await session_manager.create_trade_session(user_id, request.trade_preference)
        
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
    current_user: Optional[UserModel] = Depends(get_optional_user),
    session_manager: TradeSessionManager = Depends(get_trade_session_manager),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Get the current status of a trade negotiation session.
    
    Returns detailed information about the negotiation progress including
    current turn, status, and completion percentage.
    """
    try:
        # Validate session ownership (skip if no user)
        if current_user and not repository.validate_session_ownership(session_id, current_user.id):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="SESSION_NOT_FOUND",
                    message="Trade session not found",
                    details={"session_id": session_id}
                ).dict()
            )
        
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
    current_user: Optional[UserModel] = Depends(get_optional_user),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Get the final result of a completed trade negotiation.
    
    Returns the trade decision, conversation history, and negotiation
    outcome for completed sessions only.
    """
    try:
        # Validate session ownership (skip if no user)
        if current_user and not repository.validate_session_ownership(session_id, current_user.id):
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="SESSION_NOT_FOUND",
                    message="Trade session not found", 
                    details={"session_id": session_id}
                ).dict()
            )
        
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


# ===== Roster Chat Endpoints =====

@app.post("/api/roster-chat/start", response_model=RosterChatStartResponse, tags=["Roster Chat"])
async def start_roster_chat(
    request: RosterChatStartRequest,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Start a new roster chat session.
    
    Creates a chat session for roster advice and returns session ID.
    """
    try:
        import uuid
        from backend.agents.agent_factory import AgentFactory
        
        # Generate unique session ID
        session_id = str(uuid.uuid4())
        
        # Create chat session in database
        chat_session = repository.create_roster_chat_session(
            session_id=session_id,
            sleeper_user_id=request.sleeper_user_id,
            league_id=request.league_id,
            roster_id=request.roster_id
        )
        
        # If initial message provided, process it
        initial_response = None
        if request.initial_message:
            try:
                # Get context builder
                context_builder = get_roster_context_builder()
                if not context_builder:
                    raise HTTPException(status_code=500, detail="Context builder unavailable")
                
                # Ensure league data is cached
                league_cache = context_builder.league_cache
                cached_league = league_cache.get_cached_league_details(request.league_id)
                if not cached_league:
                    logger.info(f"League {request.league_id} not cached, fetching and caching now")
                    await league_cache.cache_league_data(request.league_id)
                
                # Ensure rosters are cached
                cached_rosters = league_cache.get_cached_rosters(request.league_id)
                if not cached_rosters:
                    logger.info(f"Rosters for league {request.league_id} not cached, fetching now")
                    await league_cache.cache_rosters(request.league_id)
                
                # Pre-warm matchup cache for current week
                try:
                    current_week = league_cache.get_current_nba_week()
                    if current_week:
                        cached_matchups = league_cache.get_cached_matchups(request.league_id, current_week)
                        if not cached_matchups:
                            logger.info(f"Matchups for league {request.league_id} week {current_week} not cached, fetching now")
                            await league_cache.cache_matchups(request.league_id)
                except Exception as matchup_error:
                    logger.warning(f"Could not pre-warm matchup cache: {matchup_error}")
                
                # Build roster context
                roster_context = await context_builder.build_roster_context(
                    league_id=request.league_id,
                    roster_id=request.roster_id,
                    sleeper_user_id=request.sleeper_user_id,
                    include_historical=False
                )
                
                # Store user message
                repository.add_roster_chat_message(
                    session_id=session_id,
                    role="user",
                    content=request.initial_message
                )
                
                # Initialize tools for function calling
                from backend.agents.tools import ROSTER_ADVISOR_TOOLS, RosterAdvisorTools
                from backend.dependencies import get_sleeper_service, get_nba_stats_service, get_nba_mcp_service
                
                sleeper_service = get_sleeper_service()
                nba_stats_service = get_nba_stats_service()
                nba_mcp_service = get_nba_mcp_service() if settings.nba_mcp_enabled else None
                
                tool_executor = RosterAdvisorTools(
                    league_id=request.league_id,
                    roster_id=request.roster_id,
                    sleeper_user_id=request.sleeper_user_id,
                    league_cache_service=league_cache,
                    player_cache_service=context_builder.player_cache,
                    sleeper_service=sleeper_service,
                    nba_stats_service=nba_stats_service,
                    nba_mcp_service=nba_mcp_service
                )
                
                # Create advisor agent with function calling support
                agent_factory = AgentFactory()
                advisor_agent = agent_factory.create_roster_advisor_agent(
                    roster_context=roster_context,
                    tools=ROSTER_ADVISOR_TOOLS,
                    tool_executor=tool_executor
                )
                
                # Build chat history for agent
                chat_history = [{"role": "user", "content": request.initial_message}]
                
                # Generate response using LLM
                try:
                    # Use autogen's generate_reply method
                    response = await advisor_agent.a_generate_reply(messages=chat_history)
                    if isinstance(response, dict):
                        initial_response = response.get("content", "I'm here to help with your roster. What would you like to know?")
                    else:
                        initial_response = str(response) if response else "I'm here to help with your roster. What would you like to know?"
                except Exception as llm_error:
                    logger.error(f"LLM generation error: {llm_error}")
                    # Fallback response
                    initial_response = "Hello! I'm your roster advisor. I can help you with lineup decisions, waiver wire targets, and player analysis. How can I assist you today?"
                
                # Store assistant response
                repository.add_roster_chat_message(
                    session_id=session_id,
                    role="assistant",
                    content=initial_response
                )
                
            except Exception as e:
                logger.error(f"Error processing initial message: {e}")
                # Continue without initial response
        
        return RosterChatStartResponse(
            session_id=session_id,
            status="active",
            message="Chat session created successfully",
            initial_response=initial_response
        )
        
    except Exception as e:
        logger.error(f"Error starting roster chat: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to start roster chat",
                details={"error": str(e)}
            ).dict()
        )


def _detect_historical_query(message: str) -> bool:
    """Detect if message contains historical query keywords."""
    historical_keywords = [
        "2022", "2023", "2021", "2020", "2019",
        "last year", "last season", "career",
        "average in", "stats in", "around this time",
        "historically", "previous season"
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in historical_keywords)


@app.post("/api/roster-chat/{session_id}/message", response_model=RosterChatMessageResponse, tags=["Roster Chat"])
async def send_chat_message(
    session_id: str,
    request: RosterChatMessageRequest,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Send a message in a roster chat session and get AI response.
    """
    try:
        from backend.agents.agent_factory import AgentFactory
        
        # Log incoming request
        logger.info(f"📨 Received chat message - Session: {session_id}, Message: '{request.message[:50]}...'")
        
        # Validate session exists
        chat_session = repository.get_roster_chat_session(session_id)
        if not chat_session:
            logger.error(f"❌ Chat session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Extract ALL values we need from chat_session immediately to avoid DetachedInstanceError
        league_id = chat_session.league_id
        roster_id = chat_session.roster_id
        sleeper_user_id = chat_session.sleeper_user_id
        session_status = chat_session.status
        
        if session_status != "active":
            raise HTTPException(status_code=400, detail="Chat session is not active")
        
        # Store user message
        repository.add_roster_chat_message(
            session_id=session_id,
            role="user",
            content=request.message
        )
        
        # Get chat history
        chat_history = repository.get_chat_history_for_context(session_id, max_messages=10)
        
        # Detect if historical query
        is_historical = _detect_historical_query(request.message) and request.include_historical
        
        # Get context builder
        context_builder = get_roster_context_builder()
        if not context_builder:
            raise HTTPException(status_code=500, detail="Context builder unavailable")
        
        # Ensure league data is cached
        league_cache = context_builder.league_cache
        cached_league = league_cache.get_cached_league_details(league_id)
        if not cached_league:
            logger.info(f"League {league_id} not cached, fetching and caching now")
            await league_cache.cache_league_data(league_id)
        
        # Ensure rosters are cached
        cached_rosters = league_cache.get_cached_rosters(league_id)
        if not cached_rosters:
            logger.info(f"Rosters for league {league_id} not cached, fetching now")
            await league_cache.cache_rosters(league_id)
        
        # Pre-warm matchup cache for current week
        try:
            current_week = league_cache.get_current_nba_week()
            if current_week:
                cached_matchups = league_cache.get_cached_matchups(league_id, current_week)
                if not cached_matchups:
                    logger.info(f"Matchups for league {league_id} week {current_week} not cached, fetching now")
                    await league_cache.cache_matchups(league_id)
        except Exception as matchup_error:
            logger.warning(f"Could not pre-warm matchup cache: {matchup_error}")
        
        # Build roster context
        roster_context = await context_builder.build_roster_context(
            league_id=league_id,
            roster_id=roster_id,
            sleeper_user_id=sleeper_user_id,
            include_historical=is_historical,
            historical_query=request.message if is_historical else None
        )
        
        # Initialize tools for function calling
        from backend.agents.tools import ROSTER_ADVISOR_TOOLS, RosterAdvisorTools
        from backend.dependencies import get_sleeper_service, get_nba_stats_service, get_nba_mcp_service, get_nba_news_service
        
        sleeper_service = get_sleeper_service()
        nba_stats_service = get_nba_stats_service()
        nba_mcp_service = get_nba_mcp_service() if settings.nba_mcp_enabled else None
        nba_news_service = get_nba_news_service()
        
        tool_executor = RosterAdvisorTools(
            league_id=league_id,
            roster_id=roster_id,
            sleeper_user_id=sleeper_user_id,
            league_cache_service=league_cache,
            player_cache_service=context_builder.player_cache,
            sleeper_service=sleeper_service,
            nba_stats_service=nba_stats_service,
            nba_mcp_service=nba_mcp_service,
            nba_news_service=nba_news_service
        )
        
        # Create advisor agent with function calling support
        agent_factory = AgentFactory()
        advisor_agent = agent_factory.create_roster_advisor_agent(
            roster_context=roster_context,
            tools=ROSTER_ADVISOR_TOOLS,
            tool_executor=tool_executor
        )
        
        # Build message history for agent (format for autogen)
        agent_messages = []
        for msg in chat_history:
            agent_messages.append({"role": msg["role"], "content": msg["content"]})
        
        # Add current user message
        agent_messages.append({"role": "user", "content": request.message})
        
        logger.info(f"Sending to LLM: {len(agent_messages)} messages, latest: '{request.message}'")
        
        # Generate response using LLM
        try:
            # Use autogen's generate_reply method
            logger.info(f"Calling a_generate_reply with {len(agent_messages)} messages")
            response = await advisor_agent.a_generate_reply(messages=agent_messages)
            logger.info(f"LLM response type: {type(response)}, content: {response}")
            if isinstance(response, dict):
                assistant_content = response.get("content", "I'm processing your request. Please try again.")
            else:
                assistant_content = str(response) if response else "I'm having trouble generating a response. Please try again."
            logger.info(f"Final assistant content: {assistant_content[:100]}...")
        except Exception as llm_error:
            logger.error(f"LLM generation error: {llm_error}")
            import traceback
            logger.error(f"LLM error traceback: {traceback.format_exc()}")
            # Fallback response with context awareness
            assistant_content = f"I understand you're asking about: '{request.message}'. Based on your roster and league settings, I recommend reviewing your lineup and considering the upcoming schedule. For more specific advice, please rephrase your question."
        
        # Store assistant response
        metadata = {"historical_stats_fetched": is_historical}
        assistant_message = repository.add_roster_chat_message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            metadata=metadata
        )
        
        # Broadcast via WebSocket
        await connection_manager.broadcast_chat_message(
            session_id=session_id,
            role="assistant",
            content=assistant_content,
            timestamp=assistant_message.timestamp.isoformat(),
            metadata=metadata
        )
        
        return RosterChatMessageResponse(
            role="assistant",
            content=assistant_content,
            timestamp=assistant_message.timestamp.isoformat(),
            session_id=session_id,
            metadata=metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"Error sending chat message: {e}")
        logger.error(f"Full traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="INTERNAL_ERROR",
                message="Failed to send message",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/roster-chat/{session_id}/history", response_model=RosterChatHistoryResponse, tags=["Roster Chat"])
async def get_chat_history(
    session_id: str,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Get full chat history for a session."""
    try:
        # Get session
        chat_session = repository.get_roster_chat_session(session_id)
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        # Get messages
        messages = repository.get_chat_messages(session_id)
        
        # Convert to response format
        message_responses = []
        for msg in messages:
            import json
            metadata = json.loads(msg.message_metadata) if msg.message_metadata else None
            message_responses.append(
                RosterChatMessageResponse(
                    role=msg.role,
                    content=msg.content,
                    timestamp=msg.timestamp.isoformat(),
                    session_id=session_id,
                    metadata=metadata
                )
            )
        
        return RosterChatHistoryResponse(
            session_id=session_id,
            messages=message_responses,
            league_id=chat_session.league_id,
            roster_id=chat_session.roster_id,
            created_at=chat_session.created_at.isoformat(),
            last_message_at=chat_session.last_message_at.isoformat() if chat_session.last_message_at else None,
            message_count=len(message_responses)
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat history")


@app.get("/api/roster-chat/sessions", response_model=RosterChatSessionListResponse, tags=["Roster Chat"])
async def get_user_chat_sessions(
    sleeper_user_id: str = Query(..., description="Sleeper user ID"),
    league_id: Optional[str] = Query(None, description="Filter by league ID"),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Get list of chat sessions for a user."""
    try:
        sessions = repository.get_user_roster_chat_sessions(
            sleeper_user_id=sleeper_user_id,
            league_id=league_id,
            limit=20
        )
        
        # Convert to response format
        session_list = []
        for session in sessions:
            session_list.append({
                "session_id": session.session_id,
                "league_id": session.league_id,
                "roster_id": session.roster_id,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "last_message_at": session.last_message_at.isoformat() if session.last_message_at else None
            })
        
        return RosterChatSessionListResponse(
            sessions=session_list,
            total_count=len(session_list)
        )
        
    except Exception as e:
        logger.error(f"Error getting user chat sessions: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve chat sessions")


@app.delete("/api/roster-chat/{session_id}", tags=["Roster Chat"])
async def archive_chat_session(
    session_id: str,
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Archive a chat session."""
    try:
        success = repository.archive_chat_session(session_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="Chat session not found")
        
        return {"success": True, "message": "Chat session archived"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error archiving chat session: {e}")
        raise HTTPException(status_code=500, detail="Failed to archive chat session")


@app.websocket("/ws/roster-chat/{session_id}")
async def websocket_roster_chat(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for roster chat real-time updates.
    """
    await websocket.accept()
    connection_manager.connect_to_chat(websocket, session_id)
    
    try:
        # Keep connection alive with ping/pong
        while True:
            try:
                message = await websocket.receive_text()
                
                # Parse message
                try:
                    import json
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    if message_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from WebSocket in chat session {session_id}")
            
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message in chat session {session_id}: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error in WebSocket connection for chat session {session_id}: {e}")
    finally:
        connection_manager.disconnect_from_chat(websocket)


# Keep old plural routes temporarily with deprecation warnings
@app.post("/api/trades/start", response_model=TradeStartResponse, tags=["Trades"], deprecated=True)
async def start_trade_negotiation_deprecated(
    request: TradeStartRequest,
    background_tasks: BackgroundTasks,
    current_user: UserModel = Depends(get_current_active_user),
    session_manager: TradeSessionManager = Depends(get_trade_session_manager)
):
    """Deprecated: Use /api/trade/start instead."""
    logger.warning("Using deprecated endpoint /api/trades/start, use /api/trade/start instead")
    return await start_trade_negotiation(request, background_tasks, current_user, session_manager)


@app.get("/api/trades/{session_id}/status", response_model=TradeNegotiationStatus, tags=["Trades"], deprecated=True)  
async def get_trade_status_deprecated(
    session_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    session_manager: TradeSessionManager = Depends(get_trade_session_manager),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Deprecated: Use /api/trade/status/{session_id} instead."""
    logger.warning("Using deprecated endpoint /api/trades/{session_id}/status")
    return await get_trade_status(session_id, current_user, session_manager, repository)


@app.get("/api/trades/{session_id}/result", response_model=TradeResultResponse, tags=["Trades"], deprecated=True)
async def get_trade_result_deprecated(
    session_id: str,
    current_user: UserModel = Depends(get_current_active_user),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """Deprecated: Use /api/trade/result/{session_id} instead."""
    logger.warning("Using deprecated endpoint /api/trades/{session_id}/result")  
    return await get_trade_result(session_id, current_user, repository)


# ============================================================================
# Trade Assistant Endpoints
# ============================================================================

@app.get(
    "/api/trade-assistant/recent-trades/{league_id}",
    response_model=List[RecentTradeResponse],
    tags=["Trade Assistant"]
)
async def get_recent_trades(
    league_id: str = Path(..., description="Sleeper league ID"),
    limit: int = Query(10, ge=1, le=50, description="Number of recent trades to fetch"),
    sleeper_service: SleeperService = Depends(get_sleeper_service)
):
    """
    Get recent completed trades in a league (for reference when creating new trades).
    
    Fetches recent transactions from Sleeper API and filters for completed trades.
    Note: Sleeper API only exposes completed trades, not pending proposals.
    """
    try:
        logger.info(f"Fetching recent trades for league {league_id}")
        
        # Fetch transactions from Sleeper
        transactions = await sleeper_service.get_transactions(league_id, round=None)
        
        # Filter for trades only (type="trade" and status="complete")
        trades = [
            t for t in transactions
            if t.get("type") == "trade" and t.get("status") == "complete"
        ][:limit]
        
        # Fetch rosters and users to get owner names
        rosters = await sleeper_service.get_league_rosters(league_id)
        users = await sleeper_service.get_league_users(league_id)
        
        # Build roster_id -> owner_name mapping
        roster_to_owner = {}
        if rosters and users:
            user_map = {u.get("user_id"): u for u in users}
            for roster in rosters:
                roster_id = roster.get("roster_id")
                owner_id = roster.get("owner_id")
                if roster_id and owner_id and owner_id in user_map:
                    user = user_map[owner_id]
                    display_name = user.get("display_name") or user.get("username") or f"Team {roster_id}"
                    roster_to_owner[roster_id] = display_name
        
        # Format response
        result = []
        for trade in trades:
            # Build human-readable description with owner names
            roster_ids = trade.get("roster_ids", [])
            if len(roster_ids) >= 2:
                owner1 = roster_to_owner.get(roster_ids[0], f"Roster {roster_ids[0]}")
                owner2 = roster_to_owner.get(roster_ids[1], f"Roster {roster_ids[1]}")
                description = f"Trade between {owner1} and {owner2}"
            else:
                description = "Trade"
            
            result.append(RecentTradeResponse(
                transaction_id=trade.get("transaction_id", ""),
                status=trade.get("status", "complete"),
                created=trade.get("created", 0),
                roster_ids=roster_ids,
                adds=trade.get("adds"),
                drops=trade.get("drops"),
                description=description
            ))
        
        logger.info(f"Found {len(result)} recent trades")
        return result
        
    except Exception as e:
        logger.error(f"Error fetching recent trades: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch recent trades: {str(e)}")


@app.post(
    "/api/trade-assistant/analyze",
    response_model=TradeAnalysisStartResponse,
    tags=["Trade Assistant"]
)
async def start_trade_analysis(
    request: TradeAnalysisStartRequest,
    background_tasks: BackgroundTasks,
    repository: BasketballRepository = Depends(get_basketball_repository),
    trade_analysis_service = Depends(get_trade_analysis_service),
    current_user: Optional[UserModel] = Depends(get_optional_user)
):
    """
    Start AI-powered trade analysis.
    
    Analyzes a proposed trade using:
    - League scoring settings
    - Current rosters
    - NBA player stats (via MCP)
    - Upcoming schedule strength
    - AI agent evaluation
    
    Returns a session ID to check results.
    """
    try:
        if trade_analysis_service is None:
            raise HTTPException(
                status_code=503,
                detail="Trade analysis service unavailable (NBA MCP required)"
            )
        
        logger.info(f"Starting trade analysis for league {request.league_id}")
        
        # Generate session ID
        import uuid
        session_id = str(uuid.uuid4())
        
        # Create database session
        db_session = repository.create_trade_analysis_session(
            session_id=session_id,
            sleeper_user_id=request.sleeper_user_id,
            league_id=request.league_id,
            user_roster_id=request.user_roster_id,
            opponent_roster_id=request.opponent_roster_id,
            user_players_out=request.user_players_out,
            user_players_in=request.user_players_in,
            user_id=request.user_id or (current_user.id if current_user else None)
        )
        
        # Run analysis in background
        async def analyze_trade_task():
            try:
                logger.info(f"Analyzing trade for session {session_id}")
                
                analysis_result = await trade_analysis_service.analyze_trade(
                    league_id=request.league_id,
                    user_roster_id=request.user_roster_id,
                    opponent_roster_id=request.opponent_roster_id,
                    user_players_out=request.user_players_out,
                    user_players_in=request.user_players_in
                )
                
                # Save result
                repository.update_trade_analysis_result(
                    session_id=session_id,
                    analysis_result=analysis_result,
                    favorability_score=analysis_result.get("favorability_score", 50.0)
                )
                
                logger.info(f"Trade analysis complete for session {session_id}")
                
            except Exception as e:
                logger.error(f"Error in trade analysis task: {e}")
                # Mark as failed in database
                try:
                    repository.update_trade_analysis_result(
                        session_id=session_id,
                        analysis_result={"error": str(e)},
                        favorability_score=None
                    )
                    # Update status to failed using managed session
                    with repository.get_session() as session:
                        stmt = session.query(TradeAnalysisSessionModel).filter_by(
                            session_id=session_id
                        )
                        stmt.update({"status": "failed"})
                        session.commit()
                except Exception as db_err:
                    logger.error(f"Failed to update failed status: {db_err}")
                    pass
        
        background_tasks.add_task(analyze_trade_task)
        
        return TradeAnalysisStartResponse(
            session_id=session_id,
            status="analyzing",
            message="Trade analysis started. Check /api/trade-assistant/analysis/{session_id} for results."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting trade analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start trade analysis: {str(e)}")


@app.get(
    "/api/trade-assistant/analysis/{session_id}",
    response_model=TradeAnalysisResultResponse,
    tags=["Trade Assistant"]
)
async def get_trade_analysis_result(
    session_id: str = Path(..., description="Trade analysis session UUID"),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Get trade analysis result.
    
    Returns the AI analysis result including:
    - Pros and cons
    - Favorability score (0-100)
    - Recommendation (Accept/Reject)
    - Reasoning
    """
    try:
        db_session = repository.get_trade_analysis_session(session_id)
        
        if not db_session:
            raise HTTPException(status_code=404, detail="Trade analysis session not found")
        
        # Convert to Pydantic-friendly dict (handles JSON parsing)
        session_data = db_session.to_pydantic()
        
        return TradeAnalysisResultResponse(
            session_id=session_data["session_id"],
            status=session_data["status"],
            analysis_result=session_data.get("analysis"),
            favorability_score=session_data.get("favorability_score"),
            simulation_result=session_data.get("simulation"),
            created_at=session_data.get("created_at", ""),
            completed_at=session_data.get("completed_at")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving trade analysis: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve analysis: {str(e)}")


@app.post(
    "/api/trade-assistant/simulate",
    response_model=TradeSimulationResponse,
    tags=["Trade Assistant"]
)
async def simulate_matchup_with_trade(
    request: TradeSimulationRequest,
    background_tasks: BackgroundTasks,
    repository: BasketballRepository = Depends(get_basketball_repository),
    simulation_service = Depends(get_matchup_simulation_service)
):
    """
    Simulate fantasy matchup for next N weeks with/without trade.
    
    Calculates projected fantasy points and win probability:
    - WITHOUT trade (current roster)
    - WITH trade (modified roster)
    - Point differential
    
    Uses NBA schedule + player stats from MCP server.
    """
    try:
        if simulation_service is None:
            raise HTTPException(
                status_code=503,
                detail="Simulation service unavailable. NBA MCP server is not configured or disabled. "
                       "Please set NBA_MCP_ENABLED=true and NBA_MCP_SERVER_PATH in your .env file."
            )
        
        # Get session
        db_session = repository.get_trade_analysis_session(request.session_id)
        if not db_session:
            raise HTTPException(status_code=404, detail="Trade analysis session not found")
        
        session_data = db_session.to_pydantic()
        
        logger.info(f"Starting matchup simulation for session {request.session_id}")
        
        # Run simulation in background
        async def simulate_task():
            try:
                simulation_result = await simulation_service.simulate_next_weeks(
                    league_id=session_data["league_id"],
                    user_roster_id=session_data["user_roster_id"],
                    opponent_roster_id=session_data["opponent_roster_id"],
                    user_players_out=session_data["user_players_out"],
                    user_players_in=session_data["user_players_in"],
                    weeks=request.weeks
                )
                
                # Save result
                repository.update_trade_simulation_result(
                    session_id=request.session_id,
                    simulation_result=simulation_result
                )
                
                logger.info(f"Simulation complete for session {request.session_id}")
                
            except Exception as e:
                logger.error(f"Error in simulation task: {e}")
        
        background_tasks.add_task(simulate_task)
        
        return TradeSimulationResponse(
            session_id=request.session_id,
            simulation_result={"status": "simulating", "message": "Simulation in progress"},
            message="Simulation started. Check /api/trade-assistant/analysis/{session_id} for results."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting simulation: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to start simulation: {str(e)}")


@app.get(
    "/api/trade-assistant/sessions",
    response_model=TradeAnalysisSessionListResponse,
    tags=["Trade Assistant"]
)
async def get_user_trade_analyses(
    sleeper_user_id: str = Query(..., description="Sleeper user ID"),
    league_id: Optional[str] = Query(None, description="Filter by league ID"),
    limit: int = Query(20, ge=1, le=100, description="Max sessions to return"),
    repository: BasketballRepository = Depends(get_basketball_repository)
):
    """
    Get user's trade analysis history.
    
    Returns list of recent trade analyses with their results.
    """
    try:
        db_sessions = repository.get_user_trade_analyses(
            sleeper_user_id=sleeper_user_id,
            league_id=league_id,
            limit=limit
        )
        
        sessions = []
        for session in db_sessions:
            session_data = session.to_pydantic()
            sessions.append({
                "session_id": session_data["session_id"],
                "league_id": session_data["league_id"],
                "status": session_data["status"],
                "favorability_score": session_data.get("favorability_score"),
                "created_at": session_data.get("created_at", ""),
                "completed_at": session_data.get("completed_at")
            })
        
        return TradeAnalysisSessionListResponse(
            sessions=sessions,
            total_count=len(sessions)
        )
        
    except Exception as e:
        logger.error(f"Error retrieving trade analysis sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve sessions: {str(e)}")


# ============================================================================
# Sleeper Integration Endpoints (continued below)
# ============================================================================


# Sleeper Integration Endpoints
@app.post("/api/sleeper/sync-players", response_model=SleeperSyncResponse, tags=["Sleeper", "Admin"])
async def sync_sleeper_players(
    current_user: UserModel = Depends(get_current_active_user),
    player_cache_service: PlayerCacheService = Depends(get_player_cache_service)
):
    """
    Manually sync NBA players from Sleeper API to cache.
    
    This endpoint fetches all NBA players from Sleeper API and caches them
    in Redis with a 24-hour TTL. Use sparingly as Sleeper recommends 
    calling their API once per day maximum.
    """
    try:
        # Enforce authentication for admin endpoints
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail=ErrorResponse(
                    error="AUTHENTICATION_REQUIRED",
                    message="Authentication required for admin endpoints",
                    details={}
                ).dict()
            )
        if player_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="Player cache service unavailable (Redis connection failed)",
                    details={}
                ).dict()
            )
        
        # Check if cache was recently updated to prevent abuse
        cache_stats = player_cache_service.get_cache_stats()
        if cache_stats.get("is_valid") and cache_stats.get("ttl_remaining", 0) > 82800:  # Less than 1 hour old
            logger.warning(f"User {current_user.email} attempted frequent cache sync")
        
        success, error_message = await player_cache_service.fetch_and_cache_players()
        
        if success:
            # Get updated cache stats
            updated_stats = player_cache_service.get_cache_stats()
            
            return SleeperSyncResponse(
                success=True,
                message="Successfully synced NBA players from Sleeper API",
                player_count=updated_stats.get("player_count"),
                cache_ttl=updated_stats.get("ttl_remaining")
            )
        else:
            return SleeperSyncResponse(
                success=False,
                message="Failed to sync NBA players",
                error=error_message
            )
            
    except Exception as e:
        logger.error(f"Error in sync_sleeper_players: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="SYNC_ERROR",
                message="Failed to sync players from Sleeper API",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/cache-status", response_model=SleeperCacheStatus, tags=["Sleeper"])
async def get_cache_status(
    current_user: UserModel = Depends(get_current_active_user),
    player_cache_service: PlayerCacheService = Depends(get_player_cache_service)
):
    """Get current status of the Sleeper player cache."""
    try:
        if player_cache_service is None:
            return SleeperCacheStatus(
                exists=False,
                ttl_remaining=0,
                player_count=0,
                last_updated=None,
                is_valid=False
            )
        
        cache_stats = player_cache_service.get_cache_stats()
        
        return SleeperCacheStatus(
            exists=cache_stats.get("exists", False),
            ttl_remaining=cache_stats.get("ttl_remaining"),
            player_count=cache_stats.get("player_count"),
            last_updated=cache_stats.get("last_updated"),
            is_valid=cache_stats.get("is_valid", False)
        )
        
    except Exception as e:
        logger.error(f"Error getting cache status: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="CACHE_STATUS_ERROR",
                message="Failed to retrieve cache status",
                details={"error": str(e)}
            ).dict()
        )


@app.delete("/api/sleeper/cache", tags=["Sleeper", "Admin"])
async def invalidate_cache(
    current_user: UserModel = Depends(get_current_active_user),
    player_cache_service: PlayerCacheService = Depends(get_player_cache_service)
):
    """Clear the Sleeper player cache."""
    try:
        # Enforce authentication for admin endpoints
        if not current_user:
            raise HTTPException(
                status_code=401,
                detail=ErrorResponse(
                    error="AUTHENTICATION_REQUIRED",
                    message="Authentication required for admin endpoints",
                    details={}
                ).dict()
            )
        if player_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE", 
                    message="Player cache service unavailable",
                    details={}
                ).dict()
            )
        
        success = player_cache_service.invalidate_cache()
        
        if success:
            return {"message": "Cache invalidated successfully"}
        else:
            return {"message": "Cache invalidation failed or cache was already empty"}
            
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="CACHE_INVALIDATION_ERROR",
                message="Failed to invalidate cache", 
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/players/{player_id}", response_model=SleeperPlayerResponse, tags=["Sleeper"])
async def get_sleeper_player(
    player_id: str,
    player_cache_service: PlayerCacheService = Depends(get_player_cache_service)
):
    """Get single player data from Sleeper cache."""
    try:
        if player_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="Player cache service unavailable",
                    details={}
                ).dict()
            )
        
        player_data = player_cache_service.get_player_by_id(player_id)
        
        if player_data is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PLAYER_NOT_FOUND",
                    message=f"Player {player_id} not found in cache",
                    details={"player_id": player_id}
                ).dict()
            )
        
        return SleeperPlayerResponse(
            player_id=player_id,
            name=player_data.get("name", "Unknown"),
            team=player_data.get("team"),
            positions=player_data.get("positions", []),
            status=player_data.get("status"),
            injury_status=player_data.get("injury_status")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting player {player_id}: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="PLAYER_RETRIEVAL_ERROR",
                message="Failed to retrieve player data",
                details={"player_id": player_id, "error": str(e)}
            ).dict()
        )


@app.post("/api/sleeper/players/bulk", tags=["Sleeper"])
async def get_sleeper_players_bulk(
    player_ids: list[str],
    player_cache_service: PlayerCacheService = Depends(get_player_cache_service)
):
    """Get multiple players data from Sleeper cache in one request."""
    try:
        if player_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="Player cache service unavailable",
                    details={}
                ).dict()
            )
        
        # Get all cached players at once
        cached_players = player_cache_service.get_cached_players()
        
        if cached_players is None:
            # Cache is empty, return empty results with cache status
            cache_stats = player_cache_service.get_cache_stats()
            return {
                "players": {},
                "cache_status": {
                    "is_valid": False,
                    "message": "Player cache is empty or unavailable. Please sync the cache first.",
                    "stats": cache_stats
                }
            }
        
        # Build result dictionary
        result_players = {}
        missing_players = []
        
        for player_id in player_ids:
            if player_id in cached_players:
                player_data = cached_players[player_id]
                result_players[player_id] = {
                    "player_id": player_id,
                    "name": player_data.get("name", "Unknown"),
                    "team": player_data.get("team"),
                    "positions": player_data.get("positions", []),
                    "status": player_data.get("status"),
                    "injury_status": player_data.get("injury_status")
                }
            else:
                missing_players.append(player_id)
                # Provide fallback data for missing players
                result_players[player_id] = {
                    "player_id": player_id,
                    "name": f"Player {player_id}",
                    "team": None,
                    "positions": [],
                    "status": None,
                    "injury_status": None
                }
        
        cache_stats = player_cache_service.get_cache_stats()
        
        return {
            "players": result_players,
            "cache_status": {
                "is_valid": cache_stats.get("is_valid", False),
                "player_count": cache_stats.get("player_count", 0),
                "ttl_remaining": cache_stats.get("ttl_remaining", 0),
                "last_updated": cache_stats.get("last_updated"),
                "missing_players": missing_players if missing_players else None
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting bulk players: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="BULK_PLAYER_RETRIEVAL_ERROR",
                message="Failed to retrieve players data",
                details={"error": str(e)}
            ).dict()
        )


@app.post("/api/sleeper/session", response_model=SleeperUserSessionResponse, tags=["Sleeper"])
async def start_sleeper_session(request: SleeperUserSessionRequest):
    """
    Start a Sleeper session by validating username and returning user data.
    Public endpoint - no authentication required.
    """
    try:
        logger.info(f"Starting Sleeper session for username: {request.sleeper_username}")
        
        # Use SleeperService to validate and get user data
        async with SleeperService() as sleeper:
            user_data = await sleeper.get_user_by_username(request.sleeper_username)
            
            if not user_data:
                logger.warning(f"Sleeper user not found: {request.sleeper_username}")
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error="USER_NOT_FOUND",
                        message=f"Sleeper username '{request.sleeper_username}' not found"
                    ).dict()
                )
            
            logger.info(f"Sleeper session created for user: {user_data.get('user_id')}")
            return SleeperUserSessionResponse(
                user_id=user_data["user_id"],
                username=user_data["username"],
                display_name=user_data.get("display_name"),
                avatar=user_data.get("avatar")
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error starting Sleeper session: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="SESSION_ERROR",
                message="Failed to start Sleeper session",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/leagues", response_model=List[SleeperLeagueResponse], tags=["Sleeper"])
async def get_sleeper_leagues(user_id: str, season: Optional[str] = None):
    """
    Get leagues for a Sleeper user.
    If no season is specified, fetches leagues from current season and previous 2 seasons.
    Public endpoint - no authentication required.
    """
    try:
        async with SleeperService() as sleeper:
            # If season is specified, fetch only that season
            if season is not None:
                seasons_to_fetch = [season]
                logger.info(f"Fetching Sleeper leagues for user: {user_id}, season: {season}")
            else:
                # Fetch current season and previous 2 seasons
                current_season = await sleeper.get_current_nba_season()
                if current_season is None:
                    current_season = settings.SLEEPER_DEFAULT_SEASON
                
                current_year = int(current_season)
                seasons_to_fetch = [
                    str(current_year),
                    str(current_year - 1),
                    str(current_year - 2)
                ]
                logger.info(f"Fetching Sleeper leagues for user: {user_id}, seasons: {seasons_to_fetch}")
            
            # Fetch leagues for all seasons
            all_leagues = []
            for s in seasons_to_fetch:
                leagues_data = await sleeper.get_user_leagues(user_id, "nba", s)
                
                if leagues_data is not None:
                    # Convert to response models
                    for league in leagues_data:
                        all_leagues.append(SleeperLeagueResponse(
                            league_id=league.get("league_id", ""),
                            name=league.get("name", "Unknown League"),
                            season=league.get("season", s),
                            total_rosters=league.get("total_rosters", 0),
                            sport=league.get("sport", "nba"),
                            status=league.get("status"),
                            settings=league.get("settings")
                        ))
            
            logger.info(f"Retrieved {len(all_leagues)} leagues for user {user_id}")
            return all_leagues
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Sleeper leagues: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="LEAGUES_ERROR",
                message="Failed to retrieve leagues",
                details={"user_id": user_id, "error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/rosters/{league_id}", response_model=List[SleeperRosterResponse], tags=["Sleeper"])
async def get_sleeper_rosters(league_id: str):
    """
    Get rosters for a Sleeper league.
    Public endpoint - no authentication required.
    """
    try:
        logger.info(f"Fetching Sleeper rosters for league: {league_id}")
        
        async with SleeperService() as sleeper:
            rosters_data = await sleeper.get_league_rosters(league_id)
            
            if rosters_data is None:
                logger.warning(f"League not found or error fetching rosters: {league_id}")
                raise HTTPException(
                    status_code=404,
                    detail=ErrorResponse(
                        error="LEAGUE_NOT_FOUND",
                        message=f"League '{league_id}' not found or error fetching rosters"
                    ).dict()
                )
            
            # Convert to response models
            rosters = []
            for roster in rosters_data:
                rosters.append(SleeperRosterResponse(
                    roster_id=roster.get("roster_id", 0),
                    owner_id=roster.get("owner_id", ""),
                    league_id=league_id,
                    players=roster.get("players", []),
                    starters=roster.get("starters"),
                    settings=roster.get("settings")
                ))
            
            logger.info(f"Retrieved {len(rosters)} rosters for league {league_id}")
            return rosters
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching Sleeper rosters: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="ROSTERS_ERROR",
                message="Failed to retrieve rosters",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/leagues/{league_id}/rosters/cached", response_model=List[SleeperRosterResponse], tags=["Sleeper", "Cache"])
async def get_sleeper_rosters_cached(
    league_id: str,
    refresh: bool = False,
    league_cache_service: LeagueDataCacheService = Depends(get_league_data_cache_service)
):
    """
    Get cached rosters for a Sleeper league with optional refresh.
    Public endpoint - no authentication required.
    """
    try:
        if league_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="League cache service unavailable",
                    details={}
                ).dict()
            )
        
        logger.info(f"Fetching cached rosters for league: {league_id}, refresh={refresh}")
        
        # Check cache first if not forcing refresh
        rosters_data = None
        if not refresh:
            rosters_data = league_cache_service.get_cached_rosters(league_id)
        
        # If cache miss or refresh requested, fetch and cache
        if rosters_data is None or refresh:
            success, error = await league_cache_service.cache_rosters(league_id)
            if not success:
                raise HTTPException(
                    status_code=500,
                    detail=ErrorResponse(
                        error="CACHE_ERROR",
                        message=f"Failed to cache rosters: {error}",
                        details={"league_id": league_id}
                    ).dict()
                )
            
            rosters_data = league_cache_service.get_cached_rosters(league_id)
            
            # Broadcast roster update if refreshed
            if refresh:
                await connection_manager.broadcast_roster_update(
                    league_id, 
                    "roster_change",
                    data={"refreshed": True, "source": "rosters_cached"}
                )
        
        if rosters_data is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="ROSTERS_NOT_FOUND",
                    message=f"No rosters found for league {league_id}"
                ).dict()
            )
        
        # Convert to response models
        rosters = []
        for roster in rosters_data:
            rosters.append(SleeperRosterResponse(
                roster_id=roster.get("roster_id", 0),
                owner_id=roster.get("owner_id", ""),
                league_id=league_id,
                players=roster.get("players", []),
                starters=roster.get("starters"),
                settings=roster.get("settings")
            ))
        
        logger.info(f"Retrieved {len(rosters)} cached rosters for league {league_id}")
        return rosters
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cached rosters: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="ROSTERS_ERROR",
                message="Failed to retrieve cached rosters",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/leagues/{league_id}/users", tags=["Sleeper"])
async def get_sleeper_league_users(
    league_id: str,
    sleeper_service: SleeperService = Depends(get_sleeper_service)
):
    """
    Get users (team owners) in a Sleeper league.
    Public endpoint - no authentication required.
    """
    try:
        if sleeper_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="Sleeper service unavailable",
                    details={}
                ).dict()
            )
        
        logger.info(f"Fetching users for league: {league_id}")
        
        users = await sleeper_service.get_league_users(league_id)
        
        if users is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="USERS_NOT_FOUND",
                    message=f"No users found for league {league_id}",
                    details={"league_id": league_id}
                ).dict()
            )
        
        logger.info(f"Retrieved {len(users)} users for league {league_id}")
        return users
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching league users: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="USERS_ERROR",
                message="Failed to retrieve league users",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/leagues/{league_id}/transactions", tags=["Sleeper", "Cache"])
async def get_sleeper_transactions(
    league_id: str,
    round: Optional[int] = None,
    refresh: bool = False,
    league_cache_service: LeagueDataCacheService = Depends(get_league_data_cache_service)
):
    """
    Get cached transactions for a Sleeper league with optional refresh.
    Public endpoint - no authentication required.
    """
    try:
        if league_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="League cache service unavailable",
                    details={}
                ).dict()
            )
        
        logger.info(f"Fetching cached transactions for league: {league_id}, round={round}, refresh={refresh}")
        
        # Check cache first if not forcing refresh
        transactions_data = None
        if not refresh:
            transactions_data = league_cache_service.get_cached_transactions(league_id, round)
        
        # If cache miss or refresh requested, fetch and cache
        if transactions_data is None or refresh:
            rounds_to_fetch = [round] if round else None
            success, error = await league_cache_service.cache_transactions(league_id, rounds_to_fetch)
            if not success:
                logger.warning(f"Failed to cache transactions: {error}")
            
            transactions_data = league_cache_service.get_cached_transactions(league_id, round)
        
        if transactions_data is None:
            return {}
        
        logger.info(f"Retrieved cached transactions for league {league_id}")
        return transactions_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cached transactions: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="TRANSACTIONS_ERROR",
                message="Failed to retrieve cached transactions",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/leagues/{league_id}/matchups", tags=["Sleeper", "Cache"])
async def get_sleeper_matchups(
    league_id: str,
    week: Optional[int] = None,
    refresh: bool = False,
    league_cache_service: LeagueDataCacheService = Depends(get_league_data_cache_service)
):
    """
    Get cached matchups for a Sleeper league with optional refresh.
    Public endpoint - no authentication required.
    """
    try:
        if league_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="League cache service unavailable",
                    details={}
                ).dict()
            )
        
        logger.info(f"Fetching cached matchups for league: {league_id}, week={week}, refresh={refresh}")
        
        # Check cache first if not forcing refresh
        matchups_data = None
        if not refresh:
            matchups_data = league_cache_service.get_cached_matchups(league_id, week)
        
        # If cache miss or refresh requested, fetch and cache
        if matchups_data is None or refresh:
            weeks_to_fetch = [week] if week else None
            success, error = await league_cache_service.cache_matchups(league_id, weeks_to_fetch)
            if not success:
                logger.warning(f"Failed to cache matchups: {error}")
            
            matchups_data = league_cache_service.get_cached_matchups(league_id, week)
        
        if matchups_data is None:
            return {}
        
        logger.info(f"Retrieved cached matchups for league {league_id}")
        return matchups_data
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cached matchups: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="MATCHUPS_ERROR",
                message="Failed to retrieve cached matchups",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


@app.post("/api/sleeper/leagues/{league_id}/refresh", response_model=LeagueDataRefreshResponse, tags=["Sleeper", "Cache"])
async def refresh_league_data(
    league_id: str,
    league_cache_service: LeagueDataCacheService = Depends(get_league_data_cache_service)
):
    """
    Refresh all cached data for a Sleeper league.
    Public endpoint - no authentication required.
    """
    try:
        if league_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="League cache service unavailable",
                    details={}
                ).dict()
            )
        
        logger.info(f"Refreshing all data for league: {league_id}")
        
        # Refresh all data types
        results = await league_cache_service.refresh_all_data(league_id)
        
        # Broadcast roster update
        await connection_manager.broadcast_roster_update(league_id, "roster_change", {"refreshed": True})
        
        # Build response
        errors = []
        if not results.get('rosters'):
            errors.append("Failed to refresh rosters")
        if not results.get('transactions'):
            errors.append("Failed to refresh transactions")
        if not results.get('matchups'):
            errors.append("Failed to refresh matchups")
        
        success = results.get('rosters', False) or results.get('transactions', False) or results.get('matchups', False)
        
        return LeagueDataRefreshResponse(
            success=success,
            league_id=league_id,
            rosters_updated=results.get('rosters', False),
            transactions_updated=results.get('transactions', False),
            matchups_updated=results.get('matchups', False),
            message="Refresh completed" if success else "Refresh failed",
            errors=errors if errors else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error refreshing league data: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="REFRESH_ERROR",
                message="Failed to refresh league data",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


@app.get("/api/sleeper/leagues/{league_id}/cache-status", response_model=LeagueDataCacheStatus, tags=["Sleeper", "Cache"])
async def get_league_cache_status(
    league_id: str,
    league_cache_service: LeagueDataCacheService = Depends(get_league_data_cache_service)
):
    """
    Get cache status for a Sleeper league.
    Public endpoint - no authentication required.
    """
    try:
        if league_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="League cache service unavailable",
                    details={}
                ).dict()
            )
        
        logger.info(f"Fetching cache status for league: {league_id}")
        
        stats = league_cache_service.get_cache_stats(league_id)
        
        return LeagueDataCacheStatus(**stats)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching cache status: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="CACHE_STATUS_ERROR",
                message="Failed to retrieve cache status",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


@app.delete("/api/sleeper/leagues/{league_id}/cache", tags=["Sleeper", "Cache"])
async def invalidate_league_cache(
    league_id: str,
    league_cache_service: LeagueDataCacheService = Depends(get_league_data_cache_service)
):
    """
    Invalidate all cached data for a Sleeper league.
    Public endpoint - no authentication required.
    """
    try:
        if league_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="SERVICE_UNAVAILABLE",
                    message="League cache service unavailable",
                    details={}
                ).dict()
            )
        
        logger.info(f"Invalidating cache for league: {league_id}")
        
        success = league_cache_service.invalidate_league_cache(league_id)
        
        if success:
            return {"message": f"Cache invalidated for league {league_id}", "success": True}
        else:
            return {"message": f"Failed to invalidate cache for league {league_id}", "success": False}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="CACHE_INVALIDATION_ERROR",
                message="Failed to invalidate cache",
                details={"league_id": league_id, "error": str(e)}
            ).dict()
        )


# ===== NBA Stats API Endpoints =====

@app.post("/api/nba/sync-schedule", response_model=NBAScheduleSyncResponse, tags=["NBA", "Admin"])
async def sync_nba_schedule(
    season: Optional[str] = None,
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Sync NBA game schedule from NBA CDN to cache and database.
    
    Requires authentication.
    
    Args:
        season: Season year (e.g., "2024"). If not provided, uses current season from config.
    
    Returns:
        NBAScheduleSyncResponse: Sync operation results
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable",
                    details={"check": "NBA_STATS_ENABLED setting"}
                ).dict()
            )
        
        logger.info(f"Starting NBA schedule sync for season: {season or 'current'}")
        
        # Use provided season or default from config
        sync_season = season or settings.NBA_CURRENT_SEASON
        
        # Fetch and cache schedule
        games = await nba_cache_service.fetch_and_cache_schedule(season=sync_season)
        
        if games is None:
            return NBAScheduleSyncResponse(
                success=False,
                games_synced=0,
                season=sync_season,
                cache_updated=False,
                database_updated=False,
                message="Failed to fetch schedule from NBA CDN",
                errors=["NBA CDN request failed"]
            )
        
        return NBAScheduleSyncResponse(
            success=True,
            games_synced=len(games),
            season=sync_season,
            cache_updated=True,
            database_updated=True,
            message=f"Successfully synced {len(games)} games for season {sync_season}"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing NBA schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_SYNC_ERROR",
                message="Failed to sync NBA schedule",
                details={"error": str(e)}
            ).dict()
        )


@app.post("/api/nba/sync-player-info", response_model=NBAPlayerInfoSyncResponse, tags=["NBA", "Admin"])
async def sync_nba_player_info(
    player_ids: List[str] = Body(..., description="List of Sleeper player IDs to sync"),
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service),
    player_cache_service: Optional[object] = Depends(get_player_cache_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Sync NBA player biographical information for specified Sleeper player IDs.
    
    Requires authentication.
    
    Args:
        player_ids: List of Sleeper player IDs to sync
    
    Returns:
        NBAPlayerInfoSyncResponse: Sync operation results
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable",
                    details={"check": "NBA_STATS_ENABLED setting"}
                ).dict()
            )
        
        if not player_ids:
            return NBAPlayerInfoSyncResponse(
                success=False,
                players_synced=0,
                cache_updated=False,
                database_updated=False,
                message="No player IDs provided",
                errors=["player_ids list is empty"]
            )
        
        logger.info(f"Starting NBA player info sync for {len(player_ids)} players")
        
        # Fetch and cache player info in batch
        result = await nba_cache_service.fetch_and_cache_players_batch(
            sleeper_player_ids=player_ids,
            player_cache_service=player_cache_service
        )
        
        failed_players = [pid for pid in player_ids if pid not in [p["sleeper_player_id"] for p in result]]
        
        return NBAPlayerInfoSyncResponse(
            success=len(result) > 0,
            players_synced=len(result),
            cache_updated=True,
            database_updated=True,
            message=f"Successfully synced {len(result)} of {len(player_ids)} players",
            failed_players=failed_players if failed_players else None
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error syncing NBA player info: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_SYNC_ERROR",
                message="Failed to sync NBA player info",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/nba/schedule", response_model=List[GameScheduleResponse], tags=["NBA"])
async def get_nba_schedule(
    start_date: str = Query(..., description="Start date (YYYY-MM-DD)"),
    end_date: str = Query(..., description="End date (YYYY-MM-DD)"),
    season: Optional[str] = Query(None, description="Season year (e.g., '2024')"),
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service)
):
    """
    Get NBA game schedule for a date range.
    
    Args:
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        season: Optional season filter
    
    Returns:
        List[GameScheduleResponse]: List of games
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        # Get from cache (falls back to database)
        games = await nba_cache_service.get_cached_schedule(
            start_date=start_date,
            end_date=end_date,
            season=season
        )
        
        if games is None:
            return []
        
        # Convert to response models
        return [GameScheduleResponse(**game) for game in games]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching NBA schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_FETCH_ERROR",
                message="Failed to fetch NBA schedule",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/nba/schedule/today", response_model=List[GameScheduleResponse], tags=["NBA"])
async def get_todays_nba_games(
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service)
):
    """
    Get today's NBA games with live scores.
    
    Returns:
        List[GameScheduleResponse]: List of today's games
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        # Get today's games (fetches live scores from NBA CDN)
        games = await nba_cache_service.get_todays_games()
        
        if games is None:
            return []
        
        # Convert to response models
        return [GameScheduleResponse(**game) for game in games]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching today's NBA games: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_FETCH_ERROR",
                message="Failed to fetch today's NBA games",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/nba/schedule/team/{tricode}", response_model=List[GameScheduleResponse], tags=["NBA"])
async def get_team_schedule(
    tricode: str = Path(..., description="Team tricode (e.g., 'LAL', 'BOS')"),
    start_date: Optional[str] = Query(None, description="Start date filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date filter (YYYY-MM-DD)"),
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service)
):
    """
    Get schedule for a specific NBA team.
    
    Args:
        tricode: Team tricode (e.g., 'LAL', 'BOS')
        start_date: Optional start date filter
        end_date: Optional end date filter
    
    Returns:
        List[GameScheduleResponse]: List of team's games
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        # Get from repository
        repository = get_basketball_repository()
        games = repository.get_games_by_team(
            team_tricode=tricode.upper(),
            start_date=start_date,
            end_date=end_date
        )
        
        # Convert to response models
        return [GameScheduleResponse(**game) for game in games]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching team schedule: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_FETCH_ERROR",
                message="Failed to fetch team schedule",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/nba/player-info/{player_id}", response_model=PlayerInfoResponse, tags=["NBA"])
async def get_nba_player_info(
    player_id: str = Path(..., description="Sleeper player ID"),
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service),
    player_cache_service: Optional[object] = Depends(get_player_cache_service)
):
    """
    Get NBA biographical information for a player.
    
    Args:
        player_id: Sleeper player ID
    
    Returns:
        PlayerInfoResponse: Player biographical information
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        # Get from cache (falls back to database, then fetches if needed)
        player_info = await nba_cache_service.get_cached_player_info(
            sleeper_player_id=player_id,
            player_cache_service=player_cache_service
        )
        
        if player_info is None:
            raise HTTPException(
                status_code=404,
                detail=ErrorResponse(
                    error="PLAYER_NOT_FOUND",
                    message=f"Player info not found for ID: {player_id}"
                ).dict()
            )
        
        return PlayerInfoResponse(**player_info)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching NBA player info: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_FETCH_ERROR",
                message="Failed to fetch NBA player info",
                details={"error": str(e)}
            ).dict()
        )


@app.post("/api/nba/player-info/bulk", response_model=Dict[str, PlayerInfoResponse], tags=["NBA"])
async def get_bulk_nba_player_info(
    player_ids: List[str] = Body(..., description="List of Sleeper player IDs"),
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service),
    player_cache_service: Optional[object] = Depends(get_player_cache_service)
):
    """
    Get NBA biographical information for multiple players.
    
    Args:
        player_ids: List of Sleeper player IDs
    
    Returns:
        Dict[str, PlayerInfoResponse]: Dict mapping player_id to player biographical information
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        if not player_ids:
            return {}
        
        # Get player info for each ID and build dict
        results = {}
        for player_id in player_ids:
            player_info = await nba_cache_service.get_cached_player_info(
                sleeper_player_id=player_id,
                player_cache_service=player_cache_service
            )
            
            if player_info is not None:
                results[player_id] = PlayerInfoResponse(**player_info)
        
        return results
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching bulk NBA player info: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_FETCH_ERROR",
                message="Failed to fetch bulk NBA player info",
                details={"error": str(e)}
            ).dict()
        )


@app.get("/api/nba/cache-status", response_model=NBACacheStatusResponse, tags=["NBA"])
async def get_nba_cache_status(
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service)
):
    """
    Get NBA cache status and statistics.
    
    Returns:
        NBACacheStatusResponse: Cache status information
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        # Get cache stats
        stats = await nba_cache_service.get_cache_stats()
        
        return NBACacheStatusResponse(
            schedule_cached=stats.get("schedule_cached", False),
            schedule_games_count=stats.get("schedule_games_count", 0),
            schedule_last_updated=stats.get("schedule_last_updated"),
            player_info_cached=stats.get("player_info_cached", False),
            player_info_count=stats.get("player_info_count", 0),
            player_info_last_updated=stats.get("player_info_last_updated"),
            cache_stats=stats
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching NBA cache status: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="NBA_FETCH_ERROR",
                message="Failed to fetch NBA cache status",
                details={"error": str(e)}
            ).dict()
        )


@app.delete("/api/nba/cache/schedule", tags=["NBA", "Admin"])
async def invalidate_nba_schedule_cache(
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Invalidate NBA schedule cache (clears Redis, keeps database).
    
    Requires authentication.
    
    Returns:
        dict: Invalidation result
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        success = await nba_cache_service.invalidate_schedule_cache()
        
        if success:
            logger.info("NBA schedule cache invalidated")
            return {"message": "NBA schedule cache invalidated successfully", "success": True}
        else:
            return {"message": "Failed to invalidate NBA schedule cache", "success": False}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating NBA schedule cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="CACHE_INVALIDATION_ERROR",
                message="Failed to invalidate NBA schedule cache",
                details={"error": str(e)}
            ).dict()
        )


@app.delete("/api/nba/cache/player-info", tags=["NBA", "Admin"])
async def invalidate_nba_player_info_cache(
    player_id: Optional[str] = Query(None, description="Specific player ID to invalidate (if not provided, clears all)"),
    nba_cache_service: Optional[object] = Depends(get_nba_cache_service),
    current_user: UserModel = Depends(get_current_active_user)
):
    """
    Invalidate NBA player info cache (clears Redis, keeps database).
    
    Requires authentication.
    
    Args:
        player_id: Optional specific player ID to invalidate
    
    Returns:
        dict: Invalidation result
    """
    try:
        if nba_cache_service is None:
            raise HTTPException(
                status_code=503,
                detail=ErrorResponse(
                    error="NBA_DISABLED",
                    message="NBA stats integration is not enabled or unavailable"
                ).dict()
            )
        
        success = await nba_cache_service.invalidate_player_info_cache(player_id=player_id)
        
        if success:
            msg = f"NBA player info cache invalidated for {player_id}" if player_id else "All NBA player info cache invalidated"
            logger.info(msg)
            return {"message": msg, "success": True}
        else:
            return {"message": "Failed to invalidate NBA player info cache", "success": False}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error invalidating NBA player info cache: {e}")
        raise HTTPException(
            status_code=500,
            detail=ErrorResponse(
                error="CACHE_INVALIDATION_ERROR",
                message="Failed to invalidate NBA player info cache",
                details={"error": str(e)}
            ).dict()
        )


# ===============================
# Roster Ranking Endpoints
# ===============================

@app.get(
    "/api/roster-ranking/{league_id}",
    response_model=RosterRankingResponse,
    tags=["Roster Ranking"]
)
async def get_roster_ranking(
    league_id: str,
    refresh: bool = Query(False, description="Force refresh from API/cache"),
    ranking_service = Depends(get_roster_ranking_service)
):
    """
    Get league-wide roster rankings (fantasy points, category breakdowns, percentiles).
    """
    if ranking_service is None:
        raise HTTPException(status_code=503, detail="Roster ranking service unavailable.")
    try:
        result = await ranking_service.calculate_league_rankings(league_id, force_refresh=refresh)
        return result
    except Exception as e:
        logger.error(f"Error calculating roster rankings: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to calculate roster rankings: {str(e)}")

@app.get(
    "/api/roster-ranking/{league_id}/cache-status",
    response_model=RosterRankingCacheStatus,
    tags=["Roster Ranking"]
)
async def get_roster_ranking_cache_status(
    league_id: str,
    ranking_service = Depends(get_roster_ranking_service)
):
    """
    Get cache status for league roster rankings.
    """
    if ranking_service is None:
        raise HTTPException(status_code=503, detail="Roster ranking service unavailable.")
    try:
        return ranking_service.get_cache_stats(league_id)
    except Exception as e:
        logger.error(f"Error getting ranking cache status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to get ranking cache status: {str(e)}")

@app.delete(
    "/api/roster-ranking/{league_id}/cache",
    tags=["Roster Ranking"]
)
async def delete_roster_ranking_cache(
    league_id: str,
    ranking_service = Depends(get_roster_ranking_service)
):
    """
    Clear cached league roster rankings.
    """
    if ranking_service is None:
        raise HTTPException(status_code=503, detail="Roster ranking service unavailable.")
    try:
        ranking_service.invalidate_rankings_cache(league_id)
        return {"success": True, "message": "Rankings cache cleared"}
    except Exception as e:
        logger.error(f"Error clearing ranking cache: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to clear ranking cache: {str(e)}")


@app.websocket("/ws/league/{league_id}")
async def websocket_league_updates(websocket: WebSocket, league_id: str):
    """WebSocket endpoint for league roster updates."""
    await connection_manager.connect_to_league(websocket, league_id)
    
    try:
        # Keep connection alive and handle any incoming messages
        while True:
            try:
                # Wait for messages
                message = await websocket.receive_text()
                
                # Parse message
                try:
                    data = json.loads(message)
                    message_type = data.get("type", "unknown")
                    
                    # Handle ping
                    if message_type == "ping":
                        await websocket.send_text(json.dumps({
                            "type": "pong",
                            "timestamp": datetime.utcnow().isoformat()
                        }))
                    
                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from WebSocket in league {league_id}")
                
            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.error(f"Error handling WebSocket message in league {league_id}: {e}")
                break
    
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"Error in WebSocket connection for league {league_id}: {e}")
    finally:
        connection_manager.disconnect_from_league(websocket)


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