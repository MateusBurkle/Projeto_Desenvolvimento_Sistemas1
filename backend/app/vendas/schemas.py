"""Modelos Pydantic do módulo 5 - vendas/pedidos (contrato modulo-5.yaml).
UC13, UC14, UC15, UC18, UC21; RF13, RF14, RF15; RN13, RN14, RN15; RNF04."""
from datetime import date
from typing import Any, Literal

from pydantic import BaseModel, field_validator

from app.equipamentos.schemas import converter_data_iso

ID_MAX = 2**63 - 1  # RNF04

SituacaoVenda = Literal["Pendente", "Confirmada", "Cancelada"]
FormaPagamento = Literal["Pix", "Boleto", "Transferência bancária", "Cartão de crédito"]  # DP-46


class PedidoEntrada(BaseModel):
    """UC13 passo 3 / FE1 (RN13, DP-45): 1 a 50 ids de equipamento, inteiros, sem repetição, dentro da faixa do banco."""
    ids_equipamento: list[Any]
    forma_pagamento: FormaPagamento | None = None  # DP-79: opcional; omitida = "A definir"

    @field_validator("ids_equipamento")
    @classmethod
    def _validar_ids(cls, ids: list) -> list[int]:
        if not 1 <= len(ids) <= 50:
            raise ValueError("informe de 1 a 50 equipamentos")
        for i in ids:
            if isinstance(i, bool) or not isinstance(i, int) or i < 1 or i > ID_MAX:
                raise ValueError("identificador de equipamento inválido")
        if len(set(ids)) != len(ids):
            raise ValueError("equipamento repetido")
        return ids


class AjusteEntrada(BaseModel):
    """UC14 FA1 (DP-47): somente a forma de pagamento."""
    forma_pagamento: FormaPagamento


class ConfirmacaoEntrada(BaseModel):
    """UC14 passo 3 / FE1 (DP-46): data ISO não futura e forma de pagamento permitida."""
    data_venda: str
    forma_pagamento: FormaPagamento

    @field_validator("data_venda")
    @classmethod
    def _validar_data(cls, valor: str) -> str:
        if converter_data_iso(valor) > date.today():
            raise ValueError("a data não pode ser futura")
        return valor


class ItemVenda(BaseModel):
    id_item_venda: int
    id_equipamento: int
    identificacao: str
    modelo: str
    categoria_nome: str
    condicao: str
    valor: float


class NotaResumoVenda(BaseModel):
    id_nota: int
    numero: str
    data_emissao: str


class Venda(BaseModel):
    id_venda: int
    id_organizacao_cliente: int
    nome_organizacao: str
    data_venda: str
    situacao: SituacaoVenda
    forma_pagamento: str
    quantidade: int
    valor_total: float
    itens: list[ItemVenda]
    nota_fiscal: NotaResumoVenda | None


class VendaResumo(BaseModel):
    id_venda: int
    id_organizacao_cliente: int
    nome_organizacao: str
    data_venda: str
    situacao: SituacaoVenda
    forma_pagamento: str
    quantidade: int
    valor_total: float
    possui_nota: bool


class PaginaVendas(BaseModel):
    items: list[VendaResumo]
    total: int
    page: int
    size: int
