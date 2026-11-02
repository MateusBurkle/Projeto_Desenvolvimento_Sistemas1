"""Rotas de acesso (contrato modulo-0.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3

from fastapi import APIRouter, Depends

from app.auth import schemas, service
from app.db import get_conexao
from app.dependencias import get_usuario_atual

router = APIRouter(prefix="/auth", tags=["Acesso"])


@router.post("/login", response_model=schemas.LoginSaida, operation_id="login")
def login(dados: schemas.LoginEntrada, conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC04, UC28, RF01, RN01, RNF03: autentica e-mail/senha e inicia a sessão (JWT)
    return service.autenticar(conexao, dados.email, dados.senha)


@router.get("/me", response_model=schemas.UsuarioSessao, operation_id="usuarioAtual")
def usuario_atual(usuario: dict = Depends(get_usuario_atual)):
    # UC04 passo 4, RN01, RN06, RN09, RNF05: sessão atual e funcionalidades do perfil (qualquer perfil autenticado)
    return usuario
