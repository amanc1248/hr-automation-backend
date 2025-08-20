"""
Analytics models for HR Automation System.
"""

from pydantic import Field
from typing import Optional, Dict, Any
from enum import Enum
from uuid import UUID
from decimal import Decimal

from .base import BaseEntity, BaseCreate, BaseUpdate


class EventType(str, Enum):
    """Analytics event type enumeration"""
    # Job events
    JOB_CREATED = "job_created"
    JOB_PUBLISHED = "job_published"
    JOB_VIEWED = "job_viewed"
    JOB_APPLIED = "job_applied"
    
    # Application events
    APPLICATION_SUBMITTED = "application_submitted"
    APPLICATION_SCREENED = "application_screened"
    APPLICATION_REVIEWED = "application_reviewed"
    APPLICATION_STATUS_CHANGED = "application_status_changed"
    
    # Interview events
    INTERVIEW_SCHEDULED = "interview_scheduled"
    INTERVIEW_COMPLETED = "interview_completed"
    AI_INTERVIEW_CONDUCTED = "ai_interview_conducted"
    
    # Assessment events
    ASSESSMENT_CREATED = "assessment_created"
    ASSESSMENT_STARTED = "assessment_started"
    ASSESSMENT_COMPLETED = "assessment_completed"
    
    # Workflow events
    WORKFLOW_STARTED = "workflow_started"
    WORKFLOW_COMPLETED = "workflow_completed"
    CLARIFICATION_REQUESTED = "clarification_requested"
    CLARIFICATION_RESOLVED = "clarification_resolved"
    
    # User events
    USER_LOGIN = "user_login"
    USER_LOGOUT = "user_logout"
    USER_ACTION = "user_action"
    
    # System events
    SYSTEM_ERROR = "system_error"
    API_CALL = "api_call"
    INTEGRATION_EVENT = "integration_event"


class AnalyticsEvent(BaseEntity):
    """Analytics event model"""
    event_type: EventType = Field(description="Type of event")
    entity_type: Optional[str] = Field(default=None, description="Type of entity involved")
    entity_id: Optional[UUID] = Field(default=None, description="ID of entity involved")
    
    user_id: Optional[UUID] = Field(default=None, description="User who triggered the event")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    # Event data
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Event properties")
    
    # Context
    ip_address: Optional[str] = Field(default=None, description="IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    referrer: Optional[str] = Field(default=None, description="Referrer URL")
    
    # Timing
    duration_ms: Optional[int] = Field(default=None, ge=0, description="Event duration in milliseconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "dd0e8400-e29b-41d4-a716-446655440008",
                "event_type": "application_screened",
                "entity_type": "application",
                "entity_id": "990e8400-e29b-41d4-a716-446655440004",
                "user_id": "550e8400-e29b-41d4-a716-446655440000",
                "metadata": {
                    "ai_score": 0.85,
                    "recommendation": "proceed",
                    "job_title": "Senior Engineer"
                },
                "properties": {
                    "screening_method": "ai_automated",
                    "confidence": 0.92
                },
                "duration_ms": 2500,
                "created_at": "2025-01-25T10:00:00Z"
            }
        }
    }


class AnalyticsEventCreate(BaseCreate):
    """Model for creating analytics events"""
    event_type: EventType = Field(description="Type of event")
    entity_type: Optional[str] = Field(default=None, description="Type of entity involved")
    entity_id: Optional[UUID] = Field(default=None, description="ID of entity involved")
    
    user_id: Optional[UUID] = Field(default=None, description="User who triggered the event")
    session_id: Optional[str] = Field(default=None, description="Session identifier")
    
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Event metadata")
    properties: Dict[str, Any] = Field(default_factory=dict, description="Event properties")
    
    ip_address: Optional[str] = Field(default=None, description="IP address")
    user_agent: Optional[str] = Field(default=None, description="User agent string")
    referrer: Optional[str] = Field(default=None, description="Referrer URL")
    
    duration_ms: Optional[int] = Field(default=None, ge=0, description="Event duration in milliseconds")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "event_type": "job_viewed",
                "entity_type": "job",
                "entity_id": "770e8400-e29b-41d4-a716-446655440002",
                "user_id": "880e8400-e29b-41d4-a716-446655440003",
                "metadata": {
                    "job_title": "Senior Engineer",
                    "source": "linkedin"
                },
                "ip_address": "192.168.1.1"
            }
        }
    }


class AnalyticsQuery(BaseCreate):
    """Model for analytics queries"""
    event_types: Optional[list[EventType]] = Field(default=None, description="Filter by event types")
    entity_type: Optional[str] = Field(default=None, description="Filter by entity type")
    entity_id: Optional[UUID] = Field(default=None, description="Filter by entity ID")
    user_id: Optional[UUID] = Field(default=None, description="Filter by user ID")
    
    date_from: Optional[str] = Field(default=None, description="Start date for query")
    date_to: Optional[str] = Field(default=None, description="End date for query")
    
    group_by: Optional[str] = Field(default=None, description="Group results by field")
    aggregate: Optional[str] = Field(default="count", description="Aggregation function (count, sum, avg)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "event_types": ["job_viewed", "job_applied"],
                "date_from": "2025-01-01",
                "date_to": "2025-01-31",
                "group_by": "event_type",
                "aggregate": "count"
            }
        }
    }


