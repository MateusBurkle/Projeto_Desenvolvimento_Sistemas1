"""Regras de negócio do módulo 2 - organizações: UC01, UC25. RF06, RF09; RN06, RN09; RNF04."""
import sqlite3

from app import permissoes
from app.erros import ErroApi
from app.organizacoes import repository
from app.usuarios import repository as usuarios_repository

SITUACAO_ATIVA = "Ativa"  # DP-03
TIPO_DOADORA = "Empresa Doadora"
_TIPOS_CLIENTE = (permissoes.CLIENTE_EMPRESA, permissoes.CLIENTE_ONG)  # RF09: o que o Funcionário pode alterar


def _para_dict(linha) -> dict:
    d = dict(linha)
    d["possui_parceria"] = bool(d["possui_parceria"])
    return d


def _obter_ou_404(conexao, id_organizacao: int):
    linha = repository.buscar_por_id(conexao, id_organizacao)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Organização não encontrada.")
    return linha


def _erro_cnpj_duplicado() -> ErroApi:
    return ErroApi(409, "CNPJ_DUPLICADO", "Este CNPJ já está cadastrado.", {"cnpj": "duplicado"})


def _exigir_cnpj_livre(conexao, cnpj: str, excluir_id: int | None = None) -> None:
    """UC25 (include de UC01), UC01 FE1, RN06/RN09: CNPJ único entre TODAS as organizações (inclusive inativas)."""
    if repository.buscar_id_por_cnpj(conexao, cnpj, excluir_id) is not None:
        raise _erro_cnpj_duplicado()


