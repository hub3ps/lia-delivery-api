from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid
import json
import logging
import unicodedata

from sqlalchemy import text
from sqlalchemy.exc import ProgrammingError

from app.settings import settings

logger = logging.getLogger(__name__)
_ORDERS_COLUMNS_CACHE: set[str] | None = None


def _normalize_text(value: str) -> str:
    if not value:
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    stripped = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return stripped.lower().strip()


def _filter_delivery_areas(rows: List[Dict[str, Any]], bairro: str) -> List[Dict[str, Any]]:
    target = _normalize_text(bairro)
    if not target:
        return rows[:10]
    exact: List[Dict[str, Any]] = []
    partial: List[Dict[str, Any]] = []
    for row in rows:
        district = row.get("bairro") or ""
        norm = _normalize_text(district)
        if norm == target:
            exact.append(row)
        elif target in norm:
            partial.append(row)
    return (exact + partial)[:10]


def _normalize_phone_digits(phone: str | None) -> str:
    if not phone:
        return ""
    return "".join(ch for ch in str(phone) if ch.isdigit())


def _find_client_id_by_phone(db, telefone: str) -> Optional[str]:
    sql = text(
        """
        WITH inp AS (
          SELECT regexp_replace(CAST(:tel AS text), '\\D', '', 'g') AS d
        ),
        cand AS (
          SELECT d AS k FROM inp
          UNION ALL SELECT CASE WHEN left(d,2)='55' THEN substring(d from 3) ELSE d END FROM inp
          UNION ALL SELECT CASE WHEN left(d,2)='55' THEN d ELSE '55'||d END FROM inp
        )
        SELECT id
        FROM archive.clients
        WHERE regexp_replace(phone, '\\D', '', 'g') IN (SELECT k FROM cand)
        LIMIT 1
        """
    )
    result = db.execute(sql, {"tel": telefone}).mappings().first()
    return result.get("id") if result else None


def upsert_client(
    db,
    telefone: str,
    nome: str | None = None,
    email: str | None = None,
    cpf_cnpj: str | None = None,
    birthday: str | None = None,
    last_purchase: datetime | None = None,
) -> Optional[str]:
    if not telefone:
        return None
    client_id = _find_client_id_by_phone(db, telefone)
    now = datetime.utcnow()
    if client_id:
        sql = text(
            """
            UPDATE archive.clients
            SET name = COALESCE(:name, name),
                phone = COALESCE(:phone, phone),
                email = COALESCE(:email, email),
                cpf_cnpj = COALESCE(:cpf_cnpj, cpf_cnpj),
                birthday = COALESCE(:birthday, birthday),
                last_seen = :now,
                last_purchase = COALESCE(:last_purchase, last_purchase)
            WHERE id = :id
            """
        )
        db.execute(
            sql,
            {
                "id": client_id,
                "name": nome,
                "phone": telefone,
                "email": email,
                "cpf_cnpj": cpf_cnpj,
                "birthday": birthday,
                "last_purchase": last_purchase,
                "now": now,
            },
        )
        db.commit()
        return str(client_id)

    new_id = str(uuid.uuid4())
    sql = text(
        """
        INSERT INTO archive.clients
          (id, name, phone, email, cpf_cnpj, birthday, first_seen, last_seen, last_purchase)
        VALUES
          (:id, :name, :phone, :email, :cpf_cnpj, :birthday, :now, :now, :last_purchase)
        """
    )
    db.execute(
        sql,
        {
            "id": new_id,
            "name": nome,
            "phone": telefone,
            "email": email,
            "cpf_cnpj": cpf_cnpj,
            "birthday": birthday,
            "last_purchase": last_purchase,
            "now": now,
        },
    )
    db.commit()
    return new_id


def _address_fingerprint(addr: Dict[str, Any]) -> str:
    parts = [
        addr.get("street") or addr.get("rua") or "",
        addr.get("number") or addr.get("numero") or "",
        addr.get("district") or addr.get("bairro") or "",
        addr.get("city") or addr.get("cidade") or "",
        addr.get("state") or addr.get("estado") or "",
        addr.get("postal_code") or addr.get("cep") or "",
        addr.get("complement") or addr.get("complemento") or "",
    ]
    normalized = "|".join(_normalize_text(p) for p in parts if p)
    return normalized


