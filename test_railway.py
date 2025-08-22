#!/usr/bin/env python3
"""
Test Railway PostgreSQL connection
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def test_railway_connection():
    """Test Railway PostgreSQL connection"""
    print("🚀 Testing Railway PostgreSQL Connection")
    print("=" * 40)
    
    try:
        from core.config import settings, validate_settings
        from core.database import check_database_connection
        
        print("🔧 Validating configuration...")
        validate_settings()
        
        print(f"📊 Database URL: {settings.DATABASE_URL[:50]}...")
        print()
        
        print("🔌 Testing database connection...")
        success = await check_database_connection()
        
        if success:
            print("\n🎉 SUCCESS: Railway PostgreSQL is working!")
            print("✅ Ready to build the authentication system!")
            return True
        else:
            print("\n❌ FAILED: Connection issues detected")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    asyncio.run(test_railway_connection())
