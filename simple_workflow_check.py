#!/usr/bin/env python3
"""
Simple check of workflow results
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def simple_check():
    """Simple check of workflows"""
    
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
            print("🔍 Simple Workflow Check")
            print("=" * 50)
            
            # Check candidate workflows
            result = await session.execute(text("""
                SELECT COUNT(*) as count FROM candidate_workflow
            """))
            workflow_count = result.scalar()
            print(f"📊 Candidate workflows count: {workflow_count}")
            
            # Check job workflow assignment
            result = await session.execute(text("""
                SELECT 
                    j.title,
                    j.workflow_template_id
                FROM jobs j
                WHERE j.id = '782c2f15-5b87-4968-a353-094b1aa7823d'
            """))
            job_info = result.fetchone()
            print(f"💼 Job: {job_info.title}")
            print(f"🔄 Has workflow template: {'Yes' if job_info.workflow_template_id else 'No'}")
            
            # Check workflow_step_detail table columns
            result = await session.execute(text("""
                SELECT column_name
                FROM information_schema.columns 
                WHERE table_name = 'workflow_step_detail'
                ORDER BY ordinal_position
            """))
            columns = [row[0] for row in result.fetchall()]
            print(f"⚙️ workflow_step_detail columns: {columns}")
            
            # Check if there are any workflow step details at all
            result = await session.execute(text("""
                SELECT COUNT(*) as count FROM workflow_step_detail
            """))
            step_count = result.scalar()
            print(f"📋 Total workflow step details: {step_count}")
            
            if step_count > 0:
                # Show some step details
                result = await session.execute(text("""
                    SELECT id, workflow_step_id, order_number 
                    FROM workflow_step_detail 
                    LIMIT 3
                """))
                steps = result.fetchall()
                print(f"📋 Sample step details:")
                for step in steps:
                    print(f"   ID: {step.id}, Step: {step.workflow_step_id}, Order: {step.order_number}")
            
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(simple_check())
