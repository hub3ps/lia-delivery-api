from app.services.debounce_queue import is_latest_message, concat_messages


def test_is_latest_message():
    queue = [
        {"id_mensagem": "1", "mensagem": "Oi"},
        {"id_mensagem": "2", "mensagem": "Tudo bem"},
    ]
    assert is_latest_message(queue, "2") is True
    assert is_latest_message(queue, "1") is False


def test_concat_messages():
    queue = [
        {"mensagem": "Oi"},
        {"mensagem": "Tudo bem?"},
    ]
    assert concat_messages(queue) == "Oi\nTudo bem?"
