"""Parser para extrair itens de pedidos do texto livre do cliente."""

from __future__ import annotations

import re
import unicodedata
from typing import List

from app.services.order_interpreter.models import ParsedItem


def _normalize_text(text: str) -> str:
    """Normaliza texto removendo acentos e convertendo para minúsculas."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    return without_accents.lower().strip()


def _split_into_items(text: str) -> List[str]:
    """Divide o texto em itens individuais."""
    # Primeiro, divide por quebras de linha
    lines = text.split("\n")

    items = []
    for line in lines:
        # Normaliza espaços apenas dentro da linha (não entre linhas)
        line = re.sub(r"\s+", " ", line.strip())
        if not line:
            continue

        # Divide por vírgula seguida de número ou "e" seguido de número
        # Ex: "2 x galinha, 1 coca" ou "2 x galinha e 1 coca"
        parts = re.split(r",\s*(?=\d)|(?<=[a-záéíóúãõ])\s+e\s+(?=\d)", line, flags=re.IGNORECASE)

        for part in parts:
            part = part.strip()
            if part:
                items.append(part)

    return items


def _extract_quantity(text: str) -> tuple[int, str]:
    """Extrai quantidade do início do texto."""
    # Padrões: "2 x galinha", "2x galinha", "2 galinha", "1"
    match = re.match(r"^(\d+)\s*[xX]?\s*", text)
    if match:
        qty = int(match.group(1))
        remaining = text[match.end():].strip()
        return qty, remaining
    return 1, text


def _extract_additionals(text: str) -> tuple[str, List[str]]:
    """Extrai adicionais do texto (padrão 'com X e Y')."""
    adicionais = []

    # Padrão: "com bacon e milho" ou "com bacon, milho"
    match = re.search(r"\s+com\s+(.+?)(?:\s+(?:sem|bem|mal|cortado|aberto|no prato)|$)", text, re.IGNORECASE)
    if match:
        adicional_text = match.group(1)
        # Remove o trecho do texto original
        text = text[:match.start()] + text[match.end():]

        # Divide adicionais por "e" ou ","
        parts = re.split(r"\s+e\s+|,\s*", adicional_text)
        for part in parts:
            part = part.strip()
            if part and not _is_observation_keyword(part):
                adicionais.append(part)

    return text.strip(), adicionais


def _is_observation_keyword(text: str) -> bool:
    """Verifica se o texto é uma palavra-chave de observação."""
    keywords = [
        "bem passado", "mal passado", "ao ponto",
        "cortado ao meio", "cortado", "sem",
        "aberto", "no prato"
    ]
    text_lower = text.lower().strip()
    return any(kw in text_lower for kw in keywords)


def _extract_observations(text: str) -> tuple[str, List[str]]:
    """Extrai observações do texto (sem X, bem passado, cortado ao meio, etc.)."""
    observacoes = []

    # Padrão: "sem X"
    sem_matches = re.findall(r"\s+sem\s+(\w+)", text, re.IGNORECASE)
    for match in sem_matches:
        observacoes.append(f"sem {match}")
    text = re.sub(r"\s+sem\s+\w+", "", text, flags=re.IGNORECASE)

    # Padrões de observação específicos
    obs_patterns = [
        (r"\s+bem\s+passado", "bem passado"),
        (r"\s+mal\s+passado", "mal passado"),
        (r"\s+ao\s+ponto", "ao ponto"),
        (r"\s+cortado\s+ao\s+meio", "cortado ao meio"),
        (r"\s+cortado", "cortado"),
    ]

    for pattern, obs in obs_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            observacoes.append(obs)
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip(), observacoes


def _extract_modifiers(text: str) -> tuple[str, List[str]]:
    """Extrai modificadores como 'careca', 'completo', 'no prato', etc."""
    modificadores = []

    # Lista de modificadores conhecidos
    modifier_patterns = [
        (r"\s+careca\b", "careca"),
        (r"\s+completo\b", "completo"),
        (r"\s+no\s+prato\b", "no prato"),
        (r"\s+aberto\s+no\s+prato\b", "no prato"),
        (r"\s+aberto\b", "no prato"),
    ]

    for pattern, mod in modifier_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            modificadores.append(mod)
            text = re.sub(pattern, "", text, flags=re.IGNORECASE)

    return text.strip(), modificadores


class OrderParser:
    """Parser para extrair itens de pedidos do texto livre."""

    def parse(self, texto_pedido: str) -> List[ParsedItem]:
        """
        Transforma texto livre em lista de ParsedItem.

        Exemplo:
            Input: "2 x galinha careca com bacon e milho cortado ao meio"
            Output: ParsedItem(
                texto_original="2 x galinha careca com bacon e milho cortado ao meio",
                quantidade=2,
                texto_produto="galinha",
                modificadores=["careca"],
                adicionais_texto=["bacon", "milho"],
                observacoes_texto=["cortado ao meio"]
            )
        """
        if not texto_pedido or not texto_pedido.strip():
            return []

        items_text = _split_into_items(texto_pedido)
        parsed_items = []

        for item_text in items_text:
            original = item_text

            # 1. Extrai quantidade
            quantidade, remaining = _extract_quantity(item_text)

            # 2. Extrai observações primeiro (sem X, bem passado, etc.)
            remaining, observacoes = _extract_observations(remaining)

            # 3. Extrai adicionais (com X e Y)
            remaining, adicionais = _extract_additionals(remaining)

            # 4. Extrai modificadores (careca, completo, no prato)
            remaining, modificadores = _extract_modifiers(remaining)

            # 5. O que sobrou é o nome do produto
            texto_produto = remaining.strip()

            # Remove artigos e preposições do início
            texto_produto = re.sub(r"^(um|uma|o|a|os|as|de|do|da)\s+", "", texto_produto, flags=re.IGNORECASE)

            if texto_produto:
                parsed_items.append(
                    ParsedItem(
                        texto_original=original,
                        quantidade=quantidade,
                        texto_produto=texto_produto,
                        modificadores=modificadores,
                        adicionais_texto=adicionais,
                        observacoes_texto=observacoes,
                    )
                )

        return parsed_items
