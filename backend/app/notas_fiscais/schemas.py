"""Modelos Pydantic do módulo 5 - notas fiscais simuladas (contrato modulo-5.yaml). UC16, UC17; RF19, RF20; RN19, RN20."""
from datetime import date

from pydantic import BaseModel

from app.vendas.schemas import Venda

ID_MAX = 2**63 - 1  # RNF04


class NotaFiscal(BaseModel):
    id_nota: int
    numero: str
    data_emissao: str
    simulada: bool
    venda: Venda


class NotaResumo(BaseModel):
    id_nota: int
    id_venda: int
    numero: str
    data_emissao: str
    id_organizacao_cliente: int
    nome_organizacao: str
    valor_total: float


class PaginaNotas(BaseModel):
    items: list[NotaResumo]
    total: int
    page: int
    size: int
