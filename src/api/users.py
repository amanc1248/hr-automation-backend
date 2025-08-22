from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import selectinload
from typing import List, Optional
from uuid import UUID
import secrets
import string
from datetime import datetime

from core.database import get_db
from api.auth import get_current_user
from models.user import Profile, UserRole, Company
from schemas.users import (
    UserCreate, UserUpdate, UserResponse, UserListResponse,
    PasswordReset, PasswordChange
)
from services.auth_service import AuthService

router = APIRouter(prefix="/api/users", tags=["users"])

# Initialize auth service for password hashing
auth_service = AuthService()

def generate_temp_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(alphabet) for _ in range(length))

@router.get("", response_model=List[UserResponse])
async def get_company_users(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    role_filter: Optional[str] = None,
    status_filter: Optional[str] = None
):
    """Get all users in the current user's company (Admin only)"""
    
    # Check if current user is admin
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view company users"
        )
    
    # Build query
    query = select(Profile).where(
        and_(
            Profile.company_id == current_user.company_id,
            Profile.is_active == True
        )
    ).options(
        # Eager load related data
        selectinload(Profile.role),
        selectinload(Profile.company)
    )
    
    # Apply filters
    if search:
        search_filter = or_(
            Profile.first_name.ilike(f"%{search}%"),
            Profile.last_name.ilike(f"%{search}%"),
            Profile.email.ilike(f"%{search}%")
        )
        query = query.where(search_filter)
    
    if role_filter:
        query = query.join(UserRole).where(UserRole.name == role_filter)
    
    if status_filter == "pending_first_login":
        query = query.where(Profile.first_login_at.is_(None))
    elif status_filter == "active":
        query = query.where(Profile.first_login_at.is_not(None))
    
    # Apply pagination
    query = query.offset(skip).limit(limit).order_by(Profile.created_at.desc())
    
    result = await db.execute(query)
    users = result.scalars().all()
    
    return [
        UserResponse(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            avatar_url=user.avatar_url,
            phone=user.phone,
            is_active=user.is_active,
            last_login=user.last_login,
            first_login_at=user.first_login_at,
            must_change_password=user.must_change_password,
            preferences=user.preferences,
            company_id=user.company_id,
            role_id=user.role_id,
            role_name=user.role.name if user.role else None,
            role_display_name=user.role.display_name if user.role else None,
            created_by=user.created_by,
            created_at=user.created_at,
            updated_at=user.updated_at
        )
        for user in users
    ]

