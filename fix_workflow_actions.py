#!/usr/bin/env python3
"""
Fix the workflow_step actions field to be proper JSON objects instead of strings
"""
import asyncio
import sys
import os

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from core.database import AsyncSessionLocal
from models.workflow import WorkflowStep

async def fix_workflow_actions():
    """Fix workflow step actions to be proper JSON objects"""
    
    async with AsyncSessionLocal() as db:
        try:
            # Get all workflow steps
            result = await db.execute(select(WorkflowStep))
            steps = result.scalars().all()
            
            print(f"Found {len(steps)} workflow steps to check")
            
            for step in steps:
                print(f"\nChecking step: {step.name}")
                print(f"Current actions type: {type(step.actions)}")
                print(f"Current actions: {step.actions}")
                
                # If actions is a list of strings, convert to proper format
                if isinstance(step.actions, list) and step.actions:
                    # Check if first item is a string (indicating it's in wrong format)
                    if isinstance(step.actions[0], str):
                        print("❌ Actions are strings, need to convert to objects")
                        
                        # Convert based on step name
                        if step.name == "Resume Analysis":
                            new_actions = [
                                {"type": "ai_analysis", "target": "resume", "action": "parse_resume"},
                                {"type": "ai_analysis", "target": "skills", "action": "extract_skills"},
                                {"type": "ai_analysis", "target": "experience", "action": "evaluate_experience"},
                                {"type": "ai_analysis", "target": "job_fit", "action": "calculate_job_fit"},
                                {"type": "decision", "target": "approval", "action": "make_decision"}
                            ]
                        elif step.name == "Send Technical Assignment":
                            new_actions = [
                                {"type": "email", "target": "candidate", "action": "send_assignment"},
                                {"type": "tracking", "target": "assignment", "action": "track_submission"}
                            ]
                        elif step.name == "Receive and Review Technical Assignment":
                            new_actions = [
                                {"type": "email", "target": "inbox", "action": "monitor_submission"},
                                {"type": "ai_analysis", "target": "assignment", "action": "review_code"},
                                {"type": "scoring", "target": "technical", "action": "calculate_score"}
                            ]
                        elif step.name == "Schedule Interview":
                            new_actions = [
                                {"type": "calendar", "target": "availability", "action": "find_slots"},
                                {"type": "email", "target": "candidate", "action": "send_invite"},
                                {"type": "calendar", "target": "booking", "action": "create_meeting"}
                            ]
                        else:
                            # Generic conversion for unknown steps
                            new_actions = [{"type": "generic", "action": action} for action in step.actions]
                        
                        # Update the step
                        step.actions = new_actions
                        print(f"✅ Updated actions to: {new_actions}")
                    else:
                        print("✅ Actions are already in correct format")
                else:
                    print("✅ Actions are empty or already in correct format")
            
            # Commit all changes
            await db.commit()
            print(f"\n✅ All workflow step actions have been fixed!")
            
        except Exception as e:
            print(f"❌ Error: {e}")
            await db.rollback()
            raise

if __name__ == "__main__":
    asyncio.run(fix_workflow_actions())
