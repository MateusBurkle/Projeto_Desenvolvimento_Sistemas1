"""Rotas do módulo 5 - notas fiscais simuladas (contrato modulo-5.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query, Response

from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.erros import ErroApi
from app.notas_fiscais import schemas, service
from app.permissoes import ADMINISTRADOR, CLIENTE_EMPRESA

router = APIRouter(tags=["Notas fiscais"])

_admin = exigir_perfis(ADMINISTRADOR)  # RN19: só o Administrador emite
_admin_ou_cliente = exigir_perfis(ADMINISTRADOR, CLIENTE_EMPRESA)  # RN20; Funcionário -> 403


def _checar_id(valor: int, mensagem: str) -> None:
    if valor > schemas.ID_MAX:  # RNF04
        raise ErroApi(404, "NAO_ENCONTRADO", mensagem)


@router.post("/vendas/{id_venda}/nota-fiscal", response_model=schemas.NotaFiscal, status_code=201,
             operation_id="emitirNotaFiscal")
def emitir(id_venda: int, response: Response, _: dict = Depends(_admin),
           conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC16 fluxo principal, FA1 (200 com a existente), FE1, FE2; RF19; RN19
    _checar_id(id_venda, "Venda não encontrada.")
    nota, criada = service.emitir(conexao, id_venda)
    if not criada:
        response.status_code = 200
    return nota


@router.get("/notas-fiscais", response_model=schemas.PaginaNotas, operation_id="listarNotasFiscais")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           id_organizacao_cliente: int | None = Query(None, le=schemas.ID_MAX),
           data_de: date | None = None, data_ate: date | None = None,
           usuario: dict = Depends(_admin_ou_cliente), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC17 passo 1-2; RF20; RN20, RNF05
    filtros = {"id_organizacao_cliente": id_organizacao_cliente, "data_de": data_de, "data_ate": data_ate}
    return service.listar(conexao, usuario, page, size, filtros)


# Declarada antes de /notas-fiscais/{id_nota}: caminhos distintos, sem conflito; mantida junto por clareza
@router.get("/notas-fiscais/{id_nota}/download", operation_id="baixarNotaFiscal", response_class=Response)
def baixar(id_nota: int, usuario: dict = Depends(_admin_ou_cliente), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC17 passo 5; RF20; RN20: HTML imprimível, com valores escapados e a marca SIMULADA
    _checar_id(id_nota, "Nota fiscal não encontrada.")
    nome, html = service.baixar(conexao, usuario, id_nota)
    return Response(content=html, media_type="text/html; charset=utf-8", headers={
        "Content-Disposition": f'attachment; filename="{nome}"',
        "X-Content-Type-Options": "nosniff",
        "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'",
    })


@router.get("/notas-fiscais/{id_nota}", response_model=schemas.NotaFiscal, operation_id="obterNotaFiscal")
def obter(id_nota: int, usuario: dict = Depends(_admin_ou_cliente), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC17 passo 3-4, FA1, FE1; RN20
    _checar_id(id_nota, "Nota fiscal não encontrada.")
    return service.obter(conexao, usuario, id_nota)
