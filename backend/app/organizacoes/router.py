"""Rotas do módulo 2 - organizações (contrato modulo-2.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.db import get_conexao
from app.erros import ID_MAX
from app.dependencias import exigir_perfis
from app.organizacoes import schemas, service
from app.permissoes import ADMINISTRADOR, CLIENTE_EMPRESA, CLIENTE_ONG, EMPRESA_DOADORA, FUNCIONARIO

IdRota = Annotated[int, Path(le=ID_MAX)]  # RNF04: id fora da faixa -> 404

router = APIRouter(tags=["Organizações"])

_admin = exigir_perfis(ADMINISTRADOR)
_admin_ou_funcionario = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)
_tres_clientes = exigir_perfis(CLIENTE_EMPRESA, CLIENTE_ONG, EMPRESA_DOADORA)  # DP-98


@router.get("/organizacao", response_model=schemas.Organizacao, operation_id="obterMinhaOrganizacao")
def obter_minha(ator: dict = Depends(_tres_clientes), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01, UC06, DP-93/98: própria organização (sem id na URL)
    return service.obter_propria(conexao, ator)


@router.patch("/organizacao", response_model=schemas.Organizacao, operation_id="atualizarMinhaOrganizacao")
def atualizar_minha(dados: schemas.MinhaOrganizacaoAlterar, ator: dict = Depends(_tres_clientes),
                    conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01, UC06, RN09, DP-93/94/98: nome e contato da própria organização
    return service.alterar_propria(conexao, ator, dados)


@router.get("/organizacoes", response_model=schemas.PaginaOrganizacoes, operation_id="listarOrganizacoes")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           tipo: schemas.TipoOrganizacao | None = None, situacao: schemas.SituacaoOrganizacao | None = None,
           sem_parceria: bool | None = None, q: str | None = Query(None, max_length=150),
           _: dict = Depends(_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01 FA1, RF06, RF09, RN03: lista com filtros (Administrador e Funcionário)
    return service.listar(conexao, page, size, tipo, situacao, q, sem_parceria)


@router.post("/organizacoes", response_model=schemas.Organizacao, status_code=201, operation_id="criarOrganizacao")
def criar(dados: schemas.OrganizacaoCriar, _: dict = Depends(_admin),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01, UC25, RF06, RN06, RN09, RNF04: cadastra organização (Administrador)
    return service.criar(conexao, dados)


@router.get("/organizacoes/{id_organizacao}", response_model=schemas.Organizacao, operation_id="obterOrganizacao")
def obter(id_organizacao: IdRota, _: dict = Depends(_admin_ou_funcionario),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01 FA1, RF09: consulta uma organização
    return service.obter(conexao, id_organizacao)


@router.put("/organizacoes/{id_organizacao}", response_model=schemas.Organizacao, operation_id="alterarOrganizacao")
def alterar(id_organizacao: IdRota, dados: schemas.OrganizacaoAlterar, _: dict = Depends(_admin),
            conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01 FA1, UC25, RN06, RN09: altera o cadastro completo (Administrador)
    return service.alterar(conexao, id_organizacao, dados)


@router.patch("/organizacoes/{id_organizacao}/contato", response_model=schemas.Organizacao,
              operation_id="alterarContatoOrganizacao")
def alterar_contato(id_organizacao: IdRota, dados: schemas.ContatoAlterar,
                    ator: dict = Depends(_admin_ou_funcionario), conexao: sqlite3.Connection = Depends(get_conexao)):
    # RF09, RN03, RN09 (DP-26): contato; Funcionário só em Cliente Empresa e Cliente ONG
    return service.alterar_contato(conexao, ator, id_organizacao, dados)


@router.patch("/organizacoes/{id_organizacao}/situacao", response_model=schemas.Organizacao,
              operation_id="alterarSituacaoOrganizacao")
def alterar_situacao(id_organizacao: IdRota, dados: schemas.SituacaoAlterar, _: dict = Depends(_admin),
                     conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01 FA2, RN06, RN09: desativa ou reativa (Administrador), sem exclusão física
    return service.alterar_situacao(conexao, id_organizacao, dados)


@router.delete("/organizacoes/{id_organizacao}", status_code=204, operation_id="excluirOrganizacao")
def excluir(id_organizacao: IdRota, excluir_usuarios: bool = False, _: dict = Depends(_admin),
            conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC01, UC06, RN06, RN09 (DP-63): exclui organização + parceria sem histórico (Administrador)
    service.excluir(conexao, id_organizacao, excluir_usuarios)
    return Response(status_code=204)
