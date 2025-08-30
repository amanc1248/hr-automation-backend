from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid
from datetime import datetime

from core.database import get_db
from api.auth import get_current_user
from models.candidate import Candidate, Application
from models.job import Job
from models.workflow import CandidateWorkflow, WorkflowStepDetail, WorkflowStep, WorkflowTemplate
from models.user import Profile
from schemas.candidate import (
    CandidateResponse,
    CandidatesListResponse,
    CandidateCreateRequest,
    CandidateUpdateRequest
)

router = APIRouter(prefix="/api/candidates")

@router.get("", response_model=CandidatesListResponse)
@router.get("/", response_model=CandidatesListResponse)
async def get_candidates(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    search: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    workflow_step: Optional[str] = Query(None),
    date_range: Optional[str] = Query("all")
):
    """Get candidates with filters and pagination"""
    try:
        # Base query with joins to get candidate data along with related info
        query = select(Candidate).options(
            selectinload(Candidate.applications).selectinload(Application.job),
            selectinload(Candidate.candidate_workflows)
        ).where(
            Candidate.company_id == current_user.company_id,
            Candidate.deleted_at.is_(None)
        )
        
        # Apply search filter
        if search:
            search_filter = f"%{search.lower()}%"
            query = query.where(
                func.lower(Candidate.first_name).like(search_filter) |
                func.lower(Candidate.last_name).like(search_filter) |
                func.lower(Candidate.email).like(search_filter)
            )
        
        # Apply job filter
        if job_id:
            query = query.join(Application).where(Application.job_id == uuid.UUID(job_id))
            
        # Apply status filter (we'll derive status from workflow)
        # Note: status logic might need adjustment based on your workflow design
        
        # Count total for pagination
        count_query = select(func.count(Candidate.id)).where(
            Candidate.company_id == current_user.company_id,
            Candidate.deleted_at.is_(None)
        )
        
        if search:
            search_filter = f"%{search.lower()}%"
            count_query = count_query.where(
                func.lower(Candidate.first_name).like(search_filter) |
                func.lower(Candidate.last_name).like(search_filter) |
                func.lower(Candidate.email).like(search_filter)
            )
            
        if job_id:
            count_query = count_query.join(Application).where(Application.job_id == uuid.UUID(job_id))
        
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Apply pagination
        offset = (page - 1) * limit
        query = query.offset(offset).limit(limit).order_by(desc(Candidate.created_at))
        
        # Execute query
        result = await db.execute(query)
        candidates = result.scalars().all()
        
        # Transform candidates to response format
        candidate_responses = []
        for candidate in candidates:
            # Get the latest application for job info
            latest_application = None
            if candidate.applications:
                latest_application = max(candidate.applications, key=lambda x: x.created_at)
            
            # Get the latest workflow for current step info
            latest_workflow = None
            current_step = "No workflow"
            workflow_progress = []
            candidate_status = "pending"
            
            # For now, keep workflow info simple to avoid async issues
            # We'll get detailed workflow info from a separate endpoint
            current_step = "No workflow"
            workflow_progress = []
            candidate_status = "pending"
            
            # Create candidate response
            candidate_response = CandidateResponse(
                id=str(candidate.id),
                name=f"{candidate.first_name} {candidate.last_name}",
                email=candidate.email,
                phone=candidate.phone,
                location=candidate.location,
                jobId=str(latest_application.job_id) if latest_application else "",
                jobTitle=latest_application.job.title if latest_application and latest_application.job else "No job",
                applicationDate=latest_application.created_at.isoformat() if latest_application else candidate.created_at.isoformat(),
                currentStep=current_step,
                workflowProgress=workflow_progress,  # We'll populate this later if needed
                resume={
                    "id": str(candidate.id),
                    "filename": "resume.pdf",
                    "originalName": "Resume.pdf", 
                    "fileSize": 0,
                    "fileType": "application/pdf",
                    "downloadUrl": candidate.resume_url or "",
                    "uploadedAt": candidate.created_at.isoformat()
                },
                communicationHistory=[],  # We'll populate this later if needed
                status=candidate_status,
                notes=[], # We'll add notes later if needed
                companyId=str(candidate.company_id),
                createdAt=candidate.created_at.isoformat(),
                updatedAt=candidate.updated_at.isoformat()
            )
            
            candidate_responses.append(candidate_response)
        
        # Calculate pagination info
        total_pages = (total + limit - 1) // limit
        
        return CandidatesListResponse(
            candidates=candidate_responses,
            total=total,
            page=page,
            limit=limit,
            totalPages=total_pages
        )
        
    except Exception as e:
        print(f"Error getting candidates: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch candidates: {str(e)}")

