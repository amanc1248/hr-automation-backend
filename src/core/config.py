from pydantic_settings import BaseSettings
from pydantic import Field
from typing import Optional
import os

class Settings(BaseSettings):
    # Database Configuration
    DATABASE_URL: str = Field(..., description="Complete PostgreSQL connection URL")
    
    # Security
    SECRET_KEY: str = Field(default="your-secret-key-change-in-production", description="JWT secret key")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="Access token expiration")
    REFRESH_TOKEN_EXPIRE_DAYS: int = Field(default=7, description="Refresh token expiration")
    
    # Application Settings
    DEBUG: bool = Field(default=True, description="Debug mode")
    ENVIRONMENT: str = Field(default="development", description="Environment")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    
    # Google OAuth Configuration
    GOOGLE_CLIENT_ID: Optional[str] = Field(default=None, description="Google OAuth client ID")
    GOOGLE_CLIENT_SECRET: Optional[str] = Field(default=None, description="Google OAuth client secret")
    GOOGLE_REDIRECT_URI: Optional[str] = Field(default=None, description="Google OAuth redirect URI")
    
    # Encryption
    ENCRYPTION_KEY: Optional[str] = Field(default=None, description="Encryption key for sensitive data")
    
    # API Keys (optional for now)
    GOOGLE_API_KEY: Optional[str] = Field(default=None, description="Google API key")
    ELEVENLABS_API_KEY: Optional[str] = Field(default=None, description="ElevenLabs API key")
    
    @property
    def async_database_url(self) -> str:
        """Convert DATABASE_URL to async format"""
        if self.DATABASE_URL.startswith("postgresql://"):
            return self.DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)
        elif self.DATABASE_URL.startswith("postgres://"):
            return self.DATABASE_URL.replace("postgres://", "postgresql+asyncpg://", 1)
        return self.DATABASE_URL
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "allow"  # Allow extra fields from .env

def validate_settings():
    """Validate critical settings"""
    settings = Settings()
    
    if not settings.DATABASE_URL:
        raise ValueError("DATABASE_URL is required")
    
    if not settings.SECRET_KEY or settings.SECRET_KEY == "your-secret-key-change-in-production":
        print("⚠️  WARNING: Using default SECRET_KEY. Change this in production!")
    
    print("✅ Settings validation passed")
    return settings

# Global settings instance
settings = Settings()
