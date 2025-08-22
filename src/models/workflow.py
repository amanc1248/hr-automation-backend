from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, BaseModelWithSoftDelete

class WorkflowTemplate(BaseModel):
    """Workflow template model"""
    __tablename__ = "workflow_templates"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)  # hiring, onboarding, performance_review
    
    # Template configuration
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    version = Column(String(20), default="1.0", nullable=False)
    
    # Company association
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Workflow settings
    auto_start = Column(Boolean, default=False, nullable=False)
    parallel_execution = Column(Boolean, default=False, nullable=False)
    timeout_hours = Column(Integer, nullable=True)
    
    # Metadata
    tags = Column(JSONB, default=list, nullable=False)
    settings = Column(JSONB, default=dict, nullable=False)
    
    # Relationships
    company = relationship("Company", back_populates="workflow_templates")
    steps = relationship("WorkflowStep", back_populates="template", cascade="all, delete-orphan", order_by="WorkflowStep.order")
    executions = relationship("WorkflowExecution", back_populates="template")
    jobs = relationship("Job", back_populates="workflow_template")

class WorkflowStep(BaseModel):
    """Workflow step model"""
    __tablename__ = "workflow_steps"
    
    template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=False)
    
    # Step details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    step_type = Column(String(50), nullable=False)
    # Types: manual_review, ai_screening, interview_scheduling, email_send, approval, decision
    
    # Ordering and flow
    order = Column(Integer, nullable=False)
    parent_step_id = Column(UUID(as_uuid=True), ForeignKey("workflow_steps.id"), nullable=True)
    
    # Step configuration
    config = Column(JSONB, default=dict, nullable=False)
    conditions = Column(JSONB, default=dict, nullable=False)  # Conditions to execute this step
    
    # Timing
    auto_execute = Column(Boolean, default=False, nullable=False)
    timeout_hours = Column(Integer, nullable=True)
    
    # Assignment
    assigned_role_id = Column(UUID(as_uuid=True), ForeignKey("user_roles.id"), nullable=True)
    assigned_user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False)
    is_required = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    template = relationship("WorkflowTemplate", back_populates="steps")
    parent_step = relationship("WorkflowStep", remote_side="WorkflowStep.id")
    child_steps = relationship("WorkflowStep", back_populates="parent_step")
    assigned_role = relationship("UserRole")
    assigned_user = relationship("Profile")
    executions = relationship("WorkflowStepExecution", back_populates="step")

class WorkflowExecution(BaseModel):
    """Workflow execution instance"""
    __tablename__ = "workflow_executions"
    
    template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_templates.id"), nullable=False)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=True)
    
    # Execution details
    status = Column(String(50), default="pending", nullable=False)
    # Statuses: pending, running, paused, completed, failed, cancelled
    
    current_step_id = Column(UUID(as_uuid=True), ForeignKey("workflow_steps.id"), nullable=True)
    
    # Execution context
    context_data = Column(JSONB, default=dict, nullable=False)  # Data passed between steps
    execution_log = Column(JSONB, default=list, nullable=False)  # Execution history
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    paused_at = Column(DateTime, nullable=True)
    
    # Ownership
    initiated_by = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False)
    
    # Results
    final_result = Column(String(50), nullable=True)  # approved, rejected, on_hold
    result_data = Column(JSONB, default=dict, nullable=False)
    
    # Relationships
    template = relationship("WorkflowTemplate", back_populates="executions")
    # One-to-one relationship: one execution can have one application
    application = relationship("Application", foreign_keys=[application_id], uselist=False)
    current_step = relationship("WorkflowStep")
    initiated_by_user = relationship("Profile", back_populates="workflow_executions")
    step_executions = relationship("WorkflowStepExecution", back_populates="workflow_execution", cascade="all, delete-orphan")
    approvals = relationship("WorkflowApproval", back_populates="workflow_execution")

class WorkflowStepExecution(BaseModel):
    """Individual step execution"""
    __tablename__ = "workflow_step_executions"
    
    workflow_execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    step_id = Column(UUID(as_uuid=True), ForeignKey("workflow_steps.id"), nullable=False)
    
    # Execution details
    status = Column(String(50), default="pending", nullable=False)
    # Statuses: pending, running, completed, failed, skipped, waiting_approval
    
    # Assignment
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    
    # Timing
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    due_at = Column(DateTime, nullable=True)
    
    # Results
    result = Column(String(50), nullable=True)  # approved, rejected, completed, failed
    result_data = Column(JSONB, default=dict, nullable=False)
    notes = Column(Text, nullable=True)
    
    # Execution log
    execution_log = Column(JSONB, default=list, nullable=False)
    error_message = Column(Text, nullable=True)
    
    # Relationships
    workflow_execution = relationship("WorkflowExecution", back_populates="step_executions")
    step = relationship("WorkflowStep", back_populates="executions")
    assigned_user = relationship("Profile")

class WorkflowApproval(BaseModel):
    """Workflow approval model"""
    __tablename__ = "workflow_approvals"
    
    workflow_execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_executions.id"), nullable=False)
    step_execution_id = Column(UUID(as_uuid=True), ForeignKey("workflow_step_executions.id"), nullable=True)
    
    # Approval details
    approval_type = Column(String(50), nullable=False)  # step_approval, final_approval, exception_approval
    required_role_id = Column(UUID(as_uuid=True), ForeignKey("user_roles.id"), nullable=True)
    
    # Status
    status = Column(String(50), default="pending", nullable=False)
    # Statuses: pending, approved, rejected, escalated
    
    # Approver
    approver_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    approved_at = Column(DateTime, nullable=True)
    
    # Approval data
    comments = Column(Text, nullable=True)
    approval_data = Column(JSONB, default=dict, nullable=False)
    
    # Escalation
    escalated_to = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=True)
    escalated_at = Column(DateTime, nullable=True)
    escalation_reason = Column(Text, nullable=True)
    
    # Relationships
    workflow_execution = relationship("WorkflowExecution", back_populates="approvals")
    step_execution = relationship("WorkflowStepExecution")
    required_role = relationship("UserRole")
    approver = relationship("Profile", foreign_keys=[approver_id], back_populates="workflow_approvals")
    escalated_user = relationship("Profile", foreign_keys=[escalated_to])
