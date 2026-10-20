import json

import main
from sqlalchemy.exc import OperationalError


class UnreachableDatabase:
    def connect(self):
        raise OperationalError("SELECT 1", {}, OSError("Network is unreachable"))


def test_health_returns_service_unavailable_when_database_is_down(monkeypatch):
    monkeypatch.setattr(main, "engine", UnreachableDatabase())

    response = main.health_check()

    assert response.status_code == 503
    payload = json.loads(response.body)
    assert payload["status"] == "degraded"
    assert payload["db"] == "unreachable"
