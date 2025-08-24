from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from core.database import get_db
from api.auth import get_current_user
from models.user import User
from services.email_polling_service import email_polling_service

router = APIRouter(prefix="/api/emails", tags=["emails"])

# Set up logging
logger = logging.getLogger(__name__)

@router.post("/polling/start")
async def start_email_polling(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start email polling for all configured Gmail accounts
    """
    try:
        # Start polling in background
        success = await email_polling_service.start_polling()
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Email polling started successfully"
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Email polling is already running or failed to start"
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to start email polling: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to start email polling: {str(e)}"
        )

@router.post("/polling/stop")
async def stop_email_polling(
    current_user: User = Depends(get_current_user)
):
    """
    Stop email polling
    """
    try:
        success = await email_polling_service.stop_polling()
        
        if success:
            return JSONResponse(
                status_code=200,
                content={
                    "status": "success",
                    "message": "Email polling stopped successfully"
                }
            )
        else:
            return JSONResponse(
                status_code=400,
                content={
                    "status": "error",
                    "message": "Email polling was not running"
                }
            )
            
    except Exception as e:
        logger.error(f"Failed to stop email polling: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to stop email polling: {str(e)}"
        )

@router.get("/polling/status")
async def get_polling_status(
    current_user: User = Depends(get_current_user)
):
    """
    Get current email polling status
    """
    try:
        status = email_polling_service.get_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "data": {
                    "is_running": status["is_running"],
                    "started_at": status["started_at"],
                    "last_poll": status["last_poll"],
                    "poll_count": status["poll_count"],
                    "error_count": status["error_count"]
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get polling status: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get polling status: {str(e)}"
        )

@router.post("/polling/test")
async def test_email_polling(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Test email polling by running one poll cycle
    """
    try:
        result = await email_polling_service._poll_all_accounts()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Test poll completed",
                "data": result
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to test email polling: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to test email polling: {str(e)}"
        )

@router.post("/polling/trigger")
async def trigger_email_polling_and_workflows(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Manually trigger email polling and start workflows for job applications
    This bypasses the scheduled polling and processes emails immediately
    """
    try:
        logger.info("🚀 Manual email polling and workflow trigger initiated")
        
        # Run the polling and workflow processing
        result = await email_polling_service._poll_all_accounts()
        
        return JSONResponse(
            status_code=200,
            content={
                "status": "success",
                "message": "Manual email polling and workflow processing completed",
                "data": {
                    "polling_result": result,
                    "message": "Check backend logs for detailed email processing information"
                }
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to trigger email polling and workflows: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to trigger email polling and workflows: {str(e)}"
        )
