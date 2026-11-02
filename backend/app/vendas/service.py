"""Regras de negócio do módulo 5 - vendas/pedidos: UC13, UC14, UC15, UC18, UC21.
RF13, RF14, RF15; RN03, RN04, RN13, RN14, RN15; DP-45 a DP-51.

Toda gravação roda dentro de `_transacao` (BEGIN IMMEDIATE + commit/rollback), de modo que verificação e gravação
formam uma unidade sem corrida. A confirmação reaproveita `equipamentos.service.mudar_situacao(permitir_vendido=True,
commit=False)` dentro da mesma transação (UC15, RN14).
"""
import logging
from contextlib import contextmanager
from datetime import date

from app.equipamentos import service as equipamentos_service
from app.erros import ErroApi
from app.permissoes import ADMINISTRADOR, CLIENTE_EMPRESA, FUNCIONARIO
from app.vendas import repository

log = logging.getLogger("leaf_ti")

SIT_PENDENTE = "Pendente"
SIT_CONFIRMADA = "Confirmada"
SIT_CANCELADA = "Cancelada"
FORMA_A_DEFINIR = "A definir"  # DP-46
SITUACAO_ORG_ATIVA = "Ativa"
_MSG_404 = "Pedido ou venda não encontrado."


@contextmanager
def _transacao(conexao):
    """Transação atômica: início exclusivo, commit ao sair sem erro e rollback total em qualquer falha."""
    repository.iniciar_transacao(conexao)
    try:
        yield
        conexao.commit()
    except BaseException:
        conexao.rollback()
        raise


# ---------------------------------------------------------------- montagem de respostas

def montar_venda(conexao, id_venda: int) -> dict:
    """Venda detalhada: itens, `quantidade` = nº de itens, `valor_total` = soma dos itens e nota (se houver)."""
    v = repository.buscar_venda(conexao, id_venda)
    itens = [{**dict(i), "valor": float(i["valor"])} for i in repository.listar_itens(conexao, id_venda)]
    nota = repository.buscar_nota(conexao, id_venda)
    return {
        "id_venda": v["id_venda"], "id_organizacao_cliente": v["id_organizacao_cliente"],
        "nome_organizacao": v["nome_organizacao"], "data_venda": v["data_venda"], "situacao": v["situacao"],
        "forma_pagamento": v["forma_pagamento"], "quantidade": len(itens),
        "valor_total": round(sum(i["valor"] for i in itens), 2), "itens": itens,
        "nota_fiscal": None if nota is None else dict(nota),
    }


def _resumo(linha) -> dict:
    d = dict(linha)
    d["valor_total"] = round(float(d["valor_total"]), 2)
    d["possui_nota"] = bool(d["possui_nota"])
    return d


def _obter_visivel(conexao, usuario: dict, id_venda: int):
    """RN04, RN15, RNF05: Cliente Empresa só enxerga a própria organização; outra ou inexistente -> 404."""
    linha = repository.buscar_venda(conexao, id_venda)
    if linha is None or (usuario["perfil"] == CLIENTE_EMPRESA
                         and linha["id_organizacao_cliente"] != usuario["id_organizacao"]):
        raise ErroApi(404, "NAO_ENCONTRADO", _MSG_404)
    return linha


def _exigir_pendente(venda) -> None:
    """UC13 FA1, UC14 FA1 (DP-47): Confirmada e Cancelada são somente leitura."""
    if venda["situacao"] != SIT_PENDENTE:
        raise ErroApi(422, "VENDA_NAO_PENDENTE", "Somente pedidos pendentes podem ser alterados.",
                      {"situacao": venda["situacao"]})


def _exigir_cliente_ativo(conexao, id_organizacao) -> None:
    """UC13 FE2, UC14 FE1, RN13: o Cliente Empresa precisa estar 'Ativa'."""
    org = repository.buscar_organizacao(conexao, id_organizacao) if id_organizacao is not None else None
    if org is None or org["situacao"] != SITUACAO_ORG_ATIVA:
        raise ErroApi(422, "CLIENTE_INATIVO", "A organização do cliente está inativa.",
                      {"id_organizacao_cliente": "inativa"})


def _erro_itens(ids: set[int]) -> ErroApi:
    """UC13 FE1, UC14 FE1: aponta os itens afetados."""
    lista = ", ".join(str(i) for i in sorted(ids))
    return ErroApi(422, "ITEM_INDISPONIVEL", "Há equipamentos indisponíveis no pedido.",
                   {"ids_equipamento": f"indisponíveis: {lista}"})


