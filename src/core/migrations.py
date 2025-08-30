"""
Database migrations and table creation
"""

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import logging

from .database import engine, AsyncSessionLocal

logger = logging.getLogger(__name__)

async def create_all_tables():
    """Create all database tables"""
    print("🔧 Creating database tables...")
    
    try:
        # Import all models to ensure they're registered
        from src.models.base import BaseModel
        from src.models.user import Profile, UserRole, Company
        from src.models.gmail_webhook import GmailWatch, EmailProcessingLog
        from src.models.job import Job
        from src.models.workflow import WorkflowTemplate, WorkflowStep, WorkflowStepDetail, CandidateWorkflow
        from src.models.approval import WorkflowApprovalRequest
        from src.models.candidate_workflow_execution import CandidateWorkflowExecution
        from src.models.candidate import Candidate, Application
        from src.models.interview import Interview, AIInterviewConfig
        from src.models.email import EmailAccount, EmailTemplate, EmailMonitoring
        
        # Create all tables
        async with engine.begin() as conn:
            # Create extensions first
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"'))
            await conn.execute(text('CREATE EXTENSION IF NOT EXISTS "pgcrypto"'))
            
            # Create all tables
            await conn.run_sync(BaseModel.metadata.create_all)
            
        print("✅ All database tables created successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create tables: {e}")
        logger.error(f"Table creation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def drop_all_tables():
    """Drop all database tables (use with caution!)"""
    print("⚠️  Dropping all database tables...")
    
    try:
        from src.models.base import BaseModel
        
        async with engine.begin() as conn:
            await conn.run_sync(BaseModel.metadata.drop_all)
            
        print("✅ All database tables dropped!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to drop tables: {e}")
        logger.error(f"Table drop failed: {e}")
        return False

async def init_default_data():
    """Initialize database with default data"""
    print("📊 Initializing default data...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if user roles exist
            from src.models.user import UserRole
            
            existing_roles = await session.execute(
                text("SELECT COUNT(*) FROM user_roles")
            )
            role_count = existing_roles.scalar()
            
            if role_count == 0:
                print("📝 Creating default user roles...")
                
                # Create default roles
                default_roles = [
                    {
                        'name': 'super_admin',
                        'display_name': 'Super Admin',
                        'description': 'Full system access and company management',
                        'permissions': ['all'],
                        'approval_types': ['all'],
                        'is_system_role': True
                    },
                    {
                        'name': 'admin',
                        'display_name': 'Admin',
                        'description': 'Company administration and user management',
                        'permissions': ['company_manage', 'user_manage', 'job_manage', 'candidate_manage'],
                        'approval_types': ['hiring_decision', 'workflow_approval'],
                        'is_system_role': False
                    },
                    {
                        'name': 'hr_manager',
                        'display_name': 'HR Manager',
                        'description': 'HR operations and candidate management',
                        'permissions': ['job_manage', 'candidate_manage', 'interview_manage'],
                        'approval_types': ['interview_approval'],
                        'is_system_role': False
                    },
                    {
                        'name': 'recruiter',
                        'display_name': 'Recruiter',
                        'description': 'Job posting and candidate sourcing',
                        'permissions': ['job_create', 'candidate_manage', 'interview_schedule'],
                        'approval_types': [],
                        'is_system_role': False
                    },
                    {
                        'name': 'hiring_manager',
                        'display_name': 'Hiring Manager',
                        'description': 'Department hiring decisions and interviews',
                        'permissions': ['candidate_review', 'interview_conduct'],
                        'approval_types': ['final_approval'],
                        'is_system_role': False
                    }
                ]
                
                for role_data in default_roles:
                    role = UserRole(**role_data)
                    session.add(role)
                
                await session.commit()
                print(f"✅ Created {len(default_roles)} default user roles")
            
            # Check if email templates exist
            from src.models.email import EmailTemplate
            
            existing_templates = await session.execute(
                text("SELECT COUNT(*) FROM email_templates WHERE is_system_template = true")
            )
            template_count = existing_templates.scalar()
            
            if template_count == 0:
                print("📧 Creating default email templates...")
                
                # Create default email templates
                default_templates = [
                    {
                        'name': 'Application Received',
                        'description': 'Confirmation email when application is received',
                        'category': 'application_received',
                        'subject': 'Application Received - {{job_title}} at {{company_name}}',
                        'body_html': '''
                        <h2>Thank you for your application!</h2>
                        <p>Dear {{candidate_name}},</p>
                        <p>We have received your application for the <strong>{{job_title}}</strong> position at {{company_name}}.</p>
                        <p>Our team will review your application and get back to you within {{review_timeline}} business days.</p>
                        <p>Best regards,<br>{{company_name}} Hiring Team</p>
                        ''',
                        'variables': ['candidate_name', 'job_title', 'company_name', 'review_timeline'],
                        'is_system_template': True
                    },
                    {
                        'name': 'Interview Invitation',
                        'description': 'Invitation for interview scheduling',
                        'category': 'interview_invite',
                        'subject': 'Interview Invitation - {{job_title}} at {{company_name}}',
                        'body_html': '''
                        <h2>Interview Invitation</h2>
                        <p>Dear {{candidate_name}},</p>
                        <p>Congratulations! We would like to invite you for an interview for the <strong>{{job_title}}</strong> position.</p>
                        <p><strong>Interview Details:</strong></p>
                        <ul>
                            <li>Date: {{interview_date}}</li>
                            <li>Time: {{interview_time}}</li>
                            <li>Duration: {{interview_duration}}</li>
                            <li>Type: {{interview_type}}</li>
                        </ul>
                        <p>Please confirm your availability by replying to this email.</p>
                        <p>Best regards,<br>{{interviewer_name}}</p>
                        ''',
                        'variables': ['candidate_name', 'job_title', 'company_name', 'interview_date', 'interview_time', 'interview_duration', 'interview_type', 'interviewer_name'],
                        'is_system_template': True
                    },
                    {
                        'name': 'Application Rejected',
                        'description': 'Polite rejection email',
                        'category': 'rejection',
                        'subject': 'Update on Your Application - {{job_title}}',
                        'body_html': '''
                        <h2>Thank you for your interest</h2>
                        <p>Dear {{candidate_name}},</p>
                        <p>Thank you for taking the time to apply for the <strong>{{job_title}}</strong> position at {{company_name}}.</p>
                        <p>After careful consideration, we have decided to move forward with other candidates whose experience more closely matches our current needs.</p>
                        <p>We encourage you to apply for future opportunities that match your background and interests.</p>
                        <p>Best wishes for your job search,<br>{{company_name}} Hiring Team</p>
                        ''',
                        'variables': ['candidate_name', 'job_title', 'company_name'],
                        'is_system_template': True
                    }
                ]
                
                for template_data in default_templates:
                    template = EmailTemplate(**template_data)
                    session.add(template)
                
                await session.commit()
                print(f"✅ Created {len(default_templates)} default email templates")
            
        print("✅ Default data initialization completed!")
        return True
        
    except Exception as e:
        print(f"❌ Failed to initialize default data: {e}")
        logger.error(f"Default data initialization failed: {e}")
        import traceback
        traceback.print_exc()
        return False

async def reset_database():
    """Reset database - drop and recreate all tables"""
    print("🔄 Resetting database...")
    
    success = await drop_all_tables()
    if not success:
        return False
    
    success = await create_all_tables()
    if not success:
        return False
    
    success = await init_default_data()
    return success

async def check_database_schema():
    """Check database schema and tables"""
    print("🔍 Checking database schema...")
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if tables exist
            tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            
            result = await session.execute(tables_query)
            tables = [row[0] for row in result.fetchall()]
            
            print(f"📊 Found {len(tables)} tables:")
            for table in tables:
                print(f"   - {table}")
            
            return tables
            
    except Exception as e:
        print(f"❌ Failed to check schema: {e}")
        return []
