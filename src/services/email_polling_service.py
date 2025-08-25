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
        self.polling_interval = 86400  # Poll every 60 seconds
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
        """Fetch recent unread emails from Gmail Primary inbox only (excludes Promotions, Social, Updates tabs)"""
        try:
            # Calculate time range (last 24 hours)
            now = datetime.utcnow()
            yesterday = now - timedelta(days=1)
            
            # Format for Gmail API query (YYYY/MM/DD format)
            after_date = yesterday.strftime('%Y/%m/%d')
            
            # Gmail API query for unread emails in Primary inbox only from last 24 hours
            # Use label-based filtering to exclude category tabs
            query = f'is:unread in:inbox -category:promotions -category:social -category:updates -category:forums after:{after_date}'
            
            logger.info(f"🔍 Polling {email_address} with query: '{query}'")
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/messages',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    },
                    params={
                        'q': query,  # Use the proper query with category exclusions
                        'maxResults': 50,  # Limit results
                        'includeSpamTrash': False
                    },
                    timeout=30.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    messages = data.get('messages', [])
                    
                    logger.info(f"📊 Found {len(messages)} unread emails in Primary inbox for {email_address}")
                    
                    # Get full email details for each message
                    emails = []
                    for i, msg in enumerate(messages[:10]):  # Process only first 10 to avoid rate limits
                        logger.info(f"📥 Fetching email {i+1}/{min(len(messages), 10)} (ID: {msg['id']})")
                        email_detail = await self._fetch_email_detail(email_address, access_token, msg['id'])
                        if email_detail:
                            emails.append(email_detail)
                    
                    logger.info(f"✅ Successfully fetched {len(emails)} email details")
                    return emails
                else:
                    logger.error(f"❌ Failed to fetch emails: {response.status_code} - {response.text}")
                    logger.error(f"   📧 Email: {email_address}")
                    logger.error(f"   🔍 Query: {query}")
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
            
            logger.info(f"📧 Processing email:")
            logger.info(f"   📋 Subject: {subject}")
            logger.info(f"   👤 From: {from_email}")
            logger.info(f"   📅 Date: {date}")
            
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
        
        # First, filter out promotional/marketing emails
        promotional_keywords = [
            'discount', 'sale', 'offer', 'deal', 'promo', 'coupon', 'save', 
            'limited time', 'free shipping', 'newsletter', 'unsubscribe',
            'marketing', 'notification', 'alert', 'update', 'new feature',
            'product', 'service', 'buy now', 'shop', 'store', 'purchase',
            'trip', 'travel', 'hotel', 'vacation', 'booking', 'reservation',
            'conference', 'event', 'webinar', 'seminar', 'workshop',
            'startup', 'showcase', 'demo', 'launch', 'announcement'
        ]
        
        promotional_domains = [
            'tripadvisor.com', 'gucci.com', 'lovable.dev', 'yourstory.com',
            'mobbin.com', 'coursiv.co', 'vervecoffee.com', 'sanimabank.com',
            'notifications', 'no-reply', 'noreply', 'marketing', 'promo'
        ]
        
        # Filter out promotional emails
        for keyword in promotional_keywords:
            if keyword in subject_lower:
                logger.debug(f"📝 Filtered out promotional email with keyword '{keyword}': {subject}")
                return False
                
        for domain in promotional_domains:
            if domain in from_lower:
                logger.debug(f"📝 Filtered out promotional email from domain '{domain}': {from_email}")
                return False
        
        # Keywords that suggest job applications
        job_keywords = [
            'application', 'resume', 'cv', 'job', 'position', 'role',
            'candidate', 'apply', 'hiring', 'career', 'employment',
            'interview', 'opportunity', 'opening'
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
            
            # 1. Extract email metadata
            headers = email.get('payload', {}).get('headers', [])
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
            from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
            date = next((h['value'] for h in headers if h['name'] == 'Date'), 'Unknown')
            
            logger.info(f"📋 Processing job application:")
            logger.info(f"   📧 Subject: {subject}")
            logger.info(f"   👤 From: {from_email}")
            logger.info(f"   📅 Date: {date}")
            
            # 2. Extract job information from subject
            job_title = self._extract_job_title_from_subject(subject)
            logger.info(f"   💼 Extracted job title: {job_title}")
            
            # 3. Parse candidate information from email
            candidate_info = self._parse_candidate_info_from_email(from_email, email)
            logger.info(f"   👥 Candidate info: {candidate_info}")
            
            # 4. Find existing job by short ID from email subject (preferred) or title (fallback)
            job = await self._find_existing_job(db, subject)
            if job:
                logger.info(f"   🎯 Job found: {job['id']} - {job['title']} (Short ID: {job['short_id']})")
            else:
                logger.warning(f"   ⚠️ No existing job found for subject: {subject}")
                logger.info(f"   💡 Make sure the job has a valid short ID in brackets [JOBXXX] or exists with title '{job_title}'")
                return
            
            # 5. Get company_id from the job
            company_id = await self._get_company_id_from_job(db, job['id'])
            if not company_id:
                logger.warning(f"   ⚠️ Could not determine company_id for job: {job['id']}")
                return
            
            # 6. Find or create candidate with company_id
            candidate = await self._find_or_create_candidate(db, candidate_info, company_id)
            if candidate:
                logger.info(f"   👤 Candidate found/created: {candidate['id']} - {candidate['email']}")
            else:
                logger.warning(f"   ⚠️ Could not find/create candidate for: {candidate_info['email']}")
                return
            
            # 7. Create application record
            application = await self._create_application(db, job['id'], candidate['id'], email)
            logger.info(f"   📝 Application created: {application['id']}")
            
            # 8. Commit candidate and application creation first
            await db.commit()
            logger.info(f"   💾 Committed candidate and application to database")
            
            # 9. Find workflow_template_id using job_id
            workflow_template_id = await self._get_workflow_template_id_from_job(db, job['id'])
            if not workflow_template_id:
                logger.warning(f"   ⚠️ No workflow template found for job: {job['title']}")
                logger.info(f"   💡 Workflow processing stopped - candidate and application were saved successfully")
                return
            
            logger.info(f"   🔄 Found workflow template ID: {workflow_template_id}")
            
            # 10. Check if candidate_workflow exists
            existing_workflow = await self._find_existing_candidate_workflow(db, job['id'], candidate['id'], workflow_template_id)
            if existing_workflow:
                logger.info(f"   ✅ Found existing candidate workflow: {existing_workflow['id']}")
                logger.info(f"   📋 Current step ID: {existing_workflow.get('current_step_detail_id', 'Not set')}")
                
                # Execute workflow progression (current step and potentially next steps)
                await self._execute_workflow_progression(db, existing_workflow, candidate, job, email)
                    
            else:
                logger.info(f"   🆕 Creating new candidate workflow...")
                # 11. Create new candidate_workflow
                new_workflow = await self._create_candidate_workflow(db, job['id'], candidate['id'], workflow_template_id, email)
                if new_workflow:
                    logger.info(f"   ✅ Created new candidate workflow: {new_workflow['id']}")
                    logger.info(f"   📋 Starting with step ID: {new_workflow.get('current_step_detail_id', 'Not set')}")
                    
                    # Execute workflow progression starting from first step
                    await self._execute_workflow_progression(db, new_workflow, candidate, job, email)
                else:
                    logger.warning(f"   ⚠️ Failed to create candidate workflow")
                    logger.info(f"   💡 Workflow processing stopped - candidate and application were saved successfully")
            
        except Exception as e:
            logger.error(f"Error starting workflow: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
    
    def _extract_job_title_from_subject(self, subject: str) -> str:
        """Extract job title from email subject"""
        import re
        
        # Common patterns for job application subjects
        patterns = [
            r"applying for (.+?) (?:role|position|job)",
            r"application for (.+?) (?:role|position|job)",
            r"(.+?) (?:role|position|job) application",
            r"applying for (.+)",
            r"application for (.+)"
        ]
        
        subject_lower = subject.lower()
        
        for pattern in patterns:
            match = re.search(pattern, subject_lower, re.IGNORECASE)
            if match:
                job_title = match.group(1).strip()
                # Clean up the job title
                job_title = re.sub(r'\s+', ' ', job_title)  # Remove extra spaces
                job_title = job_title.title()  # Proper case
                return job_title
        
        # Fallback: return the whole subject if no pattern matches
        return subject
    
    def _parse_candidate_info_from_email(self, from_email: str, email: Dict[str, Any]) -> Dict[str, Any]:
        """Parse candidate information from email"""
        import re
        
        # Extract email address
        email_match = re.search(r'<(.+?)>', from_email)
        candidate_email = email_match.group(1) if email_match else from_email
        
        # Extract name (everything before < or the whole string if no <)
        name_part = from_email.split('<')[0].strip()
        if not name_part:
            name_part = candidate_email.split('@')[0]
        
        # Try to split name into first/last
        name_parts = name_part.strip('"').split()
        first_name = name_parts[0] if name_parts else "Unknown"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        return {
            "email": candidate_email,
            "first_name": first_name,
            "last_name": last_name,
            "source": "email",
            "source_details": {
                "original_from": from_email,
                "email_id": email.get('id'),
                "received_at": datetime.utcnow().isoformat()
            }
        }
    
    async def _find_existing_job(self, db: AsyncSession, email_subject: str) -> Optional[Dict[str, Any]]:
        """Find existing job by extracting short ID from email subject (e.g., [JOB3VV])"""
        try:
            from sqlalchemy import select
            from models.job import Job
            import re
            
            # Extract job short ID from subject using regex pattern [JOBXXX]
            job_id_pattern = r'\[([A-Z]{3}\w{3})\]'  # Matches [JOB123], [JOBXXX], etc.
            match = re.search(job_id_pattern, email_subject)
            
            if match:
                job_short_id = match.group(1)  # Extract the ID (e.g., "JOB3VV")
                logger.info(f"   🔍 Extracted job short ID from subject: {job_short_id}")
                
                # Find job by short_id (exact match)
                result = await db.execute(
                    select(Job).where(
                        Job.short_id == job_short_id,
                        Job.status.in_(["active", "draft"])
                    ).limit(1)
                )
                existing_job = result.scalar_one_or_none()
                
                if existing_job:
                    logger.info(f"   ✅ Found existing job: {existing_job.title} (ID: {existing_job.short_id})")
                    return {
                        "id": existing_job.id,
                        "title": existing_job.title,
                        "short_id": existing_job.short_id,
                        "status": existing_job.status,
                        "workflow_template_id": existing_job.workflow_template_id,
                        "department": getattr(existing_job, 'department', None)
                    }
                else:
                    logger.warning(f"   ❌ No job found with short ID: {job_short_id}")
                    return None
            else:
                # Fallback: if no short ID found, try title-based matching (legacy support)
                logger.info(f"   ⚠️ No job short ID found in subject, trying title-based matching...")
                job_title = self._extract_job_title_from_subject(email_subject)
                
                result = await db.execute(
                    select(Job).where(
                        Job.title.ilike(f"%{job_title}%"),
                        Job.status.in_(["active", "draft"])
                    ).limit(1)
                )
                existing_job = result.scalar_one_or_none()
                
                if existing_job:
                    logger.info(f"   ✅ Found job by title fallback: {existing_job.title} (ID: {existing_job.short_id})")
                    return {
                        "id": existing_job.id,
                        "title": existing_job.title,
                        "short_id": existing_job.short_id,
                        "status": existing_job.status,
                        "workflow_template_id": existing_job.workflow_template_id,
                        "department": getattr(existing_job, 'department', None)
                    }
                else:
                    # Log available jobs for debugging
                    all_jobs_result = await db.execute(
                        select(Job.title, Job.short_id).where(Job.status.in_(["active", "draft"]))
                    )
                    available_jobs = [(row[0], row[1]) for row in all_jobs_result.fetchall()]
                    logger.warning(f"   ❌ No job found for subject: '{email_subject}'")
                    logger.info(f"   📋 Available jobs: {available_jobs}")
                    return None
            
        except Exception as e:
            logger.error(f"Error finding job: {e}")
            return None
    
    async def _get_company_id_from_job(self, db: AsyncSession, job_id: str) -> Optional[str]:
        """Get company_id from job"""
        try:
            from sqlalchemy import select
            from models.job import Job
            
            result = await db.execute(
                select(Job.company_id).where(Job.id == job_id)
            )
            company_id = result.scalar_one_or_none()
            return str(company_id) if company_id else None
            
        except Exception as e:
            logger.error(f"Error getting company_id from job: {e}")
            return None
    
    async def _get_workflow_template_id_from_job(self, db: AsyncSession, job_id: str) -> Optional[str]:
        """Get workflow_template_id from job"""
        try:
            from sqlalchemy import select
            from models.job import Job
            
            result = await db.execute(
                select(Job.workflow_template_id).where(Job.id == job_id)
            )
            workflow_template_id = result.scalar_one_or_none()
            return str(workflow_template_id) if workflow_template_id else None
            
        except Exception as e:
            logger.error(f"Error getting workflow_template_id from job: {e}")
            return None
    
    async def _find_existing_candidate_workflow(self, db: AsyncSession, job_id: str, candidate_id: str, workflow_template_id: str) -> Optional[Dict[str, Any]]:
        """Find existing candidate workflow using job_id, candidate_id, and workflow_template_id"""
        try:
            from sqlalchemy import select
            from models.workflow import CandidateWorkflow
            
            result = await db.execute(
                select(CandidateWorkflow).where(
                    CandidateWorkflow.job_id == job_id,
                    CandidateWorkflow.candidate_id == candidate_id,
                    CandidateWorkflow.workflow_template_id == workflow_template_id,
                    CandidateWorkflow.is_deleted == False
                )
            )
            existing_workflow = result.scalar_one_or_none()
            
            if existing_workflow:
                return {
                    "id": existing_workflow.id,
                    "name": existing_workflow.name,
                    "current_step_detail_id": existing_workflow.current_step_detail_id,
                    "workflow_template_id": existing_workflow.workflow_template_id,
                    "started_at": existing_workflow.started_at,
                    "status": "existing"
                }
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error finding existing candidate workflow: {e}")
            return None
    
    async def _create_candidate_workflow(self, db: AsyncSession, job_id: str, candidate_id: str, workflow_template_id: str, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create new candidate workflow"""
        try:
            from sqlalchemy import select
            from models.workflow import CandidateWorkflow, WorkflowStepDetail, WorkflowTemplate
            from models.job import Job
            
            # Get job details for workflow name
            job_result = await db.execute(
                select(Job.title).where(Job.id == job_id)
            )
            job_title = job_result.scalar_one_or_none() or "Unknown Job"
            
            # Get the workflow template to access steps_execution_id
            template_result = await db.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_template_id)
            )
            template = template_result.scalar_one_or_none()
            
            first_step = None
            if template and template.steps_execution_id:
                # Get the first step from the template's steps_execution_id array
                # Find the step detail with order_number == 1 from the template's steps
                first_step_result = await db.execute(
                    select(WorkflowStepDetail).where(
                        WorkflowStepDetail.id.in_(template.steps_execution_id),
                        WorkflowStepDetail.order_number == 1,
                        WorkflowStepDetail.is_deleted == False
                    ).limit(1)
                )
                first_step = first_step_result.scalar_one_or_none()
            
            # Create workflow instance
            workflow_instance = CandidateWorkflow(
                name=f"Hiring workflow for {job_title}",
                description=f"Automated workflow started from email application",
                category="hiring",
                job_id=job_id,
                workflow_template_id=workflow_template_id,
                candidate_id=candidate_id,
                current_step_detail_id=first_step.id if first_step else None,
                execution_log=[{
                    "event": "workflow_started",
                    "timestamp": datetime.utcnow().isoformat(),
                    "trigger": "email_application",
                    "email_id": email.get('id')
                }]
            )
            
            db.add(workflow_instance)
            await db.flush()
            await db.commit()
            
            return {
                "id": workflow_instance.id,
                "name": workflow_instance.name,
                "current_step_detail_id": first_step.id if first_step else None,
                "workflow_template_id": workflow_template_id,
                "started_at": workflow_instance.started_at,
                "status": "new"
            }
            
        except Exception as e:
            logger.error(f"Error creating candidate workflow: {e}")
            await db.rollback()
            return None
    
    async def _find_or_create_candidate(self, db: AsyncSession, candidate_info: Dict[str, Any], company_id: str) -> Optional[Dict[str, Any]]:
        """Find existing candidate or create a new one"""
        try:
            from sqlalchemy import select
            from models.candidate import Candidate
            
            # Try to find existing candidate by email and company
            result = await db.execute(
                select(Candidate).where(
                    Candidate.email == candidate_info["email"],
                    Candidate.company_id == company_id,
                    Candidate.is_deleted == False
                )
            )
            existing_candidate = result.scalar_one_or_none()
            
            if existing_candidate:
                logger.info(f"   ✅ Found existing candidate: {existing_candidate.email}")
                return {
                    "id": existing_candidate.id,
                    "email": existing_candidate.email,
                    "first_name": existing_candidate.first_name,
                    "last_name": existing_candidate.last_name
                }
            
            # Create new candidate
            logger.info(f"   🆕 Creating new candidate: {candidate_info['email']}")
            new_candidate = Candidate(
                first_name=candidate_info["first_name"],
                last_name=candidate_info["last_name"],
                email=candidate_info["email"],
                company_id=company_id,
                source=candidate_info["source"],
                source_details=candidate_info["source_details"],
                status="new"
            )
            
            db.add(new_candidate)
            await db.flush()  # Get the ID without committing
            
            return {
                "id": new_candidate.id,
                "email": new_candidate.email,
                "first_name": new_candidate.first_name,
                "last_name": new_candidate.last_name
            }
            
        except Exception as e:
            logger.error(f"Error finding/creating candidate: {e}")
            return None
    
    async def _create_application(self, db: AsyncSession, job_id: str, candidate_id: str, email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create an application record (or return existing one)"""
        try:
            from sqlalchemy import select
            from models.candidate import Application
            
            # Check if application already exists for this job_id + candidate_id combination
            result = await db.execute(
                select(Application).where(
                    Application.job_id == job_id,
                    Application.candidate_id == candidate_id
                )
            )
            existing_application = result.scalar_one_or_none()
            
            if existing_application:
                logger.info(f"   ✅ Application already exists for this job/candidate combination")
                return {
                    "id": existing_application.id,
                    "status": existing_application.status,
                    "applied_at": existing_application.applied_at
                }
            
            # Create new application
            logger.info(f"   🆕 Creating new application for job/candidate combination")
            new_application = Application(
                job_id=job_id,
                candidate_id=candidate_id,
                status="applied",
                application_data={
                    "email_id": email.get('id'),
                    "applied_via": "email",
                    "application_source": "email_polling"
                },
                applied_at=datetime.utcnow(),
                source="email"
            )
            
            db.add(new_application)
            await db.flush()
            
            return {
                "id": new_application.id,
                "status": new_application.status,
                "applied_at": new_application.applied_at
            }
            
        except Exception as e:
            logger.error(f"Error creating application: {e}")
            return None

    async def _execute_workflow_progression(self, db: AsyncSession, workflow: Dict[str, Any], candidate: Dict[str, Any], job: Dict[str, Any], email: Dict[str, Any]):
        """Execute workflow progression - current step and continue to next steps if approved"""
        try:
            logger.info(f"   🚀 Starting workflow progression...")
            
            # Maximum steps to prevent infinite loops
            max_steps = 10
            steps_executed = 0
            current_workflow = workflow
            
            while steps_executed < max_steps:
                steps_executed += 1
                
                # Get current step details
                current_step_detail_id = current_workflow.get('current_step_detail_id')
                if not current_step_detail_id:
                    logger.info(f"   ✅ Workflow completed - no more steps to execute")
                    break
                
                logger.info(f"   📋 Executing step {steps_executed}: {current_step_detail_id}")
                
                # Check if this step requires human approval
                approval_status = await self._check_approval_requirements(db, current_step_detail_id, current_workflow['id'], candidate, job)
                
                if approval_status == "awaiting_approval":
                    logger.info(f"   ⏸️ Step requires approval - workflow paused")
                    logger.info(f"   📧 Approval requests have been sent to approvers")
                    break
                elif approval_status == "rejected":
                    logger.info(f"   ❌ Step was rejected by approvers - workflow terminated")
                    await self._mark_workflow_rejected(db, current_workflow['id'], "Step rejected by approvers")
                    break
                elif approval_status == "approved":
                    logger.info(f"   ✅ Step approved by approvers - proceeding with execution")
                
                # Only use AI verification for the first step (steps_executed == 0)
                if steps_executed == 1:
                    # Use AI to verify if this step should execute based on email content
                    should_execute_step = await self._ai_verify_step_execution(db, current_step_detail_id, email, candidate, job)
                    
                    if not should_execute_step:
                        logger.info(f"   🤖 AI determined this step should not execute based on email content")
                        logger.info(f"   ⏭️ Skipping step execution and finding appropriate step")
                        break
                    else:
                        # AI approved current step execution
                        step_result = await self._execute_workflow_step(db, current_workflow, candidate, job, email)
                else:
                    # For subsequent steps, execute normally without AI verification
                    step_result = await self._execute_workflow_step(db, current_workflow, candidate, job, email)
                
                if not step_result:
                    logger.warning(f"   ⚠️ Step execution failed - stopping workflow progression")
                    break
                
                step_status = step_result.get('status', 'unknown')
                logger.info(f"   🎯 Step result: {step_status}")
                
                # Update execution log
                await self._update_workflow_execution_log(db, current_workflow['id'], step_result, current_step_detail_id)
                
                # Check if workflow should continue
                if step_status == 'approved':
                    logger.info(f"   ✅ Step approved - checking for next step...")
                    
                    # Get next step
                    next_step_detail_id = await self._get_next_step_detail_id(db, current_workflow['workflow_template_id'], current_step_detail_id)
                    
                    if next_step_detail_id:
                        # Check if next step should auto-start (only for steps after the first one)
                        should_continue = True
                        if steps_executed > 1:  # For 2nd step onwards, check auto_start
                            should_auto_start = await self._should_step_auto_start(db, next_step_detail_id)
                            if not should_auto_start:
                                logger.info(f"   ⏸️ Next step requires manual trigger (auto_start=false): {next_step_detail_id}")
                                should_continue = False
                        
                        # Check if next step requires human approval (regardless of auto_start)
                        next_step_approval_status = await self._check_step_approval_requirements(db, next_step_detail_id, current_workflow['id'], candidate, job)
                        
                        if next_step_approval_status == "approval_required":
                            logger.info(f"   ⏸️ Next step requires human approval: {next_step_detail_id}")
                            should_continue = False
                        
                        # Update to next step
                        logger.info(f"   ➡️ Moving to next step: {next_step_detail_id}")
                        await self._update_candidate_workflow_current_step(db, current_workflow['id'], next_step_detail_id)
                        
                        if not should_continue:
                            if next_step_approval_status == "approval_required":
                                logger.info(f"   📧 Approval requests have been sent to approvers")
                                logger.info(f"   📋 Workflow paused for approvals")
                            else:
                                logger.info(f"   📋 Workflow paused at step: {next_step_detail_id}")
                                logger.info(f"   💡 Step will execute when triggered manually or by specific event")
                            break
                        
                        # Update current workflow data for next iteration
                        current_workflow['current_step_detail_id'] = next_step_detail_id
                        # Ensure workflow_template_id is available for next iteration
                        if 'workflow_template_id' not in current_workflow:
                            current_workflow['workflow_template_id'] = workflow.get('workflow_template_id')
                        
                    else:
                        logger.info(f"   🎉 Workflow completed successfully - no more steps")
                        await self._mark_workflow_completed(db, current_workflow['id'])
                        break
                        
                elif step_status == 'rejected':
                    logger.info(f"   ❌ Step rejected - workflow terminated")
                    await self._mark_workflow_rejected(db, current_workflow['id'], step_result.get('data', 'Step rejected'))
                    break
                    
                else:
                    logger.info(f"   ⏸️ Step status '{step_status}' - workflow paused (manual intervention may be required)")
                    break
            
            if steps_executed >= max_steps:
                logger.warning(f"   ⚠️ Workflow progression stopped - maximum steps ({max_steps}) reached")
            
            logger.info(f"   📊 Workflow progression completed: {steps_executed} steps executed")
            
        except Exception as e:
            logger.error(f"Error in workflow progression: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")

    async def _execute_workflow_step(self, db: AsyncSession, workflow: Dict[str, Any], candidate: Dict[str, Any], job: Dict[str, Any], email: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute the current workflow step using Portia"""
        try:
            from sqlalchemy import select
            from models.workflow import WorkflowStepDetail, WorkflowStep
            
            current_step_detail_id = workflow.get('current_step_detail_id')
            if not current_step_detail_id:
                logger.warning("   ⚠️ No current step detail ID found in workflow")
                return None
            
            logger.info(f"   🔍 Executing workflow step detail: {current_step_detail_id}")
            
            # Get the WorkflowStepDetail and related WorkflowStep
            step_detail_result = await db.execute(
                select(WorkflowStepDetail).where(
                    WorkflowStepDetail.id == current_step_detail_id,
                    WorkflowStepDetail.is_deleted == False
                )
            )
            step_detail = step_detail_result.scalar_one_or_none()
            
            if not step_detail:
                logger.error(f"   ❌ WorkflowStepDetail not found: {current_step_detail_id}")
                return None
            
            # Get the WorkflowStep to access the description
            step_result = await db.execute(
                select(WorkflowStep).where(
                    WorkflowStep.id == step_detail.workflow_step_id,
                    WorkflowStep.is_deleted == False
                )
            )
            step = step_result.scalar_one_or_none()
            
            if not step:
                logger.error(f"   ❌ WorkflowStep not found: {step_detail.workflow_step_id}")
                return None
            
            logger.info(f"   📋 Step: {step.name}")
            logger.info(f"   📝 Description: {step.description[:100]}...")
            logger.info(f"   ⚙️ Step Type: {step.step_type}")
            logger.info(f"   🎯 Actions: {step.actions}")
            
            # Prepare data for Portia
            context_data = {
                "candidate": candidate,
                "job": job,
                "email": email,
                "step_detail": {
                    "id": str(step_detail.id),
                    "order_number": step_detail.order_number,
                    "auto_start": step_detail.auto_start,
                    "required_human_approval": step_detail.required_human_approval,
                    "delay_in_seconds": step_detail.delay_in_seconds
                },
                "step": {
                    "id": str(step.id),
                    "name": step.name,
                    "description": step.description,
                    "step_type": step.step_type,
                    "actions": step.actions
                }
            }
            
            # Execute step using Portia
            portia_result = await self._execute_step_with_portia(step.description, context_data)
            
            if portia_result:
                logger.info(f"   ✅ Portia execution completed")
                logger.info(f"   📊 Result: {portia_result}")
                
                # TODO: Update workflow instance with result and move to next step if approved
                # For now, just return the result
                return portia_result
            else:
                logger.error(f"   ❌ Portia execution failed")
                return None
                
        except Exception as e:
            logger.error(f"Error executing workflow step: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return None

    async def _execute_step_with_portia(self, step_description: str, context_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute workflow step using Portia AI"""
        try:
            logger.info(f"   🤖 Executing with Portia...")
            logger.info(f"   📋 Step Description: {step_description}")
            
            # Import the Portia service
            from services.portia_service import portia_service
            
            # Execute the step using Portia
            result = await portia_service.execute_workflow_step(step_description, context_data)
            
            if result:
                data_preview = str(result.get('data', 'No details'))[:100] if result.get('data') else 'No details'
                logger.info(f"   🎯 Portia Result: {result.get('status', 'unknown')} - {data_preview}...")
                return result
            else:
                logger.error(f"   ❌ Portia execution returned no result")
                # Return fallback result
                return {
                    "success": False,
                    "data": "Portia execution failed - no result returned",
                    "status": "approved"  # Still proceed with workflow
                }
            
        except Exception as e:
            logger.error(f"Error executing step with Portia: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "data": f"Portia execution error: {str(e)}",
                "status": "approved"  # Still proceed with workflow
            }
    
    async def _get_next_step_detail_id(self, db: AsyncSession, workflow_template_id: str, current_step_detail_id: str) -> Optional[str]:
        """Get the next step detail ID in the workflow sequence"""
        try:
            from sqlalchemy import select
            from models.workflow import WorkflowTemplate, WorkflowStepDetail
            
            # Get the workflow template to access steps_execution_id
            template_result = await db.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_template_id)
            )
            template = template_result.scalar_one_or_none()
            
            if not template or not template.steps_execution_id:
                logger.warning(f"   ⚠️ No workflow template or steps found for template: {workflow_template_id}")
                return None
            
            # Get current step detail to find its order_number
            current_step_result = await db.execute(
                select(WorkflowStepDetail).where(
                    WorkflowStepDetail.id == current_step_detail_id,
                    WorkflowStepDetail.is_deleted == False
                )
            )
            current_step = current_step_result.scalar_one_or_none()
            
            if not current_step:
                logger.warning(f"   ⚠️ Current step detail not found: {current_step_detail_id}")
                return None
            
            current_order = current_step.order_number
            next_order = current_order + 1
            
            # Find the next step in the template's steps_execution_id with next order_number
            next_step_result = await db.execute(
                select(WorkflowStepDetail).where(
                    WorkflowStepDetail.id.in_(template.steps_execution_id),
                    WorkflowStepDetail.order_number == next_order,
                    WorkflowStepDetail.is_deleted == False
                ).limit(1)
            )
            next_step = next_step_result.scalar_one_or_none()
            
            if next_step:
                logger.info(f"   ➡️ Found next step: order {next_order}, ID: {next_step.id}")
                return str(next_step.id)
            else:
                logger.info(f"   🏁 No next step found after order {current_order} - workflow complete")
                return None
                
        except Exception as e:
            logger.error(f"Error getting next step detail ID: {e}")
            return None
    
    async def _should_step_auto_start(self, db: AsyncSession, step_detail_id: str) -> bool:
        """Check if a workflow step should auto-start based on workflow_step_detail.auto_start"""
        try:
            from sqlalchemy import select
            from models.workflow import WorkflowStepDetail
            
            # Get the workflow step detail to check auto_start flag
            step_detail_result = await db.execute(
                select(WorkflowStepDetail.auto_start).where(
                    WorkflowStepDetail.id == step_detail_id,
                    WorkflowStepDetail.is_deleted == False
                )
            )
            step_detail = step_detail_result.scalar_one_or_none()
            
            if step_detail is not None:
                auto_start = bool(step_detail)
                logger.info(f"   🔍 Step {step_detail_id} auto_start: {auto_start}")
                return auto_start
            else:
                logger.warning(f"   ⚠️ Step detail not found: {step_detail_id}, defaulting to auto_start=False")
                return False
                
        except Exception as e:
            logger.error(f"Error checking auto_start for step {step_detail_id}: {e}")
            # Default to False (manual trigger) if there's an error
            return False
    
    async def _ai_verify_step_execution(self, db: AsyncSession, step_detail_id: str, email: Dict[str, Any], candidate: Dict[str, Any], job: Dict[str, Any]) -> bool:
        """Use AI to verify if the current step should execute based on email content"""
        try:
            from sqlalchemy import select
            from models.workflow import WorkflowStepDetail, WorkflowStep
            
            # Get current step details
            step_result = await db.execute(
                select(WorkflowStepDetail, WorkflowStep)
                .join(WorkflowStep, WorkflowStepDetail.workflow_step_id == WorkflowStep.id)
                .where(
                    WorkflowStepDetail.id == step_detail_id,
                    WorkflowStepDetail.is_deleted == False
                )
            )
            step_info = step_result.fetchone()
            
            if not step_info:
                logger.warning(f"   ⚠️ Step not found: {step_detail_id}")
                return False
            
            step_detail = step_info.WorkflowStepDetail
            workflow_step = step_info.WorkflowStep
            
            # Extract email content
            email_content = self._extract_email_content(email)
            
            # Use Portia's AI to analyze if this step should execute
            from services.portia_service import portia_service
            
            ai_prompt = f"""
            Analyze the following email content and determine if it should trigger the workflow step "{workflow_step.name}".
            
            Email Content:
            {email_content}
            
            Current Workflow Step: {workflow_step.name}
            Step Type: {workflow_step.step_type}
            Step Description: {workflow_step.description}
            
            Candidate: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
            Job: {job.get('title', '')}
            
            Email Analysis Guidelines:
            - If email is about "submitting assignment" or "completed technical test" → Should trigger "Review Technical Assignment"
            - If email is about "interview availability" or "scheduling" → Should trigger "Schedule Interview"  
            - If email is about "accepting offer" or "start date" → Should trigger offer-related steps
            - If email is general inquiry or unrelated → Should NOT trigger current step
            - If email is initial application → Should trigger "Resume Analysis"
            
            Respond with only: "YES" if this email should trigger the current step, "NO" if it should not.
            """
            
            # Get AI response using Portia
            try:
                import json
                from portia import Message
                
                config = portia_service.portia.config
                llm = config.get_default_model()
                
                messages = [
                    Message(role="system", content="You are an expert HR workflow analyst. Analyze emails to determine correct workflow step execution."),
                    Message(role="user", content=ai_prompt)
                ]
                
                response = llm.get_response(messages)
                ai_decision = response.value.strip().upper() if hasattr(response, 'value') else str(response).strip().upper()
                
                should_execute = "YES" in ai_decision
                
                logger.info(f"   🤖 AI Step Verification:")
                logger.info(f"      📧 Email content: {email_content[:100]}...")
                logger.info(f"      📋 Current step: {workflow_step.name}")
                logger.info(f"      🎯 AI decision: {ai_decision}")
                logger.info(f"      ✅ Should execute: {should_execute}")
                
                return should_execute
                
            except Exception as ai_error:
                logger.warning(f"   ⚠️ AI verification failed: {ai_error}, defaulting to execute")
                return True  # Default to executing if AI fails
                
        except Exception as e:
            logger.error(f"Error in AI step verification: {e}")
            return True  # Default to executing if there's an error
    
    async def _ai_suggest_workflow_step(self, db: AsyncSession, workflow_template_id: str, email: Dict[str, Any], candidate: Dict[str, Any], job: Dict[str, Any]) -> str:
        """Use AI to suggest which workflow step should execute for this email"""
        try:
            from sqlalchemy import select
            from models.workflow import WorkflowTemplate, WorkflowStepDetail, WorkflowStep
            
            # Get all available steps in this workflow template
            template_result = await db.execute(
                select(WorkflowTemplate).where(WorkflowTemplate.id == workflow_template_id)
            )
            template = template_result.scalar_one_or_none()
            
            if not template or not template.steps_execution_id:
                return None
            
            # Get all step details for this template
            steps_result = await db.execute(
                select(WorkflowStepDetail, WorkflowStep)
                .join(WorkflowStep, WorkflowStepDetail.workflow_step_id == WorkflowStep.id)
                .where(
                    WorkflowStepDetail.id.in_(template.steps_execution_id),
                    WorkflowStepDetail.is_deleted == False
                )
                .order_by(WorkflowStepDetail.order_number)
            )
            available_steps = steps_result.fetchall()
            
            if not available_steps:
                return None
            
            # Extract email content
            email_content = self._extract_email_content(email)
            
            # Create step options for AI
            step_options = []
            for step_detail, workflow_step in available_steps:
                step_options.append(f"- {workflow_step.name} (ID: {step_detail.id}) - {workflow_step.step_type}: {workflow_step.description[:100]}...")
            
            # Use AI to suggest the best step
            from services.portia_service import portia_service
            
            ai_prompt = f"""
            Analyze this email content and suggest which workflow step should execute:
            
            Email Content:
            {email_content}
            
            Available Workflow Steps:
            {chr(10).join(step_options)}
            
            Candidate: {candidate.get('first_name', '')} {candidate.get('last_name', '')}
            Job: {job.get('title', '')}
            
            Email Analysis Rules:
            - "submitted assignment" / "completed test" → Review Technical Assignment
            - "interview availability" / "scheduling" → Schedule Interview
            - "accepting offer" / "start date" → Send Offer Letter
            - Initial application → Resume Analysis
            - General inquiry → None (respond with "NONE")
            
            Respond with only the step ID (e.g., "abc123-def-456") or "NONE" if no step is appropriate.
            """
            
            try:
                import json
                from portia import Message
                
                config = portia_service.portia.config
                llm = config.get_default_model()
                
                messages = [
                    Message(role="system", content="You are an expert HR workflow analyst. Suggest the most appropriate workflow step based on email content."),
                    Message(role="user", content=ai_prompt)
                ]
                
                response = llm.get_response(messages)
                suggested_step_id = response.value.strip() if hasattr(response, 'value') else str(response).strip()
                
                if suggested_step_id.upper() == "NONE":
                    logger.info(f"   🤖 AI suggests no workflow step for this email")
                    return None
                
                # Verify the suggested step ID exists in our available steps
                valid_step_ids = [step_detail.id for step_detail, _ in available_steps]
                if suggested_step_id in [str(sid) for sid in valid_step_ids]:
                    # Find the step name for logging
                    step_name = next((ws.name for sd, ws in available_steps if str(sd.id) == suggested_step_id), "Unknown")
                    logger.info(f"   🤖 AI suggests step: {step_name} (ID: {suggested_step_id})")
                    return suggested_step_id
                else:
                    logger.warning(f"   ⚠️ AI suggested invalid step ID: {suggested_step_id}")
                    return None
                    
            except Exception as ai_error:
                logger.warning(f"   ⚠️ AI step suggestion failed: {ai_error}")
                return None
                
        except Exception as e:
            logger.error(f"Error in AI step suggestion: {e}")
            return None
    
    async def _check_approval_requirements(self, db: AsyncSession, step_detail_id: str, candidate_workflow_id: str, candidate: Dict[str, Any], job: Dict[str, Any]) -> str:
        """
        Check if step requires approval and handle approval process.
        Returns: 'approved', 'rejected', 'awaiting_approval', or 'no_approval_needed'
        """
        try:
            from sqlalchemy import select, func
            from models.workflow import WorkflowStepDetail
            from models.approval import WorkflowApprovalRequest, WorkflowApproval
            
            # Get step details to check if approval is required
            step_result = await db.execute(
                select(WorkflowStepDetail).where(
                    WorkflowStepDetail.id == step_detail_id,
                    WorkflowStepDetail.is_deleted == False
                )
            )
            step_detail = step_result.scalar_one_or_none()
            
            if not step_detail:
                logger.warning(f"   ⚠️ Step detail not found: {step_detail_id}")
                return "no_approval_needed"
            
            # Check if this step requires human approval
            if not step_detail.required_human_approval:
                logger.info(f"   ✅ Step does not require approval - proceeding")
                return "no_approval_needed"
            
            # Step requires approval - check if approval requests already exist
            existing_requests_result = await db.execute(
                select(WorkflowApprovalRequest).where(
                    WorkflowApprovalRequest.candidate_workflow_id == candidate_workflow_id,
                    WorkflowApprovalRequest.workflow_step_detail_id == step_detail_id
                )
            )
            existing_requests = existing_requests_result.scalars().all()
            
            if not existing_requests:
                # No approval requests exist - create them
                logger.info(f"   📝 Creating approval requests for step: {step_detail_id}")
                return await self._create_approval_requests(db, step_detail, candidate_workflow_id, candidate, job)
            else:
                # Approval requests exist - check their status
                logger.info(f"   🔍 Checking status of existing approval requests")
                return await self._check_approval_status(db, existing_requests, step_detail.number_of_approvals_needed)
                
        except Exception as e:
            logger.error(f"Error checking approval requirements: {e}")
            return "no_approval_needed"  # Default to proceed if there's an error
    
    async def _check_step_approval_requirements(self, db: AsyncSession, step_detail_id: str, candidate_workflow_id: str, candidate: Dict[str, Any], job: Dict[str, Any]) -> str:
        """
        Check if a specific step requires approval and create approval requests if needed.
        This is used for next steps in the workflow progression.
        Returns: 'approval_required' if approval needed, 'no_approval_needed' if not
        """
        try:
            from sqlalchemy import select
            from models.workflow import WorkflowStepDetail
            from models.approval import WorkflowApprovalRequest
            
            # Get step details to check if approval is required
            step_result = await db.execute(
                select(WorkflowStepDetail).where(
                    WorkflowStepDetail.id == step_detail_id,
                    WorkflowStepDetail.is_deleted == False
                )
            )
            step_detail = step_result.scalar_one_or_none()
            
            if not step_detail:
                logger.warning(f"   ⚠️ Step detail not found: {step_detail_id}")
                return "no_approval_needed"
            
            # Check if this step requires human approval
            if not step_detail.required_human_approval:
                logger.info(f"   ✅ Next step does not require approval")
                return "no_approval_needed"
            
            # Check number of approvals needed and approvers list
            approvers = step_detail.approvers or []
            approvals_needed = step_detail.number_of_approvals_needed or len(approvers)
            
            if not approvers:
                logger.warning(f"   ⚠️ Step requires approval but no approvers defined - skipping approval")
                return "no_approval_needed"
            
            logger.info(f"   📧 Next step requires {approvals_needed} approval(s) from {len(approvers)} approver(s)")
            
            # Check if approval requests already exist for this step
            existing_requests_result = await db.execute(
                select(WorkflowApprovalRequest).where(
                    WorkflowApprovalRequest.candidate_workflow_id == candidate_workflow_id,
                    WorkflowApprovalRequest.workflow_step_detail_id == step_detail_id
                )
            )
            existing_requests = existing_requests_result.scalars().all()
            
            if existing_requests:
                logger.info(f"   ℹ️ Approval requests already exist for this step")
                return "approval_required"
            
            # Create approval requests for this step
            logger.info(f"   📝 Creating approval requests for {len(approvers)} approver(s)")
            await self._create_approval_requests(db, step_detail, candidate_workflow_id, candidate, job)
            
            return "approval_required"
                
        except Exception as e:
            logger.error(f"Error checking step approval requirements: {e}")
            return "no_approval_needed"  # Default to proceed if there's an error
    
    async def _create_approval_requests(self, db: AsyncSession, step_detail, candidate_workflow_id: str, candidate: Dict[str, Any], job: Dict[str, Any]) -> str:
        """Create approval requests for all approvers of this step"""
        try:
            from models.approval import WorkflowApprovalRequest
            
            if not step_detail.approvers:
                logger.warning(f"   ⚠️ Step requires approval but no approvers configured")
                return "no_approval_needed"
            
            # Create approval request for each approver
            approval_requests = []
            for approver_id in step_detail.approvers:
                approval_request = WorkflowApprovalRequest(
                    candidate_workflow_id=candidate_workflow_id,
                    workflow_step_detail_id=step_detail.id,
                    approver_user_id=approver_id,
                    required_approvals=step_detail.number_of_approvals_needed or len(step_detail.approvers)
                )
                approval_requests.append(approval_request)
                db.add(approval_request)
            
            await db.commit()
            
            # Send email notifications to approvers
            await self._send_approval_notifications(db, approval_requests, candidate, job, step_detail)
            
            logger.info(f"   ✅ Created {len(approval_requests)} approval requests")
            return "awaiting_approval"
            
        except Exception as e:
            logger.error(f"Error creating approval requests: {e}")
            await db.rollback()
            return "no_approval_needed"
    
    async def _check_approval_status(self, db: AsyncSession, approval_requests: list, required_approvals: int) -> str:
        """Check the current status of approval requests"""
        try:
            from sqlalchemy import select
            from models.approval import WorkflowApproval
            
            total_requests = len(approval_requests)
            approved_count = 0
            rejected_count = 0
            
            # Check each approval request for responses
            for request in approval_requests:
                approval_result = await db.execute(
                    select(WorkflowApproval).where(
                        WorkflowApproval.approval_request_id == request.id
                    )
                )
                approval = approval_result.scalar_one_or_none()
                
                if approval:
                    if approval.decision == 'approved':
                        approved_count += 1
                    elif approval.decision == 'rejected':
                        rejected_count += 1
            
            pending_count = total_requests - approved_count - rejected_count
            
            logger.info(f"   📊 Approval Status: {approved_count} approved, {rejected_count} rejected, {pending_count} pending")
            
            # Check if any rejection (immediate rejection)
            if rejected_count > 0:
                return "rejected"
            
            # Check if enough approvals received
            if approved_count >= (required_approvals or total_requests):
                return "approved"
            
            # Still waiting for more approvals
            return "awaiting_approval"
            
        except Exception as e:
            logger.error(f"Error checking approval status: {e}")
            return "awaiting_approval"
    
    async def _send_approval_notifications(self, db: AsyncSession, approval_requests: list, candidate: Dict[str, Any], job: Dict[str, Any], step_detail) -> None:
        """Send email notifications to approvers"""
        try:
            # TODO: Implement email notification logic
            # For now, we'll just log that notifications would be sent
            logger.info(f"   📧 Would send approval notifications to {len(approval_requests)} approvers")
            logger.info(f"   📋 For candidate: {candidate.get('first_name', '')} {candidate.get('last_name', '')}")
            logger.info(f"   💼 For job: {job.get('title', '')}")
            logger.info(f"   📝 Step: {step_detail.workflow_step_id}")
            
            # TODO: Send actual emails using email service
            # This would typically include:
            # - Email template with approval/reject links
            # - Candidate information
            # - Job details
            # - Step description
            
        except Exception as e:
            logger.error(f"Error sending approval notifications: {e}")
    
    def _extract_email_content(self, email: Dict[str, Any]) -> str:
        """Extract readable content from email for AI analysis"""
        try:
            # Start with snippet
            email_content = email.get('snippet', '')
            
            # Try to get more detailed content from payload
            if 'payload' in email and 'headers' in email['payload']:
                headers = email['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                
                # Try to get email body
                body_content = ""
                if 'parts' in email['payload']:
                    for part in email['payload']['parts']:
                        if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                            try:
                                import base64
                                body_data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                                body_content = body_data
                                break
                            except:
                                continue
                
                # Combine all available content
                if body_content:
                    email_content = f"Subject: {subject}\nFrom: {sender}\n\nContent:\n{body_content}"
                else:
                    email_content = f"Subject: {subject}\nFrom: {sender}\n\nSnippet: {email.get('snippet', '')}"
            
            return email_content
            
        except Exception as e:
            logger.warning(f"Error extracting email content: {e}")
            return email.get('snippet', 'Email content not available')
    
    async def _update_candidate_workflow_current_step(self, db: AsyncSession, workflow_id: str, next_step_detail_id: str):
        """Update the current_step_detail_id in candidate_workflow"""
        try:
            from sqlalchemy import update
            from models.workflow import CandidateWorkflow
            from datetime import datetime
            
            update_query = update(CandidateWorkflow).where(
                CandidateWorkflow.id == workflow_id
            ).values(
                current_step_detail_id=next_step_detail_id,
                updated_at=datetime.utcnow()
            )
            
            await db.execute(update_query)
            await db.commit()
            
            logger.info(f"   ✅ Updated candidate workflow current step: {next_step_detail_id}")
            
        except Exception as e:
            logger.error(f"Error updating candidate workflow current step: {e}")
            await db.rollback()
    
    async def _update_workflow_execution_log(self, db: AsyncSession, workflow_id: str, step_result: Dict[str, Any], step_detail_id: str):
        """Update the execution_log in candidate_workflow with step result"""
        try:
            from sqlalchemy import select, update
            from models.workflow import CandidateWorkflow
            from datetime import datetime
            
            # Get current execution log
            result = await db.execute(
                select(CandidateWorkflow.execution_log).where(CandidateWorkflow.id == workflow_id)
            )
            current_log = result.scalar_one_or_none() or []
            
            # Add new log entry (convert UUIDs to strings for JSON serialization)
            log_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "step_detail_id": str(step_detail_id),
                "step_result": {
                    "success": step_result.get('success', False),
                    "status": step_result.get('status', 'unknown'),
                    "data": str(step_result.get('data', ''))[:200]  # Truncate data to avoid large logs
                },
                "status": step_result.get('status', 'unknown'),
                "success": step_result.get('success', False)
            }
            
            current_log.append(log_entry)
            
            # Update the execution log
            update_query = update(CandidateWorkflow).where(
                CandidateWorkflow.id == workflow_id
            ).values(
                execution_log=current_log,
                updated_at=datetime.utcnow()
            )
            
            await db.execute(update_query)
            await db.commit()
            
            logger.info(f"   📝 Updated execution log for workflow: {workflow_id}")
            
        except Exception as e:
            logger.error(f"Error updating workflow execution log: {e}")
            await db.rollback()
    
    async def _mark_workflow_completed(self, db: AsyncSession, workflow_id: str):
        """Mark workflow as completed"""
        try:
            from sqlalchemy import update
            from models.workflow import CandidateWorkflow
            from datetime import datetime
            
            update_query = update(CandidateWorkflow).where(
                CandidateWorkflow.id == workflow_id
            ).values(
                current_step_detail_id=None,  # No more steps
                completed_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            await db.execute(update_query)
            await db.commit()
            
            logger.info(f"   🎉 Marked workflow as completed: {workflow_id}")
            
        except Exception as e:
            logger.error(f"Error marking workflow as completed: {e}")
            await db.rollback()
    
    async def _mark_workflow_rejected(self, db: AsyncSession, workflow_id: str, rejection_reason: str):
        """Mark workflow as rejected"""
        try:
            from sqlalchemy import select, update
            from models.workflow import CandidateWorkflow
            from datetime import datetime
            
            # Get current execution log to add rejection entry
            result = await db.execute(
                select(CandidateWorkflow.execution_log).where(CandidateWorkflow.id == workflow_id)
            )
            current_log = result.scalar_one_or_none() or []
            
            # Add rejection log entry
            rejection_entry = {
                "timestamp": datetime.utcnow().isoformat(),
                "event": "workflow_rejected",
                "reason": rejection_reason,
                "status": "rejected"
            }
            
            current_log.append(rejection_entry)
            
            update_query = update(CandidateWorkflow).where(
                CandidateWorkflow.id == workflow_id
            ).values(
                current_step_detail_id=None,  # No more steps
                completed_at=datetime.utcnow(),
                execution_log=current_log,
                updated_at=datetime.utcnow()
            )
            
            await db.execute(update_query)
            await db.commit()
            
            logger.info(f"   ❌ Marked workflow as rejected: {workflow_id}")
            logger.info(f"   📝 Rejection reason: {rejection_reason}")
            
        except Exception as e:
            logger.error(f"Error marking workflow as rejected: {e}")
            await db.rollback()
            
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