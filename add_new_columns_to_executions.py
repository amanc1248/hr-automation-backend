#!/usr/bin/env python3
"""
Migration script to add new columns to candidate_workflow_executions table.
This script adds the missing fields from workflow_step_detail and workflow_step tables.
"""

import asyncio
import asyncpg
import os
from datetime import datetime

async def migrate_database():
    """Add new columns to candidate_workflow_executions table"""
    
    # Database connection details
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("❌ DATABASE_URL environment variable not set")
        return
    
    try:
        # Connect to database
        print("🔌 Connecting to database...")
        conn = await asyncpg.connect(database_url)
        print("✅ Connected to database successfully")
        
        # Check if columns already exist
        print("🔍 Checking existing columns...")
        columns_result = await conn.fetch("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'candidate_workflow_executions'
        """)
        existing_columns = {row['column_name'] for row in columns_result}
        print(f"📋 Existing columns: {sorted(existing_columns)}")
        
        # Define new columns to add
        new_columns = [
            ("order_number", "INTEGER NOT NULL DEFAULT 0"),
            ("auto_start", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("required_human_approval", "BOOLEAN NOT NULL DEFAULT FALSE"),
            ("number_of_approvals_needed", "INTEGER"),
            ("approvers", "JSON NOT NULL DEFAULT '[]'"),
            ("step_name", "TEXT NOT NULL DEFAULT 'Unknown Step'"),
            ("step_type", "TEXT NOT NULL DEFAULT 'unknown'"),
            ("step_description", "TEXT"),
            ("delay_in_seconds", "INTEGER")
        ]
        
        # Add new columns
        print("🔧 Adding new columns...")
        for column_name, column_definition in new_columns:
            if column_name not in existing_columns:
                try:
                    await conn.execute(f"""
                        ALTER TABLE candidate_workflow_executions 
                        ADD COLUMN {column_name} {column_definition}
                    """)
                    print(f"✅ Added column: {column_name}")
                except Exception as e:
                    print(f"❌ Failed to add column {column_name}: {e}")
            else:
                print(f"⏭️ Column {column_name} already exists, skipping")
        
        # Add indexes for performance
        print("🔧 Adding indexes...")
        indexes_to_add = [
            ("idx_executions_order_number", "order_number"),
            ("idx_executions_auto_start", "auto_start"),
            ("idx_executions_required_approval", "required_human_approval"),
            ("idx_executions_step_type", "step_type")
        ]
        
        for index_name, column_name in indexes_to_add:
            try:
                await conn.execute(f"""
                    CREATE INDEX IF NOT EXISTS {index_name} 
                    ON candidate_workflow_executions ({column_name})
                """)
                print(f"✅ Added index: {index_name}")
            except Exception as e:
                print(f"❌ Failed to add index {index_name}: {e}")
        
        print("🎉 Migration completed successfully!")
        
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        if 'conn' in locals():
            await conn.close()
            print("🔌 Database connection closed")

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    print("=" * 50)
    asyncio.run(migrate_database())
    print("=" * 50)
    print("🏁 Migration script completed")
