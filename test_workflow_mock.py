#!/usr/bin/env python3
"""
Mock test for the job application workflow
This simulates the correct flow: Jobs exist first, then candidates apply
"""
import asyncio
import sys
import os
from datetime import datetime

# Add the src directory to Python path
sys.path.append('src')

# Mock email data for testing
MOCK_EMAIL_DATA = {
    "id": "mock-email-123",
    "payload": {
        "headers": [
            {"name": "Subject", "value": "Applying for Senior Frontend Developer Position"},
            {"name": "From", "value": "Jane Smith <jane.smith@example.com>"},
            {"name": "Date", "value": "Sun, 24 Aug 2025 10:30:00 +0000"}
        ]
    }
}

# Mock existing jobs (these would already be in the database)
MOCK_EXISTING_JOBS = [
    {
        "id": "job-001",
        "title": "Senior Frontend Developer",
        "department": "Engineering",
        "status": "active",
        "workflow_template_id": "workflow-template-001"
    },
    {
        "id": "job-002", 
        "title": "Backend Engineer",
        "department": "Engineering",
        "status": "active",
        "workflow_template_id": "workflow-template-001"
    },
    {
        "id": "job-003",
        "title": "Full Stack Developer",
        "department": "Engineering", 
        "status": "active",
        "workflow_template_id": "workflow-template-001"
    }
]

class MockWorkflowTester:
    """Mock workflow tester to simulate the correct job application flow"""
    
    def extract_job_title_from_subject(self, subject: str) -> str:
        """Extract job title from email subject - same logic as the real implementation"""
        import re
        
        patterns = [
            r"applying for (.+?) (?:role|position|job)",
            r"application for (.+?) (?:role|position|job)", 
            r"(.+?) (?:role|position|job) application",
            r"applying for (.+)",
            r"application for (.+)"
        ]
        
        subject_lower = subject.lower()
        
        for pattern in patterns:
            match = re.search(pattern, subject_lower, re.IGNORECASE)
            if match:
                job_title = match.group(1).strip()
                job_title = re.sub(r'\s+', ' ', job_title)
                job_title = job_title.title()
                return job_title
        
        return subject
    
    def parse_candidate_info_from_email(self, from_email: str, email: dict) -> dict:
        """Parse candidate information from email"""
        import re
        
        # Extract email address
        email_match = re.search(r'<(.+?)>', from_email)
        candidate_email = email_match.group(1) if email_match else from_email
        
        # Extract name
        name_part = from_email.split('<')[0].strip()
        if not name_part:
            name_part = candidate_email.split('@')[0]
        
        name_parts = name_part.strip('"').split()
        first_name = name_parts[0] if name_parts else "Unknown"
        last_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        
        return {
            "email": candidate_email,
            "first_name": first_name,
            "last_name": last_name,
            "source": "email"
        }
    
    def find_job_by_title(self, job_title: str, existing_jobs: list) -> dict:
        """Find existing job by title (case-insensitive partial match)"""
        job_title_lower = job_title.lower()
        
        for job in existing_jobs:
            if job_title_lower in job["title"].lower() or job["title"].lower() in job_title_lower:
                return job
        
        return None
    
    def test_workflow_logic(self):
        """Test the complete workflow logic with mock data"""
        print("🚀 Testing Job Application Workflow with Mock Data")
        print("=" * 60)
        
        # Step 1: Extract email metadata
        headers = MOCK_EMAIL_DATA["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "No Subject")
        from_email = next((h["value"] for h in headers if h["name"] == "From"), "Unknown")
        
        print(f"📧 Email Subject: {subject}")
        print(f"👤 From: {from_email}")
        
        # Step 2: Extract job title from subject
        job_title = self.extract_job_title_from_subject(subject)
        print(f"💼 Extracted Job Title: '{job_title}'")
        
        # Step 3: Find existing job
        matched_job = self.find_job_by_title(job_title, MOCK_EXISTING_JOBS)
        
        if matched_job:
            print(f"✅ Found Existing Job: {matched_job['id']} - {matched_job['title']}")
            print(f"   📋 Department: {matched_job['department']}")
            print(f"   📊 Status: {matched_job['status']}")
            print(f"   🔄 Workflow Template: {matched_job['workflow_template_id']}")
        else:
            print(f"❌ No existing job found for title: '{job_title}'")
            print(f"📋 Available jobs:")
            for job in MOCK_EXISTING_JOBS:
                print(f"   - {job['title']}")
            return False
        
        # Step 4: Parse candidate information
        candidate_info = self.parse_candidate_info_from_email(from_email, MOCK_EMAIL_DATA)
        print(f"👥 Candidate Info:")
        print(f"   📧 Email: {candidate_info['email']}")
        print(f"   👤 Name: {candidate_info['first_name']} {candidate_info['last_name']}")
        print(f"   📍 Source: {candidate_info['source']}")
        
        # Step 5: Simulate workflow creation
        print(f"🔄 Would create workflow instance:")
        print(f"   📝 Job: {matched_job['title']} ({matched_job['id']})")
        print(f"   👤 Candidate: {candidate_info['first_name']} {candidate_info['last_name']}")
        print(f"   📧 Email: {candidate_info['email']}")
        print(f"   🎯 Workflow Template: {matched_job['workflow_template_id']}")
        
        print("\n✅ Mock workflow test completed successfully!")
        return True

def test_multiple_scenarios():
    """Test multiple email scenarios"""
    tester = MockWorkflowTester()
    
    test_emails = [
        {
            "subject": "Applying for Senior Frontend Developer Position",
            "from": "Jane Smith <jane.smith@example.com>",
            "expected_job": "Senior Frontend Developer"
        },
        {
            "subject": "Application for Backend Engineer Role", 
            "from": "John Doe <john.doe@gmail.com>",
            "expected_job": "Backend Engineer"
        },
        {
            "subject": "Full Stack Developer Job Application",
            "from": "Alice Johnson <alice@company.com>", 
            "expected_job": "Full Stack Developer"
        },
        {
            "subject": "Applying for Data Scientist Position",  # This job doesn't exist
            "from": "Bob Wilson <bob@email.com>",
            "expected_job": None
        }
    ]
    
    print("\n🧪 Testing Multiple Scenarios")
    print("=" * 60)
    
    for i, test_email in enumerate(test_emails, 1):
        print(f"\n📧 Test Case {i}:")
        print(f"Subject: {test_email['subject']}")
        print(f"From: {test_email['from']}")
        
        # Extract job title
        job_title = tester.extract_job_title_from_subject(test_email['subject'])
        print(f"Extracted: '{job_title}'")
        
        # Find job
        matched_job = tester.find_job_by_title(job_title, MOCK_EXISTING_JOBS)
        
        if matched_job:
            print(f"✅ Matched to: {matched_job['title']}")
        else:
            print(f"❌ No job found")
            
        if test_email['expected_job']:
            expected_match = any(job['title'] == test_email['expected_job'] for job in MOCK_EXISTING_JOBS)
            if matched_job and matched_job['title'] == test_email['expected_job']:
                print(f"✅ Test PASSED")
            elif not matched_job and not expected_match:
                print(f"✅ Test PASSED (correctly found no match)")
            else:
                print(f"❌ Test FAILED") 

if __name__ == "__main__":
    # Run the main test
    tester = MockWorkflowTester()
    success = tester.test_workflow_logic()
    
    if success:
        # Run additional scenario tests
        test_multiple_scenarios()
    
    print(f"\n🎯 Next step: Update the real implementation to find existing jobs instead of creating them")
