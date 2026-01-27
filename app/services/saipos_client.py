from __future__ import annotations

import time
import httpx


class SaiposClient:
    def __init__(self, base_url: str, partner_id: str, partner_secret: str, token_ttl_seconds: int = 3500) -> None:
        self.base_url = base_url.rstrip("/")
        self.partner_id = partner_id
        self.partner_secret = partner_secret
        self.token_ttl_seconds = token_ttl_seconds
        self._token: str | None = None
        self._token_exp: float = 0.0

    def _auth_headers(self) -> dict:
        if not self._token or time.time() > self._token_exp:
            self._token = self._fetch_token()
            self._token_exp = time.time() + self.token_ttl_seconds
        return {
            "Authorization": self._token,
            "accept": "application/json",
            "content-type": "application/json",
        }

    def _fetch_token(self) -> str:
        url = f"{self.base_url}/auth"
        payload = {"idPartner": self.partner_id, "secret": self.partner_secret}
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers={"content-type": "application/json", "accept": "application/json"})
            resp.raise_for_status()
            data = resp.json()
            # Saipos returns token directly or inside json
            if isinstance(data, str):
                return data
            return data.get("token") or data.get("access_token") or data.get("authorization") or ""

    def send_order(self, payload: dict) -> dict:
        url = f"{self.base_url}/order"
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, json=payload, headers=self._auth_headers())
            resp.raise_for_status()
            return resp.json()

    def cancel_order(self, cod_store: str, order_id: str) -> dict:
        url = f"{self.base_url}/cancel-order"
        payload = {"cod_store": cod_store, "order_id": order_id}
        with httpx.Client(timeout=30) as client:
            resp = client.post(url, json=payload, headers=self._auth_headers())
            resp.raise_for_status()
            return resp.json()

    def fetch_catalog(self) -> dict:
        url = f"{self.base_url}/catalog"
        with httpx.Client(timeout=60) as client:
            resp = client.get(url, headers=self._auth_headers())
            resp.raise_for_status()
            return resp.json()
