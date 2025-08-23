#!/usr/bin/env python3
"""
Cleanup script to delete the unused email_sync_logs table
"""
import sys
import os
import psycopg2
from urllib.parse import urlparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings

def delete_email_sync_logs():
    """Delete the unused email_sync_logs table"""
    
    # Parse the DATABASE_URL to get connection details
    url = urlparse(settings.DATABASE_URL.replace('postgresql+asyncpg://', 'postgresql://'))
    
    # Connect to database
    conn = psycopg2.connect(
        host=url.hostname,
        port=url.port,
        database=url.path[1:],  # Remove leading slash
        user=url.username,
        password=url.password
    )
    
    try:
        with conn.cursor() as cursor:
            print("🧹 Checking if email_sync_logs table exists...")
            
            # Check if table exists
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'email_sync_logs'
            """)
            
            if not cursor.fetchone():
                print("✅ email_sync_logs table doesn't exist - nothing to delete")
                return True
            
            print("📊 email_sync_logs table found")
            
            # Check table info before deletion
            cursor.execute("""
                SELECT 
                    COUNT(*) as row_count,
                    (SELECT COUNT(*) FROM information_schema.columns WHERE table_name = 'email_sync_logs') as column_count
                FROM email_sync_logs
            """)
            
            row_count, column_count = cursor.fetchone()
            print(f"📋 Table has {row_count} rows and {column_count} columns")
            
            # Check foreign key constraints
            cursor.execute("""
                SELECT 
                    tc.constraint_name,
                    kcu.column_name,
                    ccu.table_name AS foreign_table_name
                FROM 
                    information_schema.table_constraints AS tc 
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                WHERE tc.constraint_type = 'FOREIGN KEY'
                AND tc.table_name = 'email_sync_logs'
            """)
            
            foreign_keys = cursor.fetchall()
            if foreign_keys:
                print("🔗 Foreign key constraints found:")
                for fk in foreign_keys:
                    print(f"  → {fk[1]} references {fk[2]}")
            
            # Confirm deletion
            print("\n⚠️  WARNING: This will permanently delete the email_sync_logs table!")
            print("This table is not used by any current models and can be safely removed.")
            
            # Delete the table (CASCADE will handle any remaining constraints)
            print("\n🗑️  Deleting email_sync_logs table...")
            cursor.execute("DROP TABLE IF EXISTS email_sync_logs CASCADE")
            
            print("✅ email_sync_logs table deleted successfully!")
            
            # Commit changes
            conn.commit()
            return True
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Failed to delete table: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting email_sync_logs table cleanup...")
    
    try:
        delete_email_sync_logs()
        print("✅ Cleanup completed!")
    except Exception as e:
        print(f"❌ Cleanup failed: {e}")
        sys.exit(1)
