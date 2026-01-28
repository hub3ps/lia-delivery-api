from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Request

from app.db.session import get_db
from app.db import crud
from app.services.debounce_queue import concat_messages, process_queue
from app.services.evolution_client import EvolutionClient
from app.services.geocode_service import GeocodeService
from app.services.llm_agent import LLMAgent
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.saipos_client import SaiposClient
from app.services.status_service import StatusService
from app.settings import settings
import logging
from app.utils.phone import extract_phone_from_jid, is_group_jid, normalize_phone
from app.utils.text_splitter import split_messages
from app.utils.time import format_horario

router = APIRouter()

ALLOWED_TYPES = {"text", "audio", "image", "image/webp", "documentMessage"}
SUPPORTED_EVENTS = {"messages.upsert"}

logger = logging.getLogger(__name__)


def _get_body(payload: Dict[str, Any]) -> Dict[str, Any]:
    if not isinstance(payload, dict):
        return {}
    return payload.get("body") if "body" in payload and isinstance(payload.get("body"), dict) else payload


def _extract_event(payload: Dict[str, Any]) -> str | None:
    body = _get_body(payload)
    return body.get("event") or payload.get("event")


def _is_supported_payload(payload: Dict[str, Any]) -> tuple[bool, str | None]:
    if not isinstance(payload, dict):
        return False, "unsupported_payload"
    event = _extract_event(payload)
    if event and event not in SUPPORTED_EVENTS:
        return False, "unsupported_event"
    body = _get_body(payload)
    data = body.get("data") if isinstance(body, dict) else None
    if not isinstance(data, dict):
        return False, "unsupported_payload"
    key = data.get("key")
    message = data.get("message")
    if not isinstance(key, dict) or not isinstance(message, dict):
        return False, "unsupported_payload"
    if not (key.get("id") or key.get("remoteJid") or key.get("senderPn") or key.get("senderLid")):
        return False, "unsupported_payload"
    return True, None


def _missing_envs() -> list[str]:
    missing = []
    if not settings.database_url:
        missing.append("DATABASE_URL")
    if not settings.evolution_base_url:
        missing.append("EVOLUTION_BASE_URL")
    if not settings.evolution_api_key:
        missing.append("EVOLUTION_API_KEY")
    if not settings.openai_api_key:
        missing.append("OPENAI_API_KEY")
    return missing


def parse_evolution_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
    body = _get_body(payload)
    data = (body or {}).get("data") or {}
    key = data.get("key") or {}
    message = data.get("message") or {}

    remote_jid = key.get("remoteJid") or ""
    telefone_raw = key.get("senderPn") or remote_jid or key.get("senderLid") or ""

    telefone = normalize_phone(extract_phone_from_jid(telefone_raw))

    message_type = "other"
    if message.get("audioMessage"):
        message_type = "audio"
    elif message.get("conversation"):
        message_type = "text"
    elif message.get("stickerMessage"):
        message_type = "image/webp"
    elif message.get("documentMessage"):
        message_type = "documentMessage"
    elif message.get("imageMessage"):
        message_type = "image"

    timestamp = data.get("messageTimestamp") or 0
    timestamp_iso = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat() if timestamp else ""

    return {
        "id_mensagem": key.get("id"),
        "telefone": telefone,
        "instancia": body.get("instance") or body.get("instance_id") or "",
        "mensagem": message.get("conversation") or "",
        "mensagem_de_audio": (message.get("audioMessage") or {}).get("ptt") or False,
        "timestamp": timestamp,
        "fromMe": key.get("fromMe") or False,
        "mensagem_de_grupo": is_group_jid(remote_jid),
        "url_evolution": body.get("server_url") or settings.evolution_base_url,
        "timestamp_iso": timestamp_iso,
        "remote_jid": remote_jid,
        "message_type": message_type,
        "is_audio": (message.get("audioMessage") or {}).get("ptt") or False,
        "media_mime": (message.get("audioMessage") or {}).get("mimetype") or "",
        "media_size": (message.get("audioMessage") or {}).get("fileLength") or 0,
        "trace_id": f"{key.get('id','')}-{timestamp}",
        "url_audio": (message.get("audioMessage") or {}).get("url") or "",
        "url_imagem": (message.get("imageMessage") or {}).get("url") or "",
        "image_base64": (message.get("imageMessage") or {}).get("base64") or (message.get("imageMessage") or {}).get("jpegThumbnail"),
        "image_mimetype": (message.get("imageMessage") or {}).get("mimetype") or "image/jpeg",
    }


def _build_agent(db):
    saipos = SaiposClient(settings.saipos_base_url, settings.saipos_partner_id, settings.saipos_partner_secret, settings.saipos_token_ttl_seconds)
    menu_service = MenuService(db, saipos)
    order_service = OrderService(db, saipos)
    geocode = GeocodeService(settings.google_maps_api_key)

    atendente_prompt = (open("prompts/atendente.md", "r", encoding="utf-8").read())
    followup_prompt = (open("prompts/followup.md", "r", encoding="utf-8").read())

    return LLMAgent(db, order_service, menu_service, geocode, atendente_prompt, followup_prompt)


