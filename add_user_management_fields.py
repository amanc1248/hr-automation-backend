#!/usr/bin/env python3
"""
Database migration to add user management fields to profiles table
"""

import asyncio
import asyncpg
import sys
import os

# Add src directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings

async def migrate_database():
    """Add user management fields to profiles table"""
    
    print("🔄 Adding user management fields to profiles table...")
    
    try:
        # Connect to database
        conn = await asyncpg.connect(settings.DATABASE_URL)
        
        # Add new columns to profiles table
        migrations = [
            # Add password hash for direct authentication
            """
            ALTER TABLE profiles 
            ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255);
            """,
            
            # Add user management tracking fields
            """
            ALTER TABLE profiles 
            ADD COLUMN IF NOT EXISTS first_login_at TIMESTAMP;
            """,
            
            """
            ALTER TABLE profiles 
            ADD COLUMN IF NOT EXISTS must_change_password BOOLEAN DEFAULT FALSE;
            """,
            
            """
            ALTER TABLE profiles 
            ADD COLUMN IF NOT EXISTS password_changed_at TIMESTAMP;
            """,
            
            """
            ALTER TABLE profiles 
            ADD COLUMN IF NOT EXISTS created_by UUID REFERENCES profiles(id);
            """,
            
            # Update existing users to not require password change (for existing admin)
            """
            UPDATE profiles 
            SET must_change_password = FALSE 
            WHERE must_change_password IS NULL;
            """,
            
            # Set default for must_change_password
            """
            ALTER TABLE profiles 
            ALTER COLUMN must_change_password SET DEFAULT FALSE;
            """,
            
            """
            ALTER TABLE profiles 
            ALTER COLUMN must_change_password SET NOT NULL;
            """
        ]
        
        for i, migration in enumerate(migrations, 1):
            print(f"  📝 Running migration {i}/{len(migrations)}...")
            await conn.execute(migration)
            print(f"  ✅ Migration {i} completed")
        
        await conn.close()
        print("✅ User management fields added successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(migrate_database())
