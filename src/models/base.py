"""
Base models and common types for HR Automation System.
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID
import uuid


class TimestampMixin(BaseModel):
    """Mixin for models with timestamp fields"""
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Creation timestamp")
    updated_at: Optional[datetime] = Field(default=None, description="Last update timestamp")


class BaseEntity(TimestampMixin):
    """Base model for database entities"""
    model_config = ConfigDict(
        from_attributes=True,
        validate_assignment=True,
        arbitrary_types_allowed=True,
        json_schema_extra={
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "created_at": "2025-01-20T00:00:00Z",
                "updated_at": "2025-01-20T00:00:00Z"
            }
        }
    )
    
    id: UUID = Field(default_factory=uuid.uuid4, description="Unique identifier")


class BaseCreate(BaseModel):
    """Base model for create operations"""
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True
    )


class BaseUpdate(BaseModel):
    """Base model for update operations"""
    model_config = ConfigDict(
        validate_assignment=True,
        arbitrary_types_allowed=True
    )


class PaginationParams(BaseModel):
    """Pagination parameters for list endpoints"""
    page: int = Field(default=1, ge=1, description="Page number (1-based)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        """Calculate offset for database queries"""
        return (self.page - 1) * self.page_size


class PaginatedResponse(BaseModel):
    """Generic paginated response"""
    items: list = Field(description="List of items")
    total: int = Field(description="Total number of items")
    page: int = Field(description="Current page number")
    page_size: int = Field(description="Items per page")
    total_pages: int = Field(description="Total number of pages")
    
    @classmethod
    def create(cls, items: list, total: int, page: int, page_size: int):
        """Create paginated response"""
        total_pages = (total + page_size - 1) // page_size
        return cls(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )


class APIResponse(BaseModel):
    """Standard API response wrapper"""
    success: bool = Field(description="Whether the operation was successful")
    message: str = Field(description="Human-readable message")
    data: Optional[Dict[str, Any]] = Field(default=None, description="Response data")
    errors: Optional[list] = Field(default=None, description="List of errors if any")
    
    @classmethod
    def success_response(cls, message: str, data: Optional[Dict[str, Any]] = None):
        """Create success response"""
        return cls(success=True, message=message, data=data)
    
    @classmethod
    def error_response(cls, message: str, errors: Optional[list] = None):
        """Create error response"""
        return cls(success=False, message=message, errors=errors or [])
