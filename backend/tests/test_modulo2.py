"""Testes da API do Modulo 2 (Organizacoes e parceiros): UC01, UC06, UC25.
Requisitos: RF03, RF06, RF09, RF10; RN01, RN03, RN06, RN09, RN10; RNF04, RNF05.
Contrato: contratos/modulo-2.yaml v1.0.0 (com esclarecimentos). Contas e senhas ficticias (conftest); nunca a conta real.
Semeado pelo conftest: orgs 1 (Cliente Empresa, com usuario), 2 (Cliente ONG, com usuario), 3 (Empresa Doadora, com
usuario), 4 (Cliente Empresa INATIVA, com usuario)."""
import sqlite3

import pytest

from tests.conftest import SENHA, USUARIOS, fazer_login

O = "/api/v1/organizacoes"
P = "/api/v1/parceiros"
CHAVES = ["admin", "func", "empresa", "ong", "doadora"]
TIPOS = ["Cliente Empresa", "Cliente ONG", "Empresa Doadora"]


# ------------------------------------------------------------------ utilitarios
def _h(token):
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def adm(cliente, token_de):
    return _h(token_de(cliente, "admin"))


@pytest.fixture()
def fun(cliente, token_de):
    return _h(token_de(cliente, "func"))


def _consulta(cliente, comando, params=()):
    con = sqlite3.connect(cliente.caminho_banco)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(comando, params).fetchall()
    finally:
        con.close()


def _sql(cliente, comando, params=()):
    con = sqlite3.connect(cliente.caminho_banco)
    cur = con.execute(comando, params)
    con.commit()
    ultimo = cur.lastrowid
    con.close()
    return ultimo


def _tab(cliente, nome):
    return [tuple(r) for r in _consulta(cliente, f"SELECT * FROM {nome} ORDER BY 1")]


def _erro(r, status, codigo):
    assert r.status_code == status, r.text
    corpo = r.json()
    assert set(corpo) == {"codigo", "mensagem", "campos"}
    assert corpo["codigo"] == codigo
    assert corpo["mensagem"] and isinstance(corpo["campos"], dict)
    return corpo


_seq = [100]


def _corpo(**kw):
    _seq[0] += 1
    base = {"nome_razao_social": f"Org Teste {_seq[0]}", "cnpj": f"{_seq[0]:014d}", "tipo": "Cliente Empresa",
            "telefone": "(11) 91234-5678", "email": "contato@teste.com", "endereco": "Rua das Folhas, 100"}
    base.update(kw)
    return base


def _criar_org(cliente, adm, **kw):
    r = cliente.post(O, json=_corpo(**kw), headers=adm)
    assert r.status_code == 201, r.text
    return r.json()


def _criar_parceiro(cliente, adm, id_org, tipo="Patrocinador em Potencial", **kw):
    r = cliente.post(P, json={"id_organizacao": id_org, "tipo_parceria": tipo, **kw}, headers=adm)
    assert r.status_code == 201, r.text
    return r.json()


# ------------------------------------------------------------------ permissoes (RN01, RN03, RNF05)
def _rotas(id_org=1, id_par=9999):
    """(metodo, caminho, corpo, perfis autorizados). Corpos validos para a permissao ser o unico motivo de recusa."""
    novo = _corpo()
    contato = {"telefone": "1133334444", "email": "a@b.co", "endereco": "Rua Z"}
    return [
        ("GET", O, None, {"admin", "func"}),
        ("POST", O, novo, {"admin"}),
        ("GET", f"{O}/{id_org}", None, {"admin", "func"}),
        ("PUT", f"{O}/{id_org}", _corpo(cnpj="00000000000003"), {"admin"}),
        ("PATCH", f"{O}/{id_org}/contato", contato, {"admin", "func"}),
        ("PATCH", f"{O}/{id_org}/situacao", {"situacao": "Ativa"}, {"admin"}),
        ("GET", P, None, {"admin"}),
        ("POST", P, {"id_organizacao": 2, "tipo_parceria": "Patrocinador em Potencial"}, {"admin"}),
        ("GET", f"{P}/{id_par}", None, {"admin"}),
        ("PUT", f"{P}/{id_par}", {"tipo_parceria": "Patrocinador em Potencial"}, {"admin"}),
        ("PATCH", f"{P}/{id_par}/situacao", {"situacao_parceria": "Ativa"}, {"admin"}),
    ]


@pytest.mark.parametrize("indice", range(11))
def test_sem_token_401_em_todas_as_rotas(cliente, indice):
    # RNF05, RN01
    metodo, url, corpo, _ = _rotas()[indice]
    r = cliente.request(metodo, url, json=corpo)
    _erro(r, 401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("indice", range(11))
def test_token_invalido_401_em_todas_as_rotas(cliente, indice):
    # RNF05
    metodo, url, corpo, _ = _rotas()[indice]
    r = cliente.request(metodo, url, json=corpo, headers=_h("token.invalido.xyz"))
    _erro(r, 401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("chave", CHAVES)
@pytest.mark.parametrize("indice", range(11))
def test_matriz_de_permissoes_por_rota_e_perfil(cliente, token_de, chave, indice):
    # RN01, RN03, RF03, RF06, RF09, RF10 (x-permissoes): autorizado nao recebe 401/403; proibido recebe 403 SEM_PERMISSAO
    metodo, url, corpo, autorizados = _rotas()[indice]
    r = cliente.request(metodo, url, json=corpo, headers=_h(token_de(cliente, chave)))
    if chave in autorizados:
        assert r.status_code not in (401, 403), f"{metodo} {url} {chave}: {r.status_code} {r.text}"
    else:
        _erro(r, 403, "SEM_PERMISSAO")


@pytest.mark.parametrize("chave", ["empresa", "ong", "doadora"])
def test_clientes_e_doadora_403_em_tudo_e_nada_gravado(cliente, token_de, chave):
    # RN01, RNF05: nenhuma alteracao feita por perfil proibido
    antes = (_tab(cliente, "ORGANIZACAO"), _tab(cliente, "PARCEIRO"))
    h = _h(token_de(cliente, chave))
    for metodo, url, corpo, _ in _rotas():
        _erro(cliente.request(metodo, url, json=corpo, headers=h), 403, "SEM_PERMISSAO")
    assert (_tab(cliente, "ORGANIZACAO"), _tab(cliente, "PARCEIRO")) == antes


def test_funcionario_proibido_em_post_put_situacao_e_todo_parceiros_sem_gravar(cliente, fun):
    # RN03, RN09: CNPJ, nome, tipo, situacao e parceiros sao exclusivos do Administrador
    antes = (_tab(cliente, "ORGANIZACAO"), _tab(cliente, "PARCEIRO"))
    for metodo, url, corpo, aut in _rotas():
        if "func" not in aut:
            _erro(cliente.request(metodo, url, json=corpo, headers=fun), 403, "SEM_PERMISSAO")
    assert (_tab(cliente, "ORGANIZACAO"), _tab(cliente, "PARCEIRO")) == antes


def test_funcionario_consulta_organizacoes(cliente, fun):
    # UC01 FA3, RF09, RF03
    r = cliente.get(O, headers=fun)
    assert r.status_code == 200 and r.json()["total"] == 4
    assert cliente.get(f"{O}/1", headers=fun).status_code == 200


# ------------------------------------------------------------------ UC01 criacao
@pytest.mark.parametrize("tipo", TIPOS)
def test_criar_organizacao_por_tipo_201_situacao_padrao_ativa(cliente, adm, tipo):
    # UC01 fluxo principal, RF06, RN06
    corpo = _corpo(tipo=tipo)
    r = cliente.post(O, json=corpo, headers=adm)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["tipo"] == tipo and d["situacao"] == "Ativa" and d["possui_parceria"] is False
    assert d["cnpj"] == corpo["cnpj"] and isinstance(d["id_organizacao"], int)
    assert set(d) == {"id_organizacao", "cnpj", "nome_razao_social", "tipo", "telefone", "email", "endereco",
                      "situacao", "possui_parceria"}
    linha = _consulta(cliente, "SELECT * FROM ORGANIZACAO WHERE id_organizacao=?", (d["id_organizacao"],))[0]
    assert linha["nome_razao_social"] == corpo["nome_razao_social"]
    assert cliente.get(f"{O}/{d['id_organizacao']}", headers=adm).json() == d


def test_criar_com_situacao_inativa_explicita(cliente, adm):
    # UC01, DP-03
    assert _criar_org(cliente, adm, situacao="Inativa")["situacao"] == "Inativa"


@pytest.mark.parametrize("valor", ["ativa", "inativa", "ATIVA", "Ativo", "", "Desativada"])
def test_situacao_invalida_na_criacao_400(cliente, adm, valor):
    # UC01 FE2, DP-03: valores exatamente Ativa ou Inativa
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.post(O, json=_corpo(situacao=valor), headers=adm), 400, "DADOS_INVALIDOS")
    assert "situacao" in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes


def test_tipo_invalido_400(cliente, adm):
    # UC01 FE2
    c = _erro(cliente.post(O, json=_corpo(tipo="Patrocinador em Potencial"), headers=adm), 400, "DADOS_INVALIDOS")
    assert "tipo" in c["campos"]


@pytest.mark.parametrize("campo", ["nome_razao_social", "cnpj", "tipo", "telefone", "email", "endereco"])
def test_campo_obrigatorio_ausente_400_aponta_o_campo(cliente, adm, campo):
    # UC01 FE2, RNF04
    corpo = _corpo()
    del corpo[campo]
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.post(O, json=corpo, headers=adm), 400, "DADOS_INVALIDOS")
    assert campo in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes


