"""
Workflow Approval System Models
"""
from sqlalchemy import Column, String, Text, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import BaseModel, UUIDMixin, Base
import uuid

# ENUM types for approval system
approval_status_enum = ENUM(
    'pending', 'approved', 'rejected', 'completed',
    name='approval_status',
    create_type=False
)

approval_decision_enum = ENUM(
    'approved', 'rejected',
    name='approval_decision', 
    create_type=False
)

class WorkflowApprovalRequest(BaseModel):
    """
    Represents an approval request sent to a specific approver for a workflow step.
    Each approver gets their own approval request record.
    """
    __tablename__ = "workflow_approval_requests"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Foreign Keys
    candidate_workflow_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("candidate_workflow.id", ondelete="CASCADE"), 
        nullable=False
    )
    workflow_step_detail_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("workflow_step_detail.id", ondelete="CASCADE"), 
        nullable=False
    )
    approver_user_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("profiles.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Approval Details
    required_approvals = Column(Integer, nullable=False)
    
    # Status Tracking
    status = Column(approval_status_enum, default='pending')
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationships
    candidate_workflow = relationship("CandidateWorkflow", back_populates="approval_requests")
    workflow_step_detail = relationship("WorkflowStepDetail", back_populates="approval_requests")
    approver = relationship("Profile", foreign_keys=[approver_user_id])
    approvals = relationship("WorkflowApproval", back_populates="approval_request", cascade="all, delete-orphan")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            'candidate_workflow_id', 
            'workflow_step_detail_id', 
            'approver_user_id',
            name='unique_approval_request_per_approver'
        ),
    )

    def __repr__(self):
        return f"<WorkflowApprovalRequest(id={self.id}, approver={self.approver_user_id}, status={self.status})>"


class WorkflowApproval(Base, UUIDMixin):
    """
    Represents an individual approver's decision/response to an approval request.
    """
    __tablename__ = "workflow_approvals"

    # Foreign Keys
    approval_request_id = Column(
        UUID(as_uuid=True), 
        ForeignKey("workflow_approval_requests.id", ondelete="CASCADE"), 
        nullable=False
    )
    
    # Approval Decision
    decision = Column(approval_decision_enum, nullable=False)
    comments = Column(Text, nullable=True)
    responded_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    approval_request = relationship("WorkflowApprovalRequest", back_populates="approvals")
    
    def __repr__(self):
        return f"<WorkflowApproval(id={self.id}, decision={self.decision}, request={self.approval_request_id})>"


# Relationships are now defined statically in the workflow models
# No need for dynamic configuration
