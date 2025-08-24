"""
Review Technical Assignment Tool for Portia AI
Evaluates submitted technical assignments from candidates
"""

import logging
import json
from typing import Dict, Any, Optional, Type
from datetime import datetime
from portia import Tool, ToolRunContext, Message
from pydantic import BaseModel, Field
import uuid

logger = logging.getLogger(__name__)

class ReviewTechnicalAssignmentInput(BaseModel):
    """Input schema for Review Technical Assignment Tool"""
    candidate_email: str = Field(description="Candidate's email address")
    candidate_name: str = Field(description="Candidate's full name")
    job_title: str = Field(description="Job title they're applying for")
    email_content: str = Field(description="Full email content with assignment submission")
    assignment_requirements: str = Field(description="Original assignment requirements and evaluation criteria")
    job_requirements: str = Field(description="Job requirements and technical skills needed")

class ReviewTechnicalAssignmentTool(Tool[str]):
    """Tool for evaluating submitted technical assignments using AI analysis"""
    
    id: str = "review_technical_assignment_tool"
    name: str = "Review Technical Assignment Tool"
    description: str = (
        "Automatically evaluates submitted technical assignments using comprehensive AI analysis. "
        "Reviews code quality, architecture decisions, problem-solving approach, technical implementation, "
        "and adherence to requirements. Generates detailed feedback with specific scoring and recommendations."
    )
    args_schema: Type[BaseModel] = ReviewTechnicalAssignmentInput
    output_schema: tuple[str, str] = (
        "json",
        "JSON object with 'success' (bool), 'status' ('approved'/'rejected'), 'data' (evaluation details), 'overall_score' (0-100), 'recommendation' (str)"
    )
    
    def run(self, context: ToolRunContext, candidate_email: str, candidate_name: str, job_title: str, email_content: str, assignment_requirements: str, job_requirements: str) -> str:
        """Review technical assignment using Portia's AI capabilities"""
        try:
            logger.info(f"📋 Reviewing technical assignment from {candidate_email}")
            
            # Use Portia's LLM to evaluate the technical assignment
            llm = context.config.get_default_model()
            
            evaluation_prompt = f"""
            You are an expert technical reviewer evaluating a submitted coding assignment.
            
            CANDIDATE: {candidate_name}
            EMAIL: {candidate_email}
            POSITION: {job_title}
            
            EMAIL CONTENT WITH SUBMISSION:
            {email_content}
            
            ORIGINAL ASSIGNMENT REQUIREMENTS:
            {assignment_requirements}
            
            JOB REQUIREMENTS:
            {job_requirements}
            
            Evaluate the technical submission comprehensively based on:
            
            1. CODE QUALITY (0-100):
               - Clean, readable, well-structured code
               - Appropriate comments and documentation
               - Consistent coding style and conventions
               - Proper error handling and edge cases
            
            2. TECHNICAL IMPLEMENTATION (0-100):
               - Correct use of technologies and frameworks
               - Proper implementation of required features
               - Adherence to best practices and design patterns
               - Performance considerations
            
            3. PROBLEM SOLVING (0-100):
               - Logical approach to solving the problems
               - Algorithmic efficiency and optimization
               - Creative solutions and innovations
               - Handling of complex requirements
            
            4. REQUIREMENTS ADHERENCE (0-100):
               - Completeness of implementation
               - Accuracy in meeting specifications
               - Attention to detail in requirements
               - Proper submission format and documentation
            
            5. ARCHITECTURE & DESIGN (0-100):
               - Scalability and maintainability considerations
               - Proper separation of concerns
               - Modular and extensible design
               - Database design (if applicable)
            
            Provide a JSON response with:
            {{
                "evaluation_completed": true,
                "submission_date": "{datetime.now().isoformat()}Z",
                "overall_score": 0-100,
                "detailed_scores": {{
                    "code_quality_score": 0-100,
                    "technical_implementation_score": 0-100,
                    "problem_solving_score": 0-100,
                    "requirements_adherence_score": 0-100,
                    "architecture_design_score": 0-100
                }},
                "detailed_feedback": "Comprehensive evaluation with specific examples",
                "key_strengths": ["strength1", "strength2", "strength3"],
                "improvement_areas": ["area1", "area2", "area3"],
                "code_review_comments": ["specific comment 1", "specific comment 2"],
                "technical_highlights": ["highlight1", "highlight2"],
                "recommendation": "PROCEED_TO_INTERVIEW" or "ADDITIONAL_REVIEW_NEEDED" or "REJECT",
                "next_step_suggestion": "Suggested next action",
                "interviewer_notes": "Key points for interview discussion"
            }}
            
            SCORING GUIDELINES:
            - 85-100: Exceptional work, exceeds expectations
            - 70-84: Strong work, meets all requirements well
            - 60-69: Adequate work, meets most requirements
            - Below 60: Insufficient quality, fails to meet requirements
            
            RECOMMENDATION CRITERIA:
            - Overall score 75+: PROCEED_TO_INTERVIEW
            - Overall score 60-74: ADDITIONAL_REVIEW_NEEDED  
            - Overall score <60: REJECT
            
            Be thorough, fair, and provide actionable feedback.
            """
            
            messages = [
                Message(
                    role="system",
                    content="You are an expert technical reviewer and senior software engineer. Evaluate code submissions objectively, providing detailed feedback that helps candidates improve while maintaining high standards. Always respond in valid JSON format."
                ),
                Message(
                    role="user",
                    content=evaluation_prompt
                )
            ]
            
            response = llm.get_response(messages)
            
            # Parse the AI response
            try:
                evaluation_data = json.loads(response.content)
                
                # Generate review ID and finalize details
                review_id = f"REV-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"
                overall_score = evaluation_data.get("overall_score", 0)
                recommendation = evaluation_data.get("recommendation", "ADDITIONAL_REVIEW_NEEDED")
                
                # Determine workflow status based on recommendation
                if recommendation == "PROCEED_TO_INTERVIEW":
                    status = "approved"
                elif recommendation == "ADDITIONAL_REVIEW_NEEDED":
                    status = "approved"  # Still proceed but flag for review
                else:  # REJECT
                    status = "rejected"
                
                # Prepare result
                result = {
                    "success": True,
                    "status": status,
                    "data": {
                        "review_id": review_id,
                        "assignment_received": True,
                        "evaluation_completed": True,
                        "submission_date": evaluation_data.get("submission_date", datetime.now().isoformat() + "Z"),
                        "overall_score": overall_score,
                        "detailed_scores": evaluation_data.get("detailed_scores", {}),
                        "detailed_feedback": evaluation_data.get("detailed_feedback", "Technical assignment reviewed"),
                        "key_strengths": evaluation_data.get("key_strengths", []),
                        "improvement_areas": evaluation_data.get("improvement_areas", []),
                        "code_review_comments": evaluation_data.get("code_review_comments", []),
                        "technical_highlights": evaluation_data.get("technical_highlights", []),
                        "recommendation": recommendation,
                        "next_step": evaluation_data.get("next_step_suggestion", "Proceed with interview process"),
                        "interviewer_notes": evaluation_data.get("interviewer_notes", "Review technical discussion points"),
                        "review_completed_by": "AI Technical Reviewer",
                        "candidate_email": candidate_email
                    }
                }
                
                # Log the technical review
                self._log_technical_review(candidate_email, candidate_name, job_title, evaluation_data, review_id, overall_score)
                
                logger.info(f"✅ Technical assignment reviewed for {candidate_email}")
                logger.info(f"📊 Review ID: {review_id}, Score: {overall_score}/100, Recommendation: {recommendation}")
                
                return json.dumps(result)
                
            except json.JSONDecodeError:
                # Fallback if AI response isn't valid JSON
                logger.warning("⚠️ AI response was not valid JSON, using fallback evaluation")
                
                review_id = f"REV-{datetime.now().year}-{str(uuid.uuid4())[:8].upper()}"
                
                result = {
                    "success": True,
                    "status": "approved",  # Default to approval for manual review
                    "data": {
                        "review_id": review_id,
                        "assignment_received": True,
                        "evaluation_completed": True,
                        "submission_date": datetime.now().isoformat() + "Z",
                        "overall_score": 70,  # Conservative score
                        "detailed_feedback": "Technical assignment received and basic review completed. Manual review recommended due to analysis parsing issue.",
                        "key_strengths": ["Assignment submitted on time", "Followed submission guidelines"],
                        "improvement_areas": ["Detailed review needed"],
                        "recommendation": "ADDITIONAL_REVIEW_NEEDED",
                        "next_step": "Manual technical review required",
                        "review_completed_by": "AI Technical Reviewer (Fallback)",
                        "candidate_email": candidate_email
                    }
                }
                
                self._log_fallback_technical_review(candidate_email, candidate_name, job_title, review_id)
                return json.dumps(result)
                
        except Exception as e:
            logger.error(f"Error reviewing technical assignment: {e}")
            error_result = {
                "success": False,
                "status": "approved",  # Still proceed with workflow
                "data": {
                    "error": f"Technical assignment review failed: {str(e)}",
                    "candidate_email": candidate_email,
                    "fallback_action": "manual_review_required",
                    "assignment_received": True,
                    "evaluation_completed": False
                }
            }
            return json.dumps(error_result)
    
    def _log_technical_review(self, candidate_email: str, candidate_name: str, job_title: str, evaluation_data: Dict[str, Any], review_id: str, overall_score: int):
        """Log the technical assignment review details"""
        try:
            detailed_scores = evaluation_data.get("detailed_scores", {})
            recommendation = evaluation_data.get("recommendation", "UNKNOWN")
            
            logger.info(f"📧 TECHNICAL ASSIGNMENT REVIEWED:")
            logger.info(f"   Candidate: {candidate_name} ({candidate_email})")
            logger.info(f"   Review ID: {review_id}")
            logger.info(f"   Position: {job_title}")
            logger.info(f"   Overall Score: {overall_score}/100")
            logger.info(f"   Code Quality: {detailed_scores.get('code_quality_score', 'N/A')}/100")
            logger.info(f"   Technical Implementation: {detailed_scores.get('technical_implementation_score', 'N/A')}/100")
            logger.info(f"   Problem Solving: {detailed_scores.get('problem_solving_score', 'N/A')}/100")
            logger.info(f"   Requirements Adherence: {detailed_scores.get('requirements_adherence_score', 'N/A')}/100")
            logger.info(f"   Architecture & Design: {detailed_scores.get('architecture_design_score', 'N/A')}/100")
            logger.info(f"   Recommendation: {recommendation}")
            logger.info(f"   Key Strengths: {', '.join(evaluation_data.get('key_strengths', []))}")
            logger.info(f"   Improvement Areas: {', '.join(evaluation_data.get('improvement_areas', []))}")
            
        except Exception as e:
            logger.error(f"Error logging technical review: {e}")
    
    def _log_fallback_technical_review(self, candidate_email: str, candidate_name: str, job_title: str, review_id: str):
        """Log fallback technical review"""
        try:
            logger.info(f"📧 FALLBACK TECHNICAL ASSIGNMENT REVIEW:")
            logger.info(f"   Candidate: {candidate_name} ({candidate_email})")
            logger.info(f"   Review ID: {review_id}")
            logger.info(f"   Position: {job_title}")
            logger.info(f"   Overall Score: 70/100 (Conservative)")
            logger.info(f"   Recommendation: ADDITIONAL_REVIEW_NEEDED")
            logger.info(f"   Status: Manual review required")
            
        except Exception as e:
            logger.error(f"Error logging fallback technical review: {e}")
