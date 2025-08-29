"""
Gmail Webhook Configuration and Validation
"""

import os
from typing import Optional
from pydantic import BaseModel, field_validator

class WebhookConfig(BaseModel):
    """Configuration for Gmail webhook functionality"""
    
    # Gmail webhook settings
    gmail_webhook_url: Optional[str] = None
    google_cloud_project_id: Optional[str] = None
    gmail_webhook_secret: Optional[str] = None
    
    # Frontend URL for OAuth redirects
    frontend_url: Optional[str] = None
    
    @field_validator('gmail_webhook_url')
    @classmethod
    def validate_webhook_url(cls, v):
        """Validate webhook URL format"""
        if v and not v.startswith(('http://', 'https://')):
            raise ValueError('Webhook URL must start with http:// or https://')
        return v
    
    @field_validator('google_cloud_project_id')
    @classmethod
    def validate_project_id(cls, v):
        """Validate Google Cloud project ID format"""
        if v and not v.replace('-', '').replace('_', '').isalnum():
            raise ValueError('Google Cloud project ID must contain only letters, numbers, hyphens, and underscores')
        return v
    
    @field_validator('gmail_webhook_secret')
    @classmethod
    def validate_webhook_secret(cls, v):
        """Validate webhook secret length"""
        if v and len(v) < 16:
            raise ValueError('Webhook secret must be at least 16 characters long')
        return v
    
    model_config = {
        "env_file": ".env",
        "env_prefix": "",  # No prefix for environment variables
    }

# Create global config instance
def create_webhook_config() -> WebhookConfig:
    """Create webhook config from environment variables"""
    return WebhookConfig(
        gmail_webhook_url=os.getenv('GMAIL_WEBHOOK_URL'),
        google_cloud_project_id=os.getenv('GOOGLE_CLOUD_PROJECT_ID'),
        gmail_webhook_secret=os.getenv('GMAIL_WEBHOOK_SECRET'),
        frontend_url=os.getenv('FRONTEND_URL')
    )

webhook_config = create_webhook_config()

def get_webhook_config() -> WebhookConfig:
    """Get webhook configuration instance"""
    return webhook_config

def validate_webhook_setup() -> bool:
    """Validate that all required webhook configuration is present"""
    config = get_webhook_config()
    
    required_vars = [
        'gmail_webhook_url',
        'google_cloud_project_id', 
        'gmail_webhook_secret'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(config, var):
            missing_vars.append(var.upper())
    
    if missing_vars:
        print(f"❌ Missing required webhook environment variables: {', '.join(missing_vars)}")
        print("   Please set these in your Railway environment variables")
        return False
    
    print("✅ All required webhook environment variables are configured")
    return True
