"""Tests for Recall (memory) module (Milestone 4)."""

import socket
import tempfile
from pathlib import Path
import pytest

from nexora import App
from nexora.memory import MemoryItem, MemoryPlugin, MemoryStore, Recall
from nexora.storage import LocalStore


@pytest.fixture
def temp_store(tmp_path):
    local_store = LocalStore(name="test_mem", base_dir=tmp_path)
    return MemoryStore(local_store=local_store)


class TestMemoryStore:
    def test_remember_and_get(self, temp_store):
        item = temp_store.remember("user_pref", "dark_mode", tags=["ui", "theme"])
        assert item.id == "user_pref"
        assert item.content == "user_pref"
        assert item.value == "dark_mode"
        assert "ui" in item.tags

        retrieved = temp_store.get("user_pref")
        assert retrieved is not None
        assert retrieved.id == "user_pref"
        assert retrieved.value == "dark_mode"

    def test_secret_redaction_dict_and_content(self, temp_store):
        # 1. Dict value with sensitive keys
        data = {
            "username": "alice",
            "password": "supersecretpassword123",
            "api_key": "sk-1234567890",
            "metadata": {"nested_token": "bearer xyz"},
        }
        item = temp_store.remember("auth_creds", data)
        assert item.value["username"] == "alice"
        assert item.value["password"] == "***REDACTED***"
        assert item.value["api_key"] == "***REDACTED***"
        assert item.value["metadata"]["nested_token"] == "***REDACTED***"

        # 2. String content with password pattern
        item2 = temp_store.remember("Database config: password=mysecretpass, port=5432")
        assert "password: ***REDACTED***" in item2.content
        assert "port=5432" in item2.content

    def test_search_by_query_and_tags(self, temp_store):
        temp_store.remember("python_guide", "Guide to writing clean Python", tags=["python", "coding"])
        temp_store.remember("rust_guide", "Guide to Rust memory safety", tags=["rust", "systems"])
        temp_store.remember("database_schema", "PostgreSQL tables and indices", tags=["db", "sql"])

        # Search by keyword
        res = temp_store.search("Python")
        assert len(res) >= 1
        assert res[0].id == "python_guide"

        # Search with tag filter
        res_tag = temp_store.search("guide", tags=["rust"])
        assert len(res_tag) == 1
        assert res_tag[0].id == "rust_guide"

    def test_ask_local_retrieval(self, temp_store):
        temp_store.remember("server_port", 8080)
        temp_store.remember("database_host", "localhost:5432")

        ans = temp_store.ask("What is the server port?")
        assert ans is not None
        assert "8080" in ans

        ans_db = temp_store.ask("Where is the database host located?")
        assert ans_db is not None
        assert "localhost:5432" in ans_db

        ans_none = temp_store.ask("quantum mechanics equations")
        assert ans_none is None

    def test_forget(self, temp_store):
        temp_store.remember("temp_note", "to be deleted")
        assert temp_store.get("temp_note") is not None

        deleted = temp_store.forget("temp_note")
        assert deleted is True
        assert temp_store.get("temp_note") is None

        # Deleting non-existent returns False
        assert temp_store.forget("non_existent") is False

    def test_timeline(self, temp_store):
        temp_store.remember("step1", "start", now=100.0)
        temp_store.remember("step2", "process", now=200.0)
        temp_store.remember("step3", "finish", now=300.0)

        tl = temp_store.timeline()
        assert [m.id for m in tl] == ["step1", "step2", "step3"]

        tl_rev = temp_store.timeline(reverse=True)
        assert [m.id for m in tl_rev] == ["step3", "step2", "step1"]

        tl_limit = temp_store.timeline(limit=2)
        assert len(tl_limit) == 2

    def test_clear(self, temp_store):
        temp_store.remember("k1", "v1")
        temp_store.remember("k2", "v2")
        temp_store.clear()
        assert len(temp_store.timeline()) == 0

    def test_strictly_local_no_network_calls(self, temp_store, monkeypatch):
        """Verify that no socket connections are opened during memory operations."""
        def mock_socket_connect(*args, **kwargs):
            raise AssertionError("Network connection attempted in local memory store!")

        monkeypatch.setattr(socket.socket, "connect", mock_socket_connect)

        temp_store.remember("local_key", "local_value")
        temp_store.search("local")
        temp_store.ask("What is local?")
        temp_store.timeline()
        temp_store.forget("local_key")


class TestMemoryPlugin:
    def test_plugin_properties_and_alias(self):
        app = App(features=["memory"])
        assert app.memory is not None
        assert app.recall is not None
        assert isinstance(app.memory, MemoryPlugin)
        assert isinstance(app.memory, Recall)
        assert app.memory.name == "memory"
        assert app.memory.requires_extra is None
        assert app.memory.milestone == "M4"

    def test_remember_and_events(self):
        app = App(features=["memory"])
        events = []
        app.bus.on("memory.*", lambda e: events.append(e))

        item = app.memory.remember("cached_user", {"name": "Bob", "secret": "123"})
        assert item.value["secret"] == "***REDACTED***"

        assert any(e.type == "memory.remembered" and e.payload["id"] == "cached_user" for e in events)

        app.memory.forget("cached_user")
        assert any(e.type == "memory.forgotten" and e.payload["id"] == "cached_user" for e in events)

    def test_event_driven_memory_commands(self):
        app = App(features=["memory"])
        app.bus.emit("memory.remember", payload={"key": "cmd_note", "value": "stored via event"})

        item = app.memory.get("cmd_note")
        assert item is not None
        assert item.value == "stored via event"

        app.bus.emit("memory.forget", payload={"key": "cmd_note"})
        assert app.memory.get("cmd_note") is None

    def test_coexistence_all_four_features(self):
        """Test GhostUI, CodeWorld, MoodUI, and Recall running together."""
        app = App(features=["ghost", "world", "adaptive", "memory"])
        assert app.ghost is not None
        assert app.world is not None
        assert app.adaptive is not None
        assert app.memory is not None

        app.adaptive.opt_in()

        @app.task
        def integrated_task():
            app.memory.remember("task_checkpoint", "task started")
            app.world.create("node", entity_id="task_node", x=10, y=10)
            app.ghost.metric("progress_step", 1)

        app.run()

        assert app.memory.get("task_checkpoint") is not None
        assert app.world.get("task_node") is not None
        assert "integrated_task" in app.ghost.task_records
