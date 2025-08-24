#!/usr/bin/env python3
"""
Script to set up Gmail watch for all newly authenticated email accounts
"""
import sys
import os
import asyncio
import httpx

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.database import get_db
from sqlalchemy import text

async def setup_gmail_watch_for_all():
    """Set up Gmail watch for all configured email accounts"""
    
    print("🚀 Setting up Gmail Watch for Real-time Notifications...")
    print("=" * 60)
    
    # Get database session
    async for db in get_db():
        try:
            # Get all active Gmail configurations
            print("\n📋 Fetching Gmail configurations...")
            result = await db.execute(
                text("SELECT id, gmail_address, created_at FROM gmail_configs WHERE is_active = true")
            )
            configs = result.fetchall()
            
            if not configs:
                print("   ❌ No active Gmail configurations found")
                print("   💡 Make sure you've re-authenticated your Gmail accounts")
                return False
            
            print(f"   Found {len(configs)} active Gmail configuration(s):")
            for config in configs:
                config_dict = dict(config._mapping)
                print(f"      - {config_dict['gmail_address']} (ID: {config_dict['id']})")
            
            # Set up watch for each configuration
            print(f"\n🔧 Setting up Gmail watch for each account...")
            
            success_count = 0
            for config in configs:
                config_dict = dict(config._mapping)
                email = config_dict['gmail_address']
                config_id = config_dict['id']
                
                print(f"\n📧 Setting up watch for: {email}")
                
                try:
                    # Call the setup-watch API endpoint
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            f"http://localhost:8000/api/emails/setup-watch/{email}",
                            headers={
                                "Authorization": f"Bearer YOUR_JWT_TOKEN_HERE",  # You'll need to replace this
                                "Content-Type": "application/json"
                            },
                            timeout=30.0
                        )
                        
                        if response.status_code == 200:
                            print(f"   ✅ Watch setup successful for {email}")
                            success_count += 1
                        else:
                            print(f"   ❌ Watch setup failed for {email}: {response.status_code}")
                            print(f"      Response: {response.text}")
                            
                except Exception as e:
                    print(f"   ❌ Error setting up watch for {email}: {e}")
            
            print(f"\n🎯 Results:")
            print(f"   ✅ Successful: {success_count}/{len(configs)}")
            print(f"   ❌ Failed: {len(configs) - success_count}/{len(configs)}")
            
            if success_count > 0:
                print(f"\n🚀 Next Steps:")
                print(f"   1. ✅ Gmail watch configured for {success_count} account(s)")
                print(f"   2. 📧 Send a test email to one of your configured accounts")
                print(f"   3. 🔍 Check the backend logs for webhook notifications")
                print(f"   4. 🎯 Test real-time email processing")
            
            return success_count > 0
            
        except Exception as e:
            print(f"❌ Error setting up Gmail watch: {e}")
            return False

async def test_webhook_endpoint():
    """Test if the webhook endpoint is accessible"""
    
    print("\n🧪 Testing Webhook Endpoint...")
    print("-" * 40)
    
    try:
        async with httpx.AsyncClient() as client:
            # Test with a simple message
            test_data = {
                "message": {
                    "data": "dGVzdCBtZXNzYWdl"  # base64 encoded "test message"
                }
            }
            
            response = await client.post(
                "http://localhost:8000/api/emails/webhook",
                json=test_data,
                timeout=10.0
            )
            
            print(f"   Webhook Status: {response.status_code}")
            print(f"   Response: {response.text}")
            
            if response.status_code in [200, 400]:  # 400 is expected for test data
                print("   ✅ Webhook endpoint is accessible")
                return True
            else:
                print("   ❌ Webhook endpoint returned unexpected status")
                return False
                
    except Exception as e:
        print(f"   ❌ Error testing webhook: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Gmail Watch Setup Script")
    print("=" * 40)
    
    try:
        # First test the webhook endpoint
        webhook_ok = asyncio.run(test_webhook_endpoint())
        
        if webhook_ok:
            print("\n✅ Webhook endpoint is working!")
            print("\n⚠️  IMPORTANT: Before running the full setup, you need to:")
            print("   1. Get a valid JWT token from your dashboard")
            print("   2. Replace 'YOUR_JWT_TOKEN_HERE' in the script")
            print("   3. Or run the setup manually through the API")
            
            print(f"\n💡 Alternative: Use the API endpoint directly:")
            print(f"   POST /api/emails/setup-watch/{{email_address}}")
            print(f"   With your JWT token in the Authorization header")
            
        else:
            print("\n❌ Webhook endpoint is not accessible")
            print("   Make sure the backend server is running on localhost:8000")
            
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)
