"""All tests isolate runtime artifacts and forbid outbound network connections."""

import json
import socket

import pytest

from src.config import SAMPLE_CLIENTS_DIR


@pytest.fixture(autouse=True)
def isolated_runtime(tmp_path, monkeypatch):
    import src.agents.orchestrator as orchestrator
    import src.config as config
    import src.memory.long_term as memory
    import src.observability.logger as logger

    for module in (config, orchestrator, logger):
        monkeypatch.setattr(module, "OUTPUT_DIR", tmp_path / "output")
    for module in (config, memory):
        monkeypatch.setattr(module, "STORAGE_DIR", tmp_path / "storage")

    def no_network(*args, **kwargs):
        raise AssertionError("Tests must not open network connections")

    monkeypatch.setattr(socket.socket, "connect", no_network)
    monkeypatch.setattr(socket, "create_connection", no_network)


@pytest.fixture
def sample():
    return json.loads((SAMPLE_CLIENTS_DIR / "client_101_alex_chen.json").read_text())


@pytest.fixture
def make_runner(tmp_path):
    from src.agents.orchestrator import OrchestratorAgent
    from src.memory.long_term import LongTermMemoryStore
    from src.observability.logger import AgentLogger

    def create(**kwargs):
        defaults = dict(
            output_dir=tmp_path / "output",
            memory_store=LongTermMemoryStore(tmp_path / "storage"),
            logger=AgentLogger(tmp_path / "events.jsonl", verbose=False),
        )
        defaults.update(kwargs)
        return OrchestratorAgent(**defaults)

    return create
