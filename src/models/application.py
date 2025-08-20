"""
Application models for HR Automation System.
"""

from pydantic import Field
from typing import Optional, Dict, Any
from enum import Enum
from uuid import UUID
from decimal import Decimal

from .base import BaseEntity, BaseCreate, BaseUpdate


class ApplicationStatus(str, Enum):
    """Application status enumeration"""
    APPLIED = "applied"
    SCREENING = "screening"
    INTERVIEW = "interview"
    TECHNICAL_TEST = "technical_test"
    FINAL_INTERVIEW = "final_interview"
    OFFER = "offer"
    HIRED = "hired"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class ApplicationPriority(str, Enum):
    """Application priority enumeration"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class AIScreeningResult(BaseCreate):
    """AI screening result model"""
    score: Decimal = Field(ge=0.0, le=1.0, description="AI screening score (0-1)")
    confidence: Decimal = Field(ge=0.0, le=1.0, description="Confidence level of the score")
    summary: str = Field(description="AI-generated summary of the screening")
    strengths: list[str] = Field(default_factory=list, description="Identified strengths")
    weaknesses: list[str] = Field(default_factory=list, description="Identified weaknesses")
    skill_matches: Dict[str, Decimal] = Field(default_factory=dict, description="Skill match scores")
    recommendation: str = Field(description="AI recommendation (proceed, reject, needs_review)")
    reasoning: str = Field(description="Detailed reasoning for the recommendation")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "score": 0.85,
                "confidence": 0.92,
                "summary": "Strong candidate with excellent Python and React skills",
                "strengths": ["Strong technical skills", "Relevant experience", "Good communication"],
                "weaknesses": ["Limited leadership experience", "No cloud platform experience"],
                "skill_matches": {
                    "Python": 0.95,
                    "React": 0.80,
                    "AWS": 0.20
                },
                "recommendation": "proceed",
                "reasoning": "Candidate demonstrates strong technical abilities and relevant experience for the role"
            }
        }
    }


class Application(BaseEntity):
    """Application model"""
    job_id: UUID = Field(description="Job ID this application is for")
    candidate_id: UUID = Field(description="Candidate who submitted the application")
    
    # Application status and metadata
    status: ApplicationStatus = Field(default=ApplicationStatus.APPLIED, description="Current application status")
    priority: ApplicationPriority = Field(default=ApplicationPriority.MEDIUM, description="Application priority")
    
    # Application content
    cover_letter: Optional[str] = Field(default=None, description="Cover letter text")
    custom_responses: Dict[str, str] = Field(default_factory=dict, description="Responses to custom questions")
    
    # AI screening results
    ai_screening_score: Optional[Decimal] = Field(default=None, ge=0.0, le=1.0, description="AI screening score")
    ai_screening_result: Optional[AIScreeningResult] = Field(default=None, description="Detailed AI screening results")
    ai_screening_completed_at: Optional[str] = Field(default=None, description="When AI screening was completed")
    
    # Human review
    human_review_score: Optional[Decimal] = Field(default=None, ge=0.0, le=1.0, description="Human reviewer score")
    human_review_notes: Optional[str] = Field(default=None, description="Human reviewer notes")
    reviewed_by: Optional[UUID] = Field(default=None, description="ID of human reviewer")
    reviewed_at: Optional[str] = Field(default=None, description="When human review was completed")
    
    # Application timeline
    application_date: str = Field(description="When the application was submitted")
    last_status_change: str = Field(description="When status was last changed")
    
    # Communication tracking
    last_contact_date: Optional[str] = Field(default=None, description="Last communication with candidate")
    next_follow_up_date: Optional[str] = Field(default=None, description="Scheduled follow-up date")
    
    # Rejection details
    rejection_reason: Optional[str] = Field(default=None, description="Reason for rejection")
    rejection_feedback: Optional[str] = Field(default=None, description="Feedback provided to candidate")
    
    # Offer details
    offer_details: Optional[Dict[str, Any]] = Field(default=None, description="Offer details if applicable")
    offer_sent_date: Optional[str] = Field(default=None, description="When offer was sent")
    offer_response_deadline: Optional[str] = Field(default=None, description="Offer response deadline")
    
    # Analytics and tracking
    source_campaign: Optional[str] = Field(default=None, description="Marketing campaign source")
    referral_bonus_eligible: bool = Field(default=False, description="Whether eligible for referral bonus")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "990e8400-e29b-41d4-a716-446655440004",
                "job_id": "770e8400-e29b-41d4-a716-446655440002",
                "candidate_id": "880e8400-e29b-41d4-a716-446655440003",
                "status": "screening",
                "priority": "high",
                "cover_letter": "I am excited to apply for this position...",
                "ai_screening_score": 0.85,
                "ai_screening_result": {
                    "score": 0.85,
                    "confidence": 0.92,
                    "summary": "Strong candidate with excellent technical skills",
                    "recommendation": "proceed"
                },
                "application_date": "2025-01-20T10:00:00Z",
                "last_status_change": "2025-01-20T14:30:00Z"
            }
        }
    }


class ApplicationCreate(BaseCreate):
    """Model for creating a new application"""
    job_id: UUID = Field(description="Job ID this application is for")
    candidate_id: UUID = Field(description="Candidate who submitted the application")
    
    cover_letter: Optional[str] = Field(default=None, description="Cover letter text")
    custom_responses: Dict[str, str] = Field(default_factory=dict, description="Responses to custom questions")
    
    priority: ApplicationPriority = Field(default=ApplicationPriority.MEDIUM, description="Application priority")
    source_campaign: Optional[str] = Field(default=None, description="Marketing campaign source")
    referral_bonus_eligible: bool = Field(default=False, description="Whether eligible for referral bonus")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "job_id": "770e8400-e29b-41d4-a716-446655440002",
                "candidate_id": "880e8400-e29b-41d4-a716-446655440003",
                "cover_letter": "I am excited to apply for this position because...",
                "custom_responses": {
                    "Why do you want to work here?": "I admire the company's mission...",
                    "What is your salary expectation?": "$120,000 - $150,000"
                },
                "priority": "high"
            }
        }
    }


class ApplicationUpdate(BaseUpdate):
    """Model for updating application information"""
    status: Optional[ApplicationStatus] = Field(default=None, description="Application status")
    priority: Optional[ApplicationPriority] = Field(default=None, description="Application priority")
    
    cover_letter: Optional[str] = Field(default=None, description="Cover letter text")
    custom_responses: Optional[Dict[str, str]] = Field(default=None, description="Responses to custom questions")
    
    human_review_score: Optional[Decimal] = Field(default=None, ge=0.0, le=1.0, description="Human reviewer score")
    human_review_notes: Optional[str] = Field(default=None, description="Human reviewer notes")
    
    next_follow_up_date: Optional[str] = Field(default=None, description="Scheduled follow-up date")
    
    rejection_reason: Optional[str] = Field(default=None, description="Reason for rejection")
    rejection_feedback: Optional[str] = Field(default=None, description="Feedback provided to candidate")
    
    offer_details: Optional[Dict[str, Any]] = Field(default=None, description="Offer details")
    offer_response_deadline: Optional[str] = Field(default=None, description="Offer response deadline")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "interview",
                "priority": "high",
                "human_review_score": 0.90,
                "human_review_notes": "Excellent candidate, proceed to interview"
            }
        }
    }


class ApplicationSearch(BaseCreate):
    """Model for application search parameters"""
    job_id: Optional[UUID] = Field(default=None, description="Filter by job ID")
    candidate_id: Optional[UUID] = Field(default=None, description="Filter by candidate ID")
    status: Optional[ApplicationStatus] = Field(default=None, description="Filter by status")
    priority: Optional[ApplicationPriority] = Field(default=None, description="Filter by priority")
    
    ai_score_min: Optional[Decimal] = Field(default=None, ge=0.0, le=1.0, description="Minimum AI score")
    ai_score_max: Optional[Decimal] = Field(default=None, ge=0.0, le=1.0, description="Maximum AI score")
    
    human_score_min: Optional[Decimal] = Field(default=None, ge=0.0, le=1.0, description="Minimum human score")
    human_score_max: Optional[Decimal] = Field(default=None, ge=0.0, le=1.0, description="Maximum human score")
    
    reviewed_by: Optional[UUID] = Field(default=None, description="Filter by reviewer")
    needs_review: Optional[bool] = Field(default=None, description="Filter applications needing review")
    
    application_date_from: Optional[str] = Field(default=None, description="Filter by application date (from)")
    application_date_to: Optional[str] = Field(default=None, description="Filter by application date (to)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "screening",
                "priority": "high",
                "ai_score_min": 0.7,
                "needs_review": True,
                "application_date_from": "2025-01-01"
            }
        }
    }


class ApplicationStats(BaseCreate):
    """Model for application statistics"""
    total_applications: int = Field(ge=0, description="Total number of applications")
    by_status: Dict[str, int] = Field(description="Applications count by status")
    by_priority: Dict[str, int] = Field(description="Applications count by priority")
    average_ai_score: Optional[Decimal] = Field(default=None, description="Average AI screening score")
    average_human_score: Optional[Decimal] = Field(default=None, description="Average human review score")
    conversion_rates: Dict[str, Decimal] = Field(description="Conversion rates between stages")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "total_applications": 150,
                "by_status": {
                    "applied": 45,
                    "screening": 30,
                    "interview": 25,
                    "offer": 5,
                    "hired": 3,
                    "rejected": 42
                },
                "by_priority": {
                    "low": 30,
                    "medium": 80,
                    "high": 35,
                    "urgent": 5
                },
                "average_ai_score": 0.72,
                "average_human_score": 0.68,
                "conversion_rates": {
                    "applied_to_screening": 0.85,
                    "screening_to_interview": 0.60,
                    "interview_to_offer": 0.25,
                    "offer_to_hired": 0.80
                }
            }
        }
    }
