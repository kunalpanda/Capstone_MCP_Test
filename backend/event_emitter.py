import os
import json
from datetime import datetime
from google.cloud import pubsub_v1


class EventEmitter:

    def __init__(self):
        self.project_id = os.getenv('PROJECT_ID', 'capstone-cicd-ai')
        self.topic_name = os.getenv('PUBSUB_TOPIC_EVENTS', 'workflow-events')

        if os.getenv('PUBSUB_EMULATOR_HOST'):
            print(f"🔧 Event Emitter using Pub/Sub EMULATOR")

        self.publisher = pubsub_v1.PublisherClient()
        self.topic_path = self.publisher.topic_path(
            self.project_id, self.topic_name)

        print(f"📡 Event Emitter initialized (topic: {self.topic_name})")

    async def _publish(self, event_type: str, data: dict):
        event_data = {
            'type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            'data': data
        }

        try:
            message_bytes = json.dumps(event_data).encode('utf-8')
            future = self.publisher.publish(self.topic_path, message_bytes)
            future.result()
        except Exception as e:
            print(f"Error sending event: {e}")

    # Workflow events
    async def emit_workflow_start(self, **kwargs):
        await self._publish('workflow_start', kwargs)

    async def emit_workflow_complete(self, **kwargs):
        await self._publish('workflow_complete', kwargs)

    async def emit_error(self, **kwargs):
        await self._publish('error', kwargs)

    # Iteration events
    async def emit_iteration_start(self, iteration: int, max_iterations: int):
        await self._publish('iteration_start', {
            'iteration': iteration,
            'max_iterations': max_iterations
        })

    # Claude events
    async def emit_claude_response(self, **kwargs):
        await self._publish('claude_response', kwargs)

    # Tool events
    async def emit_tool_call(self, **kwargs):
        await self._publish('tool_call', kwargs)

    async def emit_tool_result(self, **kwargs):
        await self._publish('tool_result', kwargs)

    # State events
    async def emit_state_update(self, state_summary: dict):
        await self._publish('state_update', state_summary)

    # PR events
    async def emit_pr_summary(self, **kwargs):
        await self._publish('pr_summary', kwargs)

    # Productivity events
    async def emit_productivity_analysis(self, **kwargs):
        await self._publish('productivity_analysis', kwargs)
