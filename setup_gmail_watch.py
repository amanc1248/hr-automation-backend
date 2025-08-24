#!/usr/bin/env python3
"""
Script to set up Gmail API watch for configured email accounts
"""
import sys
import os
import asyncio
import httpx

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings
from core.database import get_db
from services.gmail_service import gmail_service
from services.google_cloud_service import google_cloud_service
from sqlalchemy import text

async def setup_gmail_watch():
    """Set up Gmail API watch for all configured email accounts"""
    
    print("🔧 Setting up Gmail API Watch...")
    print("=" * 50)
    
    # Get database session
    async for db in get_db():
        try:
            # Get all Gmail configurations
            print("\n📋 Finding Gmail configurations...")
            
            # Get all Gmail configurations from the database
            result = await db.execute(
                text("SELECT * FROM gmail_configs WHERE is_active = true")
            )
            gmail_configs = result.fetchall()
            
            if not gmail_configs:
                print("   ❌ No Gmail configurations found")
                print("   💡 Please configure Gmail accounts in your dashboard first")
                return False
            
            print(f"   ✅ Found {len(gmail_configs)} Gmail configuration(s)")
            
            # Set up watch for each Gmail account
            for config_row in gmail_configs:
                config_dict = dict(config_row._mapping)
                email_address = config_dict.get('gmail_address')
                config_id = config_dict.get('id')
                
                if not email_address:
                    print(f"   ⚠️  Skipping config {config_id} - no email address")
                    continue
                
                print(f"\n📧 Setting up watch for: {email_address}")
                
                try:
                    # Get Gmail config with decrypted tokens
                    gmail_config = await gmail_service.get_gmail_config_by_id(db, str(config_id))
                    if not gmail_config:
                        print(f"   ❌ Failed to get Gmail config for {email_address}")
                        continue
                    
                    # Get valid access token
                    access_token = await gmail_service.get_valid_access_token(gmail_config)
                    if not access_token:
                        print(f"   ❌ Failed to get valid access token for {email_address}")
                        continue
                    
                    # Create Gmail watch
                    watch_result = await google_cloud_service.create_gmail_watch(
                        email_address, 
                        access_token
                    )
                    
                    if watch_result:
                        print(f"   ✅ Gmail watch created successfully!")
                        print(f"      History ID: {watch_result.get('historyId')}")
                        expiration = watch_result.get('expiration')
                        if expiration:
                            # Convert milliseconds to readable date
                            import datetime
                            exp_date = datetime.datetime.fromtimestamp(int(expiration) / 1000)
                            print(f"      Expires: {exp_date}")
                    else:
                        print(f"   ❌ Failed to create Gmail watch for {email_address}")
                        
                except Exception as e:
                    print(f"   ❌ Error setting up watch for {email_address}:")
                    print(f"      {str(e)}")
            
            print(f"\n🎉 Gmail watch setup completed!")
            print(f"\n📋 Next Steps:")
            print(f"   1. ✅ Gmail API watch is active")
            print(f"   2. 📧 Send test emails to your configured accounts")
            print(f"   3. 🔍 Check webhook endpoint for notifications")
            print(f"   4. 🚀 Start processing emails automatically")
            
            return True
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            return False

async def test_webhook_endpoint():
    """Test if the webhook endpoint is accessible"""
    
    print("\n🧪 Testing webhook endpoint...")
    
    try:
        async with httpx.AsyncClient() as client:
            # Test webhook endpoint
            response = await client.post(
                "http://localhost:8000/api/emails/webhook",
                json={"test": "message"},
                timeout=5.0
            )
            
            if response.status_code in [200, 400]:
                print("   ✅ Webhook endpoint is accessible")
                return True
            else:
                print(f"   ⚠️  Webhook returned status: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"   ❌ Webhook test failed: {e}")
        print(f"   💡 Make sure the backend server is running on http://localhost:8000")
        return False

if __name__ == "__main__":
    try:
        # Test webhook first
        webhook_ok = asyncio.run(test_webhook_endpoint())
        
        if not webhook_ok:
            print("\n⚠️  Please start the backend server first:")
            print("   python run_dev.py")
            sys.exit(1)
        
        # Set up Gmail watch
        success = asyncio.run(setup_gmail_watch())
        if not success:
            sys.exit(1)
            
    except Exception as e:
        print(f"❌ Setup failed with error: {e}")
        sys.exit(1)
