"""Modelos Pydantic do módulo 2 - organizações (contrato modulo-2.yaml). UC01, UC25; RF06, RF09; RN06, RN09; RNF04."""
import re
from typing import Literal

from pydantic import BaseModel, field_validator, model_validator

TipoOrganizacao = Literal["Cliente Empresa", "Cliente ONG", "Empresa Doadora"]
SituacaoOrganizacao = Literal["Ativa", "Inativa"]  # DP-03

_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MASCARA_CNPJ = re.compile(r"[.\-/\s]")
_MASCARA_TELEFONE = re.compile(r"[()\-.\s+]")


def normalizar_cnpj(valor: str) -> str:
    """UC25 passo 2 (DP-21): remove . / - e espaços; exige exatamente 14 dígitos (sem dígito verificador)."""
    limpo = _MASCARA_CNPJ.sub("", valor)
    if len(limpo) != 14 or not (limpo.isascii() and limpo.isdigit()):
        raise ValueError("deve ter 14 dígitos")
    return limpo


def _validar_texto(valor: str, maximo: int) -> str:
    """UC01 FE2, RNF04: obrigatório, sem espaços nas pontas, até `maximo` caracteres."""
    valor = valor.strip()
    if not valor:
        raise ValueError("obrigatório")
    if len(valor) > maximo:
        raise ValueError(f"máximo de {maximo} caracteres")
    return valor


def _validar_telefone(valor: str) -> str:
    """DP-22: 10 ou 11 dígitos (máscara aceita); guarda só dígitos."""
    limpo = _MASCARA_TELEFONE.sub("", valor)
    if not (limpo.isascii() and limpo.isdigit()) or len(limpo) not in (10, 11):
        raise ValueError("deve ter 10 ou 11 dígitos")
    return limpo


def _validar_email(valor: str) -> str:
    """DP-22: formato x@y.z, até 254, em minúsculas."""
    valor = valor.strip().lower()
    if len(valor) > 254:
        raise ValueError("máximo de 254 caracteres")
    if not _PADRAO_EMAIL.match(valor):
        raise ValueError("formato inválido")
    return valor


class _Contato(BaseModel):
    telefone: str
    email: str
    endereco: str

    @field_validator("telefone")
    @classmethod
    def _telefone(cls, v: str) -> str:
        return _validar_telefone(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v: str) -> str:
        return _validar_email(v)

    @field_validator("endereco")
    @classmethod
    def _endereco(cls, v: str) -> str:
        return _validar_texto(v, 255)


class _Cadastro(_Contato):
    nome_razao_social: str
    cnpj: str
    tipo: TipoOrganizacao

    @field_validator("nome_razao_social")
    @classmethod
    def _nome(cls, v: str) -> str:
        return _validar_texto(v, 150)

    @field_validator("cnpj")
    @classmethod
    def _cnpj(cls, v: str) -> str:
        return normalizar_cnpj(v)


class OrganizacaoCriar(_Cadastro):
    """UC01 fluxo principal. `situacao` opcional (padrão Ativa)."""
    situacao: SituacaoOrganizacao | None = None


class OrganizacaoAlterar(_Cadastro):
    """UC01 FA1. Sem `situacao` (PATCH /situacao)."""


class ContatoAlterar(_Contato):
    """RF09, DP-26."""


class MinhaOrganizacaoAlterar(BaseModel):
    """UC01, UC06, DP-93: nome, telefone, e-mail e endereço da PRÓPRIA organização (campos extras ignorados)."""
    nome_razao_social: str | None = None
    telefone: str | None = None
    email: str | None = None
    endereco: str | None = None

    @field_validator("nome_razao_social")
    @classmethod
    def _nome(cls, v):
        return None if v is None else _validar_texto(v, 150)

    @field_validator("telefone")
    @classmethod
    def _telefone(cls, v):
        return None if v is None else _validar_telefone(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return None if v is None else _validar_email(v)

    @field_validator("endereco")
    @classmethod
    def _endereco(cls, v):
        return None if v is None else _validar_texto(v, 255)

    @model_validator(mode="after")
    def _ao_menos_um(self):
        if all(getattr(self, c) is None for c in ("nome_razao_social", "telefone", "email", "endereco")):
            raise ValueError("informe ao menos um campo")
        return self


class SituacaoAlterar(BaseModel):
    """UC01 FA2."""
    situacao: SituacaoOrganizacao


class Organizacao(BaseModel):
    id_organizacao: int
    cnpj: str
    nome_razao_social: str
    tipo: str
    telefone: str
    email: str
    endereco: str
    situacao: str
    possui_parceria: bool


class PaginaOrganizacoes(BaseModel):
    items: list[Organizacao]
    total: int
    page: int
    size: int
