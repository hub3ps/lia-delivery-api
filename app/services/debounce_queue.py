from __future__ import annotations

import time
from typing import Any, Dict, List

from app.db import crud


def is_latest_message(queue: List[Dict[str, Any]], current_message_id: str) -> bool:
    if not queue:
        return False
    last = queue[-1]
    return last.get("id_mensagem") == current_message_id


def concat_messages(queue: List[Dict[str, Any]]) -> str:
    mensagens = [m.get("mensagem") or "" for m in queue]
    return "\n".join(mensagens).strip()


def process_queue(
    db,
    telefone: str,
    current_message_id: str,
    wait_seconds: int,
) -> List[Dict[str, Any]]:
    time.sleep(max(wait_seconds, 0))
    queue = crud.get_pending_messages(db, telefone)
    if not is_latest_message(queue, current_message_id):
        return []
    return queue
