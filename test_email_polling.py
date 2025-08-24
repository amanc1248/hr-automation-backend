#!/usr/bin/env python3
"""
Test script for email polling service
"""
import sys
import os
import asyncio

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from services.email_polling_service import email_polling_service

async def test_email_polling():
    """Test the email polling service"""
    
    print("🧪 Testing Email Polling Service...")
    print("=" * 50)
    
    try:
        # Test 1: Start polling
        print("\n1️⃣ Starting email polling service...")
        await email_polling_service.start_polling()
        
        # Wait a moment
        await asyncio.sleep(2)
        
        # Test 2: Check status
        print("\n2️⃣ Checking polling status...")
        print(f"   Status: {'Running' if email_polling_service.is_running else 'Stopped'}")
        
        # Test 3: Run a test poll
        print("\n3️⃣ Running test poll cycle...")
        await email_polling_service._poll_all_accounts()
        
        # Test 4: Stop polling
        print("\n4️⃣ Stopping email polling service...")
        await email_polling_service.stop_polling()
        
        # Test 5: Final status check
        print("\n5️⃣ Final status check...")
        print(f"   Status: {'Running' if email_polling_service.is_running else 'Stopped'}")
        
        print("\n✅ All tests completed successfully!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    try:
        success = asyncio.run(test_email_polling())
        if not success:
            sys.exit(1)
    except Exception as e:
        print(f"❌ Script failed: {e}")
        sys.exit(1)

