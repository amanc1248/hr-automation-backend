from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, DateTime, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid

Base = declarative_base()

class TimestampMixin:
    """Mixin for created_at and updated_at timestamps"""
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

class UUIDMixin:
    """Mixin for UUID primary key"""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, nullable=False)

class SoftDeleteMixin:
    """Mixin for soft delete functionality"""
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

class BaseModel(Base, UUIDMixin, TimestampMixin):
    """Base model with UUID, timestamps"""
    __abstract__ = True

class BaseModelWithSoftDelete(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Base model with UUID, timestamps, and soft delete"""
    __abstract__ = True
