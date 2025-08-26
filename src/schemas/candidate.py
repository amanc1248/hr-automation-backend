from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# Resume schema
class ResumeFileResponse(BaseModel):
    id: str
    filename: str
    originalName: str
    fileSize: int
    fileType: str
    downloadUrl: str
    uploadedAt: str

# Communication schema
class CommunicationResponse(BaseModel):
    id: str
    type: str  # 'email', 'note', 'system'
    subject: Optional[str] = None
    content: str
    sender: str
    recipient: str
    timestamp: str
    status: str  # 'sent', 'delivered', 'read', 'failed'

# Workflow step schema
class WorkflowStepResponse(BaseModel):
    id: str
    name: str
    type: str
    status: str  # 'pending', 'in_progress', 'completed', 'failed', 'waiting_approval'
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    notes: Optional[str] = None

# Main candidate response
class CandidateResponse(BaseModel):
    id: str
    name: str
    email: str
    phone: Optional[str] = None
    location: Optional[str] = None
    jobId: str
    jobTitle: str
    applicationDate: str
    currentStep: str
    workflowProgress: List[WorkflowStepResponse]
    resume: ResumeFileResponse
    communicationHistory: List[CommunicationResponse]
    status: str  # 'active', 'pending', 'completed', 'rejected'
    notes: List[str]
    companyId: str
    createdAt: str
    updatedAt: str

# List response with pagination
class CandidatesListResponse(BaseModel):
    candidates: List[CandidateResponse]
    total: int
    page: int
    limit: int
    totalPages: int

# Create candidate request
class CandidateCreateRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=255)

# Update candidate request
class CandidateUpdateRequest(BaseModel):
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(None, max_length=20)
    location: Optional[str] = Field(None, max_length=255)
    status: Optional[str] = None
    notes: Optional[List[str]] = None