def upsert_address(db, client_id: str, endereco: Dict[str, Any]) -> Optional[str]:
    if not client_id or not isinstance(endereco, dict):
        return None
    fingerprint = _address_fingerprint(endereco)
    if not fingerprint:
        return None
    existing = db.execute(
        text(
            """
            SELECT id
            FROM public.addresses
            WHERE client_id = :client_id AND fingerprint = :fingerprint
            LIMIT 1
            """
        ),
        {"client_id": client_id, "fingerprint": fingerprint},
    ).mappings().first()
    if existing:
        return str(existing.get("id"))

    count = db.execute(
        text("SELECT count(*) AS c FROM public.addresses WHERE client_id = :client_id"),
        {"client_id": client_id},
    ).mappings().first()
    is_primary = True if (count and (count.get("c") or 0) == 0) else False

    addr = {
        "street": endereco.get("street") or endereco.get("rua") or "",
        "number": endereco.get("number") or endereco.get("numero") or "",
        "district": endereco.get("district") or endereco.get("bairro") or "",
        "city": endereco.get("city") or endereco.get("cidade") or "",
        "state": endereco.get("state") or endereco.get("estado") or "",
        "postal_code": endereco.get("postal_code") or endereco.get("cep") or "",
        "complement": endereco.get("complement") or endereco.get("complemento") or "",
    }
    new_id = str(uuid.uuid4())
    sql = text(
        """
        INSERT INTO public.addresses
          (id, client_id, street, number, district, city, state, postal_code, complement, is_primary, fingerprint)
        VALUES
          (:id, :client_id, :street, :number, :district, :city, :state, :postal_code, :complement, :is_primary, :fingerprint)
        """
    )
    db.execute(
        sql,
        {
            "id": new_id,
            "client_id": client_id,
            **addr,
            "is_primary": is_primary,
            "fingerprint": fingerprint,
        },
    )
    db.commit()
    return new_id


def _get_orders_columns(db) -> set[str]:
    global _ORDERS_COLUMNS_CACHE
    if _ORDERS_COLUMNS_CACHE is not None:
        return _ORDERS_COLUMNS_CACHE
    sql = text(
        """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = 'public' AND table_name = 'orders'
        """
    )
    rows = db.execute(sql).mappings().all()
    _ORDERS_COLUMNS_CACHE = {r.get("column_name") for r in rows if r.get("column_name")}
    return _ORDERS_COLUMNS_CACHE


def _calc_saipos_subtotal(payload: Dict[str, Any]) -> float:
    subtotal = 0.0
    items = payload.get("items") if isinstance(payload.get("items"), list) else []
    for item in items:
        qty = float(item.get("quantity") or 1)
        unit_price = float(item.get("unit_price") or 0)
        subtotal += qty * unit_price
        for ad in item.get("choice_items", []) or []:
            ad_qty = float(ad.get("quantity") or 1)
            ad_price = float(ad.get("aditional_price") or 0)
            subtotal += ad_qty * ad_price * qty
    return subtotal