@pytest.mark.parametrize("campo", ["nome_razao_social", "cnpj", "telefone", "email", "endereco"])
@pytest.mark.parametrize("vazio", ["", "   "])
def test_campo_obrigatorio_vazio_ou_so_espacos_400(cliente, adm, campo, vazio):
    # UC01 FE2, RNF04
    c = _erro(cliente.post(O, json=_corpo(**{campo: vazio}), headers=adm), 400, "DADOS_INVALIDOS")
    assert campo in c["campos"]


def test_corpo_vazio_aponta_todos_os_campos_pendentes(cliente, adm):
    # UC01 FE2: "aponta os campos pendentes"
    c = _erro(cliente.post(O, json={}, headers=adm), 400, "DADOS_INVALIDOS")
    assert {"nome_razao_social", "cnpj", "tipo", "telefone", "email", "endereco"} <= set(c["campos"])


def test_limite_nome_150(cliente, adm):
    # UC01 FE2 (limite do contrato)
    assert cliente.post(O, json=_corpo(nome_razao_social="N" * 150), headers=adm).status_code == 201
    c = _erro(cliente.post(O, json=_corpo(nome_razao_social="N" * 151), headers=adm), 400, "DADOS_INVALIDOS")
    assert "nome_razao_social" in c["campos"]


def test_limite_endereco_255(cliente, adm):
    # UC01 FE2
    assert cliente.post(O, json=_corpo(endereco="E" * 255), headers=adm).status_code == 201
    c = _erro(cliente.post(O, json=_corpo(endereco="E" * 256), headers=adm), 400, "DADOS_INVALIDOS")
    assert "endereco" in c["campos"]


def test_limite_email_254(cliente, adm):
    # UC01 FE2, DP-22
    ok = "a" * (254 - len("@b.co")) + "@b.co"
    assert len(ok) == 254
    assert cliente.post(O, json=_corpo(email=ok), headers=adm).status_code == 201
    c = _erro(cliente.post(O, json=_corpo(email="a" + ok), headers=adm), 400, "DADOS_INVALIDOS")
    assert "email" in c["campos"]


@pytest.mark.parametrize("email", ["semarroba", "a@b", "a b@c.com", "@c.com", "a@@c.com"])
def test_email_formato_invalido_400(cliente, adm, email):
    # UC01 passo 4, RNF04
    c = _erro(cliente.post(O, json=_corpo(email=email), headers=adm), 400, "DADOS_INVALIDOS")
    assert "email" in c["campos"]


def test_email_normalizado_para_minusculas(cliente, adm):
    # DP-22
    d = _criar_org(cliente, adm, email="  Contato@Empresa.COM ")
    assert d["email"] == "contato@empresa.com"


@pytest.mark.parametrize("tel,esperado", [("1133334444", "1133334444"), ("11912345678", "11912345678"),
                                          ("(11) 3333-4444", "1133334444"), ("(11) 91234-5678", "11912345678"),
                                          ("+55 11 3333.4444", None)])
def test_telefone_10_ou_11_digitos_com_mascara_guardado_so_com_digitos(cliente, adm, tel, esperado):
    # DP-22, esclarecimento 7
    r = cliente.post(O, json=_corpo(telefone=tel), headers=adm)
    if esperado is None:
        # "+55 11 3333.4444" tem 12 digitos: deve falhar
        _erro(r, 400, "DADOS_INVALIDOS")
    else:
        assert r.status_code == 201, r.text
        assert r.json()["telefone"] == esperado


@pytest.mark.parametrize("tel", ["123456789", "(11) 9123-567", "119123456789", "(11) 91234-56789", "abcdefghij",
                                 "11 9999x8888"])
def test_telefone_9_ou_12_digitos_ou_letras_400(cliente, adm, tel):
    # DP-22, UC01 passo 4
    c = _erro(cliente.post(O, json=_corpo(telefone=tel), headers=adm), 400, "DADOS_INVALIDOS")
    assert "telefone" in c["campos"]


# ------------------------------------------------------------------ UC25 CNPJ
@pytest.mark.parametrize("entrada", ["12345678000195", "12.345.678/0001-95", "12 345 678 0001 95", "12.345.678/000195"])
def test_cnpj_com_ou_sem_mascara_normaliza_para_14_digitos(cliente, adm, entrada):
    # UC25 passo 2, RN06, DP-21
    d = _criar_org(cliente, adm, cnpj=entrada)
    assert d["cnpj"] == "12345678000195"
    assert _consulta(cliente, "SELECT cnpj FROM ORGANIZACAO WHERE id_organizacao=?", (d["id_organizacao"],))[0][0] \
        == "12345678000195"


@pytest.mark.parametrize("cnpj", ["1234567800019", "123456780001955", "12.345.678/0001-9", "ABCDEFGHIJKLMN",
                                  "1234567800019A", "12345678000195;", "12.345.678/0001-95x"])
def test_cnpj_formato_invalido_400_nada_gravado(cliente, adm, cnpj):
    # UC25 FE1, UC01 FE1
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.post(O, json=_corpo(cnpj=cnpj), headers=adm), 400, "DADOS_INVALIDOS")
    assert "cnpj" in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes


def test_cnpj_duplicado_409_sem_gravar(cliente, adm):
    # UC25 FE1, RN06, RN09
    _criar_org(cliente, adm, cnpj="12345678000195")
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.post(O, json=_corpo(cnpj="12345678000195"), headers=adm), 409, "CNPJ_DUPLICADO")
    assert "cnpj" in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes


@pytest.mark.parametrize("primeiro,segundo", [("12345678000195", "12.345.678/0001-95"),
                                              ("12.345.678/0001-95", "12345678000195"),
                                              ("12.345.678/0001-95", "12 345 678 0001 95")])
def test_cnpj_duplicado_mascarado_versus_sem_mascara(cliente, adm, primeiro, segundo):
    # UC25: duplicidade e checada sobre o valor normalizado
    _criar_org(cliente, adm, cnpj=primeiro)
    _erro(cliente.post(O, json=_corpo(cnpj=segundo), headers=adm), 409, "CNPJ_DUPLICADO")


def test_cnpj_duplicado_vale_tambem_contra_organizacao_inativa(cliente, adm):
    # UC25, RN06: unico entre TODAS as organizacoes
    d = _criar_org(cliente, adm, cnpj="99999999000199", situacao="Inativa")
    _erro(cliente.post(O, json=_corpo(cnpj=d["cnpj"]), headers=adm), 409, "CNPJ_DUPLICADO")


