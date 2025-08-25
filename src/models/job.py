from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, BaseModelWithSoftDelete

class Job(BaseModel):
    """Job posting model"""
    __tablename__ = "jobs"
    
    title = Column(String(255), nullable=False)
    short_id = Column(String(8), unique=True, nullable=False)  # Short unique identifier for emails
    description = Column(Text, nullable=False)
    requirements = Column(Text, nullable=True)
    requirements_structured = Column(JSONB, default=dict, nullable=False)
    
    # Job details
    department = Column(String(100), nullable=True)
    location = Column(String(255), nullable=True)
    job_type = Column(String(50), nullable=False)  # full-time, part-time, contract, internship
    experience_level = Column(String(50), nullable=True)  # entry, mid, senior, executive
    remote_policy = Column(String(50), nullable=True)  # remote, hybrid, onsite
    
    # Compensation
    salary_min = Column(Numeric(12, 2), nullable=True)
    salary_max = Column(Numeric(12, 2), nullable=True)
    salary_currency = Column(String(3), default="USD", nullable=False)
    
    # Status and workflow
    status = Column(String(50), default="draft", nullable=False)  # draft, active, paused, closed
    workflow_template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_template.id"), nullable=True)
    
    # Company and ownership
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    created_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    
    # Posting details
    posted_at = Column(DateTime, nullable=True)
    expires_at = Column(DateTime, nullable=True)
    is_featured = Column(Boolean, default=False, nullable=False)
    
    # External posting tracking
    external_postings = Column(JSONB, default=list, nullable=False)  # LinkedIn, Indeed, etc.
    
    # Relationships
    company = relationship("Company", back_populates="jobs")
    creator = relationship("Profile", foreign_keys=[created_by], back_populates="created_jobs")
    assignee = relationship("Profile", foreign_keys=[assigned_to], back_populates="assigned_jobs")
    workflow_template = relationship("WorkflowTemplate")
    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    interviews = relationship("Interview", back_populates="job", cascade="all, delete-orphan")
    requirements_list = relationship("JobRequirement", back_populates="job", cascade="all, delete-orphan")
    candidate_workflows = relationship("CandidateWorkflow", back_populates="job", cascade="all, delete-orphan")

class JobRequirement(BaseModel):
    """Job requirements model"""
    __tablename__ = "job_requirements"
    
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    requirement_type = Column(String(50), nullable=False)  # skill, experience, education, certification
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, default=True, nullable=False)
    priority = Column(Integer, default=1, nullable=False)  # 1=high, 2=medium, 3=low
    
    # Skill-specific fields
    proficiency_level = Column(String(50), nullable=True)  # beginner, intermediate, advanced, expert
    years_experience = Column(Integer, nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="requirements_list")
