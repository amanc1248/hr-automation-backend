from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, BaseModelWithSoftDelete
from datetime import datetime

class Company(BaseModel):
    """Company model"""
    __tablename__ = "companies"
    
    name = Column(String(255), nullable=False)
    domain = Column(String(255), unique=True, nullable=True)
    description = Column(Text, nullable=True)
    website = Column(String(500), nullable=True)
    industry = Column(String(100), nullable=True)
    size = Column(String(50), nullable=True)  # startup, small, medium, large, enterprise
    logo_url = Column(String(500), nullable=True)
    settings = Column(JSONB, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    profiles = relationship("Profile", back_populates="company", cascade="all, delete-orphan")
    jobs = relationship("Job", back_populates="company", cascade="all, delete-orphan")
    email_accounts = relationship("EmailAccount", back_populates="company", cascade="all, delete-orphan")

class UserRole(BaseModel):
    """User roles model"""
    __tablename__ = "user_roles"
    
    name = Column(String(50), unique=True, nullable=False)
    display_name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    permissions = Column(JSONB, default=list, nullable=False)
    approval_types = Column(JSONB, default=list, nullable=False)
    is_system_role = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    profiles = relationship("Profile", back_populates="role")

class Profile(BaseModel):
    """User profile model (extends Supabase auth.users)"""
    __tablename__ = "profiles"
    
    # This ID should match Supabase auth.users.id
    # id is inherited from BaseModel (UUID)
    
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)  # For direct auth (not Supabase)
    first_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    phone = Column(String(20), nullable=True)
    
    # Company and role
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("user_roles.id"), nullable=False)
    
    # Profile settings
    preferences = Column(JSONB, default=dict, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_login = Column(DateTime, nullable=True)
    
    # User management fields
    first_login_at = Column(DateTime, nullable=True)
    must_change_password = Column(Boolean, default=False, nullable=False)
    password_changed_at = Column(DateTime, nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="profiles")
    role = relationship("UserRole", back_populates="profiles")
    created_jobs = relationship("Job", foreign_keys="Job.created_by", back_populates="creator")
    assigned_jobs = relationship("Job", foreign_keys="Job.assigned_to", back_populates="assignee")

class User(BaseModel):
    """User model for authentication (if not using Supabase auth)"""
    __tablename__ = "users"
    
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    verification_token = Column(String(255), nullable=True)
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)
    
    # Link to profile
    profile_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    profile = relationship("Profile")

class UserInvitation(BaseModel):
    """User invitation model"""
    __tablename__ = "user_invitations"
    
    email = Column(String(255), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    role_id = Column(UUID(as_uuid=True), ForeignKey("user_roles.id"), nullable=False)
    invited_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    
    invitation_token = Column(String(255), unique=True, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    is_accepted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    company = relationship("Company")
    role = relationship("UserRole")
    inviter = relationship("Profile")
