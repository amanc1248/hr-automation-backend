"""
Gmail Watch Manager Service
Integrates with existing GoogleCloudService to manage Gmail watches
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, select

from .google_cloud_service import google_cloud_service
from models.gmail_webhook import GmailWatch
from models.user import Profile
from core.webhook_config import get_webhook_config

logger = logging.getLogger(__name__)

class GmailWatchManager:
    """Manages Gmail watches for webhook notifications"""
    
    def __init__(self):
        self.config = get_webhook_config()
    
    async def setup_watch_for_user(self, db: AsyncSession, user: Profile, access_token: str) -> Dict[str, Any]:
        """
        Set up Gmail watch for a user after OAuth authorization
        """
        try:
            logger.info(f"🔧 Setting up Gmail watch for user: {user.email}")
            
            # Check if user already has an active watch
            existing_watch = await self._get_active_watch(db, user.id)
            if existing_watch:
                logger.info(f"📡 User {user.email} already has active watch: {existing_watch.channel_id}")
                return {
                    'success': True,
                    'message': f'Gmail watch already active for {user.email}',
                    'watch_id': str(existing_watch.id)
                }
            
            # Create Gmail watch using existing service
            watch_result = await google_cloud_service.create_gmail_watch(
                email_address=user.email,
                access_token=access_token
            )
            
            if not watch_result['success']:
                logger.error(f"❌ Failed to create Gmail watch for {user.email}: {watch_result['error']}")
                return watch_result
            
            # Extract watch details from Gmail API response
            watch_data = watch_result['data']
            history_id = watch_data.get('historyId', '0')
            expiration = datetime.utcnow() + timedelta(days=6)  # Renew before 7-day limit
            
            # Store watch details in database
            gmail_watch = GmailWatch(
                user_id=user.id,
                user_email=user.email,
                channel_id=f"hr-automation-{user.email}-{datetime.utcnow().strftime('%Y%m%d')}",
                resource_id=watch_data.get('resourceId', ''),
                history_id=history_id,
                expiration=expiration,
                is_active=True
            )
            
            db.add(gmail_watch)
            await db.commit()
            
            logger.info(f"✅ Gmail watch setup successful for {user.email}")
            logger.info(f"   📅 Expires: {expiration}")
            logger.info(f"   🆔 Watch ID: {gmail_watch.id}")
            
            return {
                'success': True,
                'message': f'Gmail watch activated for {user.email}',
                'watch_id': str(gmail_watch.id),
                'expires_at': expiration.isoformat()
            }
            
        except Exception as e:
            logger.error(f"❌ Error setting up Gmail watch for {user.email}: {str(e)}")
            await db.rollback()
            return {
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': f'Failed to setup Gmail watch: {str(e)}'
            }
    
    async def renew_expiring_watches(self, db: AsyncSession) -> Dict[str, Any]:
        """
        Renew Gmail watches that are expiring soon
        Should be called daily to keep watches active
        """
        try:
            logger.info("🔄 Starting Gmail watch renewal process...")
            
            # Find watches expiring in next 24 hours
            expiring_soon = datetime.utcnow() + timedelta(hours=24)
            expiring_watches = await self._get_expiring_watches(db, expiring_soon)
            
            if not expiring_watches:
                logger.info("✅ No watches need renewal")
                return {
                    'success': True,
                    'message': 'No watches need renewal',
                    'renewed_count': 0
                }
            
            logger.info(f"📡 Found {len(expiring_watches)} watches expiring soon")
            
            renewed_count = 0
            failed_count = 0
            
            for watch in expiring_watches:
                try:
                    # Get user's current access token
                    user = await self._get_user_by_id(db, watch.user_id)
                    if not user:
                        logger.warning(f"⚠️  User not found for watch {watch.id}")
                        continue
                    
                    # Get fresh access token (you'll need to implement this)
                    access_token = await self._get_user_access_token(db, user.id)
                    if not access_token:
                        logger.warning(f"⚠️  No valid access token for user {user.email}")
                        continue
                    
                    # Stop old watch
                    stop_result = await google_cloud_service.stop_gmail_watch(
                        email_address=user.email,
                        access_token=access_token
                    )
                    
                    if stop_result['success']:
                        logger.info(f"🛑 Stopped old watch for {user.email}")
                    else:
                        logger.warning(f"⚠️  Failed to stop old watch for {user.email}: {stop_result['error']}")
                    
                    # Create new watch
                    new_watch_result = await self.setup_watch_for_user(db, user, access_token)
                    
                    if new_watch_result['success']:
                        # Deactivate old watch record
                        watch.is_active = False
                        await db.commit()
                        
                        renewed_count += 1
                        logger.info(f"✅ Renewed Gmail watch for {user.email}")
                    else:
                        failed_count += 1
                        logger.error(f"❌ Failed to renew watch for {user.email}: {new_watch_result['error']}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Error renewing watch {watch.id}: {str(e)}")
                    continue
            
            logger.info(f"🔄 Watch renewal completed: {renewed_count} renewed, {failed_count} failed")
            
            return {
                'success': True,
                'message': f'Watch renewal completed: {renewed_count} renewed, {failed_count} failed',
                'renewed_count': renewed_count,
                'failed_count': failed_count
            }
            
        except Exception as e:
            logger.error(f"❌ Error in watch renewal process: {str(e)}")
            return {
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': f'Watch renewal failed: {str(e)}'
            }
    
    async def stop_watch_for_user(self, db: AsyncSession, user_id: str) -> Dict[str, Any]:
        """
        Stop Gmail watch for a specific user
        """
        try:
            watch = await self._get_active_watch(db, user_id)
            if not watch:
                return {
                    'success': False,
                    'error': 'NOT_FOUND',
                    'message': 'No active watch found for user'
                }
            
            # Stop watch via Gmail API
            user = await self._get_user_by_id(db, user_id)
            access_token = await self._get_user_access_token(db, user_id)
            
            if access_token:
                stop_result = await google_cloud_service.stop_gmail_watch(
                    email_address=user.email,
                    access_token=access_token
                )
                
                if not stop_result['success']:
                    logger.warning(f"⚠️  Failed to stop Gmail API watch: {stop_result['error']}")
            
            # Deactivate in database
            watch.is_active = False
            await db.commit()
            
            logger.info(f"✅ Gmail watch stopped for user {user.email}")
            
            return {
                'success': True,
                'message': f'Gmail watch stopped for {user.email}'
            }
            
        except Exception as e:
            logger.error(f"❌ Error stopping watch for user {user_id}: {str(e)}")
            return {
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': f'Failed to stop watch: {str(e)}'
            }
    
    async def get_user_watch_status(self, db: AsyncSession, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current watch status for a user
        """
        try:
            watch = await self._get_active_watch(db, user_id)
            if not watch:
                return None
            
            return {
                'watch_id': str(watch.id),
                'channel_id': watch.channel_id,
                'is_active': watch.is_active,
                'expires_at': watch.expiration.isoformat(),
                'last_notification': watch.last_notification.isoformat() if watch.last_notification else None
            }
            
        except Exception as e:
            logger.error(f"❌ Error getting watch status for user {user_id}: {str(e)}")
            return None
    
    # Helper methods
    async def _get_active_watch(self, db: AsyncSession, user_id: str) -> Optional[GmailWatch]:
        """Get active watch for a user"""
        result = await db.execute(
            select(GmailWatch).where(
                and_(
                    GmailWatch.user_id == user_id,
                    GmailWatch.is_active == True
                )
            )
        )
        return result.scalar_one_or_none()
    
    async def _get_expiring_watches(self, db: AsyncSession, before_time: datetime) -> List[GmailWatch]:
        """Get watches expiring before a specific time"""
        result = await db.execute(
            select(GmailWatch).where(
                and_(
                    GmailWatch.expiration <= before_time,
                    GmailWatch.is_active == True
                )
            )
        )
        return result.scalars().all()
    
    async def _get_user_by_id(self, db: AsyncSession, user_id: str) -> Optional[Profile]:
        """Get user profile by ID"""
        result = await db.execute(
            select(Profile).where(Profile.id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def _get_user_access_token(self, db: AsyncSession, user_id: str) -> Optional[str]:
        """
        Get user's current Gmail access token from gmail_configs table
        """
        try:
            from sqlalchemy import text
            
            # Get Gmail config for this user
            result = await db.execute(
                text("""
                    SELECT access_token, token_expires_at, refresh_token 
                    FROM gmail_configs 
                    WHERE user_id = :user_id AND is_active = true
                """),
                {'user_id': user_id}
            )
            
            config_row = result.fetchone()
            if not config_row:
                logger.warning(f"⚠️  No Gmail config found for user {user_id}")
                return None
            
            config = dict(config_row._mapping)
            encrypted_access_token = config['access_token']
            expires_at = config['token_expires_at']
            encrypted_refresh_token = config['refresh_token']
            
            # Decrypt tokens
            from .gmail_service import gmail_service
            access_token = gmail_service._decrypt_token(encrypted_access_token)
            refresh_token = gmail_service._decrypt_token(encrypted_refresh_token) if encrypted_refresh_token else None
            
            # Check if token is expired
            if expires_at and datetime.utcnow() >= expires_at:
                logger.info(f"🔄 Access token expired for user {user_id}, refreshing...")
                
                if refresh_token:
                    # Refresh the token
                    from .gmail_service import gmail_service
                    try:
                        new_tokens = await gmail_service.refresh_access_token(refresh_token)
                        
                        # Update the database with new tokens
                        await self._update_tokens_in_db(db, user_id, new_tokens)
                        
                        return new_tokens['access_token']
                    except Exception as e:
                        logger.error(f"❌ Failed to refresh token for user {user_id}: {str(e)}")
                        return None
                else:
                    logger.warning(f"⚠️  No refresh token available for user {user_id}")
                    return None
            
            # Token is still valid
            return access_token
            
        except Exception as e:
            logger.error(f"❌ Error getting access token for user {user_id}: {str(e)}")
            return None
    
    async def _update_tokens_in_db(self, db: AsyncSession, user_id: str, new_tokens: Dict[str, Any]):
        """Update tokens in database after refresh"""
        try:
            from sqlalchemy import text
            from .gmail_service import gmail_service
            
            # Encrypt new tokens
            encrypted_access_token = gmail_service._encrypt_token(new_tokens['access_token'])
            encrypted_refresh_token = gmail_service._encrypt_token(new_tokens['refresh_token']) if new_tokens.get('refresh_token') else None
            
            # Update tokens in database
            await db.execute(
                text("""
                    UPDATE gmail_configs 
                    SET access_token = :access_token, 
                        refresh_token = :refresh_token,
                        token_expires_at = :expires_at,
                        updated_at = NOW()
                    WHERE user_id = :user_id AND is_active = true
                """),
                {
                    'access_token': encrypted_access_token,
                    'refresh_token': encrypted_refresh_token,
                    'expires_at': new_tokens['expires_at'],
                    'user_id': user_id
                }
            )
            
            await db.commit()
            logger.info(f"✅ Updated tokens for user {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Error updating tokens for user {user_id}: {str(e)}")
            await db.rollback()
            raise

# Global instance
gmail_watch_manager = GmailWatchManager()
