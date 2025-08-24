#!/usr/bin/env python3
"""
Check workflow results after email polling
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def check_workflow_results():
    """Check if candidate workflows were created correctly"""
    
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
            print("🔍 Checking Workflow Results")
            print("=" * 60)
            
            # Check candidate workflows
            result = await session.execute(text("""
                SELECT 
                    cw.id,
                    cw.name,
                    cw.current_step_detail_id,
                    cw.started_at,
                    c.email as candidate_email,
                    j.title as job_title,
                    wt.name as workflow_template_name
                FROM candidate_workflow cw
                JOIN candidates c ON cw.candidate_id = c.id
                JOIN jobs j ON cw.job_id = j.id
                JOIN workflow_template wt ON cw.workflow_template_id = wt.id
                ORDER BY cw.started_at DESC 
                LIMIT 10
            """))
            
            workflows = result.fetchall()
            
            print(f"📋 Recent Candidate Workflows:")
            print("-" * 60)
            
            if workflows:
                for wf in workflows:
                    print(f"🔄 Workflow: {wf.name}")
                    print(f"   🆔 ID: {wf.id}")
                    print(f"   👤 Candidate: {wf.candidate_email}")
                    print(f"   💼 Job: {wf.job_title}")
                    print(f"   📋 Template: {wf.workflow_template_name}")
                    print(f"   📍 Current Step ID: {wf.current_step_detail_id}")
                    print(f"   🕒 Started: {wf.started_at}")
                    print("-" * 40)
                print(f"✅ Found {len(workflows)} candidate workflows!")
            else:
                print("❌ No candidate workflows found")
            
            # Check workflow step details to see what the first step should be
            result = await session.execute(text("""
                SELECT 
                    wsd.id,
                    wsd.order_number,
                    ws.name as step_name,
                    ws.description,
                    wt.name as template_name
                FROM workflow_step_detail wsd
                JOIN workflow_step ws ON wsd.workflow_step_id = ws.id
                JOIN workflow_template wt ON wsd.workflow_template_id = wt.id
                WHERE wt.id = '661cbcbf-0f2a-4564-b7b9-71f41f1821f0'
                ORDER BY wsd.order_number ASC
                LIMIT 5
            """))
            
            step_details = result.fetchall()
            
            print(f"\n⚙️ Workflow Steps for 'Hiring Full Stack Developer Role':")
            print("-" * 60)
            
            if step_details:
                for step in step_details:
                    print(f"📍 Step {step.order_number}: {step.step_name}")
                    print(f"   🆔 Step Detail ID: {step.id}")
                    print(f"   📝 Description: {step.description[:100]}...")
                    print("-" * 40)
            else:
                print("❌ No workflow steps found for this template")
            
            # Check specific job workflow assignment
            result = await session.execute(text("""
                SELECT 
                    j.title,
                    j.workflow_template_id,
                    wt.name as template_name
                FROM jobs j
                LEFT JOIN workflow_template wt ON j.workflow_template_id = wt.id
                WHERE j.id = '782c2f15-5b87-4968-a353-094b1aa7823d'
            """))
            
            job_info = result.fetchone()
            
            print(f"\n💼 Job Workflow Configuration:")
            print("-" * 60)
            if job_info:
                print(f"📋 Job: {job_info.title}")
                print(f"🔄 Workflow Template ID: {job_info.workflow_template_id}")
                print(f"📋 Template Name: {job_info.template_name}")
                if job_info.workflow_template_id:
                    print("✅ Job has workflow template assigned!")
                else:
                    print("❌ Job has no workflow template assigned")
            else:
                print("❌ Job not found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_workflow_results())