def listar(conexao, page, size, tipo, situacao, q, sem_parceria) -> dict:
    """UC01 FA1, RF06."""
    linhas, total = repository.listar(conexao, page, size, tipo, situacao, q, sem_parceria)
    return {"items": [_para_dict(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, id_organizacao: int) -> dict:
    """UC01 FA1: 404 se inexistente."""
    return _para_dict(_obter_ou_404(conexao, id_organizacao))


def criar(conexao, dados) -> dict:
    """UC01 fluxo principal, UC25, RN06/RN09. Formato já validado (400); depois UC25 (409); depois grava."""
    _exigir_cnpj_livre(conexao, dados.cnpj)
    valores = dados.model_dump()
    valores["situacao"] = dados.situacao or SITUACAO_ATIVA  # padrão Ativa
    try:
        novo_id = repository.inserir(conexao, valores)
    except sqlite3.IntegrityError:  # corrida entre duas requisições com o mesmo CNPJ (UC25)
        conexao.rollback()
        raise _erro_cnpj_duplicado()
    return obter(conexao, novo_id)


def _validar_mudanca_tipo(conexao, id_organizacao: int, tipo_atual: str, tipo_novo: str) -> None:
    """RN06 (DP-23): tipo não muda com usuários vinculados nem com parceria 'Empresa Doadora' (salvo manter o tipo)."""
    if tipo_novo == tipo_atual:
        return
    if repository.contar_usuarios(conexao, id_organizacao) > 0:
        raise ErroApi(422, "TIPO_EM_USO",
                      "O tipo não pode ser alterado enquanto houver usuários vinculados à organização.",
                      {"tipo": "organização possui usuários vinculados"})
    if tipo_novo != TIPO_DOADORA and repository.possui_parceria_doadora(conexao, id_organizacao):
        raise ErroApi(422, "TIPO_EM_USO",
                      "O tipo não pode ser alterado enquanto houver parceria como Empresa Doadora.",
                      {"tipo": "organização possui parceria como Empresa Doadora"})


def alterar(conexao, id_organizacao: int, dados) -> dict:
    """UC01 FA1, UC25, RN06. Ordem: 404 -> (400 no schema) -> 409 (exclui o próprio) -> 422 tipo em uso -> grava."""
    atual = _obter_ou_404(conexao, id_organizacao)
    _exigir_cnpj_livre(conexao, dados.cnpj, excluir_id=id_organizacao)
    _validar_mudanca_tipo(conexao, id_organizacao, atual["tipo"], dados.tipo)
    try:
        repository.atualizar(conexao, id_organizacao, dados.model_dump())
    except sqlite3.IntegrityError:
        conexao.rollback()
        raise _erro_cnpj_duplicado()
    return obter(conexao, id_organizacao)


def alterar_contato(conexao, ator: dict, id_organizacao: int, dados) -> dict:
    """RF09, RN09, DP-26: telefone/e-mail/endereço. Funcionário só em Cliente Empresa e Cliente ONG."""
    atual = _obter_ou_404(conexao, id_organizacao)
    if ator["perfil"] == permissoes.FUNCIONARIO and atual["tipo"] not in _TIPOS_CLIENTE:
        raise ErroApi(403, "OPERACAO_NAO_PERMITIDA",
                      "O Funcionário só pode alterar o contato de Cliente Empresa e Cliente ONG.",
                      {"id_organizacao": "tipo não permitido para este perfil"})
    repository.atualizar_contato(conexao, id_organizacao, dados.telefone, dados.email, dados.endereco)
    return obter(conexao, id_organizacao)


def _propria_ou_404(conexao, ator: dict):
    """DP-98: a organização é sempre a do usuário autenticado; sem vínculo -> 404."""
    if ator.get("id_organizacao") is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Organização não encontrada.")
    return _obter_ou_404(conexao, ator["id_organizacao"])


def obter_propria(conexao, ator: dict) -> dict:
    """UC01, UC06, DP-93/98: dados da própria organização."""
    return _para_dict(_propria_ou_404(conexao, ator))


def alterar_propria(conexao, ator: dict, dados) -> dict:
    """UC01, UC06, DP-93/94: nome e contato da própria organização (nome não é único; inativa também pode)."""
    atual = _propria_ou_404(conexao, ator)

    def escolher(novo, chave):
        return novo if novo is not None else atual[chave]

    repository.atualizar_dados_proprios(
        conexao, atual["id_organizacao"], escolher(dados.nome_razao_social, "nome_razao_social"),
        escolher(dados.telefone, "telefone"), escolher(dados.email, "email"), escolher(dados.endereco, "endereco"))
    return obter(conexao, atual["id_organizacao"])


def alterar_situacao(conexao, id_organizacao: int, dados) -> dict:
    """UC01 FA2, RN06, RN09: desativa/reativa sem apagar nada e sem cascata. Idempotente."""
    atual = _obter_ou_404(conexao, id_organizacao)
    if atual["situacao"] != dados.situacao:
        repository.atualizar_situacao(conexao, id_organizacao, dados.situacao)
    return obter(conexao, id_organizacao)


def excluir(conexao, id_organizacao: int, excluir_usuarios: bool) -> None:
    """UC01, UC06, RN06, RN09 (DP-63): exclusão física de ORGANIZACAO + PARCEIRO (+ USUARIO se confirmado).
    Ordem: 404 -> histórico (422 ORGANIZACAO_EM_USO) -> usuários sem confirmação (422 ORGANIZACAO_COM_USUARIOS)
    -> remove tudo em uma transação."""
    _obter_ou_404(conexao, id_organizacao)
    if repository.possui_historico(conexao, id_organizacao):
        raise ErroApi(422, "ORGANIZACAO_EM_USO",
                      "Esta organização tem histórico e não pode ser excluída; você pode desativá-la",
                      {"id_organizacao": "possui histórico"})
    usuarios = repository.listar_usuarios(conexao, id_organizacao)
    if usuarios and not excluir_usuarios:
        raise ErroApi(422, "ORGANIZACAO_COM_USUARIOS",
                      "Esta organização possui usuários vinculados; confirme a exclusão deles junto com a organização.",
                      {"quantidade_usuarios": len(usuarios), "usuarios": usuarios})
    # DP-65: a exclusão em lote não pode remover a última conta Administrador
    admins_na_organizacao = sum(1 for u in usuarios if u["perfil"] == "Administrador")
    if admins_na_organizacao and admins_na_organizacao >= usuarios_repository.contar_por_perfil(conexao, "Administrador"):
        raise ErroApi(422, "ALTERACAO_BLOQUEADA",
                      "Não é possível excluir a última conta Administrador do sistema.",
                      {"usuarios": "bloqueado"})
    repository.excluir_com_vinculos(conexao, id_organizacao)
