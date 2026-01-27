from __future__ import annotations

import re
import unicodedata
from typing import Dict, List, Tuple


def gerar_fingerprint(texto: str | None, is_adicional: bool = False) -> str:
    if not texto:
        return ""
    limpo = str(texto).lower()
    limpo = unicodedata.normalize("NFD", limpo)
    limpo = "".join(ch for ch in limpo if not unicodedata.combining(ch))
    if is_adicional:
        limpo = re.sub(r"^(adicionais|adicional|opcionais|borda|acrescimo)\s*[-–]?\s*", "", limpo, flags=re.I)
    limpo = re.sub(r"[^a-z0-9]", "", limpo)
    return limpo


def mapear_itens(pedido_original: Dict, indice_banco: List[Dict]) -> Tuple[List[Dict], List[str]]:
    itens_mapeados: List[Dict] = []
    erros: List[str] = []

    produtos_banco = [i for i in indice_banco if i.get("item_type") == "product"]

    itens = pedido_original.get("itens") if isinstance(pedido_original, dict) else None
    if not isinstance(itens, list):
        return [], ["Itens inválidos no pedido"]

    for item_pedido in itens:
        fp_item = gerar_fingerprint(item_pedido.get("nome"), False)

        match_pai = next((db for db in produtos_banco if db.get("fingerprint") == fp_item), None)
        if not match_pai:
            candidatos = [db for db in produtos_banco if fp_item and db.get("fingerprint") and fp_item.find(db.get("fingerprint")) != -1]
            if candidatos:
                candidatos.sort(key=lambda x: len(x.get("fingerprint") or ""), reverse=True)
                match_pai = candidatos[0]

        if not match_pai:
            erros.append(f'Produto não encontrado: "{item_pedido.get("nome")}"')
            continue

        quantidade = float(item_pedido.get("quantidade") or item_pedido.get("qtd") or 1)
        item_final = {
            "pdv": match_pai.get("pdv"),
            "descricao": match_pai.get("nome_original"),
            "quantidade": quantidade,
            "valor_unitario": float(match_pai.get("price") or 0),
            "observacao": item_pedido.get("observacoes") or item_pedido.get("obs") or "",
            "adicionais": [],
        }

        adicionais = item_pedido.get("adicionais")
        if isinstance(adicionais, list):
            for ad in adicionais:
                fp_ad = gerar_fingerprint(ad.get("nome"), True)
                match_filho = next(
                    (
                        db
                        for db in indice_banco
                        if db.get("fingerprint") == fp_ad and db.get("parent_pdv") == match_pai.get("pdv")
                    ),
                    None,
                )
                if match_filho:
                    item_final["adicionais"].append(
                        {
                            "pdv": match_filho.get("pdv"),
                            "descricao": match_filho.get("nome_original"),
                            "quantidade": float(ad.get("quantidade") or ad.get("qtd") or 1),
                            "valor_unitario": float(match_filho.get("price") or 0),
                        }
                    )

        itens_mapeados.append(item_final)

    return itens_mapeados, erros


def calcular_total_pedido(itens_mapeados: List[Dict], taxa_entrega: float, desconto: float) -> float:
    total = 0.0
    for item in itens_mapeados:
        item_total = (item.get("valor_unitario") or 0) * (item.get("quantidade") or 1)
        for ad in item.get("adicionais", []):
            item_total += (ad.get("valor_unitario") or 0) * (ad.get("quantidade") or 1) * (item.get("quantidade") or 1)
        total += item_total
    total += taxa_entrega
    total -= desconto
    return total
