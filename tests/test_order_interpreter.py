"""Testes para o Order Interpreter Service."""

import pytest
from unittest.mock import MagicMock, patch

from app.services.order_interpreter.parser import OrderParser
from app.services.order_interpreter.giria_resolver import GiriaResolver
from app.services.order_interpreter.models import ParsedItem, ResolvedItem


class TestOrderParser:
    """Testes para o OrderParser."""

    def setup_method(self):
        self.parser = OrderParser()

    def test_parse_single_item_simple(self):
        """Testa parsing de item simples."""
        result = self.parser.parse("1 x galinha")
        assert len(result) == 1
        assert result[0].quantidade == 1
        assert "galinha" in result[0].texto_produto.lower()

    def test_parse_single_item_without_x(self):
        """Testa parsing de item sem 'x'."""
        result = self.parser.parse("2 coca cola")
        assert len(result) == 1
        assert result[0].quantidade == 2

    def test_parse_multiple_items_newline(self):
        """Testa parsing de múltiplos itens separados por quebra de linha."""
        text = """1 x galinha
2 x burguer
1 coca lata"""
        result = self.parser.parse(text)
        assert len(result) == 3

    def test_parse_multiple_items_comma(self):
        """Testa parsing de múltiplos itens separados por vírgula."""
        text = "1 x galinha, 2 x burguer, 1 coca"
        result = self.parser.parse(text)
        assert len(result) == 3

    def test_parse_with_additionals(self):
        """Testa parsing de item com adicionais."""
        result = self.parser.parse("1 x galinha com bacon e milho")
        assert len(result) == 1
        assert "bacon" in [a.lower() for a in result[0].adicionais_texto]
        assert "milho" in [a.lower() for a in result[0].adicionais_texto]

    def test_parse_with_observations(self):
        """Testa parsing de item com observações."""
        result = self.parser.parse("1 x galinha sem cebola bem passado")
        assert len(result) == 1
        obs_lower = [o.lower() for o in result[0].observacoes_texto]
        assert any("sem cebola" in o for o in obs_lower)
        assert any("bem passado" in o for o in obs_lower)

    def test_parse_with_modifier_careca(self):
        """Testa parsing de item com modificador 'careca'."""
        result = self.parser.parse("1 x galinha careca")
        assert len(result) == 1
        assert "careca" in [m.lower() for m in result[0].modificadores]

    def test_parse_complex_order(self):
        """Testa parsing de pedido complexo."""
        text = "2 x galinha careca com bacon e milho cortado ao meio"
        result = self.parser.parse(text)
        assert len(result) == 1
        item = result[0]
        assert item.quantidade == 2
        assert "careca" in [m.lower() for m in item.modificadores]
        assert "bacon" in [a.lower() for a in item.adicionais_texto]
        assert "milho" in [a.lower() for a in item.adicionais_texto]
        assert any("cortado ao meio" in o.lower() for o in item.observacoes_texto)

    def test_parse_empty_text(self):
        """Testa parsing de texto vazio."""
        result = self.parser.parse("")
        assert len(result) == 0

    def test_parse_real_order_example(self):
        """Testa com exemplo real do usuário."""
        text = """1 X galinha com bacon
1 X galinha careca com batata palha cortado ao meio
1 queijo quente
2 maionese adicional"""
        result = self.parser.parse(text)
        assert len(result) == 4


class TestGiriaResolver:
    """Testes para o GiriaResolver."""

    def setup_method(self):
        self.resolver = GiriaResolver(db=None)

    def test_resolve_careca_to_sem_salada(self):
        """Testa que 'careca' vira observação 'sem salada'."""
        item = ParsedItem(
            texto_original="1 x galinha careca",
            quantidade=1,
            texto_produto="galinha",
            modificadores=["careca"],
            adicionais_texto=[],
            observacoes_texto=[],
        )
        result = self.resolver.resolve(item)
        assert "sem salada" in result.observacoes

    def test_resolve_completo_ignored(self):
        """Testa que 'completo' é ignorado."""
        item = ParsedItem(
            texto_original="1 x salada completo",
            quantidade=1,
            texto_produto="salada",
            modificadores=["completo"],
            adicionais_texto=[],
            observacoes_texto=[],
        )
        result = self.resolver.resolve(item)
        # "completo" não deve adicionar nada às observações
        assert "completo" not in " ".join(result.observacoes).lower()

    def test_resolve_no_prato_suffix(self):
        """Testa que 'no prato' é adicionado ao nome do produto."""
        item = ParsedItem(
            texto_original="1 x galinha no prato",
            quantidade=1,
            texto_produto="galinha",
            modificadores=["no prato"],
            adicionais_texto=[],
            observacoes_texto=[],
        )
        result = self.resolver.resolve(item)
        assert "prato" in result.produto_busca.lower()

    def test_normalize_product_name_x_prefix(self):
        """Testa normalização do prefixo 'x'."""
        item = ParsedItem(
            texto_original="1 x galinha",
            quantidade=1,
            texto_produto="x galinha",
            modificadores=[],
            adicionais_texto=[],
            observacoes_texto=[],
        )
        result = self.resolver.resolve(item)
        assert result.produto_busca.startswith("X ")

    def test_normalize_additional_name(self):
        """Testa normalização de nome de adicional."""
        item = ParsedItem(
            texto_original="1 x galinha com bacon",
            quantidade=1,
            texto_produto="galinha",
            modificadores=[],
            adicionais_texto=["bacon"],
            observacoes_texto=[],
        )
        result = self.resolver.resolve(item)
        assert "Bacon" in result.adicionais_busca

    def test_resolve_preserves_quantity(self):
        """Testa que a quantidade é preservada."""
        item = ParsedItem(
            texto_original="3 x galinha",
            quantidade=3,
            texto_produto="galinha",
            modificadores=[],
            adicionais_texto=[],
            observacoes_texto=[],
        )
        result = self.resolver.resolve(item)
        assert result.quantidade == 3

    def test_resolve_combines_observations(self):
        """Testa que observações são combinadas."""
        item = ParsedItem(
            texto_original="1 x galinha careca bem passado",
            quantidade=1,
            texto_produto="galinha",
            modificadores=["careca"],
            adicionais_texto=[],
            observacoes_texto=["bem passado"],
        )
        result = self.resolver.resolve(item)
        assert "sem salada" in result.observacoes
        assert "bem passado" in result.observacoes


class TestIntegration:
    """Testes de integração."""

    def test_parser_and_resolver_together(self):
        """Testa parser e resolver juntos."""
        parser = OrderParser()
        resolver = GiriaResolver(db=None)

        text = "2 x galinha careca com bacon e milho cortado ao meio"
        parsed = parser.parse(text)
        assert len(parsed) == 1

        resolved = resolver.resolve(parsed[0])
        assert resolved.quantidade == 2
        assert "sem salada" in resolved.observacoes
        assert "Bacon" in resolved.adicionais_busca
        assert "Milho" in resolved.adicionais_busca
        assert any("cortado ao meio" in o.lower() for o in resolved.observacoes)
