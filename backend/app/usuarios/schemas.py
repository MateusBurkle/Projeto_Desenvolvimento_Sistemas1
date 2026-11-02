"""Modelos Pydantic do módulo 1 (contrato modulo-1.yaml). Nunca incluem senha nem senha_hash (RNF03)."""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from app.erros import ID_MAX

_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")

Perfil = Literal["Administrador", "Funcionário", "Cliente Empresa", "Cliente ONG", "Empresa Doadora"]
TipoOrganizacao = Literal["Cliente Empresa", "Cliente ONG", "Empresa Doadora"]


def _validar_nome(valor: str) -> str:
    """UC02/UC03 FE1: nome obrigatório, 1 a 120 caracteres, sem espaços nas pontas."""
    valor = valor.strip()
    if not valor:
        raise ValueError("obrigatório")
    if len(valor) > 120:
        raise ValueError("máximo de 120 caracteres")
    return valor


def _validar_email(valor: str) -> str:
    """UC26: e-mail normalizado (strip + minúsculas), formato x@y.z, máx. 254."""
    valor = valor.strip().lower()
    if len(valor) > 254:
        raise ValueError("máximo de 254 caracteres")
    if not _PADRAO_EMAIL.match(valor):
        raise ValueError("formato inválido")
    return valor


def _validar_senha(valor: str) -> str:
    """DP-09/DP-13, RNF03: 8 a 128 caracteres."""
    if len(valor) < 8:
        raise ValueError("mínimo de 8 caracteres")
    if len(valor) > 128:
        raise ValueError("máximo de 128 caracteres")
    return valor


class _Base(BaseModel):
    @field_validator("nome", check_fields=False)
    @classmethod
    def _nome(cls, v: str) -> str:
        return _validar_nome(v)

    @field_validator("email", check_fields=False)
    @classmethod
    def _email(cls, v: str) -> str:
        return _validar_email(v)

    @field_validator("senha", check_fields=False)
    @classmethod
    def _senha(cls, v: str | None) -> str | None:
        return None if v is None else _validar_senha(v)


class UsuarioCriar(_Base):
    """UC02 passo 3, UC27 passo 1."""
    nome: str
    email: str
    senha: str
    perfil: Perfil
    id_organizacao: int | None = Field(None, le=ID_MAX)  # RNF04


class UsuarioAlterar(_Base):
    """UC02 FA1/FA2. `senha` opcional (ausente mantém a atual)."""
    nome: str
    email: str
    senha: str | None = None
    perfil: Perfil
    id_organizacao: int | None = Field(None, le=ID_MAX)  # RNF04


class UsuarioOrganizacaoCriar(_Base):
    """UC03 passo 2. perfil/id_organizacao são opcionais e só aceitos se iguais aos herdados."""
    nome: str
    email: str
    senha: str
    perfil: Perfil | None = None
    id_organizacao: int | None = Field(None, le=ID_MAX)  # RNF04


class Usuario(BaseModel):
    id_usuario: int
    nome: str
    email: str
    perfil: str
    id_organizacao: int | None
    nome_organizacao: str | None
    funcionalidades: list[str]


class PaginaUsuarios(BaseModel):
    items: list[Usuario]
    total: int
    page: int
    size: int


class PerfilAtribuivel(BaseModel):
    perfil: str
    exige_organizacao: bool
    tipo_organizacao: str | None


class OrganizacaoOpcao(BaseModel):
    id_organizacao: int
    nome_razao_social: str
    tipo: str


class ExcluirPropriaConta(BaseModel):
    """DP-64: senha atual para confirmar a exclusão da própria conta."""
    senha: str = Field(min_length=1, max_length=128)


class PropriaContaAlterar(BaseModel):
    """UC02/UC03, DP-95: nome e/ou e-mail da própria conta. Perfil/organização do corpo são ignorados."""
    nome: str | None = None
    email: str | None = None

    @field_validator("nome")
    @classmethod
    def _nome(cls, v):
        return None if v is None else _validar_nome(v)

    @field_validator("email")
    @classmethod
    def _email(cls, v):
        return None if v is None else _validar_email(v)

    @model_validator(mode="after")
    def _ao_menos_um(self):
        if self.nome is None and self.email is None:
            raise ValueError("informe ao menos um campo: nome ou email")
        return self


class PropriaSenhaAlterar(BaseModel):
    """DP-96: somente a senha nova (8 a 128 caracteres); nunca devolvida nem registrada."""
    senha_nova: str

    @field_validator("senha_nova")
    @classmethod
    def _senha(cls, v):
        return _validar_senha(v)
