"""Regras do novo UC "Solicitar doação" e do UC11 ampliado (DP-69 a DP-73, DP-77). Perfis nas rotas.
RN04/RN15 (ONG só a própria organização), RN12 (ONG ativa, equipamento Disponível e ativo), RN13."""
from contextlib import contextmanager
from datetime import date

from app.equipamentos import service as equipamentos_service
from app.erros import ErroApi
from app.permissoes import CLIENTE_ONG
from app.solicitacoes_doacao import repository

SIT_PENDENTE = "Pendente"
_MSG_404 = "Solicitação de doação não encontrada."


@contextmanager
def _transacao(conexao):
    repository.iniciar_transacao(conexao)
    try:
        yield
        conexao.commit()
    except BaseException:
        conexao.rollback()
        raise


def _montar(conexao, linha) -> dict:
    d = dict(linha)
    d["nome_organizacao"] = d["nome_ong"]  # nome que o front espera (doacoes-solicitacoes.js); nome_ong mantido
    d["itens"] = [dict(i) for i in repository.itens(conexao, linha["id_solicitacao_doacao"])]
    return d


def _obter_visivel(conexao, usuario: dict, id_solicitacao: int):
    """RN04, RN15, RNF05: ONG de outra organização -> 404."""
    linha = repository.buscar(conexao, id_solicitacao)
    if linha is None or (usuario["perfil"] == CLIENTE_ONG and linha["id_organizacao_ong"] != usuario["id_organizacao"]):
        raise ErroApi(404, "NAO_ENCONTRADO", _MSG_404)
    return linha


def _exigir_pendente(linha) -> None:
    if linha["situacao"] != SIT_PENDENTE:
        raise ErroApi(422, "SOLICITACAO_NAO_PENDENTE", "Só solicitações pendentes podem mudar de estado.",
                      {"situacao": linha["situacao"]})


def _exigir_ong_ativa(conexao, id_organizacao) -> None:
    org = repository.buscar_organizacao(conexao, id_organizacao) if id_organizacao is not None else None
    if org is None or org["tipo"] != "Cliente ONG" or org["situacao"] != "Ativa":
        raise ErroApi(422, "ORGANIZACAO_INVALIDA", "A organização precisa ser uma ONG ativa.",
                      {"id_organizacao_ong": "inválida ou inativa"})


def _erro_ids(codigo: str, mensagem: str, ids) -> ErroApi:
    return ErroApi(422, codigo, mensagem, {"ids_equipamentos": "afetados: " + ", ".join(str(i) for i in sorted(ids))})


def _nao_elegiveis(conexao, ids: list[int]) -> set[int]:
    """RN12/RN13: não existe, não está Disponível ou está inativo."""
    existentes = repository.equipamentos(conexao, ids)
    return {i for i in ids if i not in existentes or existentes[i]["situacao"] != "Disponível"
            or not existentes[i]["ativo"]}


def criar(conexao, usuario: dict, dados) -> dict:
    """Novo UC Solicitar doação (DP-69/70/72): nasce Pendente e reserva os equipamentos. Checagem e gravação juntas."""
    ids = list(dados.ids_equipamentos)
    with _transacao(conexao):
        _exigir_ong_ativa(conexao, usuario["id_organizacao"])
        indisponiveis = _nao_elegiveis(conexao, ids)
        if indisponiveis:
            raise _erro_ids("EQUIPAMENTO_INDISPONIVEL", "Há equipamentos indisponíveis na solicitação.", indisponiveis)
        reservados = repository.ids_reservados(conexao, ids)
        if reservados:
            raise _erro_ids("EQUIPAMENTO_RESERVADO", "Há equipamentos reservados por outro pedido.", reservados)
        nova = repository.inserir(conexao, usuario["id_organizacao"], date.today().isoformat(), ids)
    return _montar(conexao, repository.buscar(conexao, nova))


def listar(conexao, usuario: dict, page: int, size: int, situacao: str | None) -> dict:
    """UC19 ampliado: ONG vê só as próprias (RN04, RN15); Administrador/Funcionário veem todas."""
    id_ong = None
    if usuario["perfil"] == CLIENTE_ONG:
        id_ong = usuario["id_organizacao"] if usuario["id_organizacao"] is not None else -1
    linhas, total = repository.listar(conexao, page, size, id_ong, situacao)
    return {"items": [_montar(conexao, l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, usuario: dict, id_solicitacao: int) -> dict:
    return _montar(conexao, _obter_visivel(conexao, usuario, id_solicitacao))


def aprovar(conexao, usuario: dict, id_solicitacao: int) -> dict:
    """UC11 (DP-69/71): para cada item cria DOACAO e muda o equipamento para Doado, tudo em uma transação."""
    hoje = date.today().isoformat()
    with _transacao(conexao):
        linha = _obter_visivel(conexao, usuario, id_solicitacao)
        _exigir_pendente(linha)
        _exigir_ong_ativa(conexao, linha["id_organizacao_ong"])
        ids = repository.ids_equipamento(conexao, id_solicitacao)
        ruins = _nao_elegiveis(conexao, ids)
        if ruins:
            raise _erro_ids("EQUIPAMENTO_INDISPONIVEL", "Há equipamentos indisponíveis na solicitação.", ruins)
        for i in ids:  # reaproveita o UC11; commit=False mantém tudo na mesma transação
            equipamentos_service.mudar_situacao(conexao, i, "Doado", linha["id_organizacao_ong"], hoje, commit=False)
        repository.decidir(conexao, id_solicitacao, "Aprovada", None, usuario["nome"], hoje)
    return obter(conexao, usuario, id_solicitacao)


def recusar(conexao, usuario: dict, id_solicitacao: int, dados) -> dict:
    """DP-71/73: motivo obrigatório; registra decidido_por (nome copiado, DP-77) e data; libera a reserva."""
    with _transacao(conexao):
        _exigir_pendente(_obter_visivel(conexao, usuario, id_solicitacao))
        repository.decidir(conexao, id_solicitacao, "Recusada", dados.motivo, usuario["nome"], date.today().isoformat())
    return obter(conexao, usuario, id_solicitacao)


def cancelar(conexao, usuario: dict, id_solicitacao: int) -> dict:
    """DP-73: a ONG cancela enquanto Pendente, sem motivo; libera a reserva."""
    with _transacao(conexao):
        _exigir_pendente(_obter_visivel(conexao, usuario, id_solicitacao))
        repository.decidir(conexao, id_solicitacao, "Cancelada", None, None, date.today().isoformat())
    return obter(conexao, usuario, id_solicitacao)
