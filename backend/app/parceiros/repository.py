"""SQL do módulo 2 - parceiros (consultas parametrizadas). Sem regra de negócio."""
import sqlite3

_SELECT = """
    SELECT p.id_parceiro, p.id_organizacao, p.tipo_parceria, p.situacao_parceria,
           o.nome_razao_social, o.cnpj, o.telefone, o.email, o.endereco,
           o.tipo AS tipo_organizacao, o.situacao AS situacao_organizacao
      FROM PARCEIRO p
      JOIN ORGANIZACAO o ON o.id_organizacao = p.id_organizacao
"""


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def buscar_por_id(conexao: sqlite3.Connection, id_parceiro: int):
    """UC06 FA1: parceiro com dados da organização por junção."""
    return conexao.execute(_SELECT + " WHERE p.id_parceiro = ?", (id_parceiro,)).fetchone()


def buscar_organizacao(conexao: sqlite3.Connection, id_organizacao: int):
    """UC06 passo 4 / FE3: organização (existência, tipo, situação)."""
    return conexao.execute(
        "SELECT id_organizacao, tipo, situacao FROM ORGANIZACAO WHERE id_organizacao = ?", (id_organizacao,)
    ).fetchone()


def existe_parceria(conexao: sqlite3.Connection, id_organizacao: int) -> bool:
    """RF10, UC06 FE3: no máximo uma parceria por organização."""
    return conexao.execute("SELECT 1 FROM PARCEIRO WHERE id_organizacao = ?", (id_organizacao,)).fetchone() is not None


def listar(conexao: sqlite3.Connection, page: int, size: int, tipo_parceria: str | None,
           situacao_parceria: str | None, q: str | None):
    """UC06 FA1: filtros, ordenação por nome da organização, paginação. Devolve (linhas, total)."""
    where, params = [], []
    if tipo_parceria is not None:
        where.append("p.tipo_parceria = ?")
        params.append(tipo_parceria)
    if situacao_parceria is not None:
        where.append("p.situacao_parceria = ?")
        params.append(situacao_parceria)
    if q and q.strip():
        termo = q.strip().lower()
        sem_mascara = "".join(c for c in termo if c not in ".-/ ")
        cnpjs = sorted({f"%{_escapar_like(termo)}%"} | ({f"%{_escapar_like(sem_mascara)}%"} if sem_mascara else set()))
        where.append("(lower(o.nome_razao_social) LIKE ? ESCAPE '\\' OR "
                     + " OR ".join("o.cnpj LIKE ? ESCAPE '\\'" for _ in cnpjs) + ")")
        params.append(f"%{_escapar_like(termo)}%")
        params.extend(cnpjs)
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute(
        "SELECT COUNT(*) FROM PARCEIRO p JOIN ORGANIZACAO o ON o.id_organizacao = p.id_organizacao" + filtro, params
    ).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY o.nome_razao_social COLLATE NOCASE, p.id_parceiro LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total


def inserir(conexao: sqlite3.Connection, id_organizacao: int, tipo_parceria: str, situacao_parceria: str) -> int:
    """UC06 passo 4."""
    cursor = conexao.execute(
        "INSERT INTO PARCEIRO (id_organizacao, tipo_parceria, situacao_parceria) VALUES (?, ?, ?)",
        (id_organizacao, tipo_parceria, situacao_parceria),
    )
    conexao.commit()
    return cursor.lastrowid


def atualizar_tipo(conexao: sqlite3.Connection, id_parceiro: int, tipo_parceria: str) -> None:
    """UC06 FA1: só a atuação."""
    conexao.execute("UPDATE PARCEIRO SET tipo_parceria = ? WHERE id_parceiro = ?", (tipo_parceria, id_parceiro))
    conexao.commit()


def atualizar_situacao(conexao: sqlite3.Connection, id_parceiro: int, situacao_parceria: str) -> None:
    """UC06 FA2, RN10."""
    conexao.execute(
        "UPDATE PARCEIRO SET situacao_parceria = ? WHERE id_parceiro = ?", (situacao_parceria, id_parceiro)
    )
    conexao.commit()
