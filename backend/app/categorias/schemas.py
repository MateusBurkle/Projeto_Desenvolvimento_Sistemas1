"""Modelos Pydantic do módulo 3 - categorias (contrato modulo-3.yaml). UC05; RF07, RF08; RN07, RN08; RNF04."""
from pydantic import BaseModel, field_validator


class CategoriaEntrada(BaseModel):
    """UC05 passo 3: nome de 1 a 80 caracteres, sem espaços nas pontas (DP-31)."""
    nome: str

    @field_validator("nome")
    @classmethod
    def _nome(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("obrigatório")
        if len(v) > 80:
            raise ValueError("máximo de 80 caracteres")
        return v


class CategoriaSituacao(BaseModel):
    """UC05 FA2, RN07."""
    ativa: bool


class Categoria(BaseModel):
    id_categoria: int
    nome: str
    ativa: bool
    protegida: bool
    total_equipamentos: int


class PaginaCategorias(BaseModel):
    items: list[Categoria]
    total: int
    page: int
    size: int
