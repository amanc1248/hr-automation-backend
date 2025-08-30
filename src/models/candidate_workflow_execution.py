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
    
    execution_status = Column(String(50), nullable=False, default="pending", index=True)
    started_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    completed_at = Column(DateTime, nullable=True)
    current_step = Column(Boolean, default=False, nullable=False, index=True)
    step_metadata = Column(JSON, nullable=True)
    
    # Relationships
    candidate = relationship("Candidate", back_populates="workflow_executions")
    job = relationship("Job", back_populates="workflow_executions")
    workflow_step_detail = relationship("WorkflowStepDetail", back_populates="executions")
    
    def __repr__(self):
        return f"<CandidateWorkflowExecution(id={self.id}, candidate_id={self.candidate_id}, job_id={self.job_id}, status={self.execution_status})>"
