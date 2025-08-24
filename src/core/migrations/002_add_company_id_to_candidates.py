"""
Migration: Add company_id to candidates table
Date: 2025-08-24
"""

import psycopg2
import os
from urllib.parse import urlparse

def run_migration():
    """Add company_id column to candidates table"""
    
    # Get database URL from environment
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    
    # Parse the database URL
    parsed = urlparse(database_url)
    
    # Connect to database
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path[1:],  # Remove leading slash
        user=parsed.username,
        password=parsed.password
    )
    
    try:
        with conn.cursor() as cursor:
            # Check if the column already exists
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'candidates' AND column_name = 'company_id'
            """)
            
            if cursor.fetchone():
                print("✅ company_id column already exists in candidates table")
                return
            
            print("🔄 Adding company_id column to candidates table...")
            
            # Add the company_id column
            cursor.execute("""
                ALTER TABLE candidates 
                ADD COLUMN company_id UUID REFERENCES companies(id)
            """)
            
            # Get the first company ID to use as default
            cursor.execute("SELECT id FROM companies LIMIT 1")
            company_result = cursor.fetchone()
            
            if company_result:
                company_id = company_result[0]
                print(f"📝 Setting default company_id to: {company_id}")
                
                # Update existing candidates with the first company ID
                cursor.execute("""
                    UPDATE candidates 
                    SET company_id = %s 
                    WHERE company_id IS NULL
                """, (company_id,))
                
                updated_count = cursor.rowcount
                print(f"📊 Updated {updated_count} existing candidates")
            
            # Make the column NOT NULL after setting values
            cursor.execute("""
                ALTER TABLE candidates 
                ALTER COLUMN company_id SET NOT NULL
            """)
            
            print("✅ Successfully added company_id column to candidates table")
            
        # Commit the transaction
        conn.commit()
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    run_migration()
