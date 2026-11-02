"""Modelos Pydantic do módulo 5 - catálogo (contrato modulo-5.yaml). UC12; RF04, RF13; RN04, RN13."""
from pydantic import BaseModel

ID_MAX = 2**63 - 1  # RNF04


class ItemCatalogo(BaseModel):
    id_equipamento: int
    identificacao: str
    id_categoria: int
    categoria_nome: str
    modelo: str
    condicao: str
    valor: float


class PaginaCatalogo(BaseModel):
    items: list[ItemCatalogo]
    total: int
    page: int
    size: int
