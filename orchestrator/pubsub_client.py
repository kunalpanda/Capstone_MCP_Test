# orchestrator/pubsub_client.py
"""
Pub/Sub client for event-driven communication between services.
"""
from google.cloud import pubsub_v1
import json
import os
from typing import Dict, Any, Callable
from concurrent.futures import TimeoutError
import threading


class PubSubPublisher:
    """Publisher for sending messages to Pub/Sub topics."""
    
    def __init__(self, project_id: str):
        """
        Initialize publisher.
        
        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id
        
        # Check if using emulator
        if os.getenv('PUBSUB_EMULATOR_HOST'):
            print("🔧 Using Pub/Sub EMULATOR for publishing")
        else:
            print("☁️  Using Pub/Sub PRODUCTION for publishing")
        
        self.publisher = pubsub_v1.PublisherClient()
    
    async def publish(self, topic_name: str, message_data: Dict[str, Any]) -> str:
        """
        Publish message to topic.
        
        Args:
            topic_name: Topic name (e.g., "workflow-commands")
            message_data: Dictionary to publish
            
        Returns:
            Message ID
        """
        topic_path = self.publisher.topic_path(self.project_id, topic_name)
        
        # Convert dict to JSON bytes
        message_bytes = json.dumps(message_data).encode('utf-8')
        
        # Publish message
        future = self.publisher.publish(topic_path, message_bytes)
        message_id = future.result()  # Wait for publish confirmation
        
        print(f"📤 Published to {topic_name}: {message_id}")
        return message_id


class PubSubSubscriber:
    """Subscriber for consuming messages from Pub/Sub subscriptions."""
    
    def __init__(self, project_id: str):
        """
        Initialize subscriber.
        
        Args:
            project_id: GCP project ID
        """
        self.project_id = project_id
        
        # Check if using emulator
        if os.getenv('PUBSUB_EMULATOR_HOST'):
            print("🔧 Using Pub/Sub EMULATOR for subscribing")
        else:
            print("☁️  Using Pub/Sub PRODUCTION for subscribing")
        
        self.subscriber = pubsub_v1.SubscriberClient()
        self.streaming_futures = []
    
    def subscribe(
        self, 
        subscription_name: str, 
        callback: Callable[[Dict[str, Any]], None],
        max_messages: int = 10
    ):
        """
        Start listening to subscription in background.
        
        Args:
            subscription_name: Subscription name (e.g., "workflow-commands-sub")
            callback: Function to call for each message
            max_messages: Max concurrent message processing
        """
        subscription_path = self.subscriber.subscription_path(
            self.project_id, 
            subscription_name
        )
        
        def wrapped_callback(message):
            """Wrapper to handle message parsing and acking."""
            try:
                # Parse JSON message
                message_data = json.loads(message.data.decode('utf-8'))
                
                print(f"📥 Received message: {message.message_id}")
                
                # Call user callback
                callback(message_data)
                
                # Acknowledge message
                message.ack()
                print(f"✅ Acknowledged: {message.message_id}")
                
            except Exception as e:
                print(f"❌ Error processing message: {e}")
                # Negative acknowledge - message will be redelivered
                message.nack()
        
        # Configure flow control
        flow_control = pubsub_v1.types.FlowControl(max_messages=max_messages)
        
        # Start streaming pull
        streaming_pull_future = self.subscriber.subscribe(
            subscription_path,
            callback=wrapped_callback,
            flow_control=flow_control
        )
        
        self.streaming_futures.append(streaming_pull_future)
        
        print(f"👂 Listening to {subscription_name}...")
        
        return streaming_pull_future
    
    def start_in_background(self, subscription_name: str, callback: Callable):
        """
        Start subscriber in background thread.
        
        Args:
            subscription_name: Subscription name
            callback: Message handler function
        """
        def run_subscriber():
            try:
                future = self.subscribe(subscription_name, callback)
                future.result()  # Block until cancelled
            except TimeoutError:
                print(f"⏰ Subscriber timeout for {subscription_name}")
            except Exception as e:
                print(f"❌ Subscriber error: {e}")
        
        thread = threading.Thread(target=run_subscriber, daemon=True)
        thread.start()
        print(f"🚀 Started subscriber thread for {subscription_name}")
    
    def stop_all(self):
        """Stop all active subscriptions."""
        for future in self.streaming_futures:
            future.cancel()
        print("🛑 Stopped all subscribers")


# =====================================================================
# GLOBAL INSTANCES
# =====================================================================

_publisher = None
_subscriber = None

def get_publisher(project_id: str = None) -> PubSubPublisher:
    """Get or create global publisher."""
    global _publisher
    
    if _publisher is None:
        if not project_id:
            project_id = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
        _publisher = PubSubPublisher(project_id)
    
    return _publisher

def get_subscriber(project_id: str = None) -> PubSubSubscriber:
    """Get or create global subscriber."""
    global _subscriber
    
    if _subscriber is None:
        if not project_id:
            project_id = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
        _subscriber = PubSubSubscriber(project_id)
    
    return _subscriber