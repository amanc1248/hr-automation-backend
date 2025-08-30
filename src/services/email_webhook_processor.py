"""
Email Webhook Processor Service
Handles Gmail webhook notifications and processes emails through workflows
"""

import logging
import json
from datetime import datetime
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .gmail_service import gmail_service
from .email_polling_service import EmailPollingService
from models.gmail_webhook import GmailWatch
from models.user import Profile

logger = logging.getLogger(__name__)

class EmailWebhookProcessor:
    """Processes Gmail webhook notifications and triggers email workflows"""
    
    def __init__(self):
        self.email_polling_service = EmailPollingService()
    
    async def process_webhook_notification(
        self, 
        db: AsyncSession,
        channel_id: str,
        resource_id: str,
        resource_state: str,
        message_number: str,
        headers: Dict[str, str],
        body: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a Gmail webhook notification
        """
        try:
            logger.info(f"🔍 [Webhook Processor] Processing notification for channel: {channel_id}")
            
            # Step 1: Validate webhook and find associated user
            user_info = await self._get_user_from_channel(db, channel_id)
            if not user_info:
                logger.warning(f"⚠️  [Webhook Processor] No user found for channel: {channel_id}")
                return {
                    'success': False,
                    'error': 'USER_NOT_FOUND',
                    'message': f'No user found for channel: {channel_id}'
                }
            
            user_id, user_email = user_info
            logger.info(f"👤 [Webhook Processor] Processing for user: {user_email}")
            
            # Step 2: Handle different resource states
            if resource_state == "sync":
                logger.info(f"📡 [Webhook Processor] Sync notification - no email processing needed")
                return {
                    'success': True,
                    'message': 'Sync notification processed',
                    'action': 'sync_only'
                }
            
            elif resource_state == "exists":
                logger.info(f"📧 [Webhook Processor] New email notification - processing email")
                return await self._process_new_email_notification(
                    db, user_id, user_email, resource_id, message_number
                )
            
            else:
                logger.info(f"❓ [Webhook Processor] Unknown resource state: {resource_state}")
                return {
                    'success': True,
                    'message': f'Unknown state processed: {resource_state}',
                    'action': 'unknown_state'
                }
                
        except Exception as e:
            logger.error(f"❌ [Webhook Processor] Error processing webhook: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': 'PROCESSING_ERROR',
                'message': f'Failed to process webhook: {str(e)}'
            }
    
    async def _get_user_from_channel(self, db: AsyncSession, channel_id: str) -> Optional[tuple]:
        """
        Get user information from channel ID
        """
        try:
            # Find active watch for this channel
            result = await db.execute(
                text("""
                    SELECT user_id, user_email 
                    FROM gmail_watches 
                    WHERE channel_id = :channel_id AND is_active = true
                """),
                {'channel_id': channel_id}
            )
            
            row = result.fetchone()
            if row:
                return str(row.user_id), row.user_email
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error getting user from channel: {e}")
            return None
    
    async def _process_new_email_notification(
        self,
        db: AsyncSession,
        user_id: str,
        user_email: str,
        resource_id: str,
        message_number: str
    ) -> Dict[str, Any]:
        """
        Process a new email notification by fetching email content and triggering workflows
        """
        try:
            logger.info(f"📧 [Webhook Processor] Processing new email for {user_email}")
            
            # Step 1: Get user's Gmail access token
            access_token = await self._get_user_access_token(db, user_id)
            if not access_token:
                logger.error(f"❌ [Webhook Processor] No valid access token for user {user_email}")
                return {
                    'success': False,
                    'error': 'NO_ACCESS_TOKEN',
                    'message': 'User has no valid Gmail access token'
                }
            
            # Step 1.5: Quick check - get basic email metadata to check if it's unread
            basic_metadata = await self._get_basic_email_metadata(access_token, resource_id)
            if basic_metadata:
                label_ids = basic_metadata.get('labelIds', [])
                if 'UNREAD' not in label_ids:
                    logger.info(f"⏭️  [Webhook Processor] Skipping already-read email (early check): {resource_id}")
                    return {
                        'success': True,
                        'message': 'Email already read - skipping processing (early check)',
                        'action': 'skipped_read_email_early',
                        'email_id': resource_id
                    }
            
            # Step 2: Fetch email content using Gmail API
            email_data = await self._fetch_email_content(access_token, resource_id)
            if not email_data:
                logger.error(f"❌ [Webhook Processor] Failed to fetch email content for {user_email}")
                return {
                    'success': False,
                    'error': 'EMAIL_FETCH_FAILED',
                    'message': 'Failed to fetch email content from Gmail API'
                }
            
            # Step 2.5: Double-check if email is unread before processing (redundant safety check)
            label_ids = email_data.get('label_ids', [])
            if 'UNREAD' not in label_ids:
                logger.info(f"⏭️  [Webhook Processor] Skipping already-read email: {resource_id}")
                return {
                    'success': True,
                    'message': 'Email already read - skipping processing',
                    'action': 'skipped_read_email',
                    'email_id': resource_id
                }
            
            logger.info(f"✅ [Webhook Processor] Email content fetched successfully")
            logger.info(f"   📧 Subject: {email_data.get('subject', 'No subject')}")
            logger.info(f"   👤 From: {email_data.get('from', 'Unknown')}")
            logger.info(f"   📅 Date: {email_data.get('date', 'Unknown')}")
            logger.info(f"   🏷️  Labels: {label_ids}")
            
            # Step 3: Process email through existing workflow system
            workflow_result = await self._process_email_workflow(
                db, user_id, user_email, email_data
            )
            
            if workflow_result['success']:
                logger.info(f"✅ [Webhook Processor] Email workflow completed successfully")
                return {
                    'success': True,
                    'message': 'Email processed through workflow',
                    'action': 'workflow_completed',
                    'workflow_result': workflow_result
                }
            else:
                logger.warning(f"⚠️  [Webhook Processor] Email workflow failed: {workflow_result['error']}")
                return {
                    'success': False,
                    'error': 'WORKFLOW_FAILED',
                    'message': f'Workflow processing failed: {workflow_result["error"]}',
                    'workflow_result': workflow_result
                }
                
        except Exception as e:
            logger.error(f"❌ [Webhook Processor] Error processing new email: {str(e)}")
            return {
                'success': False,
                'error': 'EMAIL_PROCESSING_ERROR',
                'message': f'Failed to process email: {str(e)}'
            }
    
    async def _get_user_access_token(self, db: AsyncSession, user_id: str) -> Optional[str]:
        """
        Get user's current Gmail access token
        """
        try:
            from services.gmail_watch_manager import gmail_watch_manager
            return await gmail_watch_manager._get_user_access_token(db, user_id)
        except Exception as e:
            logger.error(f"❌ Error getting access token: {e}")
            return None
    
    async def _get_basic_email_metadata(self, access_token: str, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetches basic email metadata (like labelIds) without fetching full content.
        This is a quick check to see if an email is unread.
        """
        try:
            import httpx
            
            async with httpx.AsyncClient() as client:
                metadata_response = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=10.0 # Shorter timeout for basic metadata
                )
                
                if metadata_response.status_code != 200:
                    logger.error(f"❌ Failed to fetch basic email metadata: {metadata_response.status_code}")
                    return None
                
                return metadata_response.json()
                
        except Exception as e:
            logger.error(f"❌ Error fetching basic email metadata: {e}")
            return None
    
    async def _fetch_email_content(self, access_token: str, email_id: str) -> Optional[Dict[str, Any]]:
        """
        Fetch email content from Gmail API
        """
        try:
            import httpx
            
            # Fetch email metadata and content
            async with httpx.AsyncClient() as client:
                # Get email metadata
                metadata_response = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=30.0
                )
                
                if metadata_response.status_code != 200:
                    logger.error(f"❌ Failed to fetch email metadata: {metadata_response.status_code}")
                    return None
                
                metadata = metadata_response.json()
                
                # Get email content
                content_response = await client.get(
                    f'https://gmail.googleapis.com/gmail/v1/users/me/messages/{email_id}?format=full',
                    headers={'Authorization': f'Bearer {access_token}'},
                    timeout=30.0
                )
                
                if content_response.status_code != 200:
                    logger.error(f"❌ Failed to fetch email content: {content_response.status_code}")
                    return None
                
                full_email = content_response.json()
                
                # Extract key email information
                email_data = {
                    'id': email_id,
                    'thread_id': metadata.get('threadId'),
                    'subject': self._extract_header_value(full_email, 'Subject'),
                    'from': self._extract_header_value(full_email, 'From'),
                    'to': self._extract_header_value(full_email, 'To'),
                    'date': self._extract_header_value(full_email, 'Date'),
                    'content': self._extract_email_content(full_email),
                    'snippet': metadata.get('snippet', ''),
                    'label_ids': metadata.get('labelIds', []),
                    'internal_date': metadata.get('internalDate')
                }
                
                return email_data
                
        except Exception as e:
            logger.error(f"❌ Error fetching email content: {e}")
            return None
    
    def _extract_header_value(self, email_data: Dict[str, Any], header_name: str) -> Optional[str]:
        """Extract header value from email data"""
        try:
            headers = email_data.get('payload', {}).get('headers', [])
            for header in headers:
                if header.get('name') == header_name:
                    return header.get('value')
            return None
        except Exception:
            return None
    
    def _extract_email_content(self, email_data: Dict[str, Any]) -> Optional[str]:
        """Extract email body content"""
        try:
            payload = email_data.get('payload', {})
            
            # Handle multipart emails
            if payload.get('mimeType') == 'multipart/alternative':
                parts = payload.get('parts', [])
                for part in parts:
                    if part.get('mimeType') == 'text/plain':
                        return part.get('body', {}).get('data', '')
                    elif part.get('mimeType') == 'text/html':
                        return part.get('body', {}).get('data', '')
            
            # Handle simple text emails
            elif payload.get('mimeType') == 'text/plain':
                return payload.get('body', {}).get('data', '')
            
            # Handle HTML emails
            elif payload.get('mimeType') == 'text/html':
                return payload.get('body', {}).get('data', '')
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error extracting email content: {e}")
            return None
    
    async def _process_email_workflow(
        self,
        db: AsyncSession,
        user_id: str,
        user_email: str,
        email_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Process email through existing workflow system
        This integrates with your current EmailPollingService
        """
        try:
            logger.info(f"🔄 [Webhook Processor] Starting workflow processing for email: {email_data.get('subject')}")
            
            # Convert email data to the format expected by EmailPollingService
            # This mimics the structure from your existing email polling
            workflow_email = {
                'id': email_data['id'],
                'thread_id': email_data['thread_id'],
                'subject': email_data['subject'],
                'from': email_data['from'],
                'to': email_data['to'],
                'date': email_data['date'],
                'content': email_data['content'],
                'snippet': email_data['snippet'],
                'label_ids': email_data['label_ids']
            }
            
            # INTEGRATE: Call the actual workflow processing
            logger.info(f"📝 [Webhook Processor] Processing email through workflow:")
            logger.info(f"   📧 Subject: {workflow_email['subject']}")
            logger.info(f"   👤 From: {workflow_email['from']}")
            logger.info(f"   📅 Date: {workflow_email['date']}")
            
            # Call the existing workflow processing system
            try:
                # Use the existing email polling service's workflow logic
                workflow_result = await self.email_polling_service.process_email_for_workflows(
                    db, workflow_email, user_id
                )
                
                logger.info(f"✅ [Webhook Processor] Workflow processing completed")
                logger.info(f"   📊 Result: {workflow_result}")
                
                return {
                    'success': True,
                    'message': 'Email processed through workflow successfully',
                    'email_processed': True,
                    'workflow_status': 'completed',
                    'workflow_result': workflow_result
                }
                
            except Exception as workflow_error:
                logger.error(f"❌ [Webhook Processor] Workflow processing failed: {workflow_error}")
                return {
                    'success': False,
                    'error': 'WORKFLOW_EXECUTION_ERROR',
                    'message': f'Workflow execution failed: {str(workflow_error)}',
                    'email_processed': True,
                    'workflow_status': 'failed'
                }
            
        except Exception as e:
            logger.error(f"❌ [Webhook Processor] Error in workflow processing: {str(e)}")
            return {
                'success': False,
                'error': 'WORKFLOW_ERROR',
                'message': f'Workflow processing failed: {str(e)}'
            }

# Global instance
email_webhook_processor = EmailWebhookProcessor()
