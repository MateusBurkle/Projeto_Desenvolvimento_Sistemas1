"""SQL do módulo 5 - vendas/pedidos (consultas parametrizadas). UC13, UC14, UC15, UC18, UC21; RN13, RN14, RN15.
Gravações NÃO fazem commit: o service controla a transação (UC15 FE1)."""
import sqlite3

from app.catalogo.repository import PREDICADO_CATALOGO


def iniciar_transacao(conexao: sqlite3.Connection) -> None:
    """Bloqueia escritores concorrentes desde o início (sem corrida entre verificação e gravação)."""
    conexao.execute("BEGIN IMMEDIATE")


def _marcas(n: int) -> str:
    return ",".join("?" * n)  # apenas placeholders; os valores sempre vão como parâmetros


_RESUMO = """
    SELECT v.id_venda, v.id_organizacao_cliente, o.nome_razao_social AS nome_organizacao, v.data_venda, v.situacao,
           v.forma_pagamento,
           (SELECT COUNT(*) FROM ITEM_VENDA iv WHERE iv.id_venda = v.id_venda) AS quantidade,
           (SELECT COALESCE(SUM(iv.valor), 0) FROM ITEM_VENDA iv WHERE iv.id_venda = v.id_venda) AS valor_total,
           EXISTS (SELECT 1 FROM NOTA_FISCAL_SIMULADA n WHERE n.id_venda = v.id_venda) AS possui_nota
      FROM VENDA v
      JOIN ORGANIZACAO o ON o.id_organizacao = v.id_organizacao_cliente
"""


def buscar_venda(conexao: sqlite3.Connection, id_venda: int):
    """UC14 passo 2, UC18 passo 4, UC21 passo 5."""
    return conexao.execute(_RESUMO + " WHERE v.id_venda = ?", (id_venda,)).fetchone()


def listar_itens(conexao: sqlite3.Connection, id_venda: int):
    return conexao.execute(
        """SELECT iv.id_item_venda, iv.id_equipamento, e.identificacao, e.modelo, c.nome AS categoria_nome,
                  e.condicao, iv.valor
             FROM ITEM_VENDA iv
             JOIN EQUIPAMENTO e ON e.id_equipamento = iv.id_equipamento
             JOIN CATEGORIA c ON c.id_categoria = e.id_categoria
            WHERE iv.id_venda = ? ORDER BY iv.id_item_venda""", (id_venda,)).fetchall()


def buscar_nota(conexao: sqlite3.Connection, id_venda: int):
    return conexao.execute(
        "SELECT id_nota, numero, data_emissao FROM NOTA_FISCAL_SIMULADA WHERE id_venda = ?", (id_venda,)).fetchone()


def listar(conexao: sqlite3.Connection, page: int, size: int, filtros: dict):
    """UC21 passo 2-4, UC18 passo 2: data_venda desc, depois id desc. Devolve (linhas, total)."""
    where, params = [], []
    if filtros.get("id_organizacao_cliente") is not None:
        where.append("v.id_organizacao_cliente = ?")
        params.append(filtros["id_organizacao_cliente"])
    if filtros.get("situacao") is not None:
        where.append("v.situacao = ?")
        params.append(filtros["situacao"])
    if filtros.get("data_de") is not None:
        where.append("v.data_venda >= ?")
        params.append(filtros["data_de"])
    if filtros.get("data_ate") is not None:
        where.append("v.data_venda <= ?")
        params.append(filtros["data_ate"])
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM VENDA v" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        _RESUMO + filtro + " ORDER BY v.data_venda DESC, v.id_venda DESC LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size]).fetchall()
    return linhas, total


def buscar_organizacao(conexao: sqlite3.Connection, id_organizacao: int):
    return conexao.execute(
        "SELECT id_organizacao, tipo, situacao FROM ORGANIZACAO WHERE id_organizacao = ?", (id_organizacao,)).fetchone()


def ids_reservados_por_doacao(conexao: sqlite3.Connection, ids: list[int]) -> set[int]:
    """Módulo 7, DP-70: equipamentos com solicitação de doação Pendente (-> 422 EQUIPAMENTO_RESERVADO)."""
    if not ids:
        return set()
    linhas = conexao.execute(
        f"SELECT DISTINCT i.id_equipamento FROM ITEM_SOLICITACAO_DOACAO i JOIN SOLICITACAO_DOACAO s "
        f"ON s.id_solicitacao_doacao = i.id_solicitacao_doacao WHERE s.situacao = 'Pendente' "
        f"AND i.id_equipamento IN ({_marcas(len(ids))})", ids).fetchall()
    return {l[0] for l in linhas}


