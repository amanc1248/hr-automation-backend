import json
import base64
import os
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query, Request, Header
from fastapi.responses import RedirectResponse, HTMLResponse, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
import httpx

from core.database import get_db
from api.auth import get_current_user
from models.user import Profile
from services.gmail_service import gmail_service, GmailConfig

router = APIRouter(prefix="/api/gmail", tags=["gmail"])

@router.get("/oauth/url")
async def get_gmail_oauth_url(
    current_user: Profile = Depends(get_current_user)
):
    """Generate Gmail OAuth URL for admin to connect Gmail account"""
    
    # Only admins can configure Gmail
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can configure Gmail integration"
        )
    
    try:
        oauth_url = await gmail_service.generate_oauth_url(
            user_id=str(current_user.id),
            company_id=str(current_user.company_id)
        )
        
        return {
            "success": True,
            "oauth_url": oauth_url,
            "message": "Redirect user to this URL to authorize Gmail access"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate OAuth URL: {str(e)}"
        )

@router.get("/oauth/callback")
async def gmail_oauth_callback(
    code: str = Query(..., description="Authorization code from Google"),
    state: str = Query(..., description="State parameter with user info"),
    error: Optional[str] = Query(None, description="Error from OAuth"),
    db: AsyncSession = Depends(get_db)
):
    """Handle Gmail OAuth callback from Google"""
    
    # Check for OAuth errors
    if error:
        # Load and return error HTML page
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Replace success content with error content
        html_content = html_content.replace('✅', '❌')
        html_content = html_content.replace('Gmail Connected Successfully!', 'Gmail Connection Failed')
        html_content = html_content.replace('Your Gmail account has been connected.', f'OAuth error: {error}')
        
        error_url = f"http://localhost:5173/email-config?error={error}"
        html_content = html_content.replace('/email-config', error_url)
        
        return HTMLResponse(content=html_content, status_code=200)
    
    try:
        # Decode state parameter
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        user_id = state_data['user_id']
        company_id = state_data['company_id']
        
        # Exchange code for tokens
        tokens = await gmail_service.exchange_code_for_tokens(code)
        
        # Get user's Gmail information
        user_info = await gmail_service.get_user_info(tokens['access_token'])
        
        # Test Gmail connection
        connection_ok = await gmail_service.test_gmail_connection(tokens['access_token'])
        if not connection_ok:
            raise Exception("Failed to connect to Gmail API")
        
        # Save Gmail configuration
        config = await gmail_service.save_gmail_config(
            db=db,
            user_id=user_id,
            company_id=company_id,
            gmail_address=user_info['email'],
            display_name=user_info.get('name', user_info['email']),
            tokens=tokens
        )
        
        # NEW: Set up Gmail watch for webhook notifications
        try:
            from services.gmail_watch_manager import gmail_watch_manager
            from models.user import Profile
            from sqlalchemy import text
            
            # Create a temporary profile object for the connected Gmail account
            # This ensures we create the watch for the right email, not the admin's email
            connected_gmail_profile = Profile(
                id=user_id,  # Keep the admin user ID for database relationships
                email=user_info['email'],  # Use the connected Gmail account email
                company_id=company_id,
                # Add other required fields with defaults
                password_hash="",  # Not used for Gmail watch
                role_id="",  # Not used for Gmail watch
                preferences={},
                is_active=True
            )
            
            # Set up Gmail watch for the CONNECTED Gmail account
            watch_result = await gmail_watch_manager.setup_watch_for_user(
                db=db,
                user=connected_gmail_profile,  # Use the connected Gmail profile
                access_token=tokens['access_token']
            )
            
            if watch_result['success']:
                print(f"Gmail watch setup successful: {watch_result['message']}")
            else:
                print(f"Gmail watch setup failed: {watch_result['error']}")
                
        except Exception as e:
            print(f"Error setting up Gmail watch: {str(e)}")
            # Don't fail the OAuth flow if watch setup fails
        
        # Load and return success HTML page
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Get the frontend URL from environment or use a default
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        print(f"Frontend URL: {frontend_url}")
        
        # Inject the success data directly into the HTML
        html_content = html_content.replace('const success = urlParams.get(\'success\');', f'const success = \'true\';')
        html_content = html_content.replace('const email = urlParams.get(\'email\');', f'const email = \'{user_info["email"]}\';')
        html_content = html_content.replace('const error = urlParams.get(\'error\');', 'const error = null;')
        
        print(f"Injected success=true, email={user_info['email']}")
        print(f"Returning HTML response with success")
        return HTMLResponse(content=html_content, status_code=200)
        
    except Exception as e:
        print(f"Gmail OAuth callback error: {e}")
        
        # Load and return error HTML page
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        # Get the frontend URL from environment or use a default
        frontend_url = os.getenv('FRONTEND_URL', 'http://localhost:5173')
        print(f"Error case - Frontend URL: {frontend_url}")
        
        # Replace success content with error content
        html_content = html_content.replace('✅', '❌')
        html_content = html_content.replace('Gmail Connected Successfully!', 'Gmail Connection Failed')
        html_content = html_content.replace('Your Gmail account has been connected.', 'Failed to connect your Gmail account.')
        
        # Inject the error data directly into the HTML
        html_content = html_content.replace('const success = urlParams.get(\'success\');', 'const success = \'false\';')
        html_content = html_content.replace('const email = urlParams.get(\'email\');', 'const email = null;')
        html_content = html_content.replace('const error = urlParams.get(\'error\');', 'const error = \'callback_failed\';')
        
        print(f"Injected success=false, error=callback_failed")
        print(f"Returning HTML response with error")
        return HTMLResponse(content=html_content, status_code=200)

