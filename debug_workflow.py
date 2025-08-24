#!/usr/bin/env python3
"""
Debug script to check workflow issues
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def debug_workflow():
    """Debug workflow issues"""
    
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
            # Check jobs that might match email subject "Applying For Full Stack Developer Role"
            result = await session.execute(text("""
                SELECT 
                    id, 
                    title, 
                    workflow_template_id,
                    status,
                    company_id
                FROM jobs 
                WHERE status IN ('active', 'draft')
                ORDER BY created_at DESC
            """))
            
            jobs = result.fetchall()
            
            print("🔍 Available Jobs:")
            print("=" * 80)
            
            for job in jobs:
                print(f"📋 Job: {job.title}")
                print(f"   🆔 ID: {job.id}")
                print(f"   📊 Status: {job.status}")
                print(f"   🏢 Company ID: {job.company_id}")
                print(f"   🔄 Workflow Template ID: {job.workflow_template_id}")
                
                # Check if this job title would match "Applying For Full Stack Developer Role"
                if "full stack" in job.title.lower():
                    print(f"   ✅ WOULD MATCH email subject!")
                else:
                    print(f"   ❌ Would not match")
                print("-" * 40)
            
            # Check available workflow templates
            result = await session.execute(text("""
                SELECT 
                    id, 
                    name, 
                    description,
                    category,
                    is_active
                FROM workflow_template 
                WHERE is_active = true
                ORDER BY created_at DESC
            """))
            
            templates = result.fetchall()
            
            print("\n🔄 Available Workflow Templates:")
            print("=" * 80)
            
            if templates:
                for template in templates:
                    print(f"📋 Template: {template.name}")
                    print(f"   🆔 ID: {template.id}")
                    print(f"   📝 Description: {template.description}")
                    print(f"   🏷️ Category: {template.category}")
                    print("-" * 40)
            else:
                print("❌ No active workflow templates found!")
            
            # Check workflow steps
            result = await session.execute(text("""
                SELECT 
                    id, 
                    name, 
                    description
                FROM workflow_step 
                ORDER BY created_at DESC
                LIMIT 5
            """))
            
            steps = result.fetchall()
            
            print("\n⚙️ Available Workflow Steps:")
            print("=" * 80)
            
            if steps:
                for step in steps:
                    print(f"⚙️ Step: {step.name}")
                    print(f"   🆔 ID: {step.id}")
                    print(f"   📝 Description: {step.description[:100]}...")
                    print("-" * 40)
            else:
                print("❌ No workflow steps found!")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(debug_workflow())
