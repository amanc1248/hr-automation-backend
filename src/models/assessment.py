"""
Assessment models for HR Automation System.
"""

from pydantic import Field
from typing import Optional, List, Dict, Any
from enum import Enum
from uuid import UUID
from decimal import Decimal

from .base import BaseEntity, BaseCreate, BaseUpdate


class AssessmentType(str, Enum):
    """Assessment type enumeration"""
    TECHNICAL = "technical"
    CODING = "coding"
    DESIGN = "design"
    BEHAVIORAL = "behavioral"
    COGNITIVE = "cognitive"
    PERSONALITY = "personality"
    CUSTOM = "custom"


class AssessmentStatus(str, Enum):
    """Assessment status enumeration"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class QuestionType(str, Enum):
    """Question type enumeration"""
    MULTIPLE_CHOICE = "multiple_choice"
    SINGLE_CHOICE = "single_choice"
    TEXT = "text"
    CODE = "code"
    FILE_UPLOAD = "file_upload"
    RATING = "rating"


class AssessmentQuestion(BaseCreate):
    """Assessment question model"""
    question_id: str = Field(description="Unique question identifier")
    question_type: QuestionType = Field(description="Type of question")
    title: str = Field(description="Question title/prompt")
    description: Optional[str] = Field(default=None, description="Detailed question description")
    
    # Multiple choice options
    options: List[str] = Field(default_factory=list, description="Answer options for choice questions")
    correct_answers: List[str] = Field(default_factory=list, description="Correct answers (for auto-grading)")
    
    # Scoring
    max_score: Decimal = Field(default=10.0, ge=0, description="Maximum score for this question")
    weight: Decimal = Field(default=1.0, ge=0, description="Question weight in overall score")
    
    # Constraints
    time_limit_minutes: Optional[int] = Field(default=None, ge=1, description="Time limit for this question")
    required: bool = Field(default=True, description="Whether this question is required")
    
    # Metadata
    tags: List[str] = Field(default_factory=list, description="Question tags/categories")
    difficulty_level: str = Field(default="medium", description="Difficulty level (easy, medium, hard)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_id": "q1",
                "question_type": "code",
                "title": "Implement a binary search algorithm",
                "description": "Write a function that performs binary search on a sorted array",
                "max_score": 20.0,
                "weight": 2.0,
                "time_limit_minutes": 30,
                "tags": ["algorithms", "python"],
                "difficulty_level": "medium"
            }
        }
    }


class CandidateResponse(BaseCreate):
    """Candidate response to assessment question"""
    question_id: str = Field(description="Question identifier")
    response_text: Optional[str] = Field(default=None, description="Text response")
    selected_options: List[str] = Field(default_factory=list, description="Selected options for choice questions")
    file_urls: List[str] = Field(default_factory=list, description="Uploaded file URLs")
    
    # Timing
    time_spent_minutes: Optional[Decimal] = Field(default=None, ge=0, description="Time spent on this question")
    started_at: Optional[str] = Field(default=None, description="When candidate started this question")
    completed_at: Optional[str] = Field(default=None, description="When candidate completed this question")
    
    # Scoring
    score: Optional[Decimal] = Field(default=None, ge=0, description="Score received for this response")
    auto_score: Optional[Decimal] = Field(default=None, ge=0, description="Automatically calculated score")
    manual_score: Optional[Decimal] = Field(default=None, ge=0, description="Manually assigned score")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "question_id": "q1",
                "response_text": "def binary_search(arr, target):\n    left, right = 0, len(arr) - 1\n    ...",
                "time_spent_minutes": 25.5,
                "started_at": "2025-01-25T10:00:00Z",
                "completed_at": "2025-01-25T10:25:30Z",
                "auto_score": 18.0
            }
        }
    }


class AIEvaluation(BaseCreate):
    """AI evaluation of assessment"""
    overall_score: Decimal = Field(ge=0.0, le=100.0, description="Overall AI-calculated score")
    confidence: Decimal = Field(ge=0.0, le=1.0, description="Confidence in the evaluation")
    
    question_scores: Dict[str, Decimal] = Field(description="Scores for individual questions")
    strengths: List[str] = Field(default_factory=list, description="Identified strengths")
    weaknesses: List[str] = Field(default_factory=list, description="Identified weaknesses")
    
    detailed_feedback: Dict[str, str] = Field(default_factory=dict, description="Detailed feedback per question")
    recommendations: List[str] = Field(default_factory=list, description="Recommendations for improvement")
    
    skill_assessment: Dict[str, Decimal] = Field(default_factory=dict, description="Skill-specific scores")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "overall_score": 85.5,
                "confidence": 0.92,
                "question_scores": {
                    "q1": 18.0,
                    "q2": 15.5,
                    "q3": 12.0
                },
                "strengths": ["Strong algorithmic thinking", "Clean code structure"],
                "weaknesses": ["Could optimize time complexity", "Missing edge case handling"],
                "skill_assessment": {
                    "algorithms": 0.85,
                    "python": 0.90,
                    "problem_solving": 0.80
                }
            }
        }
    }


class Assessment(BaseEntity):
    """Assessment model"""
    application_id: UUID = Field(description="Application this assessment is for")
    
    # Assessment details
    assessment_type: AssessmentType = Field(description="Type of assessment")
    title: str = Field(description="Assessment title")
    description: Optional[str] = Field(default=None, description="Assessment description")
    instructions: Optional[str] = Field(default=None, description="Instructions for candidates")
    
    # Questions and structure
    questions: List[AssessmentQuestion] = Field(description="Assessment questions")
    total_questions: int = Field(ge=1, description="Total number of questions")
    
    # Timing and constraints
    time_limit_minutes: Optional[int] = Field(default=None, ge=1, description="Overall time limit")
    attempts_allowed: int = Field(default=1, ge=1, description="Number of attempts allowed")
    
    # Status and progress
    status: AssessmentStatus = Field(default=AssessmentStatus.PENDING, description="Assessment status")
    current_attempt: int = Field(default=0, ge=0, description="Current attempt number")
    
    # Candidate responses
    candidate_responses: List[CandidateResponse] = Field(default_factory=list, description="Candidate responses")
    
    # Timing tracking
    started_at: Optional[str] = Field(default=None, description="When assessment was started")
    completed_at: Optional[str] = Field(default=None, description="When assessment was completed")
    time_spent_minutes: Optional[Decimal] = Field(default=None, ge=0, description="Total time spent")
    
    # Scoring and evaluation
    score: Optional[Decimal] = Field(default=None, ge=0, description="Final assessment score")
    max_possible_score: Decimal = Field(ge=0, description="Maximum possible score")
    percentage_score: Optional[Decimal] = Field(default=None, ge=0, le=100, description="Percentage score")
    
    # AI evaluation
    ai_evaluation: Optional[AIEvaluation] = Field(default=None, description="AI-generated evaluation")
    ai_evaluation_completed_at: Optional[str] = Field(default=None, description="When AI evaluation was completed")
    
    # Human review
    human_review_score: Optional[Decimal] = Field(default=None, ge=0, description="Human reviewer score")
    human_review_notes: Optional[str] = Field(default=None, description="Human reviewer notes")
    reviewed_by: Optional[UUID] = Field(default=None, description="ID of human reviewer")
    reviewed_at: Optional[str] = Field(default=None, description="When human review was completed")
    
    # Settings
    auto_grade: bool = Field(default=True, description="Whether to auto-grade the assessment")
    show_results_immediately: bool = Field(default=False, description="Show results to candidate immediately")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "bb0e8400-e29b-41d4-a716-446655440006",
                "application_id": "990e8400-e29b-41d4-a716-446655440004",
                "assessment_type": "technical",
                "title": "Python Technical Assessment",
                "description": "Technical assessment for Python developer position",
                "total_questions": 5,
                "time_limit_minutes": 120,
                "status": "completed",
                "score": 85.5,
                "max_possible_score": 100.0,
                "percentage_score": 85.5,
                "started_at": "2025-01-25T09:00:00Z",
                "completed_at": "2025-01-25T10:45:00Z",
                "time_spent_minutes": 105.0
            }
        }
    }


class AssessmentCreate(BaseCreate):
    """Model for creating a new assessment"""
    application_id: UUID = Field(description="Application this assessment is for")
    
    assessment_type: AssessmentType = Field(description="Type of assessment")
    title: str = Field(description="Assessment title")
    description: Optional[str] = Field(default=None, description="Assessment description")
    instructions: Optional[str] = Field(default=None, description="Instructions for candidates")
    
    questions: List[AssessmentQuestion] = Field(description="Assessment questions")
    
    time_limit_minutes: Optional[int] = Field(default=None, ge=1, description="Overall time limit")
    attempts_allowed: int = Field(default=1, ge=1, description="Number of attempts allowed")
    
    auto_grade: bool = Field(default=True, description="Whether to auto-grade the assessment")
    show_results_immediately: bool = Field(default=False, description="Show results to candidate immediately")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "application_id": "990e8400-e29b-41d4-a716-446655440004",
                "assessment_type": "technical",
                "title": "Python Technical Assessment",
                "description": "Technical assessment for Python developer position",
                "questions": [
                    {
                        "question_id": "q1",
                        "question_type": "code",
                        "title": "Implement binary search",
                        "max_score": 20.0
                    }
                ],
                "time_limit_minutes": 120,
                "auto_grade": True
            }
        }
    }


class AssessmentUpdate(BaseUpdate):
    """Model for updating assessment information"""
    title: Optional[str] = Field(default=None, description="Assessment title")
    description: Optional[str] = Field(default=None, description="Assessment description")
    instructions: Optional[str] = Field(default=None, description="Instructions for candidates")
    
    status: Optional[AssessmentStatus] = Field(default=None, description="Assessment status")
    
    candidate_responses: Optional[List[CandidateResponse]] = Field(default=None, description="Candidate responses")
    
    started_at: Optional[str] = Field(default=None, description="When assessment was started")
    completed_at: Optional[str] = Field(default=None, description="When assessment was completed")
    
    score: Optional[Decimal] = Field(default=None, ge=0, description="Final assessment score")
    ai_evaluation: Optional[AIEvaluation] = Field(default=None, description="AI-generated evaluation")
    
    human_review_score: Optional[Decimal] = Field(default=None, ge=0, description="Human reviewer score")
    human_review_notes: Optional[str] = Field(default=None, description="Human reviewer notes")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "completed",
                "completed_at": "2025-01-25T10:45:00Z",
                "score": 85.5,
                "human_review_score": 88.0,
                "human_review_notes": "Excellent problem-solving approach"
            }
        }
    }


class AssessmentSearch(BaseCreate):
    """Model for assessment search parameters"""
    application_id: Optional[UUID] = Field(default=None, description="Filter by application ID")
    assessment_type: Optional[AssessmentType] = Field(default=None, description="Filter by assessment type")
    status: Optional[AssessmentStatus] = Field(default=None, description="Filter by status")
    
    score_min: Optional[Decimal] = Field(default=None, ge=0, description="Minimum score filter")
    score_max: Optional[Decimal] = Field(default=None, ge=0, description="Maximum score filter")
    
    completed_from: Optional[str] = Field(default=None, description="Filter by completion date (from)")
    completed_to: Optional[str] = Field(default=None, description="Filter by completion date (to)")
    
    needs_review: Optional[bool] = Field(default=None, description="Filter assessments needing review")
    reviewed_by: Optional[UUID] = Field(default=None, description="Filter by reviewer")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "assessment_type": "technical",
                "status": "completed",
                "score_min": 70.0,
                "needs_review": True,
                "completed_from": "2025-01-20"
            }
        }
    }
