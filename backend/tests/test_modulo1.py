"""Testes da API do Modulo 1 (Acesso e usuarios): UC02, UC03, UC26, UC27.
Requisitos: RF01, RF02, RF04, RF09; RN01, RN02, RN03, RN04, RN09; RNF03, RNF04, RNF05.
Contrato: contratos/modulo-1.yaml v1.0.0. Contas e senhas ficticias (conftest); nunca a conta real."""
import sqlite3
import sys

import bcrypt
import pytest

from tests.conftest import SENHA, USUARIOS, fazer_login

U = "/api/v1/usuarios"
ORG = "/api/v1/organizacao/usuarios"
PERFIS = ["Administrador", "Funcionário", "Cliente Empresa", "Cliente ONG", "Empresa Doadora"]
CHAVES = ["admin", "func", "empresa", "ong", "doadora"]
# ids semeados pelo conftest: usuarios 1..6 (admin, func, empresa, ong, doadora, inativo); orgs 1..4
ID_ORG = {"Cliente Empresa": 1, "Cliente ONG": 2, "Empresa Doadora": 3}
ID_ORG_INATIVA = 4


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _sql(cliente, comando, params=()):
    con = sqlite3.connect(cliente.caminho_banco)
    cur = con.execute(comando, params)
    con.commit()
    ultimo = cur.lastrowid
    con.close()
    return ultimo


def _consulta(cliente, comando, params=()):
    con = sqlite3.connect(cliente.caminho_banco)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(comando, params).fetchall()
    finally:
        con.close()


def _qtd_usuarios(cliente):
    return _consulta(cliente, "SELECT COUNT(*) AS n FROM USUARIO")[0]["n"]


def _tudo(cliente):
    return [tuple(r) for r in _consulta(cliente, "SELECT * FROM USUARIO ORDER BY id_usuario")]


def _nova_org(cliente, tipo, situacao="Ativa", nome=None):
    n = _consulta(cliente, "SELECT COUNT(*) AS n FROM ORGANIZACAO")[0]["n"] + 100
    return _sql(cliente,
                "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao)"
                " VALUES (?,?,?,?,?,?,?)",
                (f"{n:014d}", nome or f"Org {n}", tipo, "11999999999", f"o{n}@org.com", "Rua Y, 2", situacao))


def _corpo(**kw):
    base = {"nome": "Pessoa Teste", "email": "novo@teste.com", "senha": "SenhaNova123", "perfil": "Funcionário"}
    base.update(kw)
    return base


def _corpo_org(perfil, **kw):
    c = _corpo(perfil=perfil, **kw)
    if perfil in ID_ORG:
        c.setdefault("id_organizacao", ID_ORG[perfil])
    return c


def _erro(r, status, codigo):
    assert r.status_code == status, r.text
    corpo = r.json()
    assert set(corpo) == {"codigo", "mensagem", "campos"}
    assert corpo["codigo"] == codigo
    assert corpo["mensagem"] and isinstance(corpo["campos"], dict)
    return corpo


@pytest.fixture()
def adm(cliente, token_de):
    return _h(token_de(cliente, "admin"))


@pytest.fixture()
def login_com(cliente):
    def _l(email, senha):
        return cliente.post("/api/v1/auth/login", json={"email": email, "senha": senha})
    return _l


def _criar(cliente, adm, **kw):
    r = cliente.post(U, json=_corpo(**kw), headers=adm)
    assert r.status_code == 201, r.text
    return r.json()


def _put(cliente, adm, id_, **kw):
    base = {"nome": "Func", "email": "func@teste.com", "perfil": "Funcionário"}
    base.update(kw)
    return cliente.put(f"{U}/{id_}", json=base, headers=adm)


# ======================================================================= permissoes por rota
ROTAS = [
    ("GET", "/usuarios/perfis-atribuiveis", None, ["admin"]),
    ("GET", "/usuarios/opcoes-organizacao", None, ["admin"]),
    ("GET", "/usuarios", None, ["admin"]),
    ("POST", "/usuarios", "criar", ["admin"]),
    ("GET", "/usuarios/99999", None, ["admin"]),
    ("PUT", "/usuarios/99999", "alterar", ["admin"]),
    ("DELETE", "/usuarios/99999", None, ["admin"]),
    ("GET", "/organizacao/usuarios", None, ["empresa", "ong"]),
    ("POST", "/organizacao/usuarios", "org", ["empresa", "ong"]),
]


def _corpo_da_rota(tipo, chave):
    if tipo == "criar":
        return _corpo(email=f"perm-{chave}@teste.com")
    if tipo == "alterar":
        return {"nome": "X", "email": f"perm-{chave}@teste.com", "perfil": "Funcionário"}
    if tipo == "org":
        return {"nome": "X", "email": f"perm-{chave}@teste.com", "senha": "SenhaNova123"}
    return None


