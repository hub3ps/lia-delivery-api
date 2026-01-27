from __future__ import annotations

import httpx
from sqlalchemy import text

from app.db import crud
from app.settings import settings


class MenuService:
    def __init__(self, db, saipos_client) -> None:
        self.db = db
        self.saipos_client = saipos_client

    def _extract_items(self, data):
        if isinstance(data, list):
            return data
        if isinstance(data, dict):
            for key in ("items", "data", "results"):
                val = data.get(key)
                if isinstance(val, list):
                    return val
        return []

    def sync_menu(self) -> dict:
        data = self.saipos_client.fetch_catalog()
        items = self._extract_items(data)

        rows = []
        for row in items:
            codigo = row.get("codigo_saipos") or row.get("codigo") or row.get("pdv")
            pdv_code = codigo
            parent_pdv_code = None
            if codigo and isinstance(codigo, str) and "." in codigo:
                parent_pdv_code = codigo.split(".")[0]

            rows.append(
                {
                    "client_id": settings.client_id,
                    "tipo": row.get("tipo"),
                    "categoria": row.get("categoria"),
                    "tamanho": row.get("tamanho"),
                    "id_store_item": row.get("id_store_item"),
                    "item": row.get("item"),
                    "id_store_choice": row.get("id_store_choice"),
                    "complemento": row.get("complemento"),
                    "complemento_item": row.get("complemento_item"),
                    "price": row.get("price"),
                    "codigo_saipos": codigo,
                    "store_item_enabled": row.get("store_item_enabled"),
                    "store_choice_enabled": row.get("store_choice_enabled"),
                    "store_choice_item_enabled": row.get("store_choice_item_enabled"),
                    "item_type": row.get("item_type"),
                    "pdv_code": pdv_code,
                    "parent_pdv_code": parent_pdv_code,
                }
            )

        crud.delete_saipos_menu_raw(self.db, settings.client_id)
        crud.insert_saipos_menu_raw(self.db, rows)
        return {"inserted": len(rows)}

    def generate_embeddings(self) -> dict:
        # Fetch catalog from view
        result = self.db.execute(
            text(
                """
            SELECT item_id::text, pdv, display_name, category, price::numeric
            FROM v_menu_catalog
            WHERE active = true
            ORDER BY category, display_name
            """
            )
        )
        items = result.mappings().all()

        inserted = 0
        for item in items:
            embedding = self._embed_text(item.get("display_name") or "")
            if not embedding:
                continue
            embedding_str = "[" + ",".join(str(x) for x in embedding) + "]"
            self.db.execute(
                text(
                    """
                INSERT INTO menu_embeddings
                (pdv, display_name, category, price, embedding)
                VALUES (:pdv, :display_name, :category, :price, :embedding::vector)
                """
                ),
                {
                    "pdv": item.get("pdv"),
                    "display_name": item.get("display_name"),
                    "category": item.get("category"),
                    "price": item.get("price"),
                    "embedding": embedding_str,
                },
            )
            inserted += 1
        self.db.commit()
        return {"inserted": inserted}

    def _embed_text(self, text: str):
        if not settings.openai_api_key:
            return []
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
        payload = {"model": settings.openai_model_embed, "input": text}
        with httpx.Client(timeout=60) as client:
            resp = client.post(url, headers=headers, json=payload)
            resp.raise_for_status()
            data = resp.json()
        try:
            return data["data"][0]["embedding"]
        except Exception:
            return []
