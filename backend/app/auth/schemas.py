"""Modelos Pydantic do módulo de acesso (contrato modulo-0.yaml)."""
import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator

_PADRAO_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class LoginEntrada(BaseModel):
    """UC04 passo 2; RNF04. O e-mail é normalizado (strip + minúsculas)."""
    email: str = Field(max_length=254)
    senha: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalizar_email(cls, valor: str) -> str:
        valor = valor.strip().lower()
        if not _PADRAO_EMAIL.match(valor):
            raise ValueError("formato inválido")
        return valor


class UsuarioSessao(BaseModel):
    """Nunca inclui senha nem senha_hash (RNF03)."""
    id_usuario: int
    nome: str
    email: str
    perfil: str
    id_organizacao: int | None
    funcionalidades: list[str]


class LoginSaida(BaseModel):
    access_token: str
    token_type: Literal["bearer"] = "bearer"
    expires_in: int
    usuario: UsuarioSessao
