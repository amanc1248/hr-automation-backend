"""
Portia service for managing AI agents and plan runs.
Central orchestration point for all Portia-related operations.
"""

from portia import Portia, Config, LLMProvider, StorageClass, DefaultToolRegistry
from portia.cli import CLIExecutionHooks
from portia.execution_hooks import clarify_on_tool_calls
from portia.end_user import EndUser
from typing import Dict, Any, Optional, List
import logging
from functools import lru_cache
from pydantic import SecretStr

from src.config.settings import get_settings
from src.tools import (
    LinkedInJobPostingTool,
    LinkedInApplicationCollectorTool,
    ResumeScreeningTool,
    SkillsAnalysisTool,
    InterviewSchedulingTool,
    AIInterviewTool
)

logger = logging.getLogger(__name__)


class PortiaService:
    """
    Central service for managing Portia AI agents and workflows.
    Handles plan creation, execution, and monitoring.
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.portia = self._initialize_portia()
        self.agents = {}
        
    def _initialize_portia(self) -> Portia:
        """Initialize Portia with proper configuration"""
        try:
            # Determine LLM provider
            llm_provider = self._get_llm_provider()
            
            # Create Portia configuration
            config = Config.from_default(
                storage_class=StorageClass.CLOUD if self.settings.PORTIA_API_KEY else StorageClass.MEMORY,
                llm_provider=llm_provider,
                portia_api_key=self.settings.PORTIA_API_KEY if self.settings.PORTIA_API_KEY else None,
                default_log_level="INFO"
            )
            
            # Set LLM API key based on provider (skip if placeholder)
            if llm_provider == LLMProvider.OPENAI and self.settings.OPENAI_API_KEY:
                if "placeholder" not in self.settings.OPENAI_API_KEY.lower():
                    config.openai_api_key = SecretStr(self.settings.OPENAI_API_KEY)
                else:
                    logger.warning("Using placeholder OpenAI API key - some features may not work")
            elif llm_provider == LLMProvider.ANTHROPIC and self.settings.ANTHROPIC_API_KEY:
                if "placeholder" not in self.settings.ANTHROPIC_API_KEY.lower():
                    config.anthropic_api_key = SecretStr(self.settings.ANTHROPIC_API_KEY)
            elif llm_provider == LLMProvider.GOOGLE and self.settings.GOOGLE_API_KEY:
                if "placeholder" not in self.settings.GOOGLE_API_KEY.lower():
                    config.google_api_key = SecretStr(self.settings.GOOGLE_API_KEY)
            
            # Create tool registry with custom hiring tools
            tool_registry = DefaultToolRegistry(config)
            
            # Add custom hiring tools
            custom_tools = [
                LinkedInJobPostingTool(),
                LinkedInApplicationCollectorTool(),
                ResumeScreeningTool(),
                SkillsAnalysisTool(),
                InterviewSchedulingTool(),
                AIInterviewTool()
            ]
            
            # Combine default and custom tools
            tool_registry = tool_registry + custom_tools
            
            # Create execution hooks for human-in-the-loop
            execution_hooks = CLIExecutionHooks(
                before_tool_call=clarify_on_tool_calls([
                    "send_offer_letter",
                    "reject_candidate", 
                    "schedule_final_interview",
                    "ai_interview_conduct"
                ])
            )
            
            # Initialize Portia
            portia = Portia(
                config=config,
                tools=tool_registry,
                execution_hooks=execution_hooks
            )
            
            logger.info(f"Portia initialized with {llm_provider} provider")
            return portia
            
        except Exception as e:
            logger.error(f"Failed to initialize Portia: {e}")
            raise
    
    def _get_llm_provider(self) -> LLMProvider:
        """Determine which LLM provider to use based on available API keys"""
        if self.settings.OPENAI_API_KEY and "placeholder" not in self.settings.OPENAI_API_KEY.lower():
            return LLMProvider.OPENAI
        elif self.settings.ANTHROPIC_API_KEY and "placeholder" not in self.settings.ANTHROPIC_API_KEY.lower():
            return LLMProvider.ANTHROPIC
        elif self.settings.GOOGLE_API_KEY and "placeholder" not in self.settings.GOOGLE_API_KEY.lower():
            return LLMProvider.GOOGLE
        else:
            # Default to OpenAI for development with placeholder
            logger.warning("Using placeholder LLM configuration - defaulting to OpenAI")
            return LLMProvider.OPENAI
    
    async def create_hiring_workflow(self, job_data: Dict[str, Any], hr_user_id: str) -> Dict[str, Any]:
        """
        Create a complete hiring workflow for a job posting.
        
        Args:
            job_data: Job information and requirements
            hr_user_id: HR user ID for end user context
            
        Returns:
            Dict containing plan run information
        """
        try:
            # Create end user context
            end_user = EndUser(external_id=hr_user_id)
            
            # Create hiring workflow using Portia's built-in tools
            workflow_query = f"""
            Create a comprehensive hiring workflow for the {job_data.get('title', 'Software Engineer')} position.
            
            The workflow should:
            1. Monitor Gmail for job applications using 'portia:google:gmail:search_email'
            2. For each application email, extract candidate information
            3. Use 'llm_tool' to analyze resumes and score candidates
            4. Schedule interviews using 'portia:google:gcalendar:create_event'
            5. Send automated responses using 'portia:google:gmail:send_email'
            6. Notify HR team using 'portia:slack:bot:send_message'
            7. Track all candidates in a structured format
            
            Job Requirements: {job_data.get('requirements', [])}
            Job Description: {job_data.get('description', '')}
            """
            
            # Run the workflow
            plan_run = self.portia.run(
                query=workflow_query,
                end_user=end_user
            )
            
            return {
                "success": True,
                "plan_run_id": plan_run.id,
                "status": plan_run.state.value,
                "workflow_type": "hiring_automation",
                "job_title": job_data.get('title'),
                "created_at": plan_run.created_at.isoformat() if plan_run.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to create hiring workflow: {e}")
            return {
                "success": False,
                "error": str(e),
                "workflow_type": "hiring_automation"
            }

    async def process_email_applications(self, hr_email: str, job_keywords: List[str] = None) -> Dict[str, Any]:
        """
        Process job applications from HR email using Portia's Gmail tools.
        
        Args:
            hr_email: HR email address to monitor
            job_keywords: Keywords to search for in emails
            
        Returns:
            Dict containing processed applications
        """
        try:
            # Create end user context
            end_user = EndUser(external_id="hr_automation")
            
            # Use Portia's built-in Gmail search tool
            search_query = f"""
            Search Gmail inbox {hr_email} for job applications.
            
            Look for emails containing keywords: {job_keywords or ['application', 'resume', 'cv', 'job', 'position']}
            
            For each application email found:
            1. Extract sender information (name, email)
            2. Check for resume attachments
            3. Analyze email content for job interest
            4. Create a structured candidate profile
            5. Send automated acknowledgment email
            6. Notify HR team via Slack
            
            Use the following Portia tools:
            - 'portia:google:gmail:search_email' to find applications
            - 'llm_tool' to analyze email content and extract information
            - 'portia:google:gmail:send_email' to send responses
            - 'portia:slack:bot:send_message' to notify team
            """
            
            # Run the email processing workflow
            plan_run = self.portia.run(
                query=search_query,
                end_user=end_user
            )
            
            return {
                "success": True,
                "plan_run_id": plan_run.id,
                "status": plan_run.state.value,
                "email_monitored": hr_email,
                "keywords_used": job_keywords,
                "created_at": plan_run.created_at.isoformat() if plan_run.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to process email applications: {e}")
            return {
                "success": False,
                "error": str(e),
                "email_monitored": hr_email
            }

    async def schedule_interview(self, candidate_data: Dict[str, Any], interview_type: str = "technical") -> Dict[str, Any]:
        """
        Schedule interview using Portia's Google Calendar tools.
        
        Args:
            candidate_data: Candidate information
            interview_type: Type of interview (technical, behavioral, final)
            
        Returns:
            Dict containing interview scheduling result
        """
        try:
            # Create end user context
            end_user = EndUser(external_id="hr_automation")
            
            # Use Portia's built-in calendar tools
            scheduling_query = f"""
            Schedule a {interview_type} interview for candidate {candidate_data.get('name', 'Unknown')}.
            
            Candidate Details:
            - Name: {candidate_data.get('name')}
            - Email: {candidate_data.get('email')}
            - Position: {candidate_data.get('job_title', 'Software Engineer')}
            - Interview Type: {interview_type}
            
            Use the following Portia tools:
            1. 'portia:google:gcalendar:check_availability' to find available time slots
            2. 'portia:google:gcalendar:create_event' to schedule the interview
            3. 'portia:google:gmail:send_email' to send interview invitation
            4. 'portia:slack:bot:send_message' to notify HR team
            
            The interview should be:
            - 45 minutes long
            - Include video call link
            - Send calendar invite to candidate
            - Notify HR team via Slack
            """
            
            # Run the scheduling workflow
            plan_run = self.portia.run(
                query=scheduling_query,
                end_user=end_user
            )
            
            return {
                "success": True,
                "plan_run_id": plan_run.id,
                "status": plan_run.state.value,
                "candidate_name": candidate_data.get('name'),
                "interview_type": interview_type,
                "scheduled_at": plan_run.created_at.isoformat() if plan_run.created_at else None
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule interview: {e}")
            return {
                "success": False,
                "error": str(e),
                "candidate_name": candidate_data.get('name'),
                "interview_type": interview_type
            }
    
    async def screen_candidate(self, candidate_data: Dict[str, Any], job_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Screen a candidate for a specific job using AI analysis.
        
        Args:
            candidate_data: Candidate information and resume
            job_data: Job requirements and information
            
        Returns:
            Dict containing screening results
        """
        try:
            query = f"""
            Screen candidate for {job_data.get('title')} position:
            
            1. Parse resume and extract key information
            2. Analyze skills match against job requirements
            3. Evaluate experience level and background
            4. Generate AI screening score (0-1)
            5. Provide detailed recommendation with reasoning
            6. Identify any red flags or concerns
            """
            
            plan_run = self.portia.run(
                query,
                plan_run_inputs={
                    "candidate_data": candidate_data,
                    "job_data": job_data
                }
            )
            
            return {
                "success": True,
                "plan_run_id": str(plan_run.id),
                "screening_result": plan_run.outputs.final_output.value if plan_run.outputs.final_output else None,
                "status": plan_run.state
            }
            
        except Exception as e:
            logger.error(f"Failed to screen candidate: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def conduct_ai_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Conduct an AI-powered interview with voice cloning.
        
        Args:
            interview_data: Interview configuration and candidate information
            
        Returns:
            Dict containing interview results
        """
        try:
            query = f"""
            Conduct AI-powered technical interview:
            
            1. Set up voice cloning with interviewer's voice profile
            2. Generate role-specific technical questions
            3. Conduct interactive interview session
            4. Analyze candidate responses in real-time
            5. Evaluate technical skills and communication
            6. Generate comprehensive interview report with scores
            """
            
            plan_run = self.portia.run(
                query,
                plan_run_inputs={"interview_data": interview_data}
            )
            
            return {
                "success": True,
                "plan_run_id": str(plan_run.id),
                "interview_result": plan_run.outputs.final_output.value if plan_run.outputs.final_output else None,
                "status": plan_run.state
            }
            
        except Exception as e:
            logger.error(f"Failed to conduct AI interview: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def get_plan_run_status(self, plan_run_id: str) -> Dict[str, Any]:
        """
        Get current status of a plan run.
        
        Args:
            plan_run_id: Plan run identifier
            
        Returns:
            Dict containing plan run status and outputs
        """
        try:
            # TODO: Implement plan run retrieval from Portia storage
            # plan_run = self.portia.storage.get_plan_run(plan_run_id)
            
            return {
                "success": True,
                "plan_run_id": plan_run_id,
                "status": "placeholder",
                "current_step": 0,
                "outputs": {},
                "clarifications": []
            }
            
        except Exception as e:
            logger.error(f"Failed to get plan run status: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def resolve_clarification(self, plan_run_id: str, clarification_id: str, response: Any) -> Dict[str, Any]:
        """
        Resolve a clarification and resume plan execution.
        
        Args:
            plan_run_id: Plan run identifier
            clarification_id: Clarification identifier  
            response: User's response to the clarification
            
        Returns:
            Dict containing resolution result
        """
        try:
            # TODO: Implement clarification resolution
            # plan_run = self.portia.storage.get_plan_run(plan_run_id)
            # clarification = plan_run.get_clarification(clarification_id)
            # self.portia.resolve_clarification(plan_run, clarification, response)
            # self.portia.resume(plan_run)
            
            return {
                "success": True,
                "plan_run_id": plan_run_id,
                "clarification_id": clarification_id,
                "status": "resolved"
            }
            
        except Exception as e:
            logger.error(f"Failed to resolve clarification: {e}")
            return {
                "success": False,
                "error": str(e)
            }


@lru_cache()
def get_portia_service() -> PortiaService:
    """Get cached Portia service instance"""
    return PortiaService()
