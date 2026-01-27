from __future__ import annotations

import httpx


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

    return {
        "rua": find_by_type(["route"]),
        "numero": find_by_type(["street_number"]),
        "cep": find_by_type(["postal_code"]),
        "bairro": find_by_type(["sublocality_level_1"]),
        "cidade": find_by_type(["administrative_area_level_2"]),
        "estado": estado,
    }


class GeocodeService:
    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def geocode(self, query: str) -> dict:
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {"address": query, "key": self.api_key}
        with httpx.Client(timeout=30) as client:
            resp = client.get(url, params=params)
            resp.raise_for_status()
            data = resp.json()
        results = data.get("results") or []
        if not results:
            return {"error": "no_results", "raw": data}
        return parse_geocode_components(results[0])
