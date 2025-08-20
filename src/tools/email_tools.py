"""
Email processing tools for HR Automation System.
Handles email monitoring, resume processing, and candidate creation.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from portia import Tool, ToolRunContext
from datetime import datetime

from src.services.email_service import EmailService, EmailMessage
from src.services.resume_processor import ResumeProcessor
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class EmailData(BaseModel):
    """Schema for email data"""
    to_email: str = Field(description="Recipient email address")
    subject: str = Field(description="Email subject line")
    body: str = Field(description="Email body content")
    template_name: Optional[str] = Field(default=None, description="Email template to use")
    variables: Optional[Dict[str, Any]] = Field(default=None, description="Template variables")

class CommunicationData(BaseModel):
    """Schema for communication data"""
    candidate_id: str = Field(description="Candidate ID")
    candidate_name: str = Field(description="Candidate's full name")
    candidate_email: str = Field(description="Candidate's email address")
    message_type: str = Field(description="Type of message (interview_invite, task_assignment, rejection, offer)")
    job_title: str = Field(description="Job title being communicated about")
    custom_message: Optional[str] = Field(default=None, description="Custom message content")

class EmailMonitoringConfig(BaseModel):
    """Configuration for email monitoring"""
    email_address: str = Field(description="HR email address to monitor")
    check_interval: int = Field(default=300, description="Check interval in seconds")
    auto_process: bool = Field(default=True, description="Automatically process applications")
    notification_enabled: bool = Field(default=True, description="Send notifications for new applications")

class ResumeProcessingConfig(BaseModel):
    """Configuration for resume processing"""
    candidate_email: str = Field(description="Candidate's email address")
    resume_filename: str = Field(description="Resume filename")
    job_id: Optional[str] = Field(default=None, description="Job ID for application")
    auto_screen: bool = Field(default=True, description="Automatically screen candidate")

class EmailMonitoringTool(Tool[Dict[str, Any]]):
    """Tool for monitoring HR email inbox for job applications"""
    
    id: str = "email_monitoring"
    name: str = "Email Monitoring Tool"
    description: str = "Monitor HR email inbox for job applications and process them automatically"
    args_schema: type[BaseModel] = EmailMonitoringConfig
    output_schema: tuple[str, str] = ("json", "Email monitoring results with processed applications")
    
    async def run(self, ctx: ToolRunContext, **kwargs) -> Dict[str, Any]:
        """Monitor email inbox for job applications"""
        try:
            config = EmailMonitoringConfig(**kwargs)
            
            # Initialize email service
            email_service = EmailService()
            await email_service.initialize_gmail()
            
            # Get new emails
            new_emails = await email_service.get_new_emails(config.email_address)
            
            processed_applications = []
            
            for email_msg in new_emails:
                if email_service.is_job_application_email(email_msg):
                    logger.info(f"Processing job application from {email_msg.sender}")
                    
                    # Process the application
                    application_data = await email_service.process_job_application(email_msg)
                    
                    if config.auto_process and "error" not in application_data:
                        # Create candidate automatically
                        candidate_result = await self._create_candidate_from_email(application_data)
                        application_data["candidate_created"] = candidate_result
                    
                    processed_applications.append(application_data)
            
            result = {
                "success": True,
                "email_address": config.email_address,
                "emails_checked": len(new_emails),
                "applications_found": len(processed_applications),
                "applications": processed_applications,
                "check_time": datetime.now().isoformat()
            }
            
            logger.info(f"Email monitoring completed: {len(processed_applications)} applications processed")
            return result
            
        except Exception as e:
            logger.error(f"Email monitoring failed: {e}")
            raise Exception(f"Email monitoring failed: {str(e)}")
    
    async def _create_candidate_from_email(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create candidate from email application data"""
        try:
            # TODO: Integrate with candidate creation API
            # This would involve:
            # 1. Calling the candidates API endpoint
            # 2. Creating candidate with extracted data
            # 3. Linking to job applications
            
            email_info = application_data.get("email_info", {})
            resume_data = application_data.get("resume_data", {})
            
            candidate_data = {
                "name": email_info.get("name", "Unknown"),
                "email": email_info.get("email", ""),
                "source": "email_application",
                "skills": resume_data.get("skills", []) if resume_data else [],
                "experience_years": resume_data.get("experience_years", 0) if resume_data else 0,
                "status": "new_application"
            }
            
            logger.info(f"Mock: Created candidate {candidate_data['name']}")
            return {"success": True, "candidate_id": "mock_candidate_123", "data": candidate_data}
            
        except Exception as e:
            logger.error(f"Failed to create candidate: {e}")
            return {"success": False, "error": str(e)}

