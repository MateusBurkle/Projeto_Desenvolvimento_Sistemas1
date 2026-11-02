"""Modelos Pydantic do módulo 3 - equipamentos (contrato modulo-3.yaml).
UC07, UC08; RF11, RF12; RN08, RN11, RN12; RNF04."""
import re
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Literal

from pydantic import BaseModel, Field, field_validator

Situacao = Literal["Recebido", "Em avaliação", "Em manutenção", "Recondicionado", "Disponível", "Vendido", "Doado",
                   "Destinado à reciclagem"]  # RF12 (CHECK do banco)
Condicao = Literal["A avaliar", "Bom", "Regular", "Necessita reparo", "Sem condições de reuso"]  # DP-32

ID_MAX = 2**63 - 1  # RNF04: maior inteiro do SQLite; acima disso o sqlite3 levanta OverflowError

_PADRAO_DATA = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def _texto(valor: str, maximo: int) -> str:
    """UC07 FE1, RNF04: obrigatório, sem espaços nas pontas, até `maximo` caracteres."""
    valor = valor.strip()
    if not valor:
        raise ValueError("obrigatório")
    if len(valor) > maximo:
        raise ValueError(f"máximo de {maximo} caracteres")
    return valor


def converter_data_iso(valor: str) -> date:
    """Data ISO estrita AAAA-MM-DD (UC07 FE1)."""
    if not isinstance(valor, str) or not _PADRAO_DATA.match(valor):
        raise ValueError("data inválida (use AAAA-MM-DD)")
    try:
        return date.fromisoformat(valor)
    except ValueError:
        raise ValueError("data inválida (use AAAA-MM-DD)")


def _data_nao_futura(valor: str) -> str:
    if converter_data_iso(valor) > date.today():
        raise ValueError("a data não pode ser futura")
    return valor


VALOR_MAX = Decimal("9999999.99")  # DP-39


def _valor(valor):
    """UC07 passo 3: opcional, >= 0, até 2 casas decimais. Guarda como float arredondado."""
    if valor is None:
        return None
    if isinstance(valor, bool) or not isinstance(valor, (int, float, Decimal)):
        raise ValueError("deve ser um número")
    try:
        d = Decimal(str(valor))
    except InvalidOperation:
        raise ValueError("deve ser um número")
    if not d.is_finite():
        raise ValueError("deve ser um número")
    if d < 0:
        raise ValueError("não pode ser negativo")
    if d > VALOR_MAX:
        raise ValueError("no máximo 9.999.999,99")  # DP-39
    if d != d.quantize(Decimal("0.01")):
        raise ValueError("no máximo 2 casas decimais")
    return float(d)


class _Dados(BaseModel):
    identificacao: str
    id_categoria: int = Field(le=ID_MAX)  # RNF04
    modelo: str
    condicao: Condicao
    origem: str
    data_recebimento: str
    valor: float | None = None
    id_item_solicitacao: int | None = Field(None, le=ID_MAX)  # RNF04

    @field_validator("identificacao")
    @classmethod
    def _identificacao(cls, v: str) -> str:
        return _texto(v, 50)

    @field_validator("modelo")
    @classmethod
    def _modelo(cls, v: str) -> str:
        return _texto(v, 150)

    @field_validator("origem")
    @classmethod
    def _origem(cls, v: str) -> str:
        return _texto(v, 100)

    @field_validator("data_recebimento")
    @classmethod
    def _data(cls, v: str) -> str:
        return _data_nao_futura(v)

    @field_validator("valor", mode="before")
    @classmethod
    def _valor_antes(cls, v):
        return _valor(v)


class EquipamentoCriar(_Dados):
    """UC07 fluxo principal. `situacao` opcional (padrão Recebido)."""
    situacao: Situacao | None = None


class EquipamentoAlterar(_Dados):
    """UC07 FA1. Sem `situacao` nem `ativo`."""


class SituacaoEntrada(BaseModel):
    """UC08. `id_organizacao_ong` e `data_doacao` só com situacao = Doado (conferido no service, 400)."""
    situacao: Situacao
    id_organizacao_ong: int | None = Field(None, le=ID_MAX)  # RNF04
    data_doacao: str | None = None

    @field_validator("data_doacao")
    @classmethod
    def _data_doacao(cls, v: str | None) -> str | None:
        if v is not None:
            converter_data_iso(v)  # formato (400); "não futura" e "não anterior ao recebimento" são 422 DOACAO_INVALIDA
        return v


class AtivoEntrada(BaseModel):
    """UC07 FA2."""
    ativo: bool


class Doacao(BaseModel):
    id_doacao: int
    id_organizacao_ong: int
    nome_ong: str
    data_doacao: str


class Equipamento(BaseModel):
    id_equipamento: int
    identificacao: str
    id_categoria: int
    nome_categoria: str
    categoria_ativa: bool
    modelo: str
    condicao: str
    origem: str
    situacao: str
    data_recebimento: str
    valor: float | None
    id_item_solicitacao: int | None
    ativo: bool
    imagem: str | None = None  # DP-87: nome do arquivo
    imagem_url: str | None = None  # DP-90
    doacao: Doacao | None


class PaginaEquipamentos(BaseModel):
    items: list[Equipamento]
    total: int
    page: int
    size: int
