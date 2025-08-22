import asyncio
import sys
import os
from datetime import datetime

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.database import AsyncSessionLocal
from sqlalchemy import text

async def create_gmail_tables():
    """Create Gmail configuration tables"""
    
    # SQL to create gmail_configs table
    create_gmail_configs_sql = """
    CREATE TABLE IF NOT EXISTS gmail_configs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        company_id UUID REFERENCES companies(id) NOT NULL,
        user_id UUID REFERENCES profiles(id) NOT NULL,
        
        -- Gmail account info
        gmail_address VARCHAR(255) NOT NULL,
        display_name VARCHAR(255),
        
        -- OAuth tokens (will be encrypted)
        access_token TEXT NOT NULL,
        refresh_token TEXT NOT NULL,
        token_expires_at TIMESTAMP NOT NULL,
        
        -- Scopes granted
        granted_scopes TEXT[] DEFAULT ARRAY[]::TEXT[],
        
        -- Configuration
        is_active BOOLEAN DEFAULT true,
        last_sync TIMESTAMP,
        sync_frequency_minutes INTEGER DEFAULT 2,
        
        -- Email filtering settings
        monitor_folders TEXT[] DEFAULT ARRAY['INBOX']::TEXT[],
        auto_reply_enabled BOOLEAN DEFAULT false,
        auto_reply_template TEXT,
        
        -- Metadata
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW(),
        
        UNIQUE(company_id, gmail_address)
    );
    """
    
    # SQL to create email_sync_logs table
    create_email_logs_sql = """
    CREATE TABLE IF NOT EXISTS email_sync_logs (
        id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
        gmail_config_id UUID REFERENCES gmail_configs(id) ON DELETE CASCADE,
        
        -- Email identification
        message_id VARCHAR(255) NOT NULL,
        thread_id VARCHAR(255),
        
        -- Processing info
        processed_at TIMESTAMP DEFAULT NOW(),
        status VARCHAR(50) NOT NULL, -- 'processed', 'ignored', 'error', 'duplicate'
        error_message TEXT,
        
        -- Results
        candidate_id UUID REFERENCES candidates(id),
        job_id UUID REFERENCES jobs(id),
        
        -- Email metadata
        sender_email VARCHAR(255),
        subject TEXT,
        received_at TIMESTAMP,
        has_attachments BOOLEAN DEFAULT false,
        attachment_count INTEGER DEFAULT 0,
        
        UNIQUE(gmail_config_id, message_id)
    );
    """
    
    # SQL to create indexes (separate commands)
    index_commands = [
        "CREATE INDEX IF NOT EXISTS idx_gmail_configs_company ON gmail_configs(company_id);",
        "CREATE INDEX IF NOT EXISTS idx_gmail_configs_active ON gmail_configs(is_active);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_config ON email_sync_logs(gmail_config_id);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_status ON email_sync_logs(status);",
        "CREATE INDEX IF NOT EXISTS idx_email_logs_processed ON email_sync_logs(processed_at);"
    ]
    
    async with AsyncSessionLocal() as db:
        try:
            print("Creating gmail_configs table...")
            await db.execute(text(create_gmail_configs_sql))
            
            print("Creating email_sync_logs table...")
            await db.execute(text(create_email_logs_sql))
            
            print("Creating indexes...")
            for i, index_cmd in enumerate(index_commands, 1):
                print(f"  Creating index {i}/{len(index_commands)}...")
                await db.execute(text(index_cmd))
            
            await db.commit()
            print("✅ Gmail tables created successfully!")
            
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(create_gmail_tables())
