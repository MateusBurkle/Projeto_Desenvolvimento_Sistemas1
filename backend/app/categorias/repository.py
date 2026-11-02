"""SQL do módulo 3 - categorias (consultas parametrizadas). Sem regra de negócio e sem commit (o service controla)."""
import sqlite3

_SELECT = """
    SELECT c.id_categoria, c.nome, c.ativa,
           (SELECT COUNT(*) FROM EQUIPAMENTO e WHERE e.id_categoria = c.id_categoria) AS total_equipamentos
      FROM CATEGORIA c
"""


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def buscar_por_id(conexao: sqlite3.Connection, id_categoria: int):
    """UC05 FA1."""
    return conexao.execute(_SELECT + " WHERE c.id_categoria = ?", (id_categoria,)).fetchone()


def buscar_id_por_nome(conexao: sqlite3.Connection, nome: str, excluir_id: int | None = None):
    """UC05, DP-31: nome sem diferenciar caixa; `excluir_id` desconsidera o próprio registro na alteração."""
    if excluir_id is None:
        return conexao.execute(
            "SELECT id_categoria FROM CATEGORIA WHERE casefold(nome) = ?", (nome.casefold(),)
        ).fetchone()
    return conexao.execute(
        "SELECT id_categoria FROM CATEGORIA WHERE casefold(nome) = ? AND id_categoria <> ?",
        (nome.casefold(), excluir_id),
    ).fetchone()


def listar(conexao: sqlite3.Connection, page: int, size: int, ativa: bool | None, q: str | None):
    """UC05 FA1: filtros `ativa` e `q`, ordenação por nome, paginação. Devolve (linhas, total)."""
    where, params = [], []
    if ativa is not None:
        where.append("c.ativa = ?")
        params.append(1 if ativa else 0)
    if q and q.strip():
        where.append("casefold(c.nome) LIKE ? ESCAPE '\\'")
        params.append(f"%{_escapar_like(q.strip().casefold())}%")
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM CATEGORIA c" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY casefold(c.nome), c.id_categoria LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total


def inserir(conexao: sqlite3.Connection, nome: str) -> int:
    """UC05 passo 4: grava Ativa."""
    return conexao.execute("INSERT INTO CATEGORIA (nome, ativa) VALUES (?, 1)", (nome,)).lastrowid


def atualizar_nome(conexao: sqlite3.Connection, id_categoria: int, nome: str) -> None:
    """UC05 FA1: só o nome (o id e os vínculos não mudam)."""
    conexao.execute("UPDATE CATEGORIA SET nome = ? WHERE id_categoria = ?", (nome, id_categoria))


def atualizar_ativa(conexao: sqlite3.Connection, id_categoria: int, ativa: bool) -> None:
    """UC05 FA2, RN07."""
    conexao.execute("UPDATE CATEGORIA SET ativa = ? WHERE id_categoria = ?", (1 if ativa else 0, id_categoria))
