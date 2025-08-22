from sqlalchemy import Column, String, Boolean, Text, ForeignKey, DateTime, Integer, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from .base import BaseModel, BaseModelWithSoftDelete

class Interview(BaseModel):
    """Interview model"""
    __tablename__ = "interviews"
    
    job_id = Column(UUID(as_uuid=True), ForeignKey("jobs.id"), nullable=False)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), nullable=False)
    application_id = Column(UUID(as_uuid=True), ForeignKey("applications.id"), nullable=False)
    
    # Interview details
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    interview_type = Column(String(50), nullable=False)  # phone, video, onsite, ai, technical
    round_number = Column(Integer, default=1, nullable=False)
    
    # Scheduling
    scheduled_at = Column(DateTime, nullable=True)
    duration_minutes = Column(Integer, default=60, nullable=False)
    timezone = Column(String(50), nullable=True)
    location = Column(String(500), nullable=True)  # Address or video link
    
    # Status and results
    status = Column(String(50), default="scheduled", nullable=False)
    # Statuses: scheduled, in_progress, completed, cancelled, no_show
    
    # Participants
    interviewer_ids = Column(JSONB, default=list, nullable=False)  # List of profile IDs
    
    # AI Interview specific
    ai_interview_config_id = Column(UUID(as_uuid=True), ForeignKey("ai_interview_configs.id"), nullable=True)
    voice_cloning_data = Column(JSONB, default=dict, nullable=False)
    ai_questions = Column(JSONB, default=list, nullable=False)
    ai_evaluation = Column(JSONB, default=dict, nullable=False)
    
    # Results and feedback
    score = Column(Numeric(5, 2), nullable=True)  # 0.00 to 100.00
    feedback = Column(Text, nullable=True)
    notes = Column(Text, nullable=True)
    recording_url = Column(String(500), nullable=True)
    transcript = Column(Text, nullable=True)
    
    # Evaluation criteria
    evaluation_criteria = Column(JSONB, default=list, nullable=False)
    evaluation_scores = Column(JSONB, default=dict, nullable=False)
    
    # Timeline
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Relationships
    job = relationship("Job", back_populates="interviews")
    candidate = relationship("Candidate", back_populates="interviews")
    application = relationship("Application", back_populates="interviews")
    ai_config = relationship("AIInterviewConfig", back_populates="interviews")

class AIInterviewConfig(BaseModel):
    """AI Interview configuration model"""
    __tablename__ = "ai_interview_configs"
    
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    
    # AI Configuration
    interview_type = Column(String(50), nullable=False)  # technical, behavioral, screening
    difficulty_level = Column(String(50), default="medium", nullable=False)  # easy, medium, hard
    duration_minutes = Column(Integer, default=30, nullable=False)
    
    # Question configuration
    question_categories = Column(JSONB, default=list, nullable=False)
    total_questions = Column(Integer, default=5, nullable=False)
    adaptive_questioning = Column(Boolean, default=True, nullable=False)
    
    # Voice and personality
    voice_model = Column(String(100), nullable=True)  # ElevenLabs voice ID
    personality_prompt = Column(Text, nullable=True)
    interviewer_name = Column(String(100), default="Alex", nullable=False)
    
    # Evaluation criteria
    evaluation_criteria = Column(JSONB, default=list, nullable=False)
    scoring_rubric = Column(JSONB, default=dict, nullable=False)
    
    # Settings
    allow_retries = Column(Boolean, default=False, nullable=False)
    time_limit_per_question = Column(Integer, nullable=True)  # seconds
    auto_advance = Column(Boolean, default=False, nullable=False)
    
    # Company specific
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    is_template = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    company = relationship("Company")
    interviews = relationship("Interview", back_populates="ai_config")
