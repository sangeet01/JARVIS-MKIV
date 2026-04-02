"""
JARVIS-MKIII — Test Suite
Run with: pytest backend/tests/ -v  (from repo root, with PYTHONPATH=backend)
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

# ── Router tests ──────────────────────────────────────────────────────────────

from core.router import classify, TaskTier


def test_router_defaults_to_voice():
    d = classify("What time is it?")
    assert d.tier == TaskTier.VOICE


def test_router_routes_sensitive_to_local():
    d = classify("Store this in the vault and encrypt it")
    assert d.tier == TaskTier.LOCAL


def test_router_routes_reasoning():
    d = classify("Plan and architect a multi-step agent system")
    assert d.tier == TaskTier.REASONING


def test_router_single_reasoning_keyword():
    d = classify("Can you debug this code?")
    assert d.tier == TaskTier.REASONING


def test_router_local_overrides_reasoning():
    d = classify("Encrypt this sensitive agent plan in the vault")
    assert d.tier == TaskTier.LOCAL


def test_router_confidence_range():
    for prompt in ["hello", "plan a system", "encrypt vault secret"]:
        d = classify(prompt)
        assert 0.0 <= d.confidence <= 1.0


# ── Memory tests ──────────────────────────────────────────────────────────────

from memory.hindsight import HindsightMemory


def test_short_term_records_and_retrieves():
    mem = HindsightMemory()
    mem.init_session("test-session")
    mem.record("test-session", "user", "Hello JARVIS")
    mem.record("test-session", "assistant", "Hello, Agent 17.")
    ctx = mem.get_context("test-session")
    assert len(ctx) == 2
    assert ctx[0]["role"] == "user"
    assert ctx[1]["role"] == "assistant"


def test_short_term_limit_enforced():
    mem = HindsightMemory()
    mem.short._limit = 4
    for i in range(10):
        mem.record("s", "user", f"msg {i}")
    assert len(mem.get_context("s")) == 4


def test_long_term_store_and_retrieve():
    mem = HindsightMemory()
    mem.consolidate("sess-1", "Agent 17 is building JARVIS-MKIII", ["jarvis", "agent17", "build"])
    results = mem.long.retrieve("jarvis build")
    # retrieve() returns raw SQLite rows (tuples): (id, summary, keywords, source_session, timestamp)
    assert any("JARVIS" in r[1] for r in results)


def test_recall_returns_empty_when_no_match():
    mem = HindsightMemory()
    result = mem.recall("zzxyzzyabcdef")
    assert result == ""


def test_recall_returns_context_string():
    mem = HindsightMemory()
    mem.consolidate("sess-2", "Vault uses AES-256-GCM encryption", ["vault", "aes", "encryption"])
    result = mem.recall("vault encryption")
    assert "AES-256" in result or "vault" in result.lower()


# ── Sandbox tests ─────────────────────────────────────────────────────────────

from tools.sandbox import Sandbox, ToolResult


@pytest.mark.asyncio
async def test_sandbox_unknown_tool():
    s = Sandbox()
    result = await s.run("nonexistent_tool", {}, auto_confirm=True)
    assert not result.success
    # Either blocked by whitelist or rejected as unknown — both are valid refusals
    assert result.error, "Should have a non-empty error message"


@pytest.mark.asyncio
async def test_sandbox_read_file_missing():
    from tools.sandbox import sandbox
    result = await sandbox.run("read_file", {"path": "/nonexistent/path.txt"}, auto_confirm=True)
    assert not result.success


@pytest.mark.asyncio
async def test_sandbox_shell_blocked_command():
    from tools.sandbox import sandbox
    result = await sandbox.run("shell", {"command": "rm -rf /"}, auto_confirm=True)
    assert not result.success
    assert "blocked" in result.error.lower()


@pytest.mark.asyncio
async def test_sandbox_web_fetch_rejects_http():
    from tools.sandbox import sandbox
    result = await sandbox.run("web_fetch", {"url": "http://example.com"}, auto_confirm=True)
    assert not result.success
    assert "HTTPS" in result.error


def test_sandbox_tool_registration():
    s = Sandbox()
    @s.register(name="test_tool", requires_confirmation=False)
    async def my_tool(args): return ToolResult(True, "ok", "test_tool")
    tools = s.list_tools()
    assert any(t["name"] == "test_tool" for t in tools)


# ── Phase 2 tests ─────────────────────────────────────────────────────────────

def test_alert_deduplication():
    """_should_fire() must suppress the same alert type within its cooldown window."""
    from agents.proactive_agent import ProactiveAgent
    import time

    agent = ProactiveAgent()
    # Override cooldown to a large value so second call is definitely suppressed
    agent.ALERT_COOLDOWN = {"test_type": 9999}

    assert agent._should_fire("test_type") is True,  "First call must fire"
    assert agent._should_fire("test_type") is False, "Second call within cooldown must be suppressed"

    # After clearing the last-alert time, it should fire again
    agent._last_alert_times.pop("test_type")
    assert agent._should_fire("test_type") is True, "After reset, must fire again"


@pytest.mark.asyncio
async def test_tool_sandbox_whitelist():
    """Sandbox must block tool names not in ALLOWED_TOOLS."""
    from tools.sandbox import Sandbox, ToolResult
    from config.settings import ALLOWED_TOOLS

    s = Sandbox()

    # Register a harmless tool under an unauthorized name
    @s.register(name="__evil_tool__", requires_confirmation=False)
    async def evil(args): return ToolResult(True, "pwned", "__evil_tool__")

    # The tool is registered but should be blocked by the whitelist
    result = await s.run("__evil_tool__", {}, auto_confirm=True)
    assert not result.success, "Unauthorized tool must be blocked"
    assert "not in the allowed list" in result.error

    # A whitelisted tool that is also registered should pass
    @s.register(name="shell", requires_confirmation=False)
    async def fake_shell(args): return ToolResult(True, "ok", "shell")

    result2 = await s.run("shell", {}, auto_confirm=True)
    assert result2.success, "Whitelisted tool must be allowed"


def test_memory_prune():
    """prune_old_memories() must delete entries with timestamps older than retention window."""
    from datetime import datetime, timedelta
    from memory.prune import prune_old_memories

    # Build a minimal mock collection
    class MockCollection:
        def __init__(self):
            self._deleted = []
            self._entries = {
                "ids": ["id_old_1", "id_old_2"],
                "metadatas": [
                    {"timestamp": (datetime.utcnow() - timedelta(days=100)).isoformat()},
                    {"timestamp": (datetime.utcnow() - timedelta(days=95)).isoformat()},
                ],
            }

        def get(self, where, include):
            # Simulate ChromaDB $lt filter: return entries older than cutoff
            cutoff_str = where["timestamp"]["$lt"]
            cutoff = datetime.fromisoformat(cutoff_str)
            ids = [
                eid for eid, meta in zip(self._entries["ids"], self._entries["metadatas"])
                if datetime.fromisoformat(meta["timestamp"]) < cutoff
            ]
            return {"ids": ids, "metadatas": []}

        def delete(self, ids):
            self._deleted.extend(ids)

    col = MockCollection()
    deleted = prune_old_memories(col, days=90)
    assert deleted == 2, f"Expected 2 deletions, got {deleted}"
    assert "id_old_1" in col._deleted
    assert "id_old_2" in col._deleted
