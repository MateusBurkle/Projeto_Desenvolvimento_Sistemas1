"""Regras de negócio do módulo 3 - categorias: UC05. RF07, RF08; RN07, RN08; RNF04."""
import sqlite3

from app.categorias import repository
from app.db import CATEGORIAS_BASE
from app.erros import ErroApi

_BASE_SEM_CAIXA = frozenset(n.casefold() for n in CATEGORIAS_BASE)


def eh_protegida(nome: str) -> bool:
    """UC05 passo 6, RF08, DP-31: uma das seis categorias base."""
    return nome.casefold() in _BASE_SEM_CAIXA


def _para_dict(linha) -> dict:
    return {
        "id_categoria": linha["id_categoria"],
        "nome": linha["nome"],
        "ativa": bool(linha["ativa"]),
        "protegida": eh_protegida(linha["nome"]),
        "total_equipamentos": linha["total_equipamentos"],
    }


def _obter_ou_404(conexao, id_categoria: int):
    linha = repository.buscar_por_id(conexao, id_categoria)
    if linha is None:
        raise ErroApi(404, "NAO_ENCONTRADO", "Categoria não encontrada.")
    return linha


def _erro_duplicado() -> ErroApi:
    return ErroApi(409, "NOME_CATEGORIA_DUPLICADO", "Já existe uma categoria com este nome.", {"nome": "duplicado"})


def _erro_protegida(campo: str) -> ErroApi:
    return ErroApi(422, "CATEGORIA_PROTEGIDA",
                   "Esta categoria é uma das categorias base e não pode ser desativada nem renomeada.",
                   {campo: "categoria protegida"})


def listar(conexao, page, size, ativa, q) -> dict:
    """UC05 FA1, RF08."""
    linhas, total = repository.listar(conexao, page, size, ativa, q)
    return {"items": [_para_dict(l) for l in linhas], "total": total, "page": page, "size": size}


def obter(conexao, id_categoria: int) -> dict:
    """UC05 FA1: 404 se inexistente."""
    return _para_dict(_obter_ou_404(conexao, id_categoria))


def criar(conexao, dados) -> dict:
    """UC05 fluxo principal, DP-31. Formato já validado (400); depois duplicidade (409); grava Ativa."""
    if repository.buscar_id_por_nome(conexao, dados.nome) is not None:
        raise _erro_duplicado()
    novo_id = repository.inserir(conexao, dados.nome)
    conexao.commit()
    return obter(conexao, novo_id)


def alterar(conexao, id_categoria: int, dados) -> dict:
    """UC05 FA1, DP-31. Ordem: 400 (schema) -> 404 -> 422 protegida -> 409 (exclui o próprio) -> grava."""
    atual = _obter_ou_404(conexao, id_categoria)
    if eh_protegida(atual["nome"]):
        raise _erro_protegida("nome")
    if repository.buscar_id_por_nome(conexao, dados.nome, excluir_id=id_categoria) is not None:
        raise _erro_duplicado()
    repository.atualizar_nome(conexao, id_categoria, dados.nome)
    conexao.commit()
    return obter(conexao, id_categoria)


def alterar_situacao(conexao, id_categoria: int, dados) -> dict:
    """UC05 FA2, RN07, RN08: desativa/reativa sem apagar vínculos. Protegida não desativa (422). Idempotente."""
    atual = _obter_ou_404(conexao, id_categoria)
    if not dados.ativa and eh_protegida(atual["nome"]):
        raise _erro_protegida("ativa")
    if bool(atual["ativa"]) != dados.ativa:
        repository.atualizar_ativa(conexao, id_categoria, dados.ativa)
        conexao.commit()
    return obter(conexao, id_categoria)
