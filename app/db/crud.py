from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import text

from app.settings import settings


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
          SELECT regexp_replace(:tel::text, '\\D', '', 'g') AS d
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
            WHERE client_id = :client_id
            """
        ),
        {"client_id": settings.client_id},
    )
    return result.mappings().all()


def fetch_delivery_fee(db, bairro: str) -> List[Dict[str, Any]]:
    sql = text(
        """
        SELECT district AS bairro, delivery_fee AS taxa_entrega, city AS cidade
        FROM delivery_areas
        WHERE active = true
          AND unaccent(LOWER(city)) = unaccent(LOWER('Itajaí'))
          AND (
            unaccent(LOWER(district)) = unaccent(LOWER(:bairro))
            OR unaccent(LOWER(district)) LIKE '%' || unaccent(LOWER(:bairro)) || '%'
          )
        ORDER BY CASE WHEN unaccent(LOWER(district)) = unaccent(LOWER(:bairro)) THEN 0 ELSE 1 END, district
        LIMIT 10
        """
    )
    result = db.execute(sql, {"bairro": bairro}).mappings().all()
    return result


def fetch_stage_rules(db, stage: str) -> Optional[Dict[str, Any]]:
    sql = text(
        """
        SELECT stage, rules
        FROM public.delivery_policies_v2
        WHERE client_id = :client_id::uuid
          AND stage = :stage
          AND is_active = true
        LIMIT 1
        """
    )
    result = db.execute(sql, {"client_id": settings.client_id, "stage": stage}).mappings().first()
    return result


def insert_order(db, order_id: str, telefone: str, status: str, payload: Dict[str, Any], cod_store: str = "", response: Dict[str, Any] | None = None) -> None:
    sql = text(
        """
        INSERT INTO public.orders (order_id, telefone, status, payload, response, cod_store)
        VALUES (:order_id, :telefone, :status, :payload::jsonb, :response::jsonb, :cod_store)
        ON CONFLICT (order_id) DO UPDATE
        SET status = EXCLUDED.status,
            payload = EXCLUDED.payload,
            response = EXCLUDED.response,
            cod_store = EXCLUDED.cod_store,
            updated_at = now()
        """
    )
    db.execute(
        sql,
        {
            "order_id": order_id,
            "telefone": telefone,
            "status": status,
            "payload": payload,
            "response": response,
            "cod_store": cod_store,
        },
    )
    db.commit()


def update_order_status(db, order_id: str, status: str, response: Dict[str, Any] | None = None) -> None:
    sql = text(
        """
        UPDATE public.orders
        SET status = :status, response = :response::jsonb, updated_at = now()
        WHERE order_id = :order_id
        """
    )
    db.execute(sql, {"order_id": order_id, "status": status, "response": response})
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
