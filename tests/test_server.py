"""API-shape tests for the FastAPI backend. These hit only cheap, local
endpoints (no OpenAI calls) so they run in CI without needing API keys."""
from fastapi.testclient import TestClient

from server.main import app

client = TestClient(app)


def test_health_endpoint():
    res = client.get("/health")
    assert res.status_code == 200
    body = res.json()
    assert "status" in body
    assert "kb_chunks" in body


def test_kb_count_endpoint():
    res = client.get("/kb/count")
    assert res.status_code == 200
    assert isinstance(res.json()["count"], int)


def test_run_requires_topic():
    res = client.get("/run")
    assert res.status_code == 422  # missing required `topic` query param
