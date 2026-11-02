"""Modelos do marketplace público (UC12, DP-68, DP-74). Sem origem, identificação nem vínculos internos."""
from pydantic import BaseModel

ID_MAX = 2**63 - 1  # RNF04


class Categoria(BaseModel):
    id_categoria: int
    nome: str


class Produto(BaseModel):
    id_equipamento: int
    modelo: str
    categoria: str
    id_categoria: int
    condicao: str
    imagem_url: str | None = None  # DP-84/DP-90: só a URL pública; alt = modelo
    valor: float | None = None  # só para Cliente Empresa autenticado (DP-74); omitido nos demais


class PaginaProdutos(BaseModel):
    items: list[Produto]
    total: int
    page: int
    size: int