def _insert_order_new_schema(
    db,
    order_id: str,
    status: str,
    payload_json: str | None,
    response_json: str | None,
    cod_store: str,
    client_id: str | None = None,
) -> Optional[str]:
    columns = _get_orders_columns(db)
    if not columns:
        return None

    payload: Dict[str, Any] = {}
    if payload_json:
        try:
            payload = json.loads(payload_json)
        except Exception:
            payload = {}

    data: Dict[str, Any] = {
        "order_id": order_id,
        "client_id": client_id,
        "status": status,
        "payment_method": ((payload.get("payment_types") or [{}])[0] or {}).get("code") or "",
        "subtotal": _calc_saipos_subtotal(payload),
        "delivery_fee": (payload.get("order_method") or {}).get("delivery_fee") or 0,
        "descount_amount": payload.get("total_discount") or 0,
        "total_amount": payload.get("total_amount") or 0,
        "address_snapshot": json.dumps(payload.get("delivery_address")) if payload.get("delivery_address") else None,
        "payload_snapshot": payload_json,
        "source": "lia_delivery",
    }

    jsonb_cols = {"payload_snapshot", "address_snapshot"}
    cols = [c for c in data.keys() if c in columns]
    if not cols:
        return None

    values = []
    for c in cols:
        if c in jsonb_cols:
            values.append(f"CAST(:{c} AS jsonb)")
        else:
            values.append(f":{c}")

    updates = [f"{c} = EXCLUDED.{c}" for c in cols if c != "order_id"]
    update_sql = ", ".join(updates) if updates else "order_id = EXCLUDED.order_id"

    params = {c: data[c] for c in cols}
    sql = text(
        f"""
        INSERT INTO public.orders ({', '.join(cols)})
        VALUES ({', '.join(values)})
        ON CONFLICT (order_id) DO UPDATE
        SET {update_sql}
        RETURNING id
        """
    )
    try:
        result = db.execute(sql, params)
        db.commit()
        try:
            return str(result.scalar_one())
        except Exception:
            return None
    except ProgrammingError as exc:
        if "conflict" not in str(exc).lower():
            db.rollback()
            raise
        db.rollback()
        sql_no_conflict = text(
            f"""
            INSERT INTO public.orders ({', '.join(cols)})
            VALUES ({', '.join(values)})
            RETURNING id
            """
        )
        result = db.execute(sql_no_conflict, params)
        db.commit()
        try:
            return str(result.scalar_one())
        except Exception:
            return None


def enqueue_message(db, data: Dict[str, Any]) -> None:
    sql = text(
        """
        INSERT INTO public.n8n_fila_mensagens
        (telefone, mensagem, timestamp, id_mensagem, client_id, trace_id, message_id, remote_jid, message_type, status)
        VALUES
        (:telefone, :mensagem, :timestamp, :id_mensagem, :client_id, :trace_id, :message_id, :remote_jid, :message_type, :status)
        """
    )
    db.execute(sql, data)
    db.commit()


def get_pending_messages(db, telefone: str) -> List[Dict[str, Any]]:
    sql = text(
        """
        SELECT *
        FROM public.n8n_fila_mensagens
        WHERE telefone = :telefone AND status = 'pending'
        ORDER BY timestamp ASC
        """
    )
    result = db.execute(sql, {"telefone": telefone})
    return result.mappings().all()


def clear_messages(db, telefone: str) -> None:
    sql = text(
        """
        DELETE FROM public.n8n_fila_mensagens
        WHERE telefone = :telefone
        """
    )
    db.execute(sql, {"telefone": telefone})
    db.commit()


def upsert_active_session(
    db,
    session_id: str,
    last_message: str,
    last_message_type: str,
    last_message_id: Optional[str] = None,
) -> None:
    sql = text(
        """
        INSERT INTO public.active_sessions AS s
          (session_id, last_message, last_message_type, status, last_message_id)
        VALUES
          (:session_id, :last_message, :last_message_type, 'active', :last_message_id)
        ON CONFLICT (session_id) WHERE (status = 'active')
        DO UPDATE
           SET last_message = EXCLUDED.last_message,
               last_message_type = EXCLUDED.last_message_type,
               last_message_id = EXCLUDED.last_message_id,
               updated_at = now(),
               followup_sent_at = NULL
        """
    )
    db.execute(
        sql,
        {
            "session_id": session_id,
            "last_message": last_message,
            "last_message_type": last_message_type,
            "last_message_id": last_message_id,
        },
    )
    db.commit()


def update_active_session_ai(db, session_id: str, last_message: str) -> None:
    sql = text(
        """
        UPDATE public.active_sessions
        SET last_message = :last_message,
            last_message_type = 'ai',
            updated_at = now()
        WHERE session_id = :session_id AND status = 'active'
        """
    )
    db.execute(sql, {"session_id": session_id, "last_message": last_message})
    db.commit()


def update_active_session_finished(db, session_id: str) -> None:
    sql = text(
        """
        UPDATE public.active_sessions
        SET status = 'finished', updated_at = now()
        WHERE session_id = :session_id AND status = 'active'
        """
    )
    db.execute(sql, {"session_id": session_id})
    db.commit()


