from __future__ import annotations

import logging
import random
import time
from typing import Any, Dict, Tuple

from app.db import crud
from app.settings import settings
from app.utils.fingerprints import calcular_total_pedido, mapear_itens
from app.utils.phone import normalize_phone

logger = logging.getLogger(__name__)


def _num(val: Any, default: float = 0.0) -> float:
    if isinstance(val, str):
        val = val.replace(",", ".")
    try:
        return float(val)
    except Exception:
        return default


def _to_str(val: Any) -> str:
    return "" if val is None else str(val)


def build_payload_saipos(pedido_original: Dict, indice_banco: list) -> Tuple[Dict, list]:
    itens_mapeados, erros = mapear_itens(pedido_original, indice_banco)

    taxa_entrega = _num(pedido_original.get("taxa_entrega") or 0)
    desconto = _num(pedido_original.get("desconto") or 0)
    total_calculado = calcular_total_pedido(itens_mapeados, taxa_entrega, desconto)

    endereco = pedido_original.get("endereco") or {}
    rua = endereco.get("rua") or ""
    numero = endereco.get("numero") or ""
    bairro = endereco.get("bairro") or ""
    complemento = endereco.get("complemento") or ""

    if isinstance(pedido_original.get("endereco"), str):
        partes = [p.strip() for p in pedido_original.get("endereco").split(",")]
        if len(partes) >= 1:
            rua = partes[0]
        if len(partes) >= 2:
            numero = partes[1]
        if len(partes) >= 3:
            bairro = partes[2]

    payload = {
        "session_id": (pedido_original.get("dados_cliente") or {}).get("telefone") or pedido_original.get("telefone"),
        "nome": (pedido_original.get("dados_cliente") or {}).get("nome") or pedido_original.get("nome"),
        "telefone": (pedido_original.get("dados_cliente") or {}).get("telefone") or pedido_original.get("telefone"),
        "tipo_entrega": pedido_original.get("tipo_entrega"),
        "rua": rua,
        "numero": numero,
        "bairro": bairro,
        "cep": endereco.get("cep") or "",
        "cidade": "Itajaí",
        "complemento": complemento,
        "taxa_entrega": _num(pedido_original.get("taxa_entrega") or 0),
        "desconto": _num(pedido_original.get("desconto") or 0),
        "pagamento": pedido_original.get("pagamento") or "cartao_credito",
        "troco_para": _num(pedido_original.get("troco_para") or 0),
        "total": float(f"{total_calculado:.2f}"),
        "itens": itens_mapeados,
    }
    return payload, erros


