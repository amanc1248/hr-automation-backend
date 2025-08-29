from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from .base import BaseModel
from datetime import datetime

class GmailWatch(BaseModel):
    """Gmail watch configuration for webhook notifications"""
    __tablename__ = "gmail_watches"
    
    # User association
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    user_email = Column(String(255), nullable=False, index=True)
    
    # Gmail watch details
    channel_id = Column(String(255), nullable=False, unique=True, index=True)
    resource_id = Column(String(255), nullable=False)
    history_id = Column(String(255), nullable=False)
    
    # Watch management
    expiration = Column(DateTime, nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    last_notification = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("Profile", back_populates="gmail_watches")

class EmailProcessingLog(BaseModel):
    """Log of email processing attempts via webhooks"""
    __tablename__ = "email_processing_logs"
    
    # Email identification
    user_id = Column(UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False, index=True)
    email_id = Column(String(255), nullable=False, index=True)
    thread_id = Column(String(255), nullable=True, index=True)
    
    # Processing details
    processed_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    status = Column(String(50), nullable=False, index=True)  # success, failed, retry
    workflow_triggered = Column(String(100), nullable=True)  # resume_analysis, interview_scheduling, etc.
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    last_retry_at = Column(DateTime, nullable=True)
    
    # Email metadata for debugging
    subject = Column(String(500), nullable=True)
    from_email = Column(String(255), nullable=True)
    
    # Relationships
    user = relationship("Profile", back_populates="email_processing_logs")
