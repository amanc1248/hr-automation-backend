from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func, desc
from sqlalchemy.orm import selectinload
from typing import Optional, List
import uuid

from core.database import get_db
from api.auth import get_current_user
from models.candidate import Candidate, Application
from models.job import Job
from models.workflow import CandidateWorkflow, WorkflowStepDetail
from models.user import Profile
from schemas.candidate import (
    CandidateResponse,
    CandidatesListResponse,
    CandidateCreateRequest,
    CandidateUpdateRequest
)

router = APIRouter(prefix="/api/candidates")

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
            selectinload(Candidate.candidate_workflows).selectinload(CandidateWorkflow.workflow_step_details)
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
            
            if candidate.candidate_workflows:
                latest_workflow = max(candidate.candidate_workflows, key=lambda x: x.created_at)
                # Get current step info
                if latest_workflow.current_step_detail_id:
                    current_step_query = select(WorkflowStepDetail).where(
                        WorkflowStepDetail.id == latest_workflow.current_step_detail_id
                    )
                    current_step_result = await db.execute(current_step_query)
                    current_step_detail = current_step_result.scalar_one_or_none()
                    if current_step_detail:
                        current_step = current_step_detail.step_name or "Unknown step"
                
                # Determine status based on workflow state
                if latest_workflow.steps_executed > 0:
                    candidate_status = "active"
                if latest_workflow.workflow_completed:
                    candidate_status = "completed"
            
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
