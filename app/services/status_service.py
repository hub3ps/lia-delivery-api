from __future__ import annotations

from typing import Any, Dict, Optional

from app.db import crud
from app.services.evolution_client import EvolutionClient
from app.utils.phone import normalize_phone
from app.settings import settings


STATUS_MESSAGES = {
    "CONFIRMED": "Seu pedido foi confirmado com sucesso e já está na fila da cozinha. Em breve ele começa a ser preparado!",
    "READY_TO_DELIVER": "Boa notícia, {nome}! 🍔 Seu pedido já ficou pronto e agora está aguardando o entregador. Assim que sair, te aviso!",
    "DISPATCHED": "🚴‍♂️ Opa, {nome}! Seu pedido acabou de sair para entrega. Logo logo chega aí na sua casa, pode ir preparando o apetite! 😋",
    "CONCLUDED": "{nome}, acabamos de confirmar que seu pedido foi entregue ✅. Esperamos que você aproveite muito a refeição! Obrigado por pedir com a gente. 💛",
    "CANCELLED": "{nome}. 😔 Seu pedido foi cancelado. Se quiser, pode falar com a gente aqui para entendermos melhor ou fazer um novo pedido a qualquer momento. Estamos à disposição!",
}


class StatusService:
    def __init__(self, db, evolution_client: EvolutionClient) -> None:
        self.db = db
        self.evolution_client = evolution_client

    def process_event(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        body = payload.get("body") if isinstance(payload, dict) else None
        event = (body or payload).get("event") if isinstance(body or payload, dict) else None
        order_id = (body or payload).get("order_id") if isinstance(body or payload, dict) else None

        nome = (body or payload).get("nome") or (body or {}).get("customer", {}).get("name")
        telefone = (body or payload).get("telefone") or (body or {}).get("customer", {}).get("phone")

        if not telefone and order_id:
            order = crud.get_order(self.db, order_id)
            if order:
                telefone = order.get("telefone")
                if not nome:
                    payload_order = order.get("payload") or {}
                    nome = payload_order.get("customer", {}).get("name") or payload_order.get("nome")

        telefone = normalize_phone(telefone)
        nome = nome or "Cliente"

        if event:
            crud.update_order_status(self.db, order_id or "", event, response=payload)

        message_template = STATUS_MESSAGES.get(event)
        sent = False
        if message_template and telefone:
            text = message_template.format(nome=nome)
            self.evolution_client.send_text(settings.evolution_instance, telefone, text)
            sent = True

        return {"event": event, "sent": sent}
