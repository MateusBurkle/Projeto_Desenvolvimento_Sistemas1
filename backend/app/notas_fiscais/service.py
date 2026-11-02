"""Regras de negócio do módulo 5 - notas fiscais simuladas: UC16 (emissão) e UC17 (consulta/download).
RF02, RF19, RF20; RN02, RN19, RN20; RNF03, RNF05; DP-49."""
import math
from datetime import date
from html import escape

from app.erros import ErroApi
from app.notas_fiscais import repository
from app.permissoes import CLIENTE_EMPRESA
from app.vendas import repository as vendas_repository
from app.vendas import service as vendas_service

MARCA_SIMULADA = "SIMULADA – sem valor fiscal"  # DP-49
_MSG_404 = "Nota fiscal não encontrada."


def _nota_dict(nota, venda: dict) -> dict:
    return {"id_nota": nota["id_nota"], "numero": nota["numero"], "data_emissao": nota["data_emissao"],
            "simulada": True, "venda": venda}


def _exigir_consistente(conexao, id_venda: int, venda: dict) -> None:
    """UC16 FE2, RN19: a venda precisa ter itens com valores válidos, e a soma deve bater com o total gravado."""
    itens = venda["itens"]
    soma_sql = vendas_repository.buscar_venda(conexao, id_venda)["valor_total"]
    problemas = (not itens or any(not math.isfinite(i["valor"]) or i["valor"] <= 0 for i in itens)
                 or abs(float(soma_sql) - sum(i["valor"] for i in itens)) > 0.005)
    if problemas:
        raise ErroApi(422, "VENDA_INCONSISTENTE", "Os dados da venda estão inconsistentes; a nota não pode ser emitida.",
                      {"itens": "venda sem itens ou com valores inconsistentes"})


def emitir(conexao, id_venda: int) -> tuple[dict, bool]:
    """UC16 fluxo principal, FA1, FE1, FE2; RN19, DP-49. Administrador (rota). Devolve (nota, criada).
    Ordem: 404 -> nota existente (200, sem duplicar) -> VENDA_NAO_CONFIRMADA -> VENDA_INCONSISTENTE -> emite.
    Número 'NFS-AAAA-NNNNNN' sequencial por ano; leitura da sequência e INSERT na mesma transação exclusiva."""
    repository.iniciar_transacao(conexao)
    try:
        venda_linha = vendas_repository.buscar_venda(conexao, id_venda)
        if venda_linha is None:
            raise ErroApi(404, "NAO_ENCONTRADO", "Venda não encontrada.")
        existente = repository.buscar_por_venda(conexao, id_venda)
        if existente is not None:  # FA1
            conexao.commit()
            return _nota_dict(existente, vendas_service.montar_venda(conexao, id_venda)), False
        if venda_linha["situacao"] != "Confirmada":  # FE1, RN19
            raise ErroApi(422, "VENDA_NAO_CONFIRMADA", "A nota só pode ser emitida para venda confirmada.",
                          {"situacao": venda_linha["situacao"]})
        venda = vendas_service.montar_venda(conexao, id_venda)
        _exigir_consistente(conexao, id_venda, venda)  # FE2
        hoje = date.today()
        numero = f"NFS-{hoje.year:04d}-{repository.maior_sequencia_do_ano(conexao, hoje.year) + 1:06d}"
        id_nota = repository.inserir(conexao, id_venda, numero, hoje.isoformat())
        conexao.commit()
    except BaseException:
        conexao.rollback()
        raise
    return _nota_dict(repository.buscar_por_id(conexao, id_nota), vendas_service.montar_venda(conexao, id_venda)), True


def _obter_visivel(conexao, usuario: dict, id_nota: int):
    """UC17 FE1, RN20, RNF05: inexistente ou de outra organização -> 404, sem revelar dados."""
    nota = repository.buscar_por_id(conexao, id_nota)
    if nota is None or (usuario["perfil"] == CLIENTE_EMPRESA
                        and nota["id_organizacao_cliente"] != usuario["id_organizacao"]):
        raise ErroApi(404, "NAO_ENCONTRADO", _MSG_404)
    return nota


