import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import httpx
from google.cloud import pubsub_v1
from google.auth import default
from google.auth.exceptions import DefaultCredentialsError
from google.api_core.exceptions import AlreadyExists, NotFound

from core.config import settings

logger = logging.getLogger(__name__)

class GoogleCloudService:
    """Service for Google Cloud operations including Pub/Sub and Gmail push notifications"""

    def __init__(self):
        self.project_id = getattr(settings, 'GOOGLE_CLOUD_PROJECT_ID', None)
        self.topic_name = getattr(settings, 'GMAIL_PUBSUB_TOPIC', 'gmail-notifications')
        self.subscription_name = getattr(settings, 'GMAIL_PUBSUB_SUBSCRIPTION', 'gmail-notifications-sub')
        self.webhook_url = getattr(settings, 'GMAIL_WEBHOOK_URL', 'http://localhost:8000/api/gmail/webhook')

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
        """Create a Gmail watch request for Pub/Sub webhook notifications"""
        try:
            if not self.project_id or not self.publisher:
                logger.error("❌ Pub/Sub not properly configured")
                return {
                    'success': False,
                    'error': 'CONFIGURATION_ERROR',
                    'message': 'Google Cloud Pub/Sub not configured properly'
                }

            # Create topic path - Gmail requires this exact format
            topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
            
            logger.info(f"📡 Setting up Gmail watch for {email_address}")
            logger.info(f"📡 Using topic: {topic_path}")

            # Step 1: Ensure topic and subscription exist
            setup_result = await self._setup_pubsub_infrastructure(topic_path)
            if not setup_result['success']:
                return setup_result

            # Step 2: Grant Gmail permissions to publish to topic
            permissions_result = await self._grant_gmail_permissions(topic_path)
            if not permissions_result['success']:
                logger.warning("⚠️  Could not verify Gmail permissions, but continuing...")

            # Step 3: Create Gmail watch with proper topicName
            watch_request = {
                'topicName': topic_path,  # THIS IS REQUIRED - was commented out before
                'labelIds': ['INBOX'],    # Watch inbox messages
                'labelFilterAction': 'include'
            }

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
                    expiration_ms = result.get('expiration', '0')
                    expiration_date = datetime.fromtimestamp(int(expiration_ms) / 1000) if expiration_ms != '0' else None
                    
                    logger.info(f"✅ Gmail watch created successfully for {email_address}")
                    logger.info(f"   📅 Expires: {expiration_date}")
                    logger.info(f"   📡 Topic: {topic_path}")

                    return {
                        'success': True,
                        'message': f'Gmail watch created for {email_address}',
                        'data': result,
                        'topic': topic_path,
                        'expiration': expiration_date
                    }
                elif response.status_code == 403:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('error', {}).get('message', 'Permission denied')
                    
                    logger.error(f"❌ Gmail API 403 Error for {email_address}:")
                    logger.error(f"   Error: {error_message}")
                    logger.error(f"   Topic: {topic_path}")

                    return {
                        'success': False,
                        'error': 'PERMISSION_DENIED',
                        'message': 'Permission denied - check OAuth scopes and Pub/Sub permissions',
                        'details': error_message,
                        'solutions': [
                            'Verify Gmail OAuth scopes include gmail.readonly and gmail.modify',
                            'Grant gmail-api-push@system.gserviceaccount.com Publisher role on topic',
                            'Check that topic exists and is accessible'
                        ]
                    }
                elif response.status_code == 400:
                    error_data = response.json() if response.content else {}
                    error_message = error_data.get('error', {}).get('message', 'Bad request')

                    logger.error(f"❌ Gmail API 400 Error for {email_address}:")
                    logger.error(f"   Error: {error_message}")
                    logger.error(f"   Topic: {topic_path}")

                    return {
                        'success': False,
                        'error': 'API_ERROR',
                        'message': 'Gmail API error - Bad request',
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

    async def _setup_pubsub_infrastructure(self, topic_path: str) -> Dict[str, Any]:
        """Set up topic and subscription for Gmail webhooks"""
        try:
            # Step 1: Ensure topic exists
            await self._ensure_topic_exists(topic_path)
            
            # Step 2: Ensure subscription exists
            await self._ensure_subscription_exists(topic_path)
            
            logger.info("✅ Pub/Sub infrastructure ready")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"❌ Error setting up Pub/Sub infrastructure: {e}")
            return {
                'success': False,
                'error': 'PUBSUB_SETUP_ERROR',
                'message': 'Failed to set up Pub/Sub infrastructure',
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
                logger.info(f"📡 Topic already exists: {topic_path}")
            except NotFound:
                # Topic doesn't exist, create it
                logger.info(f"📡 Creating Pub/Sub topic: {topic_path}")
                self.publisher.create_topic(request={"name": topic_path})
                logger.info(f"✅ Topic created: {topic_path}")
            except AlreadyExists:
                logger.info(f"📡 Topic already exists: {topic_path}")

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
                logger.info(f"📡 Subscription already exists: {subscription_path}")
            except NotFound:
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
                logger.info(f"   🎯 Webhook endpoint: {self.webhook_url}")
            except AlreadyExists:
                logger.info(f"📡 Subscription already exists: {subscription_path}")

        except Exception as e:
            logger.error(f"❌ Error ensuring subscription exists: {e}")
            raise

    async def _grant_gmail_permissions(self, topic_path: str) -> Dict[str, Any]:
        """Grant Gmail service account permissions to publish to the topic"""
        try:
            # Gmail service account that needs Publisher permissions
            gmail_service_account = "gmail-api-push@system.gserviceaccount.com"
            
            logger.info(f"🔐 Granting Gmail permissions on topic: {topic_path}")
            
            # Get current IAM policy
            get_policy_request = pubsub_v1.GetIamPolicyRequest(resource=topic_path)
            policy = self.publisher.get_iam_policy(request=get_policy_request)
            
            # Check if Gmail service account already has Publisher role
            publisher_role = "roles/pubsub.publisher"
            gmail_member = f"serviceAccount:{gmail_service_account}"
            
            # Find or create the Publisher binding
            publisher_binding = None
            for binding in policy.bindings:
                if binding.role == publisher_role:
                    publisher_binding = binding
                    break
            
            if not publisher_binding:
                # Create new binding
                publisher_binding = pubsub_v1.Binding(
                    role=publisher_role,
                    members=[gmail_member]
                )
                policy.bindings.append(publisher_binding)
                logger.info(f"📝 Created new Publisher binding for Gmail service account")
            elif gmail_member not in publisher_binding.members:
                # Add Gmail service account to existing binding
                publisher_binding.members.append(gmail_member)
                logger.info(f"📝 Added Gmail service account to existing Publisher binding")
            else:
                logger.info(f"✅ Gmail service account already has Publisher permissions")
                return {'success': True}
            
            # Set the updated policy
            set_policy_request = pubsub_v1.SetIamPolicyRequest(
                resource=topic_path,
                policy=policy
            )
            self.publisher.set_iam_policy(request=set_policy_request)
            
            logger.info(f"✅ Gmail permissions granted successfully")
            return {'success': True}
            
        except Exception as e:
            logger.error(f"❌ Error granting Gmail permissions: {e}")
            return {
                'success': False,
                'error': 'PERMISSION_ERROR',
                'message': 'Failed to grant Gmail permissions',
                'details': str(e)
            }

    async def publish_test_message(self) -> bool:
        """Publish a test message to verify Pub/Sub setup"""
        try:
            if not self.publisher or not self.project_id:
                logger.error("❌ Pub/Sub not properly configured")
                return False

            topic_path = self.publisher.topic_path(self.project_id, self.topic_name)

            # Ensure topic and subscription exist
            setup_result = await self._setup_pubsub_infrastructure(topic_path)
            if not setup_result['success']:
                return False

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

    async def verify_pubsub_setup(self) -> Dict[str, Any]:
        """Verify that Pub/Sub is properly set up for Gmail webhooks"""
        try:
            if not self.project_id or not self.publisher or not self.subscriber:
                return {
                    'success': False,
                    'error': 'Pub/Sub not initialized',
                    'checks': {
                        'project_id': bool(self.project_id),
                        'publisher': bool(self.publisher),
                        'subscriber': bool(self.subscriber)
                    }
                }

            topic_path = self.publisher.topic_path(self.project_id, self.topic_name)
            subscription_path = self.subscriber.subscription_path(self.project_id, self.subscription_name)

            checks = {
                'project_configured': bool(self.project_id),
                'clients_initialized': bool(self.publisher and self.subscriber),
                'topic_exists': False,
                'subscription_exists': False,
                'gmail_permissions': False
            }

            # Check topic exists
            try:
                self.publisher.get_topic(request={"topic": topic_path})
                checks['topic_exists'] = True
                logger.info(f"✅ Topic exists: {topic_path}")
            except NotFound:
                logger.warning(f"⚠️  Topic does not exist: {topic_path}")
            except Exception as e:
                logger.error(f"❌ Error checking topic: {e}")

            # Check subscription exists
            try:
                subscription = self.subscriber.get_subscription(request={"subscription": subscription_path})
                checks['subscription_exists'] = True
                logger.info(f"✅ Subscription exists: {subscription_path}")
                logger.info(f"   🎯 Webhook endpoint: {subscription.push_config.push_endpoint}")
            except NotFound:
                logger.warning(f"⚠️  Subscription does not exist: {subscription_path}")
            except Exception as e:
                logger.error(f"❌ Error checking subscription: {e}")

            # Check Gmail permissions (basic check)
            try:
                get_policy_request = pubsub_v1.GetIamPolicyRequest(resource=topic_path)
                policy = self.publisher.get_iam_policy(request=get_policy_request)
                
                gmail_service_account = "gmail-api-push@system.gserviceaccount.com"
                publisher_role = "roles/pubsub.publisher"
                gmail_member = f"serviceAccount:{gmail_service_account}"
                
                for binding in policy.bindings:
                    if binding.role == publisher_role and gmail_member in binding.members:
                        checks['gmail_permissions'] = True
                        logger.info("✅ Gmail service account has Publisher permissions")
                        break
                
                if not checks['gmail_permissions']:
                    logger.warning("⚠️  Gmail service account may not have Publisher permissions")
                    
            except Exception as e:
                logger.error(f"❌ Error checking Gmail permissions: {e}")

            all_good = all(checks.values())
            
            return {
                'success': all_good,
                'message': 'Pub/Sub setup verification complete' if all_good else 'Pub/Sub setup has issues',
                'checks': checks,
                'topic_path': topic_path,
                'subscription_path': subscription_path,
                'webhook_url': self.webhook_url
            }

        except Exception as e:
            logger.error(f"❌ Error verifying Pub/Sub setup: {e}")
            return {
                'success': False,
                'error': 'VERIFICATION_ERROR',
                'message': 'Error during Pub/Sub verification',
                'details': str(e)
            }

    async def _setup_pubsub_infrastructure(self, topic_path: str) -> Dict[str, Any]:
        """Set up both topic and subscription"""
        try:
            # Create topic
            await self._ensure_topic_exists(topic_path)
            
            # Create subscription  
            await self._ensure_subscription_exists(topic_path)
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"❌ Error setting up Pub/Sub infrastructure: {e}")
            return {
                'success': False,
                'error': 'SETUP_ERROR',
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