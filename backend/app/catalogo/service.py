"""Regras de negócio do módulo 5 - catálogo: UC12 (RF04, RF13; RN04, RN13; DP-50). Perfil Cliente Empresa na rota."""
from app.catalogo import repository
from app.erros import ErroApi


def _para_dict(linha) -> dict:
    d = dict(linha)
    d["valor"] = float(d["valor"])
    return d


def listar(conexao, page: int, size: int, id_categoria: int | None, q: str | None) -> dict:
    """UC12 passo 2, FE1: lista vazia é 200 com items []. RN13: só ativos, disponíveis e aptos."""
    linhas, total = repository.listar(conexao, page, size, id_categoria, q)
    return {"items": [_para_dict(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, id_equipamento: int) -> dict:
    """UC12 passo 4, FA1: item fora das regras do catálogo -> 404."""
    linha = repository.buscar_por_id(conexao, id_equipamento)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Equipamento não encontrado no catálogo.")
    return _para_dict(linha)
