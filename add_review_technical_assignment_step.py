#!/usr/bin/env python3
"""
Script to add "Review Technical Assignment" workflow step to the database
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

async def add_review_technical_assignment_step():
    """Add the Review Technical Assignment workflow step to the database"""
    
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        raise Exception("DATABASE_URL environment variable not set")
    if database_url.startswith('postgresql://'):
        database_url = database_url.replace('postgresql://', 'postgresql+asyncpg://', 1)
    
    engine = create_async_engine(database_url, echo=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            print("🔧 Adding Review Technical Assignment workflow step to database...")
            
            # Enhanced step description with clear instructions
            step_description = """Automatically evaluate submitted technical assignments using comprehensive AI analysis combined with standardized assessment criteria. Review code quality, architecture decisions, problem-solving approach, technical implementation, and adherence to requirements. Generate detailed feedback report with specific strengths, areas for improvement, and overall competency rating.

EVALUATION CRITERIA:
- Code Quality: Clean, readable, well-structured code with appropriate comments
- Technical Implementation: Correct use of technologies, design patterns, best practices
- Problem Solving: Logical approach, edge case handling, algorithmic efficiency
- Requirements Adherence: Completeness, accuracy, attention to specifications
- Architecture & Design: Scalability considerations, separation of concerns, modularity

ANALYSIS PROCESS:
- Parse submitted code/documentation automatically
- Run automated tests if test suite provided
- Evaluate against job-specific competency framework
- Generate objective scoring across multiple dimensions
- Identify specific technical strengths and weaknesses
- Compare against benchmark solutions for role level

EXPECTED RESPONSE FORMAT: {"success": true, "data": {"assignment_received": true, "submission_date": "2024-01-25T14:30:00Z", "evaluation_completed": true, "overall_score": 78, "code_quality_score": 85, "technical_implementation_score": 75, "problem_solving_score": 80, "detailed_feedback": "Strong implementation with clean code structure. Database design shows good understanding of normalization...", "key_strengths": ["Clean code architecture", "Proper error handling"], "improvement_areas": ["Test coverage could be improved", "API documentation sparse"], "recommendation": "PROCEED_TO_INTERVIEW", "next_step": "schedule_technical_interview"}, "status": "approved"}

DECISION RULE: Use "approved" if overall_score >= 65 to proceed to interview stage. Use "rejected" if score < 65 to end workflow with feedback email. Score 65-74 = "Adequate", 75-84 = "Good", 85+ = "Excellent"."""

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
                    "type": "ai_evaluation",
                    "description": "Evaluate technical assignment using AI analysis",
                    "parameters": {
                        "evaluation_criteria": ["code_quality", "technical_implementation", "problem_solving", "requirements_adherence", "architecture_design"],
                        "scoring_scale": "0-100",
                        "threshold_scores": {
                            "proceed_to_interview": 75,
                            "additional_review": 60,
                            "reject": 59
                        }
                    }
                },
                {
                    "type": "generate_feedback",
                    "description": "Generate detailed technical feedback report",
                    "parameters": {
                        "include_sections": ["strengths", "improvement_areas", "code_review_comments", "technical_highlights"],
                        "feedback_format": "structured_report"
                    }
                },
                {
                    "type": "recommendation",
                    "description": "Provide hiring recommendation based on evaluation",
                    "parameters": {
                        "recommendation_types": ["PROCEED_TO_INTERVIEW", "ADDITIONAL_REVIEW_NEEDED", "REJECT"],
                        "include_next_steps": True
                    }
                }
            ]
            
            import json
            
            result = await session.execute(insert_query, {
                "name": "Review Technical Assignment",
                "description": step_description,
                "step_type": "ai_evaluation",
                "actions": json.dumps(actions)  # Convert to JSON string
            })
            
            new_step = result.fetchone()
            
            if new_step:
                print(f"✅ Successfully added workflow step:")
                print(f"   ID: {new_step.id}")
                print(f"   Name: {new_step.name}")
                print(f"   Type: ai_evaluation")
                print(f"   Actions: {len(actions)} actions defined")
                
                # Verify the insertion
                verify_query = text("""
                    SELECT id, name, step_type, description
                    FROM workflow_step 
                    WHERE name = 'Review Technical Assignment' 
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
                print("\n🎉 Review Technical Assignment step added successfully!")
                
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
    print("🚀 Review Technical Assignment Step Setup")
    print("=" * 60)
    
    # First check existing steps
    asyncio.run(check_existing_steps())
    
    print("\n" + "=" * 60)
    
    # Add the new step
    asyncio.run(add_review_technical_assignment_step())
