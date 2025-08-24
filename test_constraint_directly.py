#!/usr/bin/env python3
"""
Test unique constraint directly using the model
"""

import asyncio
import os
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

# Load environment variables
load_dotenv()

# Add src to path so we can import models
import sys
sys.path.append('src')

from models.candidate import Application

async def test_constraint():
    """Test unique constraint using the Application model"""
    
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
            # Get an existing application to try to duplicate
            existing_app = await session.get(Application, "0f6dca9a-92ff-4aff-b2b7-0b0cc2db3892")  # Use a real ID
            if not existing_app:
                # Get the first application
                from sqlalchemy import select
                result = await session.execute(select(Application).limit(1))
                existing_app = result.scalar_one_or_none()
            
            if existing_app:
                print(f"🎯 Attempting to duplicate application:")
                print(f"   Job ID: {existing_app.job_id}")
                print(f"   Candidate ID: {existing_app.candidate_id}")
                
                # Try to create a duplicate application using the model
                duplicate_app = Application(
                    job_id=existing_app.job_id,
                    candidate_id=existing_app.candidate_id,
                    status="applied",
                    applied_at=datetime.utcnow(),
                    source="test"
                )
                
                session.add(duplicate_app)
                
                try:
                    await session.commit()
                    print("❌ ERROR: Duplicate application was created!")
                except IntegrityError as e:
                    if "uq_application_job_candidate" in str(e) or "duplicate key" in str(e).lower():
                        print("✅ SUCCESS: Unique constraint prevented duplicate!")
                        print(f"   Error: {str(e)[:150]}...")
                    else:
                        print(f"❌ Different integrity error: {str(e)[:150]}...")
                    await session.rollback()
            else:
                print("No existing applications found to test with")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

if __name__ == "__main__":
    asyncio.run(test_constraint())
