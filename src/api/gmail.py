import json
import base64
import os
from datetime import datetime, timedelta
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
    
    if error:
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        html_content = html_content.replace('✅', '❌')
        html_content = html_content.replace('Gmail Connected Successfully!', 'Gmail Connection Failed')
        html_content = html_content.replace('Your Gmail account has been connected.', f'OAuth error: {error}')
        
        return HTMLResponse(content=html_content, status_code=200)
    
    try:
        state_data = json.loads(base64.urlsafe_b64decode(state.encode()).decode())
        user_id = state_data['user_id']
        company_id = state_data['company_id']
        
        tokens = await gmail_service.exchange_code_for_tokens(code)
        user_info = await gmail_service.get_user_info(tokens['access_token'])
        
        connection_ok = await gmail_service.test_gmail_connection(tokens['access_token'])
        if not connection_ok:
            raise Exception("Failed to connect to Gmail API")
        
        config = await gmail_service.save_gmail_config(
            db=db,
            user_id=user_id,
            company_id=company_id,
            gmail_address=user_info['email'],
            display_name=user_info.get('name', user_info['email']),
            tokens=tokens
        )
        
        try:
            from services.gmail_watch_manager import gmail_watch_manager
            from models.user import Profile
            
            connected_gmail_profile = Profile(
                id=user_id,
                email=user_info['email'],
                company_id=company_id,
                password_hash="",
                role_id="",
                preferences={},
                is_active=True
            )
            
            watch_result = await gmail_watch_manager.setup_watch_for_user(
                db=db,
                user=connected_gmail_profile,
                access_token=tokens['access_token']
            )
            
            if watch_result['success']:
                print(f"Gmail watch setup successful: {watch_result['message']}")
            else:
                print(f"Gmail watch setup failed: {watch_result['error']}")
                
        except Exception as e:
            print(f"Error setting up Gmail watch: {str(e)}")
        
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        html_content = html_content.replace('const success = urlParams.get(\'success\');', f'const success = \'true\';')
        html_content = html_content.replace('const email = urlParams.get(\'email\');', f'const email = \'{user_info["email"]}\';')
        html_content = html_content.replace('const error = urlParams.get(\'error\');', 'const error = null;')
        
        return HTMLResponse(content=html_content, status_code=200)
        
    except Exception as e:
        print(f"Gmail OAuth callback error: {e}")
        
        html_path = os.path.join(os.path.dirname(__file__), 'oauth_success.html')
        with open(html_path, 'r') as f:
            html_content = f.read()
        
        html_content = html_content.replace('✅', '❌')
        html_content = html_content.replace('Gmail Connected Successfully!', 'Gmail Connection Failed')
        html_content = html_content.replace('Your Gmail account has been connected.', 'Failed to connect your Gmail account.')
        
                # Inject the error data directly into the HTML
        html_content = html_content.replace('const success = urlParams.get(\'success\');', 'const success = \'false\';')
        html_content = html_content.replace('const email = urlParams.get(\'email\');', 'const email = null;')
        html_content = html_content.replace('const error = urlParams.get(\'error\');', 'const error = \'callback_failed\';')
        
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
    
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can test Gmail configurations"
        )
    
    try:
        config = await gmail_service.get_gmail_config_by_id(db, config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Gmail configuration not found"
            )
        
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
    
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete Gmail configurations"
        )
    
    try:
        from sqlalchemy import text
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
    
    if current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can toggle Gmail configurations"
        )
    
    try:
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
# Gmail Webhook Endpoint - PRIMARY TAB + UNREAD ONLY
# ================================================================

# Track processed history IDs and message IDs to prevent reprocessing
_last_processed_history = {}
_processed_message_ids = set()

