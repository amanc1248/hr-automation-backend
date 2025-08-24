import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import httpx
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from core.database import get_db
from services.gmail_service import gmail_service

logger = logging.getLogger(__name__)

class EmailPollingService:
    """Service for polling Gmail accounts for new emails"""
    
    def __init__(self):
        self.is_running = False
        self.polling_interval = 60  # Poll every 60 seconds
        self.polling_task = None
        
    async def start_polling(self):
        """Start the email polling service"""
        if self.is_running:
            logger.info("Email polling service is already running")
            return False
            
        self.is_running = True
        logger.info("🚀 Starting email polling service...")
        
        # Start polling in background
        self.polling_task = asyncio.create_task(self._poll_loop())
        return True
        
    async def stop_polling(self):
        """Stop the email polling service"""
        if not self.is_running:
            return False
            
        self.is_running = False
        if self.polling_task:
            self.polling_task.cancel()
            try:
                await self.polling_task
            except asyncio.CancelledError:
                pass
        logger.info("🛑 Email polling service stopped")
        return True
        
    def get_status(self):
        """Get the current polling service status"""
        return {
            "is_running": self.is_running,
            "started_at": None,  # TODO: Add started_at timestamp tracking
            "last_poll": None,   # TODO: Add last_poll timestamp tracking
            "poll_count": 0,     # TODO: Add poll count tracking
            "error_count": 0     # TODO: Add error count tracking
        }
        
    async def _poll_loop(self):
        """Main polling loop"""
        while self.is_running:
            try:
                await self._poll_all_accounts()
                await asyncio.sleep(self.polling_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in polling loop: {e}")
                await asyncio.sleep(10)  # Wait 10 seconds before retrying
                
    async def _poll_all_accounts(self):
        """Poll all configured Gmail accounts"""
        try:
            # Get database session
            async for db in get_db():
                # Get all active Gmail configurations
                result = await db.execute(
                    text("SELECT * FROM gmail_configs WHERE is_active = true")
                )
                configs = result.fetchall()
                
                if not configs:
                    logger.debug("No active Gmail configurations found")
                    return
                
                logger.info(f"📧 Polling {len(configs)} Gmail account(s)...")
                
                for config in configs:
                    config_dict = dict(config._mapping)
                    await self._poll_single_account(db, config_dict)
                    
        except Exception as e:
            logger.error(f"Error polling Gmail accounts: {e}")
            
    async def _poll_single_account(self, db: AsyncSession, config: Dict[str, Any]):
        """Poll a single Gmail account for new emails"""
        try:
            email_address = config['gmail_address']
            logger.debug(f"📬 Polling {email_address}...")
            
            # Get fresh access token
            access_token = await self._get_valid_access_token(config)
            if not access_token:
                logger.warning(f"⚠️  No valid access token for {email_address}")
                return
                
            # Get recent emails (last 24 hours)
            emails = await self._fetch_recent_emails(email_address, access_token)
            
            if emails:
                logger.info(f"📨 Found {len(emails)} new emails in {email_address}")
                await self._process_emails(db, emails, email_address)
            else:
                logger.debug(f"📭 No new emails in {email_address}")
                
        except Exception as e:
            logger.error(f"Error polling {config.get('gmail_address', 'unknown')}: {e}")
            
    async def _get_valid_access_token(self, config: Dict[str, Any]) -> Optional[str]:
        """Get a valid access token, refreshing if necessary"""
        try:
            # Decrypt tokens
            access_token = gmail_service._decrypt_token(config['access_token'])
            refresh_token = gmail_service._decrypt_token(config['refresh_token'])
            
            # Check if current token is still valid
            if config.get('token_expires_at'):
                try:
                    # Handle both string and datetime objects
                    if isinstance(config['token_expires_at'], str):
                        expires_at = datetime.fromisoformat(config['token_expires_at'])
                    else:
                        expires_at = config['token_expires_at']
                        
                    if datetime.utcnow() < expires_at:
                        return access_token
                except (ValueError, TypeError) as e:
                    logger.warning(f"Invalid token expiration format: {e}")
                    # Continue to refresh token
                    
            # Token is expired or about to expire, refresh it
            if refresh_token:
                logger.info(f"🔄 Refreshing access token for {config['gmail_address']}")
                new_tokens = await gmail_service.refresh_access_token(refresh_token)
                
                # Update the database with new tokens
                await self._update_tokens_in_db(config['id'], new_tokens)
                
                return new_tokens['access_token']
            else:
                logger.warning(f"⚠️  No refresh token available for {config['gmail_address']}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting valid access token: {e}")
            return None
            
    async def _fetch_recent_emails(self, email_address: str, access_token: str) -> List[Dict[str, Any]]:
        """Fetch recent emails from Gmail"""
        try:
            # Calculate time range (last 24 hours)
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            
            # Format for Gmail API query
            after_date = yesterday.strftime('%Y/%m/%d')
            
            # Gmail API query for recent emails
            query = f'after:{after_date}'
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/messages',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    },
                    params={
                        'q': query,
                        'maxResults': 50,  # Limit results
                        'includeSpamTrash': False
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get('messages', [])
                    
                    # Get full email details for each message
                    emails = []
                    for msg in messages[:10]:  # Process only first 10 to avoid rate limits
                        email_detail = await self._fetch_email_detail(email_address, access_token, msg['id'])
                        if email_detail:
                            emails.append(email_detail)
                            
                    return emails
                else:
                    logger.error(f"Failed to fetch emails: {response.status_code} - {response.text}")
                    return []
                    
        except Exception as e:
            logger.error(f"Error fetching emails: {e}")
            return []
            
    async def _fetch_email_detail(self, email_address: str, access_token: str, message_id: str) -> Optional[Dict[str, Any]]:
        """Fetch detailed information for a specific email"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/messages/{message_id}',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    },
                    params={
                        'format': 'full',  # Get full email content
                        'metadataHeaders': ['Subject', 'From', 'Date', 'To']
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    logger.warning(f"Failed to fetch email detail: {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Error fetching email detail: {e}")
            return None
            
    async def _process_emails(self, db: AsyncSession, emails: List[Dict[str, Any]], email_address: str):
        """Process fetched emails and start workflows if needed"""
        try:
            for email in emails:
                await self._process_single_email(db, email, email_address)
                
        except Exception as e:
            logger.error(f"Error processing emails: {e}")
            
    async def _process_single_email(self, db: AsyncSession, email: Dict[str, Any], email_address: str):
        """Process a single email and determine if it should start a workflow"""
        try:
            # Extract email metadata
            headers = email.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            
            logger.info(f"📧 Processing email: {subject} from {from_email}")
            
            # Check if this looks like a job application
            if self._is_job_application(subject, from_email):
                logger.info(f"🎯 Job application detected: {subject}")
                await self._start_workflow_for_email(db, email, email_address)
            else:
                logger.debug(f"📝 Regular email (not a job application): {subject}")
                
        except Exception as e:
            logger.error(f"Error processing single email: {e}")
            
    def _is_job_application(self, subject: str, from_email: str) -> bool:
        """Determine if an email is likely a job application"""
        subject_lower = subject.lower()
        from_lower = from_email.lower()
        
        # Keywords that suggest job applications
        job_keywords = [
            'application', 'resume', 'cv', 'job', 'position', 'role',
            'candidate', 'apply', 'hiring', 'career', 'employment'
        ]
        
        # Check subject for job-related keywords
        for keyword in job_keywords:
            if keyword in subject_lower:
                return True
                
        # Check if it's from a known job board or career site
        job_domains = [
            'indeed.com', 'linkedin.com', 'glassdoor.com', 'monster.com',
            'careerbuilder.com', 'ziprecruiter.com', 'simplyhired.com'
        ]
        
        for domain in job_domains:
            if domain in from_lower:
                return True
                
        return False
        
    async def _start_workflow_for_email(self, db: AsyncSession, email: Dict[str, Any], email_address: str):
        """Start a workflow for a job application email"""
        try:
            logger.info(f"🚀 Starting workflow for job application email")
            
            # TODO: Implement workflow logic here
            # 1. Parse email content and attachments
            # 2. Extract candidate information
            # 3. Create candidate record
            # 4. Start the appropriate workflow
            
            logger.info(f"✅ Workflow started for email from {email_address}")
            
        except Exception as e:
            logger.error(f"Error starting workflow: {e}")
            
    async def _update_tokens_in_db(self, config_id: str, new_tokens: Dict[str, Any]):
        """Update tokens in the database after refresh"""
        try:
            async for db in get_db():
                # Encrypt new tokens
                encrypted_access = gmail_service._encrypt_token(new_tokens['access_token'])
                encrypted_refresh = gmail_service._encrypt_token(new_tokens['refresh_token'])
                
                # Update database
                await db.execute(
                    text("""
                        UPDATE gmail_configs 
                        SET access_token = :access_token, 
                            refresh_token = :refresh_token,
                            token_expires_at = :expires_at,
                            updated_at = NOW()
                        WHERE id = :config_id
                    """),
                    {
                        'access_token': encrypted_access,
                        'refresh_token': encrypted_refresh,
                        'expires_at': new_tokens['expires_at'].isoformat(),
                        'config_id': config_id
                    }
                )
                await db.commit()
                logger.info(f"✅ Tokens updated in database for config {config_id}")
                
        except Exception as e:
            logger.error(f"Error updating tokens in database: {e}")

# Global instance
email_polling_service = EmailPollingService()