class ResumeProcessingTool(Tool[Dict[str, Any]]):
    """Tool for processing resume files and extracting candidate information"""
    
    id: str = "resume_processing"
    name: str = "Resume Processing Tool"
    description: str = "Process resume files and extract structured candidate information using AI"
    args_schema: type[BaseModel] = ResumeProcessingConfig
    output_schema: tuple[str, str] = ("json", "Processed resume data with extracted information")
    
    async def run(self, ctx: ToolRunContext, **kwargs) -> Dict[str, Any]:
        """Process a resume file and extract information"""
        try:
            config = ResumeProcessingConfig(**kwargs)
            
            # Initialize resume processor
            processor = ResumeProcessor()
            
            # TODO: Get actual file content from storage or email attachment
            # For now, use mock file content
            mock_file_content = b"Mock resume file content..."
            
            # Process the resume
            processed_resume = await processor.process_resume_file(
                mock_file_content, 
                config.resume_filename
            )
            
            # Create candidate data structure
            candidate_data = self._format_candidate_data(processed_resume, config)
            
            result = {
                "success": True,
                "candidate_email": config.candidate_email,
                "resume_filename": config.resume_filename,
                "processed_resume": processed_resume,
                "candidate_data": candidate_data,
                "processing_time": datetime.now().isoformat()
            }
            
            if config.auto_screen and config.job_id:
                # Perform automatic screening
                screening_result = await self._perform_auto_screening(candidate_data, config.job_id)
                result["screening_result"] = screening_result
            
            logger.info(f"Successfully processed resume: {config.resume_filename}")
            return result
            
        except Exception as e:
            logger.error(f"Resume processing failed: {e}")
            raise Exception(f"Resume processing failed: {str(e)}")
    
    def _format_candidate_data(self, processed_resume: Dict[str, Any], config: ResumeProcessingConfig) -> Dict[str, Any]:
        """Format processed resume data into candidate structure"""
        try:
            analysis = processed_resume.get("analysis", {})
            personal_info = analysis.get("personal_info", {})
            skills = analysis.get("skills", {})
            
            return {
                "name": self._extract_name_from_resume(processed_resume),
                "email": config.candidate_email,
                "phone": personal_info.get("phones", [None])[0],
                "linkedin_profile": personal_info.get("linkedin_profiles", [None])[0],
                "github_profile": personal_info.get("github_profiles", [None])[0],
                "skills": {
                    "technical": skills.get("technical_skills", []),
                    "soft": skills.get("soft_skills", []),
                    "languages": skills.get("programming_languages", [])
                },
                "experience_years": analysis.get("total_experience_years", 0),
                "education": analysis.get("education", []),
                "work_experience": analysis.get("work_experience", []),
                "ai_insights": analysis.get("ai_insights", {}),
                "resume_filename": config.resume_filename,
                "source": "resume_upload"
            }
            
        except Exception as e:
            logger.error(f"Error formatting candidate data: {e}")
            return {"error": str(e)}
    
    def _extract_name_from_resume(self, processed_resume: Dict[str, Any]) -> str:
        """Extract candidate name from processed resume"""
        try:
            # Try to extract name from personal info
            analysis = processed_resume.get("analysis", {})
            personal_info = analysis.get("personal_info", {})
            
            # If email is available, try to extract name from it
            emails = personal_info.get("emails", [])
            if emails:
                email = emails[0]
                name_part = email.split('@')[0]
                # Convert email username to readable name
                name = name_part.replace('.', ' ').replace('_', ' ').title()
                return name
            
            # Default name extraction from filename
            filename = processed_resume.get("filename", "unknown")
            name = filename.split('.')[0].replace('_', ' ').replace('-', ' ').title()
            return name
            
        except Exception as e:
            logger.error(f"Error extracting name: {e}")
            return "Unknown Candidate"
    
    async def _perform_auto_screening(self, candidate_data: Dict[str, Any], job_id: str) -> Dict[str, Any]:
        """Perform automatic candidate screening for a job"""
        try:
            # TODO: Integrate with actual screening tools
            # This would involve:
            # 1. Getting job requirements
            # 2. Matching candidate skills
            # 3. Calculating fit score
            # 4. Generating recommendations
            
            # Mock screening result
            screening_result = {
                "job_id": job_id,
                "candidate_skills": candidate_data.get("skills", {}),
                "job_fit_score": 0.82,
                "matching_skills": ["Python", "JavaScript", "React"],
                "missing_skills": ["AWS", "Docker"],
                "recommendation": "Proceed to interview",
                "confidence": 0.85,
                "screening_date": datetime.now().isoformat()
            }
            
            logger.info(f"Auto-screening completed with score: {screening_result['job_fit_score']}")
            return screening_result
            
        except Exception as e:
            logger.error(f"Auto-screening failed: {e}")
            return {"error": str(e)}

