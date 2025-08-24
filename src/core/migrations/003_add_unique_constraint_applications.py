"""
Migration: Add unique constraint to applications table
Date: 2025-08-24
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def run_migration():
    """Add unique constraint on job_id + candidate_id to applications table"""
    
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
            # Check if the constraint already exists
            result = await session.execute(text("""
                SELECT constraint_name 
                FROM information_schema.table_constraints 
                WHERE table_name = 'applications' 
                AND constraint_name = 'uq_application_job_candidate'
                AND constraint_type = 'UNIQUE'
            """))
            
            if result.fetchone():
                print("✅ Unique constraint already exists on applications table")
                return
            
            print("🔄 Adding unique constraint to applications table...")
            
            # First, check for duplicate applications that would violate the constraint
            result = await session.execute(text("""
                SELECT job_id, candidate_id, COUNT(*) as count
                FROM applications 
                GROUP BY job_id, candidate_id 
                HAVING COUNT(*) > 1
                ORDER BY count DESC
            """))
            
            duplicates = result.fetchall()
            
            if duplicates:
                print(f"⚠️  Found {len(duplicates)} duplicate job/candidate combinations:")
                for dup in duplicates:
                    print(f"   Job: {dup.job_id}, Candidate: {dup.candidate_id}, Count: {dup.count}")
                
                print("🧹 Removing duplicate applications (keeping the earliest one)...")
                
                # Remove duplicates, keeping only the earliest application for each job/candidate combo
                await session.execute(text("""
                    DELETE FROM applications a1
                    USING applications a2
                    WHERE a1.job_id = a2.job_id 
                    AND a1.candidate_id = a2.candidate_id 
                    AND a1.applied_at > a2.applied_at
                """))
                
                removed_count = session.info.get('rowcount', 0)
                print(f"🗑️  Removed {removed_count} duplicate applications")
            
            # Add the unique constraint
            await session.execute(text("""
                ALTER TABLE applications 
                ADD CONSTRAINT uq_application_job_candidate 
                UNIQUE (job_id, candidate_id)
            """))
            
            print("✅ Successfully added unique constraint to applications table")
            
            # Commit the transaction
            await session.commit()
            
        except Exception as e:
            print(f"❌ Error during migration: {e}")
            await session.rollback()
            raise
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(run_migration())
