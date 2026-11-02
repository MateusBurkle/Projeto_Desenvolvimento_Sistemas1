"""Modelos Pydantic do módulo 2 - parceiros (contrato modulo-2.yaml). UC06; RF10; RN10."""
from typing import Literal

from pydantic import BaseModel, Field

from app.erros import ID_MAX

TipoParceria = Literal["Empresa Doadora", "Patrocinador em Potencial"]
SituacaoParceria = Literal["Ativa", "Inativa"]  # DP-27


class ParceiroCriar(BaseModel):
    """UC06 passo 3. `situacao_parceria` opcional (padrão Ativa)."""
    id_organizacao: int = Field(le=ID_MAX)  # RNF04
    tipo_parceria: TipoParceria
    situacao_parceria: SituacaoParceria | None = None


class ParceiroAlterar(BaseModel):
    """UC06 FA1: somente a atuação."""
    tipo_parceria: TipoParceria


class SituacaoParceriaAlterar(BaseModel):
    """UC06 FA2."""
    situacao_parceria: SituacaoParceria


class Parceiro(BaseModel):
    id_parceiro: int
    id_organizacao: int
    tipo_parceria: str
    situacao_parceria: str
    nome_razao_social: str
    cnpj: str
    telefone: str
    email: str
    endereco: str
    tipo_organizacao: str
    situacao_organizacao: str


class PaginaParceiros(BaseModel):
    items: list[Parceiro]
    total: int
    page: int
    size: int
