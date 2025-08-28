"""
Approval API endpoints for workflow step approvals
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
from uuid import UUID
from datetime import datetime

from core.database import get_db
from api.auth import get_current_user
from models.user import Profile
from models.approval import WorkflowApprovalRequest, WorkflowApproval
from models.workflow import WorkflowStepDetail, WorkflowStep, CandidateWorkflow
from models.job import Job
from models.candidate import Candidate
from schemas.approval import (
    ApprovalRequestResponse, 
    ApprovalRequestsList,
    ApprovalSubmission,
    ApprovalSubmissionResponse
)

router = APIRouter(prefix="/api/approvals", tags=["approvals"])

@router.get("/pending", response_model=ApprovalRequestsList)
async def get_pending_approvals(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Get all pending approval requests for the current user"""
    try:
        # Check if user is admin
        is_admin = current_user.role.name == "admin"
        
        # Build the base query
        base_query = select(
            WorkflowApprovalRequest,
            WorkflowStepDetail,
            WorkflowStep,
            CandidateWorkflow,
            Job,
            Candidate
        ).join(
            WorkflowStepDetail, WorkflowApprovalRequest.workflow_step_detail_id == WorkflowStepDetail.id
        ).join(
            WorkflowStep, WorkflowStepDetail.workflow_step_id == WorkflowStep.id
        ).join(
            CandidateWorkflow, WorkflowApprovalRequest.candidate_workflow_id == CandidateWorkflow.id
        ).join(
            Job, CandidateWorkflow.job_id == Job.id
        ).join(
            Candidate, CandidateWorkflow.candidate_id == Candidate.id
        ).outerjoin(
            WorkflowApproval, WorkflowApproval.approval_request_id == WorkflowApprovalRequest.id
        ).where(
            WorkflowApprovalRequest.status == 'pending',
            WorkflowApproval.id.is_(None)  # No response yet
        )
        
        # If not admin, filter to only show approvals assigned to this user
        if not is_admin:
            base_query = base_query.where(
                WorkflowApprovalRequest.approver_user_id == current_user.id
            )
        
        # Execute the query
        requests_result = await db.execute(base_query)
        
        requests_data = requests_result.fetchall()
        
        approval_requests = []
        for request_data in requests_data:
            approval_request, step_detail, workflow_step, candidate_workflow, job, candidate = request_data
            
            # Determine if current user can approve this request
            can_approve = approval_request.approver_user_id == current_user.id
            
            approval_requests.append(
                ApprovalRequestResponse(
                    id=approval_request.id,
                    candidate_workflow_id=approval_request.candidate_workflow_id,
                    workflow_step_detail_id=approval_request.workflow_step_detail_id,
                    required_approvals=approval_request.required_approvals,
                    status=approval_request.status,
                    requested_at=approval_request.requested_at,
                    
                    # User permissions
                    can_approve=can_approve,
                    
                    # Workflow step info
                    step_name=workflow_step.name,
                    step_description=workflow_step.description,
                    step_display_name=workflow_step.display_name,
                    step_type=workflow_step.step_type,
                    
                    # Candidate info
                    candidate_name=f"{candidate.first_name} {candidate.last_name}",
                    candidate_email=candidate.email,
                    
                    # Job info
                    job_title=job.title,
                    job_department=job.department,
                )
            )
        
        return ApprovalRequestsList(
            requests=approval_requests,
            total_count=len(approval_requests)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch pending approvals: {str(e)}"
        )

