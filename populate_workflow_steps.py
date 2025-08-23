#!/usr/bin/env python3
"""
Script to populate the workflow_step table with common HR workflow steps
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from core.database import AsyncSessionLocal
from models.workflow import WorkflowStep

async def populate_workflow_steps():
    """Populate the workflow_step table with common HR workflow steps"""
    
    # Define common workflow steps
    workflow_steps = [
        {
            "name": "Resume Analysis",
            "description": "AI-powered analysis of candidate resume including skills extraction, experience evaluation, and job fit scoring",
            "step_type": "automated",
            "actions": [
                {"type": "ai_analysis", "target": "resume", "output": "skills_score"},
                {"type": "ai_analysis", "target": "resume", "output": "experience_score"},
                {"type": "ai_analysis", "target": "resume", "output": "job_fit_score"}
            ]
        },
        {
            "name": "Initial Screening",
            "description": "Basic screening to check if candidate meets minimum requirements",
            "step_type": "automated",
            "actions": [
                {"type": "requirement_check", "criteria": "minimum_experience"},
                {"type": "requirement_check", "criteria": "required_skills"},
                {"type": "requirement_check", "criteria": "location_preference"}
            ]
        },
        {
            "name": "Phone Screening",
            "description": "Initial phone interview to assess communication skills and basic qualifications",
            "step_type": "manual",
            "actions": [
                {"type": "schedule_call", "duration": 30},
                {"type": "assessment", "criteria": "communication_skills"},
                {"type": "assessment", "criteria": "basic_qualifications"}
            ]
        },
        {
            "name": "Technical Assessment",
            "description": "Technical skills evaluation through coding tests, assignments, or technical interviews",
            "step_type": "manual",
            "actions": [
                {"type": "send_assessment", "assessment_type": "coding_test"},
                {"type": "schedule_interview", "interview_type": "technical"},
                {"type": "evaluate_results", "criteria": "technical_skills"}
            ]
        },
        {
            "name": "AI Interview",
            "description": "AI-powered interview using voice cloning and natural language processing",
            "step_type": "automated",
            "actions": [
                {"type": "ai_interview", "duration": 45},
                {"type": "ai_analysis", "target": "interview_responses", "output": "competency_score"},
                {"type": "ai_analysis", "target": "interview_responses", "output": "cultural_fit_score"}
            ]
        },
        {
            "name": "HR Interview",
            "description": "Human resources interview focusing on cultural fit, motivation, and company alignment",
            "step_type": "manual",
            "actions": [
                {"type": "schedule_interview", "interview_type": "hr"},
                {"type": "assessment", "criteria": "cultural_fit"},
                {"type": "assessment", "criteria": "motivation"},
                {"type": "assessment", "criteria": "company_alignment"}
            ]
        },
        {
            "name": "Manager Interview",
            "description": "Interview with the hiring manager to assess role-specific fit and team dynamics",
            "step_type": "manual",
            "actions": [
                {"type": "schedule_interview", "interview_type": "manager"},
                {"type": "assessment", "criteria": "role_specific_skills"},
                {"type": "assessment", "criteria": "team_fit"},
                {"type": "assessment", "criteria": "leadership_potential"}
            ]
        },
        {
            "name": "Reference Check",
            "description": "Verification of candidate's work history and performance through references",
            "step_type": "manual",
            "actions": [
                {"type": "contact_references", "minimum_references": 2},
                {"type": "verify_employment", "previous_roles": "all"},
                {"type": "assess_performance", "criteria": "work_quality"}
            ]
        },
        {
            "name": "Background Check",
            "description": "Comprehensive background verification including criminal, education, and employment history",
            "step_type": "automated",
            "actions": [
                {"type": "criminal_background_check"},
                {"type": "education_verification"},
                {"type": "employment_verification"},
                {"type": "credit_check", "if_required": True}
            ]
        },
        {
            "name": "Final Review",
            "description": "Comprehensive review of all assessment results and interview feedback",
            "step_type": "approval",
            "actions": [
                {"type": "compile_feedback", "sources": "all_interviews"},
                {"type": "calculate_overall_score"},
                {"type": "generate_recommendation"}
            ]
        },
        {
            "name": "Offer Preparation",
            "description": "Preparation of job offer including salary negotiation and terms finalization",
            "step_type": "manual",
            "actions": [
                {"type": "salary_calculation", "based_on": "market_rate"},
                {"type": "prepare_offer_letter"},
                {"type": "legal_review", "if_required": True}
            ]
        },
        {
            "name": "Offer Approval",
            "description": "Management approval for the job offer and compensation package",
            "step_type": "approval",
            "actions": [
                {"type": "manager_approval", "required": True},
                {"type": "hr_approval", "required": True},
                {"type": "budget_approval", "if_above_threshold": True}
            ]
        },
        {
            "name": "Send Offer",
            "description": "Delivery of job offer to candidate with terms and conditions",
            "step_type": "automated",
            "actions": [
                {"type": "send_offer_email", "template": "standard_offer"},
                {"type": "schedule_offer_call", "optional": True},
                {"type": "track_response", "deadline": "7_days"}
            ]
        },
        {
            "name": "Onboarding Preparation",
            "description": "Preparation for new hire onboarding including documentation and system access",
            "step_type": "automated",
            "actions": [
                {"type": "create_employee_record"},
                {"type": "prepare_onboarding_materials"},
                {"type": "setup_system_access"},
                {"type": "schedule_first_day"}
            ]
        }
    ]
    
    async with AsyncSessionLocal() as db:
        try:
            print("🚀 Starting workflow steps population...")
            
            # Check if steps already exist
            existing_steps = await db.execute(
                select(func.count(WorkflowStep.id))
            )
            count = existing_steps.scalar()
            
            if count > 0:
                print(f"⚠️  Found {count} existing workflow steps. Skipping population.")
                return
            
            # Create workflow steps
            created_steps = []
            for step_data in workflow_steps:
                workflow_step = WorkflowStep(
                    name=step_data["name"],
                    description=step_data["description"],
                    step_type=step_data["step_type"],
                    actions=step_data["actions"]
                )
                db.add(workflow_step)
                created_steps.append(step_data["name"])
            
            await db.commit()
            
            print(f"✅ Successfully created {len(created_steps)} workflow steps:")
            for step_name in created_steps:
                print(f"   • {step_name}")
                
        except Exception as e:
            await db.rollback()
            print(f"❌ Error populating workflow steps: {str(e)}")
            raise

if __name__ == "__main__":
    asyncio.run(populate_workflow_steps())
