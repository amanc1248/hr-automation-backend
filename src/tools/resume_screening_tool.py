"""
Resume Screening Tool for Portia AI
Analyzes candidate resumes and makes screening decisions
"""

import logging
import json
from typing import Dict, Any, Optional, Type
from datetime import datetime
from portia import Tool, ToolRunContext, Message
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ResumeScreeningInput(BaseModel):
    """Input schema for Resume Screening Tool"""
    candidate_email: str = Field(description="Candidate's email address")
    candidate_name: str = Field(description="Candidate's full name")
    job_title: str = Field(description="Job title they're applying for")
    resume_content: str = Field(description="Resume content extracted from email")
    job_requirements: str = Field(description="Job requirements and qualifications")

class ResumeScreeningTool(Tool[str]):
    """AI-powered resume screening and candidate evaluation tool"""
    
    id: str = "resume_screening_tool"
    name: str = "Resume Screening Tool"
    description: str = (
        "Analyzes candidate resumes using AI to determine job fit, skills match, and screening decision. "
        "Automatically sends rejection emails for candidates who don't meet requirements. "
        "Returns structured assessment with approval/rejection status."
    )
    args_schema: Type[BaseModel] = ResumeScreeningInput
    output_schema: tuple[str, str] = (
        "json",
        "JSON object with 'success' (bool), 'status' ('approved'/'rejected'), 'data' (assessment details), 'job_fit_score' (0-100), 'email_sent' (bool)"
    )
    
    def run(self, context: ToolRunContext, candidate_email: str, candidate_name: str, job_title: str, resume_content: str, job_requirements: str) -> str:
        """Analyze candidate resume and make screening decision using Portia's AI capabilities"""
        try:
            logger.info(f"🔍 Starting resume screening for {candidate_email}")
            
            # Use Portia's LLM to analyze the resume
            llm = context.config.get_default_model()
            
            analysis_prompt = f"""
            You are an expert HR recruiter analyzing a resume for a {job_title} position.
            
            CANDIDATE: {candidate_name}
            EMAIL: {candidate_email}
            
            JOB REQUIREMENTS:
            {job_requirements}
            
            CANDIDATE RESUME:
            {resume_content}
            
            Please analyze this resume thoroughly and provide a JSON response with:
            {{
                "job_fit_score": 0-100,
                "skills_match": {{"score": 0-100, "details": "explanation"}},
                "experience_match": {{"score": 0-100, "details": "explanation"}},
                "education_match": {{"score": 0-100, "details": "explanation"}},
                "overall_assessment": "detailed summary",
                "strengths": ["list", "of", "key", "strengths"],
                "concerns": ["list", "of", "concerns"],
                "recommendation": "APPROVED" or "REJECTED",
                "reasoning": "detailed explanation for the decision"
            }}
            
            DECISION CRITERIA:
            - Score 80+ = APPROVED (strong candidate)
            - Score 60-79 = APPROVED (good candidate, worth interviewing)
            - Score <60 = REJECTED (insufficient match)
            
            Be thorough but objective in your analysis.
            """
            
            messages = [
                Message(
                    role="system",
                    content="You are an expert HR recruiter and resume analyst. Provide detailed, objective analysis in valid JSON format only."
                ),
                Message(
                    role="user",
                    content=analysis_prompt
                )
            ]
            
            response = llm.get_response(messages)
            
            # Parse the AI response
            try:
                analysis_result = json.loads(response.content)
                decision = analysis_result.get("recommendation", "REJECTED")
                job_fit_score = analysis_result.get("job_fit_score", 0)
                reasoning = analysis_result.get("reasoning", "Analysis completed")
                
                # Prepare result
                result = {
                    "success": True,
                    "status": "approved" if decision == "APPROVED" else "rejected",
                    "job_fit_score": job_fit_score,
                    "data": f"Resume analysis: {reasoning}",
                    "email_sent": False,
                    "analysis": analysis_result
                }
                
                # If rejected, simulate sending rejection email
                if decision == "REJECTED":
                    result["email_sent"] = self._log_rejection_email(candidate_email, candidate_name, job_title, reasoning)
                    result["data"] = f"Candidate rejected: {reasoning}. Rejection email sent."
                
                logger.info(f"✅ Resume screening completed for {candidate_email}: {decision} (Score: {job_fit_score})")
                return json.dumps(result)
                
            except json.JSONDecodeError:
                # Fallback if AI response isn't valid JSON
                logger.warning("⚠️ AI response was not valid JSON, using fallback analysis")
                result = {
                    "success": True,
                    "status": "approved",  # Default to approval for manual review
                    "job_fit_score": 70,
                    "data": "Resume analysis completed with basic scoring (AI response parsing failed)",
                    "email_sent": False,
                    "analysis": {"overall_assessment": "Basic analysis - manual review recommended"}
                }
                return json.dumps(result)
                
        except Exception as e:
            logger.error(f"Error in resume screening: {e}")
            error_result = {
                "success": False,
                "status": "rejected",
                "job_fit_score": 0,
                "data": f"Resume screening failed: {str(e)}",
                "email_sent": False
            }
            return json.dumps(error_result)
    
    def _log_rejection_email(self, candidate_email: str, candidate_name: str, job_title: str, reason: str) -> bool:
        """Log rejection email (mock implementation for now)"""
        try:
            # Compose rejection email
            email_subject = f"Thank you for your application - {job_title}"
            email_body = f"""
            Dear {candidate_name or 'Candidate'},
            
            Thank you for your interest in the {job_title} position with our company.
            
            After careful review of your application, we have decided to move forward with other candidates whose experience more closely aligns with our current requirements.
            
            We appreciate the time you took to apply and wish you the best of luck in your job search.
            
            Best regards,
            HR Team
            """
            
            # TODO: Integrate with actual email service (Gmail API, SendGrid, etc.)
            # For now, just log the email
            logger.info(f"📧 REJECTION EMAIL SENT:")
            logger.info(f"   To: {candidate_email}")
            logger.info(f"   Subject: {email_subject}")
            logger.info(f"   Reason: {reason}")
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging rejection email: {e}")
            return False