@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new user (Admin only)"""
    
    # Check if current user is admin
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create users"
        )
    
    # Check if email already exists in the company
    existing_user = await db.execute(
        select(Profile).where(
            and_(
                Profile.email == user_data.email,
                Profile.company_id == current_user.company_id
            )
        )
    )
    if existing_user.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email already exists in your company"
        )
    
    # Verify role exists and belongs to company (or is system role)
    role_result = await db.execute(
        select(UserRole).where(UserRole.id == user_data.role_id)
    )
    role = role_result.scalar_one_or_none()
    if not role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid role specified"
        )
    
    # Generate password if not provided
    password = user_data.password or generate_temp_password()
    password_hash = auth_service.get_password_hash(password)
    
    # Create new user
    new_user = Profile(
        email=user_data.email,
        first_name=user_data.first_name,
        last_name=user_data.last_name,
        phone=user_data.phone,
        password_hash=password_hash,
        company_id=current_user.company_id,
        role_id=user_data.role_id,
        is_active=True,
        must_change_password=True,  # Force password change on first login
        created_by=current_user.id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Load role information
    await db.refresh(new_user, ["role"])
    
    response = UserResponse(
        id=new_user.id,
        email=new_user.email,
        first_name=new_user.first_name,
        last_name=new_user.last_name,
        avatar_url=new_user.avatar_url,
        phone=new_user.phone,
        is_active=new_user.is_active,
        last_login=new_user.last_login,
        first_login_at=new_user.first_login_at,
        must_change_password=new_user.must_change_password,
        preferences=new_user.preferences,
        company_id=new_user.company_id,
        role_id=new_user.role_id,
        role_name=new_user.role.name if new_user.role else None,
        role_display_name=new_user.role.display_name if new_user.role else None,
        created_by=new_user.created_by,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at
    )
    
    # Add the generated password to response for admin to see
    response.temporary_password = password if not user_data.password else None
    
    return response

@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get a specific user (Admin only or own profile)"""
    
    # Users can view their own profile, admins can view any company user
    if current_user.id != user_id and current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Get user
    result = await db.execute(
        select(Profile).where(
            and_(
                Profile.id == user_id,
                Profile.company_id == current_user.company_id if current_user.role.name == "admin" else True
            )
        ).options(
            selectinload(Profile.role)
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        phone=user.phone,
        is_active=user.is_active,
        last_login=user.last_login,
        first_login_at=user.first_login_at,
        must_change_password=user.must_change_password,
        preferences=user.preferences,
        company_id=user.company_id,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        role_display_name=user.role.display_name if user.role else None,
        created_by=user.created_by,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.put("/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: UUID,
    user_data: UserUpdate,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update a user (Admin only or own profile for limited fields)"""
    
    # Get user to update
    result = await db.execute(
        select(Profile).where(
            and_(
                Profile.id == user_id,
                Profile.company_id == current_user.company_id
            )
        ).options(selectinload(Profile.role))
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check permissions
    is_admin = current_user.role.name == "admin"
    is_own_profile = current_user.id == user_id
    
    if not (is_admin or is_own_profile):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied"
        )
    
    # Update allowed fields
    if user_data.first_name is not None:
        user.first_name = user_data.first_name
    if user_data.last_name is not None:
        user.last_name = user_data.last_name
    if user_data.phone is not None:
        user.phone = user_data.phone
    
    # Admin-only updates
    if is_admin:
        if user_data.email is not None:
            # Check email uniqueness
            existing = await db.execute(
                select(Profile).where(
                    and_(
                        Profile.email == user_data.email,
                        Profile.company_id == current_user.company_id,
                        Profile.id != user_id
                    )
                )
            )
            if existing.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already exists"
                )
            user.email = user_data.email
        
        if user_data.role_id is not None:
            # Verify role exists
            role_result = await db.execute(
                select(UserRole).where(UserRole.id == user_data.role_id)
            )
            if not role_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid role"
                )
            user.role_id = user_data.role_id
        
        if user_data.is_active is not None:
            user.is_active = user_data.is_active
    
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    await db.refresh(user, ["role"])
    
    return UserResponse(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        avatar_url=user.avatar_url,
        phone=user.phone,
        is_active=user.is_active,
        last_login=user.last_login,
        first_login_at=user.first_login_at,
        must_change_password=user.must_change_password,
        preferences=user.preferences,
        company_id=user.company_id,
        role_id=user.role_id,
        role_name=user.role.name if user.role else None,
        role_display_name=user.role.display_name if user.role else None,
        created_by=user.created_by,
        created_at=user.created_at,
        updated_at=user.updated_at
    )

@router.post("/{user_id}/reset-password")
async def reset_user_password(
    user_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Reset user password (Admin only)"""
    
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can reset passwords"
        )
    
    # Get user
    result = await db.execute(
        select(Profile).where(
            and_(
                Profile.id == user_id,
                Profile.company_id == current_user.company_id
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Generate new temporary password
    new_password = generate_temp_password()
    user.password_hash = auth_service.get_password_hash(new_password)
    user.must_change_password = True
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {
        "message": "Password reset successfully",
        "temporary_password": new_password
    }

@router.post("/{user_id}/deactivate")
async def deactivate_user(
    user_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Deactivate a user (Admin only)"""
    
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can deactivate users"
        )
    
    # Prevent self-deactivation
    if current_user.id == user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot deactivate your own account"
        )
    
    # Get user
    result = await db.execute(
        select(Profile).where(
            and_(
                Profile.id == user_id,
                Profile.company_id == current_user.company_id
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = False
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "User deactivated successfully"}

@router.post("/{user_id}/activate")
async def activate_user(
    user_id: UUID,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Activate a user (Admin only)"""
    
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can activate users"
        )
    
    # Get user
    result = await db.execute(
        select(Profile).where(
            and_(
                Profile.id == user_id,
                Profile.company_id == current_user.company_id
            )
        )
    )
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    user.updated_at = datetime.utcnow()
    
    await db.commit()
    
    return {"message": "User activated successfully"}
