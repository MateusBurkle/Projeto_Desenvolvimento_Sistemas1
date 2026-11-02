"""Regras de negócio do módulo 1: UC02, UC03, UC26, UC27. RF01, RF02, RF04, RF09; RN02, RN04, RN09; RNF03."""
import sqlite3

from app import permissoes, seguranca
from app.erros import ErroApi
from app.usuarios import repository

SITUACAO_ORGANIZACAO_ATIVA = "Ativa"  # DP-03
_SEM_ORGANIZACAO = (permissoes.ADMINISTRADOR, permissoes.FUNCIONARIO)


def normalizar_email(email: str) -> str:
    return email.strip().lower()


def _para_dict(linha) -> dict:
    """Resposta sem senha/hash (RNF03), com funcionalidades do perfil (UC02 passo 6, matriz do módulo 0)."""
    return {
        "id_usuario": linha["id_usuario"],
        "nome": linha["nome"],
        "email": linha["email"],
        "perfil": linha["perfil"],
        "id_organizacao": linha["id_organizacao"],
        "nome_organizacao": linha["nome_organizacao"],
        "funcionalidades": permissoes.funcionalidades_do_perfil(linha["perfil"]),
    }


def _pagina(linhas, total: int, page: int, size: int) -> dict:
    return {"items": [_para_dict(l) for l in linhas], "total": total, "page": page, "size": size}


def _erro_email_duplicado() -> ErroApi:
    return ErroApi(409, "EMAIL_DUPLICADO", "Este e-mail já está em uso.", {"email": "duplicado"})


def _exigir_email_livre(conexao, email: str, excluir_id: int | None = None) -> None:
    """UC26 (include de UC02/UC03): e-mail sem outra conta, sem diferenciar caixa. FE1 -> 409."""
    if repository.buscar_id_por_email(conexao, email, excluir_id) is not None:
        raise _erro_email_duplicado()


def _validar_perfil_organizacao(conexao, perfil: str, id_organizacao: int | None) -> None:
    """UC27 passo 3 (DP-14), UC02 FE2, RN06/RN09: coerência perfil x organização."""
    if perfil in _SEM_ORGANIZACAO:
        if id_organizacao is not None:
            raise ErroApi(422, "VINCULO_INVALIDO", f"O perfil {perfil} não pode ter organização vinculada.",
                          {"id_organizacao": "deve ser vazio para este perfil"})
        return
    if id_organizacao is None:
        raise ErroApi(422, "VINCULO_INVALIDO", f"O perfil {perfil} exige uma organização do tipo {perfil}.",
                      {"id_organizacao": "obrigatório para este perfil"})
    organizacao = repository.buscar_organizacao(conexao, id_organizacao)
    if organizacao is None or organizacao["situacao"] != SITUACAO_ORGANIZACAO_ATIVA:
        raise ErroApi(422, "ORGANIZACAO_INVALIDA", "A organização informada não existe ou está inativa.",
                      {"id_organizacao": "inexistente ou inativa"})
    if organizacao["tipo"] != perfil:  # o tipo da organização deve ser igual ao perfil de cliente/doadora
        raise ErroApi(422, "VINCULO_INVALIDO", f"O perfil {perfil} exige uma organização do tipo {perfil}.",
                      {"id_organizacao": f"tipo diferente de {perfil}"})


def _bloqueio(mensagem: str, campo: str) -> ErroApi:
    return ErroApi(422, "ALTERACAO_BLOQUEADA", mensagem, {campo: "bloqueado"})


def _obter_ou_404(conexao, id_usuario: int):
    linha = repository.buscar_por_id(conexao, id_usuario)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Usuário não encontrado.")
    return linha


def _inserir(conexao, nome, email, senha, perfil, id_organizacao) -> dict:
    try:
        novo_id = repository.inserir(conexao, nome, email, seguranca.gerar_hash_senha(senha), perfil, id_organizacao)
    except sqlite3.IntegrityError:  # corrida entre duas requisições com o mesmo e-mail (UC26)
        conexao.rollback()
        raise _erro_email_duplicado()
    return _para_dict(repository.buscar_por_id(conexao, novo_id))


# ---- UC02 / UC27 (Administrador) ----

