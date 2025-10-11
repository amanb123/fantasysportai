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