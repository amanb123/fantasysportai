"""
Pydantic models for authentication API requests and responses.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class UserRegisterRequest(BaseModel):
    """User registration request payload."""
    
    email: EmailStr
    password: str
    confirm_password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "password123",
                "confirm_password": "password123"
            }
        }


class UserLoginRequest(BaseModel):
    """User login request payload (OAuth2 compatible)."""
    
    username: str  # Named 'username' for OAuth2 compatibility, but expects email
    password: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "username": "user@example.com",
                "password": "password123"
            }
        }


class TokenResponse(BaseModel):
    """JWT token response."""
    
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    
    class Config:
        json_schema_extra = {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer"
            }
        }


class UserResponse(BaseModel):
    """Safe user data response (excluding password)."""
    
    id: int
    email: str
    sleeper_username: Optional[str] = None
    sleeper_user_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "id": 1,
                "email": "user@example.com",
                "sleeper_username": "sleeper_user",
                "sleeper_user_id": "123456789",
                "is_active": True,
                "created_at": "2023-01-01T00:00:00",
                "last_login": "2023-01-01T12:00:00"
            }
        }


class RefreshTokenRequest(BaseModel):
    """Refresh token request."""
    
    refresh_token: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
            }
        }


class LinkSleeperRequest(BaseModel):
    """Sleeper account linking request."""
    
    sleeper_username: str
    
    class Config:
        json_schema_extra = {
            "example": {
                "sleeper_username": "sleeper_user"
            }
        }