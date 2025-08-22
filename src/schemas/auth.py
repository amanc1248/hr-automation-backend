from pydantic import BaseModel, EmailStr, Field, validator
from typing import Optional, Dict, Any, List
from datetime import datetime
from uuid import UUID

class CompanyCreate(BaseModel):
    """Schema for creating a company"""
    name: str = Field(..., min_length=1, max_length=255, description="Company name")
    domain: Optional[str] = Field(None, max_length=255, description="Company domain")
    description: Optional[str] = Field(None, description="Company description")
    website: Optional[str] = Field(None, max_length=500, description="Company website")
    industry: Optional[str] = Field(None, max_length=100, description="Industry")
    size: Optional[str] = Field(None, description="Company size: startup, small, medium, large, enterprise")
    
    @validator('size')
    def validate_size(cls, v):
        if v and v not in ['startup', 'small', 'medium', 'large', 'enterprise']:
            raise ValueError('Size must be one of: startup, small, medium, large, enterprise')
        return v

class AdminUserCreate(BaseModel):
    """Schema for creating admin user"""
    email: EmailStr = Field(..., description="Admin email address")
    first_name: str = Field(..., min_length=1, max_length=100, description="First name")
    last_name: str = Field(..., min_length=1, max_length=100, description="Last name")
    password: str = Field(..., min_length=8, description="Password (min 8 characters)")
    phone: Optional[str] = Field(None, max_length=20, description="Phone number")

class CompanyRegistration(BaseModel):
    """Schema for complete company registration"""
    company: CompanyCreate
    admin_user: AdminUserCreate

class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr = Field(..., description="Email address")
    password: str = Field(..., description="Password")

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
    preferences: Dict[str, Any]
    
    # Company and role info
    company_id: UUID
    role_id: UUID
    role_name: Optional[str]
    role_display_name: Optional[str]
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CompanyResponse(BaseModel):
    """Schema for company response"""
    id: UUID
    name: str
    domain: Optional[str]
    description: Optional[str]
    website: Optional[str]
    industry: Optional[str]
    size: Optional[str]
    logo_url: Optional[str]
    is_active: bool
    settings: Dict[str, Any]
    
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AuthResponse(BaseModel):
    """Schema for authentication response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse
    company: CompanyResponse

class TokenData(BaseModel):
    """Schema for token data"""
    user_id: Optional[UUID] = None
    email: Optional[str] = None
    company_id: Optional[UUID] = None
    role_id: Optional[UUID] = None

class PasswordReset(BaseModel):
    """Schema for password reset request"""
    email: EmailStr = Field(..., description="Email address")

class PasswordChange(BaseModel):
    """Schema for password change"""
    current_password: str = Field(..., description="Current password")
    new_password: str = Field(..., min_length=8, description="New password (min 8 characters)")

class RefreshToken(BaseModel):
    """Schema for token refresh"""
    refresh_token: str = Field(..., description="Refresh token")

class UserRoleResponse(BaseModel):
    """Schema for user role response"""
    id: UUID
    name: str
    display_name: str
    description: Optional[str]
    permissions: List[str]
    approval_types: List[str]
    is_system_role: bool
    
    class Config:
        from_attributes = True

class UserInviteCreate(BaseModel):
    """Schema for creating user invitation"""
    email: EmailStr = Field(..., description="Email address to invite")
    role_id: UUID = Field(..., description="Role ID to assign")
    
class UserInviteResponse(BaseModel):
    """Schema for user invitation response"""
    id: UUID
    email: str
    role_id: UUID
    invited_by: UUID
    invitation_token: str
    expires_at: datetime
    is_accepted: bool
    accepted_at: Optional[datetime]
    
    created_at: datetime
    
    class Config:
        from_attributes = True
