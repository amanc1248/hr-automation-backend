#!/usr/bin/env python3
"""
Clear Candidate Data Script
===========================

This script clears data from specific candidate-related tables:
- applications
- candidate_workflow  
- candidate_workflow_executions
- candidates

PRESERVES everything else including:
- workflow_step (workflow definitions)
- workflow_template (workflow templates)
- workflow_step_detail (workflow configurations)
- jobs (job postings)
- users, companies (user accounts)
- gmail_configs (email settings)

Use this when you want to clear candidate data but keep workflow and job configurations.
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

# Tables to clear - candidate-related data only
CANDIDATE_TABLES = [
    "workflow_approvals",         # Individual approval decisions
    "workflow_approval_requests", # Approval requests sent to approvers
    "applications",               # Candidate job applications
    "candidate_workflow",         # Workflow instances for candidates
    "candidate_workflow_executions", # Step execution records for candidates
    "candidates"                  # Candidate records
]

async def clear_candidate_data():
    """Clear candidate-related data from specified tables"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("🗑️  Candidate Data Cleanup")
    print("=" * 60)
    print("⚠️  This will clear CANDIDATE DATA from specific tables")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    
    async with async_session() as session:
        try:
            # Show current data status
            print(f"\n📊 Current data in candidate tables:")
            
            table_counts = {}
            for table_name in CANDIDATE_TABLES:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    row_count = count_result.scalar()
                    table_counts[table_name] = row_count
                    print(f"   📋 {table_name}: {row_count} rows")
                except Exception as e:
                    print(f"   ❓ {table_name}: table not found or error ({e})")
                    table_counts[table_name] = 0
            
            total_rows = sum(table_counts.values())
            
            if total_rows == 0:
                print(f"\n✅ All candidate tables are already empty!")
                return
            
            print(f"\n⚠️  Total rows to be deleted: {total_rows}")
            print(f"📋 Tables to clear:")
            for table_name in CANDIDATE_TABLES:
                if table_counts.get(table_name, 0) > 0:
                    print(f"   ❌ {table_name}: {table_counts[table_name]} rows")
            
            print(f"\n✅ PRESERVED (not affected):")
            print(f"   ✅ workflow_step (workflow definitions)")
            print(f"   ✅ workflow_template (workflow templates)")
            print(f"   ✅ workflow_step_detail (workflow configurations)")
            print(f"   ✅ jobs (job postings)")
            print(f"   ✅ users, companies (user accounts)")
            print(f"   ✅ gmail_configs (email settings)")
            
            # Get confirmation
            print("\n" + "⚠️ " * 20)
            print("This will delete candidate data but preserve workflow configurations!")
            print("⚠️ " * 20)
            
            confirmation = input("\nType 'CLEAR_CANDIDATE_DATA' to proceed: ")
            if confirmation != 'CLEAR_CANDIDATE_DATA':
                print("❌ Operation cancelled")
                return
            
            print(f"\n🚀 Starting candidate data cleanup...")
            
            # Disable foreign key checks temporarily for easier deletion
            print(f"🔧 Disabling foreign key constraints...")
            await session.execute(text("SET session_replication_role = replica;"))
            
            cleared_count = 0
            total_deleted = 0
            
            # Clear tables in order (respecting foreign key dependencies)
            # workflow_approvals first, then workflow_approval_requests, then applications, candidate_workflow_executions, candidate_workflow, candidates
            ordered_tables = ["workflow_approvals", "workflow_approval_requests", "applications", "candidate_workflow_executions", "candidate_workflow", "candidates"]
            
            for table_name in ordered_tables:
                if table_name in CANDIDATE_TABLES and table_counts.get(table_name, 0) > 0:
                    try:
                        print(f"   🗑️  Clearing {table_name}...")
                        
                        # Delete all rows from table
                        delete_query = text(f"DELETE FROM {table_name}")
                        result = await session.execute(delete_query)
                        
                        deleted_rows = table_counts[table_name]  # We know the count from before
                        total_deleted += deleted_rows
                        cleared_count += 1
                        
                        print(f"   ✅ Cleared {table_name}: {deleted_rows} rows deleted")
                        
                    except Exception as e:
                        print(f"   ❌ Error clearing {table_name}: {e}")
                        # Continue with other tables
            
            # Re-enable foreign key checks
            print(f"🔧 Re-enabling foreign key constraints...")
            await session.execute(text("SET session_replication_role = DEFAULT;"))
            
            # Reset sequences for cleared tables
            print(f"🔄 Resetting sequences...")
            for table_name in ordered_tables:
                if table_counts.get(table_name, 0) > 0:
                    try:
                        # Check if table has an id column with sequence
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
                    except Exception:
                        # Sequence reset is not critical
                        pass
            
            # Commit all changes
            await session.commit()
            
            print(f"\n" + "=" * 60)
            print("📊 CANDIDATE DATA CLEANUP SUMMARY")
            print("=" * 60)
            print(f"✅ Tables cleared: {cleared_count}")
            print(f"🗑️  Total rows deleted: {total_deleted}")
            
            # Verify tables are empty
            print(f"\n🎯 VERIFICATION:")
            for table_name in CANDIDATE_TABLES:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    final_count = count_result.scalar()
                    status = "✅" if final_count == 0 else "❌"
                    print(f"   {status} {table_name}: {final_count} rows remaining")
                except Exception as e:
                    print(f"   ❓ {table_name}: verification error ({e})")
            
            # Show preserved data
            print(f"\n✅ PRESERVED DATA (sample counts):")
            preserved_tables = ["workflow_step", "jobs", "users", "companies"]
            for table_name in preserved_tables:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    count = count_result.scalar()
                    print(f"   ✅ {table_name}: {count} rows preserved")
                except Exception:
                    print(f"   ❓ {table_name}: table not found")
            
            print(f"\n🎉 Candidate data cleanup completed successfully!")
            print(f"🏗️  System ready for new candidate data with preserved configurations")
            
        except Exception as e:
            print(f"❌ Error during cleanup: {e}")
            await session.rollback()
            import traceback
            traceback.print_exc()
            raise
        finally:
            await engine.dispose()

async def show_table_status():
    """Show current status of candidate tables"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("\n📊 Current Table Status:")
            print("-" * 40)
            
            all_tables = CANDIDATE_TABLES + ["workflow_step", "jobs", "users", "companies"]
            
            for table_name in all_tables:
                try:
                    count_query = text(f"SELECT COUNT(*) FROM {table_name}")
                    count_result = await session.execute(count_query)
                    row_count = count_result.scalar()
                    
                    if table_name in CANDIDATE_TABLES:
                        status = "🎯" if row_count > 0 else "✅"
                        note = " (will be cleared)" if row_count > 0 else " (already empty)"
                    else:
                        status = "✅"
                        note = " (preserved)"
                    
                    print(f"   {status} {table_name}: {row_count} rows{note}")
                except Exception:
                    print(f"   ❓ {table_name}: table not found")
                    
        except Exception as e:
            print(f"❌ Error checking status: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    print("🗑️  Candidate Data Cleanup Tool")
    print("=" * 60)
    print("This tool will clear candidate data while preserving workflow configurations")
    
    try:
        # Show current status
        asyncio.run(show_table_status())
        
        # Perform cleanup
        asyncio.run(clear_candidate_data())
        
        # Show final status
        asyncio.run(show_table_status())
        
    except KeyboardInterrupt:
        print("\n\n🛑 Cleanup cancelled by user")
    except Exception as e:
        print(f"\n❌ Cleanup failed: {e}")
        print("💡 Make sure database connection is working")