@pytest.mark.parametrize("metodo,caminho,tipo,permitidos", ROTAS)
def test_sem_token_retorna_401(cliente, metodo, caminho, tipo, permitidos):
    # RNF05, contrato 401 NAO_AUTENTICADO (todas as rotas)
    r = cliente.request(metodo, "/api/v1" + caminho, json=_corpo_da_rota(tipo, "x"))
    _erro(r, 401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("chave", CHAVES)
@pytest.mark.parametrize("metodo,caminho,tipo,permitidos", ROTAS)
def test_matriz_de_permissoes_por_perfil(cliente, token_de, chave, metodo, caminho, tipo, permitidos):
    # RN01, RN02, RN03, RN04, RNF05, DP-18: x-permissoes do contrato (5 perfis x 9 rotas)
    r = cliente.request(metodo, "/api/v1" + caminho, json=_corpo_da_rota(tipo, chave),
                        headers=_h(token_de(cliente, chave)))
    if chave in permitidos:
        assert r.status_code not in (401, 403), r.text
    else:
        _erro(r, 403, "SEM_PERMISSAO")


@pytest.mark.parametrize("chave", ["func", "doadora", "empresa", "ong"])
def test_nao_administrador_nao_cria_usuario_em_usuarios(cliente, token_de, chave):
    # RN02, RN03: nada e gravado
    antes = _qtd_usuarios(cliente)
    r = cliente.post(U, json=_corpo(), headers=_h(token_de(cliente, chave)))
    _erro(r, 403, "SEM_PERMISSAO")
    assert _qtd_usuarios(cliente) == antes


@pytest.mark.parametrize("chave", ["admin", "func", "doadora"])
def test_nao_cliente_nao_acessa_organizacao_usuarios(cliente, token_de, chave):
    # RN02, RN04, DP-18
    t = _h(token_de(cliente, chave))
    antes = _qtd_usuarios(cliente)
    _erro(cliente.get(ORG, headers=t), 403, "SEM_PERMISSAO")
    _erro(cliente.post(ORG, json={"nome": "A", "email": "a@teste.com", "senha": "SenhaNova123"}, headers=t),
          403, "SEM_PERMISSAO")
    assert _qtd_usuarios(cliente) == antes


# ======================================================================= UC02 criacao
@pytest.mark.parametrize("perfil", PERFIS)
def test_uc02_criar_usuario_por_perfil(cliente, adm, perfil):
    # UC02 fluxo principal, UC27, RN02, RF02
    r = cliente.post(U, json=_corpo_org(perfil), headers=adm)
    assert r.status_code == 201, r.text
    u = r.json()
    assert u["perfil"] == perfil and u["nome"] == "Pessoa Teste" and u["email"] == "novo@teste.com"
    assert u["id_organizacao"] == ID_ORG.get(perfil)
    assert (u["nome_organizacao"] is None) == (perfil not in ID_ORG)
    assert isinstance(u["funcionalidades"], list) and u["funcionalidades"]  # UC02 passo 6
    assert set(u) == {"id_usuario", "nome", "email", "perfil", "id_organizacao", "nome_organizacao",
                      "funcionalidades"}


@pytest.mark.parametrize("perfil", PERFIS)
def test_uc02_conta_criada_autentica_com_o_perfil_e_funcionalidades(cliente, adm, login_com, perfil):
    # UC02 passo 6, RN01: funcionalidades da resposta = as do login do mesmo perfil
    criada = cliente.post(U, json=_corpo_org(perfil), headers=adm).json()
    r = login_com("novo@teste.com", "SenhaNova123")
    assert r.status_code == 200
    assert r.json()["usuario"]["perfil"] == perfil
    assert r.json()["usuario"]["funcionalidades"] == criada["funcionalidades"]


def test_uc26_email_e_normalizado_na_criacao(cliente, adm):
    # UC26 passo 2 (strip + minusculas)
    u = _criar(cliente, adm, email="  Maria.Souza@EMPRESA.Com  ")
    assert u["email"] == "maria.souza@empresa.com"
    assert _consulta(cliente, "SELECT email FROM USUARIO WHERE id_usuario=?", (u["id_usuario"],))[0]["email"] \
        == "maria.souza@empresa.com"


def test_nome_e_aparado(cliente, adm):
    # UC02 FE1 (nome sem espacos nas pontas)
    assert _criar(cliente, adm, nome="  Ana  ")["nome"] == "Ana"


@pytest.mark.parametrize("tamanho,ok", [(7, False), (8, True), (128, True), (129, False)])
def test_senha_8_a_128_caracteres(cliente, adm, tamanho, ok):
    # RN02 M1, RNF04, DP-13: limites
    antes = _qtd_usuarios(cliente)
    r = cliente.post(U, json=_corpo(senha="a" * tamanho), headers=adm)
    if ok:
        assert r.status_code == 201
    else:
        c = _erro(r, 400, "DADOS_INVALIDOS")
        assert "senha" in c["campos"]
        assert "a" * tamanho not in r.text  # nao ecoa a senha
        assert _qtd_usuarios(cliente) == antes


@pytest.mark.parametrize("nome,ok", [("", False), ("   ", False), ("A", True), ("n" * 120, True), ("n" * 121, False)])
def test_nome_de_1_a_120_caracteres(cliente, adm, nome, ok):
    # UC02 FE1, RNF04
    r = cliente.post(U, json=_corpo(nome=nome), headers=adm)
    if ok:
        assert r.status_code == 201
    else:
        assert "nome" in _erro(r, 400, "DADOS_INVALIDOS")["campos"]


@pytest.mark.parametrize("email", ["", "semarroba", "a@b", "a b@c.com", "x" * 250 + "@a.com"])
def test_email_invalido_400(cliente, adm, email):
    # UC26 FE1, UC02 FE1, RNF04
    r = cliente.post(U, json=_corpo(email=email), headers=adm)
    assert "email" in _erro(r, 400, "DADOS_INVALIDOS")["campos"]


@pytest.mark.parametrize("campo", ["nome", "email", "senha", "perfil"])
def test_campo_obrigatorio_ausente_400(cliente, adm, campo):
    # UC02 FE1, RNF04
    corpo = _corpo()
    del corpo[campo]
    assert campo in _erro(cliente.post(U, json=corpo, headers=adm), 400, "DADOS_INVALIDOS")["campos"]


@pytest.mark.parametrize("perfil", ["Gerente", "", "administrador", None])
def test_perfil_invalido_400_com_campo_perfil(cliente, adm, perfil):
    # UC27 FE1, UC02 FE3: nenhuma conta criada
    antes = _qtd_usuarios(cliente)
    r = cliente.post(U, json=_corpo(perfil=perfil), headers=adm)
    assert "perfil" in _erro(r, 400, "DADOS_INVALIDOS")["campos"]
    assert _qtd_usuarios(cliente) == antes


def test_corpo_nao_json_ou_vazio_400(cliente, adm):
    # RNF04
    _erro(cliente.post(U, content="{", headers={**adm, "Content-Type": "application/json"}), 400, "DADOS_INVALIDOS")
    _erro(cliente.post(U, json={}, headers=adm), 400, "DADOS_INVALIDOS")


def test_campos_extras_sao_ignorados(cliente, adm):
    # contrato, esclarecimento (4)
    r = cliente.post(U, json=_corpo(campo_inventado="x", senha_hash="y"), headers=adm)
    assert r.status_code == 201
    h = _consulta(cliente, "SELECT senha_hash FROM USUARIO WHERE email='novo@teste.com'")[0]["senha_hash"]
    assert h != "y"


@pytest.mark.parametrize("rota", ["criar", "obter", "listar", "alterar", "org"])
def test_resposta_nunca_traz_senha_nem_hash(cliente, adm, token_de, rota):
    # RNF03
    if rota == "criar":
        r = cliente.post(U, json=_corpo(), headers=adm)
    elif rota == "obter":
        r = cliente.get(f"{U}/1", headers=adm)
    elif rota == "listar":
        r = cliente.get(U, headers=adm)
    elif rota == "alterar":
        r = _put(cliente, adm, 2, senha="OutraSenha123")
    else:
        r = cliente.post(ORG, json={"nome": "A", "email": "a@teste.com", "senha": "SenhaNova123"},
                         headers=_h(token_de(cliente, "empresa")))
    assert r.status_code in (200, 201)
    texto = r.text.lower()
    assert "senha" not in texto and "hash" not in texto and "$2" not in texto


def test_senha_gravada_como_hash_bcrypt(cliente, adm):
    # RNF03
    u = _criar(cliente, adm, senha="SenhaSecreta99")
    h = _consulta(cliente, "SELECT senha_hash FROM USUARIO WHERE id_usuario=?", (u["id_usuario"],))[0]["senha_hash"]
    assert h.startswith(("$2a$", "$2b$", "$2y$")) and "SenhaSecreta99" not in h
    assert bcrypt.checkpw(b"SenhaSecreta99", h.encode())


# ======================================================================= UC26 duplicidade
def test_uc26_email_duplicado_409_sem_criar(cliente, adm):
    # UC26 FE1, UC02 FE1
    antes = _qtd_usuarios(cliente)
    c = _erro(cliente.post(U, json=_corpo(email="func@teste.com"), headers=adm), 409, "EMAIL_DUPLICADO")
    assert c["campos"] == {"email": "duplicado"}
    assert _qtd_usuarios(cliente) == antes


@pytest.mark.parametrize("email", ["FUNC@TESTE.COM", "  Func@Teste.com ", "fUnC@teste.COM"])
def test_uc26_duplicidade_sem_diferenciar_caixa_na_criacao(cliente, adm, email):
    # UC26 passo 2
    _erro(cliente.post(U, json=_corpo(email=email), headers=adm), 409, "EMAIL_DUPLICADO")


def test_uc26_duplicidade_com_email_legado_em_maiusculas_no_banco(cliente, adm):
    # UC26: o UNIQUE do SQLite diferencia caixa; a checagem do service nao
    _sql(cliente, "INSERT INTO USUARIO (id_organizacao,email,perfil,senha_hash,nome) VALUES (NULL,?,?,?,?)",
         ("Legado@Teste.com", "Funcionário", "x", "Legado"))
    _erro(cliente.post(U, json=_corpo(email="legado@teste.com"), headers=adm), 409, "EMAIL_DUPLICADO")


@pytest.mark.parametrize("email", ["admin@teste.com", "ADMIN@teste.com", " Admin@Teste.com "])
def test_uc26_alteracao_para_email_de_outra_conta_409_sem_diferenciar_caixa(cliente, adm, email):
    # UC26 (alteracao), UC02 FA2
    antes = _tudo(cliente)
    _erro(_put(cliente, adm, 2, email=email), 409, "EMAIL_DUPLICADO")
    assert _tudo(cliente) == antes


@pytest.mark.parametrize("email", ["func@teste.com", "FUNC@Teste.com"])
def test_uc26_propria_conta_nao_conta_como_duplicada(cliente, adm, email):
    # UC02 FA2, UC26 passo 2
    r = _put(cliente, adm, 2, nome="Func Novo", email=email)
    assert r.status_code == 200
    assert r.json()["email"] == "func@teste.com" and r.json()["nome"] == "Func Novo"


# ======================================================================= UC27 vinculo
@pytest.mark.parametrize("perfil", ["Administrador", "Funcionário"])
def test_uc27_perfil_interno_sem_org_ok_e_com_org_vinculo_invalido(cliente, adm, perfil):
    # UC27 passo 3, DP-14, esclarecimento (2)
    assert cliente.post(U, json=_corpo(perfil=perfil), headers=adm).status_code == 201
    antes = _qtd_usuarios(cliente)
    r = cliente.post(U, json=_corpo(perfil=perfil, email="b@teste.com", id_organizacao=1), headers=adm)
    assert "id_organizacao" in _erro(r, 422, "VINCULO_INVALIDO")["campos"]
    assert _qtd_usuarios(cliente) == antes


@pytest.mark.parametrize("perfil", ["Cliente Empresa", "Cliente ONG", "Empresa Doadora"])
def test_uc27_cliente_e_doadora_sem_organizacao_vinculo_invalido(cliente, adm, perfil):
    # UC27 passo 3, esclarecimento (1)
    _erro(cliente.post(U, json=_corpo(perfil=perfil), headers=adm), 422, "VINCULO_INVALIDO")
    _erro(cliente.post(U, json=_corpo(perfil=perfil, id_organizacao=None), headers=adm), 422, "VINCULO_INVALIDO")


@pytest.mark.parametrize("perfil", ["Cliente Empresa", "Cliente ONG", "Empresa Doadora"])
def test_uc27_organizacao_de_tipo_errado_vinculo_invalido(cliente, adm, perfil):
    # UC27 passo 3
    errada = ID_ORG[next(p for p in ID_ORG if p != perfil)]
    antes = _qtd_usuarios(cliente)
    _erro(cliente.post(U, json=_corpo(perfil=perfil, id_organizacao=errada), headers=adm), 422, "VINCULO_INVALIDO")
    assert _qtd_usuarios(cliente) == antes


@pytest.mark.parametrize("perfil", ["Cliente Empresa", "Cliente ONG", "Empresa Doadora"])
@pytest.mark.parametrize("org", [99999, ID_ORG_INATIVA])
def test_uc02_fe2_organizacao_inexistente_ou_inativa(cliente, adm, perfil, org):
    # UC02 FE2, RN06, RN09 (a org 4 e inativa e do tipo Cliente Empresa)
    antes = _qtd_usuarios(cliente)
    _erro(cliente.post(U, json=_corpo(perfil=perfil, id_organizacao=org), headers=adm), 422, "ORGANIZACAO_INVALIDA")
    assert _qtd_usuarios(cliente) == antes


def test_ordem_dos_dois_422_organizacao_antes_do_tipo(cliente, adm):
    # contrato, esclarecimento (1): ORGANIZACAO_INVALIDA e checada ANTES do tipo
    inativa_outro_tipo = _nova_org(cliente, "Cliente ONG", "Inativa")
    _erro(cliente.post(U, json=_corpo(perfil="Cliente Empresa", id_organizacao=inativa_outro_tipo), headers=adm),
          422, "ORGANIZACAO_INVALIDA")
    ativa_outro_tipo = _nova_org(cliente, "Cliente ONG", "Ativa")
    _erro(cliente.post(U, json=_corpo(perfil="Cliente Empresa", id_organizacao=ativa_outro_tipo), headers=adm),
          422, "VINCULO_INVALIDO")


def test_ordem_409_antes_de_422_na_criacao(cliente, adm):
    # contrato POST: 400 -> UC26 (409) -> UC27 (422)
    _erro(cliente.post(U, json=_corpo(email="func@teste.com", perfil="Cliente Empresa"), headers=adm),
          409, "EMAIL_DUPLICADO")


def test_ordem_400_antes_de_409(cliente, adm):
    # contrato POST: 400 antes de 409
    _erro(cliente.post(U, json=_corpo(email="func@teste.com", senha="curta"), headers=adm), 400, "DADOS_INVALIDOS")


def test_perfis_atribuiveis_devolve_os_cinco_perfis(cliente, adm):
    # UC27 passo 1
    r = cliente.get(f"{U}/perfis-atribuiveis", headers=adm)
    assert r.status_code == 200
    assert r.json() == [
        {"perfil": "Administrador", "exige_organizacao": False, "tipo_organizacao": None},
        {"perfil": "Funcionário", "exige_organizacao": False, "tipo_organizacao": None},
        {"perfil": "Cliente Empresa", "exige_organizacao": True, "tipo_organizacao": "Cliente Empresa"},
        {"perfil": "Cliente ONG", "exige_organizacao": True, "tipo_organizacao": "Cliente ONG"},
        {"perfil": "Empresa Doadora", "exige_organizacao": True, "tipo_organizacao": "Empresa Doadora"},
    ]


def test_opcoes_organizacao_so_ativas(cliente, adm):
    # UC02 passo 2, DP-15, RN06
    r = cliente.get(f"{U}/opcoes-organizacao", headers=adm)
    assert r.status_code == 200
    itens = r.json()
    assert {i["id_organizacao"] for i in itens} == {1, 2, 3}  # a 4 e inativa
    for i in itens:
        assert set(i) == {"id_organizacao", "nome_razao_social", "tipo"}


@pytest.mark.parametrize("tipo,esperado", [("Cliente Empresa", {1}), ("Cliente ONG", {2}), ("Empresa Doadora", {3})])
def test_opcoes_organizacao_filtro_tipo(cliente, adm, tipo, esperado):
    # UC02 passo 2 (filtro tipo); a inativa (Cliente Empresa) nunca aparece
    r = cliente.get(f"{U}/opcoes-organizacao", params={"tipo": tipo}, headers=adm)
    assert {i["id_organizacao"] for i in r.json()} == esperado


def test_opcoes_organizacao_tipo_invalido_400(cliente, adm):
    # RNF04
    _erro(cliente.get(f"{U}/opcoes-organizacao", params={"tipo": "Outro"}, headers=adm), 400, "DADOS_INVALIDOS")


# ======================================================================= GET / listagem
def test_obter_usuario_e_404(cliente, adm):
    # UC02 FA1
    r = cliente.get(f"{U}/3", headers=adm)
    assert r.status_code == 200
    assert r.json()["perfil"] == "Cliente Empresa" and r.json()["nome_organizacao"] == "Empresa Cliente"
    _erro(cliente.get(f"{U}/99999", headers=adm), 404, "NAO_ENCONTRADO")


def test_listagem_padrao_e_paginacao(cliente, adm):
    # UC02 FA4, convencoes (items, total, page, size)
    r = cliente.get(U, headers=adm).json()
    assert set(r) == {"items", "total", "page", "size"}
    assert r["total"] == 6 and r["page"] == 1 and r["size"] == 20 and len(r["items"]) == 6
    nomes = [i["nome"].lower() for i in r["items"]]
    assert nomes == sorted(nomes)  # ordenacao por nome
    p2 = cliente.get(U, params={"page": 2, "size": 4}, headers=adm).json()
    p1 = cliente.get(U, params={"page": 1, "size": 4}, headers=adm).json()
    assert p2["page"] == 2 and p2["size"] == 4 and len(p2["items"]) == 2 and p2["total"] == 6
    assert len(p1["items"]) == 4
    assert {i["id_usuario"] for i in p1["items"]}.isdisjoint({i["id_usuario"] for i in p2["items"]})
    assert cliente.get(U, params={"page": 99}, headers=adm).json()["items"] == []


@pytest.mark.parametrize("params", [{"size": 101}, {"size": 0}, {"page": 0}, {"size": "x"}, {"perfil": "Gerente"},
                                    {"q": "a" * 121}])
def test_listagem_parametros_invalidos_400(cliente, adm, params):
    # contrato GET /usuarios 400 (size max. 100)
    _erro(cliente.get(U, params=params, headers=adm), 400, "DADOS_INVALIDOS")


def test_listagem_size_100_aceito(cliente, adm):
    # contrato (limite)
    assert cliente.get(U, params={"size": 100}, headers=adm).status_code == 200


def test_listagem_filtro_perfil(cliente, adm):
    # UC02 FA4
    r = cliente.get(U, params={"perfil": "Cliente ONG"}, headers=adm).json()
    assert r["total"] == 1 and r["items"][0]["email"] == "ong@teste.com"


def test_listagem_filtro_organizacao(cliente, adm):
    # UC02 FA4
    r = cliente.get(U, params={"id_organizacao": 1}, headers=adm).json()
    assert [i["email"] for i in r["items"]] == ["empresa@teste.com"]


TODOS = {"admin@teste.com", "func@teste.com", "empresa@teste.com", "ong@teste.com", "doadora@teste.com",
         "inativo@teste.com"}


@pytest.mark.parametrize("q,emails", [("FUNC", {"func@teste.com"}), ("nome ong", {"ong@teste.com"}),
                                     ("@TESTE.com", TODOS), ("inexistente-xyz", set())])
def test_listagem_busca_q_em_nome_e_email_sem_diferenciar_caixa(cliente, adm, q, emails):
    # UC02 FA4
    r = cliente.get(U, params={"q": q}, headers=adm).json()
    assert {i["email"] for i in r["items"]} == emails and r["total"] == len(emails)


@pytest.mark.parametrize("q", ["%", "_"])
def test_listagem_q_trata_curingas_como_texto(cliente, adm, q):
    # UC02 FA4: % e _ nao podem virar curinga do LIKE
    assert cliente.get(U, params={"q": q}, headers=adm).json()["total"] == 0


def test_listagem_filtros_combinados(cliente, adm):
    # UC02 FA4
    assert cliente.get(U, params={"perfil": "Cliente Empresa", "id_organizacao": 2}, headers=adm).json()["total"] == 0
    assert cliente.get(U, params={"perfil": "Cliente Empresa", "id_organizacao": 1}, headers=adm).json()["total"] == 1


# ======================================================================= PUT
def test_put_altera_nome_e_email(cliente, adm):
    # UC02 FA2, UC26
    r = _put(cliente, adm, 2, nome="  Func Renomeado ", email=" NOVO.func@Teste.com ")
    assert r.status_code == 200
    assert r.json()["nome"] == "Func Renomeado" and r.json()["email"] == "novo.func@teste.com"
    assert _consulta(cliente, "SELECT email FROM USUARIO WHERE id_usuario=2")[0]["email"] == "novo.func@teste.com"


def test_put_senha_omitida_mantem_login_antigo(cliente, adm, login_com):
    # UC02 FA2 (senha opcional)
    antes = _consulta(cliente, "SELECT senha_hash FROM USUARIO WHERE id_usuario=2")[0]["senha_hash"]
    assert _put(cliente, adm, 2, nome="Outro").status_code == 200
    assert _consulta(cliente, "SELECT senha_hash FROM USUARIO WHERE id_usuario=2")[0]["senha_hash"] == antes
    assert login_com("func@teste.com", SENHA).status_code == 200


def test_put_senha_nova_vale_e_a_antiga_deixa_de_valer(cliente, adm, login_com):
    # UC02 FA2, RNF03
    assert _put(cliente, adm, 2, senha="SenhaTrocada77").status_code == 200
    assert login_com("func@teste.com", "SenhaTrocada77").status_code == 200
    assert login_com("func@teste.com", SENHA).status_code == 401
    h = _consulta(cliente, "SELECT senha_hash FROM USUARIO WHERE id_usuario=2")[0]["senha_hash"]
    assert h.startswith(("$2a$", "$2b$", "$2y$")) and "SenhaTrocada77" not in h


@pytest.mark.parametrize("senha", ["1234567", "x" * 129])
def test_put_senha_fora_do_limite_400_sem_alterar(cliente, adm, login_com, senha):
    # RN02 M1, RNF04
    antes = _tudo(cliente)
    _erro(_put(cliente, adm, 2, nome="Mudou", senha=senha), 400, "DADOS_INVALIDOS")
    assert _tudo(cliente) == antes
    assert login_com("func@teste.com", SENHA).status_code == 200


def test_put_altera_perfil_e_organizacao(cliente, adm):
    # UC02 FA1, UC27
    r = _put(cliente, adm, 2, perfil="Cliente ONG", id_organizacao=2)
    assert r.status_code == 200
    assert r.json()["perfil"] == "Cliente ONG" and r.json()["id_organizacao"] == 2
    assert r.json()["nome_organizacao"] == "ONG Cliente"
    outra = _nova_org(cliente, "Cliente Empresa", nome="Outra Empresa")
    r = _put(cliente, adm, 3, nome="Empresa", email="empresa@teste.com", perfil="Cliente Empresa",
             id_organizacao=outra)
    assert r.status_code == 200 and r.json()["nome_organizacao"] == "Outra Empresa"


def test_put_omitir_organizacao_desvincula_interno_e_invalida_cliente(cliente, adm):
    # contrato PUT: ausente = nulo; so valido para Admin/Func
    assert _put(cliente, adm, 2, perfil="Funcionário").json()["id_organizacao"] is None
    antes = _tudo(cliente)
    _erro(_put(cliente, adm, 3, email="empresa@teste.com", perfil="Cliente Empresa"), 422, "VINCULO_INVALIDO")
    assert _tudo(cliente) == antes


def test_put_perfil_muda_imediatamente_com_token_antigo(cliente, adm, token_de):
    # contrato PUT: perfil lido do banco a cada requisicao
    t = _h(token_de(cliente, "func"))
    assert cliente.get(U, headers=t).status_code == 403
    assert _put(cliente, adm, 2, perfil="Administrador").status_code == 200
    assert cliente.get(U, headers=t).status_code == 200
    assert _put(cliente, adm, 2, perfil="Funcionário").status_code == 200
    assert cliente.get(U, headers=t).status_code == 403


@pytest.mark.parametrize("corpo,status,codigo", [
    ({"nome": "N", "email": "ADMIN@teste.com", "perfil": "Funcionário"}, 409, "EMAIL_DUPLICADO"),
    ({"nome": "N", "email": "func@teste.com", "perfil": "Cliente ONG", "id_organizacao": 1}, 422, "VINCULO_INVALIDO"),
    ({"nome": "N", "email": "func@teste.com", "perfil": "Cliente ONG", "id_organizacao": ID_ORG_INATIVA}, 422,
     "ORGANIZACAO_INVALIDA"),
    ({"nome": "N", "email": "func@teste.com", "perfil": "Cliente ONG", "id_organizacao": 9999}, 422,
     "ORGANIZACAO_INVALIDA"),
    ({"nome": "N", "email": "func@teste.com", "perfil": "Cliente ONG"}, 422, "VINCULO_INVALIDO"),
    ({"nome": "N", "email": "func@teste.com", "perfil": "Funcionário", "id_organizacao": 1}, 422, "VINCULO_INVALIDO"),
    ({"nome": "N", "email": "func@teste.com", "perfil": "Gerente"}, 400, "DADOS_INVALIDOS"),
    ({"nome": "", "email": "func@teste.com", "perfil": "Funcionário"}, 400, "DADOS_INVALIDOS"),
    ({"email": "func@teste.com", "perfil": "Funcionário"}, 400, "DADOS_INVALIDOS"),
])
def test_put_erro_nao_altera_a_conta(cliente, adm, corpo, status, codigo):
    # UC02 FE1, FE2, FE3; UC26; UC27
    antes = _tudo(cliente)
    _erro(cliente.put(f"{U}/2", json=corpo, headers=adm), status, codigo)
    assert _tudo(cliente) == antes


def test_put_inexistente_404(cliente, adm):
    # contrato PUT 404
    _erro(_put(cliente, adm, 99999), 404, "NAO_ENCONTRADO")


def test_put_id_nao_inteiro_400(cliente, adm):
    # RNF04
    r = cliente.put(f"{U}/abc", json={"nome": "N", "email": "a@b.com", "perfil": "Funcionário"}, headers=adm)
    assert r.status_code == 400 and r.json()["codigo"] == "DADOS_INVALIDOS"


# ======================================================================= bloqueios (UC02 FE4)
def test_admin_nao_pode_alterar_o_proprio_perfil_mesmo_com_dois_admins(cliente, adm):
    # UC02 FE4, RN02 M1
    _criar(cliente, adm, email="adm2@teste.com", perfil="Administrador")
    antes = _tudo(cliente)
    c = _erro(_put(cliente, adm, 1, nome="Nome admin", email="admin@teste.com", perfil="Funcionário"),
              422, "ALTERACAO_BLOQUEADA")
    assert c["campos"] == {"perfil": "bloqueado"}
    assert _tudo(cliente) == antes


def test_unico_admin_nao_pode_ser_rebaixado(cliente, adm):
    # UC02 FE4, RN02 M1 (ultima conta Administrador)
    antes = _tudo(cliente)
    _erro(_put(cliente, adm, 1, nome="Nome admin", email="admin@teste.com", perfil="Funcionário"),
          422, "ALTERACAO_BLOQUEADA")
    assert _tudo(cliente) == antes


def test_admin_nao_pode_alterar_a_propria_organizacao(cliente, adm):
    # contrato PUT: nem o proprio id_organizacao
    _erro(_put(cliente, adm, 1, nome="Nome admin", email="admin@teste.com", perfil="Administrador",
               id_organizacao=1), 422, "ALTERACAO_BLOQUEADA")


def test_admin_pode_alterar_proprio_nome_email_e_senha(cliente, adm, login_com):
    # contrato PUT
    r = _put(cliente, adm, 1, nome="Admin Novo", email="admin2@teste.com", perfil="Administrador",
             senha="SenhaAdminNova1")
    assert r.status_code == 200 and r.json()["nome"] == "Admin Novo"
    assert login_com("admin2@teste.com", "SenhaAdminNova1").status_code == 200


def test_admin_nao_pode_excluir_a_si_mesmo_mesmo_com_outro_admin(cliente, adm):
    # UC02 FE4, RN02 M1
    _criar(cliente, adm, email="adm2@teste.com", perfil="Administrador")
    c = _erro(cliente.delete(f"{U}/1", headers=adm), 422, "ALTERACAO_BLOQUEADA")
    assert c["campos"] == {"id_usuario": "bloqueado"}
    assert _consulta(cliente, "SELECT COUNT(*) AS n FROM USUARIO WHERE id_usuario=1")[0]["n"] == 1


def test_unico_admin_nao_pode_ser_excluido(cliente, adm):
    # UC02 FE4, RN02 M1 (ultima conta Administrador)
    antes = _tudo(cliente)
    _erro(cliente.delete(f"{U}/1", headers=adm), 422, "ALTERACAO_BLOQUEADA")
    assert _tudo(cliente) == antes


def test_com_dois_admins_pode_rebaixar_o_outro(cliente, adm):
    # UC02 FE4 (so bloqueia a ultima conta / o proprio perfil)
    alvo = _criar(cliente, adm, email="alvo@teste.com", perfil="Administrador")["id_usuario"]
    r = _put(cliente, adm, alvo, nome="Alvo", email="alvo@teste.com", perfil="Funcionário")
    assert r.status_code == 200 and r.json()["perfil"] == "Funcionário"


def test_com_dois_admins_pode_excluir_o_outro(cliente, adm):
    # UC02 FA3, FE4
    alvo = _criar(cliente, adm, email="alvo@teste.com", perfil="Administrador")["id_usuario"]
    assert cliente.delete(f"{U}/{alvo}", headers=adm).status_code == 204
    assert _consulta(cliente, "SELECT COUNT(*) AS n FROM USUARIO WHERE perfil='Administrador'")[0]["n"] == 1


def test_admin_remanescente_continua_protegido_apos_excluir_o_outro(cliente, adm):
    # UC02 FE4: apos ficar sozinho, nao pode ser excluido nem rebaixado
    alvo = _criar(cliente, adm, email="alvo@teste.com", perfil="Administrador")["id_usuario"]
    cliente.delete(f"{U}/{alvo}", headers=adm)
    _erro(cliente.delete(f"{U}/1", headers=adm), 422, "ALTERACAO_BLOQUEADA")


# ======================================================================= DELETE
def test_delete_fisico_204_depois_get_404_e_login_401(cliente, adm, login_com):
    # UC02 FA3, contrato DELETE
    r = cliente.delete(f"{U}/2", headers=adm)
    assert r.status_code == 204 and r.content == b""
    _erro(cliente.get(f"{U}/2", headers=adm), 404, "NAO_ENCONTRADO")
    assert _consulta(cliente, "SELECT COUNT(*) AS n FROM USUARIO WHERE id_usuario=2")[0]["n"] == 0
    assert login_com("func@teste.com", SENHA).status_code == 401


def test_delete_inexistente_404_e_nao_remove_nada(cliente, adm):
    # contrato DELETE
    antes = _qtd_usuarios(cliente)
    _erro(cliente.delete(f"{U}/99999", headers=adm), 404, "NAO_ENCONTRADO")
    assert _qtd_usuarios(cliente) == antes


def test_delete_duas_vezes_segunda_404(cliente, adm):
    # UC02 FA3
    assert cliente.delete(f"{U}/2", headers=adm).status_code == 204
    _erro(cliente.delete(f"{U}/2", headers=adm), 404, "NAO_ENCONTRADO")


def test_token_de_conta_excluida_deixa_de_valer(cliente, adm, token_de):
    # RNF05: dados lidos do banco a cada requisicao
    t = _h(token_de(cliente, "empresa"))
    assert cliente.get(ORG, headers=t).status_code == 200
    assert cliente.delete(f"{U}/3", headers=adm).status_code == 204
    assert cliente.get(ORG, headers=t).status_code == 401


# ======================================================================= UC03
@pytest.mark.parametrize("chave,perfil", [("empresa", "Cliente Empresa"), ("ong", "Cliente ONG")])
def test_uc03_perfil_e_organizacao_herdados(cliente, token_de, login_com, chave, perfil):
    # UC03 passo 5, RN02, RN04
    t = _h(token_de(cliente, chave))
    r = cliente.post(ORG, json={"nome": " João ", "email": " JOAO@Org.com ", "senha": "SenhaNova123"}, headers=t)
    assert r.status_code == 201, r.text
    u = r.json()
    assert u["perfil"] == perfil and u["id_organizacao"] == ID_ORG[perfil] and u["nome"] == "João"
    assert u["email"] == "joao@org.com"
    assert u["nome_organizacao"] == USUARIOS[chave][1]
    row = _consulta(cliente, "SELECT perfil,id_organizacao,senha_hash FROM USUARIO WHERE email='joao@org.com'")[0]
    assert (row["perfil"], row["id_organizacao"]) == (perfil, ID_ORG[perfil])
    assert row["senha_hash"].startswith(("$2a$", "$2b$", "$2y$"))  # RNF03
    assert login_com("joao@org.com", "SenhaNova123").json()["usuario"]["perfil"] == perfil


@pytest.mark.parametrize("extra,campo", [
    ({"perfil": "Administrador"}, "perfil"),
    ({"perfil": "Funcionário"}, "perfil"),
    ({"perfil": "Cliente ONG"}, "perfil"),
    ({"perfil": "Empresa Doadora"}, "perfil"),
    ({"id_organizacao": 2}, "id_organizacao"),
    ({"id_organizacao": 99999}, "id_organizacao"),
])
def test_uc03_fe2_perfil_ou_organizacao_diferentes_403_e_nenhuma_conta(cliente, token_de, extra, campo):
    # UC03 FE2, RN02, RN04
    t = _h(token_de(cliente, "empresa"))
    antes = _qtd_usuarios(cliente)
    r = cliente.post(ORG, json={"nome": "X", "email": "x@teste.com", "senha": "SenhaNova123", **extra}, headers=t)
    c = _erro(r, 403, "OPERACAO_NAO_PERMITIDA")
    assert c["campos"] == {campo: "não permitido"}
    assert _qtd_usuarios(cliente) == antes


def test_uc03_campos_iguais_aos_herdados_sao_aceitos(cliente, token_de):
    # contrato POST /organizacao/usuarios
    t = _h(token_de(cliente, "empresa"))
    r = cliente.post(ORG, json={"nome": "X", "email": "x@teste.com", "senha": "SenhaNova123",
                                "perfil": "Cliente Empresa", "id_organizacao": 1}, headers=t)
    assert r.status_code == 201 and r.json()["perfil"] == "Cliente Empresa" and r.json()["id_organizacao"] == 1


def test_uc03_perfil_inexistente_no_corpo_400(cliente, token_de):
    # UC03 FE1
    t = _h(token_de(cliente, "empresa"))
    r = cliente.post(ORG, json={"nome": "X", "email": "x@teste.com", "senha": "SenhaNova123", "perfil": "Root"},
                     headers=t)
    _erro(r, 400, "DADOS_INVALIDOS")


def test_uc03_email_duplicado_409_inclusive_de_outra_organizacao(cliente, token_de):
    # UC03 FE1, UC26
    t = _h(token_de(cliente, "empresa"))
    antes = _qtd_usuarios(cliente)
    for email in ("ong@teste.com", "ONG@teste.com", "empresa@teste.com"):
        _erro(cliente.post(ORG, json={"nome": "X", "email": email, "senha": "SenhaNova123"}, headers=t),
              409, "EMAIL_DUPLICADO")
    assert _qtd_usuarios(cliente) == antes


@pytest.mark.parametrize("corpo", [
    {"nome": "", "email": "x@teste.com", "senha": "SenhaNova123"},
    {"nome": "X", "email": "invalido", "senha": "SenhaNova123"},
    {"nome": "X", "email": "x@teste.com", "senha": "1234567"},
    {"nome": "X", "email": "x@teste.com", "senha": "a" * 129},
    {"nome": "X", "email": "x@teste.com"},
    {},
])
def test_uc03_dados_invalidos_400(cliente, token_de, corpo):
    # UC03 FE1, RNF04
    antes = _qtd_usuarios(cliente)
    _erro(cliente.post(ORG, json=corpo, headers=_h(token_de(cliente, "empresa"))), 400, "DADOS_INVALIDOS")
    assert _qtd_usuarios(cliente) == antes


def test_uc03_senha_8_e_128_aceitas(cliente, token_de):
    # RN02 M1
    t = _h(token_de(cliente, "ong"))
    assert cliente.post(ORG, json={"nome": "A", "email": "a8@t.com", "senha": "a" * 8}, headers=t).status_code == 201
    assert cliente.post(ORG, json={"nome": "A", "email": "a128@t.com", "senha": "a" * 128},
                        headers=t).status_code == 201


def test_uc03_listagem_so_da_propria_organizacao_com_isolamento(cliente, token_de):
    # UC03 FA1, RN04, RNF05
    te, to = _h(token_de(cliente, "empresa")), _h(token_de(cliente, "ong"))
    cliente.post(ORG, json={"nome": "E2", "email": "e2@t.com", "senha": "SenhaNova123"}, headers=te)
    cliente.post(ORG, json={"nome": "O2", "email": "o2@t.com", "senha": "SenhaNova123"}, headers=to)
    le = cliente.get(ORG, headers=te).json()
    lo = cliente.get(ORG, headers=to).json()
    assert {i["email"] for i in le["items"]} == {"empresa@teste.com", "e2@t.com"} and le["total"] == 2
    assert {i["email"] for i in lo["items"]} == {"ong@teste.com", "o2@t.com"} and lo["total"] == 2
    assert all(i["id_organizacao"] == 1 for i in le["items"]) and all(i["id_organizacao"] == 2 for i in lo["items"])


def test_uc03_duas_organizacoes_do_mesmo_tipo_nao_se_enxergam(cliente, token_de, hash_senha):
    # UC03 FA1, RN04, RNF05
    org = _nova_org(cliente, "Cliente Empresa", nome="Outra Empresa")
    _sql(cliente, "INSERT INTO USUARIO (id_organizacao,email,perfil,senha_hash,nome) VALUES (?,?,?,?,?)",
         (org, "vizinho@teste.com", "Cliente Empresa", hash_senha, "Vizinho"))
    te = _h(token_de(cliente, "empresa"))
    assert {i["email"] for i in cliente.get(ORG, headers=te).json()["items"]} == {"empresa@teste.com"}
    tv = _h(cliente.post("/api/v1/auth/login", json={"email": "vizinho@teste.com", "senha": SENHA})
            .json()["access_token"])
    assert {i["email"] for i in cliente.get(ORG, headers=tv).json()["items"]} == {"vizinho@teste.com"}
    r = cliente.post(ORG, json={"nome": "X", "email": "x@t.com", "senha": "SenhaNova123", "id_organizacao": org},
                     headers=te)
    _erro(r, 403, "OPERACAO_NAO_PERMITIDA")


def test_uc03_listagem_paginada_e_size_maximo(cliente, token_de):
    # UC03 FA1, convencoes
    t = _h(token_de(cliente, "empresa"))
    for i in range(3):
        cliente.post(ORG, json={"nome": f"U{i}", "email": f"u{i}@t.com", "senha": "SenhaNova123"}, headers=t)
    r = cliente.get(ORG, params={"page": 2, "size": 3}, headers=t).json()
    assert r["total"] == 4 and r["page"] == 2 and r["size"] == 3 and len(r["items"]) == 1
    _erro(cliente.get(ORG, params={"size": 101}, headers=t), 400, "DADOS_INVALIDOS")


def test_uc03_cliente_nao_altera_nem_exclui_nem_consulta_contas_em_usuarios(cliente, token_de):
    # UC03 FA1 M1, RN02: alterar/excluir e do Administrador
    t = _h(token_de(cliente, "empresa"))
    antes = _tudo(cliente)
    _erro(cliente.delete(f"{U}/3", headers=t), 403, "SEM_PERMISSAO")
    _erro(cliente.put(f"{U}/3", json={"nome": "X", "email": "empresa@teste.com", "perfil": "Cliente Empresa",
                                      "id_organizacao": 1}, headers=t), 403, "SEM_PERMISSAO")
    _erro(cliente.get(f"{U}/4", headers=t), 403, "SEM_PERMISSAO")
    assert _tudo(cliente) == antes


def test_uc03_organizacao_inativa_conta_inativa_403(cliente, token_de):
    # UC03 pre-condicao, RN06, RN09: organizacao desativada depois do login
    t = _h(token_de(cliente, "empresa"))
    _sql(cliente, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=1")
    antes = _qtd_usuarios(cliente)
    r = cliente.post(ORG, json={"nome": "X", "email": "x@t.com", "senha": "SenhaNova123"}, headers=t)
    _erro(r, 403, "CONTA_INATIVA")
    _erro(cliente.get(ORG, headers=t), 403, "CONTA_INATIVA")
    assert _qtd_usuarios(cliente) == antes


def test_uc03_conta_de_organizacao_inativa_nao_loga(cliente, login_com):
    # RN06, RN09, UC03 pre-condicao
    _erro(login_com("inativo@teste.com", SENHA), 403, "CONTA_INATIVA")


def test_uc03_usuario_criado_pelo_cliente_herda_permissoes_do_tipo(cliente, token_de, login_com):
    # UC03: permissoes do tipo de cliente herdadas, sem acesso administrativo
    t = _h(token_de(cliente, "ong"))
    cliente.post(ORG, json={"nome": "A", "email": "a@t.com", "senha": "SenhaNova123"}, headers=t)
    t2 = _h(login_com("a@t.com", "SenhaNova123").json()["access_token"])
    assert cliente.post(ORG, json={"nome": "B", "email": "b@t.com", "senha": "SenhaNova123"},
                        headers=t2).status_code == 201
    assert cliente.get(U, headers=t2).status_code == 403


# ======================================================================= Admin inicial (script)
def test_administrador_inicial_do_script_opera_o_modulo(ambiente, monkeypatch):
    # DP-04, UC02: o Admin criado por scripts.criar_admin loga e usa /usuarios
    for v in ("LEAF_ADMIN_EMAIL", "LEAF_ADMIN_NOME", "LEAF_ADMIN_SENHA"):
        monkeypatch.delenv(v, raising=False)
    from fastapi.testclient import TestClient
    from scripts import criar_admin
    from app.main import criar_app
    monkeypatch.setattr(sys, "argv", ["criar_admin", "--email", "Inicial@Teste.com", "--nome", "Inicial",
                                      "--senha", "SenhaInicial#1"])
    assert criar_admin.main() == 0
    with TestClient(criar_app()) as c:
        r = c.post("/api/v1/auth/login", json={"email": "inicial@teste.com", "senha": "SenhaInicial#1"})
        assert r.status_code == 200
        t = _h(r.json()["access_token"])
        assert c.get(U, headers=t).json()["total"] == 1
        assert c.post(U, json=_corpo(), headers=t).status_code == 201
        _erro(c.delete(f"{U}/{r.json()['usuario']['id_usuario']}", headers=t), 422, "ALTERACAO_BLOQUEADA")


# ======================================================================= DELETE /usuarios/me (DP-64/65/66)
ME = f"{U}/me"


@pytest.mark.parametrize("chave", ["func", "empresa", "ong", "doadora"])
def test_todo_perfil_exclui_a_propria_conta_e_token_vira_401(cliente, token_de, chave):
    # UC02 FA3 ampliado, DP-64: 204, conta some e o token deixa de valer
    t = _h(token_de(cliente, chave))
    antes = _qtd_usuarios(cliente)
    r = cliente.request("DELETE", ME, json={"senha": SENHA}, headers=t)
    assert r.status_code == 204
    assert _qtd_usuarios(cliente) == antes - 1
    assert cliente.get("/api/v1/auth/me", headers=t).status_code == 401


def test_autoexclusao_senha_errada_401_e_conta_permanece(cliente, token_de):
    # DP-64: SENHA_INVALIDA, sessao continua
    t = _h(token_de(cliente, "empresa"))
    antes = _qtd_usuarios(cliente)
    _erro(cliente.request("DELETE", ME, json={"senha": "errada"}, headers=t), 401, "SENHA_INVALIDA")
    assert _qtd_usuarios(cliente) == antes
    assert cliente.get(ORG, headers=t).status_code == 200


def test_autoexclusao_sem_token_401_e_sem_corpo_400(cliente, adm):
    assert cliente.request("DELETE", ME, json={"senha": SENHA}).status_code == 401
    assert cliente.request("DELETE", ME, headers=adm).status_code == 400


def test_ultimo_administrador_nao_se_autoexclui(cliente, adm):
    # DP-65: ALTERACAO_BLOQUEADA
    antes = _tudo(cliente)
    _erro(cliente.request("DELETE", ME, json={"senha": SENHA}, headers=adm), 422, "ALTERACAO_BLOQUEADA")
    assert _tudo(cliente) == antes


def test_administrador_com_outro_admin_pode_se_autoexcluir(cliente, adm):
    # DP-65
    _criar(cliente, adm, email="adm2@teste.com", perfil="Administrador")
    assert cliente.request("DELETE", ME, json={"senha": SENHA}, headers=adm).status_code == 204
    assert _consulta(cliente, "SELECT COUNT(*) AS n FROM USUARIO WHERE perfil='Administrador'")[0]["n"] == 1


def test_autoexclusao_preserva_a_organizacao(cliente, token_de):
    # DP-66
    t = _h(token_de(cliente, "ong"))
    cliente.request("DELETE", ME, json={"senha": SENHA}, headers=t)
    assert _consulta(cliente, "SELECT COUNT(*) AS n FROM ORGANIZACAO WHERE id_organizacao=2")[0]["n"] == 1
