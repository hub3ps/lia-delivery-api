"""Serviço principal de interpretação de pedidos."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from app.services.order_interpreter.additional_matcher import AdditionalMatcher
from app.services.order_interpreter.giria_resolver import GiriaResolver
from app.services.order_interpreter.menu_matcher import MenuMatcher
from app.services.order_interpreter.models import (
    InterpreterOutput,
    NotFoundItem,
    ResolvedItem,
    Suggestion,
    ValidAdditional,
    ValidItem,
)
from app.services.order_interpreter.parser import OrderParser

logger = logging.getLogger(__name__)


class OrderInterpreterService:
    """
    Serviço principal para interpretação de pedidos.

    Orquestra o fluxo completo:
    1. Parser: extrai itens do texto livre
    2. GiriaResolver: aplica regras de gírias
    3. MenuMatcher: encontra produtos no cardápio
    4. AdditionalMatcher: valida adicionais
    5. Monta resposta estruturada para o agente
    """

    def __init__(self, db):
        """
        Inicializa o serviço.

        Args:
            db: Conexão com banco de dados
        """
        self.db = db
        self.parser = OrderParser()
        self.giria_resolver = GiriaResolver(db)
        self.menu_matcher = MenuMatcher(db)
        self.additional_matcher = AdditionalMatcher(db)

    def _build_valid_item(
        self,
        resolved: ResolvedItem,
        product_nome: str,
        product_pdv: str,
        product_preco: float,
        valid_additionals: List[ValidAdditional],
    ) -> ValidItem:
        """Constrói um ValidItem a partir dos dados processados."""
        observacoes_str = ", ".join(resolved.observacoes) if resolved.observacoes else ""

        return ValidItem(
            nome=product_nome,
            pdv=product_pdv,
            quantidade=resolved.quantidade,
            preco_unitario=product_preco,
            adicionais=valid_additionals,
            observacoes=observacoes_str,
        )

    def _build_not_found_item(
        self, resolved: ResolvedItem, sugestoes: List[str], motivo: str = "produto_nao_encontrado"
    ) -> NotFoundItem:
        """Constrói um NotFoundItem para produto não encontrado."""
        return NotFoundItem(
            texto_original=resolved.texto_original,
            motivo=motivo,
            sugestoes=sugestoes,
        )

    def interpret(self, texto_pedido: str) -> InterpreterOutput:
        """
        Interpreta o texto do pedido do cliente.

        Args:
            texto_pedido: Texto livre do cliente com os itens do pedido

        Returns:
            InterpreterOutput: Resultado estruturado da interpretação
        """
        logger.info(f"Interpretando pedido: {texto_pedido[:100]}...")

        # Validação de entrada
        if not texto_pedido or not texto_pedido.strip():
            return InterpreterOutput(
                sucesso=False,
                avisos=["Nenhum texto de pedido fornecido."],
            )

        try:
            # 1. Parse do texto
            parsed_items = self.parser.parse(texto_pedido)
            logger.debug(f"Items parseados: {len(parsed_items)}")

            if not parsed_items:
                return InterpreterOutput(
                    sucesso=False,
                    avisos=["Não consegui identificar itens no pedido. Por favor, informe os itens desejados."],
                )

            # 2. Resolver gírias
            resolved_items = self.giria_resolver.resolve_all(parsed_items)
            logger.debug(f"Items resolvidos: {len(resolved_items)}")

            # 3. Match de produtos e adicionais
            itens_validos: List[ValidItem] = []
            itens_nao_encontrados: List[NotFoundItem] = []
            todas_sugestoes: List[Suggestion] = []
            avisos: List[str] = []

            for resolved in resolved_items:
                # 3.1 Match do produto
                product_match, product_sugestoes = self.menu_matcher.match(resolved.produto_busca)

                if not product_match:
                    # Produto não encontrado
                    itens_nao_encontrados.append(
                        self._build_not_found_item(resolved, product_sugestoes)
                    )
                    if product_sugestoes:
                        todas_sugestoes.append(
                            Suggestion(
                                texto_cliente=resolved.produto_busca,
                                sugestao=product_sugestoes[0],
                                score=0,
                            )
                        )
                    continue

                # 3.2 Match dos adicionais
                valid_additionals: List[ValidAdditional] = []
                adicionais_nao_encontrados: List[str] = []

                if resolved.adicionais_busca:
                    matched_adds, not_found_adds = self.additional_matcher.match_all(
                        resolved.adicionais_busca, product_match
                    )

                    # Converte para ValidAdditional
                    for ma in matched_adds:
                        valid_additionals.append(
                            ValidAdditional(
                                nome=ma.nome,
                                pdv=ma.pdv,
                                quantidade=ma.quantidade,
                                preco_unitario=ma.preco,
                            )
                        )

                    # Adiciona avisos para adicionais não encontrados
                    for add_texto, add_sugestoes in not_found_adds:
                        adicionais_nao_encontrados.append(add_texto)
                        if add_sugestoes:
                            avisos.append(
                                f"Adicional '{add_texto}' não encontrado para {product_match.nome}. "
                                f"Sugestões: {', '.join(add_sugestoes)}"
                            )
                        else:
                            avisos.append(
                                f"Adicional '{add_texto}' não está disponível para {product_match.nome}."
                            )

                # 3.3 Monta item válido
                item_valido = self._build_valid_item(
                    resolved,
                    product_match.nome,
                    product_match.pdv,
                    product_match.preco,
                    valid_additionals,
                )
                itens_validos.append(item_valido)

            # 4. Monta resposta final
            sucesso = len(itens_nao_encontrados) == 0

            return InterpreterOutput(
                sucesso=sucesso,
                itens_validos=itens_validos,
                itens_nao_encontrados=itens_nao_encontrados,
                sugestoes=todas_sugestoes,
                avisos=avisos,
            )

        except Exception as e:
            logger.exception("Erro ao interpretar pedido")
            return InterpreterOutput(
                sucesso=False,
                avisos=[f"Erro ao processar pedido: {str(e)}"],
            )

    def interpret_to_dict(self, texto_pedido: str) -> Dict[str, Any]:
        """
        Interpreta o pedido e retorna como dicionário.

        Conveniente para uso direto como retorno de tool.

        Args:
            texto_pedido: Texto livre do cliente

        Returns:
            Dict: Resultado da interpretação como dicionário
        """
        result = self.interpret(texto_pedido)
        return result.to_dict()
