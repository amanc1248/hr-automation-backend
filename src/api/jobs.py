"""
Jobs API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID

from core.database import get_db
from models.job import Job
from models.workflow import WorkflowTemplate
from schemas.job import (
    JobResponse,
    JobCreate,
    JobUpdate,
    JobListResponse
)
from api.auth import get_current_user
from models.user import Profile
from utils.short_id import generate_unique_job_short_id

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

@router.get("", response_model=JobListResponse)
@router.get("/", response_model=JobListResponse)
async def get_jobs(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    department: Optional[str] = Query(None)
):
    """Get all jobs for the company with pagination and filtering"""
    try:
        # Base query - filter by company
        base_query = select(Job).where(Job.company_id == current_user.company_id)
        
        # Apply filters
        if search:
            base_query = base_query.where(
                Job.title.ilike(f"%{search}%") | 
                Job.description.ilike(f"%{search}%")
            )
        
        if status:
            base_query = base_query.where(Job.status == status)
            
        if department:
            base_query = base_query.where(Job.department.ilike(f"%{department}%"))
        
        # Get total count
        count_query = select(func.count()).select_from(base_query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()
        
        # Get jobs with pagination
        jobs_query = base_query.order_by(Job.created_at.desc()).offset(skip).limit(limit)
        result = await db.execute(jobs_query)
        jobs = result.scalars().all()
        
        return JobListResponse(
            jobs=[
                JobResponse(
                    id=job.id,
                    title=job.title,
                    short_id=job.short_id,
                    description=job.description,
                    requirements=job.requirements,
                    department=job.department,
                    location=job.location,
                    job_type=job.job_type,
                    experience_level=job.experience_level,
                    remote_policy=job.remote_policy,
                    salary_min=job.salary_min,
                    salary_max=job.salary_max,
                    salary_currency=job.salary_currency,
                    status=job.status,
                    workflow_template_id=job.workflow_template_id,
                    posted_at=job.posted_at,
                    expires_at=job.expires_at,
                    is_featured=job.is_featured,
                    created_at=job.created_at,
                    updated_at=job.updated_at
                )
                for job in jobs
            ],
            total=total,
            skip=skip,
            limit=limit
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch jobs: {str(e)}"
        )

@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Get a specific job by ID"""
    try:
        result = await db.execute(
            select(Job).where(
                Job.id == job_id,
                Job.company_id == current_user.company_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return JobResponse(
            id=job.id,
            title=job.title,
            short_id=job.short_id,
            description=job.description,
            requirements=job.requirements,
            department=job.department,
            location=job.location,
            job_type=job.job_type,
            experience_level=job.experience_level,
            remote_policy=job.remote_policy,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            status=job.status,
            workflow_template_id=job.workflow_template_id,
            posted_at=job.posted_at,
            expires_at=job.expires_at,
            is_featured=job.is_featured,
            created_at=job.created_at,
            updated_at=job.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch job: {str(e)}"
        )

@router.post("", response_model=JobResponse)
@router.post("/", response_model=JobResponse)
async def create_job(
    job_data: JobCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Create a new job"""
    try:
        # Validate workflow template if provided
        if job_data.workflow_template_id:
            wf_result = await db.execute(
                select(WorkflowTemplate).where(
                    WorkflowTemplate.id == job_data.workflow_template_id,
                    WorkflowTemplate.is_deleted == False
                )
            )
            if not wf_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid workflow template ID"
                )
        
        # Generate unique short ID for the job
        short_id = await generate_unique_job_short_id(db)
        
        # Create new job
        new_job = Job(
            title=job_data.title,
            short_id=short_id,
            description=job_data.description,
            requirements=job_data.requirements,
            department=job_data.department,
            location=job_data.location,
            job_type=job_data.job_type,
            experience_level=job_data.experience_level,
            remote_policy=job_data.remote_policy,
            salary_min=job_data.salary_min,
            salary_max=job_data.salary_max,
            salary_currency=job_data.salary_currency or "USD",
            status=job_data.status or "draft",
            workflow_template_id=job_data.workflow_template_id,
            company_id=current_user.company_id,
            created_by=current_user.id,
            assigned_to=job_data.assigned_to or current_user.id,
            posted_at=job_data.posted_at,
            expires_at=job_data.expires_at,
            is_featured=job_data.is_featured or False
        )
        
        db.add(new_job)
        await db.commit()
        await db.refresh(new_job)
        
        return JobResponse(
            id=new_job.id,
            title=new_job.title,
            short_id=new_job.short_id,
            description=new_job.description,
            requirements=new_job.requirements,
            department=new_job.department,
            location=new_job.location,
            job_type=new_job.job_type,
            experience_level=new_job.experience_level,
            remote_policy=new_job.remote_policy,
            salary_min=new_job.salary_min,
            salary_max=new_job.salary_max,
            salary_currency=new_job.salary_currency,
            status=new_job.status,
            workflow_template_id=new_job.workflow_template_id,
            posted_at=new_job.posted_at,
            expires_at=new_job.expires_at,
            is_featured=new_job.is_featured,
            created_at=new_job.created_at,
            updated_at=new_job.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create job: {str(e)}"
        )

@router.put("/{job_id}", response_model=JobResponse)
async def update_job(
    job_id: UUID,
    job_data: JobUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Update an existing job"""
    try:
        # Get existing job
        result = await db.execute(
            select(Job).where(
                Job.id == job_id,
                Job.company_id == current_user.company_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Validate workflow template if provided
        if job_data.workflow_template_id:
            wf_result = await db.execute(
                select(WorkflowTemplate).where(
                    WorkflowTemplate.id == job_data.workflow_template_id,
                    WorkflowTemplate.is_deleted == False
                )
            )
            if not wf_result.scalar_one_or_none():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid workflow template ID"
                )
        
        # Update job fields (only if provided)
        update_data = job_data.dict(exclude_unset=True)
        for field, value in update_data.items():
            setattr(job, field, value)
        
        await db.commit()
        await db.refresh(job)
        
        return JobResponse(
            id=job.id,
            title=job.title,
            short_id=job.short_id,
            description=job.description,
            requirements=job.requirements,
            department=job.department,
            location=job.location,
            job_type=job.job_type,
            experience_level=job.experience_level,
            remote_policy=job.remote_policy,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            status=job.status,
            workflow_template_id=job.workflow_template_id,
            posted_at=job.posted_at,
            expires_at=job.expires_at,
            is_featured=job.is_featured,
            created_at=job.created_at,
            updated_at=job.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update job: {str(e)}"
        )

@router.delete("/{job_id}")
async def delete_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Delete a job (soft delete by changing status to 'closed')"""
    try:
        # Get existing job
        result = await db.execute(
            select(Job).where(
                Job.id == job_id,
                Job.company_id == current_user.company_id
            )
        )
        job = result.scalar_one_or_none()
        
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Soft delete by setting status to closed
        job.status = "closed"
        await db.commit()
        
        return {"message": "Job deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete job: {str(e)}"
        )
