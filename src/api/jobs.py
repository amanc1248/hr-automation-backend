"""
Job management API endpoints.
Handles job posting, updating, and retrieval operations.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from typing import Optional, List
from uuid import UUID
import logging

from src.models import (
    Job, JobCreate, JobUpdate, JobSearch, JobStatus, JobType, 
    ExperienceLevel, PaginationParams, PaginatedResponse, APIResponse
)
from src.config.database import get_supabase
from src.services.portia_service import get_portia_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_jobs(
    pagination: PaginationParams = Depends(),
    search: JobSearch = Depends(),
    supabase = Depends(get_supabase)
):
    """
    Get paginated list of jobs with optional filtering.
    """
    try:
        # Build query
        query = supabase.table("jobs").select("*")
        
        # Apply filters
        if search.query:
            query = query.ilike("title", f"%{search.query}%")
        if search.location:
            query = query.ilike("location", f"%{search.location}%")
        if search.job_type:
            query = query.eq("job_type", search.job_type.value)
        if search.experience_level:
            query = query.eq("experience_level", search.experience_level.value)
        if search.remote_allowed is not None:
            query = query.eq("remote_allowed", search.remote_allowed)
        if search.company_id:
            query = query.eq("company_id", str(search.company_id))
        if search.status:
            query = query.eq("status", search.status.value)
        
        # Get total count
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0
        
        # Apply pagination
        paginated_query = query.range(
            pagination.offset, 
            pagination.offset + pagination.page_size - 1
        ).order("created_at", desc=True)
        
        result = paginated_query.execute()
        
        jobs = [Job(**job) for job in result.data] if result.data else []
        
        return PaginatedResponse.create(
            items=jobs,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing jobs: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve jobs"
        )


@router.post("/", response_model=APIResponse)
async def create_job(
    job_data: JobCreate,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Create a new job posting and optionally start hiring workflow.
    """
    try:
        # Prepare job data for insertion
        job_dict = job_data.model_dump()
        job_dict["created_by"] = str(job_data.created_by)
        job_dict["company_id"] = str(job_data.company_id)
        
        # Convert nested models to JSON
        if job_data.requirements:
            job_dict["requirements"] = [req.model_dump() for req in job_data.requirements]
        if job_data.salary_range:
            job_dict["salary_range"] = job_data.salary_range.model_dump()
        
        # Insert job into database
        result = supabase.table("jobs").insert(job_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create job"
            )
        
        created_job = Job(**result.data[0])
        
        # Start hiring workflow if auto-posting is enabled
        if job_data.posted_platforms:
            try:
                workflow_result = await portia_service.create_hiring_workflow(
                    job_data=job_dict,
                    hr_user_id=str(job_data.created_by)
                )
                logger.info(f"Started hiring workflow: {workflow_result}")
            except Exception as workflow_error:
                logger.warning(f"Failed to start workflow: {workflow_error}")
        
        return APIResponse.success_response(
            message="Job created successfully",
            data={"job": created_job.model_dump()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating job: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create job"
        )


@router.get("/{job_id}", response_model=Job)
async def get_job(
    job_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Get a specific job by ID.
    """
    try:
        result = supabase.table("jobs").select("*").eq("id", str(job_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        # Increment view count
        supabase.table("jobs").update({
            "views_count": result.data[0]["views_count"] + 1
        }).eq("id", str(job_id)).execute()
        
        return Job(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job"
        )


@router.put("/{job_id}", response_model=APIResponse)
async def update_job(
    job_id: UUID,
    job_update: JobUpdate,
    supabase = Depends(get_supabase)
):
    """
    Update a job posting.
    """
    try:
        # Prepare update data
        update_data = job_update.model_dump(exclude_unset=True)
        
        # Convert nested models to JSON
        if "requirements" in update_data and update_data["requirements"]:
            update_data["requirements"] = [req.model_dump() for req in update_data["requirements"]]
        if "salary_range" in update_data and update_data["salary_range"]:
            update_data["salary_range"] = update_data["salary_range"].model_dump()
        
        # Update job in database
        result = supabase.table("jobs").update(update_data).eq("id", str(job_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        updated_job = Job(**result.data[0])
        
        return APIResponse.success_response(
            message="Job updated successfully",
            data={"job": updated_job.model_dump()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update job"
        )


@router.delete("/{job_id}", response_model=APIResponse)
async def delete_job(
    job_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Delete a job posting.
    """
    try:
        result = supabase.table("jobs").delete().eq("id", str(job_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        return APIResponse.success_response(
            message="Job deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete job"
        )


@router.post("/{job_id}/publish", response_model=APIResponse)
async def publish_job(
    job_id: UUID,
    platforms: List[str] = Query(..., description="Platforms to publish to"),
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Publish job to specified platforms using AI automation.
    """
    try:
        # Get job details
        job_result = supabase.table("jobs").select("*").eq("id", str(job_id)).execute()
        
        if not job_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job not found"
            )
        
        job_data = job_result.data[0]
        
        # Update job status and platforms
        update_result = supabase.table("jobs").update({
            "status": "published",
            "posted_platforms": platforms
        }).eq("id", str(job_id)).execute()
        
        # Start job posting workflow
        workflow_result = await portia_service.create_hiring_workflow(
            job_data={**job_data, "posted_platforms": platforms},
            hr_user_id=job_data["created_by"]
        )
        
        return APIResponse.success_response(
            message="Job published successfully",
            data={
                "job_id": str(job_id),
                "platforms": platforms,
                "workflow_id": workflow_result.get("plan_run_id")
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error publishing job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to publish job"
        )


@router.get("/{job_id}/applications", response_model=PaginatedResponse)
async def get_job_applications(
    job_id: UUID,
    pagination: PaginationParams = Depends(),
    supabase = Depends(get_supabase)
):
    """
    Get all applications for a specific job.
    """
    try:
        # Get applications with candidate information
        query = supabase.table("applications").select(
            "*, candidates(*)"
        ).eq("job_id", str(job_id))
        
        # Get total count
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0
        
        # Apply pagination
        paginated_query = query.range(
            pagination.offset,
            pagination.offset + pagination.page_size - 1
        ).order("application_date", desc=True)
        
        result = paginated_query.execute()
        
        return PaginatedResponse.create(
            items=result.data or [],
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except Exception as e:
        logger.error(f"Error retrieving applications for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve job applications"
        )