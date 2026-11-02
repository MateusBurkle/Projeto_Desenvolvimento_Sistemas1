"""Schemas de resposta do módulo 6 (contrato modulo-6.yaml). Somente leitura. UC22, UC23, UC24."""
from pydantic import BaseModel

SITUACOES_EQUIPAMENTO = ("Recebido", "Em avaliação", "Em manutenção", "Recondicionado", "Disponível", "Vendido",
                         "Doado", "Destinado à reciclagem")  # RN17
SITUACOES_SOLICITACAO = ("Aguardando avaliação", "Em avaliação", "Avaliada")  # RF21
ID_MAX = 2**63 - 1  # RNF04


class ItemVendaRel(BaseModel):
    id_equipamento: int
    identificacao: str
    modelo: str
    categoria: str
    valor: float


class VendaRel(BaseModel):
    id_venda: int
    data_venda: str
    id_organizacao_cliente: int
    cliente: str
    forma_pagamento: str
    quantidade: int
    valor_total: float
    itens: list[ItemVendaRel]


class RelatorioVendas(BaseModel):  # UC22, RN16
    data_de: str
    data_ate: str
    vendas: list[VendaRel]
    total_vendas: int
    total_equipamentos: int
    valor_total: float


class EquipamentoRel(BaseModel):
    id_equipamento: int
    identificacao: str
    modelo: str
    id_categoria: int
    categoria: str
    condicao: str
    situacao: str
    ativo: bool
    valor: float | None = None
    data_recebimento: str
    origem: str
    destinacao: str | None = None
    destino_detalhe: str | None = None
    data_destinacao: str | None = None


class RelatorioEquipamentos(BaseModel):  # UC23, RN17
    items: list[EquipamentoRel]
    total: int
    page: int
    size: int
    resumo_por_situacao: dict[str, int]


class EquipamentoSolRel(BaseModel):
    id_equipamento: int
    identificacao: str
    condicao: str
    situacao: str
    destinacao: str | None = None
    ong_beneficiada: str | None = None
    data_doacao: str | None = None


class ItemSolRel(BaseModel):
    id_item_solicitacao: int
    tipo: str
    modelo: str
    quantidade: int
    equipamentos_cadastrados: int
    equipamentos: list[EquipamentoSolRel]


class SolicitacaoRel(BaseModel):
    id_solicitacao: int
    id_organizacao_doadora: int
    empresa_doadora: str
    data_solicitacao: str
    situacao: str
    avaliacao_pendente: bool
    pendencias: list[str]
    itens: list[ItemSolRel]


class RelatorioOrganizacoes(BaseModel):  # UC24, RN18, RN21
    items: list[SolicitacaoRel]
    total: int
    page: int
    size: int
