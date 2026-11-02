"""SQL do módulo 4 - solicitações (consultas parametrizadas). Sem regra de negócio e sem commit:
o service controla a transação (UC10: equipamento + situação da solicitação juntos)."""
import sqlite3

# DP-41/DP-42: situações que contam como "destinação registrada" (texto fixo, sem valores do usuário)
_SITUACOES_DESTINADAS = "('Disponível', 'Doado', 'Vendido', 'Destinado à reciclagem')"
_AVALIADO = f"e.condicao <> 'A avaliar' AND e.situacao IN {_SITUACOES_DESTINADAS}"


def buscar_organizacao(conexao: sqlite3.Connection, id_organizacao: int):
    """UC09 FE2: organização do token."""
    return conexao.execute(
        "SELECT id_organizacao, nome_razao_social, tipo, situacao FROM ORGANIZACAO WHERE id_organizacao = ?",
        (id_organizacao,),
    ).fetchone()


def parceria_doadora_ativa(conexao: sqlite3.Connection, id_organizacao: int) -> bool:
    """UC09 FE3, RN10: vínculo de parceria 'Empresa Doadora' com situação 'Ativa'."""
    return conexao.execute(
        "SELECT 1 FROM PARCEIRO WHERE id_organizacao = ? AND tipo_parceria = 'Empresa Doadora' "
        "AND situacao_parceria = 'Ativa'",
        (id_organizacao,),
    ).fetchone() is not None


def inserir_solicitacao(conexao: sqlite3.Connection, id_organizacao: int, data_solicitacao: str, situacao: str) -> int:
    """UC09 passo 5."""
    return conexao.execute(
        "INSERT INTO SOLICITACAO (id_organizacao_doadora, data_solicitacao, situacao) VALUES (?, ?, ?)",
        (id_organizacao, data_solicitacao, situacao),
    ).lastrowid


def inserir_item(conexao: sqlite3.Connection, id_solicitacao: int, tipo: str, modelo: str, quantidade: int) -> int:
    """UC09 passo 3 (RN11: tipo, modelo e quantidade ficam registrados)."""
    return conexao.execute(
        "INSERT INTO ITEM_SOLICITACAO (id_solicitacao, tipo, modelo, quantidade) VALUES (?, ?, ?, ?)",
        (id_solicitacao, tipo, modelo, quantidade),
    ).lastrowid


def buscar_solicitacao(conexao: sqlite3.Connection, id_solicitacao: int):
    """UC09 FA1, UC20 passo 3."""
    return conexao.execute(
        "SELECT s.id_solicitacao, s.id_organizacao_doadora, o.nome_razao_social AS nome_organizacao, "
        "s.data_solicitacao, s.situacao FROM SOLICITACAO s "
        "JOIN ORGANIZACAO o ON o.id_organizacao = s.id_organizacao_doadora WHERE s.id_solicitacao = ?",
        (id_solicitacao,),
    ).fetchone()


def buscar_item(conexao: sqlite3.Connection, id_item_solicitacao: int):
    """UC10 passo 3: item (com a solicitação a que pertence)."""
    return conexao.execute(
        "SELECT id_item_solicitacao, id_solicitacao, tipo, modelo, quantidade FROM ITEM_SOLICITACAO "
        "WHERE id_item_solicitacao = ?",
        (id_item_solicitacao,),
    ).fetchone()


def listar_itens(conexao: sqlite3.Connection, id_solicitacao: int):
    """UC10 passo 2."""
    return conexao.execute(
        "SELECT id_item_solicitacao, tipo, modelo, quantidade FROM ITEM_SOLICITACAO "
        "WHERE id_solicitacao = ? ORDER BY id_item_solicitacao",
        (id_solicitacao,),
    ).fetchall()


def listar_equipamentos(conexao: sqlite3.Connection, id_solicitacao: int):
    """UC10/UC20: equipamentos vinculados a qualquer item da solicitação, com categoria e doação."""
    return conexao.execute(
        "SELECT e.id_equipamento, e.id_item_solicitacao, e.identificacao, e.id_categoria, c.nome AS categoria_nome, "
        "e.modelo, e.condicao, e.situacao, e.ativo, e.valor, e.data_recebimento, "
        "d.id_organizacao_ong, o.nome_razao_social AS nome_ong, d.data_doacao "
        "FROM EQUIPAMENTO e JOIN ITEM_SOLICITACAO i ON i.id_item_solicitacao = e.id_item_solicitacao "
        "JOIN CATEGORIA c ON c.id_categoria = e.id_categoria "
        "LEFT JOIN DOACAO d ON d.id_equipamento = e.id_equipamento "
        "LEFT JOIN ORGANIZACAO o ON o.id_organizacao = d.id_organizacao_ong "
        "WHERE i.id_solicitacao = ? ORDER BY e.id_equipamento",
        (id_solicitacao,),
    ).fetchall()


