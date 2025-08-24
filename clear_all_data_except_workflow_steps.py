#!/usr/bin/env python3
"""
Clear All Data Except Workflow Steps
====================================

This script clears all data from the database except the workflow_step table.
Useful for resetting the system while preserving the core workflow configuration.

PRESERVES:
- workflow_step table (core workflow definitions)

CLEARS:
- All user/company/auth data
- All job/candidate/application data  
- All workflow instance data
- All email/configuration data

Use with caution - this will delete all operational data!
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Table clearing configuration
TABLES_TO_CLEAR = [
    # User & Company Data
    "user_roles",
    "profiles", 
    "users",
    "companies",
    
    # Job & Candidate Data
    "applications",
    "candidates",
    "jobs",
    
    # Workflow Instance Data (preserve definitions)
    "candidate_workflow",
    "workflow_step_detail", 
    "workflow_template",
    
    # Email & Configuration Data
    "gmail_configs",
    "email_sync_logs",
    
    # Any other operational tables
    "sessions",
    "tokens"
]

TABLES_TO_PRESERVE = [
    "workflow_step"  # Core workflow definitions
]

async def clear_database_data():
    """Clear all data except workflow_step table"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("🗑️  Database Data Cleanup")
    print("=" * 60)
    print("⚠️  WARNING: This will delete ALL data except workflow_step table!")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    
    # Get confirmation
    print(f"\n📋 Tables to be cleared: {len(TABLES_TO_CLEAR)}")
    for table in TABLES_TO_CLEAR:
        print(f"   ❌ {table}")
    
    print(f"\n✅ Tables to be preserved: {len(TABLES_TO_PRESERVE)}")
    for table in TABLES_TO_PRESERVE:
        print(f"   ✅ {table}")
    
    print("\n" + "⚠️ " * 20)
    print("This action cannot be undone!")
    print("⚠️ " * 20)
    
    confirmation = input("\nType 'CLEAR_ALL_DATA' to proceed: ")
    if confirmation != 'CLEAR_ALL_DATA':
        print("❌ Operation cancelled")
        return
    
    async with async_session() as session:
        try:
            print(f"\n🚀 Starting database cleanup...")
            
            # First, get list of existing tables
            existing_tables_query = text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """)
            
            result = await session.execute(existing_tables_query)
            existing_tables = [row[0] for row in result.fetchall()]
            
            print(f"📊 Found {len(existing_tables)} tables in database")
            
            # Disable foreign key checks temporarily
            print(f"\n🔧 Disabling foreign key constraints...")
            await session.execute(text("SET session_replication_role = replica;"))
            
            cleared_count = 0
            preserved_count = 0
            not_found_count = 0
            
            # Clear each table
            for table_name in TABLES_TO_CLEAR:
                if table_name in existing_tables:
                    try:
                        # Get row count before deletion
                        count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                        count_result = await session.execute(count_query)
                        row_count = count_result.scalar()
                        
                        if row_count > 0:
                            # Clear the table
                            delete_query = text(f"DELETE FROM {table_name}")
                            await session.execute(delete_query)
                            print(f"   🗑️  Cleared {table_name}: {row_count} rows deleted")
                            cleared_count += 1
                        else:
                            print(f"   ⭕ {table_name}: already empty")
                    except Exception as e:
                        print(f"   ⚠️  Warning: Could not clear {table_name}: {e}")
                else:
                    print(f"   ❓ {table_name}: table not found")
                    not_found_count += 1
            
            # Show preserved tables
            for table_name in TABLES_TO_PRESERVE:
                if table_name in existing_tables:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    row_count = count_result.scalar()
                    print(f"   ✅ Preserved {table_name}: {row_count} rows kept")
                    preserved_count += 1
                else:
                    print(f"   ❓ {table_name}: table not found (would be preserved)")
            
            # Re-enable foreign key checks
            print(f"\n🔧 Re-enabling foreign key constraints...")
            await session.execute(text("SET session_replication_role = DEFAULT;"))
            
            # Reset sequences for tables that were cleared
            print(f"\n🔄 Resetting sequences...")
            for table_name in TABLES_TO_CLEAR:
                if table_name in existing_tables:
                    try:
                        # Check if table has an id column and sequence
                        seq_check_query = text(f"""
                            SELECT column_default 
                            FROM information_schema.columns 
                            WHERE table_name = '{table_name}' 
                            AND column_name = 'id'
                            AND column_default LIKE 'nextval%'
                        """)
                        seq_result = await session.execute(seq_check_query)
                        seq_info = seq_result.fetchone()
                        
                        if seq_info:
                            # Extract sequence name and reset it
                            seq_name = seq_info[0].split("'")[1]
                            reset_query = text(f"ALTER SEQUENCE {seq_name} RESTART WITH 1")
                            await session.execute(reset_query)
                            print(f"   🔄 Reset sequence for {table_name}")
                    except Exception as e:
                        # Sequence reset is not critical, just log warning
                        pass
            
            # Commit all changes
            await session.commit()
            
            print(f"\n" + "=" * 60)
            print("📊 DATABASE CLEANUP SUMMARY")
            print("=" * 60)
            print(f"✅ Tables cleared: {cleared_count}")
            print(f"🛡️  Tables preserved: {preserved_count}")
            print(f"❓ Tables not found: {not_found_count}")
            
            # Verify workflow_step preservation
            workflow_count_query = text("SELECT COUNT(*) FROM workflow_step WHERE is_deleted = FALSE")
            workflow_result = await session.execute(workflow_count_query)
            workflow_count = workflow_result.scalar()
            
            print(f"\n🎯 VERIFICATION:")
            print(f"✅ Workflow steps preserved: {workflow_count}")
            
            if workflow_count > 0:
                # Show preserved workflow steps
                steps_query = text("SELECT name, step_type FROM workflow_step WHERE is_deleted = FALSE ORDER BY created_at")
                steps_result = await session.execute(steps_query)
                steps = steps_result.fetchall()
                
                print(f"📋 Preserved workflow steps:")
                for i, (name, step_type) in enumerate(steps, 1):
                    print(f"   {i}. {name} ({step_type})")
            
            print(f"\n🎉 Database cleanup completed successfully!")
            print(f"🏗️  System is ready for fresh data with preserved workflow configuration")
            
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            await session.rollback()
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()

async def show_current_data_status():
    """Show current data status in key tables"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("\n📊 Current Database Status:")
            print("-" * 40)
            
            key_tables = [
                "companies", "users", "jobs", "candidates", 
                "applications", "candidate_workflow", "workflow_step"
            ]
            
            for table_name in key_tables:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    row_count = count_result.scalar()
                    
                    status = "✅" if table_name == "workflow_step" else "📊"
                    print(f"   {status} {table_name}: {row_count} rows")
                except Exception:
                    print(f"   ❓ {table_name}: table not found")
                    
        except Exception as e:
            print(f"❌ Error checking status: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    print("🗑️  HR Automation Database Cleanup Tool")
    print("=" * 60)
    print("This tool will clear all data except workflow_step definitions")
    
    try:
        # Show current status
        asyncio.run(show_current_data_status())
        
        # Perform cleanup
        asyncio.run(clear_database_data())
        
        # Show final status
        asyncio.run(show_current_data_status())
        
    except KeyboardInterrupt:
        print("\n\n🛑 Cleanup cancelled by user")
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        print("💡 Make sure database connection is working")