def test_validacao_400_vem_antes_do_409(cliente, adm):
    # UC01 passo 4 / contrato: campos e formatos (400) -> UC25 (409)
    _criar_org(cliente, adm, cnpj="12345678000195")
    _erro(cliente.post(O, json=_corpo(cnpj="12345678000195", telefone="123"), headers=adm), 400, "DADOS_INVALIDOS")


def test_alterar_mantendo_o_proprio_cnpj_e_ok_mesmo_mascarado(cliente, adm):
    # UC25 passo 2: exclui o proprio registro
    d = _criar_org(cliente, adm, cnpj="12345678000195")
    r = cliente.put(f"{O}/{d['id_organizacao']}", json=_corpo(cnpj="12.345.678/0001-95", nome_razao_social="Novo"),
                    headers=adm)
    assert r.status_code == 200, r.text
    assert r.json()["cnpj"] == "12345678000195" and r.json()["nome_razao_social"] == "Novo"


def test_alterar_para_cnpj_de_outra_organizacao_409_nada_alterado(cliente, adm):
    # UC25 FE1, UC01 FA1
    a = _criar_org(cliente, adm, cnpj="11111111000111")
    b = _criar_org(cliente, adm, cnpj="22222222000122")
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.put(f"{O}/{b['id_organizacao']}", json=_corpo(cnpj="11.111.111/0001-11"), headers=adm),
              409, "CNPJ_DUPLICADO")
    assert "cnpj" in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes and a


def test_nao_ha_rota_de_consulta_separada_de_cnpj(cliente, adm):
    # UC25 / DP-28: o sistema nao oferece consulta separada de CNPJ
    for caminho in (f"{O}/cnpj/12345678000195", "/api/v1/cnpj/12345678000195", f"{O}/validar-cnpj"):
        assert cliente.get(caminho, headers=adm).status_code in (400, 404, 405)


# ------------------------------------------------------------------ GET por id e PUT
def test_obter_inexistente_404(cliente, adm):
    # UC01 FA1
    _erro(cliente.get(f"{O}/9999", headers=adm), 404, "NAO_ENCONTRADO")


def test_obter_traz_possui_parceria(cliente, adm):
    # UC01 FA1, UC06
    d = _criar_org(cliente, adm)
    assert cliente.get(f"{O}/{d['id_organizacao']}", headers=adm).json()["possui_parceria"] is False
    _criar_parceiro(cliente, adm, d["id_organizacao"])
    assert cliente.get(f"{O}/{d['id_organizacao']}", headers=adm).json()["possui_parceria"] is True


def test_put_altera_os_seis_campos_e_nao_altera_situacao(cliente, adm):
    # UC01 FA1, UC25
    d = _criar_org(cliente, adm, situacao="Inativa")
    novo = {"nome_razao_social": "Razao Nova", "cnpj": "98.765.432/0001-10", "tipo": "Cliente ONG",
            "telefone": "(21) 2222-3333", "email": "Novo@Mail.com", "endereco": "Av. Nova, 5", "situacao": "Ativa"}
    r = cliente.put(f"{O}/{d['id_organizacao']}", json=novo, headers=adm)
    assert r.status_code == 200, r.text
    assert r.json() == {"id_organizacao": d["id_organizacao"], "cnpj": "98765432000110", "nome_razao_social": "Razao Nova",
                        "tipo": "Cliente ONG", "telefone": "2122223333", "email": "novo@mail.com",
                        "endereco": "Av. Nova, 5", "situacao": "Inativa", "possui_parceria": False}


def test_put_inexistente_404(cliente, adm):
    # UC01 FA1
    _erro(cliente.put(f"{O}/9999", json=_corpo(), headers=adm), 404, "NAO_ENCONTRADO")


def test_put_corpo_invalido_400_nada_alterado(cliente, adm):
    # UC01 FE2
    d = _criar_org(cliente, adm)
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.put(f"{O}/{d['id_organizacao']}", json=_corpo(telefone="1"), headers=adm), 400, "DADOS_INVALIDOS")
    assert "telefone" in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes


def test_put_exige_todos_os_campos(cliente, adm):
    # contrato: todos obrigatorios no PUT
    d = _criar_org(cliente, adm)
    corpo = _corpo()
    del corpo["endereco"]
    _erro(cliente.put(f"{O}/{d['id_organizacao']}", json=corpo, headers=adm), 400, "DADOS_INVALIDOS")


def test_put_ordem_400_antes_de_404(cliente, adm):
    # contrato, esclarecimento 1
    _erro(cliente.put(f"{O}/9999", json=_corpo(cnpj="123"), headers=adm), 400, "DADOS_INVALIDOS")


# ------------------------------------------------------------------ TIPO_EM_USO (RN06, DP-23)
def test_tipo_em_uso_com_usuario_vinculado_422(cliente, adm):
    # RN06, UC01 FE3: org 1 tem usuario
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.put(f"{O}/1", json=_corpo(cnpj="00000000000003", tipo="Cliente ONG"), headers=adm),
              422, "TIPO_EM_USO")
    assert "tipo" in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes


def test_tipo_em_uso_com_parceria_empresa_doadora_422(cliente, adm):
    # RN06, UC01 FE3
    d = _criar_org(cliente, adm, tipo="Empresa Doadora")
    _criar_parceiro(cliente, adm, d["id_organizacao"], "Empresa Doadora")
    antes = _tab(cliente, "ORGANIZACAO")
    for novo in ("Cliente Empresa", "Cliente ONG"):
        _erro(cliente.put(f"{O}/{d['id_organizacao']}", json=_corpo(cnpj=d["cnpj"], tipo=novo), headers=adm),
              422, "TIPO_EM_USO")
    assert _tab(cliente, "ORGANIZACAO") == antes


def test_tipo_em_uso_parceria_doadora_inativa_ainda_bloqueia(cliente, adm):
    # contrato, esclarecimento 5: a parceria conta em qualquer situacao
    d = _criar_org(cliente, adm, tipo="Empresa Doadora")
    p = _criar_parceiro(cliente, adm, d["id_organizacao"], "Empresa Doadora", situacao_parceria="Inativa")
    assert p["situacao_parceria"] == "Inativa"
    _erro(cliente.put(f"{O}/{d['id_organizacao']}", json=_corpo(cnpj=d["cnpj"], tipo="Cliente ONG"), headers=adm),
          422, "TIPO_EM_USO")


def test_mesmo_tipo_reenviado_nao_bloqueia(cliente, adm):
    # esclarecimento 5: so dispara quando o tipo realmente muda
    r = cliente.put(f"{O}/1", json=_corpo(cnpj="00000000000003", tipo="Cliente Empresa", nome_razao_social="Outro"),
                    headers=adm)
    assert r.status_code == 200, r.text
    d = _criar_org(cliente, adm, tipo="Empresa Doadora")
    _criar_parceiro(cliente, adm, d["id_organizacao"], "Empresa Doadora")
    r = cliente.put(f"{O}/{d['id_organizacao']}", json=_corpo(cnpj=d["cnpj"], tipo="Empresa Doadora"), headers=adm)
    assert r.status_code == 200, r.text


def test_organizacao_sem_vinculos_pode_mudar_de_tipo(cliente, adm):
    # RN06 (so bloqueia com vinculos)
    d = _criar_org(cliente, adm, tipo="Cliente Empresa")
    r = cliente.put(f"{O}/{d['id_organizacao']}", json=_corpo(cnpj=d["cnpj"], tipo="Cliente ONG"), headers=adm)
    assert r.status_code == 200 and r.json()["tipo"] == "Cliente ONG"


def test_parceria_patrocinador_nao_bloqueia_mudanca_de_tipo(cliente, adm):
    # RN06: bloqueio so para parceria como Empresa Doadora
    d = _criar_org(cliente, adm, tipo="Cliente Empresa")
    _criar_parceiro(cliente, adm, d["id_organizacao"], "Patrocinador em Potencial")
    r = cliente.put(f"{O}/{d['id_organizacao']}", json=_corpo(cnpj=d["cnpj"], tipo="Cliente ONG"), headers=adm)
    assert r.status_code == 200, r.text


