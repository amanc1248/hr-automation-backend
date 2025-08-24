import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from google.cloud import pubsub_v1
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError

from core.config import settings

logger = logging.getLogger(__name__)

class GoogleCloudService:
    """Service for Google Cloud operations including Pub/Sub and Gmail push notifications"""

    def __init__(self):
        self.project_id = getattr(settings, 'GOOGLE_CLOUD_PROJECT_ID', None)
        self.topic_name = getattr(settings, 'GMAIL_PUBSUB_TOPIC', 'gmail-notifications')
        self.subscription_name = getattr(settings, 'GMAIL_PUBSUB_SUBSCRIPTION', 'gmail-notifications-sub')
        self.webhook_url = getattr(settings, 'GMAIL_WEBHOOK_URL', 'http://localhost:8000/api/emails/webhook')

        # Initialize Pub/Sub client
        self.publisher = None
        self.subscriber = None
        self._initialize_clients()

    def _initialize_clients(self):
        """Initialize Google Cloud Pub/Sub clients"""
        try:
            if not self.project_id:
                logger.warning("⚠️  GOOGLE_CLOUD_PROJECT_ID not set, Pub/Sub features will be disabled")
                return

            # Try to get default credentials
            credentials, project = default()

            # Initialize Pub/Sub clients
            self.publisher = pubsub_v1.PublisherClient(credentials=credentials)
            self.subscriber = pubsub_v1.SubscriberClient(credentials=credentials)

            logger.info(f"✅ Google Cloud Pub/Sub initialized for project: {self.project_id}")

        except DefaultCredentialsError:
            logger.warning("⚠️  No Google Cloud credentials found. Run 'gcloud auth application-default login' or set GOOGLE_APPLICATION_CREDENTIALS")
        except Exception as e:
            logger.error(f"❌ Failed to initialize Google Cloud clients: {e}")

    async def create_gmail_watch(self, email_address: str, access_token: str) -> Dict[str, Any]:
        """Create a Gmail watch request for push notifications"""
        try:
            if not self.project_id:
                return {
                    'success': False,
                    'error': 'CONFIGURATION_ERROR',
                    'message': 'Google Cloud project ID not configured',
                    'details': 'Set GOOGLE_CLOUD_PROJECT_ID in environment variables'
                }

            # Ensure topic and subscription exist
            topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
            await self._ensure_topic_exists(topic_path)
            await self._ensure_subscription_exists(topic_path)

            # Create Gmail watch request
            watch_request = {
                'topicName': topic_path,
                'labelIds': ['INBOX'],  # Watch inbox messages
                'labelFilterAction': 'include'
            }

            logger.info(f"📡 Setting up Gmail watch for {email_address}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/watch',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    },
                    json=watch_request,
                    timeout=30.0
                )

                if response.status_code == 200:
                    result = response.json()
                    logger.info(f"✅ Gmail watch created successfully for {email_address}")
                    logger.info(f"   📅 Expires: {result.get('expiration', 'Unknown')}")

                    return {
                        'success': True,
                        'message': f'Gmail watch created for {email_address}',
                        'data': result
                    }
                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('error', {}).get('message', 'Permission denied')

                    return {
                        'success': False,
                        'error': 'PERMISSION_DENIED',
                        'message': 'Permission denied when creating Gmail watch',
                        'details': error_message,
                        'solution': 'Ensure the service account has proper Pub/Sub permissions'
                    }
                elif response.status_code == 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('error', {}).get('message', 'Bad request')

                    return {
                        'success': False,
                        'error': 'API_ERROR',
                        'message': 'Gmail API error',
                        'details': error_message
                    }
                else:
                    logger.error(f"❌ Failed to create Gmail watch: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': 'API_ERROR',
                        'message': f'Gmail API error: {response.status_code}',
                        'details': response.text
                    }

        except Exception as e:
            logger.error(f"❌ Error creating Gmail watch: {e}")
            return {
                'success': False,
                'error': 'INTERNAL_ERROR',
                'message': 'Internal error when creating Gmail watch',
                'details': str(e)
            }

    async def _ensure_topic_exists(self, topic_path: str):
        """Ensure the Pub/Sub topic exists, create if it doesn't"""
        try:
            if not self.publisher:
                raise Exception("Pub/Sub publisher not initialized")

            # Check if topic exists
            try:
                self.publisher.get_topic(request={"topic": topic_path})
                logger.debug(f"📡 Topic already exists: {topic_path}")
            except Exception:
                # Topic doesn't exist, create it
                logger.info(f"📡 Creating Pub/Sub topic: {topic_path}")
                self.publisher.create_topic(request={"name": topic_path})
                logger.info(f"✅ Topic created: {topic_path}")

        except Exception as e:
            logger.error(f"❌ Error ensuring topic exists: {e}")
            raise

    async def _ensure_subscription_exists(self, topic_path: str):
        """Ensure the Pub/Sub subscription exists, create if it doesn't"""
        try:
            if not self.subscriber:
                raise Exception("Pub/Sub subscriber not initialized")

            subscription_path = self.subscriber.subscription_path(
                self.project_id, self.subscription_name
            )

            # Check if subscription exists
            try:
                self.subscriber.get_subscription(request={"subscription": subscription_path})
                logger.debug(f"📡 Subscription already exists: {subscription_path}")
            except Exception:
                # Subscription doesn't exist, create it
                logger.info(f"📡 Creating Pub/Sub subscription: {subscription_path}")

                push_config = pubsub_v1.PushConfig(
                    push_endpoint=self.webhook_url
                )

                self.subscriber.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                        "push_config": push_config
                    }
                )
                logger.info(f"✅ Subscription created: {subscription_path}")

        except Exception as e:
            logger.error(f"❌ Error ensuring subscription exists: {e}")
            raise

    async def publish_test_message(self) -> bool:
        """Publish a test message to verify Pub/Sub setup"""
        try:
            if not self.publisher or not self.project_id:
                logger.error("❌ Pub/Sub not properly configured")
                return False

            topic_path = self.publisher.topic_path(self.project_id, self.topic_name)

            # Ensure topic exists
            await self._ensure_topic_exists(topic_path)

            # Create test message
            test_message = {
                'message': 'Test message from HR Automation Backend',
                'timestamp': datetime.utcnow().isoformat(),
                'type': 'test'
            }

            message_data = json.dumps(test_message).encode('utf-8')

            # Publish message
            logger.info(f"📡 Publishing test message to topic: {topic_path}")
            future = self.publisher.publish(topic_path, message_data)

            # Wait for the publish to complete
            message_id = future.result()
            logger.info(f"✅ Test message published successfully. Message ID: {message_id}")

            return True

        except Exception as e:
            logger.error(f"❌ Error publishing test message: {e}")
            return False

    async def stop_gmail_watch(self, email_address: str, access_token: str) -> Dict[str, Any]:
        """Stop Gmail watch notifications for an email address"""
        try:
            logger.info(f"🛑 Stopping Gmail watch for {email_address}")

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f'https://gmail.googleapis.com/gmail/v1/users/{email_address}/stop',
                    headers={
                        'Authorization': f'Bearer {access_token}',
                        'Content-Type': 'application/json'
                    },
                    timeout=30.0
                )

                if response.status_code == 200:
                    logger.info(f"✅ Gmail watch stopped for {email_address}")
                    return {
                        'success': True,
                        'message': f'Gmail watch stopped for {email_address}'
                    }
                else:
                    logger.error(f"❌ Failed to stop Gmail watch: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': f'Gmail API error: {response.status_code}',
                        'details': response.text
                    }

        except Exception as e:
            logger.error(f"❌ Error stopping Gmail watch: {e}")
            return {
                'success': False,
                'error': 'Internal error when stopping Gmail watch',
                'details': str(e)
            }

    def get_topic_path(self) -> Optional[str]:
        """Get the full topic path for this project"""
        if not self.project_id or not self.publisher:
            return None
        return self.publisher.topic_path(self.project_id, self.topic_name)

    def get_subscription_path(self) -> Optional[str]:
        """Get the full subscription path for this project"""
        if not self.project_id or not self.subscriber:
            return None
        return self.subscriber.subscription_path(self.project_id, self.subscription_name)

# Global instance
google_cloud_service = GoogleCloudService()
