"""Matcher de produtos usando fuzzy matching."""

from __future__ import annotations

import logging
import unicodedata
from typing import Any, Dict, List, Optional, Tuple

from rapidfuzz import fuzz, process

from app.services.order_interpreter.models import MatchedProduct

logger = logging.getLogger(__name__)

# Configurações de threshold
FUZZY_THRESHOLD = 75  # Mínimo para considerar match válido
EXACT_MATCH_SCORE = 100
SUBSTRING_MATCH_SCORE = 85
MAX_SUGGESTIONS = 3


def _generate_fingerprint(text: str) -> str:
    """Gera fingerprint para comparação (sem acentos, lowercase, sem espaços)."""
    if not text:
        return ""
    normalized = unicodedata.normalize("NFKD", text)
    without_accents = "".join(ch for ch in normalized if not unicodedata.combining(ch))
    # Remove caracteres não alfanuméricos
    clean = "".join(ch for ch in without_accents if ch.isalnum())
    return clean.lower()


class MenuMatcher:
    """Matcher de produtos contra o cardápio usando fuzzy matching."""

    def __init__(self, db):
        """
        Inicializa o matcher.

        Args:
            db: Conexão com banco de dados
        """
        self.db = db
        self._menu_cache: Optional[List[Dict[str, Any]]] = None
        self._products_cache: Optional[List[Dict[str, Any]]] = None

    def _load_menu(self) -> List[Dict[str, Any]]:
        """Carrega o cardápio do banco de dados."""
        if self._menu_cache is not None:
            return self._menu_cache

        from app.db import crud
        self._menu_cache = list(crud.fetch_menu_search_index(self.db))
        return self._menu_cache

    def _get_products(self) -> List[Dict[str, Any]]:
        """Retorna apenas os produtos (não adicionais) do cardápio."""
        if self._products_cache is not None:
            return self._products_cache

        menu = self._load_menu()
        self._products_cache = [
            item for item in menu
            if item.get("item_type") == "product"
        ]
        return self._products_cache

    def _get_additionals_for_product(self, product_pdv: str) -> List[Dict[str, Any]]:
        """Retorna os adicionais disponíveis para um produto."""
        menu = self._load_menu()
        return [
            item for item in menu
            if item.get("item_type") == "addition" and item.get("parent_pdv") == product_pdv
        ]

    def _exact_match(self, texto: str, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Tenta match exato por fingerprint."""
        fingerprint = _generate_fingerprint(texto)
        for product in products:
            if product.get("fingerprint") == fingerprint:
                return product
        return None

    def _substring_match(self, texto: str, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Tenta match por substring (fingerprint do produto contido no texto)."""
        fingerprint = _generate_fingerprint(texto)
        candidatos = []

        for product in products:
            prod_fp = product.get("fingerprint") or ""
            if prod_fp and prod_fp in fingerprint:
                candidatos.append(product)

        if candidatos:
            # Retorna o mais específico (fingerprint mais longo)
            candidatos.sort(key=lambda x: len(x.get("fingerprint") or ""), reverse=True)
            return candidatos[0]

        return None

    def _fuzzy_match(
        self, texto: str, products: List[Dict[str, Any]]
    ) -> Tuple[Optional[Dict[str, Any]], float, List[str]]:
        """
        Tenta match usando fuzzy matching.

        Returns:
            tuple: (produto_match, score, lista_sugestoes)
        """
        if not products:
            return None, 0, []

        # Prepara lista de nomes para comparação
        product_names = [p.get("nome_original") or "" for p in products]

        # Usa token_sort_ratio para ser mais tolerante com ordem de palavras
        results = process.extract(
            texto,
            product_names,
            scorer=fuzz.token_sort_ratio,
            limit=MAX_SUGGESTIONS + 1
        )

        if not results:
            return None, 0, []

        # Melhor match
        best_name, best_score, best_idx = results[0]

        # Coleta sugestões (excluindo o melhor se for match válido)
        sugestoes = []
        for name, score, idx in results[1:MAX_SUGGESTIONS + 1]:
            if score >= 50:  # Só sugere se tiver alguma relevância
                sugestoes.append(name)

        if best_score >= FUZZY_THRESHOLD:
            # Encontra o produto correspondente
            for product in products:
                if product.get("nome_original") == best_name:
                    return product, best_score, sugestoes
            return None, best_score, sugestoes

        # Se não atingiu threshold, adiciona o melhor como sugestão
        if best_name and best_name not in sugestoes:
            sugestoes.insert(0, best_name)

        return None, best_score, sugestoes[:MAX_SUGGESTIONS]

    def match(self, texto_produto: str) -> Tuple[Optional[MatchedProduct], List[str]]:
        """
        Encontra o produto do cardápio mais próximo do texto.

        Args:
            texto_produto: Nome do produto digitado pelo cliente

        Returns:
            tuple: (MatchedProduct ou None, lista de sugestões)
        """
        products = self._get_products()

        if not products:
            logger.warning("Cardápio vazio ou não carregado")
            return None, []

        # Camada 1: Match exato por fingerprint
        exact = self._exact_match(texto_produto, products)
        if exact:
            additionals = self._get_additionals_for_product(exact.get("pdv") or "")
            return MatchedProduct(
                pdv=exact.get("pdv") or "",
                nome=exact.get("nome_original") or "",
                preco=float(exact.get("price") or 0),
                score=EXACT_MATCH_SCORE,
                adicionais_disponiveis=[
                    {
                        "pdv": a.get("pdv"),
                        "nome": a.get("nome_original"),
                        "fingerprint": a.get("fingerprint"),
                        "preco": float(a.get("price") or 0)
                    }
                    for a in additionals
                ],
            ), []

        # Camada 2: Match por substring
        substring = self._substring_match(texto_produto, products)
        if substring:
            additionals = self._get_additionals_for_product(substring.get("pdv") or "")
            return MatchedProduct(
                pdv=substring.get("pdv") or "",
                nome=substring.get("nome_original") or "",
                preco=float(substring.get("price") or 0),
                score=SUBSTRING_MATCH_SCORE,
                adicionais_disponiveis=[
                    {
                        "pdv": a.get("pdv"),
                        "nome": a.get("nome_original"),
                        "fingerprint": a.get("fingerprint"),
                        "preco": float(a.get("price") or 0)
                    }
                    for a in additionals
                ],
            ), []

        # Camada 3: Fuzzy match
        fuzzy_match, score, sugestoes = self._fuzzy_match(texto_produto, products)
        if fuzzy_match:
            additionals = self._get_additionals_for_product(fuzzy_match.get("pdv") or "")
            return MatchedProduct(
                pdv=fuzzy_match.get("pdv") or "",
                nome=fuzzy_match.get("nome_original") or "",
                preco=float(fuzzy_match.get("price") or 0),
                score=score,
                adicionais_disponiveis=[
                    {
                        "pdv": a.get("pdv"),
                        "nome": a.get("nome_original"),
                        "fingerprint": a.get("fingerprint"),
                        "preco": float(a.get("price") or 0)
                    }
                    for a in additionals
                ],
            ), sugestoes

        # Não encontrou - retorna sugestões
        return None, sugestoes

    def clear_cache(self) -> None:
        """Limpa o cache do cardápio."""
        self._menu_cache = None
        self._products_cache = None
