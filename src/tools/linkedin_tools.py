"""
LinkedIn integration tools for HR Automation System.
Handles job posting and application collection from LinkedIn.
"""

import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from portia import Tool, ToolRunContext
from src.services.linkedin_client import LinkedInClient, LinkedInJobPost, LinkedInApplication

logger = logging.getLogger(__name__)

class LinkedInJobData(BaseModel):
    """Schema for LinkedIn job posting data"""
    title: str = Field(description="Job title")
    description: str = Field(description="Job description")
    location: str = Field(description="Job location")
    employment_type: str = Field(description="Employment type (full-time, part-time, etc.)")
    experience_level: str = Field(description="Experience level required")
    salary_range: Optional[Dict[str, Any]] = Field(default=None, description="Salary range")
    requirements: List[str] = Field(default_factory=list, description="Job requirements")
    benefits: List[str] = Field(default_factory=list, description="Job benefits")
    company_name: str = Field(description="Company name")
    company_description: Optional[str] = Field(default=None, description="Company description")

class LinkedInJobPostingTool(Tool[str]):
    """Tool for posting jobs to LinkedIn"""
    
    id: str = "linkedin_job_posting"
    name: str = "LinkedIn Job Posting Tool"
    description: str = "Post jobs to LinkedIn and return the job posting ID"
    args_schema: type[BaseModel] = LinkedInJobData
    output_schema: tuple[str, str] = ("str", "LinkedIn job posting ID and URL")
    
    async def run(self, ctx: ToolRunContext, **kwargs) -> str:
        """Post a job to LinkedIn"""
        try:
            # Create LinkedIn client
            linkedin_client = LinkedInClient()
            
            # Convert to LinkedInJobPost format
            job_data = LinkedInJobPost(
                title=kwargs.get("title"),
                description=kwargs.get("description"),
                location=kwargs.get("location"),
                employment_type=kwargs.get("employment_type"),
                experience_level=kwargs.get("experience_level"),
                requirements=kwargs.get("requirements", []),
                benefits=kwargs.get("benefits", []),
                company_name=kwargs.get("company_name"),
                salary_range=kwargs.get("salary_range")
            )
            
            # Post to LinkedIn using real API client
            result = await linkedin_client.post_job(job_data)
            
            if result["success"]:
                logger.info(f"Successfully posted job '{job_data.title}' to LinkedIn")
                return f"Job posted to LinkedIn successfully! Post ID: {result['linkedin_post_id']}, URL: {result['linkedin_url']}"
            else:
                raise Exception(f"LinkedIn API error: {result.get('error', 'Unknown error')}")
            
        except Exception as e:
            logger.error(f"Failed to post job to LinkedIn: {e}")
            raise Exception(f"LinkedIn job posting failed: {str(e)}")

class LinkedInJobArgs(BaseModel):
    """Schema for LinkedIn job arguments"""
    job_id: str = Field(description="LinkedIn job posting ID")
    max_applications: int = Field(default=50, description="Maximum applications to collect")

class LinkedInApplicationCollectorTool(Tool[Dict[str, Any]]):
    """Tool for collecting applications from LinkedIn job postings"""
    
    id: str = "linkedin_application_collector"
    name: str = "LinkedIn Application Collector"
    description: str = "Collect and parse job applications from LinkedIn job postings"
    args_schema: type[BaseModel] = LinkedInJobArgs
    output_schema: tuple[str, str] = ("json", "Collection of LinkedIn applications with candidate data")
    
    async def run(self, ctx: ToolRunContext, job_id: str, max_applications: int = 50) -> Dict[str, Any]:
        """Collect applications from a LinkedIn job posting"""
        try:
            # Create LinkedIn client
            linkedin_client = LinkedInClient()
            
            # Collect applications using real API client
            result = await linkedin_client.collect_applications(job_id, max_applications)
            
            if result["success"]:
                logger.info(f"Collected {result['applications_count']} applications from LinkedIn job {job_id}")
                return result
            else:
                logger.warning(f"LinkedIn application collection: {result.get('error')}")
                return result
            
        except Exception as e:
            logger.error(f"Failed to collect applications from LinkedIn: {e}")
            raise Exception(f"LinkedIn application collection failed: {str(e)}")