@router.post("/respond", response_model=ApprovalSubmissionResponse)
async def submit_approval_response(
    approval_data: ApprovalSubmission,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Submit approval or rejection for a workflow step"""
    try:
        # Verify the approval request exists and belongs to the current user
        request_result = await db.execute(
            select(WorkflowApprovalRequest).where(
                WorkflowApprovalRequest.id == approval_data.approval_request_id,
                WorkflowApprovalRequest.approver_user_id == current_user.id,
                WorkflowApprovalRequest.status == 'pending'
            )
        )
        approval_request = request_result.scalar_one_or_none()
        
        if not approval_request:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found or not authorized"
            )
        
        # Check if user has already responded
        existing_response_result = await db.execute(
            select(WorkflowApproval).where(
                WorkflowApproval.approval_request_id == approval_request.id
            )
        )
        existing_response = existing_response_result.scalar_one_or_none()
        
        if existing_response:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already responded to this approval request"
            )
        
        # Create the approval response
        approval_response = WorkflowApproval(
            approval_request_id=approval_request.id,
            decision=approval_data.decision,
            comments=approval_data.comments,
            responded_at=datetime.utcnow()
        )
        
        db.add(approval_response)
        
        # Update approval request status to match the decision
        approval_request.status = approval_data.decision  # 'approved' or 'rejected'
        approval_request.completed_at = datetime.utcnow()
        
        await db.commit()
        
        # Check if all required approvals are received and trigger workflow continuation
        await _check_and_continue_workflow(db, approval_request)
        
        return ApprovalSubmissionResponse(
            success=True,
            message=f"Approval {approval_data.decision} submitted successfully",
            approval_id=approval_response.id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to submit approval response: {str(e)}"
        )

async def _check_and_continue_workflow(db: AsyncSession, approval_request: WorkflowApprovalRequest):
    """Check if workflow can continue and trigger continuation if ready"""
    try:
        from sqlalchemy import select
        from models.approval import WorkflowApproval
        from models.workflow import CandidateWorkflow, WorkflowStepDetail
        from models.candidate import Candidate
        from models.job import Job
        from services.email_polling_service import EmailPollingService
        import logging
        
        logger = logging.getLogger(__name__)
        logger.info(f"🔍 Checking workflow continuation for approval request: {approval_request.id}")
        
        # Get all approval requests for this step
        all_requests_result = await db.execute(
            select(WorkflowApprovalRequest).where(
                WorkflowApprovalRequest.candidate_workflow_id == approval_request.candidate_workflow_id,
                WorkflowApprovalRequest.workflow_step_detail_id == approval_request.workflow_step_detail_id
            )
        )
        all_requests = all_requests_result.scalars().all()
        
        logger.info(f"   📊 Found {len(all_requests)} total approval requests for this step")
        
        # Get all responses (approvals) for these requests
        approval_responses_result = await db.execute(
            select(WorkflowApproval).where(
                WorkflowApproval.approval_request_id.in_([req.id for req in all_requests])
            )
        )
        approval_responses = approval_responses_result.scalars().all()
        
        logger.info(f"   📝 Found {len(approval_responses)} responses from approvers")
        
        # Check if all approvers have responded
        responded_request_ids = {resp.approval_request_id for resp in approval_responses}
        all_request_ids = {req.id for req in all_requests}
        
        if responded_request_ids != all_request_ids:
            logger.info(f"   ⏳ Not all approvers have responded yet")
            logger.info(f"   📊 Responded: {len(responded_request_ids)}/{len(all_request_ids)}")
            return  # Wait for more responses
        
        logger.info(f"   ✅ All approvers have responded!")
        
        # Check if all responses are approved
        approved_responses = [resp for resp in approval_responses if resp.decision == 'approved']
        rejected_responses = [resp for resp in approval_responses if resp.decision == 'rejected']
        
        logger.info(f"   📊 Approval breakdown: {len(approved_responses)} approved, {len(rejected_responses)} rejected")
        
        if len(rejected_responses) > 0:
            logger.info(f"   ❌ Workflow step was rejected by {len(rejected_responses)} approver(s)")
            logger.info(f"   ⏸️ No workflow continuation - manual intervention needed")
            # TODO: In future, we can implement candidate rejection logic here
            return
        
        if len(approved_responses) == len(all_requests):
            logger.info(f"   🎉 All approvers approved! Continuing workflow...")
            
            # Get workflow, candidate, and job data for continuation
            workflow_result = await db.execute(
                select(CandidateWorkflow, Candidate, Job).join(
                    Candidate, CandidateWorkflow.candidate_id == Candidate.id
                ).join(
                    Job, CandidateWorkflow.job_id == Job.id
                ).where(
                    CandidateWorkflow.id == approval_request.candidate_workflow_id
                )
            )
            workflow_data = workflow_result.first()
            
            if not workflow_data:
                logger.error(f"   ❌ Could not find workflow data for continuation")
                return
            
            candidate_workflow, candidate, job = workflow_data
            
            # Convert to dictionaries for the email service
            workflow_dict = {
                'id': candidate_workflow.id,
                'current_step_detail_id': candidate_workflow.current_step_detail_id,
                'workflow_template_id': candidate_workflow.workflow_template_id,
                'candidate_id': candidate_workflow.candidate_id,
                'job_id': candidate_workflow.job_id
            }
            
            candidate_dict = {
                'id': candidate.id,
                'first_name': candidate.first_name,
                'last_name': candidate.last_name,
                'email': candidate.email
            }
            
            job_dict = {
                'id': job.id,
                'title': job.title,
                'short_id': job.short_id
            }
            
            # Create mock email data (since this is approval-triggered, not email-triggered)
            email_dict = {
                'snippet': f'Approval completed for {candidate.first_name} {candidate.last_name}',
                'payload': {'headers': []}
            }
            
            # Trigger workflow continuation
            email_service = EmailPollingService()
            logger.info(f"   🚀 Triggering workflow continuation...")
            
            await email_service._execute_workflow_progression(
                db, workflow_dict, candidate_dict, job_dict, email_dict
            )
            
            logger.info(f"   ✅ Workflow continuation completed!")
        else:
            logger.warning(f"   ⚠️ Unexpected approval state - not all approved but no rejections")
            
    except Exception as e:
        logger.error(f"❌ Error checking workflow continuation: {e}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

@router.get("/history", response_model=List[ApprovalRequestResponse])
async def get_approval_history(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get approval history - Admin sees all, regular users see only their own"""
    try:
        # Check if user is admin
        is_admin = current_user.role.name == "admin"
        
        # Build the base query
        base_query = select(
            WorkflowApprovalRequest,
            WorkflowStepDetail,
            WorkflowStep,
            CandidateWorkflow,
            Job,
            Candidate,
            WorkflowApproval
        ).join(
            WorkflowStepDetail, WorkflowApprovalRequest.workflow_step_detail_id == WorkflowStepDetail.id
        ).join(
            WorkflowStep, WorkflowStepDetail.workflow_step_id == WorkflowStep.id
        ).join(
            CandidateWorkflow, WorkflowApprovalRequest.candidate_workflow_id == CandidateWorkflow.id
        ).join(
            Job, CandidateWorkflow.job_id == Job.id
        ).join(
            Candidate, CandidateWorkflow.candidate_id == Candidate.id
        ).outerjoin(
            WorkflowApproval, WorkflowApproval.approval_request_id == WorkflowApprovalRequest.id
        ).order_by(
            WorkflowApprovalRequest.requested_at.desc()
        ).limit(limit).offset(offset)
        
        # If not admin, filter to only show approvals assigned to this user
        if not is_admin:
            base_query = base_query.where(
                WorkflowApprovalRequest.approver_user_id == current_user.id
            )
        
        # Execute the query
        requests_result = await db.execute(base_query)
        
        requests_data = requests_result.fetchall()
        
        approval_requests = []
        for request_data in requests_data:
            approval_request, step_detail, workflow_step, candidate_workflow, job, candidate, approval_response = request_data
            
            # Determine status based on response
            if approval_response:
                status = approval_response.decision
                responded_at = approval_response.responded_at
                comments = approval_response.comments
            else:
                status = "pending"
                responded_at = None
                comments = None
            
            # Determine if current user can approve this request
            can_approve = approval_request.approver_user_id == current_user.id
            
            approval_requests.append(
                ApprovalRequestResponse(
                    id=approval_request.id,
                    candidate_workflow_id=approval_request.candidate_workflow_id,
                    workflow_step_detail_id=approval_request.workflow_step_detail_id,
                    required_approvals=approval_request.required_approvals,
                    status=status,
                    requested_at=approval_request.requested_at,
                    responded_at=responded_at,
                    comments=comments,
                    
                    # User permissions
                    can_approve=can_approve,
                    
                    # Workflow step info
                    step_name=workflow_step.name,
                    step_description=workflow_step.description,
                    step_display_name=workflow_step.display_name,
                    step_type=workflow_step.step_type,
                    
                    # Candidate info
                    candidate_name=f"{candidate.first_name} {candidate.last_name}",
                    candidate_email=candidate.email,
                    
                    # Job info
                    job_title=job.title,
                    job_department=job.department,
                )
            )
        
        return approval_requests
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch approval history: {str(e)}"
        )
