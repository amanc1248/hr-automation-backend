"""
Send Task Assignment Tool for HR Workflow
Generates technical assessments for candidates
"""

import logging
import json
from typing import Dict, Any, Optional, Type
from datetime import datetime, timedelta
from portia import Tool, ToolRunContext, Message
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SendTaskAssignmentInput(BaseModel):
    """Input schema for Send Task Assignment Tool"""
    candidate_email: str = Field(description="Candidate's email address")
    candidate_name: str = Field(description="Candidate's full name")
    job_title: str = Field(description="Job title they're applying for")
    job_requirements: str = Field(description="Detailed job requirements for the role")
    seniority_level: str = Field(description="Seniority level of the job (e.g., 'Junior', 'Mid', 'Senior')")

class SendTaskAssignmentTool(Tool[str]):
    """AI-powered technical assessment generation tool"""
    
    id: str = "send_task_assignment_tool"
    name: str = "Send Task Assignment Tool"
    description: str = (
        "Generates a personalized technical assessment tailored to specific job requirements and candidate's skill level. "
        "Creates role-appropriate coding challenges, system design questions, or technical problems that accurately evaluate "
        "job-relevant competencies. Returns detailed assessment with clear instructions, submission guidelines, and evaluation criteria."
    )
    args_schema: Type[BaseModel] = SendTaskAssignmentInput
    output_schema: tuple[str, str] = (
        "json",
        "JSON object with 'success' (bool), 'status' ('approved'), 'email_sent' (bool), 'data' (assessment details)"
    )

    def run(self, context: ToolRunContext, candidate_email: str, candidate_name: str, job_title: str, job_requirements: str, seniority_level: str) -> str:
        """Generate a technical assessment for the candidate"""
        try:
            logger.info(f"📝 Generating technical assessment for {candidate_email}")
            
            # Use Portia's LLM to generate assessment content
            llm = context.config.get_default_model()
            
            assessment_prompt = f"""
            Generate a comprehensive technical assessment for a candidate applying for {job_title} position.
            
            Candidate: {candidate_name} ({candidate_email})
            Seniority Level: {seniority_level}
            Job Requirements: {job_requirements}
            
            Create a technical assessment that includes:
            1. Clear overview of what needs to be built
            2. Specific technical requirements
            3. Submission guidelines and timeline
            4. Evaluation criteria
            5. Professional and encouraging tone
            
            The assessment should be appropriate for the {seniority_level} level and test skills relevant to: {job_requirements}
            
            Format the response as a complete technical assessment document.
            """
            
            messages = [
                Message(role="system", content="You are an expert technical recruiter creating comprehensive coding assessments."),
                Message(role="user", content=assessment_prompt)
            ]
            
            try:
                response = llm.get_response(messages)
                assessment_content = response.value if hasattr(response, 'value') else str(response)
                
                # Create structured result
                result = {
                    "success": True,
                    "status": "approved",
                    "email_sent": False,  # Will be handled by email tool in Portia
                    "data": {
                        "assessment_id": f"TA-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}",
                        "assessment_type": "technical_challenge",
                        "candidate_email": candidate_email,
                        "candidate_name": candidate_name,
                        "job_title": job_title,
                        "deadline": (datetime.now() + timedelta(days=5)).isoformat(),
                        "estimated_duration": "3-4 hours",
                        "assessment_content": assessment_content,
                        "submission_method": "email_with_github_link",
                        "difficulty_level": seniority_level.lower(),
                        "generated_at": datetime.now().isoformat()
                    }
                }
                
                logger.info(f"✅ Technical assessment generated successfully for {candidate_name}")
                logger.info(f"📋 Assessment ID: {result['data']['assessment_id']}")
                logger.info(f"⏰ Deadline: {result['data']['deadline']}")
                
                return json.dumps(result)
                
            except Exception as llm_error:
                logger.warning(f"⚠️ LLM assessment generation failed: {llm_error}, using fallback")
                
                # Fallback assessment content
                fallback_assessment = f"""
Technical Assessment - {job_title}

Dear {candidate_name},

Thank you for your application! We'd like you to complete a technical assessment to better understand your skills and problem-solving approach.

ASSIGNMENT OVERVIEW:
Build a simple full-stack application demonstrating your expertise in the technologies we use.

REQUIREMENTS:
• Frontend: Create a responsive web application
• Backend: Build RESTful API endpoints  
• Database: Design and implement a simple schema
• Documentation: Include setup instructions

SPECIFIC TASKS:
1. User authentication system
2. CRUD operations for core entities
3. Data validation and error handling
4. Responsive design

SUBMISSION:
• Host code in a public GitHub repository
• Include comprehensive README
• Deploy the application (free tier is fine)
• Send repository link and live demo URL

TIMELINE: 5 business days from today

EVALUATION:
• Code quality and organization (25%)
• Technical implementation (25%)
• Problem-solving approach (20%)
• Requirements completeness (20%)
• Documentation quality (10%)

Questions? Reply to this email.

Best regards,
Technical Hiring Team
"""
                
                result = {
                    "success": True,
                    "status": "approved", 
                    "email_sent": False,
                    "data": {
                        "assessment_id": f"TA-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}",
                        "assessment_type": "standard_technical_challenge",
                        "candidate_email": candidate_email,
                        "candidate_name": candidate_name,
                        "job_title": job_title,
                        "deadline": (datetime.now() + timedelta(days=5)).isoformat(),
                        "estimated_duration": "3-4 hours",
                        "assessment_content": fallback_assessment,
                        "submission_method": "email_with_github_link",
                        "difficulty_level": seniority_level.lower(),
                        "generated_at": datetime.now().isoformat()
                    }
                }
                
                return json.dumps(result)
                
        except Exception as e:
            logger.error(f"Error generating technical assessment: {e}")
            
            error_result = {
                "success": False,
                "status": "approved",  # Still proceed with workflow
                "email_sent": False,
                "data": {
                    "error": f"Assessment generation failed: {str(e)}",
                    "candidate_email": candidate_email,
                    "fallback_message": "Technical assessment will be sent manually"
                }
            }
            
            return json.dumps(error_result)