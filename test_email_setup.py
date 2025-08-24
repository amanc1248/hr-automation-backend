#!/usr/bin/env python3
"""
Test script to verify email monitoring setup
"""
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings
from services.google_cloud_service import google_cloud_service

async def test_email_setup():
    """Test the email monitoring setup"""
    
    print("🧪 Testing Email Monitoring Setup...")
    print("=" * 50)
    
    # Check configuration
    print("\n📋 Configuration Check:")
    print(f"   Google Cloud Project ID: {settings.GOOGLE_CLOUD_PROJECT_ID or '❌ Not set'}")
    print(f"   Pub/Sub Topic: {settings.GOOGLE_CLOUD_TOPIC_NAME}")
    print(f"   Pub/Sub Subscription: {settings.GOOGLE_CLOUD_SUBSCRIPTION_NAME}")
    
    if not settings.GOOGLE_CLOUD_PROJECT_ID:
        print("\n⚠️  Please set GOOGLE_CLOUD_PROJECT_ID in your .env file")
        print("   Example: GOOGLE_CLOUD_PROJECT_ID=your-project-id")
        return False
    
    # Test Pub/Sub connection
    print("\n🔌 Testing Pub/Sub Connection...")
    try:
        client = await google_cloud_service._get_pubsub_client()
        if client:
            print("   ✅ Pub/Sub client initialized successfully")
        else:
            print("   ❌ Failed to initialize Pub/Sub client")
            return False
    except Exception as e:
        print(f"   ❌ Pub/Sub connection failed: {e}")
        return False
    
    # Test topic creation
    print("\n📢 Testing Topic Creation...")
    try:
        topic_created = await google_cloud_service._ensure_topic_exists()
        if topic_created:
            print("   ✅ Topic creation/verification successful")
        else:
            print("   ❌ Topic creation failed")
            return False
    except Exception as e:
        print(f"   ❌ Topic creation error: {e}")
        return False
    
    # Test subscription creation
    print("\n📥 Testing Subscription Creation...")
    try:
        sub_created = await google_cloud_service._ensure_subscription_exists()
        if sub_created:
            print("   ✅ Subscription creation/verification successful")
        else:
            print("   ❌ Subscription creation failed")
            return False
    except Exception as e:
        print(f"   ❌ Subscription creation error: {e}")
        return False
    
    # Test message publishing
    print("\n📤 Testing Message Publishing...")
    try:
        message_sent = await google_cloud_service.publish_test_message("Test from HR Automation")
        if message_sent:
            print("   ✅ Test message published successfully")
        else:
            print("   ❌ Test message publishing failed")
            return False
    except Exception as e:
        print(f"   ❌ Message publishing error: {e}")
        return False
    
    print("\n🎉 All tests passed! Email monitoring setup is ready.")
    print("\n📋 Next Steps:")
    print("   1. Set up Gmail API watch for your email accounts")
    print("   2. Test the webhook endpoint")
    print("   3. Send test emails to trigger notifications")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_email_setup())
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
