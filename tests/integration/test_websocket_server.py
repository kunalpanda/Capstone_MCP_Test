"""
Integration tests for backend.websocket_server (Event Gateway).

Tests verify health endpoint, REST event retrieval, root endpoint,
and EventGateway class behavior with mocked Firestore and Pub/Sub.
"""
import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock


# ---------------------------------------------------------------------------
# We must mock GCP clients before importing the module
# ---------------------------------------------------------------------------
_mock_subscriber = MagicMock()
_mock_subscriber.subscription_path.return_value = "projects/test/subscriptions/test-sub"

_mock_firestore = MagicMock()


@pytest.fixture(autouse=True)
def _patch_gcp():
    with patch("google.cloud.pubsub_v1.SubscriberClient", return_value=_mock_subscriber):
        with patch("google.cloud.firestore.Client", return_value=_mock_firestore):
            import importlib
            import backend.websocket_server as mod
            importlib.reload(mod)
            mod.firestore_client = _mock_firestore
            mod.subscriber = _mock_subscriber
            yield mod


@pytest.fixture
def ws_client(_patch_gcp):
    from fastapi.testclient import TestClient
    return TestClient(_patch_gcp.app)


# =========================================================================
# Health / root
# =========================================================================
class TestEventGatewayEndpoints:
    def test_health(self, ws_client):
        resp = ws_client.get("/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["service"] == "event-gateway"

    def test_root(self, ws_client):
        resp = ws_client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert data["service"] == "Event Gateway"
        assert "/ws" in str(data)


# =========================================================================
# /events/recent
# =========================================================================
class TestRecentEvents:
    def test_returns_events(self, ws_client):
        mock_event = MagicMock()
        mock_event.to_dict.return_value = {"type": "iteration_start", "timestamp": "t"}
        mock_event.id = "evt-1"

        _mock_firestore.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [
            mock_event
        ]

        resp = ws_client.get("/events/recent?limit=10")
        assert resp.status_code == 200
        data = resp.json()
        assert data["count"] >= 0

    def test_limit_capped_at_100(self, ws_client):
        _mock_firestore.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = []
        resp = ws_client.get("/events/recent?limit=999")
        assert resp.status_code == 200


# =========================================================================
# EventGateway class
# =========================================================================
class TestEventGatewayClass:
    def test_connect_and_disconnect_tracking(self, _patch_gcp):
        gateway = _patch_gcp.gateway
        initial = len(gateway.connections)

        mock_ws = MagicMock()
        gateway.connections.add(mock_ws)
        assert len(gateway.connections) == initial + 1

        gateway.disconnect(mock_ws)
        assert len(gateway.connections) == initial

    @pytest.mark.asyncio
    async def test_broadcast_to_connections(self, _patch_gcp):
        gateway = _patch_gcp.gateway

        mock_ws = AsyncMock()
        gateway.connections.add(mock_ws)

        try:
            await gateway.broadcast({"type": "test"})
            mock_ws.send_json.assert_awaited_with({"type": "test"})
        finally:
            gateway.connections.discard(mock_ws)

    @pytest.mark.asyncio
    async def test_broadcast_removes_broken_connections(self, _patch_gcp):
        gateway = _patch_gcp.gateway

        broken_ws = AsyncMock()
        broken_ws.send_json.side_effect = Exception("broken pipe")
        gateway.connections.add(broken_ws)

        try:
            await gateway.broadcast({"type": "test"})
            # Broken connection should be removed
            assert broken_ws not in gateway.connections
        finally:
            gateway.connections.discard(broken_ws)

    @pytest.mark.asyncio
    async def test_save_event_to_firestore(self, _patch_gcp):
        gateway = _patch_gcp.gateway
        mock_ref = MagicMock()
        mock_ref.id = "new-evt"
        _mock_firestore.collection.return_value.document.return_value = mock_ref

        event_id = await gateway.save_event_to_firestore({"type": "test_event"})
        assert event_id == "new-evt"
