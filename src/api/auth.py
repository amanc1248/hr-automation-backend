from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from core.database import get_db
from services.auth_service import AuthService
from schemas.auth import (
    CompanyRegistration, UserLogin, AuthResponse, UserResponse, 
    RefreshToken, UserRoleResponse, UserInviteCreate, UserInviteResponse,
    PasswordReset, PasswordChange
)
from models.user import Profile, UserRole

router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer()
auth_service = AuthService()

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db)
) -> Profile:
    """Get current authenticated user"""
    try:
        token = credentials.credentials
        user = await auth_service.get_current_user(db, token)
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

@router.post("/register", response_model=AuthResponse)
async def register_company(
    registration: CompanyRegistration,
    db: AsyncSession = Depends(get_db)
):
    """Register new company with admin user"""
    try:
        result = await auth_service.register_company_and_admin(db, registration)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed"
        )

@router.post("/login", response_model=AuthResponse)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db)
):
    """User login"""
    try:
        result = await auth_service.login_user(db, login_data)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed"
        )

@router.post("/refresh", response_model=AuthResponse)
async def refresh_token(
    refresh_data: RefreshToken,
    db: AsyncSession = Depends(get_db)
):
    """Refresh access token"""
    try:
        result = await auth_service.refresh_access_token(db, refresh_data.refresh_token)
        return result
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed"
        )

@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: Profile = Depends(get_current_user)
):
    """Get current user information"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        avatar_url=current_user.avatar_url,
        phone=current_user.phone,
        is_active=current_user.is_active,
        last_login=current_user.last_login,
        preferences=current_user.preferences,
        company_id=current_user.company_id,
        role_id=current_user.role_id,
        role_name=current_user.role.name if current_user.role else None,
        role_display_name=current_user.role.display_name if current_user.role else None,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at
    )

@router.post("/logout")
async def logout(
    current_user: Profile = Depends(get_current_user)
):
    """User logout (client should discard tokens)"""
    return {"message": "Successfully logged out"}

@router.get("/roles", response_model=List[UserRoleResponse])
async def get_user_roles(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get available user roles for the company"""
    from sqlalchemy import select
    
    result = await db.execute(
        select(UserRole).where(
            (UserRole.is_system_role == False) | 
            (UserRole.name.in_(["admin", "hr_manager"]))
        ).order_by(UserRole.display_name)
    )
    roles = result.scalars().all()
    
    return [
        UserRoleResponse(
            id=role.id,
            name=role.name,
            display_name=role.display_name,
            description=role.description,
            permissions=role.permissions,
            approval_types=role.approval_types,
            is_system_role=role.is_system_role
        )
        for role in roles
    ]

@router.post("/invite", response_model=UserInviteResponse)
async def invite_user(
    invitation: UserInviteCreate,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Invite user to company"""
    try:
        # Check if current user has permission to invite
        if not current_user.role or current_user.role.name not in ["admin", "hr_manager"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions to invite users"
            )
        
        result = await auth_service.create_user_invitation(
            db, 
            str(current_user.company_id), 
            str(current_user.id), 
            invitation
        )
        
        return UserInviteResponse(
            id=result.id,
            email=result.email,
            role_id=result.role_id,
            invited_by=result.invited_by,
            invitation_token=result.invitation_token,
            expires_at=result.expires_at,
            is_accepted=result.is_accepted,
            accepted_at=result.accepted_at,
            created_at=result.created_at
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Invitation failed"
        )

@router.post("/password-reset")
async def request_password_reset(
    reset_data: PasswordReset,
    db: AsyncSession = Depends(get_db)
):
    """Request password reset (placeholder - implement email sending)"""
    # TODO: Implement password reset email sending
    return {"message": "Password reset email sent (if email exists)"}

@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Change user password"""
    try:
        from sqlalchemy import select
        from models.user import User
        
        # Get user
        result = await db.execute(
            select(User).where(User.profile_id == current_user.id)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Verify current password
        if not auth_service.verify_password(password_data.current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Current password is incorrect"
            )
        
        # Update password
        user.password_hash = auth_service.get_password_hash(password_data.new_password)
        await db.commit()
        
        return {"message": "Password changed successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password change failed"
        )

@router.get("/health")
async def auth_health():
    """Authentication service health check"""
    return {
        "status": "healthy",
        "service": "authentication",
        "timestamp": "2025-01-01T00:00:00Z"
    }
