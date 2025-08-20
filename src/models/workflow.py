"""
Workflow models for HR Automation System (Portia integration).
"""

from pydantic import Field
from typing import Optional, Dict, Any, List
from enum import Enum
from uuid import UUID
from decimal import Decimal

from .base import BaseEntity, BaseCreate, BaseUpdate


class WorkflowType(str, Enum):
    """Workflow type enumeration"""
    HIRING_PROCESS = "hiring_process"
    CANDIDATE_SCREENING = "candidate_screening"
    INTERVIEW_SCHEDULING = "interview_scheduling"
    AI_INTERVIEW = "ai_interview"
    ASSESSMENT_CREATION = "assessment_creation"
    OFFER_GENERATION = "offer_generation"
    ONBOARDING = "onboarding"
    JOB_POSTING = "job_posting"
    CUSTOM = "custom"


class WorkflowStatus(str, Enum):
    """Workflow status enumeration"""
    PENDING = "pending"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EntityType(str, Enum):
    """Entity type enumeration for workflow context"""
    JOB = "job"
    CANDIDATE = "candidate"
    APPLICATION = "application"
    INTERVIEW = "interview"
    ASSESSMENT = "assessment"
    COMPANY = "company"


class WorkflowStep(BaseCreate):
    """Individual workflow step model"""
    step_id: str = Field(description="Unique step identifier")
    step_name: str = Field(description="Human-readable step name")
    step_type: str = Field(description="Type of step (tool_call, decision, human_input)")
    description: Optional[str] = Field(default=None, description="Step description")
    
    # Execution details
    status: str = Field(default="pending", description="Step status")
    started_at: Optional[str] = Field(default=None, description="When step started")
    completed_at: Optional[str] = Field(default=None, description="When step completed")
    
    # Input/Output
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Step inputs")
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Step outputs")
    
    # Error handling
    error_message: Optional[str] = Field(default=None, description="Error message if step failed")
    retry_count: int = Field(default=0, ge=0, description="Number of retries attempted")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "step_id": "screen_resume",
                "step_name": "AI Resume Screening",
                "step_type": "tool_call",
                "description": "Analyze candidate resume using AI",
                "status": "completed",
                "started_at": "2025-01-25T10:00:00Z",
                "completed_at": "2025-01-25T10:02:30Z",
                "inputs": {"resume_text": "John Doe's resume..."},
                "outputs": {"screening_score": 0.85, "recommendation": "proceed"}
            }
        }
    }


class Clarification(BaseCreate):
    """Workflow clarification model (human-in-the-loop)"""
    clarification_id: str = Field(description="Unique clarification identifier")
    question: str = Field(description="Question for human reviewer")
    context: Dict[str, Any] = Field(default_factory=dict, description="Context information")
    
    # Response details
    response: Optional[Any] = Field(default=None, description="Human response")
    responded_by: Optional[UUID] = Field(default=None, description="ID of person who responded")
    responded_at: Optional[str] = Field(default=None, description="When response was provided")
    
    # Metadata
    priority: str = Field(default="medium", description="Clarification priority")
    timeout_minutes: Optional[int] = Field(default=None, description="Timeout for response")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "clarification_id": "approve_offer",
                "question": "Should we proceed with offer for John Doe at $120k salary?",
                "context": {
                    "candidate_name": "John Doe",
                    "position": "Senior Engineer",
                    "salary": 120000,
                    "screening_score": 0.85
                },
                "priority": "high",
                "timeout_minutes": 60
            }
        }
    }


class Workflow(BaseEntity):
    """Workflow model for Portia plan runs"""
    # Portia integration
    plan_run_id: Optional[str] = Field(default=None, description="Portia plan run ID")
    
    # Workflow identification
    workflow_type: WorkflowType = Field(description="Type of workflow")
    name: str = Field(description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    
    # Entity context
    entity_id: Optional[UUID] = Field(default=None, description="Related entity ID")
    entity_type: Optional[EntityType] = Field(default=None, description="Type of related entity")
    
    # Status and progress
    status: WorkflowStatus = Field(default=WorkflowStatus.PENDING, description="Workflow status")
    current_step_index: int = Field(default=0, ge=0, description="Current step index")
    total_steps: Optional[int] = Field(default=None, ge=0, description="Total number of steps")
    progress_percentage: Decimal = Field(default=0.0, ge=0.0, le=100.0, description="Progress percentage")
    
    # Execution details
    started_at: Optional[str] = Field(default=None, description="When workflow started")
    completed_at: Optional[str] = Field(default=None, description="When workflow completed")
    estimated_completion: Optional[str] = Field(default=None, description="Estimated completion time")
    
    # Steps and clarifications
    steps: List[WorkflowStep] = Field(default_factory=list, description="Workflow steps")
    clarifications: List[Clarification] = Field(default_factory=list, description="Pending clarifications")
    
    # Outputs and results
    outputs: Dict[str, Any] = Field(default_factory=dict, description="Workflow outputs")
    final_result: Optional[Dict[str, Any]] = Field(default=None, description="Final workflow result")
    
    # Error handling
    error_message: Optional[str] = Field(default=None, description="Error message if workflow failed")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Detailed error information")
    
    # User context
    created_by: UUID = Field(description="User who created the workflow")
    assigned_to: Optional[UUID] = Field(default=None, description="User assigned to handle clarifications")
    
    # Configuration
    auto_resume: bool = Field(default=True, description="Auto-resume after clarifications")
    timeout_minutes: Optional[int] = Field(default=None, description="Workflow timeout")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "cc0e8400-e29b-41d4-a716-446655440007",
                "plan_run_id": "prun_123456789",
                "workflow_type": "hiring_process",
                "name": "Complete Hiring Process - Senior Engineer",
                "entity_id": "770e8400-e29b-41d4-a716-446655440002",
                "entity_type": "job",
                "status": "running",
                "current_step_index": 3,
                "total_steps": 8,
                "progress_percentage": 37.5,
                "started_at": "2025-01-25T09:00:00Z",
                "created_by": "550e8400-e29b-41d4-a716-446655440000",
                "steps": [
                    {
                        "step_id": "create_job_posting",
                        "step_name": "Create Job Posting",
                        "status": "completed"
                    }
                ],
                "clarifications": [
                    {
                        "clarification_id": "approve_candidate",
                        "question": "Should we proceed with this candidate?",
                        "priority": "high"
                    }
                ]
            }
        }
    }


