"""SQL do marketplace (somente leitura). UC12; RN13; DP-50, DP-70: reutiliza o predicado do catálogo e exclui reservados."""
import sqlite3

from app.catalogo.repository import PREDICADO_CATALOGO, PREDICADO_NAO_RESERVADO_DOACAO, _escapar_like

# PREDICADO_CATALOGO já exclui qualquer equipamento com ITEM_VENDA (venda Pendente ou Confirmada).
_ELEGIVEL = PREDICADO_CATALOGO + " AND " + PREDICADO_NAO_RESERVADO_DOACAO + " AND c.ativa = 1"
_SELECT = """
    SELECT e.id_equipamento, e.modelo, c.nome AS categoria, e.id_categoria, e.condicao, e.valor, e.imagem
      FROM EQUIPAMENTO e JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
"""


def listar_categorias(conexao: sqlite3.Connection):
    """Categorias ativas que têm ao menos um produto exposto."""
    return conexao.execute(
        "SELECT c.id_categoria, c.nome FROM CATEGORIA c WHERE c.ativa = 1 AND EXISTS ("
        "SELECT 1 FROM EQUIPAMENTO e WHERE e.id_categoria = c.id_categoria AND " + PREDICADO_CATALOGO + " AND "
        + PREDICADO_NAO_RESERVADO_DOACAO + ") ORDER BY casefold(c.nome), c.id_categoria").fetchall()


def listar(conexao, page: int, size: int, id_categoria: int | None, busca: str | None):
    where, params = [_ELEGIVEL], []
    if id_categoria is not None:
        where.append("e.id_categoria = ?")
        params.append(id_categoria)
    if busca and busca.strip():
        where.append("casefold(e.modelo) LIKE ? ESCAPE '\\'")
        params.append(f"%{_escapar_like(busca.strip().casefold())}%")
    filtro = " WHERE " + " AND ".join(where)
    total = conexao.execute(
        "SELECT COUNT(*) FROM EQUIPAMENTO e JOIN CATEGORIA c ON c.id_categoria = e.id_categoria" + filtro, params
    ).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY casefold(e.modelo), e.id_equipamento LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size]).fetchall()
    return linhas, total


def buscar(conexao, id_equipamento: int):
    return conexao.execute(_SELECT + " WHERE e.id_equipamento = ? AND " + _ELEGIVEL, (id_equipamento,)).fetchone()
