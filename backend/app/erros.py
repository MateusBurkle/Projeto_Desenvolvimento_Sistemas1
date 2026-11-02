"""Erros de API e handlers globais no formato {codigo, mensagem, campos} (docs/CONVENCOES.md, RNF04)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


ID_MAX = 2**63 - 1  # RNF04: maior inteiro do SQLite; acima disso o sqlite3 levanta OverflowError


class ErroApi(Exception):
    """Erro de negócio/acesso, convertido em resposta JSON padrão."""

    def __init__(self, status: int, codigo: str, mensagem: str, campos: dict | None = None):
        super().__init__(mensagem)
        self.status = status
        self.codigo = codigo
        self.mensagem = mensagem
        self.campos = campos or {}


def _resposta(status: int, codigo: str, mensagem: str, campos: dict | None = None) -> JSONResponse:
    return JSONResponse(status_code=status, content={"codigo": codigo, "mensagem": mensagem, "campos": campos or {}})


_TIPOS = {
    "missing": "obrigatório",
    "string_too_short": "obrigatório",
    "string_too_long": "valor muito longo",
    "string_type": "texto inválido",
    "json_invalid": "JSON inválido",
}


def _texto_campo(erro: dict) -> str:
    if erro["type"] == "value_error":
        return str(erro.get("msg", "")).removeprefix("Value error, ") or "valor inválido"
    return _TIPOS.get(erro["type"], "valor inválido")


async def _tratar_erro_api(_: Request, exc: ErroApi):
    return _resposta(exc.status, exc.codigo, exc.mensagem, exc.campos)


async def _tratar_validacao(_: Request, exc: RequestValidationError):
    """Validação do Pydantic -> 400 DADOS_INVALIDOS (RNF04). Não ecoa valores enviados (evita vazar senha)."""
    erros = exc.errors()
    # id de rota fora da faixa do banco nunca existe -> 404 (RNF04), em vez de 500
    if any(e["loc"][:1] == ("path",) and e["type"] == "less_than_equal" for e in erros):
        return _resposta(404, "NAO_ENCONTRADO", "Recurso não encontrado.")
    campos = {}
    for erro in erros:
        nome = next((str(p) for p in reversed(erro["loc"]) if p not in ("body", "query", "path")), "corpo")
        campos.setdefault(nome, _texto_campo(erro))
    return _resposta(400, "DADOS_INVALIDOS", "Dados inválidos. Corrija os campos indicados.", campos)


async def _tratar_http(_: Request, exc: StarletteHTTPException):
    mapa = {404: "NAO_ENCONTRADO", 405: "METODO_NAO_PERMITIDO"}
    codigo = mapa.get(exc.status_code, "ERRO_HTTP")
    mensagem = "Recurso não encontrado." if exc.status_code == 404 else "Requisição não permitida."
    return _resposta(exc.status_code, codigo, mensagem)


async def _tratar_inesperado(_: Request, exc: Exception):
    return _resposta(500, "ERRO_INTERNO", "Erro interno. Tente novamente mais tarde.")


def registrar_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ErroApi, _tratar_erro_api)
    app.add_exception_handler(RequestValidationError, _tratar_validacao)
    app.add_exception_handler(StarletteHTTPException, _tratar_http)
    app.add_exception_handler(Exception, _tratar_inesperado)
