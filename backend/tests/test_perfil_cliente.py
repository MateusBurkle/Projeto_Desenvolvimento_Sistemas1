"""Cliente atualiza a própria conta e a própria organização (UC02, UC03, UC01, UC06; RN02, RN04, RN09; DP-93 a DP-99)."""
import sqlite3

import pytest

from tests.conftest import SENHA, fazer_login

CLIENTES = ["empresa", "ong", "doadora"]
OUTROS = ["admin", "func"]
API = "/api/v1"


def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def hd(cliente, token_de):
    return lambda chave: _h(token_de(cliente, chave))


def _sql(cliente, comando, params=()):
    con = sqlite3.connect(cliente.caminho_banco)
    con.row_factory = sqlite3.Row
    try:
        cur = con.execute(comando, params)
        con.commit()
        return cur.fetchall()
    finally:
        con.close()


# ---------------- PATCH /usuarios/me (UC02, UC03, DP-95)

@pytest.mark.parametrize("chave", CLIENTES)
def test_patch_me_ok_e_perfil_organizacao_intactos(cliente, hd, chave):
    r = cliente.patch(f"{API}/usuarios/me", headers=hd(chave),
                      json={"nome": "  Novo Nome ", "email": " NOVO.%s@X.com " % chave,
                            "perfil": "Administrador", "id_organizacao": 999})
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["nome"] == "Novo Nome" and d["email"] == f"novo.{chave}@x.com"
    assert d["perfil"] != "Administrador" and d["id_organizacao"] != 999
    assert "senha" not in r.text and "senha_hash" not in r.text


@pytest.mark.parametrize("corpo", [{"nome": "Só Nome"}, {"email": "so.email@x.com"}])
def test_patch_me_um_campo_basta(cliente, hd, corpo):
    assert cliente.patch(f"{API}/usuarios/me", headers=hd("empresa"), json=corpo).status_code == 200


@pytest.mark.parametrize("corpo", [{}, {"nome": ""}, {"nome": "x" * 121}, {"email": "invalido"}, {"foo": 1}])
def test_patch_me_invalido_400(cliente, hd, corpo):
    r = cliente.patch(f"{API}/usuarios/me", headers=hd("empresa"), json=corpo)
    assert r.status_code == 400, r.text


def test_patch_me_email_de_outra_conta_409(cliente, hd):
    r = cliente.patch(f"{API}/usuarios/me", headers=hd("empresa"), json={"email": "ONG@teste.com"})
    assert r.status_code == 409 and r.json()["codigo"] == "EMAIL_DUPLICADO"


def test_patch_me_proprio_email_aceito(cliente, hd):
    r = cliente.patch(f"{API}/usuarios/me", headers=hd("empresa"), json={"email": "Empresa@Teste.com"})
    assert r.status_code == 200 and r.json()["email"] == "empresa@teste.com"


# DP-101 a DP-104: Administrador e Funcionário também trocam a PRÓPRIA conta
@pytest.mark.parametrize("chave,perfil", [("admin", "Administrador"), ("func", "Funcionário")])
def test_admin_func_trocam_nome_email_senha(cliente, hd, chave, perfil):
    h = hd(chave)
    r = cliente.patch(f"{API}/usuarios/me", headers=h,
                      json={"nome": " Novo Nome ", "email": f"Novo.{chave}@X.com", "perfil": "Cliente ONG"})
    assert r.status_code == 200, r.text
    assert r.json()["nome"] == "Novo Nome" and r.json()["email"] == f"novo.{chave}@x.com"
    assert r.json()["perfil"] == perfil  # DP-104: perfil nunca muda
    assert _sql(cliente, "SELECT perfil FROM USUARIO WHERE email = ?", (f"novo.{chave}@x.com",))[0][0] == perfil
    # DP-102: sessão atual segue válida; e-mail antigo não loga mais
    assert fazer_login(cliente, chave).status_code == 401
    assert cliente.patch(f"{API}/usuarios/me", headers=h, json={"nome": "Outra"}).status_code == 200
    r = cliente.put(f"{API}/usuarios/me/senha", headers=h, json={"senha_nova": "OutraSenha456"})
    assert r.status_code == 204 and r.content == b""
    login = lambda s: cliente.post(f"{API}/auth/login", json={"email": f"novo.{chave}@x.com", "senha": s})
    assert login("OutraSenha456").status_code == 200
    assert login(SENHA).status_code == 401


@pytest.mark.parametrize("chave", OUTROS)
def test_admin_func_email_duplicado_409_e_corpo_vazio_400(cliente, hd, chave):
    r = cliente.patch(f"{API}/usuarios/me", headers=hd(chave), json={"email": "EMPRESA@teste.com"})
    assert r.status_code == 409 and r.json()["codigo"] == "EMAIL_DUPLICADO"
    assert cliente.patch(f"{API}/usuarios/me", headers=hd(chave), json={}).status_code == 400
    r = cliente.put(f"{API}/usuarios/me/senha", headers=hd(chave), json={"senha_nova": SENHA})
    assert r.status_code == 422 and r.json()["codigo"] == "SENHA_IGUAL_ATUAL"
    assert cliente.put(f"{API}/usuarios/me/senha", headers=hd(chave), json={"senha_nova": "curta"}).status_code == 400


def test_patch_me_visitante_401(cliente):
    assert cliente.patch(f"{API}/usuarios/me", json={"nome": "X"}).status_code == 401


# ---------------- PUT /usuarios/me/senha (RNF03, DP-96, DP-97)

