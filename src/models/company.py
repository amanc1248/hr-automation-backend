"""
Company models for HR Automation System.
"""

from pydantic import Field, HttpUrl
from typing import Optional, Dict, Any

from .base import BaseEntity, BaseCreate, BaseUpdate


class Company(BaseEntity):
    """Company model"""
    name: str = Field(min_length=1, max_length=200, description="Company name")
    domain: Optional[str] = Field(default=None, max_length=100, description="Company domain")
    website: Optional[HttpUrl] = Field(default=None, description="Company website URL")
    logo_url: Optional[HttpUrl] = Field(default=None, description="Company logo URL")
    description: Optional[str] = Field(default=None, max_length=1000, description="Company description")
    industry: Optional[str] = Field(default=None, max_length=100, description="Industry sector")
    size: Optional[str] = Field(default=None, description="Company size (e.g., '1-10', '11-50', '51-200')")
    location: Optional[str] = Field(default=None, max_length=200, description="Company headquarters location")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Company-specific settings")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "id": "660e8400-e29b-41d4-a716-446655440001",
                "name": "TechCorp Inc.",
                "domain": "techcorp.com",
                "website": "https://www.techcorp.com",
                "logo_url": "https://www.techcorp.com/logo.png",
                "description": "Leading technology company specializing in AI solutions",
                "industry": "Technology",
                "size": "51-200",
                "location": "San Francisco, CA",
                "settings": {
                    "auto_screening": True,
                    "ai_interviews": True,
                    "notification_preferences": {
                        "email": True,
                        "slack": False
                    }
                },
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z"
            }
        }
    }


class CompanyCreate(BaseCreate):
    """Model for creating a new company"""
    name: str = Field(min_length=1, max_length=200, description="Company name")
    domain: Optional[str] = Field(default=None, max_length=100, description="Company domain")
    website: Optional[HttpUrl] = Field(default=None, description="Company website URL")
    logo_url: Optional[HttpUrl] = Field(default=None, description="Company logo URL")
    description: Optional[str] = Field(default=None, max_length=1000, description="Company description")
    industry: Optional[str] = Field(default=None, max_length=100, description="Industry sector")
    size: Optional[str] = Field(default=None, description="Company size")
    location: Optional[str] = Field(default=None, max_length=200, description="Company headquarters location")
    settings: Dict[str, Any] = Field(default_factory=dict, description="Company-specific settings")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "TechCorp Inc.",
                "domain": "techcorp.com",
                "website": "https://www.techcorp.com",
                "description": "Leading technology company specializing in AI solutions",
                "industry": "Technology",
                "size": "51-200",
                "location": "San Francisco, CA"
            }
        }
    }


class CompanyUpdate(BaseUpdate):
    """Model for updating company information"""
    name: Optional[str] = Field(default=None, min_length=1, max_length=200, description="Company name")
    domain: Optional[str] = Field(default=None, max_length=100, description="Company domain")
    website: Optional[HttpUrl] = Field(default=None, description="Company website URL")
    logo_url: Optional[HttpUrl] = Field(default=None, description="Company logo URL")
    description: Optional[str] = Field(default=None, max_length=1000, description="Company description")
    industry: Optional[str] = Field(default=None, max_length=100, description="Industry sector")
    size: Optional[str] = Field(default=None, description="Company size")
    location: Optional[str] = Field(default=None, max_length=200, description="Company headquarters location")
    settings: Optional[Dict[str, Any]] = Field(default=None, description="Company-specific settings")
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "name": "TechCorp Inc. Updated",
                "description": "Updated company description",
                "settings": {
                    "auto_screening": False,
                    "ai_interviews": True
                }
            }
        }
    }


class CompanySettings(BaseCreate):
    """Model for company settings"""
    auto_screening: bool = Field(default=True, description="Enable automatic resume screening")
    ai_interviews: bool = Field(default=False, description="Enable AI-powered interviews")
    voice_cloning_enabled: bool = Field(default=False, description="Enable voice cloning for AI interviews")
    auto_job_posting: bool = Field(default=False, description="Enable automatic job posting to platforms")
    notification_preferences: Dict[str, bool] = Field(
        default_factory=lambda: {"email": True, "slack": False, "teams": False},
        description="Notification preferences"
    )
    interview_scheduling: Dict[str, Any] = Field(
        default_factory=lambda: {
            "auto_schedule": False,
            "buffer_time_minutes": 15,
            "working_hours": {"start": "09:00", "end": "17:00"},
            "time_zone": "UTC"
        },
        description="Interview scheduling settings"
    )
    screening_criteria: Dict[str, Any] = Field(
        default_factory=lambda: {
            "minimum_experience_years": 0,
            "required_skills": [],
            "preferred_skills": [],
            "education_requirements": [],
            "location_preferences": []
        },
        description="Default screening criteria"
    )
    
    model_config = {
        "json_schema_extra": {
            "example": {
                "auto_screening": True,
                "ai_interviews": True,
                "voice_cloning_enabled": False,
                "auto_job_posting": True,
                "notification_preferences": {
                    "email": True,
                    "slack": True,
                    "teams": False
                },
                "interview_scheduling": {
                    "auto_schedule": True,
                    "buffer_time_minutes": 30,
                    "working_hours": {"start": "09:00", "end": "18:00"},
                    "time_zone": "America/New_York"
                }
            }
        }
    }
