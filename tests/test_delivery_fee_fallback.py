from app.db import crud


def test_normalize_text_removes_accents():
    assert crud._normalize_text("Itajaí") == "itajai"
    assert crud._normalize_text("São  João") == "sao  joao"


def test_filter_delivery_areas_prioritizes_exact_and_partial():
    rows = [
        {"bairro": "Centro", "taxa_entrega": 5, "cidade": "Itajaí"},
        {"bairro": "Centro 1", "taxa_entrega": 6, "cidade": "Itajaí"},
        {"bairro": "São Vicente", "taxa_entrega": 7, "cidade": "Itajaí"},
    ]
    result = crud._filter_delivery_areas(rows, "Centro")
    assert result[0]["bairro"] == "Centro"
    assert len(result) == 2
