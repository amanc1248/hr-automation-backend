#!/usr/bin/env python3
"""
Test all database models
"""

import sys
from pathlib import Path

# Add src to Python path
sys.path.insert(0, str(Path(__file__).parent / "src"))

def test_model_imports():
    """Test importing all models"""
    print("🧪 Testing Database Models Import")
    print("=" * 40)
    
    try:
        # Test base models
        print("📦 Importing base models...")
        from models.base import Base, BaseModel, BaseModelWithSoftDelete
        print("✅ Base models imported successfully")
        
        # Test user models
        print("📦 Importing user models...")
        from models.user import User, Company, Profile, UserRole, UserInvitation
        print("✅ User models imported successfully")
        
        # Test job models
        print("📦 Importing job models...")
        from models.job import Job, JobRequirement
        print("✅ Job models imported successfully")
        
        # Test candidate models
        print("�� Importing candidate models...")
        from models.candidate import Candidate, Application
        print("✅ Candidate models imported successfully")
        
        # Test interview models
        print("📦 Importing interview models...")
        from models.interview import Interview, AIInterviewConfig
        print("✅ Interview models imported successfully")
        
        # Test workflow models
        print("📦 Importing workflow models...")
        from models.workflow import WorkflowTemplate, WorkflowStep, WorkflowExecution, WorkflowStepExecution, WorkflowApproval
        print("✅ Workflow models imported successfully")
        
        # Test email models
        print("📦 Importing email models...")
        from models.email import EmailAccount, EmailTemplate, EmailMonitoring
        print("✅ Email models imported successfully")
        
        # Test all models import
        print("📦 Testing models package...")
        import models
        print("✅ Models package imported successfully")
        
        # Count models
        model_count = len([
            User, Company, Profile, UserRole, UserInvitation,
            Job, JobRequirement,
            Candidate, Application,
            Interview, AIInterviewConfig,
            WorkflowTemplate, WorkflowStep, WorkflowExecution, WorkflowStepExecution, WorkflowApproval,
            EmailAccount, EmailTemplate, EmailMonitoring
        ])
        
        print(f"\n🎉 SUCCESS: All {model_count} models imported successfully!")
        print("✅ Database models are ready for use!")
        
        return True
        
    except Exception as e:
        print(f"❌ Model import failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_model_imports()
