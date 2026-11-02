"""SQL do módulo 5 - catálogo (UC12; RN13; DP-50). Consultas parametrizadas, somente leitura."""
import sqlite3

# UC12 passo 2, RN13, DP-50: ativo, Disponível, condição apta, valor > 0 e SEM linha em ITEM_VENDA (nem em pedido Pendente).
PREDICADO_CATALOGO = (
    "e.ativo = 1 AND e.situacao = 'Disponível' "
    "AND e.condicao NOT IN ('A avaliar', 'Sem condições de reuso') "
    "AND e.valor IS NOT NULL AND e.valor > 0 "
    "AND NOT EXISTS (SELECT 1 FROM ITEM_VENDA iv WHERE iv.id_equipamento = e.id_equipamento)"
)

# Módulo 7, DP-70: reservado por solicitação de doação Pendente sai do catálogo e do marketplace.
PREDICADO_NAO_RESERVADO_DOACAO = (
    "NOT EXISTS (SELECT 1 FROM ITEM_SOLICITACAO_DOACAO isd JOIN SOLICITACAO_DOACAO sd "
    "ON sd.id_solicitacao_doacao = isd.id_solicitacao_doacao "
    "WHERE isd.id_equipamento = e.id_equipamento AND sd.situacao = 'Pendente')"
)

_SELECT = """
    SELECT e.id_equipamento, e.identificacao, e.id_categoria, c.nome AS categoria_nome, e.modelo, e.condicao, e.valor
      FROM EQUIPAMENTO e
      JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
"""


def _escapar_like(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def listar(conexao: sqlite3.Connection, page: int, size: int, id_categoria: int | None, q: str | None):
    """UC12 passo 1-2: ordenado por modelo (sem caixa), depois id. Devolve (linhas, total)."""
    where, params = [PREDICADO_CATALOGO, PREDICADO_NAO_RESERVADO_DOACAO], []
    if id_categoria is not None:
        where.append("e.id_categoria = ?")
        params.append(id_categoria)
    if q and q.strip():
        where.append("casefold(e.modelo) LIKE ? ESCAPE '\\'")
        params.append(f"%{_escapar_like(q.strip().casefold())}%")
    filtro = " WHERE " + " AND ".join(where)
    total = conexao.execute(
        "SELECT COUNT(*) FROM EQUIPAMENTO e JOIN CATEGORIA c ON c.id_categoria = e.id_categoria" + filtro, params
    ).fetchone()[0]
    linhas = conexao.execute(
        _SELECT + filtro + " ORDER BY casefold(e.modelo), e.id_equipamento LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total


def buscar_por_id(conexao: sqlite3.Connection, id_equipamento: int):
    """UC12 passo 3-4: só devolve se o equipamento atende às regras do catálogo."""
    return conexao.execute(
        _SELECT + " WHERE e.id_equipamento = ? AND " + PREDICADO_CATALOGO + " AND " + PREDICADO_NAO_RESERVADO_DOACAO, (id_equipamento,)
    ).fetchone()
