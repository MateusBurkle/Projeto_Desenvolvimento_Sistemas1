"""SQL do módulo 1 (consultas parametrizadas; nenhum valor é concatenado). Sem regra de negócio."""
import sqlite3

_SELECT = """
    SELECT u.id_usuario, u.id_organizacao, u.email, u.perfil, u.nome, o.nome_razao_social AS nome_organizacao
      FROM USUARIO u
      LEFT JOIN ORGANIZACAO o ON o.id_organizacao = u.id_organizacao
"""


def buscar_por_id(conexao: sqlite3.Connection, id_usuario: int):
    """UC02 FA1: conta com nome da organização (sem senha_hash)."""
    return conexao.execute(_SELECT + " WHERE u.id_usuario = ?", (id_usuario,)).fetchone()


def buscar_id_por_email(conexao: sqlite3.Connection, email: str, excluir_id: int | None = None):
    """UC26: duplicidade sem diferenciar caixa; `excluir_id` desconsidera a própria conta na alteração."""
    if excluir_id is None:
        return conexao.execute("SELECT id_usuario FROM USUARIO WHERE lower(email) = ?", (email,)).fetchone()
    return conexao.execute(
        "SELECT id_usuario FROM USUARIO WHERE lower(email) = ? AND id_usuario <> ?", (email, excluir_id)
    ).fetchone()


def buscar_organizacao(conexao: sqlite3.Connection, id_organizacao: int):
    """UC02 FE2, RN06/RN09: organização (para checar existência, situação e tipo)."""
    return conexao.execute(
        "SELECT id_organizacao, tipo, situacao FROM ORGANIZACAO WHERE id_organizacao = ?", (id_organizacao,)
    ).fetchone()


def listar_organizacoes_ativas(conexao: sqlite3.Connection, situacao_ativa: str, tipo: str | None):
    """UC02 passo 2 (DP-15): somente leitura, organizações ativas."""
    sql = "SELECT id_organizacao, nome_razao_social, tipo FROM ORGANIZACAO WHERE situacao = ?"
    params: list = [situacao_ativa]
    if tipo is not None:
        sql += " AND tipo = ?"
        params.append(tipo)
    return conexao.execute(sql + " ORDER BY nome_razao_social COLLATE NOCASE", params).fetchall()


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def listar(conexao: sqlite3.Connection, page: int, size: int, perfil: str | None = None,
           id_organizacao: int | None = None, q: str | None = None):
    """UC02 FA1 / UC03 FA1: filtros opcionais, ordenação por nome, paginação. Devolve (linhas, total)."""
    where, params = [], []
    if perfil is not None:
        where.append("u.perfil = ?")
        params.append(perfil)
    if id_organizacao is not None:
        where.append("u.id_organizacao = ?")
        params.append(id_organizacao)
    if q and q.strip():
        padrao = f"%{_escapar_like(q.strip().lower())}%"
        where.append("(lower(u.nome) LIKE ? ESCAPE '\\' OR lower(u.email) LIKE ? ESCAPE '\\')")
        params.extend([padrao, padrao])
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM USUARIO u" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY u.nome COLLATE NOCASE, u.id_usuario LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total


def contar_por_perfil(conexao: sqlite3.Connection, perfil: str) -> int:
    """RN02 (UC02 FE4): usado para proteger a última conta Administrador."""
    return conexao.execute("SELECT COUNT(*) FROM USUARIO WHERE perfil = ?", (perfil,)).fetchone()[0]


def inserir(conexao: sqlite3.Connection, nome: str, email: str, senha_hash: str, perfil: str,
            id_organizacao: int | None) -> int:
    """UC02 passo 5 / UC03 passo 4."""
    cursor = conexao.execute(
        "INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (?, ?, ?, ?, ?)",
        (id_organizacao, email, perfil, senha_hash, nome),
    )
    conexao.commit()
    return cursor.lastrowid


def atualizar(conexao: sqlite3.Connection, id_usuario: int, nome: str, email: str, perfil: str,
              id_organizacao: int | None, senha_hash: str | None) -> None:
    """UC02 FA1/FA2: a senha só é tocada se um novo hash for informado."""
    if senha_hash is None:
        conexao.execute(
            "UPDATE USUARIO SET nome = ?, email = ?, perfil = ?, id_organizacao = ? WHERE id_usuario = ?",
            (nome, email, perfil, id_organizacao, id_usuario),
        )
    else:
        conexao.execute(
            "UPDATE USUARIO SET nome = ?, email = ?, perfil = ?, id_organizacao = ?, senha_hash = ? WHERE id_usuario = ?",
            (nome, email, perfil, id_organizacao, senha_hash, id_usuario),
        )
    conexao.commit()


def atualizar_nome_email(conexao: sqlite3.Connection, id_usuario: int, nome: str, email: str) -> None:
    """DP-95: só nome e e-mail; perfil e organização nunca são tocados."""
    conexao.execute("UPDATE USUARIO SET nome = ?, email = ? WHERE id_usuario = ?", (nome, email, id_usuario))
    conexao.commit()


def atualizar_senha_hash(conexao: sqlite3.Connection, id_usuario: int, senha_hash: str) -> None:
    """DP-96: grava somente o novo hash."""
    conexao.execute("UPDATE USUARIO SET senha_hash = ? WHERE id_usuario = ?", (senha_hash, id_usuario))
    conexao.commit()


def excluir(conexao: sqlite3.Connection, id_usuario: int) -> None:
    """UC02 FA3: exclusão física (exceção aprovada em docs/CONVENCOES.md)."""
    conexao.execute("DELETE FROM USUARIO WHERE id_usuario = ?", (id_usuario,))
    conexao.commit()


def buscar_senha_hash(conexao: sqlite3.Connection, id_usuario: int) -> str | None:
    """DP-64: hash da senha atual para confirmar a autoexclusão (nunca devolvido ao cliente, RNF03)."""
    linha = conexao.execute("SELECT senha_hash FROM USUARIO WHERE id_usuario = ?", (id_usuario,)).fetchone()
    return None if linha is None else linha["senha_hash"]


def inserir_administrador(conexao: sqlite3.Connection, nome: str, email: str, senha_hash: str) -> int:
    """Carga inicial (DP-04): cria usuário Administrador sem organização."""
    return inserir(conexao, nome, email, senha_hash, "Administrador", None)
