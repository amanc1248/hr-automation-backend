"""
Job-related Pydantic schemas
"""
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from decimal import Decimal
from uuid import UUID

class JobBase(BaseModel):
    """Base job schema with common fields"""
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    requirements: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    job_type: str = Field(..., pattern="^(full-time|part-time|contract|internship)$")
    experience_level: Optional[str] = Field(None, pattern="^(entry|mid|senior|executive)$")
    remote_policy: Optional[str] = Field(None, pattern="^(remote|hybrid|onsite)$")
    salary_min: Optional[Decimal] = Field(None, ge=0)
    salary_max: Optional[Decimal] = Field(None, ge=0)
    salary_currency: Optional[str] = Field("USD", max_length=3)
    workflow_template_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_featured: Optional[bool] = False

class JobCreate(JobBase):
    """Schema for creating a new job"""
    status: Optional[str] = Field("draft", pattern="^(draft|active|paused|closed)$")

class JobUpdate(BaseModel):
    """Schema for updating an existing job"""
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = Field(None, min_length=1)
    requirements: Optional[str] = None
    department: Optional[str] = Field(None, max_length=100)
    location: Optional[str] = Field(None, max_length=255)
    job_type: Optional[str] = Field(None, pattern="^(full-time|part-time|contract|internship)$")
    experience_level: Optional[str] = Field(None, pattern="^(entry|mid|senior|executive)$")
    remote_policy: Optional[str] = Field(None, pattern="^(remote|hybrid|onsite)$")
    salary_min: Optional[Decimal] = Field(None, ge=0)
    salary_max: Optional[Decimal] = Field(None, ge=0)
    salary_currency: Optional[str] = Field(None, max_length=3)
    status: Optional[str] = Field(None, pattern="^(draft|active|paused|closed)$")
    workflow_template_id: Optional[UUID] = None
    assigned_to: Optional[UUID] = None
    posted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    is_featured: Optional[bool] = None

class JobResponse(JobBase):
    """Response schema for jobs"""
    id: UUID
    status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class JobListResponse(BaseModel):
    """Response schema for job listings with pagination"""
    jobs: List[JobResponse]
    total: int
    skip: int
    limit: int
