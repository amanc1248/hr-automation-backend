"""
LinkedIn API client for HR Automation System.
Handles real LinkedIn API integration for job posting and application collection.
"""

import logging
import httpx
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.config.settings import get_settings

logger = logging.getLogger(__name__)

class LinkedInJobPost(BaseModel):
    """LinkedIn job post data structure"""
    title: str = Field(description="Job title")
    description: str = Field(description="Job description")
    location: str = Field(description="Job location")
    employment_type: str = Field(description="Employment type")
    experience_level: str = Field(description="Experience level")
    requirements: List[str] = Field(description="Job requirements")
    benefits: List[str] = Field(description="Job benefits")
    company_name: str = Field(description="Company name")
    salary_range: Optional[Dict[str, Any]] = Field(default=None, description="Salary range")

class LinkedInApplication(BaseModel):
    """LinkedIn application data structure"""
    application_id: str = Field(description="LinkedIn application ID")
    candidate_name: str = Field(description="Candidate name")
    candidate_email: str = Field(description="Candidate email")
    candidate_linkedin: str = Field(description="Candidate LinkedIn profile")
    resume_url: Optional[str] = Field(default=None, description="Resume URL")
    application_date: str = Field(description="Application date")
    status: str = Field(description="Application status")

class LinkedInClient:
    """LinkedIn API client for job posting and application collection"""
    
    def __init__(self):
        self.settings = get_settings()
        self.base_url = "https://api.linkedin.com/v2"
        self.access_token = self.settings.LINKEDIN_ACCESS_TOKEN
        self.company_id = getattr(self.settings, 'LINKEDIN_COMPANY_ID', None)
        
        if not self.access_token:
            logger.warning("LinkedIn access token not configured - using mock mode")
            self.mock_mode = True
        else:
            self.mock_mode = False
            self.headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
                "X-Restli-Protocol-Version": "2.0.0"
            }
    
    async def post_job(self, job_data: LinkedInJobPost) -> Dict[str, Any]:
        """
        Post a job to LinkedIn using the UGC Posts API
        
        Args:
            job_data: Job information to post
            
        Returns:
            Dict containing posting result and LinkedIn job ID
        """
        try:
            if self.mock_mode:
                return await self._mock_post_job(job_data)
            
            # Format job content for LinkedIn
            linkedin_content = self._format_job_for_linkedin(job_data)
            
            # Create UGC post
            post_data = {
                "author": f"urn:li:organization:{self.company_id}",
                "lifecycleState": "PUBLISHED",
                "specificContent": {
                    "com.linkedin.ugc.ShareContent": {
                        "shareCommentary": {
                            "text": linkedin_content["commentary"]
                        },
                        "shareMediaCategory": "NONE"
                    }
                },
                "visibility": {
                    "com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"
                }
            }
            
            # Post to LinkedIn
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/ugcPosts",
                    headers=self.headers,
                    json=post_data
                )
                response.raise_for_status()
                
                result = response.json()
                post_id = result.get("id")
                
                logger.info(f"Successfully posted job '{job_data.title}' to LinkedIn")
                
                return {
                    "success": True,
                    "linkedin_post_id": post_id,
                    "linkedin_url": f"https://linkedin.com/feed/update/{post_id}",
                    "message": "Job posted to LinkedIn successfully"
                }
                
        except httpx.HTTPStatusError as e:
            logger.error(f"LinkedIn API error: {e.response.status_code} - {e.response.text}")
            return {
                "success": False,
                "error": f"LinkedIn API error: {e.response.status_code}",
                "details": e.response.text
            }
        except Exception as e:
            logger.error(f"Failed to post job to LinkedIn: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def collect_applications(self, job_id: str, max_applications: int = 50) -> Dict[str, Any]:
        """
        Collect applications from a LinkedIn job posting
        
        Args:
            job_id: LinkedIn job posting ID
            max_applications: Maximum applications to collect
            
        Returns:
            Dict containing collected applications
        """
        try:
            if self.mock_mode:
                return await self._mock_collect_applications(job_id, max_applications)
            
            # LinkedIn doesn't provide direct access to job applications via API
            # This would require LinkedIn Talent Solutions or Recruiter account
            # For now, we'll return a placeholder with instructions
            
            logger.warning("LinkedIn job applications require Talent Solutions account")
            
            return {
                "success": False,
                "error": "LinkedIn job applications require Talent Solutions or Recruiter account",
                "suggestion": "Consider using LinkedIn's job posting with application redirect to your system",
                "job_id": job_id,
                "applications_count": 0,
                "applications": []
            }
            
        except Exception as e:
            logger.error(f"Failed to collect applications from LinkedIn: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    async def get_company_info(self) -> Dict[str, Any]:
        """Get company information from LinkedIn"""
        try:
            if self.mock_mode or not self.company_id:
                return {
                    "success": False,
                    "error": "Company ID not configured or in mock mode"
                }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/organizations/{self.company_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                
                company_data = response.json()
                
                return {
                    "success": True,
                    "company_name": company_data.get("localizedName"),
                    "company_description": company_data.get("description"),
                    "follower_count": company_data.get("followerCount"),
                    "company_id": self.company_id
                }
                
        except Exception as e:
            logger.error(f"Failed to get company info from LinkedIn: {e}")
            return {
                "success": False,
                "error": str(e)
            }
    
    def _format_job_for_linkedin(self, job_data: LinkedInJobPost) -> Dict[str, str]:
        """Format job data for LinkedIn posting"""
        # Create compelling job post content
        commentary = f"""
🚀 We're hiring! {job_data.title}

📍 Location: {job_data.location}
💼 Type: {job_data.employment_type}
🎯 Level: {job_data.experience_level}

📋 What you'll do:
{chr(10).join([f"• {req}" for req in job_data.requirements[:5]])}

🎁 Benefits:
{chr(10).join([f"• {benefit}" for benefit in job_data.benefits[:3]])}

{job_data.description[:200]}{"..." if len(job_data.description) > 200 else ""}

#hiring #jobs #tech #engineering #careers

Interested? Apply now! 🚀
        """.strip()
        
        return {
            "commentary": commentary,
            "title": job_data.title,
            "company": job_data.company_name
        }
    
    async def _mock_post_job(self, job_data: LinkedInJobPost) -> Dict[str, Any]:
        """Mock job posting for testing"""
        import uuid
        
        mock_post_id = f"urn:li:activity:{uuid.uuid4()}"
        
        logger.info(f"Mock LinkedIn job posting - Job: {job_data.title}")
        
        return {
            "success": True,
            "linkedin_post_id": mock_post_id,
            "linkedin_url": f"https://linkedin.com/feed/update/{mock_post_id}",
            "message": "Mock job posting successful (LinkedIn API not configured)",
            "mock_mode": True
        }
    
    async def _mock_collect_applications(self, job_id: str, max_applications: int) -> Dict[str, Any]:
        """Mock application collection for testing"""
        import uuid
        from datetime import datetime
        
        mock_applications = []
        for i in range(min(5, max_applications)):
            mock_applications.append(LinkedInApplication(
                application_id=str(uuid.uuid4()),
                candidate_name=f"Mock Candidate {i+1}",
                candidate_email=f"candidate{i+1}@example.com",
                candidate_linkedin=f"https://linkedin.com/in/candidate{i+1}",
                resume_url=f"https://example.com/resume{i+1}.pdf",
                application_date=datetime.now().isoformat(),
                status="applied"
            ))
        
        logger.info(f"Mock LinkedIn application collection - {len(mock_applications)} applications")
        
        return {
            "success": True,
            "job_id": job_id,
            "applications_count": len(mock_applications),
            "applications": [app.model_dump() for app in mock_applications],
            "mock_mode": True
        }
    
    def is_configured(self) -> bool:
        """Check if LinkedIn API is properly configured"""
        return (
            self.settings.LINKEDIN_CLIENT_ID and
            self.settings.LINKEDIN_CLIENT_SECRET and
            self.settings.LINKEDIN_ACCESS_TOKEN and
            not self.mock_mode
        )