def _exigir_sem_reserva_doacao(conexao, ids: list[int]) -> None:
    """Módulo 7, DP-70: equipamento reservado por solicitação de doação Pendente -> 422 EQUIPAMENTO_RESERVADO."""
    reservados = repository.ids_reservados_por_doacao(conexao, ids)
    if reservados:
        lista = ", ".join(str(i) for i in sorted(reservados))
        raise ErroApi(422, "EQUIPAMENTO_RESERVADO", "Há equipamentos reservados por uma solicitação de doação.",
                      {"ids_equipamento": f"reservados: {lista}"})


# ---------------------------------------------------------------- consultas

def listar(conexao, usuario: dict, page: int, size: int, filtros: dict) -> dict:
    """UC21 passo 2-4 e FA1 (Administrador/Funcionário, todas as situações); UC18 passo 2 (Cliente Empresa: só a
    própria organização, filtro de organização ignorado). RN15, RNF05. `data_de` > `data_ate` -> lista vazia."""
    filtros = dict(filtros)
    if usuario["perfil"] == CLIENTE_EMPRESA:
        filtros["id_organizacao_cliente"] = usuario["id_organizacao"] if usuario["id_organizacao"] is not None else -1
    for chave in ("data_de", "data_ate"):
        if filtros.get(chave) is not None:
            filtros[chave] = filtros[chave].isoformat()
    linhas, total = repository.listar(conexao, page, size, filtros)
    return {"items": [_resumo(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, usuario: dict, id_venda: int) -> dict:
    """UC14 passo 2, UC18 passo 4, UC18 FE1, UC21 passo 5: outra organização -> 404."""
    _obter_visivel(conexao, usuario, id_venda)
    return montar_venda(conexao, id_venda)


# ---------------------------------------------------------------- pedido (UC13)

def criar_pedido(conexao, usuario: dict, dados) -> dict:
    """UC13 fluxo principal, FE1, FE2; RN13, DP-45/46/48. Cliente Empresa; organização do token.
    Venda 'Pendente' + ITEM_VENDA (valor congelado) na mesma transação; o equipamento segue 'Disponível' (reservado
    pela linha em ITEM_VENDA)."""
    with _transacao(conexao):
        _exigir_cliente_ativo(conexao, usuario["id_organizacao"])  # FE2
        ids = list(dados.ids_equipamento)
        _exigir_sem_reserva_doacao(conexao, ids)  # Módulo 7, DP-70
        indisponiveis = set(ids) - repository.ids_aptos_catalogo(conexao, ids)  # passo 4: revalida a disponibilidade
        if indisponiveis:
            raise _erro_itens(indisponiveis)  # FE1
        id_venda = repository.inserir_venda(conexao, usuario["id_organizacao"], date.today().isoformat(),
                                           dados.forma_pagamento or FORMA_A_DEFINIR)  # DP-79
        for id_equipamento in ids:
            repository.inserir_item(conexao, id_venda, id_equipamento)
    return montar_venda(conexao, id_venda)


def substituir_itens(conexao, usuario: dict, id_venda: int, dados) -> dict:
    """UC13 FA1, UC14 FA1, DP-47: troca o conjunto de equipamentos do pedido Pendente. Ordem: 400 -> 404 -> 422
    VENDA_NAO_PENDENTE -> 422 ITEM_INDISPONIVEL. Itens mantidos conservam o valor congelado (DP-48)."""
    with _transacao(conexao):
        venda = _obter_visivel(conexao, usuario, id_venda)
        _exigir_pendente(venda)
        novos = list(dados.ids_equipamento)
        atuais = repository.ids_equipamento_da_venda(conexao, id_venda)
        adicionar = [i for i in novos if i not in atuais]
        retirar = [i for i in atuais if i not in novos]
        _exigir_sem_reserva_doacao(conexao, adicionar)  # Módulo 7, DP-70
        indisponiveis = set(adicionar) - repository.ids_aptos_catalogo(conexao, adicionar)  # RN13
        if indisponiveis:
            raise _erro_itens(indisponiveis)
        repository.apagar_itens(conexao, id_venda, retirar)  # libera os retirados (DP-45)
        for id_equipamento in adicionar:
            repository.inserir_item(conexao, id_venda, id_equipamento)
    return montar_venda(conexao, id_venda)


def ajustar_pedido(conexao, id_venda: int, dados) -> dict:
    """UC14 FA1, DP-47: Administrador/Funcionário ajustam a forma de pagamento do pedido Pendente.
    Ordem: 400 -> 404 -> 422."""
    with _transacao(conexao):
        venda = repository.buscar_venda(conexao, id_venda)
        if venda is None:
            raise ErroApi(404, "NAO_ENCONTRADO", _MSG_404)
        _exigir_pendente(venda)
        repository.atualizar_forma_pagamento(conexao, id_venda, dados.forma_pagamento)
    return montar_venda(conexao, id_venda)


def cancelar(conexao, usuario: dict, id_venda: int) -> dict:
    """UC13 FA1, UC14 FA2, DP-45/47: só 'Pendente' vira 'Cancelada' e as linhas de ITEM_VENDA são apagadas (liberam
    os equipamentos). Não gera nota nem venda confirmada. Idempotente se já 'Cancelada' (200)."""
    with _transacao(conexao):
        venda = _obter_visivel(conexao, usuario, id_venda)
        if venda["situacao"] != SIT_CANCELADA:
            _exigir_pendente(venda)
            repository.apagar_itens(conexao, id_venda)
            repository.atualizar_situacao(conexao, id_venda, SIT_CANCELADA)
    return montar_venda(conexao, id_venda)


# ---------------------------------------------------------------- confirmação (UC14 + UC15)

def confirmar(conexao, id_venda: int, dados) -> dict:
    """UC14 fluxo principal + UC15 (RN13, RN14, DP-46/48). Administrador/Funcionário.
    Ordem: 400 (schema) -> 404 -> VENDA_NAO_PENDENTE -> 400 (data anterior ao pedido) -> CLIENTE_INATIVO ->
    ITEM_INDISPONIVEL -> FALHA_ESTOQUE. Venda 'Confirmada' e equipamentos 'Vendido' na mesma transação; qualquer
    falha desfaz tudo e a venda continua 'Pendente' (UC15 FE1)."""
    with _transacao(conexao):
        venda = repository.buscar_venda(conexao, id_venda)
        if venda is None:
            raise ErroApi(404, "NAO_ENCONTRADO", _MSG_404)
        if (venda["situacao"] == SIT_CONFIRMADA and venda["data_venda"] == dados.data_venda
                and venda["forma_pagamento"] == dados.forma_pagamento):
            return montar_venda(conexao, id_venda)  # idempotente: mesmos dados -> 200
        _exigir_pendente(venda)
        if dados.data_venda < venda["data_venda"]:  # DP-46: não anterior à data do pedido
            raise ErroApi(400, "DADOS_INVALIDOS", "Dados inválidos. Corrija os campos indicados.",
                          {"data_venda": "não pode ser anterior à data do pedido"})
        _exigir_cliente_ativo(conexao, venda["id_organizacao_cliente"])  # UC14 FE1, RN13
        ids = repository.ids_equipamento_da_venda(conexao, id_venda)
        if not ids:  # RN13, DP-47: venda sem equipamento não é confirmada
            raise ErroApi(422, "PEDIDO_SEM_ITENS", "O pedido não tem itens. Inclua ao menos um equipamento.")
        indisponiveis = set(ids) - repository.ids_aptos_confirmacao(conexao, ids)  # UC14 passo 4, RN13
        if indisponiveis:
            raise _erro_itens(indisponiveis)
        try:
            repository.confirmar(conexao, id_venda, dados.data_venda, dados.forma_pagamento)
            for id_equipamento in ids:  # UC15 passo 2, RN14 (sem commit: mesma transação)
                equipamentos_service.mudar_situacao(
                    conexao, id_equipamento, equipamentos_service.SIT_VENDIDO, permitir_vendido=True, commit=False)
        except Exception as erro:  # UC15 FE1: rollback total (feito por `_transacao`); a venda segue 'Pendente'
            log.error("Falha ao atualizar o estoque na venda %s: %r", id_venda, erro)
            raise ErroApi(422, "FALHA_ESTOQUE",
                          "Não foi possível atualizar o estoque. A venda não foi confirmada.") from erro
    return montar_venda(conexao, id_venda)
