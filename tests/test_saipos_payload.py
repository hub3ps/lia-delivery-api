from app.services.order_service import formatar_json_saipos


def test_formatar_json_saipos():
    data = {
        "telefone": "4799999999",
        "nome": "Cliente",
        "tipo_entrega": "entrega",
        "rua": "Rua A",
        "numero": "10",
        "bairro": "Centro",
        "cep": "88300-000",
        "taxa_entrega": 5,
        "desconto": 0,
        "pagamento": "dinheiro",
        "troco_para": 20,
        "total": 30,
        "itens": [
            {"pdv": "100", "descricao": "X", "quantidade": 1, "valor_unitario": 10, "observacao": "", "adicionais": []}
        ],
    }
    res = formatar_json_saipos(data)
    assert res["payment_types"][0]["code"] == "DIN"
    assert res["order_method"]["mode"] == "DELIVERY"
    assert res["customer"]["phone"].startswith("55")