@router.get("/configs", response_model=List[dict])
async def get_gmail_configs(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all Gmail configurations for the current company"""
    
    try:
        configs = await gmail_service.get_company_gmail_configs(
            db=db,
            company_id=str(current_user.company_id)
        )
        
        # Convert to dict format for response
        config_list = []
        for config in configs:
            config_dict = {
                "id": str(config.id),
                "gmail_address": config.gmail_address,
                "display_name": config.display_name,
                "is_active": config.is_active,
                "last_sync": config.last_sync.isoformat() if config.last_sync else None,
                "sync_frequency_minutes": config.sync_frequency_minutes,
                "granted_scopes": config.granted_scopes,
                "created_at": config.created_at.isoformat(),
                "updated_at": config.updated_at.isoformat()
            }
            config_list.append(config_dict)
        
        return config_list
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch Gmail configurations: {str(e)}"
        )

@router.post("/configs/{config_id}/test")
async def test_gmail_config(
    config_id: str,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test Gmail configuration connection"""
    
    # Only admins can test configurations
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can test Gmail configurations"
        )
    
    try:
        # Get configuration with decrypted tokens
        config = await gmail_service.get_gmail_config_by_id(db, config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail configuration not found"
            )
        
        # Test connection
        connection_ok = await gmail_service.test_gmail_connection(config.access_token)
        
        return {
            "success": True,
            "connected": connection_ok,
            "gmail_address": config.gmail_address,
            "message": "Connection successful" if connection_ok else "Connection failed"
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to test Gmail configuration: {str(e)}"
        )

