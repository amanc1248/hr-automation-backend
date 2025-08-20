"""
Pydantic models for HR Automation System.
Provides data validation, serialization, and API schemas.
"""

from .base import BaseEntity, BaseCreate, BaseUpdate, PaginationParams, PaginatedResponse, APIResponse
from .user import UserProfile, UserCreate, UserUpdate, UserRole
from .company import Company, CompanyCreate, CompanyUpdate
from .job import Job, JobCreate, JobUpdate, JobStatus, JobType, ExperienceLevel, JobSearch, SalaryRange, JobRequirement
from .candidate import Candidate, CandidateCreate, CandidateUpdate, CandidateSource, CandidateStatus, Skill, WorkExperience, Education, CandidateSearch
from .application import Application, ApplicationCreate, ApplicationUpdate, ApplicationStatus, ApplicationPriority, AIScreeningResult, ApplicationSearch, ApplicationStats
from .interview import Interview, InterviewCreate, InterviewUpdate, InterviewType, InterviewStatus, InterviewMode, AIInterviewConfig, InterviewFeedback, InterviewSearch
from .assessment import Assessment, AssessmentCreate, AssessmentUpdate, AssessmentType, AssessmentStatus, AssessmentQuestion, CandidateResponse, AIEvaluation, AssessmentSearch
from .workflow import Workflow, WorkflowCreate, WorkflowUpdate, WorkflowStatus, WorkflowType, WorkflowStep, Clarification, ClarificationResponse, WorkflowSearch
from .analytics import AnalyticsEvent, AnalyticsEventCreate, EventType, HiringMetrics, JobMetrics, DashboardMetrics

__all__ = [
    # Base models
    "BaseEntity", "BaseCreate", "BaseUpdate", "PaginationParams", "PaginatedResponse", "APIResponse",
    
    # User models
    "UserProfile", "UserCreate", "UserUpdate", "UserRole",
    
    # Company models
    "Company", "CompanyCreate", "CompanyUpdate",
    
    # Job models
    "Job", "JobCreate", "JobUpdate", "JobStatus", "JobType", "ExperienceLevel", 
    "JobSearch", "SalaryRange", "JobRequirement",
    
    # Candidate models
    "Candidate", "CandidateCreate", "CandidateUpdate", "CandidateSource", "CandidateStatus",
    "Skill", "WorkExperience", "Education", "CandidateSearch",
    
    # Application models
    "Application", "ApplicationCreate", "ApplicationUpdate", "ApplicationStatus", 
    "ApplicationPriority", "AIScreeningResult", "ApplicationSearch", "ApplicationStats",
    
    # Interview models
    "Interview", "InterviewCreate", "InterviewUpdate", "InterviewType", "InterviewStatus",
    "InterviewMode", "AIInterviewConfig", "InterviewFeedback", "InterviewSearch",
    
    # Assessment models
    "Assessment", "AssessmentCreate", "AssessmentUpdate", "AssessmentType", "AssessmentStatus",
    "AssessmentQuestion", "CandidateResponse", "AIEvaluation", "AssessmentSearch",
    
    # Workflow models
    "Workflow", "WorkflowCreate", "WorkflowUpdate", "WorkflowStatus", "WorkflowType",
    "WorkflowStep", "Clarification", "ClarificationResponse", "WorkflowSearch",
    
    # Analytics models
    "AnalyticsEvent", "AnalyticsEventCreate", "EventType", "HiringMetrics", "JobMetrics", "DashboardMetrics",
]
