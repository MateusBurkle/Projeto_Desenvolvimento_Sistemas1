"""Rotas /doacoes/solicitacoes (contrato modulo-7.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from typing import Literal

from fastapi import APIRouter, Depends, Query

from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.erros import ErroApi
from app.permissoes import ADMINISTRADOR, CLIENTE_ONG, FUNCIONARIO
from app.solicitacoes_doacao import schemas, service

router = APIRouter(prefix="/doacoes/solicitacoes", tags=["Solicitação de doação"])

_ong = exigir_perfis(CLIENTE_ONG)
_decisor = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)
_leitura = exigir_perfis(CLIENTE_ONG, ADMINISTRADOR, FUNCIONARIO)


def _id(i: int) -> int:
    if i > schemas.ID_MAX:  # RNF04
        raise ErroApi(404, "NAO_ENCONTRADO", "Solicitação de doação não encontrada.")
    return i


@router.post("", status_code=201, response_model=schemas.Solicitacao, operation_id="criarSolicitacaoDoacao")
def criar(dados: schemas.CriarSolicitacao, usuario: dict = Depends(_ong), conexao: sqlite3.Connection = Depends(get_conexao)):
    # Novo UC Solicitar doação; DP-69, DP-70, DP-72; RN12
    return service.criar(conexao, usuario, dados)


@router.get("", response_model=schemas.PaginaSolicitacoes, operation_id="listarSolicitacoesDoacao")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           situacao: Literal["Pendente", "Aprovada", "Recusada", "Cancelada"] | None = None,
           usuario: dict = Depends(_leitura), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC19 ampliado; RN04, RN15
    return service.listar(conexao, usuario, page, size, situacao)


@router.get("/{id_solicitacao_doacao}", response_model=schemas.Solicitacao, operation_id="obterSolicitacaoDoacao")
def obter(id_solicitacao_doacao: int, usuario: dict = Depends(_leitura), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC19 ampliado; RN04, RN15, RNF05: de outra ONG -> 404
    return service.obter(conexao, usuario, _id(id_solicitacao_doacao))


@router.patch("/{id_solicitacao_doacao}/aprovar", response_model=schemas.Solicitacao, operation_id="aprovarSolicitacaoDoacao")
def aprovar(id_solicitacao_doacao: int, usuario: dict = Depends(_decisor), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC11; DP-69, DP-71; RN12
    return service.aprovar(conexao, usuario, _id(id_solicitacao_doacao))


@router.patch("/{id_solicitacao_doacao}/recusar", response_model=schemas.Solicitacao, operation_id="recusarSolicitacaoDoacao")
def recusar(id_solicitacao_doacao: int, dados: schemas.RecusarSolicitacao, usuario: dict = Depends(_decisor),
            conexao: sqlite3.Connection = Depends(get_conexao)):
    # DP-71, DP-73: motivo obrigatório
    return service.recusar(conexao, usuario, _id(id_solicitacao_doacao), dados)


@router.patch("/{id_solicitacao_doacao}/cancelar", response_model=schemas.Solicitacao, operation_id="cancelarSolicitacaoDoacao")
def cancelar(id_solicitacao_doacao: int, usuario: dict = Depends(_ong), conexao: sqlite3.Connection = Depends(get_conexao)):
    # DP-73: ONG cancela enquanto Pendente
    return service.cancelar(conexao, usuario, _id(id_solicitacao_doacao))
