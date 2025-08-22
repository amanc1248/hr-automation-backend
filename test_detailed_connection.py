#!/usr/bin/env python3
"""
Detailed connection test with better error handling
"""

import asyncio
import asyncpg
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_detailed_connection():
    """Test connection with detailed error reporting"""
    print("🧪 Detailed Supabase Pooler Connection Test")
    print("=" * 45)
    
    try:
        from core.config import settings
        
        print(f"📊 Connection Details:")
        print(f"   Host: {settings.DB_HOST}")
        print(f"   Port: {settings.DB_PORT}")
        print(f"   User: {settings.DB_USER}")
        print(f"   Database: {settings.DB_NAME}")
        print(f"   Password: {'*' * len(settings.DB_PASSWORD)}")
        print()
        
        print("🔌 Attempting connection...")
        
        # Test connection with timeout
        conn = await asyncio.wait_for(
            asyncpg.connect(
                host=settings.DB_HOST,
                port=settings.DB_PORT,
                user=settings.DB_USER,
                password=settings.DB_PASSWORD,
                database=settings.DB_NAME,
                statement_cache_size=0,
                command_timeout=30
            ),
            timeout=10.0
        )
        
        print("✅ Connection established!")
        
        # Test simple query
        print("🔍 Testing simple query...")
        result = await conn.fetchval("SELECT 1")
        print(f"✅ Simple query result: {result}")
        
        # Test version query
        print("🔍 Testing version query...")
        version = await conn.fetchval("SELECT version()")
        print(f"✅ Database version: {version[:80]}...")
        
        # Test current user
        print("🔍 Testing current user...")
        current_user = await conn.fetchval("SELECT current_user")
        print(f"✅ Current user: {current_user}")
        
        await conn.close()
        print("✅ Connection closed successfully")
        
        return True
            
    except asyncio.TimeoutError:
        print("❌ Connection timeout (10 seconds)")
        return False
    except asyncpg.InvalidAuthorizationSpecificationError as e:
        print(f"❌ Authentication failed: {e}")
        return False
    except asyncpg.InvalidCatalogNameError as e:
        print(f"❌ Database not found: {e}")
        return False
    except asyncpg.ConnectionDoesNotExistError as e:
        print(f"❌ Connection error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main test function"""
    print("🚀 Starting detailed connection test...\n")
    
    success = await test_detailed_connection()
    
    print("\n" + "=" * 45)
    if success:
        print("🎉 SUCCESS: Supabase connection is working!")
        print("✅ Ready to build the authentication system!")
    else:
        print("❌ FAILED: Connection issues detected")
        print("💡 Check your Supabase project and credentials")

if __name__ == "__main__":
    asyncio.run(main())
