#!/usr/bin/env python3
"""
Test script to verify Portia integration with HR workflow tools
"""

import asyncio
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from services.portia_service import portia_service

async def test_portia_integration():
    """Test the Portia integration with resume screening"""
    
    print("🧪 Testing Portia Integration with HR Workflow Tools")
    print("=" * 60)
    
    # Mock workflow step data
    step_description = "AI-powered analysis of candidate resume. This step processes incoming resume emails, extracts skills, experience, and education, calculates job fit score, and determines if candidate meets basic requirements for the Full Stack Developer position."
    
    context_data = {
        "candidate": {
            "id": "test-candidate-123",
            "email": "john.doe@example.com",
            "first_name": "John",
            "last_name": "Doe"
        },
        "job": {
            "id": "test-job-456",
            "title": "Full Stack Developer",
            "status": "active"
        },
        "email": {
            "id": "test-email-789",
            "subject": "Applying For Full Stack Developer Role"
        },
        "step": {
            "id": "test-step-detail-123",
            "name": "Resume Analysis",
            "description": step_description,
            "step_type": "resume_analysis",
            "order_number": 1
        }
    }
    
    print(f"📋 Testing Resume Screening Step:")
    print(f"   Candidate: {context_data['candidate']['first_name']} {context_data['candidate']['last_name']}")
    print(f"   Email: {context_data['candidate']['email']}")
    print(f"   Job: {context_data['job']['title']}")
    print(f"   Step: {context_data['step']['name']}")
    print("")
    
    try:
        # Execute the workflow step using Portia
        print("🚀 Executing workflow step with Portia...")
        result = await portia_service.execute_workflow_step(step_description, context_data)
        
        if result:
            print("✅ Portia execution completed!")
            print(f"📊 Result:")
            print(f"   Success: {result.get('success', 'Unknown')}")
            print(f"   Status: {result.get('status', 'Unknown')}")
            print(f"   Data: {result.get('data', 'No data')}")
            
            # If it's a resume screening result, show additional details
            if 'job_fit_score' in result:
                print(f"   Job Fit Score: {result.get('job_fit_score', 'N/A')}")
                print(f"   Email Sent: {result.get('email_sent', 'N/A')}")
            
            print("")
            print("🎯 Portia Integration Test: PASSED ✅")
        else:
            print("❌ Portia execution failed - no result returned")
            print("🎯 Portia Integration Test: FAILED ❌")
            
    except Exception as e:
        print(f"❌ Error during Portia execution: {e}")
        import traceback
        traceback.print_exc()
        print("🎯 Portia Integration Test: FAILED ❌")

if __name__ == "__main__":
    asyncio.run(test_portia_integration())
