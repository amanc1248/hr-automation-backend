"""
Pydantic models for HR Automation System.
Provides data validation, serialization, and API schemas.
"""

from .user import UserProfile, UserCreate, UserUpdate, UserRole
from .company import Company, CompanyCreate, CompanyUpdate
from .job import Job, JobCreate, JobUpdate, JobStatus, JobType, ExperienceLevel
from .candidate import Candidate, CandidateCreate, CandidateUpdate, CandidateSource
from .application import Application, ApplicationCreate, ApplicationUpdate, ApplicationStatus
from .interview import Interview, InterviewCreate, InterviewUpdate, InterviewType, InterviewStatus
from .assessment import Assessment, AssessmentCreate, AssessmentUpdate, AssessmentType, AssessmentStatus
from .workflow import Workflow, WorkflowCreate, WorkflowUpdate, WorkflowStatus, WorkflowType
from .analytics import AnalyticsEvent, AnalyticsEventCreate, EventType

__all__ = [
    # User models
    "UserProfile", "UserCreate", "UserUpdate", "UserRole",
    
    # Company models
    "Company", "CompanyCreate", "CompanyUpdate",
    
    # Job models
    "Job", "JobCreate", "JobUpdate", "JobStatus", "JobType", "ExperienceLevel",
    
    # Candidate models
    "Candidate", "CandidateCreate", "CandidateUpdate", "CandidateSource",
    
    # Application models
    "Application", "ApplicationCreate", "ApplicationUpdate", "ApplicationStatus",
    
    # Interview models
    "Interview", "InterviewCreate", "InterviewUpdate", "InterviewType", "InterviewStatus",
    
    # Assessment models
    "Assessment", "AssessmentCreate", "AssessmentUpdate", "AssessmentType", "AssessmentStatus",
    
    # Workflow models
    "Workflow", "WorkflowCreate", "WorkflowUpdate", "WorkflowStatus", "WorkflowType",
    
    # Analytics models
    "AnalyticsEvent", "AnalyticsEventCreate", "EventType",
]
