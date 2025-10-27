"""
Authentication dependency functions for FastAPI.
"""

from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session
import logging

from backend.dependencies import get_basketball_repository
from backend.session.repository import BasketballRepository
from backend.session.models import UserModel
from .security import decode_access_token

logger = logging.getLogger(__name__)

# OAuth2 password bearer for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


def get_current_user(
    token: Optional[str] = Depends(oauth2_scheme),
    repository: BasketballRepository = Depends(get_basketball_repository)
) -> Optional[UserModel]:
    """
    Get current authenticated user from JWT token.
    Modified to return None instead of raising exceptions for optional auth.
    
    Args:
        token: JWT token from Authorization header
        
    Returns:
        Optional[UserModel]: Current authenticated user or None
    """
    if not token:
        logger.debug("No token provided for optional authentication")
        return None
    
    try:
        # Decode token
        payload = decode_access_token(token)
        if payload is None:
            logger.debug("Invalid token for optional authentication")
            return None
        
        # Extract user email from token
        email: str = payload.get("sub")
        if email is None:
            logger.debug("No email in token for optional authentication")
            return None
        
        # Get user from database using injected repository
        user = repository.get_user_by_email(email)
        if user is None:
            logger.debug(f"User not found for email {email} in optional authentication")
            return None
        
        return user
    
    except Exception as e:
        logger.debug(f"Error in optional authentication: {e}")
        return None


def get_current_active_user(
    current_user: Optional[UserModel] = Depends(get_current_user)
) -> Optional[UserModel]:
    """
    Get current authenticated and active user.
    Modified to return None instead of raising exceptions for optional auth.
    
    Args:
        current_user: Current user from get_current_user dependency
        
    Returns:
        Optional[UserModel]: Current active user or None
    """
    if not current_user:
        return None
    
    if not current_user.is_active:
        logger.debug(f"User {current_user.email} is inactive in optional authentication")
        return None
    
    return current_user


def get_optional_user(
    repository: BasketballRepository = Depends(get_basketball_repository),
    token: Optional[str] = Depends(oauth2_scheme)
) -> Optional[UserModel]:
    """
    Explicitly optional user dependency that returns None without errors.
    Use this in trade endpoints that should work without auth.
    """
    return get_current_user(token, repository)