def test_demais_campos_podem_mudar_mesmo_com_tipo_em_uso(cliente, adm):
    # RN06 so protege o tipo
    r = cliente.put(f"{O}/1", json=_corpo(cnpj="00000000000003", tipo="Cliente Empresa", endereco="Nova rua"),
                    headers=adm)
    assert r.status_code == 200 and r.json()["endereco"] == "Nova rua"


# ------------------------------------------------------------------ PATCH /situacao (UC01 FA2, RN06, RN09)
def test_desativar_e_reativar_organizacao_preserva_cadastro(cliente, adm):
    # UC01 FA2
    antes = cliente.get(f"{O}/1", headers=adm).json()
    r = cliente.patch(f"{O}/1/situacao", json={"situacao": "Inativa"}, headers=adm)
    assert r.status_code == 200 and r.json()["situacao"] == "Inativa"
    assert {k: v for k, v in r.json().items() if k != "situacao"} == {k: v for k, v in antes.items() if k != "situacao"}
    r = cliente.patch(f"{O}/1/situacao", json={"situacao": "Ativa"}, headers=adm)
    assert r.status_code == 200 and r.json() == antes


def test_situacao_idempotente(cliente, adm):
    # contrato: idempotente
    for valor in ("Ativa", "Ativa", "Inativa", "Inativa"):
        r = cliente.patch(f"{O}/1/situacao", json={"situacao": valor}, headers=adm)
        assert r.status_code == 200 and r.json()["situacao"] == valor


@pytest.mark.parametrize("valor", ["ativa", "inativa", "Desativada", "", None])
def test_situacao_valor_invalido_400(cliente, adm, valor):
    # DP-03
    antes = _tab(cliente, "ORGANIZACAO")
    c = _erro(cliente.patch(f"{O}/1/situacao", json={"situacao": valor}, headers=adm), 400, "DADOS_INVALIDOS")
    assert "situacao" in c["campos"]
    assert _tab(cliente, "ORGANIZACAO") == antes


