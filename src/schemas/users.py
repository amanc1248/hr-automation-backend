from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class UserCreate(BaseModel):
    """Schema for creating a new user"""
    email: EmailStr = Field(..., description="User email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role_id: UUID = Field(..., description="Role ID to assign to user")
    password: Optional[str] = Field(None, min_length=8, description="Password (if not provided, will be auto-generated)")

class UserUpdate(BaseModel):
    """Schema for updating user information"""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100, description="First name")
    last_name: Optional[str] = Field(None, min_length=1, max_length=100, description="Last name")
    email: Optional[EmailStr] = Field(None, description="Email address")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")
    role_id: Optional[UUID] = Field(None, description="Role ID")
    is_active: Optional[bool] = Field(None, description="Active status")

class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: str
    first_name: Optional[str]
    last_name: Optional[str]
    avatar_url: Optional[str]
    phone: Optional[str]
    is_active: bool
    last_login: Optional[datetime]
    first_login_at: Optional[datetime]
    must_change_password: bool
    preferences: Dict[str, Any]
    
    # Company and role info
    company_id: UUID
    role_id: UUID
    role_name: Optional[str]
    role_display_name: Optional[str]
    
    # Audit fields
    created_by: Optional[UUID]
    created_at: datetime
    updated_at: datetime
    
    # Optional field for temporary password (only shown when creating user)
    temporary_password: Optional[str] = None
    
    class Config:
        from_attributes = True

class UserListResponse(BaseModel):
    """Schema for paginated user list"""
    users: list[UserResponse]
    total: int
    page: int
    per_page: int
    total_pages: int

class PasswordReset(BaseModel):
    """Schema for password reset"""
    user_id: UUID = Field(..., description="User ID to reset password for")

class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")
    confirm_password: str = Field(..., description="Confirm new password")
    
    @validator('confirm_password')
    def passwords_match(cls, v, values):
        if 'new_password' in values and v != values['new_password']:
            raise ValueError('Passwords do not match')
        return v

class UserStats(BaseModel):
    """Schema for user statistics"""
    total_users: int
    active_users: int
    pending_first_login: int
    inactive_users: int
    users_by_role: Dict[str, int]
    recent_logins: int  # Users who logged in within last 7 days

class UserActivityResponse(BaseModel):
    """Schema for user activity tracking"""
    user_id: UUID
    user_name: str
    last_login: Optional[datetime]
    login_count: int
    actions_count: int
    status: str  # "active", "pending", "inactive"
