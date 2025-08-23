"""
Workflow API endpoints
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import List

from core.database import get_db
from models.workflow import WorkflowStep, WorkflowTemplate, WorkflowStepDetail, CandidateWorkflow
from schemas.workflow import (
    WorkflowStepResponse, 
    WorkflowTemplateResponse, 
    WorkflowTemplateCreate,
    WorkflowTemplateCreateWithSteps,
    WorkflowTemplatePopulated,
    WorkflowStepDetailPopulated,
    WorkflowStepDetailResponse,
    CandidateWorkflowResponse
)
from api.auth import get_current_user
from models.user import Profile

router = APIRouter(prefix="/api/workflows", tags=["workflows"])

@router.get("/steps", response_model=List[WorkflowStepResponse])
async def get_workflow_steps(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Get all available workflow steps"""
    try:
        # Fetch all workflow steps that are not deleted
        result = await db.execute(
            select(WorkflowStep).where(WorkflowStep.is_deleted == False)
        )
        workflow_steps = result.scalars().all()
        
        return [
            WorkflowStepResponse(
                id=step.id,
                name=step.name,
                description=step.description,
                step_type=step.step_type,
                actions=step.actions,
                created_at=step.created_at,
                updated_at=step.updated_at
            )
            for step in workflow_steps
        ]
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow steps: {str(e)}"
        )

@router.get("/templates", response_model=List[WorkflowTemplatePopulated])
async def get_workflow_templates(
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Get all workflow templates with populated step details"""
    try:
        # Get all templates
        result = await db.execute(
            select(WorkflowTemplate).where(WorkflowTemplate.is_deleted == False)
        )
        templates = result.scalars().all()
        
        populated_templates = []
        
        for template in templates:
            # Get step details for this template
            step_details = []
            
            if template.steps_execution_id:
                # Fetch WorkflowStepDetail records
                step_detail_result = await db.execute(
                    select(WorkflowStepDetail, WorkflowStep)
                    .join(WorkflowStep, WorkflowStepDetail.workflow_step_id == WorkflowStep.id)
                    .where(
                        WorkflowStepDetail.id.in_(template.steps_execution_id),
                        WorkflowStepDetail.is_deleted == False,
                        WorkflowStep.is_deleted == False
                    )
                    .order_by(WorkflowStepDetail.order_number)
                )
                
                for step_detail, workflow_step in step_detail_result:
                    step_details.append(
                        WorkflowStepDetailPopulated(
                            id=step_detail.id,
                            workflow_step_id=step_detail.workflow_step_id,
                            delay_in_seconds=step_detail.delay_in_seconds,
                            auto_start=step_detail.auto_start,
                            required_human_approval=step_detail.required_human_approval,
                            number_of_approvals_needed=step_detail.number_of_approvals_needed,
                            status=step_detail.status,
                            order_number=step_detail.order_number,
                            created_at=step_detail.created_at,
                            updated_at=step_detail.updated_at,
                            workflow_step=WorkflowStepResponse(
                                id=workflow_step.id,
                                name=workflow_step.name,
                                description=workflow_step.description,
                                step_type=workflow_step.step_type,
                                actions=workflow_step.actions,
                                created_at=workflow_step.created_at,
                                updated_at=workflow_step.updated_at
                            )
                        )
                    )
            
            populated_templates.append(
                WorkflowTemplatePopulated(
                    id=template.id,
                    name=template.name,
                    description=template.description,
                    category=template.category,
                    steps_execution_id=template.steps_execution_id,
                    created_at=template.created_at,
                    updated_at=template.updated_at,
                    step_details=step_details
                )
            )
        
        return populated_templates
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow templates: {str(e)}"
        )

@router.post("/templates", response_model=WorkflowTemplateResponse)
async def create_workflow_template(
    template_data: WorkflowTemplateCreate,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Create a new workflow template"""
    try:
        # Create new workflow template
        new_template = WorkflowTemplate(
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            steps_execution_id=template_data.steps_execution_id
        )
        
        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)
        
        return WorkflowTemplateResponse(
            id=new_template.id,
            name=new_template.name,
            description=new_template.description,
            category=new_template.category,
            steps_execution_id=new_template.steps_execution_id,
            created_at=new_template.created_at,
            updated_at=new_template.updated_at
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow template: {str(e)}"
        )