def test_situacao_sem_corpo_400_e_inexistente_404(cliente, adm):
    # contrato; esclarecimento 1 (400 antes de 404)
    _erro(cliente.patch(f"{O}/1/situacao", json={}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(cliente.patch(f"{O}/9999/situacao", json={"situacao": "Inativa"}, headers=adm), 404, "NAO_ENCONTRADO")
    _erro(cliente.patch(f"{O}/9999/situacao", json={"situacao": "x"}, headers=adm), 400, "DADOS_INVALIDOS")


def test_desativar_nao_apaga_nada_nem_usuarios(cliente, adm):
    # UC01 FA2, RN06: preserva registros
    usuarios = _tab(cliente, "USUARIO")
    cliente.patch(f"{O}/1/situacao", json={"situacao": "Inativa"}, headers=adm)
    assert _tab(cliente, "USUARIO") == usuarios
    assert len(_tab(cliente, "ORGANIZACAO")) == 4


def test_login_de_usuario_de_organizacao_inativa_403_e_volta_apos_reativar(cliente, adm):
    # UC01 FA2, RN06, RN09, UC04 FE2 (DP-02): desativar bloqueia acesso; reativar restaura
    assert fazer_login(cliente, "empresa").status_code == 200
    cliente.patch(f"{O}/1/situacao", json={"situacao": "Inativa"}, headers=adm)
    r = fazer_login(cliente, "empresa")
    _erro(r, 403, "CONTA_INATIVA")
    cliente.patch(f"{O}/1/situacao", json={"situacao": "Ativa"}, headers=adm)
    assert fazer_login(cliente, "empresa").status_code == 200


def test_organizacao_semeada_inativa_volta_a_funcionar_apos_reativar(cliente, adm):
    # UC01 FA2: reativacao restaura o acesso
    _erro(fazer_login(cliente, "inativo"), 403, "CONTA_INATIVA")
    assert cliente.patch(f"{O}/4/situacao", json={"situacao": "Ativa"}, headers=adm).status_code == 200
    assert fazer_login(cliente, "inativo").status_code == 200


def test_desativar_organizacao_nao_faz_cascata_na_parceria(cliente, adm):
    # contrato /situacao: sem efeito em cascata sobre a parceria
    d = _criar_org(cliente, adm, tipo="Empresa Doadora")
    p = _criar_parceiro(cliente, adm, d["id_organizacao"], "Empresa Doadora")
    cliente.patch(f"{O}/{d['id_organizacao']}/situacao", json={"situacao": "Inativa"}, headers=adm)
    atual = cliente.get(f"{P}/{p['id_parceiro']}", headers=adm).json()
    assert atual["situacao_parceria"] == "Ativa" and atual["situacao_organizacao"] == "Inativa"


# ------------------------------------------------------------------ PATCH /contato (RF09, DP-26)
_CONTATO = {"telefone": "(21) 2222-3333", "email": "Novo@Contato.com", "endereco": "Rua Nova, 9"}


def test_admin_altera_contato(cliente, adm):
    # RF09, RF06
    r = cliente.patch(f"{O}/1/contato", json=_CONTATO, headers=adm)
    assert r.status_code == 200, r.text
    d = r.json()
    assert (d["telefone"], d["email"], d["endereco"]) == ("2122223333", "novo@contato.com", "Rua Nova, 9")


@pytest.mark.parametrize("id_org", [1, 2])
def test_funcionario_altera_contato_de_cliente_empresa_e_ong(cliente, fun, id_org):
    # UC01 FA3, RF09, RN09
    r = cliente.patch(f"{O}/{id_org}/contato", json=_CONTATO, headers=fun)
    assert r.status_code == 200, r.text
    assert r.json()["telefone"] == "2122223333"


def test_funcionario_em_empresa_doadora_403_operacao_nao_permitida(cliente, fun):
    # UC01 FE4, RF09, DP-26
    antes = _tab(cliente, "ORGANIZACAO")
    _erro(cliente.patch(f"{O}/3/contato", json=_CONTATO, headers=fun), 403, "OPERACAO_NAO_PERMITIDA")
    assert _tab(cliente, "ORGANIZACAO") == antes


def test_admin_altera_contato_de_empresa_doadora(cliente, adm):
    # RF06: so o Funcionario e limitado
    assert cliente.patch(f"{O}/3/contato", json=_CONTATO, headers=adm).status_code == 200


@pytest.mark.parametrize("chave", ["admin", "func"])
def test_contato_so_altera_tres_campos(cliente, token_de, chave):
    # UC01 FE4, RN09: CNPJ, nome, tipo e situacao nao mudam por esta rota
    h = _h(token_de(cliente, chave))
    antes = cliente.get(f"{O}/1", headers=h).json()
    extra = {**_CONTATO, "nome_razao_social": "HACK", "cnpj": "99999999999999", "tipo": "Cliente ONG",
             "situacao": "Inativa", "id_organizacao": 77}
    r = cliente.patch(f"{O}/1/contato", json=extra, headers=h)
    assert r.status_code == 200, r.text
    d = r.json()
    for k in ("id_organizacao", "cnpj", "nome_razao_social", "tipo", "situacao"):
        assert d[k] == antes[k], k
    assert d["telefone"] == "2122223333" and d["endereco"] == "Rua Nova, 9"


@pytest.mark.parametrize("campo,valor", [("telefone", "123"), ("email", "invalido"), ("endereco", " ")])
def test_contato_invalido_400(cliente, adm, campo, valor):
    # UC01 FE2, RNF04
    c = _erro(cliente.patch(f"{O}/1/contato", json={**_CONTATO, campo: valor}, headers=adm), 400, "DADOS_INVALIDOS")
    assert campo in c["campos"]


def test_contato_inexistente_404(cliente, adm, fun):
    # contrato
    _erro(cliente.patch(f"{O}/9999/contato", json=_CONTATO, headers=adm), 404, "NAO_ENCONTRADO")
    _erro(cliente.patch(f"{O}/9999/contato", json=_CONTATO, headers=fun), 404, "NAO_ENCONTRADO")


# ------------------------------------------------------------------ listagem de organizacoes
def _popular(cliente, adm):
    _criar_org(cliente, adm, nome_razao_social="Alfa Reciclagem", cnpj="12.345.678/0001-95", tipo="Cliente Empresa")
    _criar_org(cliente, adm, nome_razao_social="Beta ONG Verde", cnpj="22222222000122", tipo="Cliente ONG",
               situacao="Inativa")
    d = _criar_org(cliente, adm, nome_razao_social="Gama Doadora", cnpj="33333333000133", tipo="Empresa Doadora")
    return d


def test_listar_formato_paginacao_e_ordenacao_por_nome(cliente, adm):
    # UC01 FA1
    _popular(cliente, adm)
    r = cliente.get(O, headers=adm)
    assert r.status_code == 200
    d = r.json()
    assert set(d) == {"items", "total", "page", "size"} and d["total"] == 7 and d["page"] == 1 and d["size"] == 20
    nomes = [i["nome_razao_social"] for i in d["items"]]
    assert nomes == sorted(nomes, key=str.lower)


def test_listar_paginacao_page_e_size(cliente, adm):
    # UC01 FA1, CONVENCOES
    _popular(cliente, adm)
    p1 = cliente.get(f"{O}?page=1&size=3", headers=adm).json()
    p3 = cliente.get(f"{O}?page=3&size=3", headers=adm).json()
    p9 = cliente.get(f"{O}?page=9&size=3", headers=adm).json()
    assert len(p1["items"]) == 3 and p1["total"] == 7 and p1["size"] == 3
    assert len(p3["items"]) == 1 and p3["page"] == 3
    assert p9["items"] == [] and p9["total"] == 7
    ids = [i["id_organizacao"] for i in p1["items"]] + \
          [i["id_organizacao"] for i in cliente.get(f"{O}?page=2&size=3", headers=adm).json()["items"]] + \
          [i["id_organizacao"] for i in p3["items"]]
    assert len(set(ids)) == 7


def test_listar_size_100_ok(cliente, adm):
    # contrato maximum 100
    assert cliente.get(f"{O}?size=100", headers=adm).status_code == 200


@pytest.mark.parametrize("qs", ["size=101", "size=0", "page=0", "page=-1", "size=abc", "page=x"])
def test_listar_paginacao_invalida_400(cliente, adm, qs):
    # contrato (size max 100)
    _erro(cliente.get(f"{O}?{qs}", headers=adm), 400, "DADOS_INVALIDOS")


@pytest.mark.parametrize("qs", ["tipo=Patrocinador", "situacao=ativa", "situacao=Outra", "sem_parceria=talvez"])
def test_listar_filtro_invalido_400(cliente, adm, qs):
    # contrato
    _erro(cliente.get(f"{O}?{qs}", headers=adm), 400, "DADOS_INVALIDOS")


def test_listar_q_com_mais_de_150_caracteres_400(cliente, adm):
    # contrato maxLength 150
    _erro(cliente.get(f"{O}?q={'a' * 151}", headers=adm), 400, "DADOS_INVALIDOS")


def test_filtro_por_tipo(cliente, adm):
    # UC01 FA1
    _popular(cliente, adm)
    for tipo in TIPOS:
        itens = cliente.get(O, params={"tipo": tipo}, headers=adm).json()["items"]
        assert itens and all(i["tipo"] == tipo for i in itens)


def test_filtro_por_situacao(cliente, adm):
    # UC01 FA1
    _popular(cliente, adm)
    ina = cliente.get(O, params={"situacao": "Inativa"}, headers=adm).json()
    ati = cliente.get(O, params={"situacao": "Ativa"}, headers=adm).json()
    assert ina["total"] == 2 and all(i["situacao"] == "Inativa" for i in ina["items"])
    assert ati["total"] == 5 and all(i["situacao"] == "Ativa" for i in ati["items"])


def test_filtro_q_nome_sem_diferenciar_caixa(cliente, adm):
    # contrato /GET, esclarecimento 6
    _popular(cliente, adm)
    for q in ("alfa", "ALFA", "Reciclagem", "  alfa  "):
        d = cliente.get(O, params={"q": q}, headers=adm).json()
        assert [i["nome_razao_social"] for i in d["items"]] == ["Alfa Reciclagem"], q


@pytest.mark.parametrize("q", ["12345678000195", "12.345.678/0001-95", "12.345.678", "45678000", "0001-95"])
def test_filtro_q_cnpj_com_e_sem_mascara(cliente, adm, q):
    # esclarecimento 6
    _popular(cliente, adm)
    d = cliente.get(O, params={"q": q}, headers=adm).json()
    assert [i["nome_razao_social"] for i in d["items"]] == ["Alfa Reciclagem"], q


def test_filtro_q_sem_resultado_e_curingas_literais(cliente, adm):
    # esclarecimento 6; % e _ nao sao curingas
    _popular(cliente, adm)
    assert cliente.get(O, params={"q": "inexistente"}, headers=adm).json()["total"] == 0
    assert cliente.get(O, params={"q": "%"}, headers=adm).json()["total"] == 0
    assert cliente.get(O, params={"q": "_"}, headers=adm).json()["total"] == 0


def test_filtros_combinados(cliente, adm):
    # UC01 FA1
    _popular(cliente, adm)
    d = cliente.get(O, params={"tipo": "Cliente ONG", "situacao": "Inativa", "q": "verde"}, headers=adm).json()
    assert d["total"] == 1 and d["items"][0]["nome_razao_social"] == "Beta ONG Verde"
    assert cliente.get(O, params={"tipo": "Cliente ONG", "situacao": "Ativa", "q": "verde"}, headers=adm
                       ).json()["total"] == 0


def test_sem_parceria_true_e_false_e_possui_parceria(cliente, adm):
    # contrato /GET, esclarecimento 2
    d = _popular(cliente, adm)
    _criar_parceiro(cliente, adm, d["id_organizacao"], "Empresa Doadora")
    todos = cliente.get(O, headers=adm).json()
    sem = cliente.get(O, params={"sem_parceria": "true"}, headers=adm).json()
    falso = cliente.get(O, params={"sem_parceria": "false"}, headers=adm).json()
    assert sem["total"] == todos["total"] - 1
    assert all(i["possui_parceria"] is False for i in sem["items"])
    assert d["id_organizacao"] not in [i["id_organizacao"] for i in sem["items"]]
    assert falso == todos  # false = sem filtro
    assert [i["possui_parceria"] for i in todos["items"]].count(True) == 1


def test_funcionario_lista_com_filtros(cliente, fun, adm):
    # RF09
    _popular(cliente, adm)
    assert cliente.get(O, params={"tipo": "Cliente ONG"}, headers=fun).json()["total"] == 2


# ------------------------------------------------------------------ sem DELETE nas demais rotas (DP-63)
@pytest.mark.parametrize("url", [O, f"{P}/1", P, f"{O}/1/situacao", f"{P}/1/situacao", f"{O}/1/contato"])
def test_nao_existe_delete_405(cliente, adm, url):
    # DP-63, UC01 FA2, UC06 FA2: so DELETE /organizacoes/{id} existe; as demais rotas seguem sem DELETE
    r = cliente.delete(url, headers=adm)
    assert r.status_code == 405, r.text
    assert len(_tab(cliente, "ORGANIZACAO")) == 4


def test_desativar_nao_apaga_parceria_nem_organizacao(cliente, adm):
    # DP-63 (desativar convive com excluir)
    d = _criar_org(cliente, adm, tipo="Empresa Doadora")
    p = _criar_parceiro(cliente, adm, d["id_organizacao"], "Empresa Doadora")
    cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Inativa"}, headers=adm)
    cliente.patch(f"{O}/{d['id_organizacao']}/situacao", json={"situacao": "Inativa"}, headers=adm)
    assert len(_tab(cliente, "PARCEIRO")) == 1 and len(_tab(cliente, "ORGANIZACAO")) == 5


# ------------------------------------------------------------------ excluir organizacao (DP-63)
def _sql_org(cliente, comando, params=()):
    con = sqlite3.connect(cliente.caminho_banco)
    con.execute("PRAGMA foreign_keys = ON")
    try:
        con.execute(comando, params)
        con.commit()
    finally:
        con.close()


def test_excluir_organizacao_sem_vinculos_204_remove_org_e_parceria(cliente, adm):
    # UC01, UC06, DP-63
    d = _criar_org(cliente, adm, tipo="Empresa Doadora")
    _criar_parceiro(cliente, adm, d["id_organizacao"], "Empresa Doadora")
    assert cliente.delete(f"{O}/{d['id_organizacao']}", headers=adm).status_code == 204
    assert cliente.get(f"{O}/{d['id_organizacao']}", headers=adm).status_code == 404
    assert len(_tab(cliente, "PARCEIRO")) == 0 and len(_tab(cliente, "ORGANIZACAO")) == 4


def test_excluir_organizacao_inexistente_404(cliente, adm):
    assert cliente.delete(f"{O}/9999", headers=adm).status_code == 404


@pytest.mark.parametrize("chave", ["func", "empresa", "ong", "doadora"])
def test_excluir_organizacao_so_administrador(cliente, token_de, chave):
    # RN01, DP-63
    r = cliente.delete(f"{O}/1", headers=_h(token_de(cliente, chave)))
    assert r.status_code == 403 and r.json()["codigo"] == "SEM_PERMISSAO"


def test_excluir_organizacao_sem_token_401(cliente):
    assert cliente.delete(f"{O}/1").status_code == 401


def test_excluir_organizacao_com_usuarios_exige_confirmacao(cliente, adm):
    # DP-63: 422 ORGANIZACAO_COM_USUARIOS com quantidade; nada removido
    r = cliente.delete(f"{O}/1", headers=adm)
    assert r.status_code == 422 and r.json()["codigo"] == "ORGANIZACAO_COM_USUARIOS"
    campos = r.json()["campos"]
    assert campos["quantidade_usuarios"] == 1 and len(campos["usuarios"]) == 1
    assert set(campos["usuarios"][0]) == {"id_usuario", "nome", "email", "perfil"}
    assert len(_tab(cliente, "ORGANIZACAO")) == 4 and len(_tab(cliente, "USUARIO")) == 6


def test_excluir_organizacao_com_ultimo_administrador_422_nada_removido(cliente, adm):
    # DP-65: admin vinculado à organização (situação forçada no SQL) e único -> bloqueia mesmo com a flag
    _sql_org(cliente, "UPDATE USUARIO SET id_organizacao=1 WHERE perfil='Administrador'")
    r = cliente.delete(f"{O}/1", params={"excluir_usuarios": "true"}, headers=adm)
    assert r.status_code == 422 and r.json()["codigo"] == "ALTERACAO_BLOQUEADA"
    assert len(_tab(cliente, "ORGANIZACAO")) == 4 and len(_tab(cliente, "USUARIO")) == 6


def test_excluir_organizacao_com_administrador_nao_ultimo_remove(cliente, adm):
    # DP-65: havendo outro Administrador fora da organização, a exclusão segue
    _sql_org(cliente, "INSERT INTO USUARIO (nome,email,senha_hash,perfil,id_organizacao) "
                      "SELECT 'Adm2','adm2@teste.com',senha_hash,'Administrador',1 FROM USUARIO WHERE perfil='Administrador' LIMIT 1")
    r = cliente.delete(f"{O}/1", params={"excluir_usuarios": "true"}, headers=adm)
    assert r.status_code == 204


def test_excluir_organizacao_com_flag_remove_usuarios_parceria_e_org(cliente, adm):
    # DP-63: transacao unica
    _criar_parceiro(cliente, adm, 1, "Patrocinador em Potencial")
    r = cliente.delete(f"{O}/1", params={"excluir_usuarios": "true"}, headers=adm)
    assert r.status_code == 204
    assert not _consulta(cliente, "SELECT 1 FROM ORGANIZACAO WHERE id_organizacao=1")
    assert not _consulta(cliente, "SELECT 1 FROM USUARIO WHERE id_organizacao=1")
    assert not _consulta(cliente, "SELECT 1 FROM PARCEIRO WHERE id_organizacao=1")
    assert len(_tab(cliente, "USUARIO")) == 5  # demais contas intactas


def test_token_de_usuario_removido_com_a_organizacao_da_401(cliente, adm, token_de):
    # DP-63/64: token de usuario apagado passa a 401
    t = token_de(cliente, "empresa")
    cliente.delete(f"{O}/1", params={"excluir_usuarios": "true"}, headers=adm)
    assert cliente.get("/api/v1/organizacao/usuarios", headers=_h(t)).status_code == 401


@pytest.mark.parametrize("tabela,sql,params", [
    ("SOLICITACAO", "INSERT INTO SOLICITACAO (id_organizacao_doadora, data_solicitacao, situacao) VALUES (3,'2026-01-01','Pendente')", ()),
    ("VENDA", "INSERT INTO VENDA (id_organizacao_cliente, data_venda, situacao, forma_pagamento) VALUES (%s,'2026-01-01','Pendente','Pix')", ()),
])
def test_excluir_organizacao_com_historico_422_mesmo_com_flag(cliente, adm, tabela, sql, params):
    # DP-63: ORGANIZACAO_EM_USO; nada removido; desativar continua valido
    id_org = 3 if tabela == "SOLICITACAO" else 1
    _sql_org(cliente, sql % id_org if "%s" in sql else sql)
    r = cliente.delete(f"{O}/{id_org}", params={"excluir_usuarios": "true"}, headers=adm)
    assert r.status_code == 422 and r.json()["codigo"] == "ORGANIZACAO_EM_USO"
    assert r.json()["mensagem"] == "Esta organização tem histórico e não pode ser excluída; você pode desativá-la"
    assert len(_tab(cliente, "ORGANIZACAO")) == 4 and len(_tab(cliente, "USUARIO")) == 6
    assert cliente.patch(f"{O}/{id_org}/situacao", json={"situacao": "Inativa"}, headers=adm).status_code == 200


def test_excluir_organizacao_com_doacao_422(cliente, adm):
    # DP-63: doacao recebida pela ONG (org 2) e historico (FK desligada so para semear o registro)
    con = sqlite3.connect(cliente.caminho_banco)
    con.execute("INSERT INTO DOACAO (id_equipamento, id_organizacao_ong, data_doacao) VALUES (1, 2, '2026-01-01')")
    con.commit()
    con.close()
    r = cliente.delete(f"{O}/2", params={"excluir_usuarios": "true"}, headers=adm)
    assert r.status_code == 422 and r.json()["codigo"] == "ORGANIZACAO_EM_USO"
    assert len(_tab(cliente, "ORGANIZACAO")) == 4


# ================================================================== PARCEIROS (UC06)
def test_tabela_parceiro_tem_so_4_colunas_sem_duplicar_dados_da_organizacao(cliente):
    # UC06 pos-condicao, RF10: modelo fisico intacto
    cols = [r["name"] for r in _consulta(cliente, "PRAGMA table_info(PARCEIRO)")]
    assert cols == ["id_parceiro", "id_organizacao", "tipo_parceria", "situacao_parceria"]


@pytest.mark.parametrize("tipo_org,atuacao", [("Empresa Doadora", "Empresa Doadora"),
                                              ("Empresa Doadora", "Patrocinador em Potencial"),
                                              ("Cliente Empresa", "Patrocinador em Potencial"),
                                              ("Cliente ONG", "Patrocinador em Potencial")])
def test_criar_parceiro_201_situacao_padrao_ativa_e_dados_por_juncao(cliente, adm, tipo_org, atuacao):
    # UC06 fluxo principal, RF10, RN10
    o = _criar_org(cliente, adm, tipo=tipo_org)
    r = cliente.post(P, json={"id_organizacao": o["id_organizacao"], "tipo_parceria": atuacao}, headers=adm)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["situacao_parceria"] == "Ativa" and d["tipo_parceria"] == atuacao
    assert d["id_organizacao"] == o["id_organizacao"] and isinstance(d["id_parceiro"], int)
    assert set(d) == {"id_parceiro", "id_organizacao", "tipo_parceria", "situacao_parceria", "nome_razao_social",
                      "cnpj", "telefone", "email", "endereco", "tipo_organizacao", "situacao_organizacao"}
    assert d["nome_razao_social"] == o["nome_razao_social"] and d["cnpj"] == o["cnpj"]
    assert d["tipo_organizacao"] == tipo_org and d["situacao_organizacao"] == "Ativa"
    assert cliente.get(f"{P}/{d['id_parceiro']}", headers=adm).json() == d
    assert cliente.get(f"{O}/{o['id_organizacao']}", headers=adm).json()["possui_parceria"] is True


def test_dados_da_organizacao_na_parceria_acompanham_alteracoes_da_organizacao(cliente, adm):
    # UC06 pos-condicao: sem duplicacao (junção)
    o = _criar_org(cliente, adm)
    p = _criar_parceiro(cliente, adm, o["id_organizacao"])
    cliente.patch(f"{O}/{o['id_organizacao']}/contato", json=_CONTATO, headers=adm)
    atual = cliente.get(f"{P}/{p['id_parceiro']}", headers=adm).json()
    assert atual["telefone"] == "2122223333" and atual["endereco"] == "Rua Nova, 9"
    assert len(_consulta(cliente, "SELECT * FROM PARCEIRO")[0].keys()) == 4


def test_criar_parceiro_com_situacao_inativa_explicita(cliente, adm):
    # UC06 passo 3
    o = _criar_org(cliente, adm)
    assert _criar_parceiro(cliente, adm, o["id_organizacao"], situacao_parceria="Inativa")["situacao_parceria"] == "Inativa"


def test_criar_parceiro_organizacao_inexistente_404(cliente, adm):
    # UC06 pre-condicao
    c = _erro(cliente.post(P, json={"id_organizacao": 9999, "tipo_parceria": "Patrocinador em Potencial"},
                           headers=adm), 404, "NAO_ENCONTRADO")
    assert "id_organizacao" in c["campos"]


def test_criar_parceiro_organizacao_inativa_422(cliente, adm):
    # UC06 FE3, DP-27
    antes = _tab(cliente, "PARCEIRO")
    c = _erro(cliente.post(P, json={"id_organizacao": 4, "tipo_parceria": "Patrocinador em Potencial"}, headers=adm),
              422, "ORGANIZACAO_INVALIDA")
    assert "id_organizacao" in c["campos"]
    assert _tab(cliente, "PARCEIRO") == antes


def test_criar_parceiro_duplicado_409(cliente, adm):
    # UC06 FE3, RF10: no maximo um vinculo por organizacao
    o = _criar_org(cliente, adm, tipo="Empresa Doadora")
    _criar_parceiro(cliente, adm, o["id_organizacao"], "Empresa Doadora")
    antes = _tab(cliente, "PARCEIRO")
    for atuacao in ("Empresa Doadora", "Patrocinador em Potencial"):
        _erro(cliente.post(P, json={"id_organizacao": o["id_organizacao"], "tipo_parceria": atuacao}, headers=adm),
              409, "PARCERIA_DUPLICADA")
    assert _tab(cliente, "PARCEIRO") == antes


def test_criar_parceiro_duplicado_mesmo_inativo_409(cliente, adm):
    # RF10 (UNIQUE em qualquer situacao)
    o = _criar_org(cliente, adm)
    _criar_parceiro(cliente, adm, o["id_organizacao"], situacao_parceria="Inativa")
    _erro(cliente.post(P, json={"id_organizacao": o["id_organizacao"], "tipo_parceria": "Patrocinador em Potencial"},
                       headers=adm), 409, "PARCERIA_DUPLICADA")


@pytest.mark.parametrize("tipo_org", ["Cliente Empresa", "Cliente ONG"])
def test_empresa_doadora_com_organizacao_de_outro_tipo_422(cliente, adm, tipo_org):
    # UC06 FE2, RN10
    o = _criar_org(cliente, adm, tipo=tipo_org)
    antes = _tab(cliente, "PARCEIRO")
    c = _erro(cliente.post(P, json={"id_organizacao": o["id_organizacao"], "tipo_parceria": "Empresa Doadora"},
                           headers=adm), 422, "ATUACAO_INCOMPATIVEL")
    assert "tipo_parceria" in c["campos"]
    assert _tab(cliente, "PARCEIRO") == antes


def test_ordem_de_validacao_no_post_parceiros(cliente, adm):
    # contrato, esclarecimento 4: 404 -> 422 inativa -> 409 duplicada -> 422 atuacao
    # inativa + atuacao incompativel (org 4 e Cliente Empresa) -> ORGANIZACAO_INVALIDA
    _erro(cliente.post(P, json={"id_organizacao": 4, "tipo_parceria": "Empresa Doadora"}, headers=adm),
          422, "ORGANIZACAO_INVALIDA")
    # duplicada + atuacao incompativel -> PARCERIA_DUPLICADA
    o = _criar_org(cliente, adm, tipo="Cliente Empresa")
    _criar_parceiro(cliente, adm, o["id_organizacao"], "Patrocinador em Potencial")
    _erro(cliente.post(P, json={"id_organizacao": o["id_organizacao"], "tipo_parceria": "Empresa Doadora"},
                       headers=adm), 409, "PARCERIA_DUPLICADA")
    # inexistente -> 404 (antes de qualquer outra)
    _erro(cliente.post(P, json={"id_organizacao": 9999, "tipo_parceria": "Empresa Doadora"}, headers=adm),
          404, "NAO_ENCONTRADO")


@pytest.mark.parametrize("corpo", [{}, {"tipo_parceria": "Patrocinador em Potencial"}, {"id_organizacao": 1},
                                   {"id_organizacao": 1, "tipo_parceria": "Cliente Empresa"},
                                   {"id_organizacao": 1, "tipo_parceria": "Empresa Doadora", "situacao_parceria": "ativa"},
                                   {"id_organizacao": "abc", "tipo_parceria": "Empresa Doadora"}])
def test_criar_parceiro_corpo_invalido_400(cliente, adm, corpo):
    # UC06 FE1
    antes = _tab(cliente, "PARCEIRO")
    c = _erro(cliente.post(P, json=corpo, headers=adm), 400, "DADOS_INVALIDOS")
    assert c["campos"]
    assert _tab(cliente, "PARCEIRO") == antes


def test_obter_parceiro_inexistente_404(cliente, adm):
    # UC06 FA1
    _erro(cliente.get(f"{P}/9999", headers=adm), 404, "NAO_ENCONTRADO")


def test_put_parceiro_altera_so_tipo_parceria_com_revalidacao(cliente, adm):
    # UC06 FA1, FE2
    o = _criar_org(cliente, adm, tipo="Empresa Doadora")
    p = _criar_parceiro(cliente, adm, o["id_organizacao"], "Empresa Doadora", situacao_parceria="Inativa")
    r = cliente.put(f"{P}/{p['id_parceiro']}", json={"tipo_parceria": "Patrocinador em Potencial"}, headers=adm)
    assert r.status_code == 200, r.text
    assert r.json()["tipo_parceria"] == "Patrocinador em Potencial" and r.json()["situacao_parceria"] == "Inativa"
    r = cliente.put(f"{P}/{p['id_parceiro']}", json={"tipo_parceria": "Empresa Doadora"}, headers=adm)
    assert r.status_code == 200 and r.json()["tipo_parceria"] == "Empresa Doadora"


def test_put_parceiro_empresa_doadora_em_organizacao_incompativel_422(cliente, adm):
    # UC06 FE2, RN10
    o = _criar_org(cliente, adm, tipo="Cliente ONG")
    p = _criar_parceiro(cliente, adm, o["id_organizacao"], "Patrocinador em Potencial")
    antes = _tab(cliente, "PARCEIRO")
    c = _erro(cliente.put(f"{P}/{p['id_parceiro']}", json={"tipo_parceria": "Empresa Doadora"}, headers=adm),
              422, "ATUACAO_INCOMPATIVEL")
    assert "tipo_parceria" in c["campos"]
    assert _tab(cliente, "PARCEIRO") == antes


def test_put_parceiro_nao_troca_organizacao_nem_situacao(cliente, adm):
    # DP-27
    a = _criar_org(cliente, adm)
    b = _criar_org(cliente, adm)
    p = _criar_parceiro(cliente, adm, a["id_organizacao"])
    r = cliente.put(f"{P}/{p['id_parceiro']}", json={"tipo_parceria": "Patrocinador em Potencial",
                                                     "id_organizacao": b["id_organizacao"],
                                                     "situacao_parceria": "Inativa"}, headers=adm)
    assert r.status_code == 200
    assert r.json()["id_organizacao"] == a["id_organizacao"] and r.json()["situacao_parceria"] == "Ativa"
    assert _consulta(cliente, "SELECT id_organizacao FROM PARCEIRO WHERE id_parceiro=?",
                     (p["id_parceiro"],))[0][0] == a["id_organizacao"]


def test_put_parceiro_404_400_e_ordem(cliente, adm):
    # esclarecimento 1
    _erro(cliente.put(f"{P}/9999", json={"tipo_parceria": "Patrocinador em Potencial"}, headers=adm),
          404, "NAO_ENCONTRADO")
    _erro(cliente.put(f"{P}/9999", json={"tipo_parceria": "Outro"}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(cliente.put(f"{P}/9999", json={}, headers=adm), 400, "DADOS_INVALIDOS")


def test_desativar_e_reativar_parceria_preserva_vinculo(cliente, adm):
    # UC06 FA2, RN10
    o = _criar_org(cliente, adm, tipo="Empresa Doadora")
    p = _criar_parceiro(cliente, adm, o["id_organizacao"], "Empresa Doadora")
    r = cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Inativa"}, headers=adm)
    assert r.status_code == 200 and r.json()["situacao_parceria"] == "Inativa"
    assert r.json()["tipo_parceria"] == "Empresa Doadora" and len(_tab(cliente, "PARCEIRO")) == 1
    r = cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Ativa"}, headers=adm)
    assert r.status_code == 200 and r.json()["situacao_parceria"] == "Ativa"


def test_situacao_parceria_idempotente(cliente, adm):
    # contrato
    o = _criar_org(cliente, adm)
    p = _criar_parceiro(cliente, adm, o["id_organizacao"])
    for v in ("Ativa", "Ativa", "Inativa", "Inativa"):
        r = cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": v}, headers=adm)
        assert r.status_code == 200 and r.json()["situacao_parceria"] == v


def test_reativar_parceria_com_organizacao_inativa_422(cliente, adm):
    # UC06 FE3, DP-27
    o = _criar_org(cliente, adm)
    p = _criar_parceiro(cliente, adm, o["id_organizacao"])
    cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Inativa"}, headers=adm)
    cliente.patch(f"{O}/{o['id_organizacao']}/situacao", json={"situacao": "Inativa"}, headers=adm)
    c = _erro(cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Ativa"}, headers=adm),
              422, "ORGANIZACAO_INVALIDA")
    assert c["campos"]
    assert cliente.get(f"{P}/{p['id_parceiro']}", headers=adm).json()["situacao_parceria"] == "Inativa"
    # reativando a organizacao, a parceria pode ser reativada
    cliente.patch(f"{O}/{o['id_organizacao']}/situacao", json={"situacao": "Ativa"}, headers=adm)
    r = cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Ativa"}, headers=adm)
    assert r.status_code == 200 and r.json()["situacao_parceria"] == "Ativa"


def test_repetir_ativa_com_organizacao_inativa_e_idempotente_200(cliente, adm):
    # esclarecimento 3
    o = _criar_org(cliente, adm)
    p = _criar_parceiro(cliente, adm, o["id_organizacao"])
    cliente.patch(f"{O}/{o['id_organizacao']}/situacao", json={"situacao": "Inativa"}, headers=adm)
    r = cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Ativa"}, headers=adm)
    assert r.status_code == 200 and r.json()["situacao_parceria"] == "Ativa"


def test_desativar_parceria_com_organizacao_inativa_permitido(cliente, adm):
    # esclarecimento 3: so a transicao Inativa -> Ativa checa a organizacao
    o = _criar_org(cliente, adm)
    p = _criar_parceiro(cliente, adm, o["id_organizacao"])
    cliente.patch(f"{O}/{o['id_organizacao']}/situacao", json={"situacao": "Inativa"}, headers=adm)
    r = cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": "Inativa"}, headers=adm)
    assert r.status_code == 200 and r.json()["situacao_parceria"] == "Inativa"


@pytest.mark.parametrize("valor", ["ativa", "Outra", "", None])
def test_situacao_parceria_invalida_400(cliente, adm, valor):
    # DP-27
    o = _criar_org(cliente, adm)
    p = _criar_parceiro(cliente, adm, o["id_organizacao"])
    c = _erro(cliente.patch(f"{P}/{p['id_parceiro']}/situacao", json={"situacao_parceria": valor}, headers=adm),
              400, "DADOS_INVALIDOS")
    assert "situacao_parceria" in c["campos"]


def test_situacao_parceria_404(cliente, adm):
    # contrato
    _erro(cliente.patch(f"{P}/9999/situacao", json={"situacao_parceria": "Inativa"}, headers=adm),
          404, "NAO_ENCONTRADO")


def _popular_parceiros(cliente, adm):
    a = _criar_org(cliente, adm, nome_razao_social="Alfa Doadora", cnpj="11.111.111/0001-11", tipo="Empresa Doadora")
    b = _criar_org(cliente, adm, nome_razao_social="Beta Patrocinio", cnpj="22222222000122", tipo="Cliente Empresa")
    c = _criar_org(cliente, adm, nome_razao_social="Gama ONG", cnpj="33333333000133", tipo="Cliente ONG")
    _criar_parceiro(cliente, adm, a["id_organizacao"], "Empresa Doadora")
    _criar_parceiro(cliente, adm, b["id_organizacao"], "Patrocinador em Potencial", situacao_parceria="Inativa")
    _criar_parceiro(cliente, adm, c["id_organizacao"], "Patrocinador em Potencial")


def test_listar_parceiros_formato_e_ordenacao(cliente, adm):
    # UC06 FA1
    _popular_parceiros(cliente, adm)
    d = cliente.get(P, headers=adm).json()
    assert set(d) == {"items", "total", "page", "size"} and d["total"] == 3 and d["size"] == 20
    assert [i["nome_razao_social"] for i in d["items"]] == ["Alfa Doadora", "Beta Patrocinio", "Gama ONG"]
    assert all("tipo_organizacao" in i and "cnpj" in i for i in d["items"])


def test_listar_parceiros_paginacao(cliente, adm):
    # UC06 FA1
    _popular_parceiros(cliente, adm)
    d = cliente.get(f"{P}?page=2&size=2", headers=adm).json()
    assert d["total"] == 3 and len(d["items"]) == 1 and d["page"] == 2 and d["size"] == 2
    assert cliente.get(f"{P}?size=100", headers=adm).status_code == 200


@pytest.mark.parametrize("qs", ["size=101", "size=0", "page=0", "tipo_parceria=Outra", "situacao_parceria=ativa"])
def test_listar_parceiros_parametros_invalidos_400(cliente, adm, qs):
    # contrato
    _erro(cliente.get(f"{P}?{qs}", headers=adm), 400, "DADOS_INVALIDOS")


def test_listar_parceiros_filtros(cliente, adm):
    # UC06 FA1
    _popular_parceiros(cliente, adm)
    g = lambda **p: cliente.get(P, params=p, headers=adm).json()  # noqa: E731
    assert g(tipo_parceria="Empresa Doadora")["total"] == 1
    assert g(tipo_parceria="Patrocinador em Potencial")["total"] == 2
    assert g(situacao_parceria="Inativa")["total"] == 1
    assert g(situacao_parceria="Ativa")["total"] == 2
    assert g(tipo_parceria="Patrocinador em Potencial", situacao_parceria="Ativa")["items"][0][
        "nome_razao_social"] == "Gama ONG"
    assert [i["nome_razao_social"] for i in g(q="BETA")["items"]] == ["Beta Patrocinio"]
    for q in ("33333333000133", "33.333.333/0001-33", "33.333"):
        assert [i["nome_razao_social"] for i in g(q=q)["items"]] == ["Gama ONG"], q
    assert g(q="nada")["total"] == 0
    _erro(cliente.get(P, params={"q": "a" * 151}, headers=adm), 400, "DADOS_INVALIDOS")
