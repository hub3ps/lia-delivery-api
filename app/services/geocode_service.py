from __future__ import annotations

import logging
import unicodedata

import httpx

logger = logging.getLogger(__name__)


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return stripped.lower().strip()


def parse_geocode_components(result: dict) -> dict:
    components = result.get("address_components") or []

    def find_by_type(types):
        for comp in components:
            if any(t in comp.get("types", []) for t in types):
                return comp.get("long_name")
        return None

    estado = None
    for comp in components:
        if "administrative_area_level_1" in comp.get("types", []):
            estado = comp.get("short_name")
            break

    cidade = find_by_type(["locality", "administrative_area_level_2", "administrative_area_level_3"])
    bairro = find_by_type(["sublocality", "sublocality_level_1", "sublocality_level_2", "neighborhood"])

    return {
        "rua": find_by_type(["route"]),
        "numero": find_by_type(["street_number"]),
        "cep": find_by_type(["postal_code"]),
        "bairro": bairro,
        "cidade": cidade,
        "estado": estado,
    }


class GeocodeService:
    def __init__(self, api_key: str, city: str | None = None, state: str | None = None, country: str | None = None) -> None:
        self.api_key = api_key
        self.city = city or ""
        self.state = state or ""
        self.country = country or ""

    def _build_query(self, query: str) -> str:
        base = query.strip()
        if not base:
            return base
        base_norm = _normalize_text(base)
        parts = [base]
        for extra in (self.city, self.state, self.country):
            if not extra:
                continue
            extra_norm = _normalize_text(extra)
            if extra_norm and extra_norm not in base_norm:
                parts.append(extra)
        return ", ".join(parts)

    def _components_filter(self) -> str:
        parts = []
        if self.country:
            parts.append(f"country:{self.country}")
        if self.state:
            parts.append(f"administrative_area:{self.state}")
        if self.city:
            parts.append(f"locality:{self.city}")
        return "|".join(parts)

    def _validate_location(self, parsed: dict) -> tuple[bool, str | None]:
        if self.city:
            if _normalize_text(parsed.get("cidade") or "") != _normalize_text(self.city):
                return False, "outside_city"
        if self.state:
            if _normalize_text(parsed.get("estado") or "") != _normalize_text(self.state):
                return False, "outside_state"
        return True, None

    def geocode(self, query: str) -> dict:
        if not self.api_key:
            return {"error": "missing_api_key"}
        if not query or not query.strip():
            return {"error": "empty_query"}

        url = "https://maps.googleapis.com/maps/api/geocode/json"
        full_query = self._build_query(query)
        params = {"address": full_query, "key": self.api_key, "region": "br"}
        components = self._components_filter()
        if components:
            params["components"] = components

        try:
            with httpx.Client(timeout=30) as client:
                resp = client.get(url, params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as exc:
            logger.warning("geocode_request_failed", exc_info=True)
            return {"error": "geocode_exception", "message": str(exc)}

        status = data.get("status")
        if status != "OK":
            return {"error": "geocode_failed", "status": status, "message": data.get("error_message"), "raw": data}

        results = data.get("results") or []
        if not results:
            return {"error": "no_results", "raw": data}

        parsed = parse_geocode_components(results[0])
        valid, reason = self._validate_location(parsed)
        if not valid:
            return {
                "error": "address_invalid",
                "reason": reason,
                "expected_city": self.city,
                "expected_state": self.state,
                "found_city": parsed.get("cidade"),
                "found_state": parsed.get("estado"),
                "raw": data,
            }

        if not parsed.get("rua") or not parsed.get("numero"):
            return {
                "error": "address_incomplete",
                "reason": "missing_street_number",
                "found": parsed,
                "raw": data,
            }

        return parsed
