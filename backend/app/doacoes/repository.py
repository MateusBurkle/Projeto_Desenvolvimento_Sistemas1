"""SQL do módulo 4 - doações (somente leitura; consultas parametrizadas). A DOACAO é gravada por
equipamentos.service.mudar_situacao (DP-36)."""
import sqlite3

_SELECT = """
    SELECT d.id_doacao, d.id_equipamento, e.identificacao, e.modelo, c.nome AS categoria_nome, e.condicao,
           e.situacao, d.id_organizacao_ong, o.nome_razao_social AS nome_ong, d.data_doacao, i.id_solicitacao
      FROM DOACAO d
      JOIN EQUIPAMENTO e ON e.id_equipamento = d.id_equipamento
      JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
      JOIN ORGANIZACAO o ON o.id_organizacao = d.id_organizacao_ong
      LEFT JOIN ITEM_SOLICITACAO i ON i.id_item_solicitacao = e.id_item_solicitacao
"""


def listar_ongs_elegiveis(conexao: sqlite3.Connection):
    """UC11 passo 2, RN12: Cliente ONG ativas, por nome (máx. 200)."""
    return conexao.execute(
        "SELECT id_organizacao, nome_razao_social FROM ORGANIZACAO WHERE tipo = 'Cliente ONG' AND situacao = 'Ativa' "
        "ORDER BY casefold(nome_razao_social), id_organizacao LIMIT 200"
    ).fetchall()


def buscar_por_id(conexao: sqlite3.Connection, id_doacao: int):
    """UC19 passo 4."""
    return conexao.execute(_SELECT + " WHERE d.id_doacao = ?", (id_doacao,)).fetchone()


def listar(conexao: sqlite3.Connection, page: int, size: int, filtros: dict):
    """UC19 passo 2-3: ordenado por data_doacao desc, depois id desc. Devolve (linhas, total)."""
    where, params = [], []
    if filtros.get("id_organizacao_ong") is not None:
        where.append("d.id_organizacao_ong = ?")
        params.append(filtros["id_organizacao_ong"])
    if filtros.get("data_de") is not None:
        where.append("d.data_doacao >= ?")
        params.append(filtros["data_de"])
    if filtros.get("data_ate") is not None:
        where.append("d.data_doacao <= ?")
        params.append(filtros["data_ate"])
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM DOACAO d" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY d.data_doacao DESC, d.id_doacao DESC LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total
