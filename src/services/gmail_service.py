import json
import base64
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from urllib.parse import urlencode, parse_qs
import secrets
import httpx
from cryptography.fernet import Fernet

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from core.config import settings
from models.user import Profile

# Gmail OAuth scopes
GMAIL_SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send', 
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/cloud-platform'  # Required for Pub/Sub notifications
]

class GmailConfig:
    """Gmail configuration model"""
    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)

class GmailService:
    """Service for Gmail OAuth and API operations"""
    
    def __init__(self):
        self.client_id = settings.GOOGLE_CLIENT_ID
        self.client_secret = settings.GOOGLE_CLIENT_SECRET
        self.redirect_uri = settings.GOOGLE_REDIRECT_URI
        
        # Initialize encryption for tokens
        encryption_key = getattr(settings, 'ENCRYPTION_KEY', None)
        if not encryption_key:
            # Generate a key if not provided (for development)
            encryption_key = Fernet.generate_key()
            print(f"⚠️  Generated encryption key: {encryption_key.decode()}")
            print("⚠️  Add this to your .env file as ENCRYPTION_KEY")
        else:
            encryption_key = encryption_key.encode() if isinstance(encryption_key, str) else encryption_key
        
        self.cipher = Fernet(encryption_key)
    
    def _encrypt_token(self, token: str) -> str:
        """Encrypt a token for secure storage"""
        return self.cipher.encrypt(token.encode()).decode()
    
    def _decrypt_token(self, encrypted_token: str) -> str:
        """Decrypt a token for use"""
        return self.cipher.decrypt(encrypted_token.encode()).decode()
    
    async def generate_oauth_url(self, user_id: str, company_id: str) -> str:
        """Generate Gmail OAuth URL"""
        
        # Create state parameter with user info
        state_data = {
            'user_id': user_id,
            'company_id': company_id,
            'timestamp': datetime.utcnow().isoformat(),
            'nonce': secrets.token_urlsafe(16)
        }
        state = base64.urlsafe_b64encode(json.dumps(state_data).encode()).decode()
        
        # OAuth parameters
        params = {
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': ' '.join(GMAIL_SCOPES),
            'response_type': 'code',
            'access_type': 'offline',  # Get refresh token
            'prompt': 'consent',       # Force consent screen
            'state': state
        }
        
        oauth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"
        return oauth_url
    
    async def exchange_code_for_tokens(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access and refresh tokens"""
        
        token_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'code': code,
            'grant_type': 'authorization_code',
            'redirect_uri': self.redirect_uri
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://oauth2.googleapis.com/token',
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                raise Exception(f"Token exchange failed: {response.text}")
            
            tokens = response.json()
            
            # Calculate expiration time
            expires_in = tokens.get('expires_in', 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return {
                'access_token': tokens['access_token'],
                'refresh_token': tokens.get('refresh_token'),
                'expires_at': expires_at,
                'scope': tokens.get('scope', '').split()
            }
    
    async def get_user_info(self, access_token: str) -> Dict[str, Any]:
        """Get user's Gmail information"""
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                'https://www.googleapis.com/oauth2/v2/userinfo',
                headers={'Authorization': f'Bearer {access_token}'}
            )
            
            if response.status_code != 200:
                raise Exception(f"Failed to get user info: {response.text}")
            
            return response.json()
    
    async def test_gmail_connection(self, access_token: str) -> bool:
        """Test Gmail API connection"""
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    'https://gmail.googleapis.com/gmail/v1/users/me/profile',
                    headers={'Authorization': f'Bearer {access_token}'}
                )
                
                return response.status_code == 200
        except Exception:
            return False
    
    async def refresh_access_token(self, refresh_token: str) -> Dict[str, Any]:
        """Refresh expired access token"""
        
        token_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'refresh_token': refresh_token,
            'grant_type': 'refresh_token'
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                'https://oauth2.googleapis.com/token',
                data=token_data,
                headers={'Content-Type': 'application/x-www-form-urlencoded'}
            )
            
            if response.status_code != 200:
                raise Exception(f"Token refresh failed: {response.text}")
            
            tokens = response.json()
            
            # Calculate new expiration time
            expires_in = tokens.get('expires_in', 3600)
            expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            return {
                'access_token': tokens['access_token'],
                'expires_at': expires_at
            }
    
    async def save_gmail_config(
        self, 
        db: AsyncSession,
        user_id: str,
        company_id: str,
        gmail_address: str,
        display_name: str,
        tokens: Dict[str, Any]
    ) -> GmailConfig:
        """Save Gmail configuration to database"""
        
        # Encrypt tokens before storing
        encrypted_access_token = self._encrypt_token(tokens['access_token'])
        encrypted_refresh_token = self._encrypt_token(tokens['refresh_token']) if tokens.get('refresh_token') else None
        
        # Insert or update Gmail config
        from sqlalchemy import text
        
        insert_sql = """
        INSERT INTO gmail_configs (
            company_id, user_id, gmail_address, display_name,
            access_token, refresh_token, token_expires_at,
            granted_scopes, is_active
        ) VALUES (
            :company_id, :user_id, :gmail_address, :display_name,
            :access_token, :refresh_token, :token_expires_at,
            :granted_scopes, true
        )
        ON CONFLICT (company_id, gmail_address)
        DO UPDATE SET
            user_id = EXCLUDED.user_id,
            display_name = EXCLUDED.display_name,
            access_token = EXCLUDED.access_token,
            refresh_token = EXCLUDED.refresh_token,
            token_expires_at = EXCLUDED.token_expires_at,
            granted_scopes = EXCLUDED.granted_scopes,
            is_active = EXCLUDED.is_active,
            updated_at = NOW()
        RETURNING *;
        """
        
        result = await db.execute(text(insert_sql), {
            'company_id': company_id,
            'user_id': user_id,
            'gmail_address': gmail_address,
            'display_name': display_name,
            'access_token': encrypted_access_token,
            'refresh_token': encrypted_refresh_token,
            'token_expires_at': tokens['expires_at'],
            'granted_scopes': tokens.get('scope', [])
        })
        
        config_row = result.fetchone()
        await db.commit()
        
        return GmailConfig(**dict(config_row._mapping))
    
    async def get_company_gmail_configs(self, db: AsyncSession, company_id: str) -> List[GmailConfig]:
        """Get all Gmail configurations for a company"""
        
        from sqlalchemy import text
        
        result = await db.execute(
            text("SELECT * FROM gmail_configs WHERE company_id = :company_id AND is_active = true"),
            {'company_id': company_id}
        )
        
        configs = []
        for row in result.fetchall():
            config_dict = dict(row._mapping)
            # Don't decrypt tokens here for security
            config_dict['access_token'] = '[ENCRYPTED]'
            config_dict['refresh_token'] = '[ENCRYPTED]'
            configs.append(GmailConfig(**config_dict))
        
        return configs
    
    async def get_gmail_config_by_id(self, db: AsyncSession, config_id: str) -> Optional[GmailConfig]:
        """Get Gmail configuration by ID with decrypted tokens"""
        
        from sqlalchemy import text
        
        result = await db.execute(
            text("SELECT * FROM gmail_configs WHERE id = :config_id AND is_active = true"),
            {'config_id': config_id}
        )
        
        row = result.fetchone()
        if not row:
            return None
        
        config_dict = dict(row._mapping)
        
        # Decrypt tokens for use
        if config_dict['access_token']:
            config_dict['access_token'] = self._decrypt_token(config_dict['access_token'])
        if config_dict['refresh_token']:
            config_dict['refresh_token'] = self._decrypt_token(config_dict['refresh_token'])
        
        return GmailConfig(**config_dict)
    
    async def get_valid_access_token(self, gmail_config: GmailConfig) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        
        # Check if current token is still valid
        if hasattr(gmail_config, 'token_expires_at') and gmail_config.token_expires_at:
            from datetime import datetime
            if datetime.utcnow() < gmail_config.token_expires_at:
                return gmail_config.access_token
        
        # Token is expired or about to expire, refresh it
        if not hasattr(gmail_config, 'refresh_token') or not gmail_config.refresh_token:
            print(f"   ⚠️  No refresh token available for {gmail_config.gmail_address}")
            return None
        
        try:
            print(f"   🔄 Refreshing access token for {gmail_config.gmail_address}")
            new_tokens = await self.refresh_access_token(gmail_config.refresh_token)
            return new_tokens['access_token']
        except Exception as e:
            print(f"   ❌ Failed to refresh token: {e}")
            return None
    
    async def get_gmail_config_by_email(self, db: AsyncSession, email_address: str) -> Optional[GmailConfig]:
        """Get Gmail configuration by email address with decrypted tokens"""
        
        from sqlalchemy import text
        
        result = await db.execute(
            text("SELECT * FROM gmail_configs WHERE gmail_address = :email AND is_active = true"),
            {'email': email_address}
        )
        
        row = result.fetchone()
        if not row:
            return None
        
        config_dict = dict(row._mapping)
        
        # Decrypt tokens for use
        if config_dict['access_token']:
            config_dict['access_token'] = self._decrypt_token(config_dict['access_token'])
        if config_dict['refresh_token']:
            config_dict['refresh_token'] = self._decrypt_token(config_dict['refresh_token'])
        
        return GmailConfig(**config_dict)

# Global instance
gmail_service = GmailService()
