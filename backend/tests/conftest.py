"""Fixtures do Modulo 0 (UC04, UC28). Banco temporario: nunca usa backend/leaf_ti.db (RNF03)."""
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

SEGREDO_TESTE = "segredo-somente-de-teste-com-mais-de-32-bytes"
SENHA = "SenhaDeTeste123"

# chave: (perfil, nome da organizacao ou None, situacao, e-mail)
USUARIOS = {
    "admin": ("Administrador", None, None, "admin@teste.com"),
    "func": ("Funcionário", None, None, "func@teste.com"),
    "empresa": ("Cliente Empresa", "Empresa Cliente", "Ativa", "empresa@teste.com"),
    "ong": ("Cliente ONG", "ONG Cliente", "Ativa", "ong@teste.com"),
    "doadora": ("Empresa Doadora", "Doadora SA", "Ativa", "doadora@teste.com"),
    "inativo": ("Cliente Empresa", "Empresa Inativa", "Inativa", "inativo@teste.com"),
}


@pytest.fixture(scope="session")
def hash_senha():
    from app.seguranca import gerar_hash_senha
    return gerar_hash_senha(SENHA)


@pytest.fixture()
def ambiente(tmp_path, monkeypatch):
    caminho = tmp_path / "teste.db"
    monkeypatch.setenv("LEAF_DB_PATH", str(caminho))
    monkeypatch.setenv("LEAF_JWT_SECRET", SEGREDO_TESTE)
    monkeypatch.setenv("LEAF_AMBIENTE", "desenvolvimento")
    monkeypatch.setenv("LEAF_IMAGENS_DIR", str(tmp_path / "imagens"))  # DP-86: nunca a pasta real
    monkeypatch.delenv("LEAF_TOKEN_MINUTOS", raising=False)
    return caminho


@pytest.fixture()
def cliente(ambiente, hash_senha):
    """TestClient com banco temporario populado: um usuario por perfil + um de organizacao inativa."""
    from app.main import criar_app
    app = criar_app()
    with TestClient(app) as c:
        con = sqlite3.connect(ambiente)
        con.execute("PRAGMA foreign_keys = ON")
        for i, (chave, (perfil, org, sit, email)) in enumerate(USUARIOS.items(), start=1):
            id_org = None
            if org:
                cur = con.execute(
                    "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao)"
                    " VALUES (?,?,?,?,?,?,?)",
                    (f"{i:014d}", org, perfil, "11999999999", f"{chave}@org.com", "Rua X, 1", sit),
                )
                id_org = cur.lastrowid
            con.execute(
                "INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (?,?,?,?,?)",
                (id_org, email, perfil, hash_senha, f"Nome {chave}"),
            )
        con.commit()
        con.close()
        c.caminho_banco = ambiente
        yield c


def fazer_login(cliente, chave="admin", senha=SENHA):
    return cliente.post("/api/v1/auth/login", json={"email": USUARIOS[chave][3], "senha": senha})


@pytest.fixture()
def token_de():
    def _t(cliente, chave):
        r = fazer_login(cliente, chave)
        assert r.status_code == 200, r.text
        return r.json()["access_token"]
    return _t
