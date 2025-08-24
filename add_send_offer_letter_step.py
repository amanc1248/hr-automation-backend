#!/usr/bin/env python3
"""
Script to add "Send Offer Letter" workflow step to the database
"""

import asyncio
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

load_dotenv()

async def add_send_offer_letter_step():
    """Add the Send Offer Letter workflow step to the database"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("🔧 Adding Send Offer Letter workflow step to database...")
            
            # Enhanced step description with clear instructions
            step_description = """Generate comprehensive job offer letters with competitive compensation packages, benefits, and terms. Creates personalized, professional offers based on role requirements, candidate assessment, and company standards. Sends formal offer letter with clear acceptance instructions and timeline.

OFFER GENERATION PROCESS:
- Analyze candidate's performance throughout hiring process
- Determine competitive compensation based on role level and market rates
- Include comprehensive benefits package appropriate for position
- Create personalized offer letter with professional tone
- Set appropriate acceptance timeline and next steps

COMPENSATION STRUCTURE:
- Base salary aligned with role seniority and market standards
- Performance-based bonus eligibility
- Equity/stock options for eligible positions
- Comprehensive benefits (health, dental, vision, 401k)
- Paid time off and flexible work arrangements
- Professional development opportunities

OFFER LETTER COMPONENTS:
- Professional greeting and company introduction
- Position details and reporting structure  
- Detailed compensation breakdown
- Benefits and perks overview
- Employment terms and conditions
- Start date and onboarding information
- Acceptance instructions and deadline
- Contact information for questions

EXPECTED RESPONSE FORMAT: {"success": true, "data": {"offer_id": "OFFER-2024-12345678", "candidate_email": "candidate@email.com", "candidate_name": "John Doe", "job_title": "Senior Developer", "job_level": "Senior", "offer_date": "2024-01-30T10:00:00Z", "offer_valid_until": "2024-02-06T10:00:00Z", "start_date": "2024-02-15", "base_salary": "Competitive market rate", "benefits_included": ["Health insurance", "401k", "PTO", "Remote work"], "employment_type": "full_time", "equity_offered": true, "bonus_eligible": true, "remote_policy": "hybrid", "offer_letter_sent": true, "acceptance_deadline_days": 7, "next_steps": ["Review offer carefully", "Contact HR with questions", "Respond within 7 days"], "hr_contact": "hr@company.com"}, "status": "approved"}

DECISION RULE: Always return "approved" status as this step represents successful completion of the hiring process. Offer generation marks the final step where the candidate has passed all evaluations and the company is ready to extend employment."""

            # Insert the new workflow step
            insert_query = text("""
                INSERT INTO workflow_step (
                    id,
                    name,
                    description,
                    step_type,
                    actions,
                    created_at,
                    updated_at,
                    is_deleted
                ) VALUES (
                    gen_random_uuid(),
                    :name,
                    :description,
                    :step_type,
                    :actions,
                    NOW(),
                    NOW(),
                    FALSE
                )
                RETURNING id, name
            """)
            
            # Define the actions as JSON objects
            actions = [
                {
                    "type": "compensation_analysis",
                    "description": "Analyze market rates and determine competitive compensation package",
                    "parameters": {
                        "factors": ["role_level", "market_rates", "company_budget", "candidate_performance"],
                        "salary_components": ["base_salary", "bonus_potential", "equity_options"],
                        "benchmark_sources": ["market_data", "internal_equity", "role_requirements"]
                    }
                },
                {
                    "type": "offer_generation",
                    "description": "Generate comprehensive job offer letter with all terms and conditions",
                    "parameters": {
                        "offer_components": ["compensation_details", "benefits_package", "employment_terms", "start_date"],
                        "personalization": ["candidate_name", "role_specific_details", "company_culture_fit"],
                        "legal_compliance": ["employment_law", "company_policies", "industry_standards"]
                    }
                },
                {
                    "type": "delivery_tracking",
                    "description": "Send offer letter and track acceptance timeline",
                    "parameters": {
                        "delivery_method": ["email", "document_portal", "postal_mail"],
                        "tracking_metrics": ["delivery_confirmation", "open_rates", "response_timeline"],
                        "follow_up_schedule": ["reminder_emails", "deadline_notifications", "hr_contact_availability"]
                    }
                }
            ]
            
            import json
            
            result = await session.execute(insert_query, {
                "name": "Send Offer Letter",
                "description": step_description,
                "step_type": "offer_generation",
                "actions": json.dumps(actions)  # Convert to JSON string
            })
            
            new_step = result.fetchone()
            
            if new_step:
                print(f"✅ Successfully added workflow step:")
                print(f"   ID: {new_step.id}")
                print(f"   Name: {new_step.name}")
                print(f"   Type: offer_generation")
                print(f"   Actions: {len(actions)} actions defined")
                
                # Verify the insertion
                verify_query = text("""
                    SELECT id, name, step_type, description
                    FROM workflow_step 
                    WHERE name = 'Send Offer Letter' 
                    AND is_deleted = FALSE
                """)
                
                verify_result = await session.execute(verify_query)
                verification = verify_result.fetchone()
                
                if verification:
                    print(f"\n📊 Verification successful:")
                    print(f"   Step exists in database: ✅")
                    print(f"   Description length: {len(verification.description)} characters")
                    print(f"   Step type: {verification.step_type}")
                else:
                    print("❌ Verification failed - step not found in database")
                
                await session.commit()
                print("\n🎉 Send Offer Letter step added successfully!")
                
            else:
                print("❌ Failed to add workflow step")
                
        except Exception as e:
            print(f"❌ Error adding workflow step: {e}")
            await session.rollback()
            import traceback
            traceback.print_exc()
        finally:
            await engine.dispose()

async def check_existing_steps():
    """Check existing workflow steps in the database"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("📋 Current workflow steps in database:")
            print("-" * 60)
            
            query = text("""
                SELECT id, name, step_type, created_at
                FROM workflow_step 
                WHERE is_deleted = FALSE
                ORDER BY created_at ASC
            """)
            
            result = await session.execute(query)
            steps = result.fetchall()
            
            if steps:
                for i, step in enumerate(steps, 1):
                    print(f"{i}. {step.name}")
                    print(f"   ID: {step.id}")
                    print(f"   Type: {step.step_type}")
                    print(f"   Created: {step.created_at}")
                    print()
                
                print(f"📊 Total steps: {len(steps)}")
            else:
                print("No workflow steps found in database")
                
        except Exception as e:
            print(f"❌ Error checking workflow steps: {e}")
        finally:
            await engine.dispose()

if __name__ == "__main__":
    print("🚀 Send Offer Letter Step Setup")
    print("=" * 60)
    
    # First check existing steps
    asyncio.run(check_existing_steps())
    
    print("\n" + "=" * 60)
    
    # Add the new step
    asyncio.run(add_send_offer_letter_step())