def formatar_json_saipos(data: Dict[str, Any]) -> Dict[str, Any]:
    order_id = f"{int(time.time() * 1000)}{random.randint(0, 999)}"
    display_id = settings.saipos_display_id or "5457"
    cod_store = settings.saipos_cod_store or "MAR001"

    itens = data.get("itens") if isinstance(data.get("itens"), list) else []

    pedidos_array = []
    for item in itens:
        adicionais = item.get("adicionais") if isinstance(item.get("adicionais"), list) else []
        choice_items = []
        for ad in adicionais:
            pdv_completo = str(ad.get("pdv") or "")
            integration_code = pdv_completo.split(".")[1].strip() if "." in pdv_completo else pdv_completo.strip()
            choice_items.append(
                {
                    "integration_code": integration_code,
                    "desc_item_choice": ad.get("descricao") or "",
                    "aditional_price": _num(ad.get("valor_unitario")),
                    "quantity": _num(ad.get("quantidade"), 1),
                    "notes": "",
                }
            )

        pedidos_array.append(
            {
                "integration_code": str(item.get("pdv") or "").strip(),
                "desc_item": item.get("descricao") or "",
                "quantity": _num(item.get("quantidade"), 1),
                "unit_price": _num(item.get("valor_unitario")),
                "notes": item.get("observacao") or "",
                "choice_items": choice_items,
            }
        )

    payment_code = "CARD"
    pg = (data.get("pagamento") or "").lower()
    if "din" in pg:
        payment_code = "DIN"
    elif "crédit" in pg or "credit" in pg or "cartao_credito" in pg:
        payment_code = "CRE"
    elif "déb" in pg or "deb" in pg or "cartao_debito" in pg:
        payment_code = "DEB"
    elif "vale" in pg:
        payment_code = "VALE"
    elif "pix" in pg:
        payment_code = "PARTNER_PAYMENT"
    elif "online" in pg:
        payment_code = "PARTNER_PAYMENT_ONLINE"

    is_takeout = (data.get("tipo_entrega") or "").lower() == "retirada"

    order_method: Dict[str, Any] = {
        "mode": "TAKEOUT" if is_takeout else "DELIVERY",
        "scheduled": not is_takeout,
        "delivery_date_time": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }

    if not is_takeout:
        order_method["delivery_by"] = "RESTAURANT"
        order_method["delivery_fee"] = _num(data.get("taxa_entrega"))

    telefone_bruto = _to_str(data.get("telefone") or data.get("session_id") or "")
    telefone_formatado = normalize_phone(telefone_bruto)

    nome_cliente = (data.get("nome") or "Cliente").strip()
    numero_rua = (data.get("numero") or "S/N").strip()

    notes_pedido = ""
    if is_takeout and data.get("horario_retirada"):
        notes_pedido = f"Pedido agendado para retirada às {data.get('horario_retirada')}"

    json_saipos: Dict[str, Any] = {
        "order_id": order_id,
        "display_id": display_id,
        "cod_store": data.get("cod_store") or cod_store,
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "notes": notes_pedido,
        "total_increase": 0,
        "total_discount": _num(data.get("desconto")),
        "total_amount": _num(data.get("total")),
        "customer": {
            "id": _to_str(data.get("session_id") or data.get("telefone") or order_id),
            "name": nome_cliente,
            "phone": telefone_formatado,
            "document_number": "",
        },
        "order_method": order_method,
        "items": pedidos_array,
        "payment_types": [
            {
                "code": payment_code,
                "amount": _num(data.get("total")),
                "change_for": _num(data.get("troco_para")),
            }
        ],
    }

    if not is_takeout:
        json_saipos["delivery_address"] = {
            "country": "BR",
            "state": "SC",
            "city": data.get("cidade") or "Itajaí",
            "district": data.get("bairro") or "",
            "street_name": data.get("rua") or "",
            "street_number": numero_rua,
            "postal_code": (data.get("cep") or "").replace("-", ""),
            "reference": "",
            "complement": data.get("complemento") or "",
            "coordinates": {"latitude": -26.9101, "longitude": -48.6705},
        }

    return json_saipos


