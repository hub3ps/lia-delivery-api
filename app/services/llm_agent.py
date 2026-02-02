from __future__ import annotations

import json
import re
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from collections.abc import Mapping

import httpx

from app.settings import settings
from app.db import crud
from app.services.geocode_service import GeocodeService
from app.services.menu_service import MenuService
from app.services.order_service import OrderService
from app.services.order_interpreter import OrderInterpreterService


def _strip_markdown_json(text: str) -> str:
    cleaned = text.replace("```json", "").replace("```", "").strip()
    first_brace = cleaned.find("{")
    first_bracket = cleaned.find("[")
    start_index = -1
    end_index = -1
    if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
        start_index = first_brace
        end_index = cleaned.rfind("}")
    elif first_bracket != -1:
        start_index = first_bracket
        end_index = cleaned.rfind("]")
    if start_index != -1 and end_index != -1:
        cleaned = cleaned[start_index : end_index + 1]
    return cleaned


def _to_jsonable(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {key: _to_jsonable(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_to_jsonable(item) for item in obj]
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    if isinstance(obj, Decimal):
        return float(obj)
    return obj


def _json_dumps_safe(obj: Any) -> str:
    return json.dumps(_to_jsonable(obj), ensure_ascii=False)


def calcular_totais(query: Any) -> str:
    data = query or {}

    if isinstance(data, str):
        try:
            clean = _strip_markdown_json(data)
            data = json.loads(clean)
        except Exception as exc:
            erro = {
                "error": "JSON inválido ou mal formatado recebido do agente",
                "detalhe": str(exc),
                "recebido_bruto": query,
            }
            return json.dumps(erro, ensure_ascii=False)

    itens = []
    taxa_entrega = 0.0
    desconto = 0.0

    if isinstance(data, list):
        itens = data
        if isinstance(query, str):
            taxa_match = re.search(r"taxa_entrega\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)", query, re.I)
            if taxa_match:
                taxa_entrega = float(taxa_match.group(1).replace(",", "."))
            desc_match = re.search(r"desconto\s*[:=]\s*([0-9]+(?:[.,][0-9]+)?)", query, re.I)
            if desc_match:
                desconto = float(desc_match.group(1).replace(",", "."))
    elif isinstance(data, dict):
        itens = data.get("itens") if isinstance(data.get("itens"), list) else []
        taxa_entrega = float(str(data.get("taxa_entrega", 0)).replace(",", "."))
        desconto = float(str(data.get("desconto", 0)).replace(",", "."))

    subtotal = 0.0
    itens_calculados = []

    for item in itens:
        qtd = float(str(item.get("qtd", item.get("quantidade", 1))).replace(",", "."))
        valor_unitario = float(str(item.get("valor_unitario", item.get("valor", 0))).replace(",", "."))
        adicionais_orig = item.get("adicionais") if isinstance(item.get("adicionais"), list) else []

        total_item = qtd * valor_unitario
        adicionais_calculados = []

        for add in adicionais_orig:
            add_qtd = float(str(add.get("qtd", add.get("quantidade", 1))).replace(",", "."))
            add_valor = float(str(add.get("valor_unitario", add.get("valor", 0))).replace(",", "."))
            total_ad = add_qtd * add_valor
            total_item += total_ad
            adicionais_calculados.append(
                {
                    **add,
                    "qtd": add_qtd,
                    "valor_unitario": add_valor,
                    "total": total_ad,
                }
            )

        subtotal += total_item
        itens_calculados.append(
            {
                **item,
                "qtd": qtd,
                "valor_unitario": valor_unitario,
                "adicionais": adicionais_calculados,
                "total": total_item,
            }
        )

    total = subtotal + taxa_entrega - desconto
    result = {
        "status": "sucesso",
        "itens": itens_calculados,
        "subtotal": f"{subtotal:.2f}",
        "taxa_entrega": f"{taxa_entrega:.2f}",
        "desconto": f"{desconto:.2f}",
        "total_final": f"{total:.2f}",
    }
    return _json_dumps_safe(result)


def render_atendente_prompt(base_prompt: str, ctx: Dict[str, Any]) -> str:
    mapping = {
        "{{ $json.nome_restaurante || 'Marcio Lanches & Pizzas' }}": ctx.get("nome_restaurante") or "Marcio Lanches & Pizzas",
        "{{ $json.horario }}": ctx.get("horario") or "",
        "{{ $json.telefone }}": ctx.get("telefone") or "",
        "{{ $json.historico.name || \"não informado\" }}": ctx.get("historico", {}).get("name") or "não informado",
        "{{ $json.historico.total_orders || 0 }}": str(ctx.get("historico", {}).get("total_orders") or 0),
        "{{ $json.historico.last_order_items || \"nenhum\" }}": ctx.get("historico", {}).get("last_order_items") or "nenhum",
        "{{ $json.historico.last_payment_method || \"não informado\" }}": ctx.get("historico", {}).get("last_payment_method") or "não informado",
        "{{ $json.historico.street || \"não possui\" }}": ctx.get("historico", {}).get("street") or "não possui",
        "{{ $json.historico.number || \"\" }}": ctx.get("historico", {}).get("number") or "",
        "{{ $json.historico.district || \"\" }}": ctx.get("historico", {}).get("district") or "",
        "{{ $json.historico.city || \"\" }}": ctx.get("historico", {}).get("city") or "",
        "{{ $json.historico.postal_code || \"não possui\" }}": ctx.get("historico", {}).get("postal_code") or "não possui",
        "{{ $json.historico.complement || \"não informado\" }}": ctx.get("historico", {}).get("complement") or "não informado",
    }
    rendered = base_prompt
    for k, v in mapping.items():
        rendered = rendered.replace(k, str(v))
    return rendered


def render_followup_prompt(base_prompt: str) -> str:
    return base_prompt


def _history_rows_to_messages(rows: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    for row in rows:
        raw = row.get("message")
        data = None
        if isinstance(raw, dict):
            data = raw
        elif isinstance(raw, str):
            try:
                data = json.loads(raw)
            except Exception:
                data = None
        if not isinstance(data, dict):
            continue
        role = data.get("type")
        content = None
        payload = data.get("data") if isinstance(data.get("data"), dict) else {}
        if payload:
            content = payload.get("content")
        if not content:
            continue
        if role == "human":
            messages.append({"role": "user", "content": content})
        elif role == "ai":
            messages.append({"role": "assistant", "content": content})
    return messages


def _openai_chat(messages: List[Dict[str, Any]], tools: Optional[List[Dict]] = None, tool_choice: str = "auto") -> Dict[str, Any]:
    url = "https://api.openai.com/v1/chat/completions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    payload: Dict[str, Any] = {
        "model": settings.openai_model_chat,
        "messages": messages,
        "temperature": 0.3,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = tool_choice
    with httpx.Client(timeout=90) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json()


def _openai_transcribe(audio_bytes: bytes) -> str:
    url = "https://api.openai.com/v1/audio/transcriptions"
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}
    files = {
        "file": ("audio.mp3", audio_bytes, "audio/mpeg"),
        "model": (None, settings.openai_model_transcribe),
    }
    with httpx.Client(timeout=120) as client:
        resp = client.post(url, headers=headers, files=files)
        resp.raise_for_status()
        data = resp.json()
    return data.get("text") or ""


class LLMAgent:
    def __init__(self, db, order_service: OrderService, menu_service: MenuService, geocode: GeocodeService, prompt_text: str, followup_prompt: str) -> None:
        self.db = db
        self.order_service = order_service
        self.menu_service = menu_service
        self.geocode = geocode
        self.prompt_text = prompt_text
        self.followup_prompt = followup_prompt
        self.order_interpreter = OrderInterpreterService(db)

    def _tools(self) -> List[Dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "stages",
                    "description": "Retorna regras de interpretação para uma etapa específica.",
                    "parameters": {"type": "object", "properties": {"stage": {"type": "string"}}, "required": ["stage"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "cardapio",
                    "description": "Retorna todos os itens do cardápio.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "taxa_entrega",
                    "description": "Consulta taxa de entrega por bairro.",
                    "parameters": {"type": "object", "properties": {"bairro": {"type": "string"}}, "required": ["bairro"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "maps",
                    "description": "Valida endereço via Google Maps (cidade/UF adicionadas automaticamente).",
                    "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "calcular_orcamento",
                    "description": "Calcula orçamento do pedido no backend e retorna o JSON precificado.",
                    "parameters": {"type": "object", "properties": {"JSON": {"type": "object"}}, "required": ["JSON"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "enviar_pedido",
                    "description": "Envia um novo pedido para a cozinha.",
                    "parameters": {"type": "object", "properties": {"JSON": {"type": "object"}}, "required": ["JSON"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "cancelar_pedido",
                    "description": "Cancela um pedido existente.",
                    "parameters": {"type": "object", "properties": {"order_id": {"type": "string"}}, "required": ["order_id"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "validar_endereco",
                    "description": "Valida endereço e retorna componentes.",
                    "parameters": {"type": "object", "properties": {"texto": {"type": "string"}}, "required": ["texto"]},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "atualizar_cardapio",
                    "description": "Sincroniza o cardápio com Saipos.",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "interpretar_pedido",
                    "description": "OBRIGATÓRIO: Interpreta o texto do pedido do cliente. Aplica regras de gírias (ex: 'careca' = sem salada), valida contra o cardápio, e retorna itens estruturados com preços. SEMPRE use esta tool ao receber itens do pedido antes de confirmar com o cliente.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "texto_pedido": {
                                "type": "string",
                                "description": "O texto completo que o cliente enviou contendo os itens do pedido"
                            }
                        },
                        "required": ["texto_pedido"]
                    },
                },
            },
        ]

    def _execute_tool(self, name: str, args: Dict[str, Any]) -> Any:
        if name == "stages":
            return crud.fetch_stage_rules(self.db, args.get("stage") or "")
        if name == "cardapio":
            return crud.fetch_cardapio(self.db)
        if name == "taxa_entrega":
            return crud.fetch_delivery_fee(self.db, args.get("bairro") or "")
        if name == "maps":
            return self.geocode.geocode(args.get("query") or "")
        if name == "calcular_orcamento":
            return self.order_service.quote_order(args)
        if name == "enviar_pedido":
            return self.order_service.process_order(args.get("JSON") or {})
        if name == "cancelar_pedido":
            return self.order_service.cancel_order(args.get("order_id") or "")
        if name == "validar_endereco":
            return self.geocode.geocode(args.get("texto") or "")
        if name == "atualizar_cardapio":
            return self.menu_service.sync_menu()
        if name == "interpretar_pedido":
            return self.order_interpreter.interpret_to_dict(args.get("texto_pedido") or "")
        return {"error": f"tool_not_found: {name}"}

    def run(self, message: str, telefone: str, horario: str, historico: Dict[str, Any]) -> str:
        base = self.prompt_text
        prompt = render_atendente_prompt(
            base,
            {
                "telefone": telefone,
                "horario": horario,
                "historico": historico or {},
                "nome_restaurante": settings.restaurant_name,
            },
        )
        messages: List[Dict[str, Any]] = [{"role": "system", "content": prompt}]

        try:
            rows = crud.fetch_chat_history(self.db, telefone, limit=20)
            history_msgs = _history_rows_to_messages(list(reversed(rows)))
            messages.extend(history_msgs)
        except Exception:
            pass

        messages.append({"role": "user", "content": message})
        tools = self._tools()

        for _ in range(6):
            data = _openai_chat(messages, tools=tools, tool_choice="auto")
            msg = data["choices"][0]["message"]
            tool_calls = msg.get("tool_calls")
            if tool_calls:
                messages.append({"role": "assistant", "tool_calls": tool_calls})
                for call in tool_calls:
                    name = call["function"]["name"]
                    args_str = call["function"].get("arguments") or "{}"
                    try:
                        args = json.loads(args_str)
                    except Exception:
                        args = {}
                    result = self._execute_tool(name, args)
                    messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": call["id"],
                            "content": _json_dumps_safe(result),
                        }
                    )
                continue
            return msg.get("content") or ""
        return ""

    def run_followup(self, last_message: str, telefone: str, horario: str, tipo: str) -> str:
        prompt = render_followup_prompt(self.followup_prompt)
        messages: List[Dict[str, Any]] = [
            {"role": "system", "content": prompt},
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "mensagem": last_message,
                        "telefone": telefone,
                        "horario": horario,
                        "tipo": tipo,
                    },
                    ensure_ascii=False,
                ),
            },
        ]
        data = _openai_chat(messages)
        msg = data["choices"][0]["message"]
        return msg.get("content") or ""

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        if not settings.openai_api_key:
            return ""
        return _openai_transcribe(audio_bytes)
