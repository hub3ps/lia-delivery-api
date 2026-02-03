from __future__ import annotations

import json
import re
from typing import Any, Dict

import httpx

from app.settings import settings


def _strip_markdown_json(text: str) -> str:
    cleaned = text.replace("```json", "").replace("```", "").strip()
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1:
        cleaned = cleaned[start : end + 1]
    return cleaned


def _basic_heuristic(text: str) -> Dict[str, Any]:
    if not text:
        return {"valid": False, "reason": "empty_text"}
    text_lower = text.lower()
    keywords = ["pix", "comprovante", "transfer", "transf", "recebido", "pagamento", "qr code"]
    score = sum(1 for k in keywords if k in text_lower)
    return {"valid": score >= 2, "reason": "heuristic", "score": score}


def validate_pix_receipt(
    media_base64: str | None,
    mime_type: str | None = None,
    texto: str | None = None,
    return_usage: bool = False,
) -> Dict[str, Any]:
    if texto and not media_base64:
        return _basic_heuristic(texto)
    if not media_base64:
        return {"error": "missing_media"}
    if not settings.openai_api_key:
        # fallback: at least confirms receipt presence
        return {"valid": True, "reason": "no_api_key"}

    mime = mime_type or "image/jpeg"
    data_url = f"data:{mime};base64,{media_base64}"

    messages = [
        {
            "role": "system",
            "content": "Você valida comprovantes PIX no Brasil. Responda SOMENTE em JSON.",
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": "Esse arquivo é um comprovante PIX válido? Responda em JSON com campos: valid (bool), reason (string), amount (number ou null), name (string ou null), date (string ou null)."},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        },
    ]

    payload = {
        "model": settings.openai_model_chat,
        "messages": messages,
        "temperature": 0.0,
    }
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    try:
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
    except Exception as exc:
        return {"error": "openai_request_failed", "message": str(exc)}

    usage = data.get("usage") if return_usage else None
    content = data.get("choices", [{}])[0].get("message", {}).get("content") or ""
    try:
        clean = _strip_markdown_json(content)
        parsed = json.loads(clean)
        if isinstance(parsed, dict):
            if usage and isinstance(usage, dict):
                parsed["_usage"] = usage
            return parsed
    except Exception:
        pass

    # fallback: try to extract "valid" with regex
    match = re.search(r"\btrue\b|\bfalse\b", content.lower())
    if match:
        result = {"valid": match.group(0) == "true", "reason": "parsed_fallback", "raw": content}
        if usage and isinstance(usage, dict):
            result["_usage"] = usage
        return result

    result = {"valid": False, "reason": "unparseable", "raw": content}
    if usage and isinstance(usage, dict):
        result["_usage"] = usage
    return result
