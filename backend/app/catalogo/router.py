"""Rotas do módulo 5 - catálogo (contrato modulo-5.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3

from fastapi import APIRouter, Depends, Query

from app.catalogo import schemas, service
from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.erros import ErroApi
from app.permissoes import CLIENTE_EMPRESA

router = APIRouter(tags=["Catálogo"])

_cliente_empresa = exigir_perfis(CLIENTE_EMPRESA)  # UC12 FE2: demais perfis -> 403


@router.get("/catalogo", response_model=schemas.PaginaCatalogo, operation_id="listarCatalogo")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           id_categoria: int | None = Query(None, le=schemas.ID_MAX), q: str | None = Query(None, max_length=150),
           _: dict = Depends(_cliente_empresa), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC12 passo 1-2, FE1; RF04, RF13; RN04, RN13
    return service.listar(conexao, page, size, id_categoria, q)


@router.get("/catalogo/{id_equipamento}", response_model=schemas.ItemCatalogo, operation_id="obterItemCatalogo")
def obter(id_equipamento: int, _: dict = Depends(_cliente_empresa), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC12 passo 3-4, FA1; RN13
    if id_equipamento > schemas.ID_MAX:  # RNF04
        raise ErroApi(404, "NAO_ENCONTRADO", "Equipamento não encontrado no catálogo.")
    return service.obter(conexao, id_equipamento)
