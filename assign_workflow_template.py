#!/usr/bin/env python3
"""
Script to assign workflow template to job
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def assign_workflow_template():
    """Assign workflow template to the job"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    # Convert to async driver if needed
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    # Create async engine
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            # Job ID and Workflow Template ID
            job_id = "782c2f15-5b87-4968-a353-094b1aa7823d"  # "Applying For Full Stack Developer Role"
            workflow_template_id = "661cbcbf-0f2a-4564-b7b9-71f41f1821f0"  # "Hiring Full Stack Developer Role"
            
            print(f"🔧 Assigning workflow template to job...")
            print(f"   Job ID: {job_id}")
            print(f"   Workflow Template ID: {workflow_template_id}")
            
            # Update the job with workflow template
            result = await session.execute(text("""
                UPDATE jobs 
                SET workflow_template_id = :workflow_template_id,
                    updated_at = NOW()
                WHERE id = :job_id
            """), {
                "workflow_template_id": workflow_template_id,
                "job_id": job_id
            })
            
            if result.rowcount > 0:
                print("✅ Successfully assigned workflow template to job!")
                
                # Verify the update
                result = await session.execute(text("""
                    SELECT title, workflow_template_id 
                    FROM jobs 
                    WHERE id = :job_id
                """), {"job_id": job_id})
                
                job = result.fetchone()
                if job:
                    print(f"   Job: {job.title}")
                    print(f"   Workflow Template ID: {job.workflow_template_id}")
                
                await session.commit()
            else:
                print("❌ Job not found or no changes made")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            await session.rollback()
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(assign_workflow_template())
