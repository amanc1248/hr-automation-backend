"""
Candidate management API endpoints.
Handles candidate profiles, resume processing, and AI screening.
"""

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from typing import Optional, List
from uuid import UUID
import logging

from src.models import (
    Candidate, CandidateCreate, CandidateUpdate, CandidateSearch, 
    CandidateSource, CandidateStatus, PaginationParams, PaginatedResponse, APIResponse
)
from src.config.database import get_supabase
from src.services.portia_service import get_portia_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_candidates(
    pagination: PaginationParams = Depends(),
    search: CandidateSearch = Depends(),
    supabase = Depends(get_supabase)
):
    """
    Get paginated list of candidates with optional filtering.
    """
    try:
        # Build query
        query = supabase.table("candidates").select("*")
        
        # Apply filters
        if search.query:
            query = query.or_(
                f"full_name.ilike.%{search.query}%,"
                f"email.ilike.%{search.query}%,"
                f"current_company.ilike.%{search.query}%"
            )
        if search.skills:
            # Search in skills array
            for skill in search.skills:
                query = query.contains("ai_skills_extracted", [skill])
        if search.location:
            query = query.ilike("location", f"%{search.location}%")
        if search.experience_min is not None:
            query = query.gte("experience_years", search.experience_min)
        if search.experience_max is not None:
            query = query.lte("experience_years", search.experience_max)
        if search.current_company:
            query = query.ilike("current_company", f"%{search.current_company}%")
        if search.source:
            query = query.eq("source", search.source.value)
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
        
        candidates = [Candidate(**candidate) for candidate in result.data] if result.data else []
        
        return PaginatedResponse.create(
            items=candidates,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing candidates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve candidates"
        )


