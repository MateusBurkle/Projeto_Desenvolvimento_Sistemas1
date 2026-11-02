"""Regras do marketplace público (UC12 ampliado; DP-68, DP-74). Valor só para Cliente Empresa; origem nunca sai."""
from app.equipamentos.imagens import url_publica
from app.erros import ErroApi
from app.marketplace import repository
from app.permissoes import CLIENTE_EMPRESA


def _produto(linha, usuario: dict | None) -> dict:
    d = {k: linha[k] for k in ("id_equipamento", "modelo", "categoria", "id_categoria", "condicao")}
    d["imagem_url"] = url_publica(linha["imagem"])  # DP-84/DP-90 (sem origem nem vínculos, DP-74)
    # DP-74: visitante, ONG, Doadora, Administrador e Funcionário não recebem `valor`
    if usuario is not None and usuario["perfil"] == CLIENTE_EMPRESA:
        d["valor"] = None if linha["valor"] is None else float(linha["valor"])  # ausente nos demais (exclude_unset)
    return d


def categorias(conexao) -> list[dict]:
    return [dict(l) for l in repository.listar_categorias(conexao)]


def listar(conexao, usuario: dict | None, page: int, size: int, id_categoria: int | None, busca: str | None) -> dict:
    linhas, total = repository.listar(conexao, page, size, id_categoria, busca)
    return {"items": [_produto(l, usuario) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, usuario: dict | None, id_equipamento: int) -> dict:
    linha = repository.buscar(conexao, id_equipamento)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Produto não encontrado.")
    return _produto(linha, usuario)
