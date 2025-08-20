"""
Interview models for HR Automation System.
"""

from pydantic import Field, HttpUrl
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
from decimal import Decimal

from .base import BaseEntity, BaseCreate, BaseUpdate


class InterviewType(str, Enum):
    """Interview type enumeration"""
    SCREENING = "screening"
    TECHNICAL = "technical"
    BEHAVIORAL = "behavioral"
    FINAL = "final"
    AI_INTERVIEW = "ai_interview"
    PANEL = "panel"
    PHONE = "phone"
    VIDEO = "video"


class InterviewStatus(str, Enum):
    """Interview status enumeration"""
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    NO_SHOW = "no_show"
    RESCHEDULED = "rescheduled"


class InterviewMode(str, Enum):
    """Interview mode enumeration"""
    IN_PERSON = "in_person"
    VIDEO_CALL = "video_call"
    PHONE_CALL = "phone_call"
    AI_POWERED = "ai_powered"


class AIInterviewConfig(BaseCreate):
    """AI interview configuration model"""
    voice_clone_enabled: bool = Field(default=False, description="Enable voice cloning")
    interviewer_voice_id: Optional[str] = Field(default=None, description="Voice ID for cloning")
    interview_script: Optional[str] = Field(default=None, description="Custom interview script")
    questions: List[str] = Field(default_factory=list, description="Predefined questions")
    max_duration_minutes: int = Field(default=60, ge=15, le=180, description="Maximum interview duration")
    auto_evaluation: bool = Field(default=True, description="Enable automatic evaluation")
    recording_enabled: bool = Field(default=True, description="Enable interview recording")
    transcript_enabled: bool = Field(default=True, description="Enable live transcription")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "voice_clone_enabled": True,
                "interviewer_voice_id": "voice_123",
                "questions": [
                    "Tell me about your experience with Python",
                    "How do you handle debugging complex issues?",
                    "Describe a challenging project you worked on"
                ],
                "max_duration_minutes": 45,
                "auto_evaluation": True,
                "recording_enabled": True
            }
        }
    }


class InterviewFeedback(BaseCreate):
    """Interview feedback model"""
    overall_score: Decimal = Field(ge=0.0, le=10.0, description="Overall interview score (0-10)")
    technical_skills: Optional[Decimal] = Field(default=None, ge=0.0, le=10.0, description="Technical skills score")
    communication: Optional[Decimal] = Field(default=None, ge=0.0, le=10.0, description="Communication score")
    problem_solving: Optional[Decimal] = Field(default=None, ge=0.0, le=10.0, description="Problem solving score")
    cultural_fit: Optional[Decimal] = Field(default=None, ge=0.0, le=10.0, description="Cultural fit score")
    
    strengths: List[str] = Field(default_factory=list, description="Candidate strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Areas for improvement")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    recommendation: str = Field(description="Hiring recommendation (hire, no_hire, maybe)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "overall_score": 8.5,
                "technical_skills": 9.0,
                "communication": 8.0,
                "problem_solving": 8.5,
                "cultural_fit": 8.0,
                "strengths": ["Strong technical knowledge", "Good problem-solving approach"],
                "weaknesses": ["Could improve communication clarity"],
                "notes": "Solid candidate with strong technical background",
                "recommendation": "hire"
            }
        }
    }


class Interview(BaseEntity):
    """Interview model"""
    application_id: UUID = Field(description="Application this interview is for")
    
    # Interview details
    interview_type: InterviewType = Field(description="Type of interview")
    interview_mode: InterviewMode = Field(default=InterviewMode.VIDEO_CALL, description="Interview mode")
    title: str = Field(description="Interview title/subject")
    description: Optional[str] = Field(default=None, description="Interview description")
    
    # Scheduling
    scheduled_at: Optional[str] = Field(default=None, description="Scheduled date and time")
    duration_minutes: int = Field(default=60, ge=15, le=240, description="Expected duration in minutes")
    time_zone: str = Field(default="UTC", description="Time zone for the interview")
    
    # Participants
    interviewer_id: Optional[UUID] = Field(default=None, description="Primary interviewer ID")
    additional_interviewers: List[UUID] = Field(default_factory=list, description="Additional interviewer IDs")
    
    # Meeting details
    meeting_link: Optional[HttpUrl] = Field(default=None, description="Video meeting link")
    meeting_id: Optional[str] = Field(default=None, description="Meeting ID/room number")
    meeting_password: Optional[str] = Field(default=None, description="Meeting password")
    location: Optional[str] = Field(default=None, description="Physical location if in-person")
    
    # Status and progress
    status: InterviewStatus = Field(default=InterviewStatus.SCHEDULED, description="Interview status")
    actual_start_time: Optional[str] = Field(default=None, description="Actual start time")
    actual_end_time: Optional[str] = Field(default=None, description="Actual end time")
    
    # AI interview specific
    ai_interview_config: Optional[AIInterviewConfig] = Field(default=None, description="AI interview configuration")
    ai_generated_questions: List[str] = Field(default_factory=list, description="AI-generated questions")
    
    # Recording and transcription
    recording_url: Optional[HttpUrl] = Field(default=None, description="Interview recording URL")
    transcript: Optional[str] = Field(default=None, description="Interview transcript")
    
    # Feedback and evaluation
    feedback: Optional[InterviewFeedback] = Field(default=None, description="Interview feedback")
    ai_evaluation: Optional[Dict[str, Any]] = Field(default=None, description="AI-generated evaluation")
    
    # Follow-up
    follow_up_required: bool = Field(default=False, description="Whether follow-up is required")
    follow_up_notes: Optional[str] = Field(default=None, description="Follow-up notes")
    next_steps: Optional[str] = Field(default=None, description="Next steps after interview")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "aa0e8400-e29b-41d4-a716-446655440005",
                "application_id": "990e8400-e29b-41d4-a716-446655440004",
                "interview_type": "technical",
                "interview_mode": "video_call",
                "title": "Technical Interview - Senior Full Stack Engineer",
                "scheduled_at": "2025-01-25T14:00:00Z",
                "duration_minutes": 60,
                "interviewer_id": "550e8400-e29b-41d4-a716-446655440000",
                "meeting_link": "https://zoom.us/j/123456789",
                "status": "scheduled",
                "ai_interview_config": {
                    "voice_clone_enabled": True,
                    "max_duration_minutes": 45,
                    "auto_evaluation": True
                }
            }
        }
    }


