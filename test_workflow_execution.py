#!/usr/bin/env python3
"""
Test script to verify workflow execution logic
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

# Add src to path for imports
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.email_polling_service import email_polling_service

async def test_workflow_execution():
    """Test the workflow execution by simulating an email trigger"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    # Convert to async driver if needed
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    # Create async engine
    engine = create_async_engine(database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("🧪 Testing Workflow Execution Logic")
            print("=" * 60)
            
            # Mock email data
            mock_email = {
                "id": "test_email_123",
                "payload": {
                    "headers": [
                        {"name": "Subject", "value": "Applying For Full Stack Developer Role"},
                        {"name": "From", "value": "John Doe <john.doe@example.com>"},
                        {"name": "Date", "value": "Wed, 24 Aug 2025 18:00:00 +0000"}
                    ]
                }
            }
            
            print(f"📧 Mock Email:")
            print(f"   Subject: Applying For Full Stack Developer Role")
            print(f"   From: John Doe <john.doe@example.com>")
            print("")
            
            # Trigger the workflow for this email
            print(f"🚀 Starting workflow for mock email...")
            await email_polling_service._start_workflow_for_email(session, mock_email, "test@example.com")
            
            print("")
            print("✅ Workflow execution test completed!")
            
            # Check if any candidate workflows were created
            result = await session.execute(text("""
                SELECT COUNT(*) as count FROM candidate_workflow
            """))
            workflow_count = result.scalar()
            print(f"📊 Total candidate workflows in database: {workflow_count}")
            
            if workflow_count > 0:
                # Show the latest workflow
                result = await session.execute(text("""
                    SELECT 
                        cw.id,
                        cw.name,
                        cw.current_step_detail_id,
                        cw.started_at,
                        c.email as candidate_email,
                        j.title as job_title
                    FROM candidate_workflow cw
                    JOIN candidates c ON cw.candidate_id = c.id
                    JOIN jobs j ON cw.job_id = j.id
                    ORDER BY cw.started_at DESC 
                    LIMIT 1
                """))
                
                latest_workflow = result.fetchone()
                if latest_workflow:
                    print(f"📋 Latest Workflow:")
                    print(f"   🆔 ID: {latest_workflow.id}")
                    print(f"   📝 Name: {latest_workflow.name}")
                    print(f"   👤 Candidate: {latest_workflow.candidate_email}")
                    print(f"   💼 Job: {latest_workflow.job_title}")
                    print(f"   📍 Current Step ID: {latest_workflow.current_step_detail_id}")
                    print(f"   🕒 Started: {latest_workflow.started_at}")
            
        except Exception as e:
            print(f"❌ Error during test: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_workflow_execution())
