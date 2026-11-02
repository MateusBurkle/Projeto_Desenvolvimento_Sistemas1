"""SQL do módulo 2 - organizações (consultas parametrizadas). Sem regra de negócio."""
import sqlite3

_SELECT = """
    SELECT o.id_organizacao, o.cnpj, o.nome_razao_social, o.tipo, o.telefone, o.email, o.endereco, o.situacao,
           EXISTS (SELECT 1 FROM PARCEIRO p WHERE p.id_organizacao = o.id_organizacao) AS possui_parceria
      FROM ORGANIZACAO o
"""


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def buscar_por_id(conexao: sqlite3.Connection, id_organizacao: int):
    """UC01 FA1."""
    return conexao.execute(_SELECT + " WHERE o.id_organizacao = ?", (id_organizacao,)).fetchone()


def buscar_id_por_cnpj(conexao: sqlite3.Connection, cnpj: str, excluir_id: int | None = None):
    """UC25: CNPJ entre todas as organizações; `excluir_id` desconsidera o próprio registro na alteração."""
    if excluir_id is None:
        return conexao.execute("SELECT id_organizacao FROM ORGANIZACAO WHERE cnpj = ?", (cnpj,)).fetchone()
    return conexao.execute(
        "SELECT id_organizacao FROM ORGANIZACAO WHERE cnpj = ? AND id_organizacao <> ?", (cnpj, excluir_id)
    ).fetchone()


def listar(conexao: sqlite3.Connection, page: int, size: int, tipo: str | None, situacao: str | None,
           q: str | None, sem_parceria: bool | None):
    """UC01 FA1: filtros, ordenação por nome, paginação. Devolve (linhas, total)."""
    where, params = [], []
    if tipo is not None:
        where.append("o.tipo = ?")
        params.append(tipo)
    if situacao is not None:
        where.append("o.situacao = ?")
        params.append(situacao)
    if sem_parceria:
        where.append("NOT EXISTS (SELECT 1 FROM PARCEIRO p WHERE p.id_organizacao = o.id_organizacao)")
    if q and q.strip():
        termo = q.strip().lower()
        sem_mascara = "".join(c for c in termo if c not in ".-/ ")
        cnpjs = sorted({f"%{_escapar_like(termo)}%"} | ({f"%{_escapar_like(sem_mascara)}%"} if sem_mascara else set()))
        where.append("(lower(o.nome_razao_social) LIKE ? ESCAPE '\\' OR "
                     + " OR ".join("o.cnpj LIKE ? ESCAPE '\\'" for _ in cnpjs) + ")")
        params.append(f"%{_escapar_like(termo)}%")
        params.extend(cnpjs)
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM ORGANIZACAO o" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY o.nome_razao_social COLLATE NOCASE, o.id_organizacao LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total


def inserir(conexao: sqlite3.Connection, d: dict) -> int:
    """UC01 passo 5."""
    cursor = conexao.execute(
        "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (d["cnpj"], d["nome_razao_social"], d["tipo"], d["telefone"], d["email"], d["endereco"], d["situacao"]),
    )
    conexao.commit()
    return cursor.lastrowid


def atualizar(conexao: sqlite3.Connection, id_organizacao: int, d: dict) -> None:
    """UC01 FA1 (situação não é tocada)."""
    conexao.execute(
        "UPDATE ORGANIZACAO SET cnpj = ?, nome_razao_social = ?, tipo = ?, telefone = ?, email = ?, endereco = ? "
        "WHERE id_organizacao = ?",
        (d["cnpj"], d["nome_razao_social"], d["tipo"], d["telefone"], d["email"], d["endereco"], id_organizacao),
    )
    conexao.commit()


def atualizar_contato(conexao: sqlite3.Connection, id_organizacao: int, telefone: str, email: str, endereco: str) -> None:
    """RF09, DP-26."""
    conexao.execute(
        "UPDATE ORGANIZACAO SET telefone = ?, email = ?, endereco = ? WHERE id_organizacao = ?",
        (telefone, email, endereco, id_organizacao),
    )
    conexao.commit()


def atualizar_dados_proprios(conexao: sqlite3.Connection, id_organizacao: int, nome: str, telefone: str, email: str,
                             endereco: str) -> None:
    """DP-93: nome e contato; cnpj, tipo e situação nunca são tocados."""
    conexao.execute(
        "UPDATE ORGANIZACAO SET nome_razao_social = ?, telefone = ?, email = ?, endereco = ? WHERE id_organizacao = ?",
        (nome, telefone, email, endereco, id_organizacao),
    )
    conexao.commit()


def atualizar_situacao(conexao: sqlite3.Connection, id_organizacao: int, situacao: str) -> None:
    """UC01 FA2: apenas a situação (sem cascata)."""
    conexao.execute("UPDATE ORGANIZACAO SET situacao = ? WHERE id_organizacao = ?", (situacao, id_organizacao))
    conexao.commit()


def contar_usuarios(conexao: sqlite3.Connection, id_organizacao: int) -> int:
    """RN06 (DP-23): usuários vinculados à organização."""
    return conexao.execute("SELECT COUNT(*) FROM USUARIO WHERE id_organizacao = ?", (id_organizacao,)).fetchone()[0]


def listar_usuarios(conexao: sqlite3.Connection, id_organizacao: int) -> list[dict]:
    """DP-63: usuários vinculados (para a confirmação no front)."""
    linhas = conexao.execute(
        "SELECT id_usuario, nome, email, perfil FROM USUARIO WHERE id_organizacao = ? ORDER BY nome, id_usuario",
        (id_organizacao,)).fetchall()
    return [dict(l) for l in linhas]


def possui_parceria_doadora(conexao: sqlite3.Connection, id_organizacao: int) -> bool:
    """RN06 (DP-23): parceria com atuação 'Empresa Doadora' (qualquer situação)."""
    return conexao.execute(
        "SELECT 1 FROM PARCEIRO WHERE id_organizacao = ? AND tipo_parceria = 'Empresa Doadora'", (id_organizacao,)
    ).fetchone() is not None


def possui_historico(conexao: sqlite3.Connection, id_organizacao: int) -> bool:
    """DP-63: histórico = solicitação (doadora), venda (cliente) ou doação (ONG). Equipamentos chegam à organização
    por ITEM_SOLICITACAO -> SOLICITACAO, então já estão cobertos. Usuários e parceria NÃO contam."""
    return conexao.execute(
        "SELECT EXISTS (SELECT 1 FROM SOLICITACAO WHERE id_organizacao_doadora = :o) "
        "OR EXISTS (SELECT 1 FROM VENDA WHERE id_organizacao_cliente = :o) "
        "OR EXISTS (SELECT 1 FROM DOACAO WHERE id_organizacao_ong = :o) "
        "OR EXISTS (SELECT 1 FROM SOLICITACAO_DOACAO WHERE id_organizacao_ong = :o)",  # Módulo 7: solicitação de doação é histórico
        {"o": id_organizacao}
    ).fetchone()[0] == 1


def excluir_com_vinculos(conexao: sqlite3.Connection, id_organizacao: int) -> None:
    """DP-63: remove usuários, parceria e organização numa única transação (rollback em qualquer falha)."""
    try:
        conexao.execute("DELETE FROM USUARIO WHERE id_organizacao = ?", (id_organizacao,))
        conexao.execute("DELETE FROM PARCEIRO WHERE id_organizacao = ?", (id_organizacao,))
        conexao.execute("DELETE FROM ORGANIZACAO WHERE id_organizacao = ?", (id_organizacao,))
        conexao.commit()
    except sqlite3.Error:
        conexao.rollback()
        raise
