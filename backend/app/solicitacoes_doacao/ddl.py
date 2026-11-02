"""DDL do módulo 7 (DP-75): tabelas criadas na inicialização, sem editar banco/Codigo_Modelo_Fisico.sql.
Cópia fiel do `x-ddl` de contratos/modulo-7.yaml."""
import sqlite3

DDL = """
CREATE TABLE IF NOT EXISTS SOLICITACAO_DOACAO (
    id_solicitacao_doacao INTEGER PRIMARY KEY,
    id_organizacao_ong INTEGER NOT NULL,
    data_solicitacao TEXT NOT NULL,
    situacao TEXT NOT NULL CHECK (situacao IN ('Pendente','Aprovada','Recusada','Cancelada')),
    motivo_recusa TEXT NULL,
    decidido_por TEXT NULL,
    data_decisao TEXT NULL,
    FOREIGN KEY (id_organizacao_ong) REFERENCES ORGANIZACAO(id_organizacao) ON DELETE RESTRICT ON UPDATE CASCADE
);
CREATE TABLE IF NOT EXISTS ITEM_SOLICITACAO_DOACAO (
    id_item_solicitacao_doacao INTEGER PRIMARY KEY,
    id_solicitacao_doacao INTEGER NOT NULL,
    id_equipamento INTEGER NOT NULL,
    FOREIGN KEY (id_solicitacao_doacao) REFERENCES SOLICITACAO_DOACAO(id_solicitacao_doacao) ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (id_equipamento) REFERENCES EQUIPAMENTO(id_equipamento) ON DELETE RESTRICT ON UPDATE CASCADE,
    UNIQUE (id_solicitacao_doacao, id_equipamento)
);
"""


def criar_tabelas(conexao: sqlite3.Connection) -> None:
    """DP-75: idempotente (IF NOT EXISTS)."""
    conexao.executescript(DDL)
