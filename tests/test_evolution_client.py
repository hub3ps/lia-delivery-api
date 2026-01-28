import json
import httpx

from app.services.evolution_client import EvolutionClient, normalize_phone_for_evolution


def test_normalize_phone_for_evolution():
    assert normalize_phone_for_evolution("+55 (47) 9999-9999") == "554799999999"
    assert normalize_phone_for_evolution("4799999999") == "554799999999"


def test_send_text_payload_ok():
    def handler(request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode())
        assert body["number"] == "554799999999"
        assert body["text"] == "oi"
        return httpx.Response(200, json={"ok": True})

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    evo = EvolutionClient("https://evo.example", "KEY", client=client)
    res = evo.send_text("Lia", "4799999999", "oi")
    assert res["ok"] is True


def test_send_text_raises_on_400():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(400, text="bad request")

    transport = httpx.MockTransport(handler)
    client = httpx.Client(transport=transport)
    evo = EvolutionClient("https://evo.example", "KEY", client=client)
    try:
        evo.send_text("Lia", "4799999999", "oi")
        assert False, "expected exception"
    except RuntimeError as exc:
        assert "400" in str(exc)
