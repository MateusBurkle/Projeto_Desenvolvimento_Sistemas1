"""Rotas do módulo 1 (contrato modulo-1.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.db import get_conexao
from app.erros import ID_MAX
from app.dependencias import exigir_perfis, get_usuario_atual
from app.permissoes import ADMINISTRADOR, FUNCIONARIO, CLIENTE_EMPRESA, CLIENTE_ONG, EMPRESA_DOADORA
from app.usuarios import schemas, service

IdRota = Annotated[int, Path(le=ID_MAX)]  # RNF04: id fora da faixa -> 404

router = APIRouter(tags=["Usuários"])

_admin = exigir_perfis(ADMINISTRADOR)
_cliente = exigir_perfis(CLIENTE_EMPRESA, CLIENTE_ONG)
_tres_clientes = exigir_perfis(ADMINISTRADOR, FUNCIONARIO, CLIENTE_EMPRESA, CLIENTE_ONG, EMPRESA_DOADORA)  # DP-98, DP-101: cinco perfis


@router.get("/usuarios/perfis-atribuiveis", response_model=list[schemas.PerfilAtribuivel],
            operation_id="listarPerfisAtribuiveis")
def perfis_atribuiveis(_: dict = Depends(_admin)):
    # UC27 passo 1, UC02, RN02: perfis e exigência de organização (Administrador)
    return service.listar_perfis_atribuiveis()


@router.get("/usuarios/opcoes-organizacao", response_model=list[schemas.OrganizacaoOpcao],
            operation_id="listarOrganizacoesAtivas")
def opcoes_organizacao(tipo: schemas.TipoOrganizacao | None = None, _: dict = Depends(_admin),
                       conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02 passo 2 (DP-15), RN06, RN09: organizações ativas para vincular (Administrador)
    return service.listar_organizacoes_ativas(conexao, tipo)


@router.get("/usuarios", response_model=schemas.PaginaUsuarios, operation_id="listarUsuarios")
def listar_usuarios(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                    perfil: schemas.Perfil | None = None, id_organizacao: int | None = Query(None, le=ID_MAX),
                    q: str | None = Query(None, max_length=120),
                    _: dict = Depends(_admin), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02 FA1, RN02, RN03: lista usuários com filtros (somente Administrador)
    return service.listar_usuarios(conexao, page, size, perfil, id_organizacao, q)


@router.post("/usuarios", response_model=schemas.Usuario, status_code=201, operation_id="criarUsuario")
def criar_usuario(dados: schemas.UsuarioCriar, _: dict = Depends(_admin),
                  conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02, UC26, UC27, RN02, RN09, RNF03: cadastra usuário e atribui perfil
    return service.criar_usuario(conexao, dados)


@router.patch("/usuarios/me", response_model=schemas.Usuario, operation_id="atualizarPropriaConta")
def atualizar_propria_conta(dados: schemas.PropriaContaAlterar, ator: dict = Depends(_tres_clientes),
                            conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02, UC03, UC26, DP-95/98: cliente atualiza o próprio nome e e-mail (declarada antes de /usuarios/{id})
    return service.alterar_propria_conta(conexao, ator, dados)


@router.put("/usuarios/me/senha", status_code=204, operation_id="alterarPropriaSenha")
def alterar_propria_senha(dados: schemas.PropriaSenhaAlterar, ator: dict = Depends(_tres_clientes),
                          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02, RNF03, DP-96/97: troca da própria senha, sem senha atual
    service.alterar_propria_senha(conexao, ator, dados.senha_nova)
    return Response(status_code=204)


@router.delete("/usuarios/me", status_code=204, operation_id="excluirPropriaConta")
def excluir_propria_conta(dados: schemas.ExcluirPropriaConta, ator: dict = Depends(get_usuario_atual),
                          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02 FA3 ampliado, RN02, RNF03 (DP-64/65/66): todo perfil autenticado exclui a própria conta
    service.excluir_propria_conta(conexao, ator, dados.senha)
    return Response(status_code=204)


@router.get("/usuarios/{id_usuario}", response_model=schemas.Usuario, operation_id="obterUsuario")
def obter_usuario(id_usuario: IdRota, _: dict = Depends(_admin), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02 FA1, RN02: consulta uma conta
    return service.obter_usuario(conexao, id_usuario)


@router.put("/usuarios/{id_usuario}", response_model=schemas.Usuario, operation_id="alterarUsuario")
def alterar_usuario(id_usuario: IdRota, dados: schemas.UsuarioAlterar, ator: dict = Depends(_admin),
                    conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02 FA1/FA2, FE3/FE4, UC26, UC27, RN02, RNF03: altera dados, perfil ou vínculo
    return service.alterar_usuario(conexao, ator, id_usuario, dados)


@router.delete("/usuarios/{id_usuario}", status_code=204, operation_id="excluirUsuario")
def excluir_usuario(id_usuario: IdRota, ator: dict = Depends(_admin),
                    conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC02 FA3, FE4, RN02: exclui a conta (física, exceção aprovada)
    service.excluir_usuario(conexao, ator, id_usuario)
    return Response(status_code=204)


@router.get("/organizacao/usuarios", response_model=schemas.PaginaUsuarios,
            operation_id="listarUsuariosDaOrganizacao")
def listar_da_organizacao(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
                          ator: dict = Depends(_cliente), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC03 FA1, RN04: usuários da própria organização (Cliente Empresa e Cliente ONG)
    return service.listar_usuarios_da_organizacao(conexao, ator, page, size)


@router.post("/organizacao/usuarios", response_model=schemas.Usuario, status_code=201,
             operation_id="criarUsuarioDaOrganizacao")
def criar_da_organizacao(dados: schemas.UsuarioOrganizacaoCriar, ator: dict = Depends(_cliente),
                         conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC03, UC26, RN02, RN04, RNF03: adiciona usuário na própria organização, perfil herdado
    return service.criar_usuario_da_organizacao(conexao, ator, dados)
