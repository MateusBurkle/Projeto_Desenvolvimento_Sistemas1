"""Rotas do módulo 4 - solicitações e avaliação (contrato modulo-4.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.erros import ErroApi
from app.permissoes import ADMINISTRADOR, EMPRESA_DOADORA, FUNCIONARIO
from app.solicitacoes import schemas, service

router = APIRouter(tags=["Solicitações", "Avaliação"])

_admin_ou_funcionario = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)
_doadora = exigir_perfis(EMPRESA_DOADORA)
_doadora_admin_ou_funcionario = exigir_perfis(EMPRESA_DOADORA, ADMINISTRADOR, FUNCIONARIO)


def _checar_ids(**ids: int) -> None:
    # RNF04: id acima de 2^63-1 não existe no banco; devolve 404 em vez de estourar o sqlite3
    if any(valor > schemas.ID_MAX for valor in ids.values()):
        raise ErroApi(404, "NAO_ENCONTRADO", "Recurso não encontrado.")


@router.get("/solicitacoes", response_model=schemas.PaginaSolicitacoes, operation_id="listarSolicitacoes")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           situacao: schemas.SituacaoSolicitacao | None = None,
           id_organizacao_doadora: int | None = Query(None, le=schemas.ID_MAX),
           data_de: date | None = None, data_ate: date | None = None,
           usuario: dict = Depends(_doadora_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC20 passo 1-3 (Empresa Doadora, só as próprias), UC10 passo 1 (Admin/Funcionário); RN05, RN04, RN15, RNF05
    filtros = {"situacao": situacao, "id_organizacao_doadora": id_organizacao_doadora,
               "data_de": data_de, "data_ate": data_ate}
    return service.listar(conexao, usuario, page, size, filtros)


@router.post("/solicitacoes", response_model=schemas.Solicitacao, status_code=201, operation_id="criarSolicitacao",
             response_model_exclude_unset=True)
def criar(dados: schemas.SolicitacaoEntrada, usuario: dict = Depends(_doadora),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC09, RF05, RF21, RN05, RN10, RN21: registra a solicitação da organização do token (só Empresa Doadora)
    return service.criar(conexao, usuario, dados)


@router.get("/solicitacoes/{id_solicitacao}", response_model=schemas.Solicitacao, operation_id="obterSolicitacao",
            response_model_exclude_unset=True)
def obter(id_solicitacao: int, usuario: dict = Depends(_doadora_admin_ou_funcionario),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC09 FA1, UC10 passo 2, UC20 passo 3-4 e FE1; RN05, RNF05 (outra organização -> 404)
    _checar_ids(id_solicitacao=id_solicitacao)
    return service.obter(conexao, usuario, id_solicitacao)


@router.post("/solicitacoes/{id_solicitacao}/itens/{id_item_solicitacao}/equipamentos",
             response_model=schemas.EquipamentoVinculado, status_code=201,
             operation_id="avaliarItemCadastrarEquipamento")
def avaliar_item(id_solicitacao: int, id_item_solicitacao: int, dados: schemas.AvaliacaoEntrada,
                 _: dict = Depends(_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC10 passo 3, RF21, RN03, RN11, RN21 (DP-41): avalia uma unidade do item (Administrador e Funcionário)
    _checar_ids(id_solicitacao=id_solicitacao, id_item_solicitacao=id_item_solicitacao)
    return service.avaliar_item(conexao, id_solicitacao, id_item_solicitacao, dados)


@router.put("/solicitacoes/{id_solicitacao}/equipamentos/{id_equipamento}/destinacao",
            response_model=schemas.Solicitacao, operation_id="definirDestinacao", response_model_exclude_unset=True)
def definir_destinacao(id_solicitacao: int, id_equipamento: int, dados: schemas.DestinacaoEntrada,
                       usuario: dict = Depends(_admin_ou_funcionario),
                       conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC10 passo 4-7, UC11, RF12, RN11, RN12, RN21 (DP-42): venda, doação ou reciclagem (Administrador e Funcionário)
    _checar_ids(id_solicitacao=id_solicitacao, id_equipamento=id_equipamento)
    return service.definir_destinacao(conexao, usuario, id_solicitacao, id_equipamento, dados)
