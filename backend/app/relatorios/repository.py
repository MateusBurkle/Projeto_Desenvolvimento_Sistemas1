"""SQL do módulo 6 - relatórios (somente SELECT, parametrizado). UC22, UC23, UC24; RN16, RN17, RN18."""
import sqlite3

# Datas ficam como texto ISO; substr(...,1,10) ignora eventual hora e mantém a comparação por dia.


def vendas_confirmadas(conexao: sqlite3.Connection, data_de: str, data_ate: str):
    """UC22 passo 4; RN16: só situacao='Confirmada' no período (inclusive); data_venda, id_venda crescentes."""
    return conexao.execute(
        """SELECT v.id_venda, v.data_venda, v.id_organizacao_cliente, o.nome_razao_social AS cliente,
                  v.forma_pagamento, iv.id_equipamento, e.identificacao, e.modelo, c.nome AS categoria, iv.valor
             FROM VENDA v
             JOIN ORGANIZACAO o ON o.id_organizacao = v.id_organizacao_cliente
             LEFT JOIN ITEM_VENDA iv ON iv.id_venda = v.id_venda
             LEFT JOIN EQUIPAMENTO e ON e.id_equipamento = iv.id_equipamento
             LEFT JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
            WHERE v.situacao = 'Confirmada' AND substr(v.data_venda, 1, 10) >= ? AND substr(v.data_venda, 1, 10) <= ?
            ORDER BY v.data_venda, v.id_venda, iv.id_item_venda""", (data_de, data_ate)).fetchall()


def _filtro_equipamentos(f: dict):
    where, params = [], []
    if f.get("id_categoria") is not None:
        where.append("e.id_categoria = ?")
        params.append(f["id_categoria"])
    if f.get("situacao") is not None:
        where.append("e.situacao = ?")
        params.append(f["situacao"])
    if f.get("data_de") is not None:
        where.append("substr(e.data_recebimento, 1, 10) >= ?")
        params.append(f["data_de"])
    if f.get("data_ate") is not None:
        where.append("substr(e.data_recebimento, 1, 10) <= ?")
        params.append(f["data_ate"])
    return ((" WHERE " + " AND ".join(where)) if where else ""), params


def equipamentos(conexao: sqlite3.Connection, filtros: dict, page: int, size: int):
    """UC23 passo 4; RN17. Devolve (linhas da página, total, resumo por situação do conjunto filtrado)."""
    filtro, params = _filtro_equipamentos(filtros)
    resumo = conexao.execute(
        "SELECT e.situacao, COUNT(*) FROM EQUIPAMENTO e" + filtro + " GROUP BY e.situacao", params).fetchall()
    linhas = conexao.execute(
        """SELECT e.id_equipamento, e.identificacao, e.modelo, e.id_categoria, c.nome AS categoria, e.condicao,
                  e.situacao, e.ativo, e.valor, e.data_recebimento, e.origem,
                  ov.nome_razao_social AS cliente_venda, v.data_venda,
                  og.nome_razao_social AS ong, d.data_doacao
             FROM EQUIPAMENTO e
             JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
             LEFT JOIN ITEM_VENDA iv ON iv.id_equipamento = e.id_equipamento
             LEFT JOIN VENDA v ON v.id_venda = iv.id_venda AND v.situacao = 'Confirmada'
             LEFT JOIN ORGANIZACAO ov ON ov.id_organizacao = v.id_organizacao_cliente
             LEFT JOIN DOACAO d ON d.id_equipamento = e.id_equipamento
             LEFT JOIN ORGANIZACAO og ON og.id_organizacao = d.id_organizacao_ong""" + filtro +
        " ORDER BY e.id_equipamento LIMIT ? OFFSET ?", [*params, size, (page - 1) * size]).fetchall()
    return linhas, sum(r[1] for r in resumo), {r[0]: r[1] for r in resumo}


def _filtro_solicitacoes(f: dict):
    where, params = [], []
    if f.get("id_organizacao_doadora") is not None:
        where.append("s.id_organizacao_doadora = ?")
        params.append(f["id_organizacao_doadora"])
    if f.get("situacao") is not None:
        where.append("s.situacao = ?")
        params.append(f["situacao"])
    if f.get("data_de") is not None:
        where.append("substr(s.data_solicitacao, 1, 10) >= ?")
        params.append(f["data_de"])
    if f.get("data_ate") is not None:
        where.append("substr(s.data_solicitacao, 1, 10) <= ?")
        params.append(f["data_ate"])
    return ((" WHERE " + " AND ".join(where)) if where else ""), params


def solicitacoes(conexao: sqlite3.Connection, filtros: dict, page: int, size: int):
    """UC24 passo 2; RN18: todas as solicitações, data e id decrescentes. Devolve (linhas, total)."""
    filtro, params = _filtro_solicitacoes(filtros)
    total = conexao.execute("SELECT COUNT(*) FROM SOLICITACAO s" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        """SELECT s.id_solicitacao, s.id_organizacao_doadora, o.nome_razao_social AS empresa_doadora,
                  s.data_solicitacao, s.situacao
             FROM SOLICITACAO s JOIN ORGANIZACAO o ON o.id_organizacao = s.id_organizacao_doadora""" + filtro +
        " ORDER BY s.data_solicitacao DESC, s.id_solicitacao DESC LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size]).fetchall()
    return linhas, total


def itens_das_solicitacoes(conexao: sqlite3.Connection, ids: list[int]):
    """UC24 passo 3: itens (tipo, modelo, quantidade) das solicitações da página."""
    if not ids:
        return []
    marcas = ",".join("?" * len(ids))  # apenas placeholders
    return conexao.execute(
        "SELECT id_item_solicitacao, id_solicitacao, tipo, modelo, quantidade FROM ITEM_SOLICITACAO "
        "WHERE id_solicitacao IN (" + marcas + ") ORDER BY id_item_solicitacao", ids).fetchall()


def equipamentos_dos_itens(conexao: sqlite3.Connection, ids_itens: list[int]):
    """UC24 passo 3-4; RN21: equipamentos vinculados aos itens, com ONG e data da doação quando houver."""
    if not ids_itens:
        return []
    marcas = ",".join("?" * len(ids_itens))
    return conexao.execute(
        """SELECT e.id_item_solicitacao, e.id_equipamento, e.identificacao, e.condicao, e.situacao,
                  og.nome_razao_social AS ong, d.data_doacao
             FROM EQUIPAMENTO e
             LEFT JOIN DOACAO d ON d.id_equipamento = e.id_equipamento
             LEFT JOIN ORGANIZACAO og ON og.id_organizacao = d.id_organizacao_ong
            WHERE e.id_item_solicitacao IN (""" + marcas + ") ORDER BY e.id_equipamento", ids_itens).fetchall()
