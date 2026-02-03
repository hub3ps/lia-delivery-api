from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx
import psycopg


def _load_case(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def _now_ts() -> int:
    return int(datetime.now(tz=timezone.utc).timestamp())


def _build_payload(
    phone: str,
    instance: str,
    text: str,
    message_id: str,
    timestamp: int,
) -> Dict[str, Any]:
    return {
        "event": "messages.upsert",
        "instance": instance,
        "data": {
            "key": {
                "id": message_id,
                "remoteJid": f"{phone}@s.whatsapp.net",
                "fromMe": False,
                "senderPn": phone,
            },
            "message": {"conversation": text},
            "messageTimestamp": timestamp,
        },
    }


def _send_message(url: str, payload: Dict[str, Any]) -> None:
    with httpx.Client(timeout=30) as client:
        resp = client.post(url, json=payload)
        resp.raise_for_status()


def _wait_delay(delay_seconds: float) -> None:
    if delay_seconds <= 0:
        return
    time.sleep(delay_seconds)


def _print_step(index: int, total: int, text: str) -> None:
    print(f"[{index}/{total}] Enviando: {text}")


def _get_db_url(arg_value: str | None) -> str:
    return (arg_value or os.getenv("DATABASE_URL") or "").strip()


def _fetch_latest_ai_id(conn: psycopg.Connection, session_id: str) -> int | None:
    sql = """
        SELECT id
        FROM public.n8n_historico_mensagens
        WHERE session_id = %s
          AND message->>'type' = 'ai'
        ORDER BY id DESC
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (session_id,))
        row = cur.fetchone()
    return int(row[0]) if row and row[0] is not None else None


def _wait_for_ai_response(
    conn: psycopg.Connection,
    session_id: str,
    last_ai_id: int | None,
    timeout_seconds: float,
    poll_interval: float,
) -> bool:
    start = time.monotonic()
    while (time.monotonic() - start) < timeout_seconds:
        current = _fetch_latest_ai_id(conn, session_id)
        if last_ai_id is None and current is not None:
            return True
        if last_ai_id is not None and current is not None and current > last_ai_id:
            return True
        time.sleep(max(poll_interval, 0.2))
    return False


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay de conversa para /v3.1.")
    parser.add_argument("--case", required=True, help="Caminho do arquivo JSON com a conversa.")
    parser.add_argument("--url", required=True, help="URL completa do webhook (ex: https://api.seu-dominio.com/v3.1).")
    parser.add_argument("--pause", action="store_true", help="Aguardar Enter antes de cada mensagem.")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay fixo entre mensagens (segundos).")
    parser.add_argument("--phone", default=None, help="Sobrescreve o telefone do caso.")
    parser.add_argument("--instance", default=None, help="Sobrescreve a instancia do caso.")
    parser.add_argument("--wait-ai", action="store_true", help="Aguardar resposta do AI antes de enviar a proxima mensagem.")
    parser.add_argument("--db-url", default=None, help="DATABASE_URL para aguardar respostas do AI via banco.")
    parser.add_argument("--ai-timeout", type=float, default=120.0, help="Timeout para aguardar resposta do AI (segundos).")
    parser.add_argument("--ai-poll", type=float, default=1.0, help="Intervalo de polling do AI (segundos).")

    args = parser.parse_args()
    case = _load_case(args.case)

    phone = args.phone or case.get("phone") or case.get("session_id")
    if not phone:
        raise SystemExit("Telefone ausente no caso. Informe --phone ou 'phone' no JSON.")

    instance = args.instance or case.get("instance") or "test"
    messages: List[Dict[str, Any]] = case.get("messages") or []
    if not messages:
        raise SystemExit("Nenhuma mensagem encontrada no caso.")

    conn: psycopg.Connection | None = None
    if args.wait_ai:
        db_url = _get_db_url(args.db_url)
        if not db_url:
            raise SystemExit("Para usar --wait-ai, informe --db-url ou defina DATABASE_URL.")
        conn = psycopg.connect(db_url)

    total = len(messages)
    for idx, msg in enumerate(messages, start=1):
        text = (msg.get("text") or "").strip()
        if not text:
            continue

        if args.pause:
            input(f"\nPressione Enter para enviar a mensagem {idx}/{total}...")

        _print_step(idx, total, text)
        last_ai_id = _fetch_latest_ai_id(conn, phone) if conn else None
        timestamp = int(msg.get("timestamp") or _now_ts())
        message_id = msg.get("id") or f"replay-{uuid.uuid4().hex[:12]}"
        payload = _build_payload(phone, instance, text, message_id, timestamp)
        _send_message(args.url, payload)

        if conn and args.wait_ai:
            ok = _wait_for_ai_response(conn, phone, last_ai_id, args.ai_timeout, args.ai_poll)
            if not ok:
                print("Aviso: timeout aguardando resposta do AI. Continuando replay.")

        delay = float(msg.get("delay_seconds") or args.delay or 0)
        _wait_delay(delay)

    print("\nReplay finalizado.")

    if conn:
        conn.close()


if __name__ == "__main__":
    main()