@router.get("/{candidate_id}", response_model=CandidateResponse)
async def get_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Get a specific candidate by ID"""
    try:
        query = select(Candidate).options(
            selectinload(Candidate.applications).selectinload(Application.job),
            selectinload(Candidate.candidate_workflows)
        ).where(
            Candidate.id == uuid.UUID(candidate_id),
            Candidate.company_id == current_user.company_id,
            Candidate.deleted_at.is_(None)
        )
        
        result = await db.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Transform to response format (similar to above)
        latest_application = None
        if candidate.applications:
            latest_application = max(candidate.applications, key=lambda x: x.created_at)
        
        return CandidateResponse(
            id=str(candidate.id),
            name=f"{candidate.first_name} {candidate.last_name}",
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            jobId=str(latest_application.job_id) if latest_application else "",
            jobTitle=latest_application.job.title if latest_application and latest_application.job else "No job",
            applicationDate=latest_application.created_at.isoformat() if latest_application else candidate.created_at.isoformat(),
            currentStep="resume_analysis",  # Default for now
            workflowProgress=[],
            resume={
                "id": str(candidate.id),
                "filename": "resume.pdf",
                "originalName": "Resume.pdf",
                "fileSize": 0,
                "fileType": "application/pdf", 
                "downloadUrl": candidate.resume_url or "",
                "uploadedAt": candidate.created_at.isoformat()
            },
            communicationHistory=[],
            status="active",
            notes=[],
            companyId=str(candidate.company_id),
            createdAt=candidate.created_at.isoformat(),
            updatedAt=candidate.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting candidate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch candidate: {str(e)}")

@router.post("", response_model=CandidateResponse)
@router.post("/", response_model=CandidateResponse)
async def create_candidate(
    candidate_data: CandidateCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Create a new candidate"""
    try:
        # Check if candidate with this email already exists
        existing_query = select(Candidate).where(
            Candidate.email == candidate_data.email,
            Candidate.company_id == current_user.company_id,
            Candidate.deleted_at.is_(None)
        )
        existing_result = await db.execute(existing_query)
        existing_candidate = existing_result.scalar_one_or_none()
        
        if existing_candidate:
            raise HTTPException(status_code=400, detail="Candidate with this email already exists")
        
        # Create new candidate
        new_candidate = Candidate(
            first_name=candidate_data.first_name,
            last_name=candidate_data.last_name,
            email=candidate_data.email,
            phone=candidate_data.phone,
            location=candidate_data.location,
            company_id=current_user.company_id
        )
        
        db.add(new_candidate)
        await db.commit()
        await db.refresh(new_candidate)
        
        # Return response
        return CandidateResponse(
            id=str(new_candidate.id),
            name=f"{new_candidate.first_name} {new_candidate.last_name}",
            email=new_candidate.email,
            phone=new_candidate.phone,
            location=new_candidate.location,
            jobId="",
            jobTitle="",
            applicationDate=new_candidate.created_at.isoformat(),
            currentStep="new",
            workflowProgress=[],
            resume={
                "id": str(new_candidate.id),
                "filename": "",
                "originalName": "",
                "fileSize": 0,
                "fileType": "",
                "downloadUrl": "",
                "uploadedAt": new_candidate.created_at.isoformat()
            },
            communicationHistory=[],
            status="pending",
            notes=[],
            companyId=str(new_candidate.company_id),
            createdAt=new_candidate.created_at.isoformat(),
            updatedAt=new_candidate.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error creating candidate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create candidate: {str(e)}")

@router.put("/{candidate_id}", response_model=CandidateResponse)
async def update_candidate(
    candidate_id: str,
    candidate_data: CandidateUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Update an existing candidate"""
    try:
        # Get existing candidate
        query = select(Candidate).where(
            Candidate.id == uuid.UUID(candidate_id),
            Candidate.company_id == current_user.company_id,
            Candidate.deleted_at.is_(None)
        )
        result = await db.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Check if email is being changed and if it conflicts with another candidate
        if candidate_data.email != candidate.email:
            existing_query = select(Candidate).where(
                Candidate.email == candidate_data.email,
                Candidate.company_id == current_user.company_id,
                Candidate.id != candidate.id,
                Candidate.deleted_at.is_(None)
            )
            existing_result = await db.execute(existing_query)
            if existing_result.scalar_one_or_none():
                raise HTTPException(status_code=400, detail="Another candidate with this email already exists")
        
        # Update candidate fields
        candidate.first_name = candidate_data.first_name
        candidate.last_name = candidate_data.last_name
        candidate.email = candidate_data.email
        candidate.phone = candidate_data.phone
        candidate.location = candidate_data.location
        
        await db.commit()
        await db.refresh(candidate)
        
        # Return updated candidate
        return CandidateResponse(
            id=str(candidate.id),
            name=f"{candidate.first_name} {candidate.last_name}",
            email=candidate.email,
            phone=candidate.phone,
            location=candidate.location,
            jobId="",  # Will be populated when applications exist
            jobTitle="",
            applicationDate=candidate.created_at.isoformat(),
            currentStep="updated",
            workflowProgress=[],
            resume={
                "id": str(candidate.id),
                "filename": "",
                "originalName": "",
                "fileSize": 0,
                "fileType": "",
                "downloadUrl": candidate.resume_url or "",
                "uploadedAt": candidate.created_at.isoformat()
            },
            communicationHistory=[],
            status="active",
            notes=[],
            companyId=str(candidate.company_id),
            createdAt=candidate.created_at.isoformat(),
            updatedAt=candidate.updated_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error updating candidate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to update candidate: {str(e)}")

@router.delete("/{candidate_id}", status_code=204)
async def delete_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Soft delete a candidate"""
    try:
        # Get existing candidate
        query = select(Candidate).where(
            Candidate.id == uuid.UUID(candidate_id),
            Candidate.company_id == current_user.company_id,
            Candidate.deleted_at.is_(None)
        )
        result = await db.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Soft delete by setting deleted_at timestamp
        candidate.deleted_at = datetime.utcnow()
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"Error deleting candidate: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete candidate: {str(e)}")

@router.get("/{candidate_id}/workflow", response_model=dict)
async def get_candidate_workflow(
    candidate_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Get workflow details for a specific candidate using the new candidate_workflow_executions table"""
    try:
        from models.candidate_workflow_execution import CandidateWorkflowExecution
        
        # Get candidate with workflow information
        query = select(Candidate).options(
            selectinload(Candidate.candidate_workflows)
        ).where(
            Candidate.id == uuid.UUID(candidate_id),
            Candidate.company_id == current_user.company_id,
            Candidate.deleted_at.is_(None)
        )
        
        result = await db.execute(query)
        candidate = result.scalar_one_or_none()
        
        if not candidate:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Get workflow information
        workflow_info = {
            "has_workflow": False,
            "current_step": "No workflow",
            "status": "pending",
            "progress": {
                "completed": 0,
                "total": 0,
                "percentage": 0
            },
            "steps": []
        }
        
        if candidate.candidate_workflows:
            latest_workflow = max(candidate.candidate_workflows, key=lambda x: x.created_at)
            workflow_info["has_workflow"] = True
            
            # Get current step info from execution records
            if latest_workflow.current_step_detail_id:
                current_step_execution_query = select(CandidateWorkflowExecution).where(
                    CandidateWorkflowExecution.workflow_step_detail_id == latest_workflow.current_step_detail_id,
                    CandidateWorkflowExecution.candidate_id == candidate.id,
                    CandidateWorkflowExecution.job_id == latest_workflow.job_id,
                    CandidateWorkflowExecution.is_deleted == False
                )
                current_step_result = await db.execute(current_step_execution_query)
                current_step_execution = current_step_result.scalar_one_or_none()
                
                if current_step_execution:
                    workflow_info["current_step"] = current_step_execution.step_name or "Current Step"
                else:
                    # Fallback to old method if execution record not found
                    current_step_query = select(WorkflowStepDetail).options(
                        selectinload(WorkflowStepDetail.workflow_step)
                    ).where(WorkflowStepDetail.id == latest_workflow.current_step_detail_id)
                    current_step_result = await db.execute(current_step_query)
                    current_step_detail = current_step_result.scalar_one_or_none()
                    if current_step_detail and current_step_detail.workflow_step:
                        workflow_info["current_step"] = current_step_detail.workflow_step.name
            
            # If no current step detail ID, try to determine from execution records
            if workflow_info["current_step"] == "No workflow":
                # Look for the step that is marked as current_step=True in execution records
                current_step_execution_query = select(CandidateWorkflowExecution).where(
                    CandidateWorkflowExecution.candidate_id == candidate.id,
                    CandidateWorkflowExecution.job_id == latest_workflow.job_id,
                    CandidateWorkflowExecution.current_step == True,
                    CandidateWorkflowExecution.is_deleted == False
                )
                current_step_result = await db.execute(current_step_execution_query)
                current_step_execution = current_step_result.scalar_one_or_none()
                
                if current_step_execution:
                    workflow_info["current_step"] = current_step_execution.step_name or "Current Step"
                else:
                    # If no current step found, check if workflow is completed
                    all_steps_finished_query = select(CandidateWorkflowExecution).where(
                        CandidateWorkflowExecution.candidate_id == candidate.id,
                        CandidateWorkflowExecution.job_id == latest_workflow.job_id,
                        CandidateWorkflowExecution.is_deleted == False
                    )
                    all_steps_result = await db.execute(all_steps_finished_query)
                    all_steps = all_steps_result.scalars().all()
                    
                    if all_steps and all(step.execution_status == "finished" for step in all_steps):
                        workflow_info["current_step"] = "Workflow Completed"
                    else:
                        workflow_info["current_step"] = "Workflow in Progress"
            
            # Determine status - check both workflow flags and actual step completion
            if latest_workflow.workflow_completed:
                workflow_info["status"] = "completed"
            else:
                # Check if all steps are actually finished by looking at execution records
                all_steps_status_query = select(CandidateWorkflowExecution).where(
                    CandidateWorkflowExecution.candidate_id == candidate.id,
                    CandidateWorkflowExecution.job_id == latest_workflow.job_id,
                    CandidateWorkflowExecution.is_deleted == False
                )
                all_steps_status_result = await db.execute(all_steps_status_query)
                all_steps_status = all_steps_status_result.scalars().all()
                
                if all_steps_status:
                    # Check if all steps are finished
                    all_finished = all(step.execution_status == "finished" for step in all_steps_status)
                    if all_finished:
                        workflow_info["status"] = "completed"
                    elif latest_workflow.steps_executed > 0:
                        workflow_info["status"] = "active"
                    else:
                        workflow_info["status"] = "pending"
                else:
                    # Fallback to old logic
                    if latest_workflow.steps_executed > 0:
                        workflow_info["status"] = "active"
                    else:
                        workflow_info["status"] = "pending"
            
            # Get workflow step details for this workflow template
            if latest_workflow.workflow_template_id:
                # First get the workflow template to access steps_execution_id
                template_query = select(WorkflowTemplate).where(
                    WorkflowTemplate.id == latest_workflow.workflow_template_id
                )
                template_result = await db.execute(template_query)
                workflow_template = template_result.scalar_one_or_none()
                
                if workflow_template and workflow_template.steps_execution_id:
                    # steps_execution_id contains WorkflowStepDetail IDs, not WorkflowStep IDs
                    step_detail_ids = workflow_template.steps_execution_id
                    if not isinstance(step_detail_ids, list):
                        step_detail_ids = [step_detail_ids] if step_detail_ids else []
                    
                    if step_detail_ids:
                        # Get all workflow step details for this template, ordered by order_number
                        step_details_query = select(WorkflowStepDetail).options(
                            selectinload(WorkflowStepDetail.workflow_step)
                        ).where(
                            WorkflowStepDetail.id.in_(step_detail_ids)
                        ).order_by(WorkflowStepDetail.order_number)
                        
                        step_details_result = await db.execute(step_details_query)
                        step_details = step_details_result.scalars().all()
                        
                        if step_details:
                            total_steps = len(step_details)
                            
                            # Create steps array with real step names and statuses from execution records
                            workflow_info["steps"] = []
                            completed_steps = 0
                            
                            for i, step_detail in enumerate(step_details):
                                # Get the execution record for this specific candidate and job
                                execution_query = select(CandidateWorkflowExecution).where(
                                    CandidateWorkflowExecution.workflow_step_detail_id == step_detail.id,
                                    CandidateWorkflowExecution.candidate_id == candidate.id,
                                    CandidateWorkflowExecution.job_id == latest_workflow.job_id,
                                    CandidateWorkflowExecution.is_deleted == False
                                )
                                execution_result = await db.execute(execution_query)
                                execution_record = execution_result.scalar_one_or_none()
                                
                                # Use execution record data if available, otherwise fallback to step detail
                                if execution_record:
                                    step_status = execution_record.execution_status
                                    step_name = execution_record.step_name or step_detail.workflow_step.name if step_detail.workflow_step else f"Step {i + 1}"
                                    requires_approval = execution_record.required_human_approval
                                    approvers = execution_record.approvers or []
                                    order_number = execution_record.order_number
                                else:
                                    # Fallback to old method
                                    step_status = step_detail.status
                                    step_name = step_detail.workflow_step.name if step_detail.workflow_step else f"Step {i + 1}"
                                    requires_approval = step_detail.required_human_approval
                                    approvers = step_detail.approvers or []
                                    order_number = step_detail.order_number
                                
                                step_info = {
                                    "step": i + 1,
                                    "name": step_name,
                                    "status": step_status,
                                    "completed": step_status == "finished",
                                    "order_number": order_number,
                                    "requires_approval": requires_approval,
                                    "approvers": approvers
                                }
                                
                                # Count completed steps
                                if step_status == "finished":
                                    completed_steps += 1
                                
                                workflow_info["steps"].append(step_info)
                            
                            # Calculate progress based on actual completed steps
                            workflow_info["progress"]["total"] = total_steps
                            workflow_info["progress"]["completed"] = completed_steps
                            workflow_info["progress"]["percentage"] = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
                        else:
                            # If no step details found, try to get workflow steps directly
                            # This might happen if steps_execution_id contains WorkflowStep IDs instead
                            workflow_steps_query = select(WorkflowStep).where(
                                WorkflowStep.id.in_(step_detail_ids)
                            ).order_by(WorkflowStep.id)
                            
                            workflow_steps_result = await db.execute(workflow_steps_query)
                            workflow_steps = workflow_steps_result.scalars().all()
                            
                            if workflow_steps:
                                total_steps = len(workflow_steps)
                                
                                # Create steps array with workflow step names
                                workflow_info["steps"] = []
                                completed_steps = 0
                                
                                for i, workflow_step in enumerate(workflow_steps):
                                    step_info = {
                                        "step": i + 1,
                                        "name": workflow_step.name,
                                        "status": "pending",  # Default status since no step details exist
                                        "completed": False,
                                        "order_number": i + 1,
                                        "requires_approval": False,
                                        "approvers": []
                                    }
                                    workflow_info["steps"].append(step_info)
                                
                                # Calculate progress based on actual completed steps
                                workflow_info["progress"]["total"] = total_steps
                                workflow_info["progress"]["completed"] = completed_steps
                                workflow_info["progress"]["percentage"] = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
                            else:
                                # Final fallback: Create generic steps based on common workflow patterns
                                # This will show at least some workflow structure
                                generic_steps = [
                                    "Email Reception",
                                    "Resume Analysis", 
                                    "Technical Assessment",
                                    "Interview Scheduling",
                                    "Offer Letter"
                                ]
                                
                                total_steps = len(generic_steps)
                                
                                # Create generic steps array
                                workflow_info["steps"] = []
                                completed_steps = 0
                                
                                for i, step_name in enumerate(generic_steps):
                                    step_info = {
                                        "step": i + 1,
                                        "name": step_name,
                                        "status": "pending",
                                        "completed": False,
                                        "order_number": i + 1,
                                        "requires_approval": False,
                                        "approvers": []
                                    }
                                    workflow_info["steps"].append(step_info)
                                
                                # Calculate progress based on actual completed steps
                                workflow_info["progress"]["total"] = total_steps
                                workflow_info["progress"]["completed"] = completed_steps
                                workflow_info["progress"]["percentage"] = int((completed_steps / total_steps) * 100) if total_steps > 0 else 0
        
        return workflow_info
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"Error getting candidate workflow: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch candidate workflow: {str(e)}")
