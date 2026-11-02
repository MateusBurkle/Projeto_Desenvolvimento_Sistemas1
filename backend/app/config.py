"""Configuração da aplicação, lida de variáveis de ambiente (RNF03, RNF05).

Variáveis:
- LEAF_AMBIENTE        'desenvolvimento' (padrão) ou 'producao'.
- LEAF_JWT_SECRET      segredo HS256. OBRIGATÓRIO em producao.
- LEAF_DB_PATH         caminho do arquivo SQLite (padrão: backend/leaf_ti.db).
- LEAF_CORS_ORIGINS    origens permitidas, separadas por vírgula.
- LEAF_TOKEN_MINUTOS   validade do token (padrão 60, DP-04).
- LEAF_IMAGENS_DIR     pasta das imagens de equipamento (padrão: <raiz>/armazenamento/imagens/equipamentos; DP-86).
"""
import os
from dataclasses import dataclass
from pathlib import Path

RAIZ_BACKEND = Path(__file__).resolve().parent.parent
RAIZ_PROJETO = RAIZ_BACKEND.parent
ARQUIVO_SQL = RAIZ_PROJETO / "banco" / "Codigo_Modelo_Fisico.sql"

# ATENÇÃO: segredo PADRÃO SOMENTE PARA DESENVOLVIMENTO. Nunca use em produção.
SEGREDO_DEV_INSEGURO = "dev-somente-desenvolvimento-nao-use-em-producao"

ORIGENS_PADRAO = (
    "http://localhost:5500,http://127.0.0.1:5500,"
    "http://localhost:8080,http://127.0.0.1:8080,"
    "http://localhost:3000,http://127.0.0.1:3000,"
    "http://localhost:8000,http://127.0.0.1:8000,"
    "null"  # front aberto direto do disco (file://)
)


@dataclass(frozen=True)
class Configuracao:
    ambiente: str
    jwt_segredo: str
    jwt_algoritmo: str
    token_minutos: int
    caminho_banco: str
    origens_cors: list
    segredo_inseguro: bool
    imagens_dir: str = ""


def obter_configuracao() -> Configuracao:
    """Lê o ambiente a cada chamada (facilita testes)."""
    ambiente = os.environ.get("LEAF_AMBIENTE", "desenvolvimento").strip().lower()
    segredo = os.environ.get("LEAF_JWT_SECRET", "").strip()
    inseguro = False
    if not segredo:
        if ambiente == "producao":
            raise RuntimeError("Defina LEAF_JWT_SECRET: segredo JWT é obrigatório em produção.")
        segredo = SEGREDO_DEV_INSEGURO
        inseguro = True
    origens = os.environ.get("LEAF_CORS_ORIGINS", ORIGENS_PADRAO)
    return Configuracao(
        ambiente=ambiente,
        jwt_segredo=segredo,
        jwt_algoritmo="HS256",
        token_minutos=int(os.environ.get("LEAF_TOKEN_MINUTOS", "60")),
        caminho_banco=os.environ.get("LEAF_DB_PATH", str(RAIZ_BACKEND / "leaf_ti.db")),
        origens_cors=[o.strip() for o in origens.split(",") if o.strip()],
        segredo_inseguro=inseguro,
        imagens_dir=os.environ.get("LEAF_IMAGENS_DIR") or str(RAIZ_PROJETO / "armazenamento" / "imagens" / "equipamentos"),
    )