class CandidateNotificationConfig(BaseModel):
    """Configuration for candidate notifications"""
    candidate_name: str = Field(description="Candidate name")
    candidate_email: str = Field(description="Candidate email")
    job_title: str = Field(description="Job title applied for")
    screening_score: float = Field(description="AI screening score")
    notification_type: str = Field(default="new_application", description="Type of notification")

class CandidateNotificationTool(Tool[str]):
    """Tool for sending notifications about new candidates"""
    
    id: str = "candidate_notification"
    name: str = "Candidate Notification Tool"
    description: str = "Send notifications to HR team about new candidate applications"
    args_schema: type[BaseModel] = CandidateNotificationConfig
    output_schema: tuple[str, str] = ("str", "Notification sending result")
    
    async def run(self, ctx: ToolRunContext, **kwargs) -> str:
        """Send notification about new candidate"""
        try:
            candidate_name = kwargs.get("candidate_name")
            candidate_email = kwargs.get("candidate_email")
            job_title = kwargs.get("job_title")
            screening_score = kwargs.get("screening_score", 0)
            
            # Format notification message
            message = f"""
            🎯 New Job Application Received!
            
            Candidate: {candidate_name}
            Email: {candidate_email}
            Position: {job_title}
            AI Screening Score: {screening_score:.2f}/1.00
            
            {"✅ Recommended for interview" if screening_score > 0.7 else "⚠️ Requires review"}
            """
            
            # TODO: Send actual notification
            # This could involve:
            # 1. Email notifications to HR team
            # 2. Slack/Teams integration
            # 3. Dashboard notifications
            # 4. SMS alerts for urgent cases
            
            logger.info(f"Mock: Sending notification about {candidate_name}")
            return f"Notification sent successfully for {candidate_name} (Score: {screening_score:.2f})"
            
        except Exception as e:
            logger.error(f"Failed to send notification: {e}")
            raise Exception(f"Notification failed: {str(e)}")

class EmailNotificationTool(Tool[str]):
    """Tool for sending email notifications"""
    
    id: str = "email_notification"
    name: str = "Email Notification Tool"
    description: str = "Send automated email notifications to candidates and team members"
    args_schema: type[BaseModel] = EmailData
    output_schema: tuple[str, str] = ("str", "Email sending result and message ID")
    
    async def run(self, ctx: ToolRunContext, **kwargs) -> str:
        """Send an email notification"""
        try:
            email_data = EmailData(**kwargs)
            
            # Send email (placeholder implementation)
            # TODO: Integrate with email service (Gmail API, SendGrid, etc.)
            send_result = self._send_email(email_data)
            
            logger.info(f"Successfully sent email to {email_data.to_email}")
            return send_result
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            raise Exception(f"Email sending failed: {str(e)}")
    
    def _send_email(self, email_data: EmailData) -> str:
        """Send email (placeholder implementation)"""
        # TODO: Implement actual email sending using:
        # 1. Gmail API integration
        # 2. SendGrid or similar service
        # 3. Email templates and personalization
        # 4. Delivery tracking and analytics
        
        # Mock email sending
        import uuid
        
        message_id = str(uuid.uuid4())
        
        # Log email details (in production, this would be sent)
        logger.info(f"Mock email sent - To: {email_data.to_email}, Subject: {email_data.subject}")
        logger.info(f"Email body: {email_data.body[:100]}...")
        
        return f"Email sent successfully! Message ID: {message_id}, To: {email_data.to_email}"