def listar_perfis_atribuiveis() -> list[dict]:
    """UC27 passo 1, RN02: perfis e a exigência de organização/tipo."""
    return [
        {"perfil": p, "exige_organizacao": p not in _SEM_ORGANIZACAO,
         "tipo_organizacao": None if p in _SEM_ORGANIZACAO else p}
        for p in permissoes.PERFIS
    ]


def listar_organizacoes_ativas(conexao, tipo: str | None) -> list[dict]:
    """UC02 passo 2 (DP-15), RN06/RN09."""
    return [dict(l) for l in repository.listar_organizacoes_ativas(conexao, SITUACAO_ORGANIZACAO_ATIVA, tipo)]


def listar_usuarios(conexao, page, size, perfil, id_organizacao, q) -> dict:
    """UC02 FA1."""
    linhas, total = repository.listar(conexao, page, size, perfil, id_organizacao, q)
    return _pagina(linhas, total, page, size)


def obter_usuario(conexao, id_usuario: int) -> dict:
    """UC02 FA1: 404 se inexistente."""
    return _para_dict(_obter_ou_404(conexao, id_usuario))


def criar_usuario(conexao, dados) -> dict:
    """UC02 (passos 3-6), UC26, UC27, RN02, RNF03. Ordem: 409 (UC26) -> 422 (UC27) -> hash -> grava."""
    _exigir_email_livre(conexao, dados.email)
    _validar_perfil_organizacao(conexao, dados.perfil, dados.id_organizacao)
    return _inserir(conexao, dados.nome, dados.email, dados.senha, dados.perfil, dados.id_organizacao)


def alterar_usuario(conexao, ator: dict, id_usuario: int, dados) -> dict:
    """UC02 FA1/FA2, FE3/FE4, UC26, UC27, RN02. Ordem: 404 -> bloqueios -> 409 -> 422 -> grava."""
    atual = _obter_ou_404(conexao, id_usuario)
    if id_usuario == ator["id_usuario"] and (
        dados.perfil != atual["perfil"] or dados.id_organizacao != atual["id_organizacao"]
    ):
        raise _bloqueio("Você não pode alterar o seu próprio perfil ou organização.", "perfil")  # UC02 FE4
    if (atual["perfil"] == permissoes.ADMINISTRADOR and dados.perfil != permissoes.ADMINISTRADOR
            and repository.contar_por_perfil(conexao, permissoes.ADMINISTRADOR) <= 1):
        raise _bloqueio("Não é possível alterar o perfil da última conta Administrador.", "perfil")  # UC02 FE4
    _exigir_email_livre(conexao, dados.email, excluir_id=id_usuario)  # a própria conta não conta como duplicada
    _validar_perfil_organizacao(conexao, dados.perfil, dados.id_organizacao)
    senha_hash = seguranca.gerar_hash_senha(dados.senha) if dados.senha is not None else None
    try:
        repository.atualizar(conexao, id_usuario, dados.nome, dados.email, dados.perfil, dados.id_organizacao, senha_hash)
    except sqlite3.IntegrityError:
        conexao.rollback()
        raise _erro_email_duplicado()
    return _para_dict(repository.buscar_por_id(conexao, id_usuario))


def excluir_usuario(conexao, ator: dict, id_usuario: int) -> None:
    """UC02 FA3, FE4, RN02: exclusão física; bloqueia a própria conta e a última conta Administrador."""
    alvo = _obter_ou_404(conexao, id_usuario)
    if id_usuario == ator["id_usuario"]:
        raise _bloqueio("Você não pode excluir a sua própria conta.", "id_usuario")
    if (alvo["perfil"] == permissoes.ADMINISTRADOR
            and repository.contar_por_perfil(conexao, permissoes.ADMINISTRADOR) <= 1):
        raise _bloqueio("Não é possível excluir a última conta Administrador.", "id_usuario")
    repository.excluir(conexao, id_usuario)


