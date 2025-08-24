#!/usr/bin/env python3
"""
Test script to verify application uniqueness is working
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def test_application_uniqueness():
    """Test that duplicate applications are prevented"""
    
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
            print("🧪 Testing Application Uniqueness")
            print("=" * 50)
            
            # Get current applications count
            result = await session.execute(text("""
                SELECT COUNT(*) as total_applications
                FROM applications
            """))
            initial_count = result.scalar()
            print(f"📊 Initial applications count: {initial_count}")
            
            # Check for existing duplicates in the current data
            result = await session.execute(text("""
                SELECT 
                    job_id, 
                    candidate_id, 
                    COUNT(*) as count,
                    STRING_AGG(CAST(id AS TEXT), ', ') as application_ids
                FROM applications 
                GROUP BY job_id, candidate_id 
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """))
            
            duplicates = result.fetchall()
            
            if duplicates:
                print(f"⚠️  Found {len(duplicates)} duplicate combinations:")
                for dup in duplicates:
                    print(f"   Job: {dup.job_id}")
                    print(f"   Candidate: {dup.candidate_id}")
                    print(f"   Count: {dup.count}")
                    print(f"   Application IDs: {dup.application_ids}")
                    print("-" * 30)
            else:
                print("✅ No duplicate applications found!")
            
            # Test the unique constraint
            print("\n🔧 Testing unique constraint...")
            
            # Get a sample job_id and candidate_id from existing applications
            result = await session.execute(text("""
                SELECT job_id, candidate_id 
                FROM applications 
                LIMIT 1
            """))
            sample = result.fetchone()
            
            if sample:
                job_id, candidate_id = sample
                print(f"🎯 Attempting to create duplicate application:")
                print(f"   Job ID: {job_id}")
                print(f"   Candidate ID: {candidate_id}")
                
                try:
                    # Try to insert a duplicate application (with all required fields)
                    await session.execute(text("""
                        INSERT INTO applications (
                            job_id, candidate_id, status, applied_at, 
                            application_data, ai_analysis
                        )
                        VALUES (
                            :job_id, :candidate_id, 'applied', NOW(), 
                            '{}', '{}'
                        )
                    """), {
                        "job_id": job_id,
                        "candidate_id": candidate_id
                    })
                    await session.commit()
                    print("❌ ERROR: Duplicate application was allowed!")
                    
                except Exception as e:
                    if "uq_application_job_candidate" in str(e) or "duplicate key value violates unique constraint" in str(e):
                        print("✅ SUCCESS: Unique constraint prevented duplicate application!")
                        print(f"   Error: {str(e)[:100]}...")
                        await session.rollback()
                    else:
                        print(f"❌ Unexpected error: {str(e)[:100]}...")
                        await session.rollback()
            
            # Final count check
            result = await session.execute(text("""
                SELECT COUNT(*) as total_applications
                FROM applications
            """))
            final_count = result.scalar()
            print(f"\n📊 Final applications count: {final_count}")
            
            if final_count == initial_count:
                print("✅ Application count unchanged - no duplicates created!")
            else:
                print(f"⚠️  Application count changed by {final_count - initial_count}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_application_uniqueness())