def ids_aptos_catalogo(conexao: sqlite3.Connection, ids: list[int]) -> set[int]:
    """RN13, DP-50: dos ids informados, os que atendem às regras do catálogo (inclui 'sem linha em ITEM_VENDA')."""
    if not ids:
        return set()
    linhas = conexao.execute(
        f"SELECT e.id_equipamento FROM EQUIPAMENTO e WHERE e.id_equipamento IN ({_marcas(len(ids))}) AND "
        + PREDICADO_CATALOGO, ids).fetchall()
    return {l[0] for l in linhas}


def ids_aptos_confirmacao(conexao: sqlite3.Connection, ids: list[int]) -> set[int]:
    """UC14 passo 4, RN13, DP-48: ativo, 'Disponível' e condição apta (o item já está reservado no pedido)."""
    if not ids:
        return set()
    linhas = conexao.execute(
        f"SELECT e.id_equipamento FROM EQUIPAMENTO e WHERE e.id_equipamento IN ({_marcas(len(ids))}) "
        "AND e.ativo = 1 AND e.situacao = 'Disponível' "
        "AND e.condicao NOT IN ('A avaliar', 'Sem condições de reuso')", ids).fetchall()
    return {l[0] for l in linhas}


def inserir_venda(conexao: sqlite3.Connection, id_organizacao: int, data_venda: str, forma_pagamento: str) -> int:
    """UC13 passo 4, DP-46: nasce 'Pendente'."""
    return conexao.execute(
        "INSERT INTO VENDA (id_organizacao_cliente, data_venda, situacao, forma_pagamento) VALUES (?, ?, 'Pendente', ?)",
        (id_organizacao, data_venda, forma_pagamento)).lastrowid


def inserir_item(conexao: sqlite3.Connection, id_venda: int, id_equipamento: int) -> None:
    """DP-48: o valor do item é o EQUIPAMENTO.valor congelado no momento do pedido."""
    conexao.execute(
        "INSERT INTO ITEM_VENDA (id_venda, id_equipamento, valor) SELECT ?, id_equipamento, valor "
        "FROM EQUIPAMENTO WHERE id_equipamento = ?", (id_venda, id_equipamento))


def ids_equipamento_da_venda(conexao: sqlite3.Connection, id_venda: int) -> list[int]:
    return [l[0] for l in conexao.execute(
        "SELECT id_equipamento FROM ITEM_VENDA WHERE id_venda = ? ORDER BY id_item_venda", (id_venda,))]


def apagar_itens(conexao: sqlite3.Connection, id_venda: int, ids_equipamento: list[int] | None = None) -> None:
    """DP-45: única exclusão física do módulo (itens de venda Pendente). Sem `ids`, apaga todos os itens do pedido."""
    if ids_equipamento is None:
        conexao.execute("DELETE FROM ITEM_VENDA WHERE id_venda = ?", (id_venda,))
    elif ids_equipamento:
        conexao.execute(
            f"DELETE FROM ITEM_VENDA WHERE id_venda = ? AND id_equipamento IN ({_marcas(len(ids_equipamento))})",
            [id_venda, *ids_equipamento])


def atualizar_situacao(conexao: sqlite3.Connection, id_venda: int, situacao: str) -> None:
    conexao.execute("UPDATE VENDA SET situacao = ? WHERE id_venda = ?", (situacao, id_venda))


def atualizar_forma_pagamento(conexao: sqlite3.Connection, id_venda: int, forma_pagamento: str) -> None:
    conexao.execute("UPDATE VENDA SET forma_pagamento = ? WHERE id_venda = ?", (forma_pagamento, id_venda))


def confirmar(conexao: sqlite3.Connection, id_venda: int, data_venda: str, forma_pagamento: str) -> None:
    """UC14 passo 5: 'Confirmada' com data e forma de pagamento informadas."""
    conexao.execute(
        "UPDATE VENDA SET situacao = 'Confirmada', data_venda = ?, forma_pagamento = ? WHERE id_venda = ?",
        (data_venda, forma_pagamento, id_venda))
