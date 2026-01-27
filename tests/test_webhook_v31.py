from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.routes_webhooks import router
from app.settings import settings


def make_app():
    app = FastAPI()
    app.include_router(router)
    return app


def test_v31_ping_ignored():
    client = TestClient(make_app())
    resp = client.post("/v3.1", json={"ping": "ok"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ignored"
    assert body["reason"] in ("unsupported_payload", "unsupported_event")


def test_v31_min_payload_degraded():
    settings.evolution_base_url = "https://evo.example"
    settings.evolution_api_key = "dummy"
    settings.openai_api_key = ""

    client = TestClient(make_app())
    payload = {
        "event": "messages.upsert",
        "data": {
            "key": {"id": "abc", "remoteJid": "554799999999@s.whatsapp.net", "fromMe": False},
            "message": {"conversation": "oi"},
            "messageTimestamp": 1730000000,
        },
        "instance": "inst1",
        "server_url": "https://evo.example",
    }
    resp = client.post("/v3.1", json=payload)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] in ("degraded", "queued", "ignored")
    assert body["status"] == "degraded"
    assert body["reason"] == "missing_env"
