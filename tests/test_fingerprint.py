from app.utils.fingerprints import gerar_fingerprint, mapear_itens


def test_gerar_fingerprint():
    assert gerar_fingerprint("X Salada") == "xsalada"
    assert gerar_fingerprint("Adicionais - Bacon", is_adicional=True) == "bacon"


def test_mapear_itens():
    indice = [
        {"item_type": "product", "fingerprint": "xsalada", "pdv": "100", "nome_original": "X Salada", "price": "10"},
        {"item_type": "addition", "fingerprint": "bacon", "parent_pdv": "100", "pdv": "100.1", "nome_original": "Bacon", "price": "2"},
    ]
    pedido = {
        "itens": [
            {"nome": "X Salada", "qtd": 2, "adicionais": [{"nome": "Bacon", "qtd": 1}]}
        ]
    }
    itens, erros = mapear_itens(pedido, indice)
    assert not erros
    assert itens[0]["pdv"] == "100"
    assert itens[0]["adicionais"][0]["pdv"] == "100.1"
