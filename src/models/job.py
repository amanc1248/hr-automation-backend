"""
Job models for HR Automation System.
"""

from pydantic import Field, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
from decimal import Decimal

from .base import BaseEntity, BaseCreate, BaseUpdate


class JobType(str, Enum):
    """Job type enumeration"""
    FULL_TIME = "full_time"
    PART_TIME = "part_time"
    CONTRACT = "contract"
    INTERNSHIP = "internship"
    FREELANCE = "freelance"


class JobStatus(str, Enum):
    """Job status enumeration"""
    DRAFT = "draft"
    PUBLISHED = "published"
    PAUSED = "paused"
    CLOSED = "closed"
    ARCHIVED = "archived"


class ExperienceLevel(str, Enum):
    """Experience level enumeration"""
    ENTRY = "entry"
    JUNIOR = "junior"
    MID = "mid"
    SENIOR = "senior"
    LEAD = "lead"
    PRINCIPAL = "principal"


class SalaryRange(BaseCreate):
    """Salary range model"""
    min_salary: Optional[Decimal] = Field(default=None, ge=0, description="Minimum salary")
    max_salary: Optional[Decimal] = Field(default=None, ge=0, description="Maximum salary")
    currency: str = Field(default="USD", max_length=3, description="Currency code (ISO 4217)")
    period: str = Field(default="yearly", description="Salary period (yearly, monthly, hourly)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "min_salary": 80000,
                "max_salary": 120000,
                "currency": "USD",
                "period": "yearly"
            }
        }
    }


class JobRequirement(BaseCreate):
    """Job requirement model"""
    category: str = Field(description="Requirement category (skills, education, experience)")
    name: str = Field(description="Requirement name")
    level: str = Field(default="required", description="Requirement level (required, preferred, nice_to_have)")
    years_experience: Optional[int] = Field(default=None, ge=0, description="Years of experience required")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "category": "skills",
                "name": "Python",
                "level": "required",
                "years_experience": 3
            }
        }
    }


class Job(BaseEntity):
    """Job model"""
    title: str = Field(min_length=1, max_length=200, description="Job title")
    description: Optional[str] = Field(default=None, description="Job description")
    summary: Optional[str] = Field(default=None, max_length=500, description="Brief job summary")
    requirements: List[JobRequirement] = Field(default_factory=list, description="Job requirements")
    responsibilities: List[str] = Field(default_factory=list, description="Job responsibilities")
    benefits: List[str] = Field(default_factory=list, description="Job benefits")
    
    # Location and work arrangement
    location: Optional[str] = Field(default=None, max_length=200, description="Job location")
    remote_allowed: bool = Field(default=False, description="Whether remote work is allowed")
    hybrid_allowed: bool = Field(default=False, description="Whether hybrid work is allowed")
    
    # Job details
    job_type: JobType = Field(default=JobType.FULL_TIME, description="Type of employment")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.MID, description="Required experience level")
    salary_range: Optional[SalaryRange] = Field(default=None, description="Salary range")
    
    # Status and metadata
    status: JobStatus = Field(default=JobStatus.DRAFT, description="Job posting status")
    company_id: UUID = Field(description="Company that posted the job")
    created_by: UUID = Field(description="User who created the job")
    
    # Posting and application settings
    posted_platforms: List[str] = Field(default_factory=list, description="Platforms where job is posted")
    application_deadline: Optional[str] = Field(default=None, description="Application deadline")
    external_job_id: Optional[str] = Field(default=None, description="External job ID from job boards")
    
    # AI and automation settings
    auto_screening_enabled: bool = Field(default=True, description="Enable automatic screening")
    ai_interview_enabled: bool = Field(default=False, description="Enable AI interviews")
    screening_questions: List[str] = Field(default_factory=list, description="Custom screening questions")
    
    # Analytics
    views_count: int = Field(default=0, ge=0, description="Number of job views")
    applications_count: int = Field(default=0, ge=0, description="Number of applications received")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "770e8400-e29b-41d4-a716-446655440002",
                "title": "Senior Full Stack Engineer",
                "description": "We are looking for a senior full stack engineer...",
                "summary": "Senior role for experienced full stack developer",
                "requirements": [
                    {
                        "category": "skills",
                        "name": "Python",
                        "level": "required",
                        "years_experience": 5
                    },
                    {
                        "category": "skills", 
                        "name": "React",
                        "level": "required",
                        "years_experience": 3
                    }
                ],
                "responsibilities": [
                    "Develop and maintain web applications",
                    "Collaborate with cross-functional teams",
                    "Mentor junior developers"
                ],
                "location": "San Francisco, CA",
                "remote_allowed": True,
                "job_type": "full_time",
                "experience_level": "senior",
                "salary_range": {
                    "min_salary": 120000,
                    "max_salary": 180000,
                    "currency": "USD",
                    "period": "yearly"
                },
                "status": "published",
                "company_id": "660e8400-e29b-41d4-a716-446655440001",
                "auto_screening_enabled": True,
                "ai_interview_enabled": True
            }
        }
    }


