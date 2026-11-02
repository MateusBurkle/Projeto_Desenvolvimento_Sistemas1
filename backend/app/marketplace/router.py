"""Rotas públicas do marketplace (contrato modulo-7.yaml; DP-68, DP-74). Token opcional; regra no service."""
import sqlite3

from fastapi import APIRouter, Depends, Query
from fastapi.security import HTTPAuthorizationCredentials

from app.auth import service as auth_service
from app.db import get_conexao
from app.dependencias import _esquema_bearer
from app.erros import ErroApi
from app.marketplace import schemas, service
from app.seguranca import decodificar_token

router = APIRouter(prefix="/marketplace", tags=["Marketplace"])


def usuario_opcional(credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
                     conexao: sqlite3.Connection = Depends(get_conexao)) -> dict | None:
    """Token OPCIONAL: sem token, token inválido ou conta inativa -> visitante (None)."""
    claims = decodificar_token(credenciais.credentials) if credenciais else None
    if claims is None:
        return None
    try:
        return auth_service.obter_usuario_autenticado(conexao, int(claims["sub"]))
    except ErroApi:
        return None


@router.get("/categorias", response_model=list[schemas.Categoria], operation_id="listarCategoriasMarketplace")
def categorias(conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC12 ampliado (público)
    return service.categorias(conexao)


@router.get("/produtos", response_model=schemas.PaginaProdutos, response_model_exclude_unset=True,
            operation_id="listarProdutosMarketplace")
def listar(page: int = Query(1, ge=1), size: int = Query(12, ge=1, le=100),
           id_categoria: int | None = Query(None, le=schemas.ID_MAX), busca: str | None = Query(None, max_length=150),
           usuario: dict | None = Depends(usuario_opcional), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC12 ampliado; RN13; DP-70, DP-74 (valor só Cliente Empresa)
    return service.listar(conexao, usuario, page, size, id_categoria, busca)


@router.get("/produtos/{id_equipamento}", response_model=schemas.Produto, response_model_exclude_unset=True,
            operation_id="obterProdutoMarketplace")
def obter(id_equipamento: int, usuario: dict | None = Depends(usuario_opcional),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC12 ampliado; RN13; DP-74
    if id_equipamento > schemas.ID_MAX:  # RNF04
        raise ErroApi(404, "NAO_ENCONTRADO", "Produto não encontrado.")
    return service.obter(conexao, usuario, id_equipamento)
