-- Modelo físico do banco LEAF TI para SQLite
-- Datas: armazenadas em TEXT no padrão ISO 8601 (AAAA-MM-DD).
-- Valores monetários: NUMERIC; a validação de duas casas decimais deve ocorrer na aplicação.
-- As chaves estrangeiras são ativadas por conexão com PRAGMA foreign_keys = ON.


PRAGMA foreign_keys = ON;

BEGIN TRANSACTION;

CREATE TABLE IF NOT EXISTS ORGANIZACAO (
    id_organizacao INTEGER PRIMARY KEY,
    cnpj TEXT NOT NULL UNIQUE
        CHECK (length(cnpj) = 14 AND cnpj NOT GLOB '*[^0-9]*'),
    nome_razao_social TEXT NOT NULL,
    tipo TEXT NOT NULL,
    telefone TEXT NOT NULL,
    email TEXT NOT NULL,
    endereco TEXT NOT NULL,
    situacao TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS PARCEIRO (
    id_parceiro INTEGER PRIMARY KEY,
    id_organizacao INTEGER NOT NULL UNIQUE,
    tipo_parceria TEXT NOT NULL
        CHECK (tipo_parceria IN ('Empresa Doadora', 'Patrocinador em Potencial')),
    situacao_parceria TEXT NOT NULL,
    FOREIGN KEY (id_organizacao) REFERENCES ORGANIZACAO(id_organizacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS USUARIO (
    id_usuario INTEGER PRIMARY KEY,
    id_organizacao INTEGER NULL,
    email TEXT NOT NULL UNIQUE,
    perfil TEXT NOT NULL
        CHECK (perfil IN ('Administrador', 'Funcionário', 'Cliente Empresa', 'Cliente ONG', 'Empresa Doadora')),
    senha_hash TEXT NOT NULL,
    nome TEXT NOT NULL,
    FOREIGN KEY (id_organizacao) REFERENCES ORGANIZACAO(id_organizacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS SOLICITACAO (
    id_solicitacao INTEGER PRIMARY KEY,
    id_organizacao_doadora INTEGER NOT NULL,
    data_solicitacao TEXT NOT NULL,
    situacao TEXT NOT NULL,
    FOREIGN KEY (id_organizacao_doadora) REFERENCES ORGANIZACAO(id_organizacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS ITEM_SOLICITACAO (
    id_item_solicitacao INTEGER PRIMARY KEY,
    id_solicitacao INTEGER NOT NULL,
    tipo TEXT NOT NULL,
    modelo TEXT NOT NULL,
    quantidade INTEGER NOT NULL,
    FOREIGN KEY (id_solicitacao) REFERENCES SOLICITACAO(id_solicitacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS CATEGORIA (
    id_categoria INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    ativa INTEGER NOT NULL CHECK (ativa IN (0, 1))
);

CREATE TABLE IF NOT EXISTS EQUIPAMENTO (
    id_equipamento INTEGER PRIMARY KEY,
    id_categoria INTEGER NOT NULL,
    id_item_solicitacao INTEGER NULL,
    identificacao TEXT NOT NULL UNIQUE,
    modelo TEXT NOT NULL,
    condicao TEXT NOT NULL,
    origem TEXT NOT NULL,
    situacao TEXT NOT NULL CHECK (situacao IN (
        'Recebido', 'Em avaliação', 'Em manutenção', 'Recondicionado',
        'Disponível', 'Vendido', 'Doado', 'Destinado à reciclagem'
    )),
    ativo INTEGER NOT NULL DEFAULT 1 CHECK (ativo IN (0, 1)),
    valor NUMERIC NULL,
    data_recebimento TEXT NOT NULL,
    imagem TEXT NULL,
    FOREIGN KEY (id_categoria) REFERENCES CATEGORIA(id_categoria)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (id_item_solicitacao) REFERENCES ITEM_SOLICITACAO(id_item_solicitacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- VENDA também guarda o pedido do Cliente Empresa: situacao 'Pendente' = aguardando confirmação (UC13/UC14).
CREATE TABLE IF NOT EXISTS VENDA (
    id_venda INTEGER PRIMARY KEY,
    id_organizacao_cliente INTEGER NOT NULL,
    data_venda TEXT NOT NULL,
    situacao TEXT NOT NULL CHECK (situacao IN ('Pendente', 'Confirmada', 'Cancelada')),
    forma_pagamento TEXT NOT NULL,
    FOREIGN KEY (id_organizacao_cliente) REFERENCES ORGANIZACAO(id_organizacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Cada item representa uma unidade física única (quantidade 1); a quantidade da venda é a contagem dos itens.
CREATE TABLE IF NOT EXISTS ITEM_VENDA (
    id_item_venda INTEGER PRIMARY KEY,
    id_venda INTEGER NOT NULL,
    id_equipamento INTEGER NOT NULL UNIQUE,
    valor NUMERIC NOT NULL,
    FOREIGN KEY (id_venda) REFERENCES VENDA(id_venda)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (id_equipamento) REFERENCES EQUIPAMENTO(id_equipamento)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS NOTA_FISCAL_SIMULADA (
    id_nota INTEGER PRIMARY KEY,
    id_venda INTEGER NOT NULL UNIQUE,
    numero TEXT NOT NULL UNIQUE,
    data_emissao TEXT NOT NULL,
    FOREIGN KEY (id_venda) REFERENCES VENDA(id_venda)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS DOACAO (
    id_doacao INTEGER PRIMARY KEY,
    id_equipamento INTEGER NOT NULL UNIQUE,
    id_organizacao_ong INTEGER NOT NULL,
    data_doacao TEXT NOT NULL,
    FOREIGN KEY (id_equipamento) REFERENCES EQUIPAMENTO(id_equipamento)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (id_organizacao_ong) REFERENCES ORGANIZACAO(id_organizacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

-- Solicitação de doação da ONG (DP-69 a DP-77, aprovada pelo usuário em 2026-10-31).
-- decidido_por guarda o nome copiado de quem decidiu, sem chave estrangeira para USUARIO (DP-66, DP-77).
CREATE TABLE IF NOT EXISTS SOLICITACAO_DOACAO (
    id_solicitacao_doacao INTEGER PRIMARY KEY,
    id_organizacao_ong INTEGER NOT NULL,
    data_solicitacao TEXT NOT NULL,
    situacao TEXT NOT NULL CHECK (situacao IN ('Pendente', 'Aprovada', 'Recusada', 'Cancelada')),
    motivo_recusa TEXT NULL,
    decidido_por TEXT NULL,
    data_decisao TEXT NULL,
    FOREIGN KEY (id_organizacao_ong) REFERENCES ORGANIZACAO(id_organizacao)
        ON DELETE RESTRICT ON UPDATE CASCADE
);

CREATE TABLE IF NOT EXISTS ITEM_SOLICITACAO_DOACAO (
    id_item_solicitacao_doacao INTEGER PRIMARY KEY,
    id_solicitacao_doacao INTEGER NOT NULL,
    id_equipamento INTEGER NOT NULL,
    FOREIGN KEY (id_solicitacao_doacao) REFERENCES SOLICITACAO_DOACAO(id_solicitacao_doacao)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    FOREIGN KEY (id_equipamento) REFERENCES EQUIPAMENTO(id_equipamento)
        ON DELETE RESTRICT ON UPDATE CASCADE,
    UNIQUE (id_solicitacao_doacao, id_equipamento)
);

COMMIT;
