#!/usr/bin/env python3
"""
Script to check current Gmail configurations
"""
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.database import get_db
from sqlalchemy import text

async def check_gmail_configs():
    """Check current Gmail configurations"""
    
    print("📋 Checking Gmail Configurations...")
    print("=" * 40)
    
    # Get database session
    async for db in get_db():
        try:
            # Get all Gmail configurations
            result = await db.execute(
                text("SELECT id, gmail_address, is_active, created_at FROM gmail_configs")
            )
            configs = result.fetchall()
            
            if not configs:
                print("   ❌ No Gmail configurations found")
                print("   💡 Make sure you've re-authenticated your Gmail accounts")
                return False
            
            print(f"   Found {len(configs)} Gmail configuration(s):")
            print()
            
            for i, config in enumerate(configs, 1):
                config_dict = dict(config._mapping)
                status = "✅ Active" if config_dict['is_active'] else "❌ Inactive"
                print(f"   {i}. {config_dict['gmail_address']}")
                print(f"      Status: {status}")
                print(f"      ID: {config_dict['id']}")
                print(f"      Created: {config_dict['created_at']}")
                print()
            
            return True
            
        except Exception as e:
            print(f"❌ Error checking Gmail configs: {e}")
            return False

if __name__ == "__main__":
    try:
        asyncio.run(check_gmail_configs())
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
