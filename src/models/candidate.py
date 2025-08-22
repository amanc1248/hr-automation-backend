from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, BaseModelWithSoftDelete

class Candidate(BaseModelWithSoftDelete):
    """Candidate model"""
    __tablename__ = "candidates"
    
    # Personal information
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    phone = Column(String(20), nullable=True)
    
    # Location
    location = Column(String(255), nullable=True)
    timezone = Column(String(50), nullable=True)
    
    # Professional information
    current_title = Column(String(255), nullable=True)
    current_company = Column(String(255), nullable=True)
    experience_years = Column(Integer, nullable=True)
    
    # Resume and portfolio
    resume_url = Column(String(500), nullable=True)
    resume_text = Column(Text, nullable=True)  # Extracted text for searching
    portfolio_url = Column(String(500), nullable=True)
    linkedin_url = Column(String(500), nullable=True)
    github_url = Column(String(500), nullable=True)
    
    # Skills and preferences
    skills = Column(JSONB, default=list, nullable=False)
    preferences = Column(JSONB, default=dict, nullable=False)  # salary, location, remote, etc.
    
    # AI analysis
    ai_summary = Column(Text, nullable=True)
    ai_skills_extracted = Column(JSONB, default=list, nullable=False)
    ai_experience_analysis = Column(JSONB, default=dict, nullable=False)
    
    # Source tracking
    source = Column(String(100), nullable=True)  # linkedin, referral, website, etc.
    source_details = Column(JSONB, default=dict, nullable=False)
    
    # Status
    status = Column(String(50), default="new", nullable=False)  # new, reviewing, qualified, rejected
    
    # Relationships
    applications = relationship("Application", back_populates="candidate", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="candidate", cascade="all, delete-orphan")

class Application(BaseModel):
    """Job application model"""
    __tablename__ = "applications"
    
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    
    # Application details
    status = Column(String(50), default="applied", nullable=False)
    # Statuses: applied, screening, interviewing, offer, hired, rejected, withdrawn
    
    # Application data
    cover_letter = Column(Text, nullable=True)
    resume_version = Column(String(500), nullable=True)  # URL to specific resume version
    application_data = Column(JSONB, default=dict, nullable=False)  # Custom form fields
    
    # Workflow tracking
    workflow_execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=True)
    current_stage = Column(String(100), nullable=True)
    
    # Scoring and evaluation
    ai_score = Column(Numeric(5, 2), nullable=True)  # 0.00 to 100.00
    ai_analysis = Column(JSONB, default=dict, nullable=False)
    manual_score = Column(Numeric(5, 2), nullable=True)
    manual_notes = Column(Text, nullable=True)
    
    # Timeline
    applied_at = Column(DateTime, nullable=False)
    reviewed_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    
    # Source and referral
    source = Column(String(100), nullable=True)
    referrer_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="applications")
    candidate = relationship("Candidate", back_populates="applications")
    # One-to-one relationship: one application can have one workflow execution
    workflow_execution = relationship("WorkflowExecution", foreign_keys=[workflow_execution_id], uselist=False)
    referrer = relationship("Profile")
    interviews = relationship("Interview", back_populates="application", cascade="all, delete-orphan")
