"""SQL do módulo 3 - equipamentos (consultas parametrizadas). Sem regra de negócio.

Nenhuma função de escrita faz commit: o service controla a transação (UC08 FE1: situação + DOACAO juntas).
"""
import sqlite3

_SELECT = """
    SELECT e.id_equipamento, e.identificacao, e.id_categoria, c.nome AS nome_categoria, c.ativa AS categoria_ativa,
           e.modelo, e.condicao, e.origem, e.situacao, e.data_recebimento, e.valor, e.id_item_solicitacao, e.ativo, e.imagem,
           d.id_doacao, d.id_organizacao_ong, o.nome_razao_social AS nome_ong, d.data_doacao
      FROM EQUIPAMENTO e
      JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
      LEFT JOIN DOACAO d ON d.id_equipamento = e.id_equipamento
      LEFT JOIN ORGANIZACAO o ON o.id_organizacao = d.id_organizacao_ong
"""


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def buscar_por_id(conexao: sqlite3.Connection, id_equipamento: int):
    """UC07 FA1."""
    return conexao.execute(_SELECT + " WHERE e.id_equipamento = ?", (id_equipamento,)).fetchone()


def buscar_id_por_identificacao(conexao: sqlite3.Connection, identificacao: str, excluir_id: int | None = None):
    """UC07 FE1: identificação sem diferenciar caixa; `excluir_id` desconsidera o próprio registro (UC07 FA1)."""
    if excluir_id is None:
        return conexao.execute(
            "SELECT id_equipamento FROM EQUIPAMENTO WHERE casefold(identificacao) = ?", (identificacao.casefold(),)
        ).fetchone()
    return conexao.execute(
        "SELECT id_equipamento FROM EQUIPAMENTO WHERE casefold(identificacao) = ? AND id_equipamento <> ?",
        (identificacao.casefold(), excluir_id),
    ).fetchone()


def buscar_categoria(conexao: sqlite3.Connection, id_categoria: int):
    """RN08: categoria para validar existência e situação."""
    return conexao.execute(
        "SELECT id_categoria, nome, ativa FROM CATEGORIA WHERE id_categoria = ?", (id_categoria,)
    ).fetchone()


def item_solicitacao_existe(conexao: sqlite3.Connection, id_item_solicitacao: int) -> bool:
    """UC07 passo 4 (DP-33)."""
    return conexao.execute(
        "SELECT 1 FROM ITEM_SOLICITACAO WHERE id_item_solicitacao = ?", (id_item_solicitacao,)
    ).fetchone() is not None


def buscar_quantidade_item(conexao: sqlite3.Connection, id_item_solicitacao: int) -> int | None:
    """DP-52, UC07 passo 4: quantidade prevista do item (None se o item não existe)."""
    linha = conexao.execute(
        "SELECT quantidade FROM ITEM_SOLICITACAO WHERE id_item_solicitacao = ?", (id_item_solicitacao,)
    ).fetchone()
    return None if linha is None else linha[0]


def buscar_organizacao(conexao: sqlite3.Connection, id_organizacao: int):
    """UC08 FE1: ONG da doação."""
    return conexao.execute(
        "SELECT id_organizacao, tipo, situacao FROM ORGANIZACAO WHERE id_organizacao = ?", (id_organizacao,)
    ).fetchone()


def listar(conexao: sqlite3.Connection, page: int, size: int, filtros: dict):
    """UC07 FA1: filtros, ordenação por data_recebimento desc e identificação, paginação. Devolve (linhas, total)."""
    where, params = [], []
    if filtros.get("id_categoria") is not None:
        where.append("e.id_categoria = ?")
        params.append(filtros["id_categoria"])
    if filtros.get("situacao") is not None:
        where.append("e.situacao = ?")
        params.append(filtros["situacao"])
    if filtros.get("condicao") is not None:
        where.append("e.condicao = ?")
        params.append(filtros["condicao"])
    if filtros.get("ativo") is not None:
        where.append("e.ativo = ?")
        params.append(1 if filtros["ativo"] else 0)
    if filtros.get("data_recebimento_de") is not None:
        where.append("e.data_recebimento >= ?")
        params.append(filtros["data_recebimento_de"])
    if filtros.get("data_recebimento_ate") is not None:
        where.append("e.data_recebimento <= ?")
        params.append(filtros["data_recebimento_ate"])
    q = filtros.get("q")
    if q and q.strip():
        termo = f"%{_escapar_like(q.strip().casefold())}%"
        where.append("(casefold(e.identificacao) LIKE ? ESCAPE '\\' OR casefold(e.modelo) LIKE ? ESCAPE '\\')")
        params.extend([termo, termo])
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM EQUIPAMENTO e" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY e.data_recebimento DESC, casefold(e.identificacao), e.id_equipamento "
                           "LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total


def inserir(conexao: sqlite3.Connection, d: dict) -> int:
    """UC07 passo 5: nasce ativo."""
    cursor = conexao.execute(
        "INSERT INTO EQUIPAMENTO (id_categoria, id_item_solicitacao, identificacao, modelo, condicao, origem, "
        "situacao, ativo, valor, data_recebimento) VALUES (?, ?, ?, ?, ?, ?, ?, 1, ?, ?)",
        (d["id_categoria"], d["id_item_solicitacao"], d["identificacao"], d["modelo"], d["condicao"], d["origem"],
         d["situacao"], d["valor"], d["data_recebimento"]),
    )
    return cursor.lastrowid


def atualizar(conexao: sqlite3.Connection, id_equipamento: int, d: dict) -> None:
    """UC07 FA1 (situação e ativo não são tocados)."""
    conexao.execute(
        "UPDATE EQUIPAMENTO SET id_categoria = ?, id_item_solicitacao = ?, identificacao = ?, modelo = ?, "
        "condicao = ?, origem = ?, valor = ?, data_recebimento = ? WHERE id_equipamento = ?",
        (d["id_categoria"], d["id_item_solicitacao"], d["identificacao"], d["modelo"], d["condicao"], d["origem"],
         d["valor"], d["data_recebimento"], id_equipamento),
    )


def atualizar_situacao(conexao: sqlite3.Connection, id_equipamento: int, situacao: str) -> None:
    """UC08."""
    conexao.execute("UPDATE EQUIPAMENTO SET situacao = ? WHERE id_equipamento = ?", (situacao, id_equipamento))


def atualizar_ativo(conexao: sqlite3.Connection, id_equipamento: int, ativo: bool) -> None:
    """UC07 FA2."""
    conexao.execute("UPDATE EQUIPAMENTO SET ativo = ? WHERE id_equipamento = ?", (1 if ativo else 0, id_equipamento))


def inserir_doacao(conexao: sqlite3.Connection, id_equipamento: int, id_organizacao_ong: int, data_doacao: str) -> int:
    """UC08 FE1, UC11: grava a DOACAO (na mesma transação da mudança de situação)."""
    return conexao.execute(
        "INSERT INTO DOACAO (id_equipamento, id_organizacao_ong, data_doacao) VALUES (?, ?, ?)",
        (id_equipamento, id_organizacao_ong, data_doacao),
    ).lastrowid


def atualizar_imagem(conexao: sqlite3.Connection, id_equipamento: int, imagem: str | None) -> None:
    """UC07, DP-84/DP-87: grava (ou zera) apenas o nome do arquivo da imagem."""
    conexao.execute("UPDATE EQUIPAMENTO SET imagem = ? WHERE id_equipamento = ?", (imagem, id_equipamento))
