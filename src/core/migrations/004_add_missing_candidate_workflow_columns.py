"""
Migration: Add missing columns to candidate_workflow table
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
    """Add missing columns to candidate_workflow table"""
    
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
            print("🔄 Adding missing columns to candidate_workflow table...")
            
            # Check which columns are missing
            result = await session.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidate_workflow'
            """))
            existing_columns = {row[0] for row in result.fetchall()}
            
            required_columns = {
                'current_step_detail_id',
                'started_at', 
                'completed_at',
                'execution_log'
            }
            
            missing_columns = required_columns - existing_columns
            
            if not missing_columns:
                print("✅ All required columns already exist")
                return
            
            print(f"📝 Missing columns: {missing_columns}")
            
            # Add missing columns one by one
            if 'current_step_detail_id' in missing_columns:
                print("➕ Adding current_step_detail_id column...")
                await session.execute(text("""
                    ALTER TABLE candidate_workflow 
                    ADD COLUMN current_step_detail_id UUID REFERENCES workflow_step_detail(id)
                """))
            
            if 'started_at' in missing_columns:
                print("➕ Adding started_at column...")
                await session.execute(text("""
                    ALTER TABLE candidate_workflow 
                    ADD COLUMN started_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP
                """))
            
            if 'completed_at' in missing_columns:
                print("➕ Adding completed_at column...")
                await session.execute(text("""
                    ALTER TABLE candidate_workflow 
                    ADD COLUMN completed_at TIMESTAMP WITH TIME ZONE
                """))
            
            if 'execution_log' in missing_columns:
                print("➕ Adding execution_log column...")
                await session.execute(text("""
                    ALTER TABLE candidate_workflow 
                    ADD COLUMN execution_log JSONB NOT NULL DEFAULT '[]'::jsonb
                """))
            
            print("✅ Successfully added missing columns to candidate_workflow table")
            
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
