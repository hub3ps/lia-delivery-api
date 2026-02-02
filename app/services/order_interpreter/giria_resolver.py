"""Resolver de gírias e normalizações para pedidos."""

from __future__ import annotations

import re
import logging
from typing import Any, Dict, List, Optional

from app.services.order_interpreter.models import ParsedItem, ResolvedItem

logger = logging.getLogger(__name__)


# Gírias conhecidas e suas transformações
# Tipo: "observacao" = adiciona em observações
# Tipo: "sufixo_produto" = concatena ao nome do produto
# Tipo: "ignorar" = remove sem fazer nada
GIRIAS_PADRAO: Dict[str, Dict[str, Any]] = {
    "careca": {"tipo": "observacao", "valor": "sem salada"},
    "completo": {"tipo": "ignorar", "valor": None},
    "no prato": {"tipo": "sufixo_produto", "valor": " no Prato"},
    "aberto": {"tipo": "sufixo_produto", "valor": " no Prato"},
}

# Normalizações de tamanho/volume
NORMALIZACOES: Dict[str, str] = {
    "2l": "2 Litros",
    "2 l": "2 Litros",
    "2 litro": "2 Litros",
    "2 litros": "2 Litros",
    "1l": "1 Litro",
    "1 l": "1 Litro",
    "1 litro": "1 Litro",
    "600ml": "600ml",
    "600 ml": "600ml",
    "350ml": "350ml",
    "350 ml": "350ml",
    "latinha": "Lata",
    "lata": "Lata",
    "1/4": "(1/4 Porção)",
    "um quarto": "(1/4 Porção)",
    "meia": "(Meia Porção)",
    "meia porcao": "(Meia Porção)",
    "meia porção": "(Meia Porção)",
    "pequena": "(1/4 Porção)",
    "pequeno": "(1/4 Porção)",
    "grande": "(Porção)",
    "inteira": "(Porção)",
}

# Prefixos de produtos que devem ser padronizados
PREFIXOS_PRODUTO: Dict[str, str] = {
    "x ": "X ",
    "x-": "X ",
    "xis ": "X ",
}


class GiriaResolver:
    """Resolve gírias e aplica normalizações aos itens parseados."""

    def __init__(self, db=None):
        """
        Inicializa o resolver.

        Args:
            db: Conexão com banco de dados (opcional, para carregar regras dinâmicas)
        """
        self.db = db
        self._rules_cache: Optional[Dict[str, Any]] = None

    def _load_rules_from_db(self) -> Dict[str, Any]:
        """Carrega regras de interpretação do banco de dados."""
        if self._rules_cache is not None:
            return self._rules_cache

        if not self.db:
            return {}

        try:
            from app.db import crud
            result = crud.fetch_stage_rules(self.db, "interpretacao")
            if result:
                self._rules_cache = result
                return result
        except Exception as e:
            logger.warning(f"Erro ao carregar regras do banco: {e}")

        return {}

    def _apply_girias(self, item: ParsedItem) -> tuple[str, List[str]]:
        """
        Aplica transformações de gírias.

        Returns:
            tuple: (produto_modificado, observacoes_adicionais)
        """
        produto = item.texto_produto
        observacoes_adicionais = []

        for modificador in item.modificadores:
            mod_lower = modificador.lower()
            if mod_lower in GIRIAS_PADRAO:
                regra = GIRIAS_PADRAO[mod_lower]
                tipo = regra["tipo"]
                valor = regra["valor"]

                if tipo == "observacao" and valor:
                    observacoes_adicionais.append(valor)
                elif tipo == "sufixo_produto" and valor:
                    produto = produto + valor
                # tipo "ignorar" não faz nada

        return produto, observacoes_adicionais

    def _normalize_product_name(self, produto: str) -> str:
        """Normaliza o nome do produto."""
        resultado = produto

        # Padroniza prefixos (x galinha -> X Galinha)
        for prefixo, padrao in PREFIXOS_PRODUTO.items():
            if resultado.lower().startswith(prefixo):
                resultado = padrao + resultado[len(prefixo):]
                break

        # Aplica normalizações de tamanho/volume
        resultado_lower = resultado.lower()
        for termo, normalizacao in NORMALIZACOES.items():
            if termo in resultado_lower:
                # Substitui mantendo o case correto
                pattern = re.compile(re.escape(termo), re.IGNORECASE)
                resultado = pattern.sub(normalizacao, resultado)
                break

        # Capitaliza primeira letra de cada palavra
        palavras = resultado.split()
        palavras_capitalizadas = []
        for palavra in palavras:
            # Não capitaliza artigos e preposições pequenas
            if palavra.lower() in ["de", "da", "do", "e", "com", "no", "na"]:
                palavras_capitalizadas.append(palavra.lower())
            elif palavra.startswith("("):
                palavras_capitalizadas.append(palavra)
            else:
                palavras_capitalizadas.append(palavra.capitalize())

        return " ".join(palavras_capitalizadas)

    def _normalize_additional(self, adicional: str) -> str:
        """Normaliza o nome de um adicional."""
        # Remove artigos do início
        adicional = re.sub(r"^(um|uma|o|a)\s+", "", adicional, flags=re.IGNORECASE)
        # Capitaliza
        return adicional.strip().capitalize()

    def resolve(self, item: ParsedItem) -> ResolvedItem:
        """
        Resolve um ParsedItem aplicando gírias e normalizações.

        Args:
            item: Item parseado do texto do cliente

        Returns:
            ResolvedItem: Item com gírias resolvidas e nomes normalizados
        """
        # 1. Aplica gírias
        produto, obs_girias = self._apply_girias(item)

        # 2. Normaliza nome do produto
        produto_normalizado = self._normalize_product_name(produto)

        # 3. Normaliza adicionais
        adicionais_normalizados = [
            self._normalize_additional(a) for a in item.adicionais_texto
        ]

        # 4. Combina observações
        todas_observacoes = obs_girias + item.observacoes_texto

        return ResolvedItem(
            texto_original=item.texto_original,
            quantidade=item.quantidade,
            produto_busca=produto_normalizado,
            adicionais_busca=adicionais_normalizados,
            observacoes=todas_observacoes,
        )

    def resolve_all(self, items: List[ParsedItem]) -> List[ResolvedItem]:
        """Resolve uma lista de ParsedItems."""
        return [self.resolve(item) for item in items]
