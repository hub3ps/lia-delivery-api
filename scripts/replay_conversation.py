from __future__ import annotations

import argparse
import json
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List

import httpx


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


def main() -> None:
    parser = argparse.ArgumentParser(description="Replay de conversa para /v3.1.")
    parser.add_argument("--case", required=True, help="Caminho do arquivo JSON com a conversa.")
    parser.add_argument("--url", required=True, help="URL completa do webhook (ex: https://api.seu-dominio.com/v3.1).")
    parser.add_argument("--pause", action="store_true", help="Aguardar Enter antes de cada mensagem.")
    parser.add_argument("--delay", type=float, default=0.0, help="Delay fixo entre mensagens (segundos).")
    parser.add_argument("--phone", default=None, help="Sobrescreve o telefone do caso.")
    parser.add_argument("--instance", default=None, help="Sobrescreve a instancia do caso.")

    args = parser.parse_args()
    case = _load_case(args.case)

    phone = args.phone or case.get("phone") or case.get("session_id")
    if not phone:
        raise SystemExit("Telefone ausente no caso. Informe --phone ou 'phone' no JSON.")

    instance = args.instance or case.get("instance") or "test"
    messages: List[Dict[str, Any]] = case.get("messages") or []
    if not messages:
        raise SystemExit("Nenhuma mensagem encontrada no caso.")

    total = len(messages)
    for idx, msg in enumerate(messages, start=1):
        text = (msg.get("text") or "").strip()
        if not text:
            continue

        if args.pause:
            input(f"\nPressione Enter para enviar a mensagem {idx}/{total}...")

        _print_step(idx, total, text)
        timestamp = int(msg.get("timestamp") or _now_ts())
        message_id = msg.get("id") or f"replay-{uuid.uuid4().hex[:12]}"
        payload = _build_payload(phone, instance, text, message_id, timestamp)
        _send_message(args.url, payload)

        delay = float(msg.get("delay_seconds") or args.delay or 0)
        _wait_delay(delay)

    print("\nReplay finalizado.")


if __name__ == "__main__":
    main()
