"""SQL do módulo 5 - notas fiscais simuladas (consultas parametrizadas). UC16, UC17; RN19, RN20."""
import sqlite3

_SELECT = """
    SELECT n.id_nota, n.id_venda, n.numero, n.data_emissao, v.id_organizacao_cliente,
           o.nome_razao_social AS nome_organizacao,
           (SELECT COALESCE(SUM(iv.valor), 0) FROM ITEM_VENDA iv WHERE iv.id_venda = n.id_venda) AS valor_total
      FROM NOTA_FISCAL_SIMULADA n
      JOIN VENDA v ON v.id_venda = n.id_venda
      JOIN ORGANIZACAO o ON o.id_organizacao = v.id_organizacao_cliente
"""


def buscar_por_id(conexao: sqlite3.Connection, id_nota: int):
    """UC17 passo 3-4."""
    return conexao.execute(_SELECT + " WHERE n.id_nota = ?", (id_nota,)).fetchone()


def buscar_por_venda(conexao: sqlite3.Connection, id_venda: int):
    """UC16 FA1: nota já existente da venda."""
    return conexao.execute(_SELECT + " WHERE n.id_venda = ?", (id_venda,)).fetchone()


def listar(conexao: sqlite3.Connection, page: int, size: int, filtros: dict):
    """UC17 passo 1-2: data_emissao desc, depois id desc. Devolve (linhas, total)."""
    where, params = [], []
    if filtros.get("id_organizacao_cliente") is not None:
        where.append("v.id_organizacao_cliente = ?")
        params.append(filtros["id_organizacao_cliente"])
    if filtros.get("data_de") is not None:
        where.append("n.data_emissao >= ?")
        params.append(filtros["data_de"])
    if filtros.get("data_ate") is not None:
        where.append("n.data_emissao <= ?")
        params.append(filtros["data_ate"])
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute(
        "SELECT COUNT(*) FROM NOTA_FISCAL_SIMULADA n JOIN VENDA v ON v.id_venda = n.id_venda" + filtro, params
    ).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY n.data_emissao DESC, n.id_nota DESC LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size]).fetchall()
    return linhas, total


def iniciar_transacao(conexao: sqlite3.Connection) -> None:
    """Bloqueia escritores concorrentes: a sequência do número é lida e gravada sem corrida (RN19)."""
    conexao.execute("BEGIN IMMEDIATE")


def maior_sequencia_do_ano(conexao: sqlite3.Connection, ano: int) -> int:
    """UC16 passo 4: maior NNNNNN já usado em 'NFS-AAAA-NNNNNN' (0 se não houver)."""
    prefixo = f"NFS-{ano:04d}-"
    linha = conexao.execute(
        "SELECT MAX(CAST(substr(numero, ?) AS INTEGER)) FROM NOTA_FISCAL_SIMULADA WHERE substr(numero, 1, ?) = ?",
        (len(prefixo) + 1, len(prefixo), prefixo)).fetchone()
    return linha[0] or 0


def inserir(conexao: sqlite3.Connection, id_venda: int, numero: str, data_emissao: str) -> int:
    """UC16 passo 4: número único e vínculo com a venda (UNIQUE no banco)."""
    return conexao.execute(
        "INSERT INTO NOTA_FISCAL_SIMULADA (id_venda, numero, data_emissao) VALUES (?, ?, ?)",
        (id_venda, numero, data_emissao)).lastrowid
