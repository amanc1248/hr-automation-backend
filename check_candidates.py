#!/usr/bin/env python3
"""
Quick script to check if candidates were created
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def check_candidates():
    """Check candidates in database"""
    
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
            # Check candidates
            result = await session.execute(text("""
                SELECT 
                    id, 
                    first_name, 
                    last_name, 
                    email, 
                    company_id,
                    source,
                    status,
                    created_at
                FROM candidates 
                ORDER BY created_at DESC 
                LIMIT 5
            """))
            
            candidates = result.fetchall()
            
            print("🔍 Recent Candidates:")
            print("=" * 80)
            
            if candidates:
                for candidate in candidates:
                    print(f"📧 {candidate.email} ({candidate.first_name} {candidate.last_name})")
                    print(f"   🏢 Company ID: {candidate.company_id}")
                    print(f"   📊 Status: {candidate.status} | Source: {candidate.source}")
                    print(f"   🕒 Created: {candidate.created_at}")
                    print("-" * 40)
                print(f"✅ Found {len(candidates)} candidates!")
            else:
                print("❌ No candidates found")
            
            # Check applications
            result = await session.execute(text("""
                SELECT 
                    a.id,
                    a.status,
                    a.applied_at,
                    c.email as candidate_email,
                    j.title as job_title
                FROM applications a
                JOIN candidates c ON a.candidate_id = c.id
                JOIN jobs j ON a.job_id = j.id
                ORDER BY a.applied_at DESC 
                LIMIT 5
            """))
            
            applications = result.fetchall()
            
            print(f"\n📝 Recent Applications:")
            print("=" * 80)
            
            if applications:
                for app in applications:
                    print(f"🎯 {app.candidate_email} → {app.job_title}")
                    print(f"   📊 Status: {app.status}")
                    print(f"   🕒 Applied: {app.applied_at}")
                    print("-" * 40)
                print(f"✅ Found {len(applications)} applications!")
            else:
                print("❌ No applications found")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_candidates())
