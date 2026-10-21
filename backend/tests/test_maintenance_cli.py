from __future__ import annotations

import sys

from app import maintenance_cli as cli
from app import maintenance_control as barrier


class FakeRedis:
    def __init__(self, *, owner="maintenance-test", active=0):
        self.values = {barrier.MAINTENANCE_KEY: f"{owner}:active"}
        self.active = active
        self.closed = False

    def get(self, key):
        return self.values.get(key)

    def hlen(self, key):
        return self.active

    def hgetall(self, key):
        return {}

    def close(self):
        self.closed = True


def test_cli_maintenance_begin_uses_explicit_operation(monkeypatch, capsys):
    monkeypatch.setenv(barrier.MAINTENANCE_ENABLED_ENV, "true")
    client = FakeRedis()
    started = []
    monkeypatch.setattr(cli, "begin_maintenance", lambda operation: started.append(operation) or client)
    monkeypatch.setattr(sys, "argv", ["maintenance", "maintenance-begin", "--operation", "maintenance-test"])

    assert cli.main() == 0
    assert started == ["maintenance-test"]
    assert '"state": "maintenance_active"' in capsys.readouterr().out


def test_cli_refuses_maintenance_finish_with_persisted_work(monkeypatch, capsys):
    monkeypatch.setenv(barrier.MAINTENANCE_ENABLED_ENV, "true")
    client = FakeRedis()
    finished = []
    monkeypatch.setattr(cli, "redis_client", lambda: client)
    monkeypatch.setattr(cli, "_persisted_active_queues", lambda: {"raw": 1})
    monkeypatch.setattr(cli, "finish_maintenance", lambda *args, **kwargs: finished.append(True))
    monkeypatch.setattr(sys, "argv", ["maintenance", "maintenance-finish", "--operation", "maintenance-test"])

    assert cli.main() == 2
    assert finished == []
    assert '"state": "persisted_work_active"' in capsys.readouterr().out
    assert client.closed


def test_cli_finishes_only_after_redis_and_database_are_clear(monkeypatch, capsys):
    monkeypatch.setenv(barrier.MAINTENANCE_ENABLED_ENV, "true")
    client = FakeRedis()
    finished = []
    monkeypatch.setattr(cli, "redis_client", lambda: client)
    monkeypatch.setattr(cli, "_persisted_active_queues", dict)
    monkeypatch.setattr(cli, "finish_maintenance", lambda operation, client: finished.append(operation))
    monkeypatch.setattr(sys, "argv", ["maintenance", "maintenance-finish", "--operation", "maintenance-test"])

    assert cli.main() == 0
    assert finished == ["maintenance-test"]
    assert '"state": "maintenance_closed"' in capsys.readouterr().out
    assert client.closed
