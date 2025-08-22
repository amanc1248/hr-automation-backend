#!/usr/bin/env python3
"""
Test database connection with individual DB components
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def main():
    """Test database connection"""
    print("🧪 Testing Database Connection (Individual Components)")
    print("=" * 50)
    
    try:
        # Import our modules
        from core.config import settings, validate_settings
        from core.database import check_database_connection
        
        # Show current settings
        print(f"📊 Database Configuration:")
        print(f"   DB_HOST: {settings.DB_HOST}")
        print(f"   DB_PORT: {settings.DB_PORT}")
        print(f"   DB_USER: {settings.DB_USER}")
        print(f"   DB_NAME: {settings.DB_NAME}")
        print(f"   Built URL: {settings.database_url.split('@')[0]}@***")
        print()
        
        # Validate settings
        print("🔧 Validating settings...")
        validate_settings()
        print()
        
        # Test database connection
        print("🔌 Testing database connection...")
        success = await check_database_connection()
        
        if success:
            print("\n✅ Database connection test PASSED!")
            print("�� Ready to build the authentication system!")
        else:
            print("\n❌ Database connection test FAILED!")
            print("💡 Please check your Supabase project status")
            
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
