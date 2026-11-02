"""Dependências reutilizáveis de autenticação e autorização (RN01, RNF05).

Uso nas rotas dos próximos módulos:
    usuario = Depends(get_usuario_atual)
    usuario = Depends(exigir_perfis("Administrador", "Funcionário"))
O dicionário devolvido tem: id_usuario, nome, email, perfil, id_organizacao, funcionalidades.
"""
import sqlite3

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import service as auth_service
from app.db import get_conexao
from app.erros import ErroApi
from app.seguranca import decodificar_token

_esquema_bearer = HTTPBearer(auto_error=False)


def get_usuario_atual(
    credenciais: HTTPAuthorizationCredentials | None = Depends(_esquema_bearer),
    conexao: sqlite3.Connection = Depends(get_conexao),
) -> dict:
    """UC04, RN01, RNF05: 401 NAO_AUTENTICADO sem token válido; 403 CONTA_INATIVA se a conta/organização foi desativada."""
    claims = decodificar_token(credenciais.credentials) if credenciais else None
    if claims is None:
        raise ErroApi(401, "NAO_AUTENTICADO", "Sessão inválida ou expirada. Entre novamente.")
    return auth_service.obter_usuario_autenticado(conexao, int(claims["sub"]))


def exigir_perfis(*perfis: str):
    """Fábrica de dependência: só os perfis informados passam; os demais recebem 403 SEM_PERMISSAO (RN01)."""

    def _verificar(usuario: dict = Depends(get_usuario_atual)) -> dict:
        if usuario["perfil"] not in perfis:
            raise ErroApi(403, "SEM_PERMISSAO", "Você não tem permissão para realizar esta operação.")
        return usuario

    return _verificar