class OrderService:
    def __init__(self, db, saipos_client) -> None:
        self.db = db
        self.saipos_client = saipos_client

    def quote_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("JSON") if isinstance(payload, dict) and payload.get("JSON") else payload
        if not isinstance(data, dict):
            return {"error": "payload_invalid"}

        indice = crud.fetch_menu_search_index(self.db)
        itens_mapeados, erros = mapear_itens(data, indice)
        if erros:
            return {"error": "item_not_found", "details": erros}

        taxa_entrega = _num(data.get("taxa_entrega") or 0)
        desconto = _num(data.get("desconto") or 0)

        subtotal = 0.0
        itens_saida: list[Dict[str, Any]] = []
        for item in itens_mapeados:
            item_total = (item.get("valor_unitario") or 0) * (item.get("quantidade") or 1)
            adicionais_saida = []
            for ad in item.get("adicionais", []):
                item_total += (ad.get("valor_unitario") or 0) * (ad.get("quantidade") or 1) * (item.get("quantidade") or 1)
                adicionais_saida.append(
                    {
                        "nome": ad.get("descricao") or "",
                        "qtd": ad.get("quantidade") or 1,
                        "valor_unitario": ad.get("valor_unitario") or 0,
                    }
                )
            subtotal += item_total
            itens_saida.append(
                {
                    "nome": item.get("descricao") or "",
                    "qtd": item.get("quantidade") or 1,
                    "valor_unitario": item.get("valor_unitario") or 0,
                    "obs": item.get("observacao") or "",
                    "adicionais": adicionais_saida,
                }
            )

        total = subtotal + taxa_entrega - desconto

        normalized = dict(data)
        normalized["itens"] = itens_saida
        normalized["taxa_entrega"] = taxa_entrega
        normalized["desconto"] = desconto
        normalized["subtotal"] = float(f"{subtotal:.2f}")
        normalized["total"] = float(f"{total:.2f}")

        session_id = (data.get("dados_cliente") or {}).get("telefone") or data.get("telefone") or ""
        telefone = (data.get("dados_cliente") or {}).get("telefone") or data.get("telefone") or ""
        trace_id = payload.get("trace_id") if isinstance(payload, dict) else None
        try:
            crud.insert_order_audit_quote(
                self.db,
                session_id=session_id,
                telefone=telefone,
                trace_id=trace_id,
                agent_order_json=data,
                quoted_json=normalized,
            )
        except Exception:
            logger.warning("order_audit_quote_insert_failed", exc_info=True)

        return {"JSON": normalized}

    def process_order(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        data = payload.get("JSON") if isinstance(payload, dict) and payload.get("JSON") else payload
        if not isinstance(data, dict):
            return {"error": "payload_invalid"}

        raw_session_id = (data.get("dados_cliente") or {}).get("telefone") or data.get("telefone") or ""
        raw_telefone = (data.get("dados_cliente") or {}).get("telefone") or data.get("telefone") or ""
        trace_id = payload.get("trace_id") if isinstance(payload, dict) else None
        audit_id = None
        try:
            audit_id = crud.insert_order_audit_raw(
                self.db,
                session_id=raw_session_id,
                telefone=raw_telefone,
                trace_id=trace_id,
                agent_order_json=data,
            )
        except Exception:
            logger.warning("order_audit_raw_insert_failed", exc_info=True)

        try:
            indice = crud.fetch_menu_search_index(self.db)
            payload_saipos, erros = build_payload_saipos(data, indice)
            json_saipos = formatar_json_saipos(payload_saipos)

            if audit_id:
                try:
                    crud.update_order_audit_saipos(
                        self.db,
                        audit_id=audit_id,
                        status="prepared",
                        saipos_payload_json=json_saipos,
                        error=None,
                    )
                except Exception:
                    logger.warning("order_audit_update_failed", exc_info=True)
        except Exception as exc:
            if audit_id:
                try:
                    crud.update_order_audit_saipos(
                        self.db,
                        audit_id=audit_id,
                        status="failed",
                        saipos_payload_json=None,
                        error=str(exc),
                    )
                except Exception:
                    logger.warning("order_audit_update_failed", exc_info=True)
            raise

        if settings.saipos_dry_run:
            response = {"status": "dry_run", "message": "Saipos envio desativado em testes."}
        else:
            response = self.saipos_client.send_order(json_saipos)

        crud.insert_order(
            self.db,
            order_id=json_saipos.get("order_id"),
            telefone=payload_saipos.get("telefone") or "",
            status="created",
            payload=json_saipos,
            response=response,
            cod_store=json_saipos.get("cod_store") or "",
        )

        session_id = payload_saipos.get("session_id") or payload_saipos.get("telefone")
        if session_id:
            crud.update_active_session_finished(self.db, session_id)

        return {
            "payload": json_saipos,
            "response": response,
            "erros": erros or None,
        }

    def cancel_order(self, order_id: str) -> Dict[str, Any]:
        order = crud.get_order(self.db, order_id)
        cod_store = settings.saipos_cod_store or (order.get("cod_store") if order else "")
        response = self.saipos_client.cancel_order(cod_store=cod_store, order_id=order_id)
        crud.update_order_status(self.db, order_id, "cancelled", response=response)
        return {"order_id": order_id, "response": response}