@router.post("/templates/with-steps", response_model=WorkflowTemplateResponse)
async def create_workflow_template_with_steps(
    template_data: WorkflowTemplateCreateWithSteps,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Create a new workflow template with step details"""
    try:
        # Create WorkflowStepDetail records first
        step_detail_ids = []
        
        for step in template_data.steps:
            # Create WorkflowStepDetail record
            step_detail = WorkflowStepDetail(
                workflow_step_id=step.workflow_step_id,
                delay_in_seconds=step.delay_in_seconds,
                auto_start=step.auto_start,
                required_human_approval=step.required_human_approval,
                number_of_approvals_needed=step.number_of_approvals_needed,
                order_number=step.order_number,
                status="awaiting"
            )
            
            db.add(step_detail)
            await db.flush()  # Flush to get the ID without committing
            step_detail_ids.append(step_detail.id)
        
        # Create workflow template with step detail IDs
        new_template = WorkflowTemplate(
            name=template_data.name,
            description=template_data.description,
            category=template_data.category,
            steps_execution_id=step_detail_ids
        )
        
        db.add(new_template)
        await db.commit()
        await db.refresh(new_template)
        
        return WorkflowTemplateResponse(
            id=new_template.id,
            name=new_template.name,
            description=new_template.description,
            category=new_template.category,
            steps_execution_id=new_template.steps_execution_id,
            created_at=new_template.created_at,
            updated_at=new_template.updated_at
        )
        
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create workflow template with steps: {str(e)}"
        )

@router.put("/templates/{template_id}", response_model=WorkflowTemplateResponse)
async def update_workflow_template(
    template_id: str,
    template_data: WorkflowTemplateCreateWithSteps,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Update an existing workflow template with step details"""
    try:
        # Get existing template
        result = await db.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.id == template_id,
                WorkflowTemplate.is_deleted == False
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow template not found"
            )
        
        # Delete existing step details
        if template.steps_execution_id:
            from sqlalchemy import update
            await db.execute(
                update(WorkflowStepDetail)
                .where(WorkflowStepDetail.id.in_(template.steps_execution_id))
                .values(is_deleted=True)
            )
        
        # Create new step details
        step_detail_ids = []
        for step in template_data.steps:
            step_detail = WorkflowStepDetail(
                workflow_step_id=step.workflow_step_id,
                delay_in_seconds=step.delay_in_seconds,
                auto_start=step.auto_start,
                required_human_approval=step.required_human_approval,
                number_of_approvals_needed=step.number_of_approvals_needed,
                order_number=step.order_number,
                status="awaiting"
            )
            
            db.add(step_detail)
            await db.flush()
            step_detail_ids.append(step_detail.id)
        
        # Update template
        template.name = template_data.name
        template.description = template_data.description
        template.category = template_data.category
        template.steps_execution_id = step_detail_ids
        
        await db.commit()
        await db.refresh(template)
        
        return WorkflowTemplateResponse(
            id=template.id,
            name=template.name,
            description=template.description,
            category=template.category,
            steps_execution_id=template.steps_execution_id,
            created_at=template.created_at,
            updated_at=template.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update workflow template: {str(e)}"
        )

@router.delete("/templates/{template_id}")
async def delete_workflow_template(
    template_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Delete a workflow template and its step details"""
    try:
        # Get existing template
        result = await db.execute(
            select(WorkflowTemplate).where(
                WorkflowTemplate.id == template_id,
                WorkflowTemplate.is_deleted == False
            )
        )
        template = result.scalar_one_or_none()
        
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow template not found"
            )
        
        # Soft delete step details
        if template.steps_execution_id:
            from sqlalchemy import update
            await db.execute(
                update(WorkflowStepDetail)
                .where(WorkflowStepDetail.id.in_(template.steps_execution_id))
                .values(is_deleted=True)
            )
        
        # Soft delete template
        template.is_deleted = True
        
        await db.commit()
        
        return {"message": "Workflow template deleted successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete workflow template: {str(e)}"
        )

@router.get("/steps/{step_id}", response_model=WorkflowStepResponse)
async def get_workflow_step(
    step_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: Profile = Depends(get_current_user)
):
    """Get a specific workflow step by ID"""
    try:
        result = await db.execute(
            select(WorkflowStep).where(
                WorkflowStep.id == step_id,
                WorkflowStep.is_deleted == False
            )
        )
        step = result.scalar_one_or_none()
        
        if not step:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow step not found"
            )
        
        return WorkflowStepResponse(
            id=step.id,
            name=step.name,
            description=step.description,
            step_type=step.step_type,
            actions=step.actions,
            created_at=step.created_at,
            updated_at=step.updated_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch workflow step: {str(e)}"
        )
