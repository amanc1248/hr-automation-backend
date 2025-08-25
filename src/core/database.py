from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from typing import AsyncGenerator
import logging

from .config import settings

logger = logging.getLogger(__name__)

print(f"Database URL: {settings.async_database_url[:50]}...")

# Create async engine for Railway PostgreSQL
engine = create_async_engine(
    settings.async_database_url,  # Use async version
    echo=False,  # Disable SQL query logging for performance
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,  # Verify connections before use
    pool_recycle=300,  # Recycle connections every 5 minutes
)

# Create async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False
)

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Database dependency for FastAPI"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

async def check_database_connection():
    """Check if database connection works"""
    print(f"🔍 Railway PostgreSQL Connection Test")
    print(f"   URL: {settings.async_database_url[:50]}...")
    print()
    
    try:
        print("Database connection test...")
        
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text
            
            # Test simple query
            result = await session.execute(text("SELECT 1 as test"))
            test_value = result.scalar()
            
            if test_value == 1:
                print("✅ Database connection successful!")
                
                # Test version query
                version_result = await session.execute(text("SELECT version()"))
                version = version_result.scalar()
                print(f"✅ Database version: {version[:60]}...")
                
                # Test current database
                db_result = await session.execute(text("SELECT current_database()"))
                current_db = db_result.scalar()
                print(f"✅ Current database: {current_db}")
                
                return True
            else:
                print(f"❌ Unexpected result: {test_value}")
                return False
                
    except Exception as e:
        print(f"❌ Connection failed: {str(e)[:200]}...")
        return False

async def close_database():
    """Close database connections"""
    try:
        await engine.dispose()
        print("✅ Database connections closed")
    except Exception as e:
        print(f"❌ Error closing database: {e}")