def excluir_propria_conta(conexao, ator: dict, senha: str) -> None:
    """UC02 FA3 ampliado, RN02, RNF03 (DP-64/65/66): qualquer perfil exclui a própria conta com a senha atual.
    Senha errada -> 401 SENHA_INVALIDA; última conta Administrador -> 422 ALTERACAO_BLOQUEADA."""
    senha_hash = repository.buscar_senha_hash(conexao, ator["id_usuario"])
    if senha_hash is None or not seguranca.verificar_senha(senha, senha_hash):
        raise ErroApi(401, "SENHA_INVALIDA", "Senha atual incorreta.", {"senha": "incorreta"})
    if (ator["perfil"] == permissoes.ADMINISTRADOR
            and repository.contar_por_perfil(conexao, permissoes.ADMINISTRADOR) <= 1):
        raise _bloqueio("Não é possível excluir a última conta Administrador.", "id_usuario")  # DP-65
    repository.excluir(conexao, ator["id_usuario"])  # DP-66: organização e histórico permanecem


# ---- Conta própria (Cliente Empresa / Cliente ONG / Empresa Doadora) ----

def alterar_propria_conta(conexao, ator: dict, dados) -> dict:
    """UC02, UC03, UC26, DP-95: nome/e-mail da própria conta. E-mail de OUTRA conta -> 409; perfil/organização intactos."""
    atual = _obter_ou_404(conexao, ator["id_usuario"])
    nome = dados.nome if dados.nome is not None else atual["nome"]
    email = dados.email if dados.email is not None else atual["email"]
    _exigir_email_livre(conexao, email, excluir_id=ator["id_usuario"])
    try:
        repository.atualizar_nome_email(conexao, ator["id_usuario"], nome, email)
    except sqlite3.IntegrityError:
        conexao.rollback()
        raise _erro_email_duplicado()
    return _para_dict(repository.buscar_por_id(conexao, ator["id_usuario"]))


def alterar_propria_senha(conexao, ator: dict, senha_nova: str) -> None:
    """UC02, RNF03, DP-96/97: sem senha atual; igual à atual (checkpw no hash guardado) -> 422 SENHA_IGUAL_ATUAL."""
    senha_hash = repository.buscar_senha_hash(conexao, ator["id_usuario"])
    if senha_hash is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Usuário não encontrado.")
    if seguranca.verificar_senha(senha_nova, senha_hash):
        raise ErroApi(422, "SENHA_IGUAL_ATUAL", "A nova senha deve ser diferente da senha atual.",
                      {"senha_nova": "igual à atual"})
    repository.atualizar_senha_hash(conexao, ator["id_usuario"], seguranca.gerar_hash_senha(senha_nova))


# ---- UC03 (Cliente Empresa / Cliente ONG) ----

def listar_usuarios_da_organizacao(conexao, ator: dict, page: int, size: int) -> dict:
    """UC03 FA1, RN04: somente contas do mesmo id_organizacao do solicitante."""
    linhas, total = repository.listar(conexao, page, size, id_organizacao=ator["id_organizacao"])
    return _pagina(linhas, total, page, size)


def _negado(campo: str) -> ErroApi:
    return ErroApi(403, "OPERACAO_NAO_PERMITIDA",
                   "Você só pode cadastrar usuários da sua própria organização, com o mesmo perfil.",
                   {campo: "não permitido"})  # UC03 FE2


def criar_usuario_da_organizacao(conexao, ator: dict, dados) -> dict:
    """UC03 (passos 2-5), FE1, FE2, UC26, RN02, RN04. Perfil e organização são herdados de quem cadastra."""
    if dados.perfil is not None and dados.perfil != ator["perfil"]:
        raise _negado("perfil")
    if dados.id_organizacao is not None and dados.id_organizacao != ator["id_organizacao"]:
        raise _negado("id_organizacao")
    _exigir_email_livre(conexao, dados.email)
    return _inserir(conexao, dados.nome, dados.email, dados.senha, ator["perfil"], ator["id_organizacao"])


# ---- Carga inicial (DP-04) ----

def criar_administrador_inicial(conexao: sqlite3.Connection, nome: str, email: str, senha: str) -> int:
    """Carga inicial do primeiro Administrador (DP-04). Senha gravada só como hash bcrypt (RNF03)."""
    email = normalizar_email(email)
    if repository.buscar_id_por_email(conexao, email) is not None:
        raise ValueError("Já existe um usuário com este e-mail.")
    return repository.inserir_administrador(conexao, nome.strip(), email, seguranca.gerar_hash_senha(senha))
