"""Matcher de adicionais para produtos."""

from __future__ import annotations

import logging
import re
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from app.services.order_interpreter.models import MatchedAdditional, MatchedProduct

logger = logging.getLogger(__name__)

# Configurações
FUZZY_THRESHOLD = 70  # Threshold mais baixo para adicionais (nomes mais curtos)
MAX_SUGGESTIONS = 2


def _generate_fingerprint(text: str) -> str:
    """Gera fingerprint para comparação."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    clean = "".join(ch for ch in without_accents if ch.isalnum())
    return clean.lower()


def _clean_additional_name(name: str) -> str:
    """Limpa o nome do adicional removendo prefixos."""
    # Remove prefixos como "Adicionais ", "Adicionais - ", etc.
    patterns = [
        r"^adicionais?\s*[-–]?\s*",
        r"^acr[ée]scimos?\s*[-–]?\s*",
        r"^extras?\s*[-–]?\s*",
        r"^no prato\s*[-–]?\s*",
    ]
    result = name
    for pattern in patterns:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)
    return result.strip()


class AdditionalMatcher:
    """Matcher de adicionais contra os adicionais disponíveis do produto."""

    def __init__(self, db=None):
        """
        Inicializa o matcher.

        Args:
            db: Conexão com banco de dados (opcional, para uso futuro)
        """
        self.db = db

    def _exact_match(
        self, texto: str, additionals: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Tenta match exato por fingerprint."""
        fingerprint = _generate_fingerprint(texto)

        for additional in additionals:
            # Verifica fingerprint do banco
            if additional.get("fingerprint") == fingerprint:
                return additional

            # Verifica fingerprint do nome limpo
            nome_limpo = _clean_additional_name(additional.get("nome") or "")
            if _generate_fingerprint(nome_limpo) == fingerprint:
                return additional

        return None

    def _fuzzy_match(
        self, texto: str, additionals: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], float, List[str]]:
        """
        Tenta match usando fuzzy matching.

        Returns:
            tuple: (adicional_match, score, lista_sugestoes)
        """
        if not additionals:
            return None, 0, []

        # Prepara lista de nomes limpos para comparação
        clean_names = []
        name_to_additional = {}

        for add in additionals:
            original_name = add.get("nome") or ""
            clean_name = _clean_additional_name(original_name)
            if clean_name:
                clean_names.append(clean_name)
                name_to_additional[clean_name] = add

        if not clean_names:
            return None, 0, []

        # Fuzzy match
        results = process.extract(
            texto,
            clean_names,
            scorer=fuzz.token_sort_ratio,
            limit=MAX_SUGGESTIONS + 1
        )

        if not results:
            return None, 0, []

        best_name, best_score, _ = results[0]

        # Coleta sugestões
        sugestoes = [name for name, score, _ in results[1:MAX_SUGGESTIONS + 1] if score >= 50]

        if best_score >= FUZZY_THRESHOLD:
            return name_to_additional.get(best_name), best_score, sugestoes

        # Se não atingiu threshold, adiciona o melhor como sugestão
        if best_name and best_name not in sugestoes:
            sugestoes.insert(0, best_name)

        return None, best_score, sugestoes[:MAX_SUGGESTIONS]

    def match_additional(
        self, texto_adicional: str, product: MatchedProduct
    ) -> Tuple[Optional[MatchedAdditional], List[str]]:
        """
        Encontra o adicional mais próximo do texto.

        Args:
            texto_adicional: Nome do adicional digitado pelo cliente
            product: Produto ao qual o adicional pertence

        Returns:
            tuple: (MatchedAdditional ou None, lista de sugestões)
        """
        additionals = product.adicionais_disponiveis

        if not additionals:
            logger.debug(f"Produto {product.nome} não tem adicionais disponíveis")
            return None, []

        # Camada 1: Match exato
        exact = self._exact_match(texto_adicional, additionals)
        if exact:
            return MatchedAdditional(
                pdv=exact.get("pdv") or "",
                nome=_clean_additional_name(exact.get("nome") or ""),
                preco=float(exact.get("preco") or 0),
                quantidade=1,
                score=100.0,
            ), []

        # Camada 2: Fuzzy match
        fuzzy_match, score, sugestoes = self._fuzzy_match(texto_adicional, additionals)
        if fuzzy_match:
            return MatchedAdditional(
                pdv=fuzzy_match.get("pdv") or "",
                nome=_clean_additional_name(fuzzy_match.get("nome") or ""),
                preco=float(fuzzy_match.get("preco") or 0),
                quantidade=1,
                score=score,
            ), sugestoes

        return None, sugestoes

    def match_all(
        self, adicionais_texto: List[str], product: MatchedProduct
    ) -> Tuple[List[MatchedAdditional], List[Tuple[str, List[str]]]]:
        """
        Encontra todos os adicionais do texto.

        Args:
            adicionais_texto: Lista de nomes de adicionais do cliente
            product: Produto ao qual os adicionais pertencem

        Returns:
            tuple: (lista de adicionais válidos, lista de (adicional não encontrado, sugestões))
        """
        validos = []
        nao_encontrados = []

        for texto in adicionais_texto:
            matched, sugestoes = self.match_additional(texto, product)
            if matched:
                validos.append(matched)
            else:
                nao_encontrados.append((texto, sugestoes))

        return validos, nao_encontrados
