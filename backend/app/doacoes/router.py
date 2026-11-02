"""Rotas do módulo 4 - doações (contrato modulo-4.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.doacoes import schemas, service
from app.erros import ErroApi
from app.permissoes import ADMINISTRADOR, CLIENTE_ONG, FUNCIONARIO

router = APIRouter(tags=["Doações"])

_admin_ou_funcionario = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)
_ong_admin_ou_funcionario = exigir_perfis(CLIENTE_ONG, ADMINISTRADOR, FUNCIONARIO)


# Declarada antes de /doacoes/{id_doacao} para não ser capturada como id
@router.get("/doacoes/ongs-elegiveis", response_model=list[schemas.OngElegivel], operation_id="listarOngsElegiveis")
def listar_ongs_elegiveis(_: dict = Depends(_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC11 passo 2, RN12: ONGs ativas elegíveis (Administrador e Funcionário)
    return service.listar_ongs_elegiveis(conexao)


@router.get("/doacoes", response_model=schemas.PaginaDoacoes, operation_id="listarDoacoes")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           id_organizacao_ong: int | None = Query(None, le=schemas.ID_MAX),
           data_de: date | None = None, data_ate: date | None = None,
           usuario: dict = Depends(_ong_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC19 passo 2-3 e FA1; RF04, RF15, RN04, RN15, RNF05: Cliente ONG vê só as próprias doações
    filtros = {"id_organizacao_ong": id_organizacao_ong, "data_de": data_de, "data_ate": data_ate}
    return service.listar(conexao, usuario, page, size, filtros)


@router.get("/doacoes/{id_doacao}", response_model=schemas.Doacao, operation_id="obterDoacao")
def obter(id_doacao: int, usuario: dict = Depends(_ong_admin_ou_funcionario),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC19 passo 4 e FE1; RN04, RN15, RNF05: de outra ONG -> 404
    if id_doacao > schemas.ID_MAX:  # RNF04
        raise ErroApi(404, "NAO_ENCONTRADO", "Doação não encontrada.")
    return service.obter(conexao, usuario, id_doacao)
