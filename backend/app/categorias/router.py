"""Rotas do módulo 3 - categorias (contrato modulo-3.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3

from fastapi import APIRouter, Depends, Query

from app.categorias import schemas, service
from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.erros import ErroApi
from app.permissoes import ADMINISTRADOR, FUNCIONARIO

router = APIRouter(tags=["Categorias"])

_ID_MAX = 2**63 - 1


def _checar_id(id_categoria: int) -> None:
    # RNF04: id acima de 2^63-1 não existe no banco; devolve 404 em vez de estourar o sqlite3
    if id_categoria > _ID_MAX:
        raise ErroApi(404, "NAO_ENCONTRADO", "Categoria não encontrada.")

_admin = exigir_perfis(ADMINISTRADOR)
_admin_ou_funcionario = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)


@router.get("/categorias", response_model=schemas.PaginaCategorias, operation_id="listarCategorias")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100), ativa: bool | None = None,
           q: str | None = Query(None, max_length=80), _: dict = Depends(_admin_ou_funcionario),
           conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC05 FA1, UC07 passo 2, RF08: lista com filtros (Administrador e Funcionário)
    return service.listar(conexao, page, size, ativa, q)


@router.post("/categorias", response_model=schemas.Categoria, status_code=201, operation_id="criarCategoria")
def criar(dados: schemas.CategoriaEntrada, _: dict = Depends(_admin),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC05, RF07, RN07: cadastra categoria Ativa (Administrador)
    return service.criar(conexao, dados)


@router.get("/categorias/{id_categoria}", response_model=schemas.Categoria, operation_id="obterCategoria")
def obter(id_categoria: int, _: dict = Depends(_admin_ou_funcionario),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC05 FA1: consulta uma categoria
    _checar_id(id_categoria)
    return service.obter(conexao, id_categoria)


@router.put("/categorias/{id_categoria}", response_model=schemas.Categoria, operation_id="alterarCategoria")
def alterar(id_categoria: int, dados: schemas.CategoriaEntrada, _: dict = Depends(_admin),
            conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC05 FA1, RF08: altera o nome; categorias base protegidas (Administrador)
    _checar_id(id_categoria)
    return service.alterar(conexao, id_categoria, dados)


@router.patch("/categorias/{id_categoria}/situacao", response_model=schemas.Categoria,
              operation_id="alterarSituacaoCategoria")
def alterar_situacao(id_categoria: int, dados: schemas.CategoriaSituacao, _: dict = Depends(_admin),
                     conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC05 FA2, RN07, RN08: desativa ou reativa (Administrador), sem exclusão física
    _checar_id(id_categoria)
    return service.alterar_situacao(conexao, id_categoria, dados)
