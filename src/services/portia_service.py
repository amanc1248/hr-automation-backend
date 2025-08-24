"""
Portia Integration Service
Handles workflow step execution using Portia AI
"""

import logging
import json
from typing import Dict, Any, Optional
from portia import Portia, Config, InMemoryToolRegistry
from tools.resume_screening_tool import ResumeScreeningTool
from tools.send_task_assignment_tool import SendTaskAssignmentTool
from tools.schedule_interview_tool import ScheduleInterviewTool
from tools.send_offer_letter_tool import SendOfferLetterTool
from tools.review_technical_assignment_tool import ReviewTechnicalAssignmentTool

logger = logging.getLogger(__name__)

class PortiaService:
    """Service for executing workflow steps using Portia AI"""
    
    def __init__(self):
        self.portia = None
        self._initialize_portia()
    
    def _initialize_portia(self):
        """Initialize Portia with HR workflow tools"""
        try:
            # Create Portia config
            config = Config.from_default(
                default_model="openai/gpt-4o-mini",
                default_log_level="INFO"
            )
            
            # Create tool registry with our HR tools
            hr_tools = [
                ResumeScreeningTool(),
                SendTaskAssignmentTool(),
                ScheduleInterviewTool(),
                SendOfferLetterTool(),
                ReviewTechnicalAssignmentTool(),
            ]
            
            tool_registry = InMemoryToolRegistry.from_local_tools(hr_tools)
            
            # Initialize Portia
            self.portia = Portia(
                config=config,
                tools=tool_registry
            )
            
            logger.info(f"✅ Portia initialized with {len(hr_tools)} HR workflow tools")
            
        except Exception as e:
            logger.error(f"Failed to initialize Portia: {e}")
            self.portia = None
    
    async def execute_workflow_step(self, step_description: str, context_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Execute a workflow step using Portia AI"""
        try:
            if not self.portia:
                logger.error("Portia not initialized")
                return None
            
            # Extract relevant data
            candidate = context_data.get("candidate", {})
            job = context_data.get("job", {})
            email = context_data.get("email", {})
            step = context_data.get("step", {})
            
            candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
            
            # Extract email content - this is critical for Portia context
            email_content = email.get('snippet', '')
            if 'payload' in email and 'headers' in email['payload']:
                # Get subject and body content
                headers = email['payload']['headers']
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
                sender = next((h['value'] for h in headers if h['name'] == 'From'), '')
                date = next((h['value'] for h in headers if h['name'] == 'Date'), '')
                
                # Try to get email body if available
                if 'parts' in email['payload']:
                    for part in email['payload']['parts']:
                        if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                            import base64
                            try:
                                body_data = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                                email_content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\nContent:\n{body_data}"
                            except:
                                email_content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\nSnippet: {email.get('snippet', '')}"
                        elif part.get('mimeType') == 'text/html' and not email_content:
                            # Fallback to snippet if we can't get plain text
                            email_content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\nSnippet: {email.get('snippet', '')}"
                else:
                    email_content = f"Subject: {subject}\nFrom: {sender}\nDate: {date}\n\nSnippet: {email.get('snippet', '')}"
            
            # Create a task for Portia based on the step description and available tools
            task = self._create_portia_task(step_description, candidate, job, email, step, email_content)
            
            logger.info(f"🤖 Executing Portia task: {task[:100]}...")
            
            # Execute the task
            plan_run = self.portia.run(task)
            
            # Parse result
            if plan_run.state.name == "COMPLETE":
                result = self._parse_portia_result(plan_run, step)
                logger.info(f"✅ Portia task completed successfully")
                return result
            else:
                logger.error(f"❌ Portia task failed with state: {plan_run.state}")
                return {
                    "success": False,
                    "data": f"Portia execution failed with state: {plan_run.state}",
                    "status": "approved"  # Still proceed with workflow
                }
                
        except Exception as e:
            logger.error(f"Error executing Portia workflow step: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {
                "success": False,
                "data": f"Portia execution error: {str(e)}",
                "status": "approved"  # Still proceed with workflow
            }
    
    def _create_portia_task(self, step_description: str, candidate: Dict[str, Any], job: Dict[str, Any], email: Dict[str, Any], step: Dict[str, Any], email_content: str) -> str:
        """Create a Portia task based on the workflow step"""
        
        candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
        candidate_email = candidate.get('email', '')
        job_title = job.get('title', 'Unknown Position')
        step_name = step.get('name', '').lower()
        
        # Mock resume content for testing
        resume_content = f"""
        {candidate_name}
        Full Stack Developer
        Email: {candidate_email}
        
        EXPERIENCE:
        • 5+ years of full-stack development experience
        • Proficient in React, Node.js, Python, PostgreSQL
        • Built and deployed 10+ web applications
        • Experience with AWS, Docker, Git
        
        EDUCATION:
        • Bachelor's in Computer Science (2018)
        
        SKILLS:
        • Frontend: React, TypeScript, HTML/CSS
        • Backend: Node.js, Python, FastAPI
        • Database: PostgreSQL, MongoDB
        • Cloud: AWS, Docker
        """
        
        # Job requirements (mock for testing)
        job_requirements = f"""
        REQUIRED SKILLS for {job_title}:
        • 3+ years full-stack development experience
        • Frontend: React, TypeScript, modern CSS
        • Backend: Node.js or Python, RESTful APIs
        • Database: PostgreSQL or similar SQL database
        • Version control: Git
        • Problem-solving and communication skills
        """
        
        # Create task based on step type
        if "resume" in step_name or "analysis" in step_name or "screening" in step_name:
            task = f"""
            Use the resume_screening_tool to analyze the candidate's resume and make a screening decision.
            
            Candidate Details:
            - Name: {candidate_name}
            - Email: {candidate_email}
            - Job Applied For: {job_title}
            
            Resume Content:
            {resume_content}
            
            Job Requirements:
            {job_requirements}
            
            Step Description: {step_description}
            
            Please use the resume_screening_tool with the provided information to analyze the candidate's fit for the position.
            """
        elif "technical" in step_name or "assignment" in step_name or "assessment" in step_name:
            task = f"""
            Use the send_task_assignment_tool to generate a technical assessment for the candidate, then send the assessment via email.
            
            Candidate Details:
            - Name: {candidate_name}
            - Email: {candidate_email}
            - Job Applied For: {job_title}
            
            Job Requirements:
            {job_requirements}
            
            Step Description: {step_description}
            
            Instructions:
            1. First, use the send_task_assignment_tool to create an appropriate technical assessment for this candidate
            2. Then, send an email to {candidate_email} with the subject "Technical Assessment - {job_title} Position"
            3. Include the generated assessment details in the email body
            4. Make sure the email is professional and includes clear submission guidelines and timeline
            
            The email should contain the complete technical assessment with requirements, submission instructions, and evaluation criteria.
            """
        elif "interview" in step_name or "schedule" in step_name:
            task = f"""
            Use the schedule_interview_tool to schedule an interview with the candidate.
            
            Candidate Details:
            - Name: {candidate_name}
            - Email: {candidate_email}
            - Job Applied For: {job_title}
            
            Step Description: {step_description}
            
            Please use the schedule_interview_tool to arrange an appropriate interview for this candidate.
            """
        elif "offer" in step_name or "letter" in step_name:
            task = f"""
            Use the send_offer_letter_tool to generate a comprehensive job offer letter for the candidate, then send the offer via email.
            
            Candidate Details:
            - Name: {candidate_name}
            - Email: {candidate_email}
            - Job Applied For: {job_title}
            
            Step Description: {step_description}
            
            Instructions:
            1. First, use the send_offer_letter_tool to create a comprehensive job offer for this successful candidate
            2. Then, send an email to {candidate_email} with the subject "Job Offer - {job_title} Position (Action Required)"
            3. Include the complete offer details in the email body with salary, benefits, start date, and next steps
            4. Make sure the email is professional, celebratory, and includes all necessary offer information
            
            The email should contain the full job offer with compensation package, benefits overview, timeline, and acceptance instructions.
            """
        elif "review" in step_name and ("technical" in step_name or "assignment" in step_name):
            # Mock assignment requirements for context
            assignment_requirements = f"""
            ORIGINAL TECHNICAL ASSIGNMENT for {job_title}:
            
            1. Backend API Development:
               - Create RESTful API endpoints using Node.js/Python
               - Implement proper authentication and authorization
               - Include comprehensive error handling
               - Write unit tests with good coverage
            
            2. Frontend Implementation:
               - Build responsive UI using React/TypeScript
               - Implement state management
               - Connect to backend APIs
               - Ensure mobile compatibility
            
            3. Database Design:
               - Design normalized database schema
               - Implement proper indexing
               - Write efficient queries
               - Include data validation
            
            EVALUATION CRITERIA:
            - Code quality and structure (25%)
            - Technical implementation (25%)
            - Problem-solving approach (20%)
            - Requirements adherence (20%)
            - Architecture and design (10%)
            
            SUBMISSION REQUIREMENTS:
            - Complete source code in GitHub repository
            - README with setup instructions
            - API documentation
            - Test cases and results
            - Brief explanation of design decisions
            """
            
            task = f"""
            Use the review_technical_assignment_tool to evaluate the candidate's submitted technical assignment.
            
            Candidate Details:
            - Name: {candidate_name}
            - Email: {candidate_email}
            - Job Applied For: {job_title}
            
            Email Content with Technical Assignment Submission:
            {email_content}
            
            Original Assignment Requirements:
            {assignment_requirements}
            
            Job Requirements:
            {job_requirements}
            
            Step Description: {step_description}
            
            Please use the review_technical_assignment_tool to comprehensively evaluate the candidate's technical submission.
            """
        else:
            # For other step types, create a general task
            task = f"""
            Process the following workflow step for candidate {candidate_name} applying for {job_title}:
            
            Step: {step.get('name', 'Unknown Step')}
            Description: {step_description}
            
            Candidate: {candidate_name} ({candidate_email})
            Job: {job_title}
            
            Execute the appropriate action based on the step description.
            """
        
        return task
    
    def _parse_portia_result(self, plan_run, step: Dict[str, Any]) -> Dict[str, Any]:
        """Parse Portia execution result"""
        try:
            # Get the final output from Portia
            if hasattr(plan_run, 'outputs') and plan_run.outputs and hasattr(plan_run.outputs, 'final_output'):
                final_output = plan_run.outputs.final_output.value
                
                # Try to parse as JSON if it's a string
                if isinstance(final_output, str):
                    try:
                        result = json.loads(final_output)
                        # Ensure required fields
                        if not isinstance(result, dict):
                            result = {"data": str(final_output)}
                    except json.JSONDecodeError:
                        result = {"data": final_output}
                else:
                    result = final_output if isinstance(final_output, dict) else {"data": str(final_output)}
                
                # Ensure required fields exist
                result.setdefault("success", True)
                result.setdefault("status", "approved")
                result.setdefault("data", "Step completed successfully")
                
                return result
            else:
                # Fallback result
                return {
                    "success": True,
                    "data": f"Step '{step.get('name', 'Unknown')}' completed via Portia",
                    "status": "approved"
                }
                
        except Exception as e:
            logger.error(f"Error parsing Portia result: {e}")
            return {
                "success": False,
                "data": f"Error parsing result: {str(e)}",
                "status": "approved"
            }

# Global instance
portia_service = PortiaService()
