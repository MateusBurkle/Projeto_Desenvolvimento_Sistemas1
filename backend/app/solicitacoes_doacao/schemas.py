"""Modelos Pydantic da solicitação de doação (contrato modulo-7.yaml; DP-69 a DP-73). Nunca expõe valor."""
from pydantic import BaseModel, Field, field_validator

ID_MAX = 2**63 - 1  # RNF04


class CriarSolicitacao(BaseModel):
    ids_equipamentos: list[int] = Field(min_length=1, max_length=20)

    @field_validator("ids_equipamentos")
    @classmethod
    def _validar(cls, ids):
        if len(set(ids)) != len(ids):
            raise ValueError("não repita equipamentos")
        if any(i < 1 or i > ID_MAX for i in ids):
            raise ValueError("identificador inválido")
        return ids


class RecusarSolicitacao(BaseModel):
    motivo: str = Field(min_length=3, max_length=500)  # DP-73

    @field_validator("motivo")
    @classmethod
    def _aparar(cls, v):
        v = v.strip()
        if len(v) < 3:
            raise ValueError("mínimo de 3 caracteres")
        return v


class ItemSolicitacao(BaseModel):
    id_equipamento: int
    modelo: str
    categoria: str
    condicao: str


class Solicitacao(BaseModel):
    id_solicitacao_doacao: int
    id_organizacao_ong: int
    nome_ong: str
    nome_organizacao: str  # igual a nome_ong (nome esperado pelo front)
    data_solicitacao: str
    situacao: str
    motivo_recusa: str | None
    decidido_por: str | None
    data_decisao: str | None
    itens: list[ItemSolicitacao]


class PaginaSolicitacoes(BaseModel):
    items: list[Solicitacao]
    total: int
    page: int
    size: int
