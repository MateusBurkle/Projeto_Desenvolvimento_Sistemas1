"""Ponto de entrada da API LEAF TI. Rodar: uvicorn app.main:app --reload (dentro de backend/)."""
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.auth.router import router as auth_router
from app.catalogo.router import router as catalogo_router
from app.categorias.router import router as categorias_router
from app.config import obter_configuracao
from app.db import inicializar_banco
from app.doacoes.router import router as doacoes_router
from app.equipamentos.router import router as equipamentos_router
from app.erros import registrar_handlers
from app.notas_fiscais.router import router as notas_fiscais_router
from app.organizacoes.router import router as organizacoes_router
from app.parceiros.router import router as parceiros_router
from app.relatorios.router import router as relatorios_router
from app.marketplace.router import router as marketplace_router
from app.solicitacoes_doacao.router import router as solicitacoes_doacao_router
from app.solicitacoes.router import router as solicitacoes_router
from app.usuarios.router import router as usuarios_router
from app.vendas.router import router as vendas_router

log = logging.getLogger("leaf_ti")

# backend/app/main.py -> raiz do projeto/frontend
_PASTA_FRONT_PADRAO = Path(__file__).resolve().parent.parent.parent / "frontend"


@asynccontextmanager
async def ciclo_de_vida(_: FastAPI):
    cfg = obter_configuracao()
    if cfg.segredo_inseguro:
        log.warning("LEAF_JWT_SECRET não definido: usando segredo de DESENVOLVIMENTO (inseguro). Não use em produção.")
    inicializar_banco()
    yield


def criar_app() -> FastAPI:
    app = FastAPI(title="LEAF TI - API", version="1.0.0", lifespan=ciclo_de_vida)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=obter_configuracao().origens_cors,
        allow_methods=["*"],
        allow_headers=["Authorization", "Content-Type"],
    )
    registrar_handlers(app)
    app.include_router(auth_router, prefix="/api/v1")
    app.include_router(usuarios_router, prefix="/api/v1")  # Módulo 1: UC02, UC03, UC26, UC27
    app.include_router(organizacoes_router, prefix="/api/v1")  # Módulo 2: UC01, UC25
    app.include_router(parceiros_router, prefix="/api/v1")  # Módulo 2: UC06
    app.include_router(categorias_router, prefix="/api/v1")  # Módulo 3: UC05
    app.include_router(equipamentos_router, prefix="/api/v1")  # Módulo 3: UC07, UC08
    app.include_router(solicitacoes_router, prefix="/api/v1")  # Módulo 4: UC09, UC10, UC20
    # Módulo 7: antes de doacoes_router, para /doacoes/solicitacoes não ser capturada por /doacoes/{id_doacao}
    app.include_router(solicitacoes_doacao_router, prefix="/api/v1")  # Novo UC Solicitar doação, UC11, UC19
    app.include_router(marketplace_router, prefix="/api/v1")  # UC12 ampliado (público)
    app.include_router(doacoes_router, prefix="/api/v1")  # Módulo 4: UC11, UC19
    app.include_router(catalogo_router, prefix="/api/v1")  # Módulo 5: UC12
    app.include_router(vendas_router, prefix="/api/v1")  # Módulo 5: UC13, UC14, UC15, UC18, UC21
    app.include_router(relatorios_router, prefix="/api/v1")  # Módulo 6: UC22, UC23, UC24
    app.include_router(notas_fiscais_router, prefix="/api/v1")  # Módulo 5: UC16, UC17
    # Front-end estático na raiz, montado DEPOIS da API (js/api.js usa /api/v1 na mesma origem).
    pasta_front = Path(os.environ.get("LEAF_FRONTEND_DIR") or _PASTA_FRONT_PADRAO).resolve()
    if pasta_front.is_dir():
        # Fallback do roteador (e não app.mount("/")): serve o front só quando nenhuma rota da API casa,
        # inclusive rotas adicionadas depois; /api/* inexistente cai no 404 JSON padrão.
        app.router.default = StaticFiles(directory=str(pasta_front), html=True)
    else:
        log.warning("Pasta do front-end não encontrada: %s (somente a API será servida).", pasta_front)
    return app


app = criar_app()
