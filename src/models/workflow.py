from sqlalchemy import Column, String, Boolean, Text, ForeignKey, Integer, ARRAY
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, BaseModelWithSoftDelete

class WorkflowTemplate(BaseModelWithSoftDelete):
    """Workflow template model - defines reusable workflow processes"""
    __tablename__ = "workflow_template"
    
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Text, nullable=False)
    steps_execution_id = Column(ARRAY(UUID(as_uuid=True)), nullable=False, default=list)
    
    # Relationships
    candidate_workflows = relationship("CandidateWorkflow", back_populates="workflow_template")

class WorkflowStep(BaseModelWithSoftDelete):
    """Workflow step model - defines individual reusable steps"""
    __tablename__ = "workflow_step"
    
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    step_type = Column(Text, nullable=False)
    actions = Column(JSONB, nullable=False, default=list)
    
    # Relationships
    step_details = relationship("WorkflowStepDetail", back_populates="workflow_step")

class WorkflowStepDetail(BaseModelWithSoftDelete):
    """Workflow step detail model - configuration for steps in specific workflows"""
    __tablename__ = "workflow_step_detail"
    
    workflow_step_id = Column(UUID(as_uuid=True), ForeignKey("workflow_step.id"), nullable=False)
    delay_in_seconds = Column(Integer, nullable=True)
    auto_start = Column(Boolean, nullable=False, default=False)
    required_human_approval = Column(Boolean, nullable=False, default=False)
    number_of_approvals_needed = Column(Integer, nullable=True)
    status = Column(Text, nullable=False, default="awaiting")  # awaiting, finished, rejected
    order_number = Column(Integer, nullable=False)
    
    # Relationships
    workflow_step = relationship("WorkflowStep", back_populates="step_details")

class CandidateWorkflow(BaseModelWithSoftDelete):
    """Candidate workflow model - tracks workflow instances for specific candidates"""
    __tablename__ = "candidate_workflow"
    
    name = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    category = Column(Text, nullable=False)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    workflow_template_id = Column(UUID(as_uuid=True), ForeignKey("workflow_template.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    
    # Relationships
    job = relationship("Job", back_populates="candidate_workflows")
    workflow_template = relationship("WorkflowTemplate", back_populates="candidate_workflows")
    candidate = relationship("Candidate", back_populates="candidate_workflows")