class WorkflowCreate(BaseCreate):
    """Model for creating a new workflow"""
    workflow_type: WorkflowType = Field(description="Type of workflow")
    name: str = Field(description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    
    entity_id: Optional[UUID] = Field(default=None, description="Related entity ID")
    entity_type: Optional[EntityType] = Field(default=None, description="Type of related entity")
    
    created_by: UUID = Field(description="User who created the workflow")
    assigned_to: Optional[UUID] = Field(default=None, description="User assigned to handle clarifications")
    
    # Configuration
    auto_resume: bool = Field(default=True, description="Auto-resume after clarifications")
    timeout_minutes: Optional[int] = Field(default=None, description="Workflow timeout")
    
    # Initial inputs
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Initial workflow inputs")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow_type": "hiring_process",
                "name": "Complete Hiring Process - Senior Engineer",
                "description": "Full hiring workflow for senior engineer position",
                "entity_id": "770e8400-e29b-41d4-a716-446655440002",
                "entity_type": "job",
                "created_by": "550e8400-e29b-41d4-a716-446655440000",
                "inputs": {
                    "job_title": "Senior Full Stack Engineer",
                    "auto_screening": True,
                    "ai_interviews": True
                }
            }
        }
    }


class WorkflowUpdate(BaseUpdate):
    """Model for updating workflow information"""
    name: Optional[str] = Field(default=None, description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    
    status: Optional[WorkflowStatus] = Field(default=None, description="Workflow status")
    assigned_to: Optional[UUID] = Field(default=None, description="User assigned to handle clarifications")
    
    steps: Optional[List[WorkflowStep]] = Field(default=None, description="Updated workflow steps")
    clarifications: Optional[List[Clarification]] = Field(default=None, description="Updated clarifications")
    
    outputs: Optional[Dict[str, Any]] = Field(default=None, description="Workflow outputs")
    final_result: Optional[Dict[str, Any]] = Field(default=None, description="Final workflow result")
    
    error_message: Optional[str] = Field(default=None, description="Error message")
    error_details: Optional[Dict[str, Any]] = Field(default=None, description="Error details")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "status": "paused",
                "assigned_to": "550e8400-e29b-41d4-a716-446655440000",
                "error_message": "Waiting for human approval"
            }
        }
    }


class WorkflowSearch(BaseCreate):
    """Model for workflow search parameters"""
    workflow_type: Optional[WorkflowType] = Field(default=None, description="Filter by workflow type")
    status: Optional[WorkflowStatus] = Field(default=None, description="Filter by status")
    
    entity_id: Optional[UUID] = Field(default=None, description="Filter by entity ID")
    entity_type: Optional[EntityType] = Field(default=None, description="Filter by entity type")
    
    created_by: Optional[UUID] = Field(default=None, description="Filter by creator")
    assigned_to: Optional[UUID] = Field(default=None, description="Filter by assignee")
    
    has_clarifications: Optional[bool] = Field(default=None, description="Filter workflows with pending clarifications")
    
    created_from: Optional[str] = Field(default=None, description="Filter by creation date (from)")
    created_to: Optional[str] = Field(default=None, description="Filter by creation date (to)")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "workflow_type": "hiring_process",
                "status": "running",
                "has_clarifications": True,
                "created_from": "2025-01-20"
            }
        }
    }


class ClarificationResponse(BaseCreate):
    """Model for responding to workflow clarifications"""
    clarification_id: str = Field(description="Clarification identifier")
    response: Any = Field(description="Response to the clarification")
    notes: Optional[str] = Field(default=None, description="Additional notes")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "clarification_id": "approve_offer",
                "response": True,
                "notes": "Approved with standard benefits package"
            }
        }
    }