def buscar_equipamento_vinculado(conexao: sqlite3.Connection, id_solicitacao: int, id_equipamento: int):
    """UC10 passo 4: equipamento precisa estar vinculado a um item DESTA solicitação."""
    return conexao.execute(
        "SELECT e.id_equipamento, e.situacao, e.condicao, e.id_item_solicitacao FROM EQUIPAMENTO e "
        "JOIN ITEM_SOLICITACAO i ON i.id_item_solicitacao = e.id_item_solicitacao "
        "WHERE i.id_solicitacao = ? AND e.id_equipamento = ?",
        (id_solicitacao, id_equipamento),
    ).fetchone()


def buscar_solicitacao_do_item(conexao: sqlite3.Connection, id_item_solicitacao: int):
    """DP-40: solicitação (id e situação atual) a que o item pertence."""
    return conexao.execute(
        "SELECT s.id_solicitacao, s.situacao FROM ITEM_SOLICITACAO i "
        "JOIN SOLICITACAO s ON s.id_solicitacao = i.id_solicitacao WHERE i.id_item_solicitacao = ?",
        (id_item_solicitacao,),
    ).fetchone()


def contar_equipamentos_do_item(conexao: sqlite3.Connection, id_item_solicitacao: int) -> int:
    """UC10 (DP-41): equipamentos já vinculados ao item."""
    return conexao.execute(
        "SELECT COUNT(*) FROM EQUIPAMENTO WHERE id_item_solicitacao = ?", (id_item_solicitacao,)
    ).fetchone()[0]


def contagens_dos_itens(conexao: sqlite3.Connection, id_solicitacao: int):
    """DP-40/DP-41: por item, quantidade, equipamentos cadastrados e avaliados (condição avaliada + destinação)."""
    return conexao.execute(
        "SELECT i.id_item_solicitacao, i.quantidade, "
        "COUNT(e.id_equipamento) AS cadastrada, "
        f"COALESCE(SUM(CASE WHEN {_AVALIADO} THEN 1 ELSE 0 END), 0) AS avaliada "
        "FROM ITEM_SOLICITACAO i LEFT JOIN EQUIPAMENTO e ON e.id_item_solicitacao = i.id_item_solicitacao "
        "WHERE i.id_solicitacao = ? GROUP BY i.id_item_solicitacao, i.quantidade ORDER BY i.id_item_solicitacao",
        (id_solicitacao,),
    ).fetchall()


def atualizar_situacao(conexao: sqlite3.Connection, id_solicitacao: int, situacao: str) -> None:
    """DP-40."""
    conexao.execute("UPDATE SOLICITACAO SET situacao = ? WHERE id_solicitacao = ?", (situacao, id_solicitacao))


def listar(conexao: sqlite3.Connection, page: int, size: int, filtros: dict):
    """UC20 passo 1-3, UC10 passo 1: filtros, ordenação por data desc e id desc, resumo por solicitação."""
    where, params = [], []
    if filtros.get("id_organizacao_doadora") is not None:
        where.append("s.id_organizacao_doadora = ?")
        params.append(filtros["id_organizacao_doadora"])
    if filtros.get("situacao") is not None:
        where.append("s.situacao = ?")
        params.append(filtros["situacao"])
    if filtros.get("data_de") is not None:
        where.append("s.data_solicitacao >= ?")
        params.append(filtros["data_de"])
    if filtros.get("data_ate") is not None:
        where.append("s.data_solicitacao <= ?")
        params.append(filtros["data_ate"])
    filtro = (" WHERE " + " AND ".join(where)) if where else ""
    total = conexao.execute("SELECT COUNT(*) FROM SOLICITACAO s" + filtro, params).fetchone()[0]
    linhas = conexao.execute(
        "SELECT s.id_solicitacao, s.id_organizacao_doadora, o.nome_razao_social AS nome_organizacao, "
        "s.data_solicitacao, s.situacao, "
        "(SELECT COUNT(*) FROM ITEM_SOLICITACAO i WHERE i.id_solicitacao = s.id_solicitacao) AS total_itens, "
        "(SELECT COALESCE(SUM(i.quantidade), 0) FROM ITEM_SOLICITACAO i WHERE i.id_solicitacao = s.id_solicitacao) "
        "AS total_unidades, "
        "(SELECT COUNT(*) FROM EQUIPAMENTO e JOIN ITEM_SOLICITACAO i ON i.id_item_solicitacao = e.id_item_solicitacao "
        f"WHERE i.id_solicitacao = s.id_solicitacao AND {_AVALIADO}) AS unidades_avaliadas "
        "FROM SOLICITACAO s JOIN ORGANIZACAO o ON o.id_organizacao = s.id_organizacao_doadora"
        + filtro + " ORDER BY s.data_solicitacao DESC, s.id_solicitacao DESC LIMIT ? OFFSET ?",
        [*params, size, (page - 1) * size],
    ).fetchall()
    return linhas, total