def fetch_cart(db, session_id: str) -> Optional[Dict[str, Any]]:
    sql = text(
        """
        SELECT cart_json
        FROM public.active_sessions
        WHERE session_id = :session_id
        ORDER BY CASE WHEN status = 'active' THEN 0 ELSE 1 END, updated_at DESC
        LIMIT 1
        """
    )
    result = db.execute(sql, {"session_id": session_id}).mappings().first()
    if not result:
        return None
    cart = result.get("cart_json")
    return cart if isinstance(cart, dict) else None


def update_cart(db, session_id: str, cart: Dict[str, Any]) -> Dict[str, Any]:
    sql = text(
        """
        UPDATE public.active_sessions
        SET cart_json = CAST(:cart_json AS jsonb),
            cart_updated_at = now(),
            updated_at = now()
        WHERE session_id = :session_id AND status = 'active'
        """
    )
    db.execute(sql, {"session_id": session_id, "cart_json": json.dumps(cart)})
    db.commit()
    return cart


def patch_cart(db, session_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    current = fetch_cart(db, session_id) or {}
    if not isinstance(current, dict):
        current = {}
    for key, value in patch.items():
        if value is None:
            continue
        current[key] = value
    return update_cart(db, session_id, current)


def clear_cart(db, session_id: str) -> None:
    sql = text(
        """
        UPDATE public.active_sessions
        SET cart_json = NULL,
            cart_updated_at = now(),
            updated_at = now()
        WHERE session_id = :session_id
        """
    )
    db.execute(sql, {"session_id": session_id})
    db.commit()


def get_active_session(db, session_id: str) -> Optional[Dict[str, Any]]:
    sql = text(
        """
        SELECT * FROM public.active_sessions
        WHERE session_id = :session_id AND status = 'active'
        LIMIT 1
        """
    )
    result = db.execute(sql, {"session_id": session_id}).mappings().first()
    return result


def is_duplicate_message(db, session_id: str, message_id: str) -> bool:
    session = get_active_session(db, session_id)
    if not session:
        return False
    last_id = session.get("last_message_id")
    return bool(last_id and message_id and last_id == message_id)


def fetch_client_snapshot(db, telefone: str) -> Optional[Dict[str, Any]]:
    sql = text(
        """
        WITH inp AS (
          SELECT regexp_replace(CAST(:tel AS text), '\\D', '', 'g') AS d
        ),
        cand AS (
          SELECT d AS k FROM inp
          UNION ALL SELECT CASE WHEN left(d,2)='55' THEN substring(d from 3) ELSE d END FROM inp
          UNION ALL SELECT CASE WHEN left(d,2)='55' THEN d ELSE '55'||d END FROM inp
        )
        SELECT *
        FROM public.view_client_snapshot
        WHERE regexp_replace(phone, '\\D', '', 'g') IN (SELECT k FROM cand)
        ORDER BY last_order_at DESC NULLS LAST
        LIMIT 1
        """
    )
    result = db.execute(sql, {"tel": telefone}).mappings().first()
    return result


def fetch_menu_search_index(db) -> List[Dict[str, Any]]:
    result = db.execute(text("SELECT * FROM v_menu_search_index"))
    return result.mappings().all()


def fetch_cardapio(db) -> List[Dict[str, Any]]:
    result = db.execute(
        text(
            """
            SELECT categoria, item, tamanho, tipo, price, adicionais
            FROM public.menu_catalog_agent_v1
            """
        )
    )
    return result.mappings().all()


def fetch_delivery_fee(db, bairro: str) -> List[Dict[str, Any]]:
    cidade = settings.delivery_city or "Itajaí"
    sql = text(
        """
        SELECT district AS bairro, delivery_fee AS taxa_entrega, city AS cidade
        FROM delivery_areas
        WHERE active = true
          AND unaccent(LOWER(city)) = unaccent(LOWER(:cidade))
          AND (
            unaccent(LOWER(district)) = unaccent(LOWER(:bairro))
            OR unaccent(LOWER(district)) LIKE '%' || unaccent(LOWER(:bairro)) || '%'
          )
        ORDER BY CASE WHEN unaccent(LOWER(district)) = unaccent(LOWER(:bairro)) THEN 0 ELSE 1 END, district
        LIMIT 10
        """
    )
    try:
        result = db.execute(sql, {"bairro": bairro, "cidade": cidade}).mappings().all()
        return result
    except ProgrammingError as exc:
        if "unaccent" not in str(exc).lower():
            raise
        db.rollback()
        logger.warning("delivery_fee_unaccent_missing_fallback", extra={"cidade": cidade})
        fallback_sql = text(
            """
            SELECT district AS bairro, delivery_fee AS taxa_entrega, city AS cidade
            FROM delivery_areas
            WHERE active = true
              AND lower(city) = lower(:cidade)
            ORDER BY district
            """
        )
        rows = db.execute(fallback_sql, {"cidade": cidade}).mappings().all()
        return _filter_delivery_areas(rows, bairro)


def fetch_stage_rules(db, stage: str) -> Optional[Dict[str, Any]]:
    sql = text(
        """
        SELECT stage, rules
        FROM public.delivery_policies_v2
        WHERE stage = :stage
          AND is_active = true
        LIMIT 1
        """
    )
    result = db.execute(sql, {"stage": stage}).mappings().first()
    return result


def insert_order(
    db,
    order_id: str,
    telefone: str,
    status: str,
    payload: Dict[str, Any],
    cod_store: str = "",
    response: Dict[str, Any] | None = None,
    client_id: str | None = None,
) -> Optional[str]:
    payload_json = json.dumps(payload) if payload is not None else None
    response_json = json.dumps(response) if response is not None else None
    columns = _get_orders_columns(db)
    if "payload_snapshot" in columns:
        return _insert_order_new_schema(db, order_id, status, payload_json, response_json, cod_store, client_id=client_id)
    sql = text(
        """
        INSERT INTO public.orders (order_id, telefone, status, payload, response, cod_store)
        VALUES (:order_id, :telefone, :status, CAST(:payload AS jsonb), CAST(:response AS jsonb), :cod_store)
        ON CONFLICT (order_id) DO UPDATE
        SET status = EXCLUDED.status,
            payload = EXCLUDED.payload,
            response = EXCLUDED.response,
            cod_store = EXCLUDED.cod_store,
            updated_at = now()
        """
    )
    params = {
        "order_id": order_id,
        "telefone": telefone,
        "status": status,
        "payload": payload_json,
        "response": response_json,
        "cod_store": cod_store,
    }
    try:
        db.execute(sql, params)
        db.commit()
    except ProgrammingError as exc:
        if "telefone" not in str(exc).lower():
            db.rollback()
            raise
        db.rollback()
        fallback_sql = text(
            """
            INSERT INTO public.orders (order_id, status, payload, response, cod_store)
            VALUES (:order_id, :status, CAST(:payload AS jsonb), CAST(:response AS jsonb), :cod_store)
            ON CONFLICT (order_id) DO UPDATE
            SET status = EXCLUDED.status,
                payload = EXCLUDED.payload,
                response = EXCLUDED.response,
                cod_store = EXCLUDED.cod_store,
                updated_at = now()
            """
        )
        fallback_params = {
            "order_id": order_id,
            "status": status,
            "payload": payload_json,
            "response": response_json,
            "cod_store": cod_store,
        }
        db.execute(fallback_sql, fallback_params)
        db.commit()


def insert_order_items(db, order_db_id: str, items: List[Dict[str, Any]]) -> None:
    if not order_db_id or not items:
        return
    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        rows.append(
            {
                "id": str(uuid.uuid4()),
                "order_id": order_db_id,
                "pdv": item.get("pdv") or "",
                "description": item.get("descricao") or item.get("nome") or "",
                "item_type": item.get("item_type") or "product",
                "quantity": int(item.get("quantidade") or item.get("qtd") or 1),
                "unit_price": float(item.get("valor_unitario") or 0),
                "notes": item.get("observacao") or "",
            }
        )
        adicionais = item.get("adicionais") if isinstance(item.get("adicionais"), list) else []
        for ad in adicionais:
            if not isinstance(ad, dict):
                continue
            rows.append(
                {
                    "id": str(uuid.uuid4()),
                    "order_id": order_db_id,
                    "pdv": ad.get("pdv") or "",
                    "description": ad.get("descricao") or ad.get("nome") or "",
                    "item_type": "addition",
                    "quantity": int(ad.get("quantidade") or ad.get("qtd") or 1),
                    "unit_price": float(ad.get("valor_unitario") or 0),
                    "notes": "",
                }
            )
    sql = text(
        """
        INSERT INTO public.order_items
          (id, order_id, pdv, description, item_type, quantity, unit_price, notes)
        VALUES
          (:id, :order_id, :pdv, :description, :item_type, :quantity, :unit_price, :notes)
        """
    )
    db.execute(sql, rows)
    db.commit()


def update_order_status(db, order_id: str, status: str, response: Dict[str, Any] | None = None) -> None:
    response_json = json.dumps(response) if response is not None else None
    columns = _get_orders_columns(db)
    if "response" not in columns:
        sql = text(
            """
            UPDATE public.orders
            SET status = :status, updated_at = now()
            WHERE order_id = :order_id
            """
        )
        db.execute(sql, {"order_id": order_id, "status": status})
        db.commit()
        return
    sql = text(
        """
        UPDATE public.orders
        SET status = :status, response = CAST(:response AS jsonb), updated_at = now()
        WHERE order_id = :order_id
        """
    )
    db.execute(sql, {"order_id": order_id, "status": status, "response": response_json})
    db.commit()


def get_order(db, order_id: str) -> Optional[Dict[str, Any]]:
    sql = text(
        """
        SELECT * FROM public.orders WHERE order_id = :order_id LIMIT 1
        """
    )
    return db.execute(sql, {"order_id": order_id}).mappings().first()


def delete_saipos_menu_raw(db, client_id: str) -> None:
    sql = text(
        """
        DELETE FROM public.saipos_menu_raw WHERE client_id = :client_id::uuid
        """
    )
    db.execute(sql, {"client_id": client_id})
    db.commit()


def insert_saipos_menu_raw(db, rows: List[Dict[str, Any]]) -> None:
    if not rows:
        return
    sql = text(
        """
        INSERT INTO public.saipos_menu_raw
        (client_id, tipo, categoria, tamanho, id_store_item, item, id_store_choice, complemento, complemento_item,
         price, codigo_saipos, store_item_enabled, store_choice_enabled, store_choice_item_enabled, item_type,
         pdv_code, parent_pdv_code)
        VALUES
        (:client_id, :tipo, :categoria, :tamanho, :id_store_item, :item, :id_store_choice, :complemento, :complemento_item,
         :price, :codigo_saipos, :store_item_enabled, :store_choice_enabled, :store_choice_item_enabled, :item_type,
         :pdv_code, :parent_pdv_code)
        """
    )
    db.execute(sql, rows)
    db.commit()


def fetch_followup_candidates(db) -> List[Dict[str, Any]]:
    sql = text(
        """
        SELECT id, session_id, last_message, last_message_type, updated_at, followup_count
        FROM public.active_sessions
        WHERE status = 'active'
          AND last_message_type IN ('ai','human')
          AND updated_at < now() - interval '10 minutes'
          AND COALESCE(followup_count,0) < 2
          AND followup_sent_at IS NULL
        ORDER BY updated_at ASC
        LIMIT 200
        """
    )
    return db.execute(sql).mappings().all()


def mark_followup_sent(db, session_id: str, message: str) -> None:
    sql = text(
        """
        UPDATE public.active_sessions
        SET
          last_message = :message,
          last_message_type = 'ai',
          updated_at = NOW(),
          followup_sent_at = NOW(),
          followup_count = COALESCE(followup_count, 0) + 1
        WHERE session_id = :session_id AND status = 'active'
        """
    )
    db.execute(sql, {"session_id": session_id, "message": message})
    db.commit()


def insert_chat_history(db, session_id: str, role: str, content: str) -> None:
    message = {
        "type": role,
        "data": {
            "content": content or "",
            "additional_kwargs": {},
        },
    }
    sql = text(
        """
        INSERT INTO public.n8n_historico_mensagens (session_id, message)
        VALUES (:session_id, CAST(:message AS jsonb))
        """
    )
    try:
        db.execute(sql, {"session_id": session_id, "message": json.dumps(message)})
        db.commit()
    except Exception:
        db.rollback()
        raise


def insert_order_audit(
    db,
    session_id: str,
    telefone: str,
    trace_id: Optional[str],
    status: str,
    agent_order_json: Dict[str, Any],
    saipos_payload_json: Dict[str, Any],
    error: Optional[str] = None,
) -> None:
    sql = text(
        """
        INSERT INTO public.order_audit
          (session_id, telefone, trace_id, status, agent_order_json, saipos_payload_json, error)
        VALUES
          (:session_id, :telefone, :trace_id, :status, CAST(:agent_order_json AS jsonb), CAST(:saipos_payload_json AS jsonb), :error)
        """
    )
    try:
        db.execute(
            sql,
            {
                "session_id": session_id,
                "telefone": telefone,
                "trace_id": trace_id,
                "status": status,
                "agent_order_json": json.dumps(agent_order_json),
                "saipos_payload_json": json.dumps(saipos_payload_json),
                "error": error,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


def insert_order_audit_raw(
    db,
    session_id: str,
    telefone: str,
    trace_id: Optional[str],
    agent_order_json: Dict[str, Any],
) -> Optional[int]:
    sql = text(
        """
        INSERT INTO public.order_audit
          (session_id, telefone, trace_id, status, agent_order_json)
        VALUES
          (:session_id, :telefone, :trace_id, 'raw', CAST(:agent_order_json AS jsonb))
        RETURNING id
        """
    )
    try:
        result = db.execute(
            sql,
            {
                "session_id": session_id,
                "telefone": telefone,
                "trace_id": trace_id,
                "agent_order_json": json.dumps(agent_order_json),
            },
        )
        audit_id = result.scalar_one_or_none()
        db.commit()
        return audit_id
    except Exception:
        db.rollback()
        raise


def insert_order_audit_quote(
    db,
    session_id: str,
    telefone: str,
    trace_id: Optional[str],
    agent_order_json: Dict[str, Any],
    quoted_json: Dict[str, Any],
) -> Optional[int]:
    sql = text(
        """
        INSERT INTO public.order_audit
          (session_id, telefone, trace_id, status, agent_order_json, quoted_json)
        VALUES
          (:session_id, :telefone, :trace_id, 'quote', CAST(:agent_order_json AS jsonb), CAST(:quoted_json AS jsonb))
        RETURNING id
        """
    )
    try:
        result = db.execute(
            sql,
            {
                "session_id": session_id,
                "telefone": telefone,
                "trace_id": trace_id,
                "agent_order_json": json.dumps(agent_order_json),
                "quoted_json": json.dumps(quoted_json),
            },
        )
        audit_id = result.scalar_one_or_none()
        db.commit()
        return audit_id
    except Exception:
        db.rollback()
        raise


def update_order_audit_saipos(
    db,
    audit_id: int,
    status: str,
    saipos_payload_json: Dict[str, Any] | None,
    error: Optional[str] = None,
) -> None:
    sql = text(
        """
        UPDATE public.order_audit
        SET status = :status,
            saipos_payload_json = CAST(:saipos_payload_json AS jsonb),
            error = :error
        WHERE id = :id
        """
    )
    try:
        db.execute(
            sql,
            {
                "id": audit_id,
                "status": status,
                "saipos_payload_json": None if saipos_payload_json is None else json.dumps(saipos_payload_json),
                "error": error,
            },
        )
        db.commit()
    except Exception:
        db.rollback()
        raise


def fetch_chat_history(db, session_id: str, limit: int = 20) -> List[Dict[str, Any]]:
    sql = text(
        """
        SELECT message
        FROM public.n8n_historico_mensagens
        WHERE session_id = :session_id
        ORDER BY id DESC
        LIMIT :limit
        """
    )
    result = db.execute(sql, {"session_id": session_id, "limit": limit}).mappings().all()
    return result