@pytest.mark.parametrize("chave", CLIENTES)
def test_senha_nova_ok_login_novo_sim_antigo_nao(cliente, hd, chave):
    r = cliente.put(f"{API}/usuarios/me/senha", headers=hd(chave), json={"senha_nova": "OutraSenha456"})
    assert r.status_code == 204 and r.content == b""
    assert fazer_login(cliente, chave, "OutraSenha456").status_code == 200
    assert fazer_login(cliente, chave, SENHA).status_code == 401
    hash_ = _sql(cliente, "SELECT senha_hash FROM USUARIO WHERE email = ?", (f"{chave}@teste.com",))[0][0]
    assert hash_.startswith("$2") and "OutraSenha456" not in hash_


@pytest.mark.parametrize("senha", ["curta12", "x" * 129, ""])
def test_senha_fora_do_tamanho_400(cliente, hd, senha):
    assert cliente.put(f"{API}/usuarios/me/senha", headers=hd("ong"), json={"senha_nova": senha}).status_code == 400


def test_senha_igual_atual_422(cliente, hd):
    r = cliente.put(f"{API}/usuarios/me/senha", headers=hd("ong"), json={"senha_nova": SENHA})
    assert r.status_code == 422 and "SENHA_IGUAL_ATUAL" in r.text
    assert SENHA not in r.text
    assert fazer_login(cliente, "ong").status_code == 200


def test_senha_visitante_401(cliente):
    assert cliente.put(f"{API}/usuarios/me/senha", json={"senha_nova": "OutraSenha456"}).status_code == 401


# ---------------- GET/PATCH /organizacao (UC01, UC06, DP-93, DP-94, DP-98)

@pytest.mark.parametrize("chave,nome", [("empresa", "Empresa Cliente"), ("ong", "ONG Cliente"), ("doadora", "Doadora SA")])
def test_get_organizacao_propria(cliente, hd, chave, nome):
    r = cliente.get(f"{API}/organizacao", headers=hd(chave))
    assert r.status_code == 200 and r.json()["nome_razao_social"] == nome


@pytest.mark.parametrize("chave", CLIENTES)
def test_patch_organizacao_ok_cnpj_tipo_situacao_intactos(cliente, hd, chave):
    antes = cliente.get(f"{API}/organizacao", headers=hd(chave)).json()
    r = cliente.patch(f"{API}/organizacao", headers=hd(chave), json={
        "nome_razao_social": " Nome Novo ", "telefone": "(11) 98888-7777", "email": "NOVO@org.com",
        "endereco": "Rua Nova, 2", "cnpj": "99999999999999", "tipo": "Cliente ONG", "situacao": "Inativa",
        "id_organizacao": 1})
    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["nome_razao_social"], d["telefone"], d["email"], d["endereco"]) == (
        "Nome Novo", "11988887777", "novo@org.com", "Rua Nova, 2")
    assert d["id_organizacao"] == antes["id_organizacao"]
    for campo in ("cnpj", "tipo", "situacao", "possui_parceria"):
        assert d[campo] == antes[campo]


def test_patch_organizacao_nao_altera_outra(cliente, hd):
    outras = _sql(cliente, "SELECT id_organizacao, nome_razao_social FROM ORGANIZACAO WHERE nome_razao_social <> 'Empresa Cliente'")
    cliente.patch(f"{API}/organizacao", headers=hd("empresa"), json={"nome_razao_social": "Mudou", "id_organizacao": outras[0][0]})
    depois = _sql(cliente, "SELECT id_organizacao, nome_razao_social FROM ORGANIZACAO WHERE nome_razao_social <> 'Mudou'")
    assert [tuple(x) for x in outras] == [tuple(x) for x in depois]


def test_patch_organizacao_nome_nao_e_unico(cliente, hd):
    r = cliente.patch(f"{API}/organizacao", headers=hd("empresa"), json={"nome_razao_social": "ONG Cliente"})
    assert r.status_code == 200


@pytest.mark.parametrize("corpo", [{}, {"cnpj": "1"}, {"telefone": "123"}, {"email": "x"}, {"endereco": " "},
                                    {"nome_razao_social": "x" * 151}])
def test_patch_organizacao_invalido_400(cliente, hd, corpo):
    assert cliente.patch(f"{API}/organizacao", headers=hd("empresa"), json=corpo).status_code == 400


@pytest.mark.parametrize("chave", OUTROS)
def test_organizacao_outros_perfis_403(cliente, hd, chave):
    assert cliente.get(f"{API}/organizacao", headers=hd(chave)).status_code == 403
    assert cliente.patch(f"{API}/organizacao", headers=hd(chave), json={"endereco": "X"}).status_code == 403


def test_organizacao_visitante_401(cliente):
    assert cliente.get(f"{API}/organizacao").status_code == 401
    assert cliente.patch(f"{API}/organizacao", json={"endereco": "X"}).status_code == 401


def test_cliente_continua_403_em_rotas_com_id(cliente, hd):
    h = hd("empresa")
    assert cliente.put(f"{API}/organizacoes/2", headers=h, json={}).status_code == 403
    assert cliente.patch(f"{API}/organizacoes/2/contato", headers=h, json={}).status_code == 403


def test_nome_novo_aparece_em_vendas(cliente, hd):
    id_org = _sql(cliente, "SELECT id_organizacao FROM ORGANIZACAO WHERE nome_razao_social = 'Empresa Cliente'")[0][0]
    _sql(cliente, "INSERT INTO VENDA (id_organizacao_cliente, data_venda, situacao, forma_pagamento) "
                  "VALUES (?, '2026-01-01', 'Pendente', 'PIX')", (id_org,))
    cliente.patch(f"{API}/organizacao", headers=hd("empresa"), json={"nome_razao_social": "Nome Atual Ltda"})
    r = cliente.get(f"{API}/vendas", headers=hd("admin"))
    assert r.status_code == 200 and r.json()["items"][0]["nome_organizacao"] == "Nome Atual Ltda"
