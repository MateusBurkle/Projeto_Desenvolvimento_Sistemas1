"""Rotas do módulo 6 - relatórios (contrato modulo-6.yaml). Somente leitura; regra no service."""
import sqlite3

from fastapi import APIRouter, Depends, Query

from app.db import get_conexao
from app.dependencias import exigir_perfis
from app.permissoes import ADMINISTRADOR, FUNCIONARIO
from app.relatorios import schemas, service

router = APIRouter(tags=["Relatórios"])

_interno = exigir_perfis(ADMINISTRADOR, FUNCIONARIO)  # RN17, RN03, RNF05: demais perfis -> 403

# Datas e situação chegam como texto e são validadas no service (400 PERIODO_INVALIDO / FILTRO_INVALIDO, DP-58).
# page limitado para evitar OFFSET fora da faixa do SQLite (RNF04).


@router.get("/relatorios/vendas", response_model=schemas.RelatorioVendas, operation_id="relatorioVendas")
def vendas(data_de: str | None = None, data_ate: str | None = None,
           _: dict = Depends(_interno), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC22; RF16; RN16, RNF05
    return service.relatorio_vendas(conexao, data_de, data_ate)


@router.get("/relatorios/equipamentos", response_model=schemas.RelatorioEquipamentos,
            operation_id="relatorioEquipamentos")
def equipamentos(id_categoria: int | None = None, situacao: str | None = None,
                 data_de: str | None = None, data_ate: str | None = None,
                 page: int = Query(1, ge=1, le=10**9), size: int = Query(20, ge=1, le=100),
                 _: dict = Depends(_interno), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC23; RF17; RN17, RNF05
    return service.relatorio_equipamentos(conexao, id_categoria, situacao, data_de, data_ate, page, size)


@router.get("/relatorios/organizacoes-destinacoes", response_model=schemas.RelatorioOrganizacoes,
            operation_id="relatorioOrganizacoesDestinacoes")
def organizacoes_destinacoes(id_organizacao_doadora: int | None = None, situacao: str | None = None,
                             data_de: str | None = None, data_ate: str | None = None,
                             page: int = Query(1, ge=1, le=10**9), size: int = Query(20, ge=1, le=100),
                             _: dict = Depends(_interno), conexao: sqlite3.Connection = Depends(get_conexao)):
    # UC24; RF18, RF21; RN18, RN21, RNF05
    return service.relatorio_organizacoes(conexao, id_organizacao_doadora, situacao, data_de, data_ate, page, size)
