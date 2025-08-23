"""
Workflow-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class WorkflowStepResponse(BaseModel):
    """Response schema for workflow steps"""
    id: UUID
    name: str
    description: Optional[str] = None
    step_type: str  # automated, manual, approval
    actions: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkflowStepCreate(BaseModel):
    """Schema for creating workflow steps"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    step_type: str = Field(..., pattern="^(automated|manual|approval)$")
    actions: List[Dict[str, Any]] = Field(default_factory=list)

class WorkflowTemplateResponse(BaseModel):
    """Response schema for workflow templates"""
    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    steps_execution_id: List[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkflowStepDetailPopulated(BaseModel):
    """Populated workflow step detail with workflow step info"""
    id: UUID
    workflow_step_id: UUID
    delay_in_seconds: Optional[int] = None
    auto_start: bool = False
    required_human_approval: bool = False
    number_of_approvals_needed: Optional[int] = None
    status: str = "awaiting"
    order_number: int
    created_at: datetime
    updated_at: datetime
    
    # Populated workflow step info
    workflow_step: WorkflowStepResponse

    class Config:
        from_attributes = True

class WorkflowTemplatePopulated(BaseModel):
    """Populated workflow template with step details"""
    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    steps_execution_id: List[UUID] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime
    
    # Populated step details
    step_details: List[WorkflowStepDetailPopulated] = Field(default_factory=list)

    class Config:
        from_attributes = True

class WorkflowTemplateCreate(BaseModel):
    """Schema for creating workflow templates"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    steps_execution_id: List[UUID] = Field(default_factory=list)

class WorkflowStepForTemplate(BaseModel):
    """Schema for workflow steps when creating templates"""
    workflow_step_id: UUID  # Reference to existing workflow_step
    delay_in_seconds: Optional[int] = Field(None, ge=0)
    auto_start: bool = False
    required_human_approval: bool = False
    number_of_approvals_needed: Optional[int] = Field(None, ge=1)
    order_number: int = Field(..., ge=1)

class WorkflowTemplateCreateWithSteps(BaseModel):
    """Schema for creating workflow templates with step details"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    steps: List[WorkflowStepForTemplate] = Field(default_factory=list)

class WorkflowStepDetailResponse(BaseModel):
    """Response schema for workflow step details"""
    id: UUID
    workflow_step_id: UUID
    delay_in_seconds: Optional[int] = None
    auto_start: bool = False
    required_human_approval: bool = False
    number_of_approvals_needed: Optional[int] = None
    status: str = "awaiting"  # awaiting, finished, rejected
    order_number: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class WorkflowStepDetailCreate(BaseModel):
    """Schema for creating workflow step details"""
    workflow_step_id: UUID
    delay_in_seconds: Optional[int] = Field(None, ge=0)
    auto_start: bool = False
    required_human_approval: bool = False
    number_of_approvals_needed: Optional[int] = Field(None, ge=1)
    order_number: int = Field(..., ge=1)

class CandidateWorkflowResponse(BaseModel):
    """Response schema for candidate workflows"""
    id: UUID
    name: str
    description: Optional[str] = None
    category: str
    job_id: UUID
    workflow_template_id: UUID
    candidate_id: UUID
    current_step_detail_id: Optional[UUID] = None
    started_at: datetime
    completed_at: Optional[datetime] = None
    execution_log: List[Dict[str, Any]] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CandidateWorkflowCreate(BaseModel):
    """Schema for creating candidate workflows"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    category: str = Field(..., min_length=1, max_length=100)
    job_id: UUID
    workflow_template_id: UUID
    candidate_id: UUID
