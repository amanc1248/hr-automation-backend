from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from uuid import uuid4
import secrets

from passlib.context import CryptContext
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from core.config import settings
from models.user import User, Company, Profile, UserRole, UserInvitation
from schemas.auth import CompanyRegistration, UserLogin, TokenData, AuthResponse, UserInviteCreate

class AuthService:
    """Authentication service"""
    
    def __init__(self):
        self.pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        """Verify password against hash"""
        return self.pwd_context.verify(plain_password, hashed_password)
    
    def get_password_hash(self, password: str) -> str:
        """Generate password hash"""
        return self.pwd_context.hash(password)
    
    def create_access_token(self, data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
        """Create access token"""
        to_encode = data.copy()
        
        if expires_delta:
            expire = datetime.utcnow() + expires_delta
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        to_encode.update({"exp": expire, "type": "access"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def create_refresh_token(self, data: Dict[str, Any]) -> str:
        """Create refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    
    def verify_token(self, token: str, token_type: str = "access") -> Optional[TokenData]:
        """Verify and decode token"""
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            
            # Check token type
            if payload.get("type") != token_type:
                return None
            
            user_id = payload.get("sub")
            email = payload.get("email")
            company_id = payload.get("company_id")
            role_id = payload.get("role_id")
            
            if user_id is None:
                return None
            
            return TokenData(
                user_id=user_id,
                email=email,
                company_id=company_id,
                role_id=role_id
            )
        except JWTError:
            return None
    
    async def register_company_and_admin(
        self, 
        db: AsyncSession, 
        registration: CompanyRegistration
    ) -> AuthResponse:
        """Register new company with admin user"""
        
        # Check if email already exists
        existing_user = await db.execute(
            select(User).where(User.email == registration.admin_user.email)
        )
        if existing_user.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Check if company domain already exists
        if registration.company.domain:
            existing_company = await db.execute(
                select(Company).where(Company.domain == registration.company.domain)
            )
            if existing_company.scalar_one_or_none():
                raise ValueError("Company domain already registered")
        
        # Get admin role
        admin_role = await db.execute(
            select(UserRole).where(UserRole.name == "admin")
        )
        admin_role = admin_role.scalar_one_or_none()
        if not admin_role:
            raise ValueError("Admin role not found")
        
        # Create company
        company = Company(
            name=registration.company.name,
            domain=registration.company.domain,
            description=registration.company.description,
            website=registration.company.website,
            industry=registration.company.industry,
            size=registration.company.size,
            settings={}
        )
        db.add(company)
        await db.flush()  # Get company ID
        
        # Create profile
        profile = Profile(
            email=registration.admin_user.email,
            first_name=registration.admin_user.first_name,
            last_name=registration.admin_user.last_name,
            phone=registration.admin_user.phone,
            company_id=company.id,
            role_id=admin_role.id,
            preferences={}
        )
        db.add(profile)
        await db.flush()  # Get profile ID
        
        # Create user
        user = User(
            email=registration.admin_user.email,
            password_hash=self.get_password_hash(registration.admin_user.password),
            is_verified=True,
            is_active=True,
            profile_id=profile.id
        )
        db.add(user)
        
        await db.commit()
        
        # Refresh objects to get relationships
        await db.refresh(company)
        await db.refresh(profile)
        await db.refresh(user)
        
        # Create tokens
        token_data = {
            "sub": str(user.id),
            "email": user.email,
            "company_id": str(company.id),
            "role_id": str(admin_role.id)
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        # Update last login
        profile.last_login = datetime.utcnow()
        await db.commit()
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": profile.id,
                "email": profile.email,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "avatar_url": profile.avatar_url,
                "phone": profile.phone,
                "is_active": profile.is_active,
                "last_login": profile.last_login,
                "preferences": profile.preferences,
                "company_id": company.id,
                "role_id": admin_role.id,
                "role_name": admin_role.name,
                "role_display_name": admin_role.display_name,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            },
            company={
                "id": company.id,
                "name": company.name,
                "domain": company.domain,
                "description": company.description,
                "website": company.website,
                "industry": company.industry,
                "size": company.size,
                "logo_url": company.logo_url,
                "is_active": company.is_active,
                "settings": company.settings,
                "created_at": company.created_at,
                "updated_at": company.updated_at
            }
        )
    
    async def authenticate_user(self, db: AsyncSession, email: str, password: str) -> Optional[Profile]:
        """Authenticate user with email and password"""
        try:
            # First, get the profile
            result = await db.execute(
                select(Profile)
                .options(
                    selectinload(Profile.company),
                    selectinload(Profile.role)
                )
                .where(Profile.email == email, Profile.is_active == True)
            )
            profile = result.scalar_one_or_none()
            
            if not profile:
                return None
            
            # Check if profile has password hash (new user system)
            if profile.password_hash and self.verify_password(password, profile.password_hash):
                return profile
            
            # Fall back to old User table for existing users
            user_result = await db.execute(
                select(User)
                .where(User.profile_id == profile.id, User.is_active == True)
            )
            user = user_result.scalar_one_or_none()
            
            if user and user.password_hash and self.verify_password(password, user.password_hash):
                return profile
            
            return None
        except Exception as e:
            import sys
            print(f"❌ Error in authenticate_user: {e}", file=sys.stderr)
            return None
    async def login_user(self, db: AsyncSession, login_data: UserLogin) -> AuthResponse:
        """Login user and return tokens"""
        profile = await self.authenticate_user(db, login_data.email, login_data.password)
        
        if not profile:
            raise ValueError("Invalid email or password")
        
        # Create tokens
        token_data = {
            "sub": str(profile.id),
            "email": profile.email,
            "company_id": str(profile.company.id),
            "role_id": str(profile.role.id)
        }
        
        access_token = self.create_access_token(token_data)
        refresh_token = self.create_refresh_token(token_data)
        
        # Update last login and first login tracking
        profile.last_login = datetime.utcnow()
        if not profile.first_login_at:
            profile.first_login_at = datetime.utcnow()
        
        await db.commit()
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": profile.id,
                "email": profile.email,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "avatar_url": profile.avatar_url,
                "phone": profile.phone,
                "is_active": profile.is_active,
                "last_login": profile.last_login,
                "preferences": profile.preferences,
                "company_id": profile.company.id,
                "role_id": profile.role.id,
                "role_name": profile.role.name,
                "role_display_name": profile.role.display_name,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            },
            company={
                "id": profile.company.id,
                "name": profile.company.name,
                "domain": profile.company.domain,
                "description": profile.company.description,
                "website": profile.company.website,
                "industry": profile.company.industry,
                "size": profile.company.size,
                "logo_url": profile.company.logo_url,
                "is_active": profile.company.is_active,
                "settings": profile.company.settings,
                "created_at": profile.company.created_at,
                "updated_at": profile.company.updated_at
            }
        )
    
    async def get_current_user(self, db: AsyncSession, token: str) -> Optional[Profile]:
        """Get current user from token"""
        token_data = self.verify_token(token)
        
        if not token_data or not token_data.user_id:
            return None
        
        # First try to find by Profile.id (new system)
        result = await db.execute(
            select(Profile)
            .options(
                selectinload(Profile.company),
                selectinload(Profile.role)
            )
            .where(Profile.id == token_data.user_id, Profile.is_active == True)
        )
        profile = result.scalar_one_or_none()
        
        if profile:
            return profile
        
        # Fall back to old system - find by User.id
        result = await db.execute(
            select(Profile)
            .options(
                selectinload(Profile.company),
                selectinload(Profile.role)
            )
            .join(User, User.profile_id == Profile.id)
            .where(User.id == token_data.user_id, User.is_active == True)
        )
        
        return result.scalar_one_or_none()
    
    async def refresh_access_token(self, db: AsyncSession, refresh_token: str) -> AuthResponse:
        """Refresh access token"""
        token_data = self.verify_token(refresh_token, "refresh")
        
        if not token_data or not token_data.user_id:
            raise ValueError("Invalid refresh token")
        
        # Get user and profile
        result = await db.execute(
            select(User)
            .options(selectinload(User.profile))
            .where(User.id == token_data.user_id, User.is_active == True)
        )
        user = result.scalar_one_or_none()
        
        if not user or not user.profile:
            raise ValueError("User not found")
        
        # Get full profile with relationships
        result = await db.execute(
            select(Profile)
            .options(
                selectinload(Profile.company),
                selectinload(Profile.role)
            )
            .where(Profile.id == user.profile_id)
        )
        profile = result.scalar_one()
        
        # Create new tokens
        new_token_data = {
            "sub": str(user.id),
            "email": user.email,
            "company_id": str(profile.company.id),
            "role_id": str(profile.role.id)
        }
        
        access_token = self.create_access_token(new_token_data)
        new_refresh_token = self.create_refresh_token(new_token_data)
        
        return AuthResponse(
            access_token=access_token,
            refresh_token=new_refresh_token,
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            user={
                "id": profile.id,
                "email": profile.email,
                "first_name": profile.first_name,
                "last_name": profile.last_name,
                "avatar_url": profile.avatar_url,
                "phone": profile.phone,
                "is_active": profile.is_active,
                "last_login": profile.last_login,
                "preferences": profile.preferences,
                "company_id": profile.company.id,
                "role_id": profile.role.id,
                "role_name": profile.role.name,
                "role_display_name": profile.role.display_name,
                "created_at": profile.created_at,
                "updated_at": profile.updated_at
            },
            company={
                "id": profile.company.id,
                "name": profile.company.name,
                "domain": profile.company.domain,
                "description": profile.company.description,
                "website": profile.company.website,
                "industry": profile.company.industry,
                "size": profile.company.size,
                "logo_url": profile.company.logo_url,
                "is_active": profile.company.is_active,
                "settings": profile.company.settings,
                "created_at": profile.company.created_at,
                "updated_at": profile.company.updated_at
            }
        )
    
    async def create_user_invitation(
        self, 
        db: AsyncSession, 
        company_id: str, 
        inviter_id: str, 
        invitation: UserInviteCreate
    ) -> UserInvitation:
        """Create user invitation"""
        
        # Check if email already exists
        existing_user = await db.execute(
            select(User).where(User.email == invitation.email)
        )
        if existing_user.scalar_one_or_none():
            raise ValueError("Email already registered")
        
        # Check if invitation already exists
        existing_invitation = await db.execute(
            select(UserInvitation).where(
                UserInvitation.email == invitation.email,
                UserInvitation.company_id == company_id,
                UserInvitation.is_accepted == False
            )
        )
        if existing_invitation.scalar_one_or_none():
            raise ValueError("Invitation already sent")
        
        # Create invitation
        invitation_token = secrets.token_urlsafe(32)
        expires_at = datetime.utcnow() + timedelta(days=7)  # 7 days to accept
        
        user_invitation = UserInvitation(
            email=invitation.email,
            company_id=company_id,
            role_id=invitation.role_id,
            invited_by=inviter_id,
            invitation_token=invitation_token,
            expires_at=expires_at
        )
        
        db.add(user_invitation)
        await db.commit()
        await db.refresh(user_invitation)
        
        return user_invitation
