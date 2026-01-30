from app.db import crud
from app.services.order_service import OrderService


class _DummySaipos:
    def send_order(self, payload):  # pragma: no cover - not used in quote
        return {}


def test_quote_order_precifies_items(monkeypatch):
    indice = [
        {"item_type": "product", "fingerprint": "xsalada", "pdv": "100", "nome_original": "X Salada", "price": "10"},
        {"item_type": "addition", "fingerprint": "bacon", "parent_pdv": "100", "pdv": "100.1", "nome_original": "Bacon", "price": "2"},
    ]

    monkeypatch.setattr(crud, "fetch_menu_search_index", lambda db: indice)
    service = OrderService(db=object(), saipos_client=_DummySaipos())

    payload = {
        "JSON": {
            "itens": [{"nome": "X Salada", "qtd": 2, "adicionais": [{"nome": "Bacon", "qtd": 1}]}],
            "taxa_entrega": 5,
            "desconto": 0,
        }
    }

    result = service.quote_order(payload)
    data = result["JSON"]
    assert data["itens"][0]["valor_unitario"] == 10
    assert data["itens"][0]["adicionais"][0]["valor_unitario"] == 2
    assert data["subtotal"] == 24.0
    assert data["total"] == 29.0


def test_quote_order_missing_item(monkeypatch):
    monkeypatch.setattr(crud, "fetch_menu_search_index", lambda db: [])
    service = OrderService(db=object(), saipos_client=_DummySaipos())
    result = service.quote_order({"JSON": {"itens": [{"nome": "X Inexistente"}]}})
    assert result["error"] == "item_not_found"
