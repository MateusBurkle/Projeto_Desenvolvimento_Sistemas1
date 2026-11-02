"""Regras de negócio do módulo 4 - doações: UC11 (ONGs elegíveis) e UC19 (consulta). RF04, RF12, RF15; RN04, RN12, RN15; RNF05.
A criação da DOACAO ocorre somente pela situação 'Doado' (DP-36); aqui há apenas leitura (DP-44)."""
from app.doacoes import repository
from app.erros import ErroApi
from app.permissoes import CLIENTE_ONG


def listar_ongs_elegiveis(conexao) -> list[dict]:
    """UC11 passo 2: ONGs ativas elegíveis."""
    return [dict(l) for l in repository.listar_ongs_elegiveis(conexao)]


def listar(conexao, usuario: dict, page: int, size: int, filtros: dict) -> dict:
    """UC19 passo 2-3, FA1 (lista vazia é 200). Cliente ONG: só a própria organização (RN04, RN15); o filtro é ignorado."""
    filtros = dict(filtros)
    if usuario["perfil"] == CLIENTE_ONG:
        filtros["id_organizacao_ong"] = usuario["id_organizacao"] if usuario["id_organizacao"] is not None else -1
    for chave in ("data_de", "data_ate"):
        if filtros.get(chave) is not None:
            filtros[chave] = filtros[chave].isoformat()
    linhas, total = repository.listar(conexao, page, size, filtros)
    return {"items": [dict(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, usuario: dict, id_doacao: int) -> dict:
    """UC19 passo 4, FE1: doação de outra ONG -> 404 (RN04, RN15, RNF05)."""
    linha = repository.buscar_por_id(conexao, id_doacao)
    if linha is None or (usuario["perfil"] == CLIENTE_ONG and linha["id_organizacao_ong"] != usuario["id_organizacao"]):
        raise ErroApi(404, "NAO_ENCONTRADO", "Doação não encontrada.")
    return dict(linha)