class JobCreate(BaseCreate):
    """Model for creating a new job"""
    title: str = Field(min_length=1, max_length=200, description="Job title")
    description: Optional[str] = Field(default=None, description="Job description")
    summary: Optional[str] = Field(default=None, max_length=500, description="Brief job summary")
    requirements: List[JobRequirement] = Field(default_factory=list, description="Job requirements")
    responsibilities: List[str] = Field(default_factory=list, description="Job responsibilities")
    benefits: List[str] = Field(default_factory=list, description="Job benefits")
    
    location: Optional[str] = Field(default=None, max_length=200, description="Job location")
    remote_allowed: bool = Field(default=False, description="Whether remote work is allowed")
    hybrid_allowed: bool = Field(default=False, description="Whether hybrid work is allowed")
    
    job_type: JobType = Field(default=JobType.FULL_TIME, description="Type of employment")
    experience_level: ExperienceLevel = Field(default=ExperienceLevel.MID, description="Required experience level")
    salary_range: Optional[SalaryRange] = Field(default=None, description="Salary range")
    
    company_id: UUID = Field(description="Company that posted the job")
    
    posted_platforms: List[str] = Field(default_factory=list, description="Platforms where job should be posted")
    application_deadline: Optional[str] = Field(default=None, description="Application deadline")
    
    auto_screening_enabled: bool = Field(default=True, description="Enable automatic screening")
    ai_interview_enabled: bool = Field(default=False, description="Enable AI interviews")
    screening_questions: List[str] = Field(default_factory=list, description="Custom screening questions")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Senior Full Stack Engineer",
                "description": "We are looking for a senior full stack engineer to join our team...",
                "summary": "Senior role for experienced full stack developer",
                "requirements": [
                    {
                        "category": "skills",
                        "name": "Python",
                        "level": "required",
                        "years_experience": 5
                    }
                ],
                "responsibilities": [
                    "Develop and maintain web applications",
                    "Collaborate with cross-functional teams"
                ],
                "location": "San Francisco, CA",
                "remote_allowed": True,
                "job_type": "full_time",
                "experience_level": "senior",
                "company_id": "660e8400-e29b-41d4-a716-446655440001",
                "posted_platforms": ["linkedin", "indeed"],
                "auto_screening_enabled": True,
                "ai_interview_enabled": True
            }
        }
    }


class JobUpdate(BaseUpdate):
    """Model for updating job information"""
    title: Optional[str] = Field(default=None, min_length=1, max_length=200, description="Job title")
    description: Optional[str] = Field(default=None, description="Job description")
    summary: Optional[str] = Field(default=None, max_length=500, description="Brief job summary")
    requirements: Optional[List[JobRequirement]] = Field(default=None, description="Job requirements")
    responsibilities: Optional[List[str]] = Field(default=None, description="Job responsibilities")
    benefits: Optional[List[str]] = Field(default=None, description="Job benefits")
    
    location: Optional[str] = Field(default=None, max_length=200, description="Job location")
    remote_allowed: Optional[bool] = Field(default=None, description="Whether remote work is allowed")
    hybrid_allowed: Optional[bool] = Field(default=None, description="Whether hybrid work is allowed")
    
    job_type: Optional[JobType] = Field(default=None, description="Type of employment")
    experience_level: Optional[ExperienceLevel] = Field(default=None, description="Required experience level")
    salary_range: Optional[SalaryRange] = Field(default=None, description="Salary range")
    
    status: Optional[JobStatus] = Field(default=None, description="Job posting status")
    posted_platforms: Optional[List[str]] = Field(default=None, description="Platforms where job is posted")
    application_deadline: Optional[str] = Field(default=None, description="Application deadline")
    
    auto_screening_enabled: Optional[bool] = Field(default=None, description="Enable automatic screening")
    ai_interview_enabled: Optional[bool] = Field(default=None, description="Enable AI interviews")
    screening_questions: Optional[List[str]] = Field(default=None, description="Custom screening questions")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "title": "Senior Full Stack Engineer - Updated",
                "status": "published",
                "remote_allowed": True,
                "ai_interview_enabled": True
            }
        }
    }


class JobSearch(BaseCreate):
    """Model for job search parameters"""
    query: Optional[str] = Field(default=None, description="Search query")
    location: Optional[str] = Field(default=None, description="Location filter")
    job_type: Optional[JobType] = Field(default=None, description="Job type filter")
    experience_level: Optional[ExperienceLevel] = Field(default=None, description="Experience level filter")
    remote_allowed: Optional[bool] = Field(default=None, description="Remote work filter")
    salary_min: Optional[Decimal] = Field(default=None, ge=0, description="Minimum salary filter")
    salary_max: Optional[Decimal] = Field(default=None, ge=0, description="Maximum salary filter")
    company_id: Optional[UUID] = Field(default=None, description="Company filter")
    status: Optional[JobStatus] = Field(default=None, description="Status filter")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "python developer",
                "location": "San Francisco",
                "job_type": "full_time",
                "experience_level": "senior",
                "remote_allowed": True,
                "salary_min": 100000
            }
        }
    }
