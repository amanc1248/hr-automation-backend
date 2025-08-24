#!/usr/bin/env python3
"""
Check actual table schema in database
"""

import asyncio
import os
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Load environment variables
load_dotenv()

async def check_table_schema():
    """Check the actual database schema"""
    
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
            print("🔍 Checking Database Schema")
            print("=" * 60)
            
            # Check candidate_workflow table columns
            result = await session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'candidate_workflow'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            
            print(f"📋 candidate_workflow table columns:")
            print("-" * 60)
            
            if columns:
                for col in columns:
                    print(f"📍 {col.column_name}")
                    print(f"   Type: {col.data_type}")
                    print(f"   Nullable: {col.is_nullable}")
                    print(f"   Default: {col.column_default}")
                    print("-" * 30)
            else:
                print("❌ Table not found or no columns")
            
            # Simple query to see what data exists
            try:
                result = await session.execute(text("""
                    SELECT COUNT(*) as count FROM candidate_workflow
                """))
                count = result.scalar()
                print(f"\n📊 Records in candidate_workflow: {count}")
                
                if count > 0:
                    # Show a sample record with all basic columns
                    result = await session.execute(text("""
                        SELECT id, name, category, job_id, workflow_template_id, candidate_id
                        FROM candidate_workflow 
                        LIMIT 1
                    """))
                    sample = result.fetchone()
                    if sample:
                        print(f"\n📋 Sample record:")
                        print(f"   ID: {sample.id}")
                        print(f"   Name: {sample.name}")
                        print(f"   Category: {sample.category}")
                        print(f"   Job ID: {sample.job_id}")
                        print(f"   Template ID: {sample.workflow_template_id}")
                        print(f"   Candidate ID: {sample.candidate_id}")
                        
            except Exception as e:
                print(f"❌ Error querying candidate_workflow: {e}")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(check_table_schema())
