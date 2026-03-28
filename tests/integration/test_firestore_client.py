"""
Integration tests for orchestrator.firestore_client.

Tests verify workflow CRUD, event operations, context save/load,
and the deterministic generate_workflow_id function.
"""
import pytest
from unittest.mock import MagicMock, patch

from orchestrator.firestore_client import generate_workflow_id


# =========================================================================
# generate_workflow_id
# =========================================================================
class TestGenerateWorkflowId:
    def test_returns_16_char_hex(self):
        wid = generate_workflow_id("kunalpanda/test_banking_app", "main", "abc123")
        assert len(wid) == 16
        assert all(c in "0123456789abcdef" for c in wid)

    def test_deterministic(self):
        a = generate_workflow_id("o/r", "main", "sha1")
        b = generate_workflow_id("o/r", "main", "sha1")
        assert a == b

    def test_different_inputs_different_ids(self):
        a = generate_workflow_id("o/r", "main", "sha1")
        b = generate_workflow_id("o/r", "main", "sha2")
        assert a != b

    def test_branch_affects_id(self):
        a = generate_workflow_id("o/r", "main", "sha")
        b = generate_workflow_id("o/r", "dev", "sha")
        assert a != b


# =========================================================================
# FirestoreClient – workflow operations
# =========================================================================
class TestFirestoreClientWorkflows:
    @pytest.fixture
    def mock_db(self):
        db = MagicMock()
        return db

    @pytest.fixture
    def client(self, mock_db):
        with patch("orchestrator.firestore_client.firestore.Client", return_value=mock_db):
            from orchestrator.firestore_client import FirestoreClient
            fc = FirestoreClient(project_id="test-project")
            fc.db = mock_db
            return fc

    @pytest.mark.asyncio
    async def test_create_workflow(self, client, mock_db):
        await client.create_workflow("wf-1", {"repo": "o/r", "status": "running"})
        mock_db.collection.assert_called_with("workflows")
        mock_db.collection().document.assert_called_with("wf-1")
        mock_db.collection().document().set.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_workflow_found(self, client, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {"status": "running"}
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = await client.get_workflow("wf-1")
        assert result == {"status": "running"}

    @pytest.mark.asyncio
    async def test_get_workflow_not_found(self, client, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = await client.get_workflow("wf-missing")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_workflow(self, client, mock_db):
        await client.update_workflow("wf-1", {"iteration": 5})
        mock_db.collection().document().update.assert_called_once()

    @pytest.mark.asyncio
    async def test_workflow_exists_true(self, client, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        assert await client.workflow_exists("wf-1") is True

    @pytest.mark.asyncio
    async def test_workflow_exists_false(self, client, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc
        assert await client.workflow_exists("wf-missing") is False


# =========================================================================
# FirestoreClient – event operations
# =========================================================================
class TestFirestoreClientEvents:
    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def client(self, mock_db):
        with patch("orchestrator.firestore_client.firestore.Client", return_value=mock_db):
            from orchestrator.firestore_client import FirestoreClient
            fc = FirestoreClient(project_id="test-project")
            fc.db = mock_db
            return fc

    @pytest.mark.asyncio
    async def test_add_event(self, client, mock_db):
        mock_ref = MagicMock()
        mock_ref.id = "evt-abc"
        mock_db.collection.return_value.add.return_value = (None, mock_ref)

        event_id = await client.add_event({"type": "test_event"})
        assert event_id == "evt-abc"

    @pytest.mark.asyncio
    async def test_get_recent_events(self, client, mock_db):
        mock_event = MagicMock()
        mock_event.to_dict.return_value = {"type": "iteration_start"}
        mock_db.collection.return_value.order_by.return_value.limit.return_value.stream.return_value = [mock_event]

        events = await client.get_recent_events(limit=10)
        assert len(events) == 1
        assert events[0]["type"] == "iteration_start"


# =========================================================================
# FirestoreClient – context operations
# =========================================================================
class TestFirestoreClientContext:
    @pytest.fixture
    def mock_db(self):
        return MagicMock()

    @pytest.fixture
    def client(self, mock_db):
        with patch("orchestrator.firestore_client.firestore.Client", return_value=mock_db):
            from orchestrator.firestore_client import FirestoreClient
            fc = FirestoreClient(project_id="test-project")
            fc.db = mock_db
            return fc

    @pytest.mark.asyncio
    async def test_save_context(self, client, mock_db):
        messages = [{"role": "user", "content": "hi"}]
        await client.save_context("wf-1", messages)
        mock_db.collection.assert_called_with("contexts")
        mock_db.collection().document().set.assert_called_once()

    @pytest.mark.asyncio
    async def test_load_context_found(self, client, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = {
            "messages": [{"role": "user", "content": "hi"}],
            "messageCount": 1,
        }
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = await client.load_context("wf-1")
        assert len(result) == 1

    @pytest.mark.asyncio
    async def test_load_context_not_found(self, client, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = await client.load_context("wf-missing")
        assert result is None


# =========================================================================
# get_firestore_client singleton
# =========================================================================
class TestGetFirestoreClientSingleton:
    def test_returns_same_instance(self):
        import orchestrator.firestore_client as mod
        mod._firestore_client = None  # Reset

        with patch("orchestrator.firestore_client.firestore.Client"):
            c1 = mod.get_firestore_client("test-project")
            c2 = mod.get_firestore_client("test-project")
            assert c1 is c2

        mod._firestore_client = None  # Cleanup
