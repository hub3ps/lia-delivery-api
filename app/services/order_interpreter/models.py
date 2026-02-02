"""Modelos de dados para o Order Interpreter."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ParsedItem:
    """Item extraído do texto do cliente (antes de aplicar regras)."""

    texto_original: str
    quantidade: int = 1
    texto_produto: str = ""
    modificadores: List[str] = field(default_factory=list)
    adicionais_texto: List[str] = field(default_factory=list)
    observacoes_texto: List[str] = field(default_factory=list)


@dataclass
class ResolvedItem:
    """Item após aplicar regras de gírias e normalização."""

    texto_original: str
    quantidade: int
    produto_busca: str
    adicionais_busca: List[str] = field(default_factory=list)
    observacoes: List[str] = field(default_factory=list)


@dataclass
class MatchedProduct:
    """Produto encontrado no cardápio."""

    pdv: str
    nome: str
    preco: float
    score: float
    adicionais_disponiveis: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class MatchedAdditional:
    """Adicional encontrado e validado."""

    pdv: str
    nome: str
    preco: float
    quantidade: int = 1
    score: float = 100.0


@dataclass
class ValidAdditional:
    """Adicional validado para output final."""

    nome: str
    pdv: str
    quantidade: int
    preco_unitario: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nome": self.nome,
            "pdv": self.pdv,
            "quantidade": self.quantidade,
            "preco_unitario": self.preco_unitario,
        }


@dataclass
class ValidItem:
    """Item validado para output final."""

    nome: str
    pdv: str
    quantidade: int
    preco_unitario: float
    adicionais: List[ValidAdditional] = field(default_factory=list)
    observacoes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "nome": self.nome,
            "pdv": self.pdv,
            "quantidade": self.quantidade,
            "preco_unitario": self.preco_unitario,
            "adicionais": [a.to_dict() for a in self.adicionais],
            "observacoes": self.observacoes,
        }


@dataclass
class NotFoundItem:
    """Item não encontrado no cardápio."""

    texto_original: str
    motivo: str
    sugestoes: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "texto_original": self.texto_original,
            "motivo": self.motivo,
            "sugestoes": self.sugestoes,
        }


@dataclass
class Suggestion:
    """Sugestão de correção."""

    texto_cliente: str
    sugestao: str
    score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "texto_cliente": self.texto_cliente,
            "sugestao": self.sugestao,
            "score": self.score,
        }


@dataclass
class InterpreterOutput:
    """Output final do interpretador para o agente."""

    sucesso: bool
    itens_validos: List[ValidItem] = field(default_factory=list)
    itens_nao_encontrados: List[NotFoundItem] = field(default_factory=list)
    sugestoes: List[Suggestion] = field(default_factory=list)
    avisos: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "sucesso": self.sucesso,
            "itens_validos": [i.to_dict() for i in self.itens_validos],
            "itens_nao_encontrados": [i.to_dict() for i in self.itens_nao_encontrados],
            "sugestoes": [s.to_dict() for s in self.sugestoes],
            "avisos": self.avisos,
        }
