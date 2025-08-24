import json
import base64
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from google.cloud import pubsub_v1

from core.config import settings
from services.gmail_service import GmailService

class GoogleCloudService:
    """Service for Google Cloud operations including Pub/Sub and Gmail API watch"""
    
    def __init__(self):
        self.project_id = settings.GOOGLE_CLOUD_PROJECT_ID
        self.topic_name = settings.GOOGLE_CLOUD_TOPIC_NAME
        self.subscription_name = settings.GOOGLE_CLOUD_SUBSCRIPTION_NAME
        
        # Initialize Gmail service for API calls
        self.gmail_service = GmailService()
        
        # Pub/Sub clients (will be initialized when needed)
        self.publisher_client = None
        self.subscriber_client = None
        
    async def _get_publisher_client(self):
        """Get or create Publisher client"""
        if self.publisher_client is None:
            try:
                # Use application default credentials
                from google.auth import default
                credentials, project = default()
                
                if project != self.project_id:
                    print(f"⚠️  Warning: Authenticated project ({project}) differs from configured project ({self.project_id})")
                
                self.publisher_client = pubsub_v1.PublisherClient(credentials=credentials)
                print(f"✅ Publisher client initialized with project: {project}")
            except Exception as e:
                print(f"⚠️  Failed to initialize Publisher client: {e}")
                print("⚠️  Make sure you're authenticated with: gcloud auth application-default login")
                return None
        return self.publisher_client
    
    async def _get_subscriber_client(self):
        """Get or create Subscriber client"""
        if self.subscriber_client is None:
            try:
                # Use application default credentials
                from google.auth import default
                credentials, project = default()
                
                if project != self.project_id:
                    print(f"⚠️  Warning: Authenticated project ({project}) differs from configured project ({self.project_id})")
                
                self.subscriber_client = pubsub_v1.SubscriberClient(credentials=credentials)
                print(f"✅ Subscriber client initialized with project: {project}")
            except Exception as e:
                print(f"⚠️  Failed to initialize Subscriber client: {e}")
                print("⚠️  Make sure you're authenticated with: gcloud auth application-default login")
                return None
        return self.subscriber_client
    
    async def create_gmail_watch(self, email_address: str, access_token: str) -> Dict[str, Any]:
        """Create a Gmail API watch for push notifications"""
        await self._ensure_topic_exists()
        await self._ensure_subscription_exists()
        
        watch_request = {
            'topicName': f'projects/{self.project_id}/topics/{self.topic_name}',
            'labelIds': ['INBOX'],  # Watch INBOX folder
            'labelFilterAction': 'include'
        }
        
        try:
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
                    watch_data = response.json()
                    print(f"✅ Gmail watch created successfully for {email_address}")
                    print(f"   History ID: {watch_data.get('historyId')}")
                    print(f"   Expiration: {watch_data.get('expiration')}")
                    return watch_data
                elif response.status_code == 403:
                    error_data = response.json()
                    error_message = error_data.get('error', {}).get('message', 'Unknown permission error')
                    
                    if 'Cloud PubSub' in error_message and 'User not authorized' in error_message:
                        print(f"❌ Permission denied: Your account doesn't have permission to publish to Pub/Sub")
                        print(f"   💡 Solution: Use a service account with proper Pub/Sub permissions")
                        print(f"   📋 Required roles: 'Pub/Sub Publisher' and 'Pub/Sub Subscriber'")
                        print(f"   🔧 Alternative: Use 'gcloud auth application-default login' with a service account")
                        return {
                            'success': False,
                            'error': 'PERMISSION_DENIED',
                            'message': 'Your account lacks Pub/Sub permissions. Please use a service account with proper roles.',
                            'details': error_message
                        }
                    else:
                        print(f"❌ Permission denied: {error_message}")
                        return {
                            'success': False,
                            'error': 'PERMISSION_DENIED',
                            'message': f'Permission denied: {error_message}'
                        }
                else:
                    print(f"❌ Failed to create Gmail watch: {response.status_code} - {response.text}")
                    return {
                        'success': False,
                        'error': 'API_ERROR',
                        'message': f'Gmail API error: {response.status_code}',
                        'details': response.text
                    }
                    
        except Exception as e:
            print(f"❌ Error creating Gmail watch: {e}")
            return {
                'success': False,
                'error': 'EXCEPTION',
                'message': f'Exception occurred: {str(e)}'
            }
    
    async def _ensure_topic_exists(self):
        """Ensure the Pub/Sub topic exists"""
        try:
            client = await self._get_publisher_client()
            if not client:
                return False
                
            topic_path = client.topic_path(self.project_id, self.topic_name)
            
            try:
                # Try to get the topic
                client.get_topic(request={"topic": topic_path})
                print(f"✅ Pub/Sub topic '{self.topic_name}' already exists")
            except Exception:
                # Topic doesn't exist, create it
                client.create_topic(request={"name": topic_path})
                print(f"✅ Created Pub/Sub topic '{self.topic_name}'")
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to ensure topic exists: {e}")
            return False
    
    async def _ensure_subscription_exists(self):
        """Ensure the Pub/Sub subscription exists"""
        try:
            client = await self._get_subscriber_client()
            if not client:
                return False
                
            topic_path = client.topic_path(self.project_id, self.topic_name)
            subscription_path = client.subscription_path(self.project_id, self.subscription_name)
            
            try:
                # Try to get the subscription
                client.get_subscription(request={"subscription": subscription_path})
                print(f"✅ Pub/Sub subscription '{self.subscription_name}' already exists")
            except Exception:
                # Subscription doesn't exist, create it
                client.create_subscription(
                    request={
                        "name": subscription_path,
                        "topic": topic_path,
                        "ack_deadline_seconds": 60,  # 1 minute to acknowledge
                        "retain_acked_messages": False
                    }
                )
                print(f"✅ Created Pub/Sub subscription '{self.subscription_name}'")
                
            return True
            
        except Exception as e:
            print(f"❌ Failed to ensure subscription exists: {e}")
            return False
    
    async def publish_test_message(self, message: str = "Test message from HR Automation") -> bool:
        """Publish a test message to verify Pub/Sub setup"""
        try:
            client = await self._get_publisher_client()
            if not client:
                return False
                
            topic_path = client.topic_path(self.project_id, self.topic_name)
            
            # Publish message
            future = client.publish(
                topic_path,
                message.encode("utf-8"),
                origin="hr-automation-system"
            )
            
            message_id = future.result()
            print(f"✅ Test message published with ID: {message_id}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to publish test message: {e}")
            return False
    
    async def stop_gmail_watch(self, email_address: str, access_token: str) -> bool:
        """Stop Gmail API watch"""
        try:
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
                    print(f"✅ Gmail watch stopped for {email_address}")
                    return True
                else:
                    print(f"❌ Failed to stop Gmail watch: {response.status_code} - {response.text}")
                    return False
                    
        except Exception as e:
            print(f"❌ Error stopping Gmail watch: {e}")
            return False

# Global instance
google_cloud_service = GoogleCloudService()
