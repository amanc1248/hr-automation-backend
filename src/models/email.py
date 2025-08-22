from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, BaseModelWithSoftDelete

class EmailAccount(BaseModel):
    """Email account configuration"""
    __tablename__ = "email_accounts"
    
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False)
    
    # Account details
    name = Column(String(255), nullable=False)
    email_address = Column(String(255), nullable=False)
    display_name = Column(String(255), nullable=True)
    
    # Provider configuration
    provider = Column(String(50), nullable=False)  # gmail, outlook, smtp
    provider_config = Column(JSONB, default=dict, nullable=False)
    
    # SMTP/IMAP settings (encrypted)
    smtp_host = Column(String(255), nullable=True)
    smtp_port = Column(Integer, nullable=True)
    smtp_username = Column(String(255), nullable=True)
    smtp_password_encrypted = Column(Text, nullable=True)
    
    imap_host = Column(String(255), nullable=True)
    imap_port = Column(Integer, nullable=True)
    imap_username = Column(String(255), nullable=True)
    imap_password_encrypted = Column(Text, nullable=True)
    
    # OAuth tokens (encrypted)
    oauth_tokens = Column(JSONB, default=dict, nullable=False)
    
    # Settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_default = Column(Boolean, default=False, nullable=False)
    auto_sync = Column(Boolean, default=True, nullable=False)
    
    # Usage tracking
    daily_send_limit = Column(Integer, default=500, nullable=False)
    daily_send_count = Column(Integer, default=0, nullable=False)
    last_sync_at = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship("Company", back_populates="email_accounts")
    sent_emails = relationship("EmailMonitoring", back_populates="email_account")

class EmailTemplate(BaseModel):
    """Email template model"""
    __tablename__ = "email_templates"
    
    # Template details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    category = Column(String(100), nullable=False)  # application_received, interview_invite, rejection, etc.
    
    # Template content
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=True)
    
    # Template variables
    variables = Column(JSONB, default=list, nullable=False)  # List of available variables
    
    # Company association (null = system template)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    
    # Template settings
    is_active = Column(Boolean, default=True, nullable=False)
    is_system_template = Column(Boolean, default=False, nullable=False)
    
    # Usage tracking
    usage_count = Column(Integer, default=0, nullable=False)
    last_used_at = Column(DateTime, nullable=True)
    
    # Relationships
    company = relationship("Company")
    sent_emails = relationship("EmailMonitoring", back_populates="email_template")

class EmailMonitoring(BaseModel):
    """Email monitoring and tracking"""
    __tablename__ = "email_monitoring"
    
    # Email details
    email_account_id = Column(UUID(as_uuid=True), ForeignKey("email_accounts.id"), nullable=False)
    email_template_id = Column(UUID(as_uuid=True), ForeignKey("email_templates.id"), nullable=True)
    
    # Recipients
    to_email = Column(String(255), nullable=False)
    to_name = Column(String(255), nullable=True)
    cc_emails = Column(JSONB, default=list, nullable=False)
    bcc_emails = Column(JSONB, default=list, nullable=False)
    
    # Email content
    subject = Column(String(500), nullable=False)
    body_html = Column(Text, nullable=True)
    body_text = Column(Text, nullable=True)
    
    # Context
    context_type = Column(String(50), nullable=True)  # application, interview, job_posting
    context_id = Column(UUID(as_uuid=True), nullable=True)  # ID of related object
    context_data = Column(JSONB, default=dict, nullable=False)
    
    # Sending status
    status = Column(String(50), default="pending", nullable=False)
    # Statuses: pending, sent, delivered, bounced, failed, opened, clicked
    
    # Provider details
    provider_message_id = Column(String(255), nullable=True)
    provider_response = Column(JSONB, default=dict, nullable=False)
    
    # Timing
    scheduled_at = Column(DateTime, nullable=True)
    sent_at = Column(DateTime, nullable=True)
    delivered_at = Column(DateTime, nullable=True)
    opened_at = Column(DateTime, nullable=True)
    clicked_at = Column(DateTime, nullable=True)
    bounced_at = Column(DateTime, nullable=True)
    
    # Tracking
    open_count = Column(Integer, default=0, nullable=False)
    click_count = Column(Integer, default=0, nullable=False)
    tracking_data = Column(JSONB, default=dict, nullable=False)
    
    # Error handling
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    
    # Relationships
    email_account = relationship("EmailAccount", back_populates="sent_emails")
    email_template = relationship("EmailTemplate", back_populates="sent_emails")
