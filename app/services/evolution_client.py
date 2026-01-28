from __future__ import annotations

import logging
import re

import httpx

logger = logging.getLogger(__name__)


def normalize_phone_for_evolution(phone: str) -> str:
    digits = re.sub(r"\D+", "", phone or "")
    if digits and not digits.startswith("55"):
        digits = "55" + digits
    return digits


class EvolutionClient:
    def __init__(self, base_url: str, api_key: str, client: httpx.Client | None = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self._client = client

    def _headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["apikey"] = self.api_key
        return headers

    def _post(self, url: str, payload: dict, timeout: int) -> httpx.Response:
        if self._client is not None:
            return self._client.post(url, headers=self._headers(), json=payload)
        with httpx.Client(timeout=timeout) as client:
            return client.post(url, headers=self._headers(), json=payload)

    def send_text(self, instance: str, number: str, text: str, delay: int = 4000, base_url: str | None = None) -> dict:
        base = (base_url or self.base_url).rstrip("/")
        url = f"{base}/message/sendText/{instance}"
        normalized = normalize_phone_for_evolution(number)
        payload = {"number": normalized, "text": text, "delay": delay}
        resp = self._post(url, payload, timeout=30)
        if resp.status_code >= 400:
            logger.error(
                "evolution_send_text_failed",
                extra={
                    "status_code": resp.status_code,
                    "url": url,
                    "number_tail": normalized[-4:] if normalized else "",
                    "text_len": len(text or ""),
                    "response": resp.text[:500],
                },
            )
            raise RuntimeError(f"Evolution send_text failed: {resp.status_code} {resp.text[:500]}")
        return resp.json()

    def get_base64_from_media(self, instance: str, message_id: str, base_url: str | None = None) -> dict:
        base = (base_url or self.base_url).rstrip("/")
        url = f"{base}/chat/getBase64FromMediaMessage/{instance}"
        payload = {
            "message": {"key": {"id": message_id}},
            "convertToMp4": True,
        }
        resp = self._post(url, payload, timeout=60)
        resp.raise_for_status()
        return resp.json()