def _process_message(info: Dict[str, Any]) -> None:
    try:
        evolution = EvolutionClient(settings.evolution_base_url, settings.evolution_api_key)

        with get_db() as db:
            queue = process_queue(db, info["telefone"], info["id_mensagem"], settings.debounce_wait_seconds)
            if not queue:
                return

            # build content
            content = ""
            if info.get("message_type") == "audio":
                resp = evolution.get_base64_from_media(info.get("instancia"), info.get("id_mensagem"), base_url=info.get("url_evolution"))
                base64_data = resp.get("base64") or resp.get("data") or ""
                if base64_data:
                    if "," in base64_data:
                        base64_data = base64_data.split(",")[-1]
                    audio_bytes = base64.b64decode(base64_data)
                    agent = _build_agent(db)
                    content = agent.transcribe_audio(audio_bytes)
            if not content:
                content = concat_messages(queue) or info.get("mensagem") or ""

            try:
                historico = crud.fetch_client_snapshot(db, info.get("telefone")) or {}
            except Exception:
                logger.warning("snapshot_fetch_failed", exc_info=True)
                historico = {}

            horario = ""
            if info.get("timestamp"):
                horario = format_horario(datetime.fromtimestamp(info["timestamp"], tz=timezone.utc), settings.timezone)

            agent = _build_agent(db)
            reply = agent.run(content, info.get("telefone"), horario, historico)
            if reply is None:
                reply = ""

            crud.clear_messages(db, info.get("telefone"))

            if reply.strip():
                parts = split_messages(reply)
                for part in parts:
                    evolution.send_text(info.get("instancia"), info.get("telefone"), part, base_url=info.get("url_evolution"))

                crud.update_active_session_ai(db, info.get("telefone"), reply)
    except Exception:
        logger.exception("background_process_failed")


@router.post("/v3.1")
async def webhook_v3(request: Request, background_tasks: BackgroundTasks):
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored", "reason": "invalid_json"}

    supported, reason = _is_supported_payload(payload)
    if not supported:
        return {"status": "ignored", "reason": reason or "unsupported_payload"}

    missing = _missing_envs()
    if missing:
        logger.warning("missing_env", extra={"missing": missing})
        return {"status": "degraded", "reason": "missing_env", "missing": missing}

    info = parse_evolution_payload(payload)

    if info.get("fromMe"):
        return {"status": "ignored", "reason": "from_me"}
    if info.get("mensagem_de_grupo"):
        return {"status": "ignored", "reason": "group_message"}
    if info.get("message_type") not in ALLOWED_TYPES:
        return {"status": "ignored", "reason": "unsupported_message_type"}
    if not info.get("telefone") or len(info.get("telefone")) < 10:
        return {"status": "ignored", "reason": "invalid_phone"}

    with get_db() as db:
        if crud.is_duplicate_message(db, info.get("telefone"), info.get("id_mensagem")):
            return {"status": "duplicate"}

        crud.enqueue_message(
            db,
            {
                "telefone": info.get("telefone"),
                "mensagem": info.get("mensagem"),
                "timestamp": datetime.fromtimestamp(info.get("timestamp"), tz=timezone.utc) if info.get("timestamp") else None,
                "id_mensagem": info.get("id_mensagem"),
                "client_id": settings.client_id,
                "trace_id": info.get("trace_id"),
                "message_id": info.get("id_mensagem"),
                "remote_jid": info.get("remote_jid"),
                "message_type": info.get("message_type"),
                "status": "pending",
            },
        )

        crud.upsert_active_session(
            db,
            session_id=info.get("telefone"),
            last_message=info.get("mensagem") or "",
            last_message_type="human",
            last_message_id=info.get("id_mensagem"),
        )

    background_tasks.add_task(_process_message, info)
    return {"status": "queued"}


@router.post("/webhooks/evolution")
async def webhook_evolution_alias(request: Request, background_tasks: BackgroundTasks):
    return await webhook_v3(request, background_tasks)


@router.post("/enviar-pedido")
async def enviar_pedido(request: Request):
    payload = await request.json()
    with get_db() as db:
        saipos = SaiposClient(settings.saipos_base_url, settings.saipos_partner_id, settings.saipos_partner_secret, settings.saipos_token_ttl_seconds)
        order_service = OrderService(db, saipos)
        result = order_service.process_order(payload)
        return result


@router.post("/cancelar_pedido")
async def cancelar_pedido(request: Request):
    payload = await request.json()
    order_id = payload.get("order_id") or payload.get("body", {}).get("order_id")
    with get_db() as db:
        saipos = SaiposClient(settings.saipos_base_url, settings.saipos_partner_id, settings.saipos_partner_secret, settings.saipos_token_ttl_seconds)
        order_service = OrderService(db, saipos)
        result = order_service.cancel_order(order_id)
        return result


@router.post("/saipos-central")
async def saipos_central(request: Request):
    payload = await request.json()
    body = _get_body(payload)
    cod_store = body.get("cod_store") or body.get("codStore")
    if cod_store and settings.saipos_cod_store and cod_store != settings.saipos_cod_store:
        return {"status": "ignored"}

    with get_db() as db:
        evolution = EvolutionClient(settings.evolution_base_url, settings.evolution_api_key)
        status_service = StatusService(db, evolution)
        return status_service.process_event(payload)


@router.post("/webhooks/saipos")
async def saipos_alias(request: Request):
    return await saipos_central(request)


@router.post("/marcio_lanches")
async def marcio_lanches(request: Request):
    payload = await request.json()
    with get_db() as db:
        evolution = EvolutionClient(settings.evolution_base_url, settings.evolution_api_key)
        status_service = StatusService(db, evolution)
        return status_service.process_event(payload)
