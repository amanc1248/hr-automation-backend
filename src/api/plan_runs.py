"""
Workflow (Plan Runs) API endpoints.
Handles Portia workflow execution, monitoring, and clarifications.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from typing import List, Optional, Dict, Any
from uuid import UUID
import logging

from src.models import (
    Workflow, WorkflowCreate, WorkflowUpdate, WorkflowSearch,
    WorkflowStatus, WorkflowType, ClarificationResponse,
    PaginationParams, PaginatedResponse, APIResponse
)
from src.config.database import get_supabase
from src.services.portia_service import get_portia_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/", response_model=PaginatedResponse)
async def list_workflows(
    pagination: PaginationParams = Depends(),
    search: WorkflowSearch = Depends(),
    supabase = Depends(get_supabase)
):
    """
    Get paginated list of workflows with optional filtering.
    """
    try:
        # Build query
        query = supabase.table("workflows").select("*")
        
        # Apply filters
        if search.workflow_type:
            query = query.eq("workflow_type", search.workflow_type.value)
        if search.status:
            query = query.eq("status", search.status.value)
        if search.entity_id:
            query = query.eq("entity_id", str(search.entity_id))
        if search.entity_type:
            query = query.eq("entity_type", search.entity_type.value)
        if search.created_by:
            query = query.eq("created_by", str(search.created_by))
        if search.assigned_to:
            query = query.eq("assigned_to", str(search.assigned_to))
        if search.has_clarifications:
            if search.has_clarifications:
                query = query.neq("clarifications", "[]")
            else:
                query = query.eq("clarifications", "[]")
        if search.created_from:
            query = query.gte("created_at", search.created_from)
        if search.created_to:
            query = query.lte("created_at", search.created_to)
        
        # Get total count
        count_result = query.execute()
        total = len(count_result.data) if count_result.data else 0
        
        # Apply pagination
        paginated_query = query.range(
            pagination.offset,
            pagination.offset + pagination.page_size - 1
        ).order("created_at", desc=True)
        
        result = paginated_query.execute()
        
        workflows = [Workflow(**workflow) for workflow in result.data] if result.data else []
        
        return PaginatedResponse.create(
            items=workflows,
            total=total,
            page=pagination.page,
            page_size=pagination.page_size
        )
        
    except Exception as e:
        logger.error(f"Error listing workflows: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflows"
        )


@router.post("/", response_model=APIResponse)
async def create_workflow(
    workflow_data: WorkflowCreate,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Create and start a new workflow using Portia.
    """
    try:
        # Prepare workflow data
        workflow_dict = workflow_data.model_dump()
        workflow_dict["created_by"] = str(workflow_data.created_by)
        
        if workflow_data.entity_id:
            workflow_dict["entity_id"] = str(workflow_data.entity_id)
        if workflow_data.assigned_to:
            workflow_dict["assigned_to"] = str(workflow_data.assigned_to)
        
        # Start Portia workflow based on type
        portia_result = None
        if workflow_data.workflow_type == WorkflowType.HIRING_PROCESS:
            portia_result = await portia_service.create_hiring_workflow(
                job_data=workflow_data.inputs,
                hr_user_id=str(workflow_data.created_by)
            )
        elif workflow_data.workflow_type == WorkflowType.CANDIDATE_SCREENING:
            portia_result = await portia_service.screen_candidate(
                candidate_data=workflow_data.inputs.get("candidate_data", {}),
                job_data=workflow_data.inputs.get("job_data", {})
            )
        elif workflow_data.workflow_type == WorkflowType.INTERVIEW_SCHEDULING:
            portia_result = await portia_service.schedule_interview(
                interview_data=workflow_data.inputs
            )
        elif workflow_data.workflow_type == WorkflowType.AI_INTERVIEW:
            portia_result = await portia_service.conduct_ai_interview(
                interview_data=workflow_data.inputs
            )
        
        # Add Portia plan run ID if available
        if portia_result and portia_result.get("plan_run_id"):
            workflow_dict["plan_run_id"] = portia_result["plan_run_id"]
            workflow_dict["status"] = "running"
        
        # Insert workflow into database
        result = supabase.table("workflows").insert(workflow_dict).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create workflow"
            )
        
        created_workflow = Workflow(**result.data[0])
        
        return APIResponse.success_response(
            message="Workflow created and started successfully",
            data={
                "workflow": created_workflow.model_dump(),
                "portia_result": portia_result
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating workflow: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create workflow"
        )


@router.get("/{workflow_id}", response_model=Workflow)
async def get_workflow(
    workflow_id: UUID,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Get a specific workflow by ID with current status.
    """
    try:
        result = supabase.table("workflows").select("*").eq("id", str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        workflow_data = result.data[0]
        
        # Get current status from Portia if plan_run_id exists
        if workflow_data.get("plan_run_id"):
            try:
                portia_status = portia_service.get_plan_run_status(workflow_data["plan_run_id"])
                if portia_status.get("success"):
                    # Update workflow with current Portia status
                    workflow_data.update({
                        "status": portia_status.get("status", workflow_data["status"]),
                        "current_step_index": portia_status.get("current_step", 0),
                        "outputs": portia_status.get("outputs", {}),
                        "clarifications": portia_status.get("clarifications", [])
                    })
            except Exception as portia_error:
                logger.warning(f"Failed to get Portia status: {portia_error}")
        
        return Workflow(**workflow_data)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve workflow"
        )


@router.put("/{workflow_id}", response_model=APIResponse)
async def update_workflow(
    workflow_id: UUID,
    workflow_update: WorkflowUpdate,
    supabase = Depends(get_supabase)
):
    """
    Update a workflow.
    """
    try:
        # Prepare update data
        update_data = workflow_update.model_dump(exclude_unset=True)
        
        if "assigned_to" in update_data and update_data["assigned_to"]:
            update_data["assigned_to"] = str(update_data["assigned_to"])
        
        # Update workflow in database
        result = supabase.table("workflows").update(update_data).eq("id", str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        updated_workflow = Workflow(**result.data[0])
        
        return APIResponse.success_response(
            message="Workflow updated successfully",
            data={"workflow": updated_workflow.model_dump()}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update workflow"
        )


@router.post("/{workflow_id}/clarifications/{clarification_id}/respond", response_model=APIResponse)
async def respond_to_clarification(
    workflow_id: UUID,
    clarification_id: str,
    response_data: ClarificationResponse,
    supabase = Depends(get_supabase),
    portia_service = Depends(get_portia_service)
):
    """
    Respond to a workflow clarification and resume execution.
    """
    try:
        # Get workflow
        workflow_result = supabase.table("workflows").select("*").eq("id", str(workflow_id)).execute()
        
        if not workflow_result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        workflow_data = workflow_result.data[0]
        
        # Submit clarification response to Portia
        if workflow_data.get("plan_run_id"):
            portia_result = portia_service.resolve_clarification(
                plan_run_id=workflow_data["plan_run_id"],
                clarification_id=clarification_id,
                response=response_data.response
            )
            
            if not portia_result.get("success"):
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to submit clarification response to Portia"
                )
        
        # Update workflow status
        supabase.table("workflows").update({
            "status": "running"
        }).eq("id", str(workflow_id)).execute()
        
        return APIResponse.success_response(
            message="Clarification response submitted and workflow resumed",
            data={
                "workflow_id": str(workflow_id),
                "clarification_id": clarification_id,
                "response": response_data.response
            }
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error responding to clarification: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to respond to clarification"
        )


@router.post("/{workflow_id}/pause", response_model=APIResponse)
async def pause_workflow(
    workflow_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Pause a running workflow.
    """
    try:
        # Update workflow status
        result = supabase.table("workflows").update({
            "status": "paused"
        }).eq("id", str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        return APIResponse.success_response(
            message="Workflow paused successfully",
            data={"workflow_id": str(workflow_id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error pausing workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to pause workflow"
        )


@router.post("/{workflow_id}/resume", response_model=APIResponse)
async def resume_workflow(
    workflow_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Resume a paused workflow.
    """
    try:
        # Update workflow status
        result = supabase.table("workflows").update({
            "status": "running"
        }).eq("id", str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        return APIResponse.success_response(
            message="Workflow resumed successfully",
            data={"workflow_id": str(workflow_id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error resuming workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to resume workflow"
        )


@router.delete("/{workflow_id}", response_model=APIResponse)
async def cancel_workflow(
    workflow_id: UUID,
    supabase = Depends(get_supabase)
):
    """
    Cancel a workflow.
    """
    try:
        # Update workflow status
        result = supabase.table("workflows").update({
            "status": "cancelled"
        }).eq("id", str(workflow_id)).execute()
        
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found"
            )
        
        return APIResponse.success_response(
            message="Workflow cancelled successfully",
            data={"workflow_id": str(workflow_id)}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelling workflow {workflow_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to cancel workflow"
        )