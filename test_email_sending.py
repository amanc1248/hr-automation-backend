#!/usr/bin/env python3
"""
Test Email Sending with Updated Portia Service
Tests that our updated service can send real emails via Gmail
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.portia_service import PortiaService

async def test_email_sending():
    """Test email sending with the updated Portia service"""
    
    print("📧 Testing Email Sending with Updated Portia Service")
    print("=" * 60)
    
    # Check required environment variables
    if not os.getenv('PORTIA_API_KEY'):
        print("❌ PORTIA_API_KEY not found in .env file")
        print("💡 Get your key from: https://app.portialabs.ai")
        return
    
    if not os.getenv('OPENAI_API_KEY'):
        print("❌ OPENAI_API_KEY not found in .env file")
        return
    
    print("✅ API keys found!")
    print("⚠️  This will send a REAL email to caman374@gmail.com")
    
    # Initialize Portia service
    portia_service = PortiaService()
    
    if not portia_service.portia:
        print("❌ Failed to initialize Portia service")
        return
    
    print("✅ Portia service initialized with Gmail tools")
    
    # Test data for technical assessment email
    candidate_data = {
        "first_name": "Test",
        "last_name": "Candidate", 
        "email": "caman374@gmail.com",  # Target email
        "skills": ["Python", "React", "AWS"],
        "experience_years": 3
    }
    
    job_data = {
        "title": "Full Stack Developer",
        "description": "Full-stack development role",
        "requirements": "3+ years experience with Python, React, and cloud technologies"
    }
    
    email_data = {
        "id": "test_email_001",
        "subject": "Application for Full Stack Developer Role",
        "snippet": "I am applying for the Full Stack Developer position...",
        "payload": {
            "headers": [
                {"name": "Subject", "value": "Application for Full Stack Developer Role"},
                {"name": "From", "value": "Test Candidate <caman374@gmail.com>"},
                {"name": "Date", "value": datetime.now().isoformat()}
            ]
        }
    }
    
    step_data = {
        "id": "test-step-1",
        "name": "Send Technical Assignment",
        "description": "Generate and deliver personalized technical assessment tailored to specific job requirements.",
        "step_type": "technical_assessment",
        "order_number": 1
    }
    
    context_data = {
        "candidate": candidate_data,
        "job": job_data,
        "email": email_data,
        "step": step_data
    }
    
    print(f"\n🎯 Testing: Send Technical Assessment Email")
    print("-" * 50)
    print(f"📧 Target Email: {candidate_data['email']}")
    print(f"💼 Job: {job_data['title']}")
    print(f"👤 Candidate: {candidate_data['first_name']} {candidate_data['last_name']}")
    
    try:
        print(f"\n🚀 Executing workflow step with real Gmail integration...")
        
        result = await portia_service.execute_workflow_step(
            step_data['description'], 
            context_data
        )
        
        if result and result.get('success'):
            print(f"✅ SUCCESS: Technical assessment email sent!")
            print(f"📊 Status: {result.get('status', 'Unknown')}")
            print(f"📄 Data: {str(result.get('data', 'No details'))[:100]}...")
            
            print(f"\n📬 CHECK YOUR EMAIL!")
            print(f"📧 Email sent to: {candidate_data['email']}")
            print(f"📋 Subject: Technical Assessment - {job_data['title']} Position")
            print(f"💌 Should contain detailed technical assessment with:")
            print(f"   • Clear requirements and timeline")
            print(f"   • Submission guidelines")
            print(f"   • Evaluation criteria")
            print(f"   • Professional tone")
            
        else:
            print(f"❌ FAILED: Email sending failed")
            print(f"📄 Result: {result}")
            
            if result and 'Missing required email sending tool' in str(result.get('data', '')):
                print(f"\n💡 TROUBLESHOOTING:")
                print(f"   • Make sure PORTIA_API_KEY is valid")
                print(f"   • Ensure Gmail authentication is set up")
                print(f"   • Check Portia dashboard for tool availability")
                
    except Exception as e:
        print(f"❌ FAILED: Exception occurred: {e}")
        
        if 'Missing required email sending tool' in str(e):
            print(f"\n🔧 EMAIL TOOL NOT AVAILABLE:")
            print(f"   This error means Portia can't find Gmail tools")
            print(f"   Possible solutions:")
            print(f"   1. Check Portia API key is valid")
            print(f"   2. Verify Gmail integration is enabled in Portia dashboard")
            print(f"   3. Ensure proper authentication setup")
            
    print(f"\n🌐 Monitor execution at: https://app.portialabs.ai")

if __name__ == "__main__":
    print("🚀 Email Sending Test for HR Automation")
    print("=" * 60)
    print("This will test sending a REAL technical assessment email")
    print("⚠️  Make sure you have valid PORTIA_API_KEY and OPENAI_API_KEY")
    
    try:
        asyncio.run(test_email_sending())
    except KeyboardInterrupt:
        print("\n\n🛑 Test interrupted by user")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        print("💡 Ensure API keys are properly configured in .env file")