def listar(conexao, usuario: dict, page: int, size: int, filtros: dict) -> dict:
    """UC17 passo 1-2, RN20: Administrador vê todas; Cliente Empresa só as da própria organização (filtro ignorado)."""
    filtros = dict(filtros)
    if usuario["perfil"] == CLIENTE_EMPRESA:
        filtros["id_organizacao_cliente"] = usuario["id_organizacao"] if usuario["id_organizacao"] is not None else -1
    for chave in ("data_de", "data_ate"):
        if filtros.get(chave) is not None:
            filtros[chave] = filtros[chave].isoformat()
    linhas, total = repository.listar(conexao, page, size, filtros)
    itens = [{**dict(l), "valor_total": round(float(l["valor_total"]), 2)} for l in linhas]
    return {"items": itens, "total": total, "page": page, "size": size}


def obter(conexao, usuario: dict, id_nota: int) -> dict:
    """UC17 passo 3-4, FA1, FE1."""
    nota = _obter_visivel(conexao, usuario, id_nota)
    return _nota_dict(nota, vendas_service.montar_venda(conexao, nota["id_venda"]))


def _moeda(valor: float) -> str:
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def _data_br(iso: str) -> str:
    return "/".join(reversed(iso.split("-")))


def baixar(conexao, usuario: dict, id_nota: int) -> tuple[str, str]:
    """UC17 passo 5, RN20, DP-49: HTML imprimível gerado pela API. TODO valor dinâmico passa por `html.escape`
    (sem injeção). Devolve (nome_do_arquivo, html)."""
    nota = obter(conexao, usuario, id_nota)
    venda = nota["venda"]
    e = lambda v: escape(str(v), quote=True)  # noqa: E731
    linhas = "".join(
        f"<tr><td>{e(i['identificacao'])}</td><td>{e(i['categoria_nome'])}</td><td>{e(i['modelo'])}</td>"
        f"<td>{e(i['condicao'])}</td><td class=\"num\">{e(_moeda(i['valor']))}</td></tr>"
        for i in venda["itens"]
    )
    html = f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<title>Nota fiscal simulada {e(nota['numero'])}</title>
<style>
body {{ font-family: Arial, sans-serif; margin: 2rem; color: #222; }}
h1 {{ font-size: 1.4rem; margin-bottom: .2rem; }}
.marca {{ border: 3px solid #b00020; color: #b00020; font-weight: bold; text-align: center; padding: .6rem; margin: 1rem 0; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
th, td {{ border: 1px solid #999; padding: .4rem; text-align: left; }}
.num {{ text-align: right; }}
@media print {{ body {{ margin: 0; }} }}
</style>
</head>
<body>
<h1>LEAF TI - Nota fiscal simulada</h1>
<div class="marca">{e(MARCA_SIMULADA)}</div>
<p><strong>Número:</strong> {e(nota['numero'])}<br>
<strong>Data de emissão:</strong> {e(_data_br(nota['data_emissao']))}</p>
<p><strong>Cliente:</strong> {e(venda['nome_organizacao'])}<br>
<strong>Venda:</strong> {e(venda['id_venda'])}<br>
<strong>Data da venda:</strong> {e(_data_br(venda['data_venda']))}<br>
<strong>Forma de pagamento:</strong> {e(venda['forma_pagamento'])}</p>
<table>
<thead><tr><th>Identificação</th><th>Categoria</th><th>Modelo</th><th>Condição</th><th>Valor</th></tr></thead>
<tbody>{linhas}</tbody>
<tfoot><tr><th colspan="4">Quantidade: {e(venda['quantidade'])} - Total</th><th class="num">{e(_moeda(venda['valor_total']))}</th></tr></tfoot>
</table>
<p class="marca">{e(MARCA_SIMULADA)}</p>
</body>
</html>
"""
    return f"{nota['numero']}.html", html
