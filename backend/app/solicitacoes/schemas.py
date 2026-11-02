"""Modelos Pydantic do módulo 4 - solicitações (contrato modulo-4.yaml).
UC09, UC10, UC11, UC20; RF05, RF21; RN05, RN10, RN11, RN12, RN21; RNF04."""
from typing import Literal

from pydantic import BaseModel, Field, StrictInt, field_validator

from app.equipamentos.schemas import ID_MAX, Condicao, _data_nao_futura, _texto, _valor, converter_data_iso

SituacaoSolicitacao = Literal["Aguardando avaliação", "Em avaliação", "Avaliada"]  # DP-40
Destinacao = Literal["Venda", "Doação", "Reciclagem"]  # DP-42
SituacaoInicialEquipamento = Literal["Recebido", "Em avaliação", "Em manutenção"]  # contrato AvaliacaoEntrada


class ItemEntrada(BaseModel):
    """UC09 passo 2-3, FE1 (400), DP-43: tipo e modelo de 1 a 100; quantidade inteira de 1 a 9999."""
    tipo: str
    modelo: str
    quantidade: StrictInt

    @field_validator("tipo", "modelo")
    @classmethod
    def _textos(cls, v: str) -> str:
        return _texto(v, 100)

    @field_validator("quantidade")
    @classmethod
    def _quantidade(cls, v: int) -> int:
        if not 1 <= v <= 9999:
            raise ValueError("deve ser de 1 a 9999")
        return v


class SolicitacaoEntrada(BaseModel):
    """UC09: de 1 a 50 itens (DP-43). A organização vem do token, nunca do corpo (RN05)."""
    itens: list[ItemEntrada] = Field(min_length=1, max_length=50)


class AvaliacaoEntrada(BaseModel):
    """UC10 passo 3 (DP-41): dados de uma unidade avaliada. `modelo` vem do item; `origem` padrão 'Solicitação N'."""
    identificacao: str
    id_categoria: int = Field(le=ID_MAX)  # RNF04
    condicao: Condicao
    origem: str | None = None
    data_recebimento: str
    valor: float | None = None
    situacao: SituacaoInicialEquipamento | None = None

    @field_validator("identificacao")
    @classmethod
    def _identificacao(cls, v: str) -> str:
        return _texto(v, 50)

    @field_validator("origem")
    @classmethod
    def _origem(cls, v: str | None) -> str | None:
        return None if v is None else _texto(v, 100)

    @field_validator("data_recebimento")
    @classmethod
    def _data(cls, v: str) -> str:
        return _data_nao_futura(v)

    @field_validator("valor", mode="before")
    @classmethod
    def _valor_antes(cls, v):
        return _valor(v)


class DestinacaoEntrada(BaseModel):
    """UC10 passo 4, UC11 passo 3. Doação exige ONG e data; Venda/Reciclagem rejeitam (conferido no service, 400)."""
    destinacao: Destinacao
    id_organizacao_ong: int | None = Field(None, le=ID_MAX)  # RNF04
    data_doacao: str | None = None

    @field_validator("data_doacao")
    @classmethod
    def _data_doacao(cls, v: str | None) -> str | None:
        if v is not None:
            converter_data_iso(v)  # formato (400); regras de data são 422 DOACAO_INVALIDA
        return v


class EquipamentoVinculado(BaseModel):
    """UC10/UC20: `valor` é omitido para Empresa Doadora (a chave nem é enviada; rotas usam exclude_unset)."""
    id_equipamento: int
    identificacao: str
    id_categoria: int
    categoria_nome: str
    modelo: str
    condicao: str
    situacao: str
    ativo: bool
    valor: float | None = None
    data_recebimento: str
    destinacao: Destinacao | None
    id_organizacao_ong: int | None
    nome_ong: str | None
    data_doacao: str | None


class ItemSolicitacao(BaseModel):
    id_item_solicitacao: int
    tipo: str
    modelo: str
    quantidade: int
    quantidade_cadastrada: int
    quantidade_avaliada: int
    avaliado: bool
    equipamentos: list[EquipamentoVinculado]


class Solicitacao(BaseModel):
    id_solicitacao: int
    id_organizacao_doadora: int
    nome_organizacao: str
    data_solicitacao: str
    situacao: SituacaoSolicitacao
    pendencias: list[str]
    itens: list[ItemSolicitacao]


class SolicitacaoResumo(BaseModel):
    id_solicitacao: int
    id_organizacao_doadora: int
    nome_organizacao: str
    data_solicitacao: str
    situacao: SituacaoSolicitacao
    total_itens: int
    total_unidades: int
    unidades_avaliadas: int


class PaginaSolicitacoes(BaseModel):
    items: list[SolicitacaoResumo]
    total: int
    page: int
    size: int
