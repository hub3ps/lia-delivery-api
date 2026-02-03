from __future__ import annotations

import argparse
import json
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

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


def _normalize_db_url(value: str) -> str:
    if not value:
        return value
    if value.startswith("postgresql+psycopg://"):
        return "postgresql://" + value.split("postgresql+psycopg://", 1)[1]
    return value


def _get_db_url(arg_value: str | None) -> str:
    raw = (arg_value or os.getenv("DATABASE_URL") or "").strip()
    return _normalize_db_url(raw)


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


def _fetch_cart(conn: psycopg.Connection, session_id: str) -> Dict[str, Any]:
    sql = """
        SELECT cart_json::text
        FROM public.active_sessions
        WHERE session_id = %s
        ORDER BY updated_at DESC
        LIMIT 1
    """
    with conn.cursor() as cur:
        cur.execute(sql, (session_id,))
        row = cur.fetchone()
    if not row or not row[0]:
        return {}
    try:
        return json.loads(row[0])
    except Exception:
        return {}


def _normalize_text(value: str) -> str:
    return (value or "").strip().lower()


def _address_has_value(addr: Any, needle: str) -> bool:
    if not needle:
        return False
    needle_norm = _normalize_text(needle)
    if isinstance(addr, dict):
        for key in ("rua", "numero", "bairro", "cidade", "estado", "cep", "complemento"):
            if needle_norm and needle_norm in _normalize_text(str(addr.get(key) or "")):
                return True
        return False
    if isinstance(addr, str):
        return needle_norm in _normalize_text(addr)
    return False


def _smart_next_message(cart: Dict[str, Any], scenario: Dict[str, Any], state: Dict[str, bool]) -> Optional[str]:
    pendencias = cart.get("pendencias") if isinstance(cart.get("pendencias"), list) else []
    itens = cart.get("itens") if isinstance(cart.get("itens"), list) else []
    tipo_entrega = cart.get("tipo_entrega")
    endereco = cart.get("endereco")
    pagamento = cart.get("pagamento")

    confirm_pending = scenario.get("confirm_pending") or "Confirma"
    confirm_items = scenario.get("confirm_items") or "Confirma"
    confirm_address = scenario.get("confirm_address") or "Sim"

    delivery = scenario.get("delivery") if isinstance(scenario.get("delivery"), dict) else {}
    tipo_desejado = delivery.get("tipo") or delivery.get("tipo_entrega")
    bairro = delivery.get("bairro") or ""
    complemento = delivery.get("complemento") or ""
    endereco_line = delivery.get("endereco") or ""

    payment = scenario.get("payment") if isinstance(scenario.get("payment"), dict) else {}
    metodo_pagamento = payment.get("metodo") or payment.get("pagamento")
    troco_para = payment.get("troco_para")
    pix_texto = payment.get("pix_texto")

    if pendencias and not state.get("sent_confirm_pending"):
        state["sent_confirm_pending"] = True
        return confirm_pending

    if itens and not pendencias and not state.get("sent_confirm_items") and not tipo_entrega:
        state["sent_confirm_items"] = True
        return confirm_items

    if not tipo_entrega and tipo_desejado:
        state["sent_tipo_entrega"] = True
        return tipo_desejado

    if (tipo_entrega or tipo_desejado) == "entrega":
        if not endereco and endereco_line and not state.get("sent_endereco"):
            state["sent_endereco"] = True
            return endereco_line

        if bairro and not _address_has_value(endereco, bairro) and not state.get("sent_bairro"):
            state["sent_bairro"] = True
            return bairro

        if complemento and not _address_has_value(endereco, complemento) and not state.get("sent_complemento"):
            state["sent_complemento"] = True
            return complemento

        if endereco and not state.get("sent_confirm_address"):
            state["sent_confirm_address"] = True
            return confirm_address

    if not pagamento and metodo_pagamento:
        state["sent_pagamento"] = True
        return metodo_pagamento

    if pagamento == "dinheiro" and troco_para and not state.get("sent_troco"):
        state["sent_troco"] = True
        return f"Troco para {troco_para}"

    if pagamento == "pix" and pix_texto and not state.get("sent_pix"):
        state["sent_pix"] = True
        return pix_texto

    return None


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
    parser.add_argument("--smart", action="store_true", help="Replay inteligente baseado no estado do carrinho.")
    parser.add_argument("--max-steps", type=int, default=20, help="Maximo de passos no modo --smart.")

    args = parser.parse_args()
    case = _load_case(args.case)

    phone = args.phone or case.get("phone") or case.get("session_id")
    if not phone:
        raise SystemExit("Telefone ausente no caso. Informe --phone ou 'phone' no JSON.")

    instance = args.instance or case.get("instance") or "test"
    messages: List[Dict[str, Any]] = case.get("messages") or []
    if not messages and not args.smart:
        raise SystemExit("Nenhuma mensagem encontrada no caso.")

    conn: psycopg.Connection | None = None
    if args.wait_ai or args.smart:
        db_url = _get_db_url(args.db_url)
        if not db_url:
            raise SystemExit("Para usar --wait-ai, informe --db-url ou defina DATABASE_URL.")
        conn = psycopg.connect(db_url)

    if args.smart:
        scenario = case if isinstance(case, dict) else {}
        initial_message = scenario.get("initial_message")
        if not initial_message and messages:
            initial_message = (messages[0].get("text") or "").strip()
        if not initial_message:
            raise SystemExit("Modo --smart requer 'initial_message' no caso.")

        _print_step(1, 1, initial_message)
        last_ai_id = _fetch_latest_ai_id(conn, phone) if conn else None
        payload = _build_payload(phone, instance, initial_message, f"replay-{uuid.uuid4().hex[:12]}", _now_ts())
        _send_message(args.url, payload)
        if conn:
            _wait_for_ai_response(conn, phone, last_ai_id, args.ai_timeout, args.ai_poll)

        state: Dict[str, bool] = {}
        for step in range(args.max_steps):
            cart = _fetch_cart(conn, phone) if conn else {}
            next_message = _smart_next_message(cart, scenario, state)
            if not next_message:
                break

            _print_step(step + 2, args.max_steps + 1, next_message)
            last_ai_id = _fetch_latest_ai_id(conn, phone) if conn else None
            payload = _build_payload(phone, instance, next_message, f"replay-{uuid.uuid4().hex[:12]}", _now_ts())
            _send_message(args.url, payload)
            if conn:
                _wait_for_ai_response(conn, phone, last_ai_id, args.ai_timeout, args.ai_poll)

        print("\nReplay finalizado.")
        if conn:
            conn.close()
        return

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
