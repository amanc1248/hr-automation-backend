#!/usr/bin/env python3
"""
Test raw asyncpg connection to Supabase pooler
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_raw_connection():
    """Test direct asyncpg connection"""
    print("🧪 Testing Raw AsyncPG Connection to Supabase Pooler")
    print("=" * 55)
    
    try:
        from core.config import settings
        
        print(f"📊 Connection Details:")
        print(f"   Host: {settings.DB_HOST}")
        print(f"   Port: {settings.DB_PORT}")
        print(f"   User: {settings.DB_USER}")
        print(f"   Database: {settings.DB_NAME}")
        print()
        
        # Test raw asyncpg connection with correct parameters
        print("🔌 Testing raw asyncpg connection...")
        
        conn = await asyncpg.connect(
            host=settings.DB_HOST,
            port=settings.DB_PORT,
            user=settings.DB_USER,
            password=settings.DB_PASSWORD,
            database=settings.DB_NAME,
            # Correct asyncpg parameters for pooler
            statement_cache_size=0,
            command_timeout=60
        )
        
        # Test simple query
        result = await conn.fetchval("SELECT 1")
        
        # Test a more complex query
        version = await conn.fetchval("SELECT version()")
        
        await conn.close()
        
        if result == 1:
            print("✅ Raw asyncpg connection successful!")
            print(f"✅ Database version: {version[:50]}...")
            print("🎉 Supabase pooler is working!")
            return True
        else:
            print(f"❌ Unexpected result: {result}")
            return False
            
    except Exception as e:
        print(f"❌ Raw connection failed: {e}")
        return False

async def main():
    """Main test function"""
    success = await test_raw_connection()
    
    if success:
        print("\n🎯 Next Steps:")
        print("   1. Raw connection works!")
        print("   2. Need to fix SQLAlchemy configuration")
        print("   3. Ready to build authentication system!")
    else:
        print("\n💡 Troubleshooting:")
        print("   1. Check Supabase project status")
        print("   2. Verify credentials in .env")
        print("   3. Check network connectivity")

if __name__ == "__main__":
    asyncio.run(main())
