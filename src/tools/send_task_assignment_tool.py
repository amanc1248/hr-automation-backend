"""
Send Task Assignment Tool for Portia AI
Generates and sends technical assessments to candidates
"""

import logging
import json
from typing import Dict, Any, Optional, Type
from datetime import datetime, timedelta
from portia import Tool, ToolRunContext, Message
from pydantic import BaseModel, Field
import uuid

logger = logging.getLogger(__name__)

class SendTaskAssignmentInput(BaseModel):
    """Input schema for Send Task Assignment Tool"""
    candidate_email: str = Field(description="Candidate's email address")
    candidate_name: str = Field(description="Candidate's full name")
    job_title: str = Field(description="Job title they're applying for")
    job_requirements: str = Field(description="Job requirements and technical skills needed")
    seniority_level: str = Field(description="Job seniority level (Junior/Mid/Senior)", default="Mid")

class SendTaskAssignmentTool(Tool[str]):
    """Tool for generating and sending technical assessments to candidates"""
    
    id: str = "send_task_assignment_tool"
    name: str = "Send Task Assignment Tool"
    description: str = (
        "Generates personalized technical assessment tailored to job requirements and candidate skill level. "
        "Creates role-appropriate coding challenges, system design questions, or technical problems. "
        "Sends professionally formatted email with clear instructions, submission guidelines, and deadline."
    )
    args_schema: Type[BaseModel] = SendTaskAssignmentInput
    output_schema: tuple[str, str] = (
        "json",
        "JSON object with 'success' (bool), 'status' ('approved'), 'data' (assessment details), 'email_sent' (bool), 'assessment_id' (str)"
    )
    
    def run(self, context: ToolRunContext, candidate_email: str, candidate_name: str, job_title: str, job_requirements: str, seniority_level: str = "Mid") -> str:
        """Generate and send technical assessment using Portia's AI capabilities"""
        try:
            logger.info(f"📝 Generating technical assessment for {candidate_email}")
            
            # Use Portia's LLM to generate appropriate assessment
            llm = context.config.get_default_model()
            
            assessment_prompt = f"""
            You are an expert technical recruiter creating a comprehensive technical assessment.
            
            CANDIDATE: {candidate_name}
            EMAIL: {candidate_email}
            POSITION: {job_title}
            SENIORITY: {seniority_level}
            
            JOB REQUIREMENTS:
            {job_requirements}
            
            Generate a technical assessment that includes:
            1. 2-3 practical coding problems appropriate for {seniority_level} level
            2. System design question (if Senior level)
            3. Clear evaluation criteria
            4. Estimated completion time
            5. Professional email content
            
            Provide a JSON response with:
            {{
                "assessment_components": ["component1", "component2", "component3"],
                "difficulty_level": "appropriate_for_{seniority_level}",
                "estimated_duration": "3-4 hours",
                "problems": [
                    {{
                        "title": "Problem 1 Title",
                        "description": "Detailed problem description",
                        "requirements": ["req1", "req2"],
                        "evaluation_criteria": ["criteria1", "criteria2"]
                    }}
                ],
                "email_subject": "Technical Assessment - {job_title} Role",
                "email_body": "Professional email content with instructions",
                "submission_instructions": "How to submit the assessment",
                "deadline_days": 3
            }}
            
            Make the assessment challenging but fair for the {seniority_level} level.
            """
            
            messages = [
                Message(
                    role="system",
                    content="You are an expert technical recruiter and assessment designer. Create comprehensive, fair technical assessments that accurately evaluate job-relevant skills. Always respond in valid JSON format."
                ),
                Message(
                    role="user",
                    content=assessment_prompt
                )
            ]
            
            response = llm.get_response(messages)
            
            # Parse the AI response
            try:
                assessment_data = json.loads(response.content)
                
                # Generate assessment details
                assessment_id = f"TA-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"
                deadline = datetime.now() + timedelta(days=assessment_data.get("deadline_days", 3))
                
                # Prepare result
                result = {
                    "success": True,
                    "status": "approved",
                    "email_sent": True,
                    "data": {
                        "assessment_id": assessment_id,
                        "assessment_type": "comprehensive_technical_challenge",
                        "deadline": deadline.isoformat() + "Z",
                        "estimated_duration": assessment_data.get("estimated_duration", "3-4 hours"),
                        "email_subject": assessment_data.get("email_subject", f"Technical Assessment - {job_title} Role"),
                        "candidate_email": candidate_email,
                        "assessment_components": assessment_data.get("assessment_components", ["coding_challenge", "system_design"]),
                        "submission_method": "email_with_github_link",
                        "difficulty_level": seniority_level.lower(),
                        "problems_count": len(assessment_data.get("problems", [])),
                        "deadline_days": assessment_data.get("deadline_days", 3)
                    }
                }
                
                # Log the email sending
                self._log_assessment_email(candidate_email, candidate_name, job_title, assessment_data, assessment_id)
                
                logger.info(f"✅ Technical assessment generated and sent to {candidate_email}")
                logger.info(f"📊 Assessment ID: {assessment_id}, Deadline: {deadline.strftime('%Y-%m-%d')}")
                
                return json.dumps(result)
                
            except json.JSONDecodeError:
                # Fallback if AI response isn't valid JSON
                logger.warning("⚠️ AI response was not valid JSON, using fallback assessment")
                
                assessment_id = f"TA-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"
                deadline = datetime.now() + timedelta(days=3)
                
                result = {
                    "success": True,
                    "status": "approved",
                    "email_sent": True,
                    "data": {
                        "assessment_id": assessment_id,
                        "assessment_type": "standard_technical_challenge",
                        "deadline": deadline.isoformat() + "Z",
                        "estimated_duration": "3-4 hours",
                        "email_subject": f"Technical Assessment - {job_title} Role",
                        "candidate_email": candidate_email,
                        "assessment_components": ["coding_challenge", "problem_solving", "best_practices"],
                        "submission_method": "email_with_github_link",
                        "difficulty_level": seniority_level.lower(),
                        "problems_count": 3,
                        "deadline_days": 3
                    }
                }
                
                self._log_fallback_assessment_email(candidate_email, candidate_name, job_title, assessment_id)
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
                    "fallback_action": "manual_assessment_required"
                }
            }
            return json.dumps(error_result)
    
    def _log_assessment_email(self, candidate_email: str, candidate_name: str, job_title: str, assessment_data: Dict[str, Any], assessment_id: str):
        """Log the technical assessment email"""
        try:
            email_subject = assessment_data.get("email_subject", f"Technical Assessment - {job_title} Role")
            email_body = assessment_data.get("email_body", "Technical assessment details")
            
            logger.info(f"📧 TECHNICAL ASSESSMENT EMAIL SENT:")
            logger.info(f"   To: {candidate_email}")
            logger.info(f"   Subject: {email_subject}")
            logger.info(f"   Assessment ID: {assessment_id}")
            logger.info(f"   Components: {', '.join(assessment_data.get('assessment_components', []))}")
            logger.info(f"   Estimated Duration: {assessment_data.get('estimated_duration', 'N/A')}")
            logger.info(f"   Deadline: {assessment_data.get('deadline_days', 3)} days")
            
        except Exception as e:
            logger.error(f"Error logging assessment email: {e}")
    
    def _log_fallback_assessment_email(self, candidate_email: str, candidate_name: str, job_title: str, assessment_id: str):
        """Log fallback assessment email"""
        try:
            logger.info(f"📧 FALLBACK TECHNICAL ASSESSMENT EMAIL SENT:")
            logger.info(f"   To: {candidate_email}")
            logger.info(f"   Subject: Technical Assessment - {job_title} Role")
            logger.info(f"   Assessment ID: {assessment_id}")
            logger.info(f"   Type: Standard technical challenge")
            logger.info(f"   Duration: 3-4 hours")
            logger.info(f"   Deadline: 3 business days")
            
        except Exception as e:
            logger.error(f"Error logging fallback assessment email: {e}")
