"""Regras de negócio do módulo 2 - parceiros: UC06. RF10; RN03, RN10."""
import sqlite3

from app.erros import ErroApi
from app.parceiros import repository

SITUACAO_ATIVA = "Ativa"
TIPO_DOADORA = "Empresa Doadora"


def _obter_ou_404(conexao, id_parceiro: int):
    linha = repository.buscar_por_id(conexao, id_parceiro)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Parceiro não encontrado.")
    return linha


def _organizacao_inativa() -> ErroApi:
    return ErroApi(422, "ORGANIZACAO_INVALIDA", "A organização está inativa.",
                   {"id_organizacao": "organização inativa"})


def _erro_parceria_duplicada() -> ErroApi:
    return ErroApi(409, "PARCERIA_DUPLICADA", "Esta organização já possui um vínculo de parceria.",
                   {"id_organizacao": "duplicado"})


def _validar_atuacao(tipo_parceria: str, tipo_organizacao: str) -> None:
    """UC06 FE2, RN10: atuação Empresa Doadora exige organização do tipo Empresa Doadora."""
    if tipo_parceria == TIPO_DOADORA and tipo_organizacao != TIPO_DOADORA:
        raise ErroApi(422, "ATUACAO_INCOMPATIVEL",
                      "A atuação Empresa Doadora exige uma organização do tipo Empresa Doadora.",
                      {"tipo_parceria": "incompatível com o tipo da organização"})


def listar(conexao, page, size, tipo_parceria, situacao_parceria, q) -> dict:
    """UC06 FA1, RF10."""
    linhas, total = repository.listar(conexao, page, size, tipo_parceria, situacao_parceria, q)
    return {"items": [dict(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, id_parceiro: int) -> dict:
    """UC06 FA1: 404 se inexistente."""
    return dict(_obter_ou_404(conexao, id_parceiro))


def criar(conexao, dados) -> dict:
    """UC06 fluxo principal, FE1-FE3, RF10, RN10. Ordem: 404 org -> 422 inativa -> 409 duplicada -> 422 atuação."""
    organizacao = repository.buscar_organizacao(conexao, dados.id_organizacao)
    if organizacao is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Organização não encontrada.", {"id_organizacao": "inexistente"})
    if organizacao["situacao"] != SITUACAO_ATIVA:
        raise _organizacao_inativa()
    if repository.existe_parceria(conexao, dados.id_organizacao):
        raise _erro_parceria_duplicada()
    _validar_atuacao(dados.tipo_parceria, organizacao["tipo"])
    try:
        novo_id = repository.inserir(conexao, dados.id_organizacao, dados.tipo_parceria,
                                     dados.situacao_parceria or SITUACAO_ATIVA)
    except sqlite3.IntegrityError:  # corrida: UNIQUE em PARCEIRO.id_organizacao
        conexao.rollback()
        raise _erro_parceria_duplicada()
    return obter(conexao, novo_id)


def alterar(conexao, id_parceiro: int, dados) -> dict:
    """UC06 FA1, FE2: altera só a atuação; revalida contra o tipo da organização."""
    atual = _obter_ou_404(conexao, id_parceiro)
    _validar_atuacao(dados.tipo_parceria, atual["tipo_organizacao"])
    repository.atualizar_tipo(conexao, id_parceiro, dados.tipo_parceria)
    return obter(conexao, id_parceiro)


def alterar_situacao(conexao, id_parceiro: int, dados) -> dict:
    """UC06 FA2, FE3, RN10: desativa (preserva histórico) ou reativa (exige organização Ativa). Idempotente."""
    atual = _obter_ou_404(conexao, id_parceiro)
    if atual["situacao_parceria"] != dados.situacao_parceria:
        if dados.situacao_parceria == SITUACAO_ATIVA and atual["situacao_organizacao"] != SITUACAO_ATIVA:
            raise _organizacao_inativa()
        repository.atualizar_situacao(conexao, id_parceiro, dados.situacao_parceria)
    return obter(conexao, id_parceiro)
