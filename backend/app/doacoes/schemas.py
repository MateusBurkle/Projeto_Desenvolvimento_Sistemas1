"""Modelos Pydantic do módulo 4 - doações (contrato modulo-4.yaml). UC11, UC19; RF04, RF12, RF15; RN12, RN15."""
from pydantic import BaseModel

ID_MAX = 2**63 - 1  # RNF04


class OngElegivel(BaseModel):
    id_organizacao: int
    nome_razao_social: str


class Doacao(BaseModel):
    id_doacao: int
    id_equipamento: int
    identificacao: str
    modelo: str
    categoria_nome: str
    condicao: str
    situacao: str
    id_organizacao_ong: int
    nome_ong: str
    data_doacao: str
    id_solicitacao: int | None


class PaginaDoacoes(BaseModel):
    items: list[Doacao]
    total: int
    page: int
    size: int
