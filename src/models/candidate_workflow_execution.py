from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModelWithSoftDelete
from datetime import datetime
from typing import Optional

class CandidateWorkflowExecution(BaseModelWithSoftDelete):
    __tablename__ = "candidate_workflow_executions"
    
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False, index=True)
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False, index=True)
    workflow_step_detail_id = Column(UUID(as_uuid=True), ForeignKey("workflow_step_detail.id"), nullable=False, index=True)
    
    # Execution tracking
    execution_status = Column(String(50), nullable=False, default="pending", index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    current_step = Column(Boolean, default=False, nullable=False, index=True)
    step_metadata = Column(JSON, nullable=True)
    
    # Step configuration (copied from workflow_step_detail for efficiency)
    order_number = Column(Integer, nullable=False, index=True)  # Step sequence (1, 2, 3...)
    auto_start = Column(Boolean, nullable=False, default=False)  # Whether step auto-starts
    required_human_approval = Column(Boolean, nullable=False, default=False)  # Whether approval needed
    number_of_approvals_needed = Column(Integer, nullable=True)  # How many approvals required
    approvers = Column(JSON, default=list, nullable=False)  # Array of user IDs who can approve
    
    # Step information (copied from workflow_step for efficiency)
    step_name = Column(Text, nullable=False)  # Human-readable step name
    step_type = Column(Text, nullable=False)  # resume_analysis, interview, etc.
    step_description = Column(Text, nullable=True)  # Step description
    
    # Timing
    delay_in_seconds = Column(Integer, nullable=True)  # Delay before step execution
    
    # Relationships
    candidate = relationship("Candidate", back_populates="workflow_executions")
    job = relationship("Job", back_populates="workflow_executions")
    workflow_step_detail = relationship("WorkflowStepDetail", back_populates="executions")
    
    def __repr__(self):
        return f"<CandidateWorkflowExecution(id={self.id}, candidate_id={self.candidate_id}, job_id={self.job_id}, status={self.execution_status})>"