@router.delete("/configs/{config_id}")
async def delete_gmail_config(
    config_id: str,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete Gmail configuration"""
    
    # Only admins can delete configurations
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete Gmail configurations"
        )
    
    try:
        from sqlalchemy import text
        
        # Soft delete by setting is_active to false
        result = await db.execute(
            text("UPDATE gmail_configs SET is_active = false, updated_at = NOW() WHERE id = :config_id AND company_id = :company_id"),
            {'config_id': config_id, 'company_id': str(current_user.company_id)}
        )
        
        if result.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail configuration not found"
            )
        
        await db.commit()
        
        return {
            "success": True,
            "message": "Gmail configuration deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete Gmail configuration: {str(e)}"
        )

@router.post("/configs/{config_id}/toggle")
async def toggle_gmail_config(
    config_id: str,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle Gmail configuration active status"""
    
    # Only admins can toggle configurations
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can toggle Gmail configurations"
        )
    
    try:
        from sqlalchemy import text
        
        # Toggle is_active status
        result = await db.execute(
            text("""
                UPDATE gmail_configs 
                SET is_active = NOT is_active, updated_at = NOW() 
                WHERE id = :config_id AND company_id = :company_id
                RETURNING is_active
            """),
            {'config_id': config_id, 'company_id': str(current_user.company_id)}
        )
        
        row = result.fetchone()
        if not row:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail configuration not found"
            )
        
        await db.commit()
        
        return {
            "success": True,
            "is_active": row[0],
            "message": f"Gmail configuration {'activated' if row[0] else 'deactivated'}"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle Gmail configuration: {str(e)}"
        )

# ================================================================
# Gmail Webhook Endpoint - CORRECTED FOR PUB/SUB
# ================================================================

