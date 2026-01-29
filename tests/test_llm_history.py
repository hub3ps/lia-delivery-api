from app.services.llm_agent import _history_rows_to_messages


def test_history_rows_to_messages():
    rows = [
        {"message": {"type": "human", "data": {"content": "Oi"}}},
        {"message": {"type": "ai", "data": {"content": "Olá"}}},
        {"message": "{\"type\":\"human\",\"data\":{\"content\":\"Mais\"}}"},
    ]
    msgs = _history_rows_to_messages(rows)
    assert msgs[0]["role"] == "user"
    assert msgs[0]["content"] == "Oi"
    assert msgs[1]["role"] == "assistant"
    assert msgs[1]["content"] == "Olá"
    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"] == "Mais"
