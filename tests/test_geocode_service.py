from app.services.geocode_service import GeocodeService, _normalize_text


def test_normalize_text():
    assert _normalize_text("Itajaí") == "itajai"
    assert _normalize_text("São Vicente") == "sao vicente"


def test_build_query_appends_city_state_country():
    svc = GeocodeService("key", city="Itajaí", state="SC", country="BR")
    query = svc._build_query("Avenida Campos Novos 382, São Vicente")
    assert "Itajaí" in query
    assert "SC" in query
    assert "BR" in query


def test_validate_location():
    svc = GeocodeService("key", city="Itajaí", state="SC", country="BR")
    ok, reason = svc._validate_location({"cidade": "Itajaí", "estado": "SC"})
    assert ok
    assert reason is None
    ok, reason = svc._validate_location({"cidade": "São Vicente", "estado": "SP"})
    assert not ok
    assert reason == "outside_city"
