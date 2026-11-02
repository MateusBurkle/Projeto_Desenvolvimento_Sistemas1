"""Rotas do módulo 2 - parceiros (contrato modulo-2.yaml). Somente Administrador (RN03). Sem DELETE (DP-25)."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.db import get_conexao
from app.erros import ID_MAX
from app.dependencias import exigir_perfis
from app.parceiros import schemas, service
from app.permissoes import ADMINISTRADOR

IdRota = Annotated[int, Path(le=ID_MAX)]  # RNF04: id fora da faixa -> 404

router = APIRouter(tags=["Parceiros"])

_admin = exigir_perfis(ADMINISTRADOR)


@router.get("/parceiros", response_model=schemas.PaginaParceiros, operation_id="listarParceiros")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           tipo_parceria: schemas.TipoParceria | None = None, situacao_parceria: schemas.SituacaoParceria | None = None,
           q: str | None = Query(None, max_length=150), _: dict = Depends(_admin),
           conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC06 FA1, RF10, RN03: lista parceiros com dados da organização
    return service.listar(conexao, page, size, tipo_parceria, situacao_parceria, q)


@router.post("/parceiros", response_model=schemas.Parceiro, status_code=201, operation_id="criarParceiro")
def criar(dados: schemas.ParceiroCriar, _: dict = Depends(_admin), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC06, RF10, RN10: cadastra o vínculo de parceria
    return service.criar(conexao, dados)


@router.get("/parceiros/{id_parceiro}", response_model=schemas.Parceiro, operation_id="obterParceiro")
def obter(id_parceiro: IdRota, _: dict = Depends(_admin), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC06 FA1, RF10: consulta um parceiro
    return service.obter(conexao, id_parceiro)


@router.put("/parceiros/{id_parceiro}", response_model=schemas.Parceiro, operation_id="alterarParceiro")
def alterar(id_parceiro: IdRota, dados: schemas.ParceiroAlterar, _: dict = Depends(_admin),
            conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC06 FA1, FE2, RN10: altera a atuação na parceria
    return service.alterar(conexao, id_parceiro, dados)


@router.patch("/parceiros/{id_parceiro}/situacao", response_model=schemas.Parceiro,
              operation_id="alterarSituacaoParceiro")
def alterar_situacao(id_parceiro: IdRota, dados: schemas.SituacaoParceriaAlterar, _: dict = Depends(_admin),
                     conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC06 FA2, FE3, RN10: desativa ou reativa o vínculo, sem exclusão física
    return service.alterar_situacao(conexao, id_parceiro, dados)
