"""
Portia Integration Service
Handles workflow step execution using Portia AI
"""

import logging
import json
from typing import Dict, Any, Optional
from portia import Portia, Config, InMemoryToolRegistry, StorageClass, LogLevel
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
        """Initialize Portia with HR workflow tools and real Gmail integration"""
        try:
            # Create Portia config with cloud storage for real email integration
            config = Config.from_default(
                storage_class=StorageClass.CLOUD,
                default_model="openai/gpt-4o-mini",
                default_log_level=LogLevel.INFO
            )
            
            # Create tool registry with our custom HR tools
            custom_tools = [
                ResumeScreeningTool(),
                SendTaskAssignmentTool(),
                ScheduleInterviewTool(),
                SendOfferLetterTool(),
                ReviewTechnicalAssignmentTool()
            ]
            
            # Use InMemoryToolRegistry with custom tools
            tool_registry = InMemoryToolRegistry(tools=custom_tools)
            
            # Initialize Portia with config and tools
            self.portia = Portia(
                config=config,
                tools=tool_registry
            )
            
            logger.info("✅ Portia initialized successfully with custom HR tools")
            logger.info(f"🔧 Available tools: {[tool.id for tool in custom_tools]}")
            
        except Exception as e:
            logger.error(f"❌ Failed to initialize Portia: {e}")
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
        """Create a Portia task using the step description directly with candidate/job context"""
        
        candidate_name = f"{candidate.get('first_name', '')} {candidate.get('last_name', '')}".strip()
        candidate_email = candidate.get('email', '')
        job_title = job.get('title', 'Unknown Position')
        job_short_id = job.get('short_id', 'JOBXXX')
        
        # Mock resume content for screening steps
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
        
        # Job requirements for context
        job_requirements = f"""
        REQUIRED SKILLS for {job_title}:
        • 3+ years full-stack development experience
        • Frontend: React, TypeScript, modern CSS
        • Backend: Node.js or Python, RESTful APIs
        • Database: PostgreSQL or similar SQL database
        • Version control: Git
        • Problem-solving and communication skills
        """
        
        # Use the step description directly as the main instruction
        # and append candidate/job context
        task = f"""
        {step_description}
        
        CANDIDATE INFORMATION:
        - Name: {candidate_name}
        - Email: {candidate_email}
        - Job Applied For: {job_title}
        - Job Short ID: {job_short_id}
        
        JOB REQUIREMENTS:
        {job_requirements}
        
        RESUME CONTENT (for screening steps):
        {resume_content}
        
        EMAIL CONTENT (for review steps):
        {email_content}
        
        EMAIL SUBJECT FORMAT:
        - Technical Assessments: [{job_short_id}] Technical Assessment - {job_title} Position
        - Interview Invitations: [{job_short_id}] Interview Invitation - {job_title} Position  
        - Offer Letters: [{job_short_id}] Job Offer - {job_title} Position (Action Required)
        
        Execute the workflow step according to the description above.
        """
        
        return task.strip()
    
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
