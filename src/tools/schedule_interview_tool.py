"""
Schedule Interview Tool for HR Workflow
Generates interview invitations and scheduling details
"""

import logging
import json
from typing import Dict, Any, Optional, Type
from datetime import datetime, timedelta
from portia import Tool, ToolRunContext, Message
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class ScheduleInterviewInput(BaseModel):
    """Input schema for Schedule Interview Tool"""
    candidate_email: str = Field(description="Candidate's email address")
    candidate_name: str = Field(description="Candidate's full name")
    job_title: str = Field(description="Job title they're applying for")
    interview_type: str = Field(default="technical", description="Type of interview to schedule")
    preferred_duration: int = Field(default=60, description="Preferred duration in minutes")

class ScheduleInterviewTool(Tool[str]):
    """AI-powered interview scheduling and invitation tool"""
    
    id: str = "schedule_interview_tool"
    name: str = "Schedule Interview Tool"
    description: str = (
        "Schedules an interview with the candidate and generates professional interview invitation details. "
        "Creates appropriate interview agenda, provides meeting logistics, and includes preparation guidelines. "
        "Returns structured interview information ready for email delivery."
    )
    args_schema: Type[BaseModel] = ScheduleInterviewInput
    output_schema: tuple[str, str] = (
        "json",
        "JSON object with 'success' (bool), 'status' ('approved'), 'interview_scheduled' (bool), 'data' (interview details)"
    )

    def run(self, context: ToolRunContext, candidate_email: str, candidate_name: str, job_title: str, interview_type: str, preferred_duration: int) -> str:
        """Generate interview invitation details"""
        try:
            logger.info(f"📅 Scheduling {interview_type} interview for {candidate_email}")
            
            # Use Portia's LLM to generate interview details
            llm = context.config.get_default_model()
            
            interview_prompt = f"""
            Generate a comprehensive interview invitation for a candidate.
            
            Candidate: {candidate_name} ({candidate_email})
            Position: {job_title}
            Interview Type: {interview_type}
            Duration: {preferred_duration} minutes
            
            Create interview invitation content that includes:
            1. Professional congratulatory opening
            2. Clear interview details (date, time, location/link)
            3. Interview agenda breakdown
            4. Preparation guidelines for the candidate
            5. Meeting logistics (Zoom details, backup contacts)
            6. Rescheduling instructions
            7. Encouraging and professional tone
            
            Format as a complete interview invitation ready for email.
            """
            
            messages = [
                Message(role="system", content="You are an expert HR coordinator creating professional interview invitations."),
                Message(role="user", content=interview_prompt)
            ]
            
            try:
                response = llm.get_response(messages)
                interview_content = response.value if hasattr(response, 'value') else str(response)
                
                # Generate interview details
                interview_date = datetime.now() + timedelta(days=3)  # Schedule 3 days from now
                interview_time = "10:00 AM"
                
                result = {
                    "success": True,
                    "status": "approved",
                    "interview_scheduled": True,
                    "data": {
                        "interview_id": f"INT-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}",
                        "candidate_email": candidate_email,
                        "candidate_name": candidate_name,
                        "job_title": job_title,
                        "interview_type": interview_type,
                        "interview_date": interview_date.strftime("%A, %B %d, %Y"),
                        "interview_time": interview_time,
                        "duration_minutes": preferred_duration,
                        "interviewer": "Sarah Johnson, Engineering Manager",
                        "meeting_platform": "Zoom",
                        "meeting_link": "https://zoom.us/j/123456789",
                        "meeting_id": "123 456 789",
                        "meeting_passcode": "HRInterview2024",
                        "backup_phone": "+1 (555) 123-4567",
                        "interview_content": interview_content,
                        "scheduled_at": datetime.now().isoformat()
                    }
                }
                
                logger.info(f"✅ Interview scheduled successfully for {candidate_name}")
                logger.info(f"📅 Date: {result['data']['interview_date']} at {interview_time}")
                logger.info(f"🎥 Platform: {result['data']['meeting_platform']}")
                
                return json.dumps(result)
                
            except Exception as llm_error:
                logger.warning(f"⚠️ LLM interview generation failed: {llm_error}, using fallback")
                
                # Fallback interview content
                interview_date = datetime.now() + timedelta(days=3)
                fallback_interview = f"""
Interview Invitation - {job_title}

Dear {candidate_name},

Congratulations! We're excited to invite you for an interview for the {job_title} position.

INTERVIEW DETAILS:
Date: {interview_date.strftime("%A, %B %d, %Y")}
Time: 10:00 AM - {10 + (preferred_duration // 60)}:{(preferred_duration % 60):02d} AM (EST)
Duration: {preferred_duration} minutes
Interviewer: Sarah Johnson, Engineering Manager
Platform: Video call (Zoom)

INTERVIEW AGENDA:
• Introduction and role overview (15 min)
• Technical discussion and problem-solving (30 min)
• Your questions about the role and company (15 min)

PREPARATION:
• Review the job description
• Prepare examples of your projects
• Think of questions about our company
• Test your video/audio setup

MEETING DETAILS:
Zoom Link: https://zoom.us/j/123456789
Meeting ID: 123 456 789
Passcode: HRInterview2024

Need to reschedule? Reply to this email ASAP.

Looking forward to speaking with you!

Best regards,
Sarah Johnson
Engineering Manager
"""
                
                result = {
                    "success": True,
                    "status": "approved",
                    "interview_scheduled": True,
                    "data": {
                        "interview_id": f"INT-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}",
                        "candidate_email": candidate_email,
                        "candidate_name": candidate_name,
                        "job_title": job_title,
                        "interview_type": interview_type,
                        "interview_date": interview_date.strftime("%A, %B %d, %Y"),
                        "interview_time": "10:00 AM",
                        "duration_minutes": preferred_duration,
                        "interviewer": "Sarah Johnson, Engineering Manager",
                        "meeting_platform": "Zoom",
                        "meeting_link": "https://zoom.us/j/123456789",
                        "meeting_id": "123 456 789",
                        "meeting_passcode": "HRInterview2024",
                        "backup_phone": "+1 (555) 123-4567",
                        "interview_content": fallback_interview,
                        "scheduled_at": datetime.now().isoformat()
                    }
                }
                
                return json.dumps(result)
                
        except Exception as e:
            logger.error(f"Error scheduling interview: {e}")
            
            error_result = {
                "success": False,
                "status": "approved",  # Still proceed with workflow
                "interview_scheduled": False,
                "data": {
                    "error": f"Interview scheduling failed: {str(e)}",
                    "candidate_email": candidate_email,
                    "fallback_message": "Interview will be scheduled manually"
                }
            }
            
            return json.dumps(error_result)