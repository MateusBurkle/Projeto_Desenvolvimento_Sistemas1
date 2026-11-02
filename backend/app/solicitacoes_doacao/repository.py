"""SQL da solicitação de doação (consultas parametrizadas). Gravações NÃO fazem commit: o service controla a transação."""
import sqlite3

_SELECT = """
    SELECT s.id_solicitacao_doacao, s.id_organizacao_ong, o.nome_razao_social AS nome_ong, s.data_solicitacao,
           s.situacao, s.motivo_recusa, s.decidido_por, s.data_decisao
      FROM SOLICITACAO_DOACAO s JOIN ORGANIZACAO o ON o.id_organizacao = s.id_organizacao_ong
"""


def iniciar_transacao(conexao: sqlite3.Connection) -> None:
    conexao.execute("BEGIN IMMEDIATE")  # sem corrida entre checagem de reserva e gravação (DP-70)


def _marcas(n: int) -> str:
    return ",".join("?" * n)  # só placeholders; valores sempre como parâmetros


def buscar_organizacao(conexao, id_organizacao):
    return conexao.execute(
        "SELECT id_organizacao, tipo, situacao FROM ORGANIZACAO WHERE id_organizacao = ?", (id_organizacao,)).fetchone()


def equipamentos(conexao, ids: list[int]) -> dict:
    """id -> linha (situacao, ativo) dos equipamentos existentes."""
    linhas = conexao.execute(
        f"SELECT id_equipamento, situacao, ativo FROM EQUIPAMENTO WHERE id_equipamento IN ({_marcas(len(ids))})", ids)
    return {l["id_equipamento"]: l for l in linhas}


def ids_reservados(conexao, ids: list[int]) -> set[int]:
    """DP-70: com item em solicitação de doação Pendente ou em VENDA Pendente."""
    linhas = conexao.execute(
        f"""SELECT i.id_equipamento FROM ITEM_SOLICITACAO_DOACAO i JOIN SOLICITACAO_DOACAO s
                ON s.id_solicitacao_doacao = i.id_solicitacao_doacao
             WHERE s.situacao = 'Pendente' AND i.id_equipamento IN ({_marcas(len(ids))})
            UNION
            SELECT iv.id_equipamento FROM ITEM_VENDA iv JOIN VENDA v ON v.id_venda = iv.id_venda
             WHERE v.situacao = 'Pendente' AND iv.id_equipamento IN ({_marcas(len(ids))})""",
        [*ids, *ids]).fetchall()
    return {l[0] for l in linhas}


def inserir(conexao, id_ong: int, data: str, ids: list[int]) -> int:
    nova = conexao.execute(
        "INSERT INTO SOLICITACAO_DOACAO (id_organizacao_ong, data_solicitacao, situacao) VALUES (?, ?, 'Pendente')",
        (id_ong, data)).lastrowid
    for i in ids:
        conexao.execute("INSERT INTO ITEM_SOLICITACAO_DOACAO (id_solicitacao_doacao, id_equipamento) VALUES (?, ?)",
                        (nova, i))
    return nova


def buscar(conexao, id_solicitacao: int):
    return conexao.execute(_SELECT + " WHERE s.id_solicitacao_doacao = ?", (id_solicitacao,)).fetchone()


def itens(conexao, id_solicitacao: int):
    """Sem valor, origem ou vínculos internos."""
    return conexao.execute(
        """SELECT i.id_equipamento, e.modelo, c.nome AS categoria, e.condicao
             FROM ITEM_SOLICITACAO_DOACAO i JOIN EQUIPAMENTO e ON e.id_equipamento = i.id_equipamento
             JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
            WHERE i.id_solicitacao_doacao = ? ORDER BY i.id_item_solicitacao_doacao""", (id_solicitacao,)).fetchall()


def ids_equipamento(conexao, id_solicitacao: int) -> list[int]:
    return [l[0] for l in conexao.execute(
        "SELECT id_equipamento FROM ITEM_SOLICITACAO_DOACAO WHERE id_solicitacao_doacao = ? "
        "ORDER BY id_item_solicitacao_doacao", (id_solicitacao,))]


def listar(conexao, page: int, size: int, id_ong: int | None, situacao: str | None):
    where, params = [], []
    if id_ong is not None:
        where.append("s.id_organizacao_ong = ?")
        params.append(id_ong)
    if situacao is not None:
        where.append("s.situacao = ?")
        params.append(situacao)
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM SOLICITACAO_DOACAO s" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY s.data_solicitacao DESC, s.id_solicitacao_doacao DESC LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size]).fetchall()
    return linhas, total


def decidir(conexao, id_solicitacao: int, situacao: str, motivo: str | None, decidido_por: str | None, data: str):
    conexao.execute(
        "UPDATE SOLICITACAO_DOACAO SET situacao = ?, motivo_recusa = ?, decidido_por = ?, data_decisao = ? "
        "WHERE id_solicitacao_doacao = ?", (situacao, motivo, decidido_por, data, id_solicitacao))