class HiringMetrics(BaseCreate):
    """Hiring process metrics model"""
    # Time metrics
    average_time_to_hire_days: Decimal = Field(ge=0, description="Average time from job posting to hire")
    average_time_to_screen_hours: Decimal = Field(ge=0, description="Average time to complete screening")
    average_time_to_interview_days: Decimal = Field(ge=0, description="Average time from application to interview")
    
    # Conversion metrics
    application_to_screening_rate: Decimal = Field(ge=0, le=1, description="Applications that pass screening")
    screening_to_interview_rate: Decimal = Field(ge=0, le=1, description="Screenings that lead to interviews")
    interview_to_offer_rate: Decimal = Field(ge=0, le=1, description="Interviews that lead to offers")
    offer_to_hire_rate: Decimal = Field(ge=0, le=1, description="Offers that are accepted")
    
    # Volume metrics
    total_jobs_posted: int = Field(ge=0, description="Total jobs posted")
    total_applications: int = Field(ge=0, description="Total applications received")
    total_interviews: int = Field(ge=0, description="Total interviews conducted")
    total_hires: int = Field(ge=0, description="Total successful hires")
    
    # Quality metrics
    average_candidate_score: Decimal = Field(ge=0, le=10, description="Average candidate screening score")
    ai_screening_accuracy: Decimal = Field(ge=0, le=1, description="AI screening accuracy vs human review")
    
    # Cost metrics (if available)
    cost_per_hire: Optional[Decimal] = Field(default=None, ge=0, description="Average cost per hire")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "average_time_to_hire_days": 21.5,
                "average_time_to_screen_hours": 2.3,
                "average_time_to_interview_days": 7.2,
                "application_to_screening_rate": 0.75,
                "screening_to_interview_rate": 0.45,
                "interview_to_offer_rate": 0.30,
                "offer_to_hire_rate": 0.85,
                "total_jobs_posted": 25,
                "total_applications": 450,
                "total_interviews": 135,
                "total_hires": 18,
                "average_candidate_score": 7.2,
                "ai_screening_accuracy": 0.88
            }
        }
    }


class JobMetrics(BaseCreate):
    """Job-specific metrics model"""
    job_id: UUID = Field(description="Job ID")
    job_title: str = Field(description="Job title")
    
    # Application metrics
    total_views: int = Field(ge=0, description="Total job views")
    total_applications: int = Field(ge=0, description="Total applications")
    applications_per_view: Decimal = Field(ge=0, description="Application conversion rate")
    
    # Source metrics
    applications_by_source: Dict[str, int] = Field(description="Applications by source")
    top_performing_source: Optional[str] = Field(default=None, description="Best performing source")
    
    # Quality metrics
    average_candidate_score: Decimal = Field(ge=0, le=10, description="Average candidate score")
    qualified_candidates_count: int = Field(ge=0, description="Number of qualified candidates")
    qualification_rate: Decimal = Field(ge=0, le=1, description="Percentage of qualified candidates")
    
    # Timeline metrics
    days_since_posted: int = Field(ge=0, description="Days since job was posted")
    average_response_time_hours: Decimal = Field(ge=0, description="Average time to respond to applications")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "770e8400-e29b-41d4-a716-446655440002",
                "job_title": "Senior Full Stack Engineer",
                "total_views": 1250,
                "total_applications": 89,
                "applications_per_view": 0.071,
                "applications_by_source": {
                    "linkedin": 45,
                    "direct": 25,
                    "referral": 19
                },
                "top_performing_source": "linkedin",
                "average_candidate_score": 7.8,
                "qualified_candidates_count": 23,
                "qualification_rate": 0.26,
                "days_since_posted": 14,
                "average_response_time_hours": 18.5
            }
        }
    }


class DashboardMetrics(BaseCreate):
    """Dashboard overview metrics model"""
    # Current period metrics
    active_jobs: int = Field(ge=0, description="Number of active job postings")
    pending_applications: int = Field(ge=0, description="Applications awaiting review")
    scheduled_interviews: int = Field(ge=0, description="Upcoming interviews")
    pending_offers: int = Field(ge=0, description="Outstanding offers")
    
    # Recent activity (last 30 days)
    recent_applications: int = Field(ge=0, description="Applications in last 30 days")
    recent_hires: int = Field(ge=0, description="Hires in last 30 days")
    recent_interviews: int = Field(ge=0, description="Interviews in last 30 days")
    
    # AI automation metrics
    ai_screenings_completed: int = Field(ge=0, description="AI screenings completed")
    ai_interviews_conducted: int = Field(ge=0, description="AI interviews conducted")
    automation_time_saved_hours: Decimal = Field(ge=0, description="Time saved through automation")
    
    # Workflow metrics
    active_workflows: int = Field(ge=0, description="Currently running workflows")
    pending_clarifications: int = Field(ge=0, description="Workflows awaiting human input")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "active_jobs": 12,
                "pending_applications": 45,
                "scheduled_interviews": 8,
                "pending_offers": 3,
                "recent_applications": 156,
                "recent_hires": 7,
                "recent_interviews": 28,
                "ai_screenings_completed": 134,
                "ai_interviews_conducted": 15,
                "automation_time_saved_hours": 67.5,
                "active_workflows": 5,
                "pending_clarifications": 2
            }
        }
    }
