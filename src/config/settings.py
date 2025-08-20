"""
Application configuration management using Pydantic Settings.
Handles environment variables and application settings.
"""

from pydantic_settings import BaseSettings
from pydantic import Field
from typing import List
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""
    
    # Supabase Configuration
    SUPABASE_URL: str = Field(default="https://placeholder.supabase.co", description="Supabase project URL")
    SUPABASE_ANON_KEY: str = Field(default="placeholder_anon_key", description="Supabase anonymous key")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(default="placeholder_service_role_key", description="Supabase service role key")
    
    # Portia Configuration
    PORTIA_API_KEY: str = Field(default="", description="Portia AI API key")
    
    # LLM Configuration
    OPENAI_API_KEY: str = Field(default="placeholder_openai_key", description="OpenAI API key")
    ANTHROPIC_API_KEY: str = Field(default="", description="Anthropic API key")
    GOOGLE_API_KEY: str = Field(default="", description="Google GenAI API key")
    
    # LinkedIn Configuration
    LINKEDIN_CLIENT_ID: str = Field(default="", description="LinkedIn API Client ID")
    LINKEDIN_CLIENT_SECRET: str = Field(default="", description="LinkedIn API Client Secret")
    LINKEDIN_ACCESS_TOKEN: str = Field(default="", description="LinkedIn API Access Token")
    
    # FastAPI Configuration
    SECRET_KEY: str = Field(default="development_secret_key_change_in_production", description="Secret key for JWT tokens")
    ALGORITHM: str = Field(default="HS256", description="JWT algorithm")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(default=30, description="JWT token expiration")
    
    # External API Keys
    LINKEDIN_CLIENT_ID: str = Field(default="", description="LinkedIn OAuth client ID")
    LINKEDIN_CLIENT_SECRET: str = Field(default="", description="LinkedIn OAuth client secret")
    GMAIL_CLIENT_ID: str = Field(default="", description="Gmail API client ID")
    GMAIL_CLIENT_SECRET: str = Field(default="", description="Gmail API client secret")
    
    # Application Settings
    ENVIRONMENT: str = Field(default="development", description="Environment (development/production)")
    DEBUG: bool = Field(default=True, description="Debug mode")
    LOG_LEVEL: str = Field(default="INFO", description="Logging level")
    CORS_ORIGINS: List[str] = Field(default=["http://localhost:3000"], description="CORS origins")
    
    # Voice Cloning Service
    ELEVENLABS_API_KEY: str = Field(default="", description="ElevenLabs API key for voice cloning")
    
    # Calendar Integration
    GOOGLE_CALENDAR_CREDENTIALS_FILE: str = Field(default="", description="Google Calendar credentials file path")
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        
    def get_llm_provider(self) -> str:
        """Determine which LLM provider to use based on available API keys"""
        if self.OPENAI_API_KEY:
            return "openai"
        elif self.ANTHROPIC_API_KEY:
            return "anthropic"
        elif self.GOOGLE_API_KEY:
            return "google"
        else:
            raise ValueError("No LLM API key provided. Please set OPENAI_API_KEY, ANTHROPIC_API_KEY, or GOOGLE_API_KEY")
    
    def get_llm_api_key(self) -> str:
        """Get the API key for the selected LLM provider"""
        provider = self.get_llm_provider()
        if provider == "openai":
            return self.OPENAI_API_KEY
        elif provider == "anthropic":
            return self.ANTHROPIC_API_KEY
        elif provider == "google":
            return self.GOOGLE_API_KEY
        else:
            raise ValueError(f"Unknown LLM provider: {provider}")


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings"""
    return Settings()
