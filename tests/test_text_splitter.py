from app.utils.text_splitter import split_messages


def test_split_messages():
    text = "Linha 1\n\nLinha 2\n\n\nLinha 3"
    parts = split_messages(text)
    assert parts == ["Linha 1", "Linha 2", "Linha 3"]


def test_split_empty():
    assert split_messages("") == [""]
