"""Regras de negócio do acesso: UC04 (Acessar o sistema) e UC28 (Validar credenciais). RF01, RN01, RNF03."""
import sqlite3

from app import permissoes, seguranca
from app.auth import repository
from app.erros import ErroApi

SITUACAO_ORGANIZACAO_ATIVA = "Ativa"  # DP-03

_ERRO_CREDENCIAIS = ("CREDENCIAIS_INVALIDAS", "Não foi possível entrar. Verifique o e-mail e a senha.")
_ERRO_INATIVA = ("CONTA_INATIVA", "Acesso negado. A conta ou a organização está inativa.")


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def conta_esta_ativa(usuario) -> bool:
    """DP-02, RN06, RN09: Administrador/Funcionário (sem organização) sempre ativos; demais exigem
    organização vinculada com situacao 'Ativa'. Perfil de cliente/doadora sem organização é tratado como inativo."""
    if usuario["id_organizacao"] is None:
        return usuario["perfil"] in (permissoes.ADMINISTRADOR, permissoes.FUNCIONARIO)
    return usuario["situacao_organizacao"] == SITUACAO_ORGANIZACAO_ATIVA


def montar_sessao(usuario) -> dict:
    """UC04 passo 4: dados do usuário e funcionalidades do perfil (RN01). Sem senha/hash."""
    return {
        "id_usuario": usuario["id_usuario"],
        "nome": usuario["nome"],
        "email": usuario["email"],
        "perfil": usuario["perfil"],
        "id_organizacao": usuario["id_organizacao"],
        "funcionalidades": permissoes.funcionalidades_do_perfil(usuario["perfil"]),
    }


def autenticar(conexao: sqlite3.Connection, email: str, senha: str) -> dict:
    """UC04 / UC28 (RN01, RNF03). 401 igual para e-mail inexistente e senha errada (DP-05);
    403 CONTA_INATIVA somente após a senha correta."""
    usuario = repository.buscar_por_email(conexao, normalizar_email(email))
    # A comparação bcrypt ocorre mesmo sem usuário, para não revelar a existência do e-mail pelo tempo.
    hash_comparado = usuario["senha_hash"] if usuario else seguranca.HASH_FALSO
    senha_ok = seguranca.verificar_senha(senha, hash_comparado)
    if usuario is None or not senha_ok:
        raise ErroApi(401, *_ERRO_CREDENCIAIS)  # UC04 FE1, UC28 FE1
    if not conta_esta_ativa(usuario):
        raise ErroApi(403, *_ERRO_INATIVA)  # UC04 FE2, UC28 FE1
    token, expira_em = seguranca.criar_token(usuario["id_usuario"], usuario["perfil"], usuario["id_organizacao"])
    return {"access_token": token, "token_type": "bearer", "expires_in": expira_em, "usuario": montar_sessao(usuario)}


def obter_usuario_autenticado(conexao: sqlite3.Connection, id_usuario: int) -> dict:
    """Reavalia a conta a cada requisição (RN06, RN09). Usuário removido -> 401; conta inativa -> 403."""
    usuario = repository.buscar_por_id(conexao, id_usuario)
    if usuario is None:
        raise ErroApi(401, "NAO_AUTENTICADO", "Sessão inválida ou expirada. Entre novamente.")
    if not conta_esta_ativa(usuario):
        raise ErroApi(403, *_ERRO_INATIVA)
    return montar_sessao(usuario)


def criar_administrador_inicial(conexao: sqlite3.Connection, nome: str, email: str, senha: str) -> int:
    """Mantido por compatibilidade (testes do módulo 0); a implementação agora está em app.usuarios.service."""
    from app.usuarios import service as usuarios_service  # import tardio evita ciclo
    return usuarios_service.criar_administrador_inicial(conexao, nome, email, senha)