@router.post("/webhook")
async def gmail_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Gmail webhook endpoint - processes only PRIMARY tab UNREAD emails
    """
    try:
        request_body = await request.body()
        all_headers = dict(request.headers)
        
        print(f"\n========== GMAIL WEBHOOK (PRIMARY + UNREAD ONLY) ==========")
        print(f"Timestamp: {datetime.utcnow().isoformat()}")
        print(f"Client IP: {request.client.host}")
        
        if not request_body:
            print("No request body found")
            return Response(status_code=400, content="No request body")
        
        try:
            pubsub_message = json.loads(request_body.decode('utf-8'))
            print(f"Pub/Sub Message ID: {pubsub_message.get('message', {}).get('messageId')}")
            
            message = pubsub_message.get('message', {})
            
            if 'data' in message:
                try:
                    decoded_data = base64.b64decode(message['data']).decode('utf-8')
                    gmail_notification = json.loads(decoded_data)
                    
                    email_address = gmail_notification.get('emailAddress')
                    history_id = gmail_notification.get('historyId')
                    
                    print(f"Gmail Notification: {email_address}, History: {history_id}")
                    
                    if email_address and history_id:
                        result = await _process_gmail_history_change(
                            db, email_address, history_id
                        )
                        
                        print(f"Processing result: {result}")
                        print(f"==========================================\n")
                        
                        return Response(status_code=200, content="Notification processed")
                    else:
                        return Response(status_code=200, content="Invalid notification")
                        
                except Exception as decode_error:
                    print(f"Error decoding Gmail data: {decode_error}")
                    return Response(status_code=200, content="Decode error")
            else:
                return Response(status_code=200, content="No data")
                
        except json.JSONDecodeError as e:
            print(f"JSON parse error: {e}")
            return Response(status_code=400, content="Invalid JSON")
        
    except Exception as e:
        print(f"Critical webhook error: {e}")
        return Response(status_code=200, content="Error processed")

# ================================================================
# Helper Functions - PRIMARY TAB + UNREAD FILTERING
# ================================================================

async def _process_gmail_history_change(
    db: AsyncSession, 
    email_address: str, 
    history_id: str
) -> Dict[str, Any]:
    """Process Gmail history - PRIMARY tab UNREAD emails only"""
    try:
        print(f"Processing history for {email_address}, ID: {history_id}")
        
        # Prevent reprocessing same history
        last_processed = _last_processed_history.get(email_address)
        if last_processed and int(history_id) <= int(last_processed):
            print(f"History {history_id} already processed - SKIPPING")
            return {'success': True, 'processed_messages': 0, 'reason': 'already_processed'}
        
        access_token = await _get_access_token_for_email(db, email_address)
        if not access_token:
            return {'success': False, 'error': 'NO_ACCESS_TOKEN'}
        
        # Get only PRIMARY tab UNREAD messages
        new_messages = await _get_primary_unread_messages(email_address, access_token, history_id)
        
        if new_messages:
            print(f"Found {len(new_messages)} PRIMARY unread messages")
            
            processed_count = 0
            for message in new_messages:
                message_id = message['id']
                
                # Skip if already processed this message
                if message_id in _processed_message_ids:
                    print(f"  Message {message_id} already processed - SKIPPING")
                    continue
                
                try:
                    success = await _process_primary_unread_message(db, email_address, message, access_token)
                    if success:
                        processed_count += 1
                        _processed_message_ids.add(message_id)
                        print(f"  PRIMARY message {message_id} processed successfully")
                except Exception as msg_error:
                    print(f"  Error processing message {message_id}: {msg_error}")
            
            # Update processed history
            _last_processed_history[email_address] = history_id
            
            return {
                'success': True, 
                'processed_messages': processed_count,
                'total_messages': len(new_messages)
            }
        else:
            print("No PRIMARY unread messages found")
            _last_processed_history[email_address] = history_id
            return {'success': True, 'processed_messages': 0}
            
    except Exception as e:
        print(f"Error processing history: {e}")
        return {'success': False, 'error': str(e)}

async def _get_access_token_for_email(db: AsyncSession, email_address: str) -> Optional[str]:
    """Get access token for Gmail address"""
    try:
        result = await db.execute(
            text("SELECT access_token, refresh_token, token_expires_at FROM gmail_configs WHERE gmail_address = :email AND is_active = true"),
            {'email': email_address}
        )
        
        row = result.fetchone()
        if not row:
            return None
        
        access_token = gmail_service._decrypt_token(row.access_token)
        
        # Refresh if expired
        if row.token_expires_at and datetime.utcnow() >= row.token_expires_at:
            if row.refresh_token:
                refresh_token = gmail_service._decrypt_token(row.refresh_token)
                new_tokens = await gmail_service.refresh_access_token(refresh_token)
                
                # Update tokens
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
        print(f"Error getting access token: {e}")
        return None

async def _get_primary_unread_messages(email_address: str, access_token: str, history_id: str) -> List[Dict]:
    """Get PRIMARY tab UNREAD messages only"""
    try:
        # Try history API first
        history_messages = await _get_history_primary_messages(email_address, access_token, history_id)
        
        if history_messages:
            return history_messages
        
        # Fallback to direct query
        print("No history results, trying direct PRIMARY query...")
        return await _get_recent_primary_unread_messages(email_address, access_token)
        
    except Exception as e:
        print(f"Error getting PRIMARY messages: {e}")
        return []

async def _get_history_primary_messages(email_address: str, access_token: str, history_id: str) -> List[Dict]:
    """Get PRIMARY messages from Gmail history"""
    try:
        async with httpx.AsyncClient() as client:
            try:
                history_id_int = int(history_id)
                start_history_id = max(1, history_id_int - 20)
            except ValueError:
                start_history_id = history_id
            
            print(f"Checking history from {start_history_id} to {history_id}")
            
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
                history_entries = history_data.get('history', [])
                
                print(f"Found {len(history_entries)} history entries")
                
                primary_unread_messages = []
                
                for history_entry in history_entries:
                    for message_added in history_entry.get('messagesAdded', []):
                        message = message_added['message']
                        message_id = message['id']
                        label_ids = message.get('labelIds', [])
                        
                        # Check if message is PRIMARY and UNREAD
                        if await _is_primary_unread_message(email_address, access_token, message_id, label_ids):
                            primary_unread_messages.append(message)
                            print(f"  Found PRIMARY unread: {message_id}")
                        else:
                            print(f"  Filtered out: {message_id}")
                
                return primary_unread_messages
                
            else:
                print(f"History API error: {response.status_code}")
                return []
                
    except Exception as e:
        print(f"Error getting history messages: {e}")
        return []

async def _get_recent_primary_unread_messages(email_address: str, access_token: str) -> List[Dict]:
    """Get recent PRIMARY tab UNREAD messages"""
    try:
        print(f"Getting recent PRIMARY unread messages for {email_address}")
        
        async with httpx.AsyncClient() as client:
            # Only last 30 minutes to avoid old emails
            thirty_min_ago = datetime.utcnow() - timedelta(minutes=30)
            after_date = thirty_min_ago.strftime('%Y/%m/%d')
            
            # Strong PRIMARY tab filter
            query = (
                f'is:unread in:inbox '
                f'-category:promotions -category:social -category:updates -category:forums '
                f'after:{after_date}'
            )
            
            print(f"PRIMARY query: {query}")
            
            response = await client.get(
                f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/messages',
                headers={'Authorization': f'Bearer {access_token}'},
                params={
                    'q': query,
                    'maxResults': 3  # Very limited
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                messages = data.get('messages', [])
                
                print(f"Query found {len(messages)} messages")
                
                # Double-verify PRIMARY tab status
                verified_messages = []
                for msg in messages:
                    if msg['id'] not in _processed_message_ids:
                        if await _verify_primary_unread_status(email_address, access_token, msg['id']):
                            verified_messages.append({
                                'id': msg['id'],
                                'threadId': msg['threadId'],
                                'labelIds': ['INBOX', 'UNREAD']
                            })
                            print(f"  Verified PRIMARY unread: {msg['id']}")
                        else:
                            print(f"  Not PRIMARY or not unread: {msg['id']}")
                    else:
                        print(f"  Already processed: {msg['id']}")
                
                return verified_messages
            else:
                print(f"Query failed: {response.status_code}")
                return []
                
    except Exception as e:
        print(f"Error getting recent PRIMARY messages: {e}")
        return []

async def _is_primary_unread_message(email_address: str, access_token: str, message_id: str, label_ids: List[str]) -> bool:
    """Check if message is PRIMARY tab and UNREAD"""
    try:
        # Quick check: must have INBOX and UNREAD labels
        if 'INBOX' not in label_ids or 'UNREAD' not in label_ids:
            return False
        
        # Check for category labels that exclude from PRIMARY
        category_labels = [
            'CATEGORY_PROMOTIONS',
            'CATEGORY_SOCIAL', 
            'CATEGORY_UPDATES',
            'CATEGORY_FORUMS',
            'SPAM',
            'TRASH'
        ]
        
        # If has any category, not PRIMARY
        if any(cat in label_ids for cat in category_labels):
            return False
        
        # Additional verification for edge cases
        return await _verify_primary_unread_status(email_address, access_token, message_id)
        
    except Exception as e:
        print(f"Error checking PRIMARY status: {e}")
        return False

async def _verify_primary_unread_status(email_address: str, access_token: str, message_id: str) -> bool:
    """Double-verify message is PRIMARY and UNREAD"""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/messages/{message_id}',
                headers={'Authorization': f'Bearer {access_token}'},
                params={'format': 'minimal'},
                timeout=10.0
            )
            
            if response.status_code == 200:
                message_data = response.json()
                label_ids = message_data.get('labelIds', [])
                
                # Must be INBOX + UNREAD
                is_inbox_unread = 'INBOX' in label_ids and 'UNREAD' in label_ids
                
                # Must NOT have category labels
                category_labels = [
                    'CATEGORY_PROMOTIONS', 'CATEGORY_SOCIAL', 'CATEGORY_UPDATES', 
                    'CATEGORY_FORUMS', 'SPAM', 'TRASH'
                ]
                has_categories = any(cat in label_ids for cat in category_labels)
                
                is_primary_unread = is_inbox_unread and not has_categories
                
                if is_primary_unread:
                    print(f"    ✓ Message {message_id} verified as PRIMARY + UNREAD")
                else:
                    categories_found = [cat for cat in category_labels if cat in label_ids]
                    print(f"    ✗ Message {message_id} filtered out (categories: {categories_found}, unread: {'UNREAD' in label_ids})")
                
                return is_primary_unread
            else:
                return False
                
    except Exception as e:
        print(f"Error verifying status: {e}")
        return False

async def _process_primary_unread_message(db: AsyncSession, email_address: str, message: Dict, access_token: str) -> bool:
    """Process a PRIMARY tab UNREAD message"""
    try:
        message_id = message['id']
        
        # Final verification before processing
        if not await _verify_primary_unread_status(email_address, access_token, message_id):
            print(f"  Message {message_id} failed final verification - SKIPPING")
            return False
        
        print(f"Processing PRIMARY unread message {message_id}")
        
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
                
                headers = full_message.get('payload', {}).get('headers', [])
                subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
                from_email = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown')
                
                print(f"  Subject: {subject}")
                print(f"  From: {from_email}")
                
                # Check if it's a job application before processing workflow
                from services.email_polling_service import EmailPollingService
                polling_service = EmailPollingService()
                
                if polling_service._is_job_application(subject, from_email):
                    print(f"  JOB APPLICATION detected - processing workflow")
                    await polling_service._process_single_email(db, full_message, email_address)
                    return True
                else:
                    print(f"  Not a job application - SKIPPING workflow")
                    return False
                    
            else:
                print(f"  Failed to get message details: {response.status_code}")
                return False
                
    except Exception as e:
        print(f"Error processing PRIMARY message: {e}")
        return False

@router.post("/webhook/test")
async def test_gmail_webhook():
    """Test webhook simulation"""
    try:
        test_notification = {
            "emailAddress": "amanc1248@gmail.com",
            "historyId": "12345"
        }
        
        encoded_notification = base64.b64encode(
            json.dumps(test_notification).encode('utf-8')
        ).decode('utf-8')
        
        test_message = {
            "message": {
                "data": encoded_notification,
                "messageId": "test-123",
                "publishTime": datetime.utcnow().isoformat() + "Z"
            },
            "subscription": "projects/jarvis-voice-assistant-467210/subscriptions/gmail-notifications-sub"
        }
        
        return {
            "success": True,
            "message": "Test webhook prepared",
            "test_data": test_message
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/webhook/process-test-email")
async def test_email_processing(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Test email processing"""
    try:
        if current_user.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can test email processing"
            )
        
        from services.email_webhook_processor import email_webhook_processor
        
        result = await email_webhook_processor.process_webhook_notification(
            db=db,
            channel_id=f"test-{current_user.email}",
            resource_id="test-123",
            resource_state="exists",
            message_number="1",
            headers={"test": "true"},
            body='{"test": "processing"}'
        )
        
        return {
            "success": True,
            "message": "Test completed",
            "processing_result": result
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

@router.post("/hybrid/start")
async def start_hybrid_email_service(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Start hybrid email service"""
    try:
        if current_user.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can start the service"
            )
        
        from services.hybrid_email_service import hybrid_email_service
        result = await hybrid_email_service.start_hybrid_service(db)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start service: {str(e)}"
        )

@router.get("/hybrid/status")
async def get_hybrid_service_status(
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get service status"""
    try:
        from services.hybrid_email_service import hybrid_email_service
        status_result = await hybrid_email_service.get_service_status(db)
        return status_result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get status: {str(e)}"
        )

@router.post("/hybrid/toggle")
async def toggle_hybrid_service_mode(
    force_mode: Optional[str] = None,
    current_user: Profile = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Toggle service modes"""
    try:
        if current_user.role.name != "admin":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admins can toggle modes"
            )
        
        from services.hybrid_email_service import hybrid_email_service
        result = await hybrid_email_service.toggle_mode(db, force_mode)
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to toggle mode: {str(e)}"
        )