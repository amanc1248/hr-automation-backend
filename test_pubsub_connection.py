#!/usr/bin/env python3
"""
Test script to verify Google Cloud Pub/Sub connection
"""
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from core.config import settings
from services.google_cloud_service import google_cloud_service

async def test_pubsub_connection():
    """Test the Google Cloud Pub/Sub connection"""
    
    print("🧪 Testing Google Cloud Pub/Sub Connection...")
    print("=" * 60)
    
    # Check configuration
    print("\n📋 Configuration Check:")
    print(f"   Project ID: {settings.GOOGLE_CLOUD_PROJECT_ID}")
    print(f"   Topic Name: {settings.GOOGLE_CLOUD_TOPIC_NAME}")
    print(f"   Subscription Name: {settings.GOOGLE_CLOUD_SUBSCRIPTION_NAME}")
    
    # Test Pub/Sub client initialization
    print("\n🔌 Testing Pub/Sub Client...")
    try:
        publisher_client = await google_cloud_service._get_publisher_client()
        subscriber_client = await google_cloud_service._get_subscriber_client()
        if publisher_client and subscriber_client:
            print("   ✅ Pub/Sub clients initialized successfully")
        else:
            print("   ❌ Failed to initialize Pub/Sub clients")
            return False
    except Exception as e:
        print(f"   ❌ Pub/Sub client error: {e}")
        return False
    
    # Test topic creation/verification
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
    
    # Test subscription creation/verification
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
        message_sent = await google_cloud_service.publish_test_message("Test message from HR Automation System")
        if message_sent:
            print("   ✅ Test message published successfully")
        else:
            print("   ❌ Test message publishing failed")
            return False
    except Exception as e:
        print(f"   ❌ Message publishing error: {e}")
        return False
    
    print("\n🎉 All Pub/Sub tests passed!")
    print("\n📋 Next Steps:")
    print("   1. ✅ Pub/Sub infrastructure is ready")
    print("   2. 🔄 Set up Gmail API watch for your email accounts")
    print("   3. 📧 Test with real email notifications")
    
    return True

if __name__ == "__main__":
    try:
        success = asyncio.run(test_pubsub_connection())
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        sys.exit(1)
