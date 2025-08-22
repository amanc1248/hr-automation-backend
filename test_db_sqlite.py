#!/usr/bin/env python3
"""
Test database connection with SQLite (for demo)
"""

import asyncio
import sys
import os
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

# Override database settings for SQLite
os.environ["DB_HOST"] = "localhost"
os.environ["DB_PORT"] = "5432"
os.environ["DB_USER"] = "test"
os.environ["DB_PASSWORD"] = "test"
os.environ["DB_NAME"] = "test.db"

async def main():
    """Test database connection with SQLite"""
    print("🧪 Testing Database Connection (SQLite Demo)")
    print("=" * 50)
    
    try:
        # Import our modules
        from core.config import settings, validate_settings
        
        # Override the database_url property for SQLite
        settings.database_url = "sqlite+aiosqlite:///./test.db"
        
        from core.database import check_database_connection
        
        print(f"📊 Demo Configuration:")
        print(f"   Using SQLite for testing")
        print(f"   Database: ./test.db")
        print()
        
        # Test database connection
        print("🔌 Testing SQLite connection...")
        success = await check_database_connection()
        
        if success:
            print("\n✅ Database connection test PASSED!")
            print("🎉 The system works - just need working Supabase!")
        else:
            print("\n❌ Database connection test FAILED!")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