@router.post("/", response_model=APIResponse)
async def create_candidate(
    candidate_data: CandidateCreate,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Create a new candidate profile with AI resume analysis.
    """
    try:
        # Prepare candidate data for insertion
        candidate_dict = candidate_data.model_dump()
        
        # Convert nested models to JSON
        if candidate_data.skills:
            candidate_dict["skills"] = [skill.model_dump() for skill in candidate_data.skills]
        if candidate_data.work_experience:
            candidate_dict["work_experience"] = [exp.model_dump() for exp in candidate_data.work_experience]
        if candidate_data.education:
            candidate_dict["education"] = [edu.model_dump() for edu in candidate_data.education]
        
        # AI Resume Analysis if resume text is provided
        if candidate_data.resume_text:
            try:
                # Use Portia to analyze resume
                analysis_result = await portia_service.screen_candidate(
                    candidate_data=candidate_dict,
                    job_data={}  # General analysis without specific job
                )
                
                if analysis_result.get("success"):
                    screening_data = analysis_result.get("screening_result", {})
                    candidate_dict["ai_summary"] = screening_data.get("summary", "")
                    candidate_dict["ai_skills_extracted"] = screening_data.get("skills", [])
                    
            except Exception as ai_error:
                logger.warning(f"AI resume analysis failed: {ai_error}")
        
        # Insert candidate into database
        result = supabase.table("candidates").insert(candidate_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create candidate"
            )
        
        created_candidate = Candidate(**result.data[0])
        
        return APIResponse.success_response(
            message="Candidate created successfully",
            data={"candidate": created_candidate.model_dump()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating candidate: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create candidate"
        )


@router.get("/{candidate_id}", response_model=Candidate)
async def get_candidate(
    candidate_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Get a specific candidate by ID.
    """
    try:
        result = supabase.table("candidates").select("*").eq("id", str(candidate_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        # Increment profile views
        supabase.table("candidates").update({
            "profile_views": result.data[0]["profile_views"] + 1
        }).eq("id", str(candidate_id)).execute()
        
        return Candidate(**result.data[0])
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving candidate {candidate_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve candidate"
        )


@router.put("/{candidate_id}", response_model=APIResponse)
async def update_candidate(
    candidate_id: UUID,
    candidate_update: CandidateUpdate,
    supabase = Depends(get_supabase)
):
    """
    Update a candidate profile.
    """
    try:
        # Prepare update data
        update_data = candidate_update.model_dump(exclude_unset=True)
        
        # Convert nested models to JSON
        if "skills" in update_data and update_data["skills"]:
            update_data["skills"] = [skill.model_dump() for skill in update_data["skills"]]
        if "work_experience" in update_data and update_data["work_experience"]:
            update_data["work_experience"] = [exp.model_dump() for exp in update_data["work_experience"]]
        if "education" in update_data and update_data["education"]:
            update_data["education"] = [edu.model_dump() for edu in update_data["education"]]
        
        # Update candidate in database
        result = supabase.table("candidates").update(update_data).eq("id", str(candidate_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        updated_candidate = Candidate(**result.data[0])
        
        return APIResponse.success_response(
            message="Candidate updated successfully",
            data={"candidate": updated_candidate.model_dump()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating candidate {candidate_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update candidate"
        )


@router.delete("/{candidate_id}", response_model=APIResponse)
async def delete_candidate(
    candidate_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Delete a candidate profile.
    """
    try:
        result = supabase.table("candidates").delete().eq("id", str(candidate_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        return APIResponse.success_response(
            message="Candidate deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting candidate {candidate_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete candidate"
        )


@router.post("/{candidate_id}/upload-resume", response_model=APIResponse)
async def upload_resume(
    candidate_id: UUID,
    resume_file: UploadFile = File(...),
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Upload and process candidate resume with AI analysis.
    """
    try:
        # Validate file type
        if not resume_file.content_type.startswith(('application/pdf', 'text/', 'application/msword')):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid file type. Please upload PDF, DOC, or TXT files."
            )
        
        # Read file content
        file_content = await resume_file.read()
        
        # TODO: Implement file storage (Supabase Storage or S3)
        # For now, we'll simulate storing the file and extracting text
        resume_url = f"https://storage.example.com/resumes/{candidate_id}/{resume_file.filename}"
        
        # TODO: Implement text extraction from PDF/DOC
        # For now, simulate extracted text
        resume_text = "Extracted resume text would go here..."
        
        # AI Resume Analysis
        try:
            analysis_result = await portia_service.screen_candidate(
                candidate_data={"resume_text": resume_text},
                job_data={}
            )
            
            ai_summary = ""
            ai_skills = []
            
            if analysis_result.get("success"):
                screening_data = analysis_result.get("screening_result", {})
                ai_summary = screening_data.get("summary", "")
                ai_skills = screening_data.get("skills", [])
                
        except Exception as ai_error:
            logger.warning(f"AI resume analysis failed: {ai_error}")
            ai_summary = "AI analysis unavailable"
            ai_skills = []
        
        # Update candidate with resume information
        update_data = {
            "resume_url": resume_url,
            "resume_text": resume_text,
            "ai_summary": ai_summary,
            "ai_skills_extracted": ai_skills
        }
        
        result = supabase.table("candidates").update(update_data).eq("id", str(candidate_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found"
            )
        
        return APIResponse.success_response(
            message="Resume uploaded and analyzed successfully",
            data={
                "resume_url": resume_url,
                "ai_summary": ai_summary,
                "ai_skills_extracted": ai_skills
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error uploading resume for candidate {candidate_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload resume"
        )


@router.get("/{candidate_id}/applications", response_model=PaginatedResponse)
async def get_candidate_applications(
    candidate_id: UUID,
    pagination: PaginationParams = Depends(),
    supabase = Depends(get_supabase)
):
    """
    Get all applications for a specific candidate.
    """
    try:
        # Get applications with job information
        query = supabase.table("applications").select(
            "*, jobs(*)"
        ).eq("candidate_id", str(candidate_id))
        
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
        logger.error(f"Error retrieving applications for candidate {candidate_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve candidate applications"
        )


@router.post("/{candidate_id}/screen", response_model=APIResponse)
async def screen_candidate_for_job(
    candidate_id: UUID,
    job_id: UUID,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Screen a candidate for a specific job using AI analysis.
    """
    try:
        # Get candidate data
        candidate_result = supabase.table("candidates").select("*").eq("id", str(candidate_id)).execute()
        if not candidate_result.data:
            raise HTTPException(status_code=404, detail="Candidate not found")
        
        # Get job data
        job_result = supabase.table("jobs").select("*").eq("id", str(job_id)).execute()
        if not job_result.data:
            raise HTTPException(status_code=404, detail="Job not found")
        
        candidate_data = candidate_result.data[0]
        job_data = job_result.data[0]
        
        # Perform AI screening
        screening_result = await portia_service.screen_candidate(
            candidate_data=candidate_data,
            job_data=job_data
        )
        
        return APIResponse.success_response(
            message="Candidate screening completed",
            data={
                "candidate_id": str(candidate_id),
                "job_id": str(job_id),
                "screening_result": screening_result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error screening candidate {candidate_id} for job {job_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to screen candidate"
        )