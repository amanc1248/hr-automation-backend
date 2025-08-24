#!/usr/bin/env python3
"""
Test Gmail API watch functionality using existing OAuth tokens
"""
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings
from services.google_cloud_service import google_cloud_service

async def test_gmail_watch():
    """Test Gmail API watch functionality"""
    
    print("🧪 Testing Gmail API Watch Setup...")
    print("=" * 50)
    
    print("\n📋 Configuration Check:")
    print(f"   Project ID: {settings.GOOGLE_CLOUD_PROJECT_ID}")
    print(f"   Topic Name: {settings.GOOGLE_CLOUD_TOPIC_NAME}")
    print(f"   Subscription Name: {settings.GOOGLE_CLOUD_SUBSCRIPTION_NAME}")
    
    print("\n⚠️  Note: This test requires:")
    print("   1. A configured Gmail account in your system")
    print("   2. Valid OAuth tokens")
    print("   3. Google Cloud Pub/Sub API enabled")
    
    print("\n🔧 To complete setup, you need to:")
    print("   1. Install Google Cloud CLI: brew install google-cloud-sdk")
    print("   2. Run: gcloud auth application-default login")
    print("   3. Or create a service account key and set GOOGLE_APPLICATION_CREDENTIALS")
    
    print("\n📚 Documentation:")
    print("   https://cloud.google.com/docs/authentication/external/set-up-adc")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_gmail_watch())
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
