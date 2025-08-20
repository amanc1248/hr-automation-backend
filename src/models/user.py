"""
User and profile models for HR Automation System.
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional
from enum import Enum
from uuid import UUID

from .base import BaseEntity, BaseCreate, BaseUpdate


class UserRole(str, Enum):
    """User roles in the system"""
    HR_MANAGER = "hr_manager"
    INTERVIEWER = "interviewer"
    ADMIN = "admin"


class UserProfile(BaseEntity):
    """User profile model"""
    email: EmailStr = Field(description="User email address")
    full_name: Optional[str] = Field(default=None, description="User's full name")
    role: UserRole = Field(default=UserRole.HR_MANAGER, description="User role in the system")
    company_id: Optional[UUID] = Field(default=None, description="Associated company ID")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "hr@company.com",
                "full_name": "Jane Smith",
                "role": "hr_manager",
                "company_id": "660e8400-e29b-41d4-a716-446655440001",
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z"
            }
        }
    }


class UserCreate(BaseCreate):
    """Model for creating a new user profile"""
    email: EmailStr = Field(description="User email address")
    full_name: Optional[str] = Field(default=None, description="User's full name")
    role: UserRole = Field(default=UserRole.HR_MANAGER, description="User role in the system")
    company_id: Optional[UUID] = Field(default=None, description="Associated company ID")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "hr@company.com",
                "full_name": "Jane Smith",
                "role": "hr_manager",
                "company_id": "660e8400-e29b-41d4-a716-446655440001"
            }
        }
    }


class UserUpdate(BaseUpdate):
    """Model for updating user profile"""
    full_name: Optional[str] = Field(default=None, description="User's full name")
    role: Optional[UserRole] = Field(default=None, description="User role in the system")
    company_id: Optional[UUID] = Field(default=None, description="Associated company ID")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "Jane Smith Updated",
                "role": "admin"
            }
        }
    }


class UserLogin(BaseModel):
    """Model for user login"""
    email: EmailStr = Field(description="User email address")
    password: str = Field(min_length=8, description="User password")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "hr@company.com",
                "password": "securepassword123"
            }
        }
    }


class UserToken(BaseModel):
    """Model for authentication token response"""
    access_token: str = Field(description="JWT access token")
    token_type: str = Field(default="bearer", description="Token type")
    expires_in: int = Field(description="Token expiration time in seconds")
    user: UserProfile = Field(description="User profile information")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
                "token_type": "bearer",
                "expires_in": 3600,
                "user": {
                    "id": "550e8400-e29b-41d4-a716-446655440000",
                    "email": "hr@company.com",
                    "full_name": "Jane Smith",
                    "role": "hr_manager"
                }
            }
        }
    }
