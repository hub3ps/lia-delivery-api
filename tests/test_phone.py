from app.utils.phone import normalize_phone, extract_phone_from_jid, is_group_jid


def test_normalize_phone():
    assert normalize_phone("47 9648-9767") == "554796489767"
    assert normalize_phone("554799999999") == "554799999999"


def test_extract_phone_from_jid():
    assert extract_phone_from_jid("554799999999@s.whatsapp.net") == "554799999999"


def test_group_jid():
    assert is_group_jid("123@g.us") is True
    assert is_group_jid("123@s.whatsapp.net") is False
