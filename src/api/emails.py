from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any, Optional
import json
import base64
import logging

from core.database import get_db
from .auth import get_current_user
from models.user import User
from services.google_cloud_service import google_cloud_service
from services.gmail_service import gmail_service

router = APIRouter(prefix="/api/emails", tags=["emails"])

# Set up logging
logger = logging.getLogger(__name__)

@router.post("/webhook")
async def gmail_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """
    Webhook endpoint to receive Gmail push notifications via Google Cloud Pub/Sub
    """
    try:
        # Get the raw body
        body = await request.body()
        
        # Parse the Pub/Sub message
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in webhook body")
            return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
        
        # Handle Pub/Sub push message format
        if "message" in data:
            # This is a Pub/Sub push message
            message = data["message"]
            
            # Decode the message data
            if "data" in message:
                try:
                    # Decode base64 data
                    decoded_data = base64.b64decode(message["data"]).decode("utf-8")
                    logger.info(f"Received Pub/Sub message: {decoded_data}")
                    
                    # Process the Gmail notification in background
                    background_tasks.add_task(
                        process_gmail_notification, 
                        decoded_data, 
                        db
                    )
                    
                    # Acknowledge the message
                    return JSONResponse(
                        status_code=200, 
                        content={"status": "acknowledged"}
                    )
                    
                except Exception as e:
                    logger.error(f"Error processing Pub/Sub message: {e}")
                    return JSONResponse(
                        status_code=500, 
                        content={"error": "Failed to process message"}
                    )
        
        # Handle direct Gmail API notification (for testing)
        elif "emailAddress" in data:
            logger.info(f"Received direct Gmail notification for: {data['emailAddress']}")
            
            # Process in background
            background_tasks.add_task(
                process_gmail_notification, 
                json.dumps(data), 
                db
            )
            
            return JSONResponse(
                status_code=200, 
                content={"status": "processing"}
            )
        
        else:
            logger.warning(f"Unknown webhook format: {data}")
            return JSONResponse(
                status_code=400, 
                content={"error": "Unknown message format"}
            )
            
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return JSONResponse(
            status_code=500, 
            content={"error": "Internal server error"}
        )

@router.post("/setup-watch/{email_address}")
async def setup_gmail_watch(
    email_address: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Set up Gmail API watch for push notifications
    """
    try:
        # Get Gmail configuration for this email
        gmail_config = await gmail_service.get_gmail_config_by_email(db, email_address)
        if not gmail_config:
            raise HTTPException(
                status_code=404, 
                detail=f"No Gmail configuration found for {email_address}"
            )
        
        # Get fresh access token
        access_token = await gmail_service.get_valid_access_token(gmail_config)
        if not access_token:
            raise HTTPException(
                status_code=400, 
                detail="Invalid or expired Gmail access token"
            )
        
        # Create Gmail watch
        watch_result = await google_cloud_service.create_gmail_watch(
            email_address, 
            access_token
        )
        
        if watch_result and watch_result.get('success') is not False:
            return {
                "success": True,
                "message": f"Gmail watch created successfully for {email_address}",
                "data": watch_result
            }
        else:
            # Handle specific error cases
            if watch_result and watch_result.get('error') == 'PERMISSION_DENIED':
                return JSONResponse(
                    status_code=403,
                    content={
                        "success": False,
                        "error": "PERMISSION_DENIED",
                        "message": watch_result.get('message', 'Permission denied'),
                        "details": watch_result.get('details', ''),
                        "solution": "Use a service account with Pub/Sub Publisher and Subscriber roles"
                    }
                )
            elif watch_result and watch_result.get('error') == 'API_ERROR':
                return JSONResponse(
                    status_code=400,
                    content={
                        "success": False,
                        "error": "API_ERROR",
                        "message": watch_result.get('message', 'Gmail API error'),
                        "details": watch_result.get('details', '')
                    }
                )
            else:
                raise HTTPException(
                    status_code=500, 
                    detail="Failed to create Gmail watch"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error setting up Gmail watch: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error"
        )

@router.post("/test-pubsub")
async def test_pubsub(
    current_user: User = Depends(get_current_user)
):
    """
    Test Pub/Sub setup by publishing a test message
    """
    try:
        success = await google_cloud_service.publish_test_message()
        
        if success:
            return {
                "success": True,
                "message": "Test message published successfully"
            }
        else:
            raise HTTPException(
                status_code=500, 
                detail="Failed to publish test message"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error testing Pub/Sub: {e}")
        raise HTTPException(
            status_code=500, 
            detail="Internal server error"
        )

async def process_gmail_notification(notification_data: str, db: AsyncSession):
    """
    Process Gmail notification in background
    This function will be called as a background task
    """
    try:
        logger.info(f"Processing Gmail notification: {notification_data}")
        
        # Parse the notification data
        try:
            data = json.loads(notification_data)
        except json.JSONDecodeError:
            logger.error("Invalid JSON in notification data")
            return
        
        # Extract email information
        email_address = data.get("emailAddress")
        history_id = data.get("historyId")
        
        if not email_address or not history_id:
            logger.warning("Missing emailAddress or historyId in notification")
            return
        
        logger.info(f"Processing notification for {email_address}, history ID: {history_id}")
        
        # TODO: In the next phase, we'll:
        # 1. Fetch email details using Gmail API
        # 2. Parse email content and attachments
        # 3. Identify if it's a job application
        # 4. Start the appropriate workflow
        
        # For now, just log the notification
        logger.info(f"✅ Gmail notification processed for {email_address}")
        
    except Exception as e:
        logger.error(f"Error processing Gmail notification: {e}")
