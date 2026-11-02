"""Acesso ao SQLite (sqlite3 da biblioteca padrão). O modelo vem de banco/Codigo_Modelo_Fisico.sql."""
import sqlite3

from app.solicitacoes_doacao.ddl import criar_tabelas as criar_tabelas_doacao
from app.config import ARQUIVO_SQL, obter_configuracao


def conectar() -> sqlite3.Connection:
    """Abre uma conexão com chaves estrangeiras ativas (o PRAGMA vale por conexão)."""
    conexao = sqlite3.connect(obter_configuracao().caminho_banco, check_same_thread=False)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    # Comparação sem diferenciar maiúsculas/minúsculas inclusive com acentos (DP-31; lower() do SQLite só trata ASCII).
    conexao.create_function("casefold", 1, lambda s: s.casefold() if isinstance(s, str) else s, deterministic=True)
    return conexao


# Módulo 3, UC05 passo 6, RF08: categorias base, criadas na inicialização e protegidas.
CATEGORIAS_BASE = ("Computadores", "Notebooks", "Monitores", "Periféricos", "Placas de vídeo", "Placas-mãe")


def _migrar_equipamento_ativo(conexao: sqlite3.Connection) -> None:
    """DP-30 (opção A): bancos criados antes do Módulo 3 recebem EQUIPAMENTO.ativo sem perder dados."""
    colunas = {linha["name"] for linha in conexao.execute("PRAGMA table_info(EQUIPAMENTO)")}
    if colunas and "ativo" not in colunas:
        conexao.execute("ALTER TABLE EQUIPAMENTO ADD COLUMN ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1))")
        conexao.commit()


def _migrar_equipamento_imagem(conexao: sqlite3.Connection) -> None:
    """UC07, DP-84 a DP-87: EQUIPAMENTO.imagem TEXT NULL (só o nome do arquivo), criada por DDL se não existir."""
    colunas = {linha["name"] for linha in conexao.execute("PRAGMA table_info(EQUIPAMENTO)")}
    if colunas and "imagem" not in colunas:
        conexao.execute("ALTER TABLE EQUIPAMENTO ADD COLUMN imagem TEXT NULL")
        conexao.commit()


def _semear_categorias_base(conexao: sqlite3.Connection) -> None:
    """UC05, RF08, DP-31: cria as seis categorias base que ainda não existem (comparação sem caixa). Idempotente."""
    existentes = {linha["nome"].casefold() for linha in conexao.execute("SELECT nome FROM CATEGORIA")}
    for nome in CATEGORIAS_BASE:
        if nome.casefold() not in existentes:
            conexao.execute("INSERT INTO CATEGORIA (nome, ativa) VALUES (?, 1)", (nome,))
    conexao.commit()


def inicializar_banco() -> None:
    """Cria as tabelas a partir do SQL oficial (idempotente: usa IF NOT EXISTS), migra bancos antigos e semeia
    as categorias base. Não altera o modelo oficial."""
    conexao = conectar()
    try:
        conexao.executescript(ARQUIVO_SQL.read_text(encoding="utf-8"))
        _migrar_equipamento_ativo(conexao)
        _migrar_equipamento_imagem(conexao)  # DP-87
        from app.equipamentos import imagens
        imagens.garantir_pasta()  # DP-86
        criar_tabelas_doacao(conexao)  # Módulo 7, DP-75
        _semear_categorias_base(conexao)
    finally:
        conexao.close()


def get_conexao():
    """Dependência do FastAPI: uma conexão por requisição, sempre fechada ao final."""
    conexao = conectar()
    try:
        yield conexao
    finally:
        conexao.close()
