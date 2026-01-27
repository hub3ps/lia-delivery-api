from __future__ import annotations

import httpx


class EvolutionClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key

    def _headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["apikey"] = self.api_key
        return headers

    def send_text(self, instance: str, number: str, text: str, delay: int = 4000, base_url: str | None = None) -> dict:
        base = (base_url or self.base_url).rstrip("/")
        url = f"{base}/message/sendText/{instance}"
        payload = {"number": number, "text": text, "delay": delay}
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()

    def get_base64_from_media(self, instance: str, message_id: str, base_url: str | None = None) -> dict:
        base = (base_url or self.base_url).rstrip("/")
        url = f"{base}/chat/getBase64FromMediaMessage/{instance}"
        payload = {
            "message": {"key": {"id": message_id}},
            "convertToMp4": True,
        }
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=self._headers(), json=payload)
            resp.raise_for_status()
            return resp.json()
