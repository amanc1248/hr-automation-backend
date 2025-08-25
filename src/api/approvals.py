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
        # Get approval requests for this user that haven't been responded to
        requests_result = await db.execute(
            select(
                WorkflowApprovalRequest,
                WorkflowStepDetail,
                WorkflowStep,
                CandidateWorkflow,
                Job,
                Candidate
            )
            .join(WorkflowStepDetail, WorkflowApprovalRequest.workflow_step_detail_id == WorkflowStepDetail.id)
            .join(WorkflowStep, WorkflowStepDetail.workflow_step_id == WorkflowStep.id)
            .join(CandidateWorkflow, WorkflowApprovalRequest.candidate_workflow_id == CandidateWorkflow.id)
            .join(Job, CandidateWorkflow.job_id == Job.id)
            .join(Candidate, CandidateWorkflow.candidate_id == Candidate.id)
            .outerjoin(WorkflowApproval, WorkflowApproval.approval_request_id == WorkflowApprovalRequest.id)
            .where(
                WorkflowApprovalRequest.approver_user_id == current_user.id,
                WorkflowApprovalRequest.status == 'pending',
                WorkflowApproval.id.is_(None)  # No response yet
            )
        )
        
        requests_data = requests_result.fetchall()
        
        approval_requests = []
        for request_data in requests_data:
            approval_request, step_detail, workflow_step, candidate_workflow, job, candidate = request_data
            
            approval_requests.append(
                ApprovalRequestResponse(
                    id=approval_request.id,
                    candidate_workflow_id=approval_request.candidate_workflow_id,
                    workflow_step_detail_id=approval_request.workflow_step_detail_id,
                    required_approvals=approval_request.required_approvals,
                    status=approval_request.status,
                    requested_at=approval_request.requested_at,
                    
                    # Workflow step info
                    step_name=workflow_step.name,
                    step_description=workflow_step.description,
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
        
        # Update approval request status if needed
        if approval_data.decision == 'rejected':
            approval_request.status = 'rejected'
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
        # Import here to avoid circular imports
        from services.email_polling_service import EmailPollingService
        
        # Get all approval requests for this step
        all_requests_result = await db.execute(
            select(WorkflowApprovalRequest).where(
                WorkflowApprovalRequest.candidate_workflow_id == approval_request.candidate_workflow_id,
                WorkflowApprovalRequest.workflow_step_detail_id == approval_request.workflow_step_detail_id
            )
        )
        all_requests = all_requests_result.scalars().all()
        
        # Check approval status
        email_service = EmailPollingService()
        approval_status = await email_service._check_approval_status(
            db, all_requests, approval_request.required_approvals
        )
        
        if approval_status in ['approved', 'rejected']:
            # TODO: Trigger workflow continuation
            # This would typically involve:
            # 1. Getting the candidate workflow
            # 2. Calling the workflow progression logic
            # 3. Continuing from the current step
            print(f"🔄 Workflow should continue with status: {approval_status}")
            
    except Exception as e:
        print(f"Error checking workflow continuation: {e}")

@router.get("/history", response_model=List[ApprovalRequestResponse])
async def get_approval_history(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
    limit: int = 50,
    offset: int = 0
):
    """Get approval history for the current user"""
    try:
        # Get all approval requests for this user (responded and pending)
        requests_result = await db.execute(
            select(
                WorkflowApprovalRequest,
                WorkflowStepDetail,
                WorkflowStep,
                CandidateWorkflow,
                Job,
                Candidate,
                WorkflowApproval
            )
            .join(WorkflowStepDetail, WorkflowApprovalRequest.workflow_step_detail_id == WorkflowStepDetail.id)
            .join(WorkflowStep, WorkflowStepDetail.workflow_step_id == WorkflowStep.id)
            .join(CandidateWorkflow, WorkflowApprovalRequest.candidate_workflow_id == CandidateWorkflow.id)
            .join(Job, CandidateWorkflow.job_id == Job.id)
            .join(Candidate, CandidateWorkflow.candidate_id == Candidate.id)
            .outerjoin(WorkflowApproval, WorkflowApproval.approval_request_id == WorkflowApprovalRequest.id)
            .where(WorkflowApprovalRequest.approver_user_id == current_user.id)
            .order_by(WorkflowApprovalRequest.requested_at.desc())
            .limit(limit)
            .offset(offset)
        )
        
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
                    
                    # Workflow step info
                    step_name=workflow_step.name,
                    step_description=workflow_step.description,
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
