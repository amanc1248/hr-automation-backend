#!/usr/bin/env python3
"""
Migration script to add company_id to workflow_template table
"""
import sys
import os
import psycopg2
from urllib.parse import urlparse

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings

def migrate_workflow_templates():
    """Add company_id column to workflow_template table"""
    
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
            print("🔧 Adding company_id column to workflow_template table...")
            
            # Check if column already exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'workflow_template' 
                AND column_name = 'company_id'
            """)
            
            if cursor.fetchone():
                print("✅ company_id column already exists")
            else:
                # Add company_id column
                cursor.execute("""
                    ALTER TABLE workflow_template 
                    ADD COLUMN company_id UUID REFERENCES companies(id)
                """)
                print("✅ Added company_id column")
            
            # Get the first company (assuming there's at least one)
            cursor.execute("SELECT id FROM companies LIMIT 1")
            company = cursor.fetchone()
            
            if company:
                company_id = company[0]
                print(f"🏢 Found company with ID: {company_id}")
                
                # Update existing templates to use this company_id
                cursor.execute("""
                    UPDATE workflow_template 
                    SET company_id = %s 
                    WHERE company_id IS NULL
                """, (company_id,))
                
                print(f"✅ Updated {cursor.rowcount} existing templates with company_id")
                
                # Make company_id NOT NULL
                cursor.execute("""
                    ALTER TABLE workflow_template 
                    ALTER COLUMN company_id SET NOT NULL
                """)
                
                print("✅ Made company_id NOT NULL")
            else:
                print("❌ No companies found! Please create a company first.")
                return False
            
            # Commit changes
            conn.commit()
            print("🎉 Migration completed successfully!")
            return True
            
    except Exception as e:
        conn.rollback()
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        conn.close()

if __name__ == "__main__":
    print("🚀 Starting workflow template migration...")
    
    try:
        migrate_workflow_templates()
        print("✅ Migration completed!")
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        sys.exit(1)
