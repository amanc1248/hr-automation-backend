"""
Approval schema definitions
"""
from pydantic import BaseModel, Field
from uuid import UUID
from typing import Optional, List
from datetime import datetime
from enum import Enum

class ApprovalDecision(str, Enum):
    approved = "approved"
    rejected = "rejected"

class ApprovalStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    completed = "completed"

class ApprovalSubmission(BaseModel):
    """Schema for submitting approval decision"""
    approval_request_id: UUID
    decision: ApprovalDecision
    comments: Optional[str] = None

class ApprovalSubmissionResponse(BaseModel):
    """Response after submitting approval"""
    success: bool
    message: str
    approval_id: UUID

class ApprovalRequestResponse(BaseModel):
    """Schema for approval request details"""
    id: UUID
    candidate_workflow_id: UUID
    workflow_step_detail_id: UUID
    required_approvals: int
    status: str
    requested_at: datetime
    responded_at: Optional[datetime] = None
    comments: Optional[str] = None
    
    # User permissions
    can_approve: bool = True  # Whether current user can approve this request
    
    # Workflow step information
    step_name: str
    step_description: str
    step_display_name: Optional[str] = None
    step_type: str
    
    # Candidate information
    candidate_name: str
    candidate_email: str
    
    # Job information
    job_title: str
    job_department: str
    
    class Config:
        from_attributes = True

class ApprovalRequestsList(BaseModel):
    """Schema for list of approval requests"""
    requests: List[ApprovalRequestResponse]
    total_count: int

class ApprovalStatsResponse(BaseModel):
    """Schema for approval statistics"""
    pending_count: int
    approved_count: int
    rejected_count: int
    total_count: int