class CommunicationTool(Tool[Dict[str, Any]]):
    """Tool for automated candidate communication"""
    
    id: str = "candidate_communication"
    name: str = "Candidate Communication Tool"
    description: str = "Send automated communications to candidates based on message type"
    args_schema: type[BaseModel] = CommunicationData
    output_schema: tuple[str, str] = ("json", "Communication result with message details and status")
    
    async def run(self, ctx: ToolRunContext, **kwargs) -> Dict[str, Any]:
        """Send automated communication to candidate"""
        try:
            comm_data = CommunicationData(**kwargs)
            
            # Generate and send communication (placeholder implementation)
            comm_result = self._send_candidate_communication(comm_data)
            
            logger.info(f"Successfully sent {comm_data.message_type} to {comm_data.candidate_name}")
            return comm_result
            
        except Exception as e:
            logger.error(f"Failed to send candidate communication: {e}")
            raise Exception(f"Communication failed: {str(e)}")
    
    def _send_candidate_communication(self, comm_data: CommunicationData) -> Dict[str, Any]:
        """Send candidate communication (placeholder implementation)"""
        # TODO: Implement actual communication logic:
        # 1. Message template selection
        # 2. Content personalization
        # 3. Multi-channel delivery (email, SMS, etc.)
        # 4. Communication tracking
        
        import uuid
        from datetime import datetime
        
        # Generate message based on type
        if comm_data.message_type == "interview_invite":
            subject = f"Interview Invitation - {comm_data.job_title} Position"
            body = f"""
            Dear {comm_data.candidate_name},
            
            We are pleased to invite you for an interview for the {comm_data.job_title} position.
            
            Please check your email for scheduling details and meeting link.
            
            Best regards,
            HR Team
            """
        elif comm_data.message_type == "task_assignment":
            subject = f"Technical Task Assignment - {comm_data.job_title}"
            body = f"""
            Dear {comm_data.candidate_name},
            
            As part of the interview process for the {comm_data.job_title} position, 
            we would like you to complete a technical task.
            
            Please check the attached task description and submit your solution.
            
            Best regards,
            HR Team
            """
        elif comm_data.message_type == "rejection":
            subject = f"Application Update - {comm_data.job_title}"
            body = f"""
            Dear {comm_data.candidate_name},
            
            Thank you for your interest in the {comm_data.job_title} position.
            
            After careful consideration, we regret to inform you that we will not be 
            moving forward with your application at this time.
            
            We wish you the best in your future endeavors.
            
            Best regards,
            HR Team
            """
        elif comm_data.message_type == "offer":
            subject = f"Job Offer - {comm_data.job_title} Position"
            body = f"""
            Dear {comm_data.candidate_name},
            
            Congratulations! We are pleased to offer you the {comm_data.job_title} position.
            
            Please review the attached offer letter and respond within the specified timeframe.
            
            We look forward to having you join our team!
            
            Best regards,
            HR Team
            """
        else:
            subject = f"Message from HR - {comm_data.job_title}"
            body = comm_data.custom_message or "You have a new message from our HR team."
        
        # Mock email sending
        message_id = str(uuid.uuid4())
        
        return {
            "communication_id": message_id,
            "candidate_name": comm_data.candidate_name,
            "candidate_email": comm_data.candidate_email,
            "message_type": comm_data.message_type,
            "subject": subject,
            "body": body,
            "sent_at": datetime.now().isoformat(),
            "status": "sent",
            "delivery_confirmation": "Mock delivery confirmed",
            "template_used": f"{comm_data.message_type}_template"
        }