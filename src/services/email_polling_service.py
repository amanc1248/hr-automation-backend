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
            
            # 4. Find existing job (jobs must be created beforehand by HR/recruiters)
            job = await self._find_existing_job(db, job_title)
            if job:
                logger.info(f"   🎯 Job found: {job['id']} - {job['title']}")
            else:
                logger.warning(f"   ⚠️ No existing job found for title: {job_title}")
                logger.info(f"   💡 Make sure the job '{job_title}' exists in the system before candidates apply")
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
                
                # Execute current workflow step
                step_result = await self._execute_workflow_step(db, existing_workflow, candidate, job, email)
                if step_result:
                    logger.info(f"   🎯 Workflow step executed: {step_result.get('status', 'unknown')}")
                else:
                    logger.warning(f"   ⚠️ Failed to execute workflow step")
                    
            else:
                logger.info(f"   🆕 Creating new candidate workflow...")
                # 11. Create new candidate_workflow
                new_workflow = await self._create_candidate_workflow(db, job['id'], candidate['id'], workflow_template_id, email)
                if new_workflow:
                    logger.info(f"   ✅ Created new candidate workflow: {new_workflow['id']}")
                    logger.info(f"   📋 Starting with step ID: {new_workflow.get('current_step_detail_id', 'Not set')}")
                    
                    # Execute first workflow step
                    step_result = await self._execute_workflow_step(db, new_workflow, candidate, job, email)
                    if step_result:
                        logger.info(f"   🎯 Workflow step executed: {step_result.get('status', 'unknown')}")
                    else:
                        logger.warning(f"   ⚠️ Failed to execute workflow step")
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
    
    async def _find_existing_job(self, db: AsyncSession, job_title: str) -> Optional[Dict[str, Any]]:
        """Find existing job by title (no job creation - jobs must exist first)"""
        try:
            from sqlalchemy import select
            from models.job import Job
            
            # Find existing job by title (case-insensitive partial match)
            # Try exact match first, then partial match
            result = await db.execute(
                select(Job).where(
                    Job.title.ilike(f"%{job_title}%"),
                    Job.status.in_(["active", "draft"])
                ).limit(1)
            )
            existing_job = result.scalar_one_or_none()
            
            if existing_job:
                logger.info(f"   ✅ Found existing job: {existing_job.title}")
                return {
                    "id": existing_job.id,
                    "title": existing_job.title,
                    "status": existing_job.status,
                    "workflow_template_id": existing_job.workflow_template_id,
                    "department": getattr(existing_job, 'department', None)
                }
            else:
                # Log available jobs for debugging
                all_jobs_result = await db.execute(
                    select(Job.title).where(Job.status.in_(["active", "draft"]))
                )
                available_jobs = [row[0] for row in all_jobs_result.fetchall()]
                logger.warning(f"   ❌ No job found for title: '{job_title}'")
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
                logger.info(f"   🎯 Portia Result: {result.get('status', 'unknown')} - {result.get('data', 'No details')[:100]}...")
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