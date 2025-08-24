#!/usr/bin/env python3
"""
Debug script to check Gmail tokens
"""
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.database import get_db
from services.gmail_service import gmail_service
from sqlalchemy import text

async def debug_gmail_tokens():
    """Debug Gmail tokens"""
    
    print("🔍 Debugging Gmail Tokens...")
    print("=" * 40)
    
    # Get database session
    async for db in get_db():
        try:
            # Get Gmail configurations
            result = await db.execute(
                text("SELECT id, gmail_address, access_token, refresh_token, token_expires_at FROM gmail_configs WHERE is_active = true LIMIT 1")
            )
            config_row = result.fetchone()
            
            if not config_row:
                print("   ❌ No Gmail configurations found")
                return False
            
            config_dict = dict(config_row._mapping)
            print(f"📧 Testing: {config_dict['gmail_address']}")
            print(f"   Config ID: {config_dict['id']}")
            print(f"   Has access token: {'Yes' if config_dict['access_token'] else 'No'}")
            print(f"   Has refresh token: {'Yes' if config_dict['refresh_token'] else 'No'}")
            print(f"   Token expires at: {config_dict['token_expires_at']}")
            
            # Try to get the config with decrypted tokens
            print("\n🔓 Getting decrypted config...")
            try:
                gmail_config = await gmail_service.get_gmail_config_by_id(db, str(config_dict['id']))
                
                if not gmail_config:
                    print("   ❌ Failed to get Gmail config")
                    return False
                
                print("   ✅ Got Gmail config successfully")
            except Exception as e:
                print(f"   ❌ Error getting Gmail config: {e}")
                import traceback
                traceback.print_exc()
                return False
            print(f"   Access token length: {len(gmail_config.access_token) if gmail_config.access_token else 0}")
            print(f"   Refresh token length: {len(gmail_config.refresh_token) if gmail_config.refresh_token else 0}")
            
            # Try to get valid access token
            print("\n🔑 Getting valid access token...")
            try:
                access_token = await gmail_service.get_valid_access_token(gmail_config)
                if access_token:
                    print("   ✅ Got valid access token successfully")
                    print(f"   Token length: {len(access_token)}")
                    return True
                else:
                    print("   ❌ Failed to get valid access token")
                    return False
            except Exception as e:
                print(f"   ❌ Error getting access token: {e}")
                return False
            
        except Exception as e:
            print(f"❌ Debug error: {e}")
            return False

if __name__ == "__main__":
    try:
        success = asyncio.run(debug_gmail_tokens())
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Debug failed: {e}")
        sys.exit(1)