@router.post("/webhook")
async def gmail_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Gmail webhook endpoint that receives Pub/Sub push notifications
    """
    try:
        # Get request body and headers
        request_body = await request.body()
        all_headers = dict(request.headers)
        
        print(f"\n========== GMAIL WEBHOOK RECEIVED ==========")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Client IP: {request.client.host}")
        print(f"User-Agent: {all_headers.get('user-agent', 'Unknown')}")
        print(f"Content-Type: {all_headers.get('content-type', 'Unknown')}")
        
        if not request_body:
            print("No request body found")
            return Response(status_code=400, content="No request body")
        
        try:
            # Parse Pub/Sub message
            pubsub_message = json.loads(request_body.decode('utf-8'))
            print(f"Pub/Sub Message Structure:")
            print(f"  Message ID: {pubsub_message.get('message', {}).get('messageId')}")
            print(f"  Publish Time: {pubsub_message.get('message', {}).get('publishTime')}")
            print(f"  Subscription: {pubsub_message.get('subscription', '')}")
            
            # Extract the Gmail notification from Pub/Sub message
            message = pubsub_message.get('message', {})
            
            if 'data' in message:
                # Decode the base64 Gmail notification data
                try:
                    decoded_data = base64.b64decode(message['data']).decode('utf-8')
                    gmail_notification = json.loads(decoded_data)
                    
                    print(f"Gmail Notification:")
                    print(f"  Email Address: {gmail_notification.get('emailAddress')}")
                    print(f"  History ID: {gmail_notification.get('historyId')}")
                    
                    # Extract Gmail data
                    email_address = gmail_notification.get('emailAddress')
                    history_id = gmail_notification.get('historyId')
                    
                    if email_address and history_id:
                        # Process the Gmail notification
                        result = await _process_gmail_history_change(
                            db, email_address, history_id
                        )
                        
                        print(f"Processing result: {result}")
                        print(f"==========================================\n")
                        
                        if result['success']:
                            return Response(status_code=200, content="Gmail notification processed successfully")
                        else:
                            return Response(status_code=200, content=f"Processing failed: {result.get('error', 'Unknown error')}")
                    else:
                        print("Missing email_address or history_id in Gmail notification")
                        return Response(status_code=200, content="Invalid Gmail notification - missing data")
                        
                except Exception as decode_error:
                    print(f"Error decoding Gmail notification data: {decode_error}")
                    print(f"Raw data: {message.get('data', 'No data')}")
                    return Response(status_code=200, content="Error decoding Gmail notification")
            else:
                print("No data field in Pub/Sub message")
                return Response(status_code=200, content="No data in Pub/Sub message")
                
        except json.JSONDecodeError as e:
            print(f"Failed to parse Pub/Sub JSON: {e}")
            print(f"Raw body: {request_body}")
            return Response(status_code=400, content="Invalid JSON in request body")
        except Exception as parse_error:
            print(f"Error parsing Pub/Sub message: {parse_error}")
            return Response(status_code=200, content="Error parsing message")
        
    except Exception as e:
        print(f"CRITICAL ERROR in Gmail webhook: {e}")
        import traceback
        traceback.print_exc()
        return Response(status_code=200, content="Critical error processed")

# Helper functions for webhook processing
async def _process_gmail_history_change(
    db: AsyncSession, 
    email_address: str, 
    history_id: str
) -> Dict[str, Any]:
    """Process Gmail history change notification"""
    try:
        print(f"Processing Gmail history change for {email_address}, history: {history_id}")
        
        # Get user's access token
        access_token = await _get_access_token_for_email(db, email_address)
        if not access_token:
            print(f"No access token found for {email_address}")
            return {'success': False, 'error': 'NO_ACCESS_TOKEN'}
        
        # Get Gmail history to find new messages
        new_messages = await _get_gmail_history_messages(email_address, access_token, history_id)
        
        if new_messages:
            print(f"Found {len(new_messages)} new messages")
            
            # Process each new message through existing workflow
            processed_count = 0
            for message in new_messages:
                try:
                    success = await _process_new_gmail_message(db, email_address, message, access_token)
                    if success:
                        processed_count += 1
                except Exception as msg_error:
                    print(f"Error processing message {message.get('id')}: {msg_error}")
                    continue
            
            return {
                'success': True, 
                'processed_messages': processed_count,
                'total_messages': len(new_messages)
            }
        else:
            print("No new messages found in history")
            return {'success': True, 'processed_messages': 0}
            
    except Exception as e:
        print(f"Error processing Gmail history change: {e}")
        import traceback
        traceback.print_exc()
        return {'success': False, 'error': str(e)}

async def _get_access_token_for_email(db: AsyncSession, email_address: str) -> Optional[str]:
    """Get access token for specific Gmail address"""
    try:
        result = await db.execute(
            text("SELECT access_token, refresh_token, token_expires_at FROM gmail_configs WHERE gmail_address = :email AND is_active = true"),
            {'email': email_address}
        )
        
        row = result.fetchone()
        if not row:
            print(f"No gmail_config found for {email_address}")
            return None
        
        # Decrypt tokens
        access_token = gmail_service._decrypt_token(row.access_token)
        
        # Check if token is expired and refresh if needed
        if row.token_expires_at and datetime.utcnow() >= row.token_expires_at:
            if row.refresh_token:
                refresh_token = gmail_service._decrypt_token(row.refresh_token)
                print(f"Refreshing expired token for {email_address}")
                new_tokens = await gmail_service.refresh_access_token(refresh_token)
                
                # Update tokens in DB
                encrypted_access = gmail_service._encrypt_token(new_tokens['access_token'])
                encrypted_refresh = gmail_service._encrypt_token(new_tokens['refresh_token'])
                
                await db.execute(
                    text("""
                        UPDATE gmail_configs 
                        SET access_token = :access_token, 
                            refresh_token = :refresh_token,
                            token_expires_at = :expires_at,
                            updated_at = NOW()
                        WHERE gmail_address = :email AND is_active = true
                    """),
                    {
                        'access_token': encrypted_access,
                        'refresh_token': encrypted_refresh,
                        'expires_at': new_tokens['expires_at'],
                        'email': email_address
                    }
                )
                await db.commit()
                
                return new_tokens['access_token']
        
        return access_token
        
    except Exception as e:
        print(f"Error getting access token for {email_address}: {e}")
        return None

async def _get_gmail_history_messages(email_address: str, access_token: str, history_id: str) -> List[Dict]:
    """Get new messages from Gmail history API - FIXED VERSION"""
    try:
        async with httpx.AsyncClient() as client:
            # Try Method 1: Get history from a slightly earlier point
            # Convert history_id to int and subtract a small amount to catch recent changes
            try:
                history_id_int = int(history_id)
                # Start from a bit earlier to catch the actual changes
                start_history_id = max(1, history_id_int - 100)  # Go back 100 history entries
            except ValueError:
                start_history_id = history_id
            
            print(f"Fetching Gmail history from {start_history_id} to current ({history_id})")
            
            response = await client.get(
                f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/history',
                headers={'Authorization': f'Bearer {access_token}'},
                params={
                    'startHistoryId': str(start_history_id),
                    'historyTypes': 'messageAdded'
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                history_data = response.json()
                print(f"Gmail History API response: {len(history_data.get('history', []))} history entries")
                
                new_messages = []
                for history_entry in history_data.get('history', []):
                    for message_added in history_entry.get('messagesAdded', []):
                        message = message_added['message']
                        label_ids = message.get('labelIds', [])
                        
                        # Only process messages in INBOX that are UNREAD
                        if 'INBOX' in label_ids and 'UNREAD' in label_ids:
                            new_messages.append(message)
                            print(f"  Found new inbox message: {message['id']}")
                
                # If no messages found with history method, try recent messages approach
                if not new_messages:
                    print("No messages found via history API, trying recent messages approach...")
                    return await _get_recent_unread_messages(email_address, access_token)
                
                return new_messages
                
            elif response.status_code == 404:
                # History ID is too old or invalid, get recent unread messages instead
                print(f"History ID {history_id} not found, fetching recent unread messages")
                return await _get_recent_unread_messages(email_address, access_token)
                
            else:
                print(f"Gmail history API error: {response.status_code} - {response.text}")
                # Fallback to recent messages
                return await _get_recent_unread_messages(email_address, access_token)
                
    except Exception as e:
        print(f"Error getting Gmail history: {e}")
        # Fallback to recent messages approach
        return await _get_recent_unread_messages(email_address, access_token)

async def _get_recent_unread_messages(email_address: str, access_token: str) -> List[Dict]:
    """Fallback method: Get recent unread messages directly"""
    try:
        print(f"Fetching recent unread messages for {email_address}")
        
        async with httpx.AsyncClient() as client:
            # Get unread messages from the last hour
            from datetime import datetime, timedelta
            one_hour_ago = datetime.utcnow() - timedelta(hours=1)
            after_date = one_hour_ago.strftime('%Y/%m/%d')
            
            # Query for recent unread inbox messages
            query = f'is:unread in:inbox after:{after_date}'
            
            response = await client.get(
                f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/messages',
                headers={'Authorization': f'Bearer {access_token}'},
                params={
                    'q': query,
                    'maxResults': 10
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])
                
                print(f"Found {len(messages)} recent unread messages")
                
                # Return messages in the same format as history API
                formatted_messages = []
                for msg in messages:
                    formatted_messages.append({
                        'id': msg['id'],
                        'threadId': msg['threadId'],
                        'labelIds': ['INBOX', 'UNREAD']  # Assume these since they matched our query
                    })
                
                return formatted_messages
            else:
                print(f"Failed to get recent messages: {response.status_code} - {response.text}")
                return []
                
    except Exception as e:
        print(f"Error getting recent unread messages: {e}")
        return []
async def _process_new_gmail_message(db: AsyncSession, email_address: str, message: Dict, access_token: str) -> bool:
    """Process a new Gmail message through existing workflow"""
    try:
        message_id = message['id']
        print(f"Processing message {message_id} for {email_address}")
        
        # Get full message details
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/messages/{message_id}',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'format': 'full'},
                timeout=30.0
            )
            
            if response.status_code == 200:
                full_message = response.json()
                
                # Extract basic email info for logging
                headers = full_message.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                
                print(f"  Subject: {subject}")
                print(f"  From: {from_email}")
                
                # Use existing email processing logic from EmailPollingService
                from services.email_polling_service import EmailPollingService
                polling_service = EmailPollingService()
                
                # Process this message through the existing workflow system
                await polling_service._process_single_email(db, full_message, email_address)
                
                print(f"  Successfully processed message {message_id}")
                return True
            else:
                print(f"  Failed to get message details: {response.status_code} - {response.text}")
                return False
                
    except Exception as e:
        print(f"Error processing Gmail message {message.get('id', 'unknown')}: {e}")
        return False

@router.post("/webhook/test")
async def test_gmail_webhook():
    """
    Test endpoint to simulate Gmail webhook notifications
    Use this to test webhook processing without real Gmail notifications
    """
    try:
        print("\nTesting Gmail webhook notification...")
        
        # Simulate a Pub/Sub message with Gmail notification
        test_gmail_notification = {
            "emailAddress": "amanc1248@gmail.com",
            "historyId": "12345"
        }
        
        # Encode like Pub/Sub does
        encoded_notification = base64.b64encode(
            json.dumps(test_gmail_notification).encode('utf-8')
        ).decode('utf-8')
        
        test_pubsub_message = {
            "message": {
                "data": encoded_notification,
                "messageId": "test-message-123",
                "publishTime": datetime.utcnow().isoformat() + "Z"
            },
            "subscription": "projects/jarvis-voice-assistant-467210/subscriptions/gmail-notifications-sub"
        }
        
        print(f"Test Pub/Sub message: {json.dumps(test_pubsub_message, indent=2)}")
        print(f"Decoded Gmail notification: {json.dumps(test_gmail_notification, indent=2)}")
        
        return {
            "success": True,
            "message": "Test webhook data prepared successfully",
            "test_data": test_pubsub_message,
            "note": "This simulates what your webhook endpoint receives from Pub/Sub"
        }
        
    except Exception as e:
        print(f"Error in test webhook: {str(e)}")
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/webhook/process-test-email")
async def test_email_processing(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Test endpoint to simulate email processing through webhook pipeline
    This helps test the email processing logic without real Gmail webhooks
    """
    try:
        print("\nTesting email processing pipeline...")
        
        # Only admins can test email processing
        if current_user.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can test email processing"
            )
        
        from services.email_webhook_processor import email_webhook_processor
        
        # Simulate a webhook notification
        test_channel_id = f"hr-automation-{current_user.email}-{datetime.now().strftime('%Y%m%d')}"
        test_resource_id = "test-email-123"
        test_message_number = "1"
        
        print(f"Test Channel ID: {test_channel_id}")
        print(f"Test Resource ID: {test_resource_id}")
        print(f"Test User: {current_user.email}")
        
        # Test the webhook processor
        result = await email_webhook_processor.process_webhook_notification(
            db=db,
            channel_id=test_channel_id,
            resource_id=test_resource_id,
            resource_state="exists",
            message_number=test_message_number,
            headers={"test": "true"},
            body='{"test": "email processing"}'
        )
        
        print(f"Processing Result: {result}")
        
        return {
            "success": True,
            "message": "Email processing test completed",
            "test_data": {
                "channel_id": test_channel_id,
                "resource_id": test_resource_id,
                "user_email": current_user.email
            },
            "processing_result": result
        }
        
    except Exception as e:
        print(f"Error in test email processing: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e)
        }

@router.post("/hybrid/start")
async def start_hybrid_email_service(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Start the hybrid email service (webhook + polling fallback)
    Only admins can start the service
    """
    try:
        # Only admins can start the service
        if current_user.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can start the hybrid email service"
            )
        
        from services.hybrid_email_service import hybrid_email_service
        
        result = await hybrid_email_service.start_hybrid_service(db)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start hybrid service: {str(e)}"
        )

@router.get("/hybrid/status")
async def get_hybrid_service_status(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get the current status of the hybrid email service
    """
    try:
        from services.hybrid_email_service import hybrid_email_service
        
        status = await hybrid_email_service.get_service_status(db)
        
        return status
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get service status: {str(e)}"
        )

@router.post("/hybrid/toggle")
async def toggle_hybrid_service_mode(
    force_mode: Optional[str] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Toggle between webhook and polling modes
    Only admins can toggle modes
    """
    try:
        # Only admins can toggle modes
        if current_user.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can toggle service modes"
            )
        
        from services.hybrid_email_service import hybrid_email_service
        
        result = await hybrid_email_service.toggle_mode(db, force_mode)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle service mode: {str(e)}"
        )