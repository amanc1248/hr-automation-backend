"""
Portia service for managing AI agents and plan runs.
Central orchestration point for all Portia-related operations.
"""

from portia import Portia, Config, LLMProvider, StorageClass, DefaultToolRegistry
from portia.cli import CLIExecutionHooks
from portia.execution_hooks import clarify_on_tool_calls
from portia.end_user import EndUser
from typing import Dict, Any, Optional
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
    AIInterviewTool,
    EmailNotificationTool,
    CommunicationTool,
    EmailMonitoringTool,
    ResumeProcessingTool,
    CandidateNotificationTool
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
                AIInterviewTool(),
                EmailNotificationTool(),
                CommunicationTool(),
                EmailMonitoringTool(),
                ResumeProcessingTool(),
                CandidateNotificationTool()
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
            query = f"""
            Execute comprehensive hiring process for {job_data.get('title', 'Software Engineer')}:
            
            Phase 1: Job Creation & Distribution
            1. Create compelling job posting with requirements
            2. Post to LinkedIn and selected platforms
            3. Set up automated application collection system
            
            Phase 2: Application Processing  
            4. Parse and analyze incoming resumes
            5. Screen candidates using AI analysis
            6. Rank candidates by job fit score
            
            Phase 3: Interview Process
            7. Schedule initial screening interviews
            8. Conduct AI-powered technical interviews
            9. Collect feedback from human interviewers
            
            Phase 4: Decision Making
            10. Generate comprehensive candidate reports
            11. Make hiring recommendations
            12. Handle offer letters and rejections
            """
            
            # Create end user context
            end_user = EndUser(
                external_id=hr_user_id,
                email="hr@company.com",  # TODO: Get from user data
                additional_data={"job_data": job_data}
            )
            
            # Execute plan
            plan_run = self.portia.run(
                query,
                end_user=end_user,
                plan_run_inputs={"job_data": job_data}
            )
            
            return {
                "success": True,
                "plan_run_id": str(plan_run.id),
                "status": plan_run.state,
                "current_step": plan_run.current_step_index,
                "message": "Hiring workflow created successfully"
            }
            
        except Exception as e:
            logger.error(f"Failed to create hiring workflow: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Failed to create hiring workflow"
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
    
    async def schedule_interview(self, interview_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Schedule an interview using AI coordination.
        
        Args:
            interview_data: Interview details and participant information
            
        Returns:
            Dict containing scheduling results
        """
        try:
            query = f"""
            Schedule interview for candidate:
            
            1. Check interviewer availability in calendar
            2. Find optimal time slots for all participants
            3. Send calendar invites with meeting details
            4. Create meeting links (Zoom/Teams)
            5. Send confirmation emails to all parties
            6. Set up reminder notifications
            """
            
            plan_run = self.portia.run(
                query,
                plan_run_inputs={"interview_data": interview_data}
            )
            
            return {
                "success": True,
                "plan_run_id": str(plan_run.id),
                "scheduling_result": plan_run.outputs.final_output.value if plan_run.outputs.final_output else None,
                "status": plan_run.state
            }
            
        except Exception as e:
            logger.error(f"Failed to schedule interview: {e}")
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
