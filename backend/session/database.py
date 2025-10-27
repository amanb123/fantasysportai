"""
Database initialization module for the Fantasy Basketball League.
"""

from sqlmodel import create_engine, SQLModel
from typing import Optional
import logging

logger = logging.getLogger(__name__)

# Global variables
_engine: Optional[object] = None
_repository: Optional[object] = None


def init_database(database_url: str, echo: bool = False):
    """
    Initialize the database connection and create tables.
    
    Args:
        database_url: Neon PostgreSQL connection string
        echo: Enable SQL query logging
        
    Returns:
        SQLModel engine instance
    """
    global _engine
    
    try:
        logger.info(f"Initializing database connection to: {database_url[:50]}...")
        
        # Create SQLModel engine
        _engine = create_engine(database_url, echo=echo)
        
        # Create all tables
        SQLModel.metadata.create_all(_engine)
        
        logger.info("Database initialization successful")
        return _engine
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise


def get_engine():
    """
    Get the database engine.
    
    Returns:
        SQLModel engine instance
        
    Raises:
        RuntimeError: If database is not initialized
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    return _engine


def ensure_refresh_token_columns():
    """
    Ensure refresh token columns exist in the user table.
    This handles migration for existing databases.
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    try:
        from sqlalchemy import text, inspect
        
        inspector = inspect(_engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        # Check if refresh token columns exist
        if 'hashed_refresh_token' not in columns or 'refresh_token_expires_at' not in columns:
            logger.info("Adding refresh token columns to users table...")
            
            with _engine.begin() as conn:
                if 'hashed_refresh_token' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN hashed_refresh_token VARCHAR"))
                    
                if 'refresh_token_expires_at' not in columns:
                    conn.execute(text("ALTER TABLE users ADD COLUMN refresh_token_expires_at TIMESTAMP"))
                    
            logger.info("Refresh token columns added successfully")
        else:
            logger.info("Refresh token columns already exist")
            
    except Exception as e:
        logger.warning(f"Could not check/add refresh token columns: {e}")
        # Continue anyway, as create_all will handle new installations


def ensure_trade_sessions_user_id_column():
    """
    Ensure user_id column exists in the trade_sessions table.
    This handles migration for existing databases.
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    try:
        from sqlalchemy import text, inspect
        
        inspector = inspect(_engine)
        
        # Check if trade_sessions table exists
        if 'trade_sessions' not in inspector.get_table_names():
            logger.info("trade_sessions table does not exist yet, will be created by create_all")
            return
            
        columns = [col['name'] for col in inspector.get_columns('trade_sessions')]
        
        # Check if user_id column exists
        if 'user_id' not in columns:
            logger.info("Adding user_id column to trade_sessions table...")
            
            with _engine.begin() as conn:
                # Add the user_id column
                conn.execute(text("ALTER TABLE trade_sessions ADD COLUMN user_id INTEGER"))
                
                # Add index for better performance
                conn.execute(text("CREATE INDEX IF NOT EXISTS ix_trade_sessions_user_id ON trade_sessions (user_id)"))
                    
            logger.info("user_id column added to trade_sessions successfully")
        else:
            logger.info("user_id column already exists in trade_sessions")
            
    except Exception as e:
        logger.warning(f"Could not check/add user_id column to trade_sessions: {e}")
        # Continue anyway, as create_all will handle new installations


def ensure_roster_chat_tables():
    """
    Ensure roster chat tables exist.
    This handles migration for existing databases.
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    try:
        from sqlalchemy import inspect
        from backend.session.models import RosterChatSessionModel, RosterChatMessageModel
        
        inspector = inspect(_engine)
        existing_tables = inspector.get_table_names()
        
        # Check if roster chat tables exist
        if 'roster_chat_sessions' not in existing_tables or 'roster_chat_messages' not in existing_tables:
            logger.info("Creating roster chat tables...")
            
            # Create tables
            SQLModel.metadata.create_all(_engine, tables=[
                RosterChatSessionModel.__table__,
                RosterChatMessageModel.__table__
            ])
            
            logger.info("Roster chat tables created successfully")
        else:
            logger.info("Roster chat tables already exist")
            
    except Exception as e:
        logger.warning(f"Could not check/create roster chat tables: {e}")
        # Continue anyway


def ensure_trade_analysis_tables():
    """
    Ensure trade analysis tables exist.
    This handles migration for existing databases.
    """
    global _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    try:
        from sqlalchemy import inspect
        from backend.session.models import TradeAnalysisSessionModel
        
        inspector = inspect(_engine)
        existing_tables = inspector.get_table_names()
        
        # Check if trade analysis table exists
        if 'trade_analysis_sessions' not in existing_tables:
            logger.info("Creating trade analysis tables...")
            
            # Create table
            SQLModel.metadata.create_all(_engine, tables=[
                TradeAnalysisSessionModel.__table__
            ])
            
            logger.info("Trade analysis tables created successfully")
        else:
            logger.info("Trade analysis tables already exist")
            
    except Exception as e:
        logger.warning(f"Could not check/create trade analysis tables: {e}")
        # Continue anyway


def get_repository():
    """
    Get the repository instance (singleton).
    
    Returns:
        BasketballRepository instance
        
    Raises:
        RuntimeError: If database is not initialized
    """
    global _repository, _engine
    
    if _engine is None:
        raise RuntimeError("Database not initialized. Call init_database() first.")
    
    if _repository is None:
        from .repository import BasketballRepository
        _repository = BasketballRepository(_engine)
    
    return _repository