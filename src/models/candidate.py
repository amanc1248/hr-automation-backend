"""
Candidate models for HR Automation System.
"""

from pydantic import Field, EmailStr, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID

from .base import BaseEntity, BaseCreate, BaseUpdate


class CandidateSource(str, Enum):
    """Source of candidate application"""
    DIRECT = "direct"
    LINKEDIN = "linkedin"
    EMAIL = "email"
    REFERRAL = "referral"
    INDEED = "indeed"
    GLASSDOOR = "glassdoor"
    OTHER = "other"


class CandidateStatus(str, Enum):
    """Overall candidate status in the system"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    BLACKLISTED = "blacklisted"


class Skill(BaseCreate):
    """Skill model"""
    name: str = Field(description="Skill name")
    level: str = Field(default="intermediate", description="Skill level (beginner, intermediate, advanced, expert)")
    years_experience: Optional[int] = Field(default=None, ge=0, description="Years of experience with this skill")
    verified: bool = Field(default=False, description="Whether the skill is verified")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "Python",
                "level": "advanced",
                "years_experience": 5,
                "verified": False
            }
        }
    }


class WorkExperience(BaseCreate):
    """Work experience model"""
    company: str = Field(description="Company name")
    position: str = Field(description="Job position/title")
    description: Optional[str] = Field(default=None, description="Job description")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY-MM)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY-MM) or 'present'")
    location: Optional[str] = Field(default=None, description="Work location")
    is_current: bool = Field(default=False, description="Whether this is the current job")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "company": "TechCorp Inc.",
                "position": "Senior Software Engineer",
                "description": "Developed web applications using Python and React",
                "start_date": "2022-01",
                "end_date": "present",
                "location": "San Francisco, CA",
                "is_current": True
            }
        }
    }


class Education(BaseCreate):
    """Education model"""
    institution: str = Field(description="Educational institution name")
    degree: str = Field(description="Degree type and field")
    field_of_study: Optional[str] = Field(default=None, description="Field of study")
    start_date: Optional[str] = Field(default=None, description="Start date (YYYY)")
    end_date: Optional[str] = Field(default=None, description="End date (YYYY)")
    gpa: Optional[float] = Field(default=None, ge=0.0, le=4.0, description="GPA score")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "institution": "Stanford University",
                "degree": "Bachelor of Science",
                "field_of_study": "Computer Science",
                "start_date": "2018",
                "end_date": "2022",
                "gpa": 3.8
            }
        }
    }


class Candidate(BaseEntity):
    """Candidate model"""
    # Personal information
    email: EmailStr = Field(description="Candidate email address")
    full_name: Optional[str] = Field(default=None, description="Candidate's full name")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Current location")
    
    # Professional information
    current_company: Optional[str] = Field(default=None, description="Current employer")
    current_position: Optional[str] = Field(default=None, description="Current job title")
    experience_years: Optional[int] = Field(default=None, ge=0, description="Total years of experience")
    
    # Skills and experience
    skills: List[Skill] = Field(default_factory=list, description="Candidate skills")
    work_experience: List[WorkExperience] = Field(default_factory=list, description="Work experience history")
    education: List[Education] = Field(default_factory=list, description="Educational background")
    
    # Documents and links
    resume_url: Optional[HttpUrl] = Field(default=None, description="Resume file URL")
    resume_text: Optional[str] = Field(default=None, description="Extracted resume text")
    portfolio_url: Optional[HttpUrl] = Field(default=None, description="Portfolio website URL")
    linkedin_profile: Optional[HttpUrl] = Field(default=None, description="LinkedIn profile URL")
    github_profile: Optional[HttpUrl] = Field(default=None, description="GitHub profile URL")
    
    # Application metadata
    source: CandidateSource = Field(default=CandidateSource.DIRECT, description="Source of application")
    status: CandidateStatus = Field(default=CandidateStatus.ACTIVE, description="Candidate status")
    referrer_id: Optional[UUID] = Field(default=None, description="ID of person who referred this candidate")
    
    # AI analysis
    ai_summary: Optional[str] = Field(default=None, description="AI-generated candidate summary")
    ai_skills_extracted: List[str] = Field(default_factory=list, description="AI-extracted skills from resume")
    ai_experience_summary: Optional[str] = Field(default=None, description="AI-generated experience summary")
    
    # Privacy and preferences
    consent_to_process: bool = Field(default=False, description="Consent to process personal data")
    marketing_consent: bool = Field(default=False, description="Consent to marketing communications")
    preferred_contact_method: str = Field(default="email", description="Preferred contact method")
    
    # Analytics
    profile_views: int = Field(default=0, ge=0, description="Number of profile views")
    last_activity: Optional[str] = Field(default=None, description="Last activity timestamp")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "880e8400-e29b-41d4-a716-446655440003",
                "email": "john.doe@email.com",
                "full_name": "John Doe",
                "phone": "+1-555-0123",
                "location": "New York, NY",
                "current_company": "StartupXYZ",
                "current_position": "Software Engineer",
                "experience_years": 5,
                "skills": [
                    {
                        "name": "Python",
                        "level": "advanced",
                        "years_experience": 5
                    },
                    {
                        "name": "React",
                        "level": "intermediate",
                        "years_experience": 3
                    }
                ],
                "resume_url": "https://storage.example.com/resumes/john-doe.pdf",
                "linkedin_profile": "https://linkedin.com/in/johndoe",
                "source": "linkedin",
                "status": "active",
                "consent_to_process": True
            }
        }
    }


class CandidateCreate(BaseCreate):
    """Model for creating a new candidate"""
    email: EmailStr = Field(description="Candidate email address")
    full_name: Optional[str] = Field(default=None, description="Candidate's full name")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Current location")
    
    current_company: Optional[str] = Field(default=None, description="Current employer")
    current_position: Optional[str] = Field(default=None, description="Current job title")
    experience_years: Optional[int] = Field(default=None, ge=0, description="Total years of experience")
    
    skills: List[Skill] = Field(default_factory=list, description="Candidate skills")
    work_experience: List[WorkExperience] = Field(default_factory=list, description="Work experience history")
    education: List[Education] = Field(default_factory=list, description="Educational background")
    
    resume_url: Optional[HttpUrl] = Field(default=None, description="Resume file URL")
    resume_text: Optional[str] = Field(default=None, description="Resume text content")
    portfolio_url: Optional[HttpUrl] = Field(default=None, description="Portfolio website URL")
    linkedin_profile: Optional[HttpUrl] = Field(default=None, description="LinkedIn profile URL")
    github_profile: Optional[HttpUrl] = Field(default=None, description="GitHub profile URL")
    
    source: CandidateSource = Field(default=CandidateSource.DIRECT, description="Source of application")
    referrer_id: Optional[UUID] = Field(default=None, description="ID of person who referred this candidate")
    
    consent_to_process: bool = Field(default=False, description="Consent to process personal data")
    marketing_consent: bool = Field(default=False, description="Consent to marketing communications")
    preferred_contact_method: str = Field(default="email", description="Preferred contact method")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "email": "john.doe@email.com",
                "full_name": "John Doe",
                "phone": "+1-555-0123",
                "current_company": "StartupXYZ",
                "current_position": "Software Engineer",
                "experience_years": 5,
                "linkedin_profile": "https://linkedin.com/in/johndoe",
                "source": "linkedin",
                "consent_to_process": True
            }
        }
    }


class CandidateUpdate(BaseUpdate):
    """Model for updating candidate information"""
    full_name: Optional[str] = Field(default=None, description="Candidate's full name")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Current location")
    
    current_company: Optional[str] = Field(default=None, description="Current employer")
    current_position: Optional[str] = Field(default=None, description="Current job title")
    experience_years: Optional[int] = Field(default=None, ge=0, description="Total years of experience")
    
    skills: Optional[List[Skill]] = Field(default=None, description="Candidate skills")
    work_experience: Optional[List[WorkExperience]] = Field(default=None, description="Work experience history")
    education: Optional[List[Education]] = Field(default=None, description="Educational background")
    
    resume_url: Optional[HttpUrl] = Field(default=None, description="Resume file URL")
    resume_text: Optional[str] = Field(default=None, description="Resume text content")
    portfolio_url: Optional[HttpUrl] = Field(default=None, description="Portfolio website URL")
    linkedin_profile: Optional[HttpUrl] = Field(default=None, description="LinkedIn profile URL")
    github_profile: Optional[HttpUrl] = Field(default=None, description="GitHub profile URL")
    
    status: Optional[CandidateStatus] = Field(default=None, description="Candidate status")
    preferred_contact_method: Optional[str] = Field(default=None, description="Preferred contact method")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "full_name": "John Doe Updated",
                "current_position": "Senior Software Engineer",
                "experience_years": 6
            }
        }
    }


class CandidateSearch(BaseCreate):
    """Model for candidate search parameters"""
    query: Optional[str] = Field(default=None, description="Search query")
    skills: Optional[List[str]] = Field(default=None, description="Required skills")
    location: Optional[str] = Field(default=None, description="Location filter")
    experience_min: Optional[int] = Field(default=None, ge=0, description="Minimum years of experience")
    experience_max: Optional[int] = Field(default=None, ge=0, description="Maximum years of experience")
    current_company: Optional[str] = Field(default=None, description="Current company filter")
    source: Optional[CandidateSource] = Field(default=None, description="Application source filter")
    status: Optional[CandidateStatus] = Field(default=None, description="Candidate status filter")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "query": "python developer",
                "skills": ["Python", "React"],
                "location": "San Francisco",
                "experience_min": 3,
                "experience_max": 8,
                "source": "linkedin"
            }
        }
    }