class InterviewCreate(BaseCreate):
    """Model for creating a new interview"""
    application_id: UUID = Field(description="Application this interview is for")
    
    interview_type: InterviewType = Field(description="Type of interview")
    interview_mode: InterviewMode = Field(default=InterviewMode.VIDEO_CALL, description="Interview mode")
    title: str = Field(description="Interview title/subject")
    description: Optional[str] = Field(default=None, description="Interview description")
    
    scheduled_at: Optional[str] = Field(default=None, description="Scheduled date and time")
    duration_minutes: int = Field(default=60, ge=15, le=240, description="Expected duration in minutes")
    time_zone: str = Field(default="UTC", description="Time zone for the interview")
    
    interviewer_id: Optional[UUID] = Field(default=None, description="Primary interviewer ID")
    additional_interviewers: List[UUID] = Field(default_factory=list, description="Additional interviewer IDs")
    
    meeting_link: Optional[HttpUrl] = Field(default=None, description="Video meeting link")
    location: Optional[str] = Field(default=None, description="Physical location if in-person")
    
    ai_interview_config: Optional[AIInterviewConfig] = Field(default=None, description="AI interview configuration")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "application_id": "990e8400-e29b-41d4-a716-446655440004",
                "interview_type": "technical",
                "interview_mode": "ai_powered",
                "title": "AI Technical Interview",
                "scheduled_at": "2025-01-25T14:00:00Z",
                "duration_minutes": 45,
                "ai_interview_config": {
                    "voice_clone_enabled": True,
                    "questions": ["Tell me about your Python experience"],
                    "max_duration_minutes": 45
                }
            }
        }
    }


class InterviewUpdate(BaseUpdate):
    """Model for updating interview information"""
    interview_type: Optional[InterviewType] = Field(default=None, description="Type of interview")
    interview_mode: Optional[InterviewMode] = Field(default=None, description="Interview mode")
    title: Optional[str] = Field(default=None, description="Interview title/subject")
    description: Optional[str] = Field(default=None, description="Interview description")
    
    scheduled_at: Optional[str] = Field(default=None, description="Scheduled date and time")
    duration_minutes: Optional[int] = Field(default=None, ge=15, le=240, description="Expected duration in minutes")
    
    interviewer_id: Optional[UUID] = Field(default=None, description="Primary interviewer ID")
    additional_interviewers: Optional[List[UUID]] = Field(default=None, description="Additional interviewer IDs")
    
    meeting_link: Optional[HttpUrl] = Field(default=None, description="Video meeting link")
    location: Optional[str] = Field(default=None, description="Physical location if in-person")
    
    status: Optional[InterviewStatus] = Field(default=None, description="Interview status")
    actual_start_time: Optional[str] = Field(default=None, description="Actual start time")
    actual_end_time: Optional[str] = Field(default=None, description="Actual end time")
    
    recording_url: Optional[HttpUrl] = Field(default=None, description="Interview recording URL")
    transcript: Optional[str] = Field(default=None, description="Interview transcript")
    
    feedback: Optional[InterviewFeedback] = Field(default=None, description="Interview feedback")
    ai_evaluation: Optional[Dict[str, Any]] = Field(default=None, description="AI-generated evaluation")
    
    follow_up_required: Optional[bool] = Field(default=None, description="Whether follow-up is required")
    follow_up_notes: Optional[str] = Field(default=None, description="Follow-up notes")
    next_steps: Optional[str] = Field(default=None, description="Next steps after interview")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "completed",
                "actual_start_time": "2025-01-25T14:00:00Z",
                "actual_end_time": "2025-01-25T14:45:00Z",
                "feedback": {
                    "overall_score": 8.5,
                    "recommendation": "hire"
                },
                "next_steps": "Proceed to final interview"
            }
        }
    }


class InterviewSearch(BaseCreate):
    """Model for interview search parameters"""
    application_id: Optional[UUID] = Field(default=None, description="Filter by application ID")
    interviewer_id: Optional[UUID] = Field(default=None, description="Filter by interviewer ID")
    interview_type: Optional[InterviewType] = Field(default=None, description="Filter by interview type")
    interview_mode: Optional[InterviewMode] = Field(default=None, description="Filter by interview mode")
    status: Optional[InterviewStatus] = Field(default=None, description="Filter by status")
    
    scheduled_from: Optional[str] = Field(default=None, description="Filter by scheduled date (from)")
    scheduled_to: Optional[str] = Field(default=None, description="Filter by scheduled date (to)")
    
    needs_feedback: Optional[bool] = Field(default=None, description="Filter interviews needing feedback")
    ai_interviews_only: Optional[bool] = Field(default=None, description="Filter AI interviews only")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "interview_type": "technical",
                "status": "completed",
                "scheduled_from": "2025-01-20",
                "scheduled_to": "2025-01-27",
                "needs_feedback": True
            }
        }
    }
