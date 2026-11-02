"""Rotas do módulo 5 - vendas e pedidos (contrato modulo-5.yaml). Sem regra de negócio aqui: tudo no service."""
import sqlite3
from datetime import date

from fastapi import APIRouter, Depends, Query

from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.erros import ErroApi
from app.permissoes import ADMINISTRADOR, CLIENTE_EMPRESA, FUNCIONARIO
from app.vendas import schemas, service

router = APIRouter(tags=["Vendas"])

_interno = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)
_interno_ou_cliente = exigir_perfis(ADMINISTRADOR, FUNCIONARIO, CLIENTE_EMPRESA)  # RN15: ONG/Doadora -> 403
_cliente_empresa = exigir_perfis(CLIENTE_EMPRESA)  # RN13: Cliente ONG não compra


def _checar_id(id_venda: int) -> None:
    # RNF04: id acima de 2^63-1 não existe no banco; 404 em vez de estourar o sqlite3
    if id_venda > schemas.ID_MAX:
        raise ErroApi(404, "NAO_ENCONTRADO", "Pedido ou venda não encontrado.")


@router.get("/vendas", response_model=schemas.PaginaVendas, operation_id="listarVendas")
def listar(page: int = Query(1, ge=1), size: int = Query(20, ge=1, le=100),
           situacao: schemas.SituacaoVenda | None = None,
           id_organizacao_cliente: int | None = Query(None, le=schemas.ID_MAX),
           data_de: date | None = None, data_ate: date | None = None,
           usuario: dict = Depends(_interno_ou_cliente), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC21 passo 2-4 (geral) e UC18 passo 2 (próprias); RF15; RN15, RNF05
    filtros = {"situacao": situacao, "id_organizacao_cliente": id_organizacao_cliente,
               "data_de": data_de, "data_ate": data_ate}
    return service.listar(conexao, usuario, page, size, filtros)


@router.post("/vendas", response_model=schemas.Venda, status_code=201, operation_id="criarPedido")
def criar(dados: schemas.PedidoEntrada, usuario: dict = Depends(_cliente_empresa),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC13 fluxo principal, FE1, FE2; RF13; RN13 (Cliente Empresa; organização do token)
    return service.criar_pedido(conexao, usuario, dados)


@router.get("/vendas/{id_venda}", response_model=schemas.Venda, operation_id="obterVenda")
def obter(id_venda: int, usuario: dict = Depends(_interno_ou_cliente),
          conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC14 passo 2, UC18 passo 4/FE1, UC21 passo 5; RN15, RNF05
    _checar_id(id_venda)
    return service.obter(conexao, usuario, id_venda)


@router.patch("/vendas/{id_venda}", response_model=schemas.Venda, operation_id="ajustarPedido")
def ajustar(id_venda: int, dados: schemas.AjusteEntrada, _: dict = Depends(_interno),
            conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC14 FA1, RN03, DP-47: ajusta a forma de pagamento do pedido pendente
    _checar_id(id_venda)
    return service.ajustar_pedido(conexao, id_venda, dados)


@router.put("/vendas/{id_venda}/itens", response_model=schemas.Venda, operation_id="substituirItensPedido")
def substituir_itens(id_venda: int, dados: schemas.PedidoEntrada, usuario: dict = Depends(_interno_ou_cliente),
                     conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC13 FA1, UC14 FA1; RN13, DP-47: altera os equipamentos do pedido pendente
    _checar_id(id_venda)
    return service.substituir_itens(conexao, usuario, id_venda, dados)


@router.post("/vendas/{id_venda}/cancelar", response_model=schemas.Venda, operation_id="cancelarPedido")
def cancelar(id_venda: int, usuario: dict = Depends(_interno_ou_cliente),
             conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC13 FA1, UC14 FA2; DP-45, DP-47: cancela o pedido pendente e libera os equipamentos
    _checar_id(id_venda)
    return service.cancelar(conexao, usuario, id_venda)


@router.post("/vendas/{id_venda}/confirmar", response_model=schemas.Venda, operation_id="confirmarVenda")
def confirmar(id_venda: int, dados: schemas.ConfirmacaoEntrada, _: dict = Depends(_interno),
              conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC14 fluxo principal + UC15 (include); RF13, RF14; RN03, RN13, RN14: confirma a venda e baixa o estoque
    _checar_id(id_venda)
    return service.confirmar(conexao, id_venda, dados)
