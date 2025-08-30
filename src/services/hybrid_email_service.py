"""
Hybrid Email Service
Combines webhook-driven processing with polling fallback for reliability
"""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text

from .email_webhook_processor import email_webhook_processor
from .email_polling_service import EmailPollingService
from .gmail_watch_manager import gmail_watch_manager

logger = logging.getLogger(__name__)

class HybridEmailService:
    """
    Hybrid email service that combines webhook and polling approaches
    - Primary: Webhook-driven real-time processing
    - Fallback: Polling for missed emails or webhook failures
    """
    
    def __init__(self):
        self.email_polling_service = EmailPollingService()
        self.webhook_processor = email_webhook_processor
        self.is_webhook_mode = True  # Can be toggled
    
    async def start_hybrid_service(self, db: AsyncSession):
        """
        Start the hybrid email service
        """
        try:
            logger.info("🚀 [Hybrid Service] Starting hybrid email service...")
            
            # Check webhook status for all users
            webhook_status = await self._check_webhook_status(db)
            
            if webhook_status['active_watches'] > 0:
                logger.info(f"✅ [Hybrid Service] {webhook_status['active_watches']} active webhook watches")
                self.is_webhook_mode = True
            else:
                logger.warning("⚠️  [Hybrid Service] No active webhooks - falling back to polling mode")
                self.is_webhook_mode = False
            
            # Start background polling as fallback (reduced frequency)
            if self.is_webhook_mode:
                logger.info("📡 [Hybrid Service] Webhook mode active - starting background polling fallback")
                asyncio.create_task(self._background_polling_fallback(db))
            else:
                logger.info("📡 [Hybrid Service] Polling mode active - starting standard polling")
                asyncio.create_task(self._standard_polling(db))
            
            return {
                'success': True,
                'mode': 'webhook' if self.is_webhook_mode else 'polling',
                'active_watches': webhook_status['active_watches'],
                'message': 'Hybrid email service started successfully'
            }
            
        except Exception as e:
            logger.error(f"❌ [Hybrid Service] Failed to start service: {str(e)}")
            return {
                'success': False,
                'error': 'STARTUP_ERROR',
                'message': f'Failed to start hybrid service: {str(e)}'
            }
    
    async def _check_webhook_status(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Check the status of webhook watches for all users
        """
        try:
            result = await db.execute(
                text("""
                    SELECT COUNT(*) as active_count, 
                           COUNT(CASE WHEN expiration <= NOW() + INTERVAL '1 day' THEN 1 END) as expiring_soon
                    FROM gmail_watches 
                    WHERE is_active = true
                """)
            )
            
            row = result.fetchone()
            active_watches = row.active_count if row else 0
            expiring_soon = row.expiring_soon if row else 0
            
            return {
                'active_watches': active_watches,
                'expiring_soon': expiring_soon,
                'status': 'healthy' if active_watches > 0 else 'no_watches'
            }
            
        except Exception as e:
            logger.error(f"❌ Error checking webhook status: {e}")
            return {
                'active_watches': 0,
                'expiring_soon': 0,
                'status': 'error'
            }
    
    async def _background_polling_fallback(self, db: AsyncSession):
        """
        Background polling with reduced frequency as fallback for webhook mode
        Runs every 15 minutes instead of every 5 minutes
        """
        try:
            logger.info("🔄 [Hybrid Service] Background polling fallback started (15-minute intervals)")
            
            while True:
                try:
                    # Check if webhooks are still active
                    webhook_status = await self._check_webhook_status(db)
                    
                    if webhook_status['active_watches'] == 0:
                        logger.warning("⚠️  [Hybrid Service] No active webhooks - switching to polling mode")
                        self.is_webhook_mode = False
                        break
                    
                    # Run reduced-frequency polling
                    logger.info("🔄 [Hybrid Service] Running background polling fallback...")
                    await self.email_polling_service.poll_all_gmail_accounts(db)
                    
                    # Wait 15 minutes before next poll
                    await asyncio.sleep(15 * 60)
                    
                except Exception as e:
                    logger.error(f"❌ [Hybrid Service] Background polling error: {e}")
                    await asyncio.sleep(5 * 60)  # Wait 5 minutes on error
                    
        except asyncio.CancelledError:
            logger.info("🛑 [Hybrid Service] Background polling cancelled")
        except Exception as e:
            logger.error(f"❌ [Hybrid Service] Background polling failed: {e}")
    
    async def _standard_polling(self, db: AsyncSession):
        """
        Standard polling mode when webhooks are not available
        """
        try:
            logger.info("🔄 [Hybrid Service] Standard polling mode started (5-minute intervals)")
            
            while True:
                try:
                    # Check if webhooks have become available
                    webhook_status = await self._check_webhook_status(db)
                    
                    if webhook_status['active_watches'] > 0:
                        logger.info("✅ [Hybrid Service] Webhooks available - switching to webhook mode")
                        self.is_webhook_mode = True
                        break
                    
                    # Run standard polling
                    logger.info("🔄 [Hybrid Service] Running standard polling...")
                    await self.email_polling_service.poll_all_gmail_accounts(db)
                    
                    # Wait 5 minutes before next poll
                    await asyncio.sleep(5 * 60)
                    
                except Exception as e:
                    logger.error(f"❌ [Hybrid Service] Standard polling error: {e}")
                    await asyncio.sleep(2 * 60)  # Wait 2 minutes on error
                    
        except asyncio.CancelledError:
            logger.info("🛑 [Hybrid Service] Standard polling cancelled")
        except Exception as e:
            logger.error(f"❌ [Hybrid Service] Standard polling failed: {e}")
    
    async def process_email_hybrid(
        self, 
        db: AsyncSession, 
        email_data: Dict[str, Any], 
        user_id: str,
        source: str = "webhook"
    ) -> Dict[str, Any]:
        """
        Process email using the best available method
        """
        try:
            logger.info(f"📧 [Hybrid Service] Processing email via {source}")
            
            if source == "webhook" and self.is_webhook_mode:
                # Use webhook processor
                logger.info("📡 [Hybrid Service] Using webhook processor")
                return await self.webhook_processor._process_email_workflow(
                    db, user_id, "user@example.com", email_data
                )
            else:
                # Use polling service
                logger.info("📡 [Hybrid Service] Using polling service")
                return await self.email_polling_service.process_email_for_workflows(
                    db, email_data, user_id
                )
                
        except Exception as e:
            logger.error(f"❌ [Hybrid Service] Error in hybrid processing: {e}")
            return {
                'success': False,
                'error': 'HYBRID_PROCESSING_ERROR',
                'message': f'Hybrid processing failed: {str(e)}'
            }
    
    async def get_service_status(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Get current status of the hybrid email service
        """
        try:
            webhook_status = await self._check_webhook_status(db)
            
            return {
                'success': True,
                'mode': 'webhook' if self.is_webhook_mode else 'polling',
                'webhook_status': webhook_status,
                'service_healthy': True,
                'last_check': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting service status: {e}")
            return {
                'success': False,
                'error': 'STATUS_CHECK_ERROR',
                'message': f'Failed to get status: {str(e)}'
            }
    
    async def toggle_mode(self, db: AsyncSession, force_mode: Optional[str] = None) -> Dict[str, Any]:
        """
        Toggle between webhook and polling modes
        """
        try:
            if force_mode:
                new_mode = force_mode
            else:
                new_mode = 'polling' if self.is_webhook_mode else 'webhook'
            
            if new_mode == 'webhook':
                # Check if webhooks are available
                webhook_status = await self._check_webhook_status(db)
                if webhook_status['active_watches'] == 0:
                    return {
                        'success': False,
                        'error': 'NO_WEBHOOKS_AVAILABLE',
                        'message': 'Cannot switch to webhook mode - no active watches'
                    }
                
                self.is_webhook_mode = True
                logger.info("🔄 [Hybrid Service] Switched to webhook mode")
                
            else:
                self.is_webhook_mode = False
                logger.info("🔄 [Hybrid Service] Switched to polling mode")
            
            return {
                'success': True,
                'mode': new_mode,
                'message': f'Successfully switched to {new_mode} mode'
            }
            
        except Exception as e:
            logger.error(f"❌ Error toggling mode: {e}")
            return {
                'success': False,
                'error': 'MODE_TOGGLE_ERROR',
                'message': f'Failed to toggle mode: {str(e)}'
            }

# Global instance
hybrid_email_service = HybridEmailService()
