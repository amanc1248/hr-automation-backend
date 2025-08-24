"""
Send Offer Letter Tool for HR Workflow
Generates comprehensive job offer letters
"""

import logging
import json
from typing import Dict, Any, Optional, Type
from datetime import datetime, timedelta
from portia import Tool, ToolRunContext, Message
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class SendOfferLetterInput(BaseModel):
    """Input schema for Send Offer Letter Tool"""
    candidate_email: str = Field(description="Candidate's email address")
    candidate_name: str = Field(description="Candidate's full name")
    job_title: str = Field(description="Job title for which the offer is being extended")
    job_level: str = Field(default="Mid-Level", description="Seniority level of the job")
    start_date: Optional[str] = Field(default=None, description="Proposed start date (YYYY-MM-DD)")
    salary_range: Optional[str] = Field(default=None, description="Proposed salary range or amount")

class SendOfferLetterTool(Tool[str]):
    """AI-powered job offer letter generation tool"""
    
    id: str = "send_offer_letter_tool"
    name: str = "Send Offer Letter Tool"
    description: str = (
        "Generates a comprehensive job offer letter with competitive compensation packages, benefits, and terms. "
        "Creates personalized, professional offers based on role requirements, candidate assessment, and company standards. "
        "Returns complete offer details ready for email delivery with clear acceptance instructions and timeline."
    )
    args_schema: Type[BaseModel] = SendOfferLetterInput
    output_schema: tuple[str, str] = (
        "json",
        "JSON object with 'success' (bool), 'status' ('approved'), 'offer_sent' (bool), 'data' (offer details)"
    )

    def run(self, context: ToolRunContext, candidate_email: str, candidate_name: str, job_title: str, job_level: str, start_date: Optional[str], salary_range: Optional[str]) -> str:
        """Generate a comprehensive job offer letter"""
        try:
            logger.info(f"💼 Generating job offer letter for {candidate_email}")
            
            # Use Portia's LLM to generate offer content
            llm = context.config.get_default_model()
            
            # Set default start date if not provided
            if not start_date:
                proposed_start = datetime.now() + timedelta(weeks=2)
                start_date = proposed_start.strftime("%Y-%m-%d")
            
            # Set default salary range if not provided
            if not salary_range:
                salary_ranges = {
                    "junior": "$70,000 - $90,000",
                    "mid": "$90,000 - $120,000", 
                    "senior": "$120,000 - $150,000",
                    "lead": "$150,000 - $180,000"
                }
                salary_range = salary_ranges.get(job_level.lower().split("-")[0], "$90,000 - $120,000")
            
            offer_prompt = f"""
            Generate a comprehensive job offer letter for a successful candidate.
            
            Candidate: {candidate_name} ({candidate_email})
            Position: {job_title}
            Level: {job_level}
            Start Date: {start_date}
            Salary Range: {salary_range}
            
            Create a complete job offer letter that includes:
            1. Congratulatory opening and excitement to extend offer
            2. Position details and department
            3. Comprehensive compensation package (salary, bonus, equity)
            4. Complete benefits overview (health, PTO, professional development)
            5. Employment terms and conditions
            6. Clear next steps and acceptance timeline
            7. Contact information for questions
            8. Professional yet celebratory tone
            
            Make it feel personalized and exciting while maintaining professionalism.
            Format as a complete offer letter ready for email delivery.
            """
            
            messages = [
                Message(role="system", content="You are an expert HR professional creating compelling job offer letters."),
                Message(role="user", content=offer_prompt)
            ]
            
            try:
                response = llm.get_response(messages)
                offer_content = response.value if hasattr(response, 'value') else str(response)
                
                # Calculate offer validity date (1 week from now)
                offer_valid_until = datetime.now() + timedelta(days=7)
                
                result = {
                    "success": True,
                    "status": "approved",
                    "offer_sent": False,  # Will be handled by email tool in Portia
                    "data": {
                        "offer_id": f"OFFER-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}",
                        "candidate_email": candidate_email,
                        "candidate_name": candidate_name,
                        "job_title": job_title,
                        "job_level": job_level,
                        "offer_date": datetime.now().isoformat(),
                        "offer_valid_until": offer_valid_until.isoformat(),
                        "start_date": start_date,
                        "base_salary": salary_range,
                        "benefits_included": [
                            "Health insurance", "401k", "PTO", "Remote work",
                            "Professional development", "Stock options"
                        ],
                        "employment_type": "full_time",
                        "equity_offered": True,
                        "bonus_eligible": True,
                        "remote_policy": "hybrid",
                        "offer_letter_content": offer_content,
                        "acceptance_deadline_days": 7,
                        "next_steps": [
                            "Review offer carefully",
                            "Contact HR with questions", 
                            "Respond within 7 days"
                        ],
                        "hr_contact": "hr@company.com",
                        "generated_at": datetime.now().isoformat()
                    }
                }
                
                logger.info(f"✅ Job offer generated successfully for {candidate_name}")
                logger.info(f"💰 Salary: {salary_range}")
                logger.info(f"📅 Start Date: {start_date}")
                logger.info(f"⏰ Valid Until: {offer_valid_until.strftime('%Y-%m-%d')}")
                
                return json.dumps(result)
                
            except Exception as llm_error:
                logger.warning(f"⚠️ LLM offer generation failed: {llm_error}, using fallback")
                
                # Fallback offer content
                offer_valid_until = datetime.now() + timedelta(days=7)
                fallback_offer = f"""
Job Offer - {job_title}

Dear {candidate_name},

Congratulations! We are thrilled to extend a formal job offer for the {job_title} position.

JOB OFFER DETAILS:
Position: {job_title}
Level: {job_level}
Department: Engineering
Start Date: {start_date}
Employment Type: Full-time
Location: Remote/Hybrid (flexible)

COMPENSATION PACKAGE:
Base Salary: {salary_range} annually
Performance Bonus: Up to 15% of annual salary
Stock Options: Equity package included
Benefits: Comprehensive package

BENEFITS & PERKS:
• Medical, dental, and vision insurance
• 25 days PTO + company holidays
• $3,000 annual learning budget
• Flexible work arrangements
• 401(k) with company matching
• Life and disability insurance

NEXT STEPS:
1. Review this offer carefully
2. Contact HR with questions: hr@company.com
3. Respond by {offer_valid_until.strftime('%B %d, %Y')}

We're excited about the expertise you'll bring to our team!

Best regards,
HR Team
"""
                
                result = {
                    "success": True,
                    "status": "approved",
                    "offer_sent": False,
                    "data": {
                        "offer_id": f"OFFER-{datetime.now().year}-{datetime.now().strftime('%m%d%H%M')}",
                        "candidate_email": candidate_email,
                        "candidate_name": candidate_name,
                        "job_title": job_title,
                        "job_level": job_level,
                        "offer_date": datetime.now().isoformat(),
                        "offer_valid_until": offer_valid_until.isoformat(),
                        "start_date": start_date,
                        "base_salary": salary_range,
                        "benefits_included": [
                            "Health insurance", "401k", "PTO", "Remote work"
                        ],
                        "employment_type": "full_time",
                        "equity_offered": True,
                        "bonus_eligible": True,
                        "remote_policy": "hybrid",
                        "offer_letter_content": fallback_offer,
                        "acceptance_deadline_days": 7,
                        "next_steps": [
                            "Review offer carefully",
                            "Contact HR with questions",
                            "Respond within 7 days"
                        ],
                        "hr_contact": "hr@company.com",
                        "generated_at": datetime.now().isoformat()
                    }
                }
                
                return json.dumps(result)
                
        except Exception as e:
            logger.error(f"Error generating job offer: {e}")
            
            error_result = {
                "success": False,
                "status": "approved",  # Still proceed with workflow
                "offer_sent": False,
                "data": {
                    "error": f"Offer generation failed: {str(e)}",
                    "candidate_email": candidate_email,
                    "fallback_message": "Job offer will be prepared manually"
                }
            }
            
            return json.dumps(error_result)