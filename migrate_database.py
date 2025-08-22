#!/usr/bin/env python3
"""
Database migration runner
"""

import asyncio
import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

async def main():
    """Run database migrations"""
    print("🚀 HR Automation - Database Migration")
    print("=" * 40)
    
    try:
        from core.config import settings, validate_settings
        from core.database import check_database_connection
        from core.migrations import create_all_tables, init_default_data, check_database_schema
        
        # Validate configuration
        print("🔧 Validating configuration...")
        validate_settings()
        
        # Test database connection
        print("🔌 Testing database connection...")
        db_success = await check_database_connection()
        
        if not db_success:
            print("❌ Database connection failed. Please check your configuration.")
            return False
        
        # Check current schema
        print("\n�� Current database schema:")
        existing_tables = await check_database_schema()
        
        if existing_tables:
            print(f"\n⚠️  Found {len(existing_tables)} existing tables.")
            response = input("Do you want to continue? This will create missing tables. (y/N): ")
            if response.lower() != 'y':
                print("❌ Migration cancelled by user.")
                return False
        
        # Create tables
        print("\n🔧 Creating database tables...")
        success = await create_all_tables()
        
        if not success:
            print("❌ Failed to create tables.")
            return False
        
        # Initialize default data
        print("\n📊 Initializing default data...")
        success = await init_default_data()
        
        if not success:
            print("❌ Failed to initialize default data.")
            return False
        
        # Final schema check
        print("\n📋 Final database schema:")
        final_tables = await check_database_schema()
        
        print(f"\n🎉 SUCCESS: Database migration completed!")
        print(f"✅ Created {len(final_tables)} tables")
        print("✅ Initialized default roles and email templates")
        print("✅ Database is ready for the HR Automation system!")
        
        return True
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
