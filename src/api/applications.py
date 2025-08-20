"""
Application management API endpoints.
Handles job applications, screening, and pipeline management.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import Optional, List
from uuid import UUID
import logging

from src.models import (
    Application, ApplicationCreate, ApplicationUpdate, ApplicationSearch,
    ApplicationStatus, ApplicationPriority, PaginationParams, PaginatedResponse, APIResponse
)
from src.config.database import get_supabase
from src.services.portia_service import get_portia_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_applications(
    pagination: PaginationParams = Depends(),
    search: ApplicationSearch = Depends(),
    supabase = Depends(get_supabase)
):
    """
    Get paginated list of applications with optional filtering.
    """
    try:
        # Build query with joins
        query = supabase.table("applications").select(
            "*, jobs(title, company_id), candidates(full_name, email)"
        )
        
        # Apply filters
        if search.job_id:
            query = query.eq("job_id", str(search.job_id))
        if search.candidate_id:
            query = query.eq("candidate_id", str(search.candidate_id))
        if search.status:
            query = query.eq("status", search.status.value)
        if search.priority:
            query = query.eq("priority", search.priority.value)
        if search.ai_score_min is not None:
            query = query.gte("ai_screening_score", float(search.ai_score_min))
        if search.ai_score_max is not None:
            query = query.lte("ai_screening_score", float(search.ai_score_max))
        if search.human_score_min is not None:
            query = query.gte("human_review_score", float(search.human_score_min))
        if search.human_score_max is not None:
            query = query.lte("human_review_score", float(search.human_score_max))
        if search.reviewed_by:
            query = query.eq("reviewed_by", str(search.reviewed_by))
        if search.needs_review:
            query = query.is_("human_review_score", "null")
        if search.application_date_from:
            query = query.gte("application_date", search.application_date_from)
        if search.application_date_to:
            query = query.lte("application_date", search.application_date_to)
        
        # Get total count
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0
        
        # Apply pagination
        paginated_query = query.range(
            pagination.offset,
            pagination.offset + pagination.page_size - 1
        ).order("application_date", desc=True)
        
        result = paginated_query.execute()
        
        applications = [Application(**app) for app in result.data] if result.data else []
        
        return PaginatedResponse.create(
            items=applications,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing applications: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve applications"
        )


@router.post("/", response_model=APIResponse)
async def create_application(
    application_data: ApplicationCreate,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Create a new job application and trigger AI screening.
    """
    try:
        # Check if application already exists
        existing = supabase.table("applications").select("id").eq(
            "job_id", str(application_data.job_id)
        ).eq("candidate_id", str(application_data.candidate_id)).execute()
        
        if existing.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Application already exists for this job and candidate"
            )
        
        # Prepare application data
        app_dict = application_data.model_dump()
        app_dict["job_id"] = str(application_data.job_id)
        app_dict["candidate_id"] = str(application_data.candidate_id)
        app_dict["application_date"] = "now()"
        app_dict["last_status_change"] = "now()"
        
        # Insert application
        result = supabase.table("applications").insert(app_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create application"
            )
        
        created_application = Application(**result.data[0])
        
        # Trigger AI screening if enabled
        try:
            # Get job details to check if auto-screening is enabled
            job_result = supabase.table("jobs").select("auto_screening_enabled").eq(
                "id", str(application_data.job_id)
            ).execute()
            
            if job_result.data and job_result.data[0].get("auto_screening_enabled", False):
                # Get candidate and job data for screening
                candidate_result = supabase.table("candidates").select("*").eq(
                    "id", str(application_data.candidate_id)
                ).execute()
                
                job_full_result = supabase.table("jobs").select("*").eq(
                    "id", str(application_data.job_id)
                ).execute()
                
                if candidate_result.data and job_full_result.data:
                    screening_result = await portia_service.screen_candidate(
                        candidate_data=candidate_result.data[0],
                        job_data=job_full_result.data[0]
                    )
                    
                    if screening_result.get("success"):
                        # Update application with screening results
                        screening_data = screening_result.get("screening_result", {})
                        supabase.table("applications").update({
                            "ai_screening_score": screening_data.get("score", 0),
                            "ai_screening_result": screening_data,
                            "ai_screening_completed_at": "now()"
                        }).eq("id", str(created_application.id)).execute()
                        
        except Exception as screening_error:
            logger.warning(f"AI screening failed: {screening_error}")
        
        # Update job application count
        supabase.rpc("increment_job_applications", {"job_uuid": str(application_data.job_id)}).execute()
        
        return APIResponse.success_response(
            message="Application created successfully",
            data={"application": created_application.model_dump()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating application: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create application"
        )


@router.get("/{application_id}", response_model=Application)
async def get_application(
    application_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Get a specific application by ID with related data.
    """
    try:
        result = supabase.table("applications").select(
            "*, jobs(title, company_id), candidates(full_name, email, resume_url)"
        ).eq("id", str(application_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        return Application(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving application {application_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve application"
        )


@router.put("/{application_id}", response_model=APIResponse)
async def update_application(
    application_id: UUID,
    application_update: ApplicationUpdate,
    supabase = Depends(get_supabase)
):
    """
    Update an application.
    """
    try:
        # Prepare update data
        update_data = application_update.model_dump(exclude_unset=True)
        
        # Add timestamp for status changes
        if "status" in update_data:
            update_data["last_status_change"] = "now()"
        
        # Update application
        result = supabase.table("applications").update(update_data).eq(
            "id", str(application_id)
        ).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        updated_application = Application(**result.data[0])
        
        return APIResponse.success_response(
            message="Application updated successfully",
            data={"application": updated_application.model_dump()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating application {application_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update application"
        )


@router.post("/{application_id}/screen", response_model=APIResponse)
async def screen_application(
    application_id: UUID,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Manually trigger AI screening for an application.
    """
    try:
        # Get application with related data
        app_result = supabase.table("applications").select(
            "*, jobs(*), candidates(*)"
        ).eq("id", str(application_id)).execute()
        
        if not app_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        app_data = app_result.data[0]
        
        # Perform AI screening
        screening_result = await portia_service.screen_candidate(
            candidate_data=app_data["candidates"],
            job_data=app_data["jobs"]
        )
        
        if screening_result.get("success"):
            # Update application with screening results
            screening_data = screening_result.get("screening_result", {})
            supabase.table("applications").update({
                "ai_screening_score": screening_data.get("score", 0),
                "ai_screening_result": screening_data,
                "ai_screening_completed_at": "now()",
                "status": "screening"
            }).eq("id", str(application_id)).execute()
            
            return APIResponse.success_response(
                message="Application screening completed",
                data={"screening_result": screening_data}
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="AI screening failed"
            )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error screening application {application_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to screen application"
        )


@router.post("/{application_id}/review", response_model=APIResponse)
async def review_application(
    application_id: UUID,
    review_score: float,
    review_notes: str,
    reviewer_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Add human review to an application.
    """
    try:
        # Update application with human review
        result = supabase.table("applications").update({
            "human_review_score": review_score,
            "human_review_notes": review_notes,
            "reviewed_by": str(reviewer_id),
            "reviewed_at": "now()"
        }).eq("id", str(application_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        return APIResponse.success_response(
            message="Application reviewed successfully",
            data={
                "application_id": str(application_id),
                "review_score": review_score,
                "reviewer_id": str(reviewer_id)
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing application {application_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review application"
        )


@router.post("/{application_id}/advance", response_model=APIResponse)
async def advance_application(
    application_id: UUID,
    next_stage: ApplicationStatus,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Advance application to next stage and trigger appropriate workflows.
    """
    try:
        # Update application status
        result = supabase.table("applications").update({
            "status": next_stage.value,
            "last_status_change": "now()"
        }).eq("id", str(application_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found"
            )
        
        # Trigger appropriate workflows based on next stage
        workflow_result = None
        if next_stage == ApplicationStatus.INTERVIEW:
            # Schedule interview
            workflow_result = await portia_service.schedule_interview({
                "application_id": str(application_id),
                "interview_type": "screening"
            })
        elif next_stage == ApplicationStatus.TECHNICAL_TEST:
            # Create assessment
            # TODO: Implement assessment creation workflow
            pass
        
        return APIResponse.success_response(
            message=f"Application advanced to {next_stage.value}",
            data={
                "application_id": str(application_id),
                "new_status": next_stage.value,
                "workflow_result": workflow_result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error advancing application {application_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to advance application"
        )
