# Run this after Docker Compose starts.
import os
import time
from google.cloud import pubsub_v1

print("⏳ Waiting for Pub/Sub emulator to be ready...")
time.sleep(5)

os.environ['PUBSUB_EMULATOR_HOST'] = 'localhost:8085'
project_id = 'test-project'

publisher = pubsub_v1.PublisherClient()
subscriber = pubsub_v1.SubscriberClient()

print("\n🔧 Setting up Pub/Sub topics and subscriptions...\n")

# Create workflow-commands topic
try:
    topic_path = publisher.topic_path(project_id, 'workflow-commands')
    publisher.create_topic(request={"name": topic_path})
    print(f"✅ Created topic: workflow-commands")
except Exception as e:
    print(f"⚠️  Topic workflow-commands may already exist: {e}")

# Create workflow-commands subscription
try:
    sub_path = subscriber.subscription_path(project_id, 'workflow-commands-sub')
    topic_path = publisher.topic_path(project_id, 'workflow-commands')
    subscriber.create_subscription(
        request={
            "name": sub_path,
            "topic": topic_path,
            "ack_deadline_seconds": 600
        }
    )
    print(f"✅ Created subscription: workflow-commands-sub")
except Exception as e:
    print(f"⚠️  Subscription workflow-commands-sub may already exist: {e}")

# Create workflow-events topic
try:
    topic_path = publisher.topic_path(project_id, 'workflow-events')
    publisher.create_topic(request={"name": topic_path})
    print(f"✅ Created topic: workflow-events")
except Exception as e:
    print(f"⚠️  Topic workflow-events may already exist: {e}")

# Create workflow-events subscription
try:
    sub_path = subscriber.subscription_path(project_id, 'workflow-events-sub')
    topic_path = publisher.topic_path(project_id, 'workflow-events')
    subscriber.create_subscription(
        request={
            "name": sub_path,
            "topic": topic_path,
            "ack_deadline_seconds": 60
        }
    )
    print(f"✅ Created subscription: workflow-events-sub")
except Exception as e:
    print(f"⚠️  Subscription workflow-events-sub may already exist: {e}")

print("\n✅ Pub/Sub setup complete!\n")