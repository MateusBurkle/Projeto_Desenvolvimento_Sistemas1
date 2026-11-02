"""Testes da API do Modulo 4 (Solicitacoes e doacoes): UC09, UC10, UC11, UC19, UC20.
Requisitos: RF04, RF05, RF10, RF11, RF12, RF15, RF21; RN03, RN04, RN05, RN10, RN11, RN12, RN15, RN21; RNF04, RNF05.
Contrato: contratos/modulo-4.yaml v1.0.0 (inclui esclarecimentos); DP-40 a DP-44 (e DP-52, aberta). Contas ficticias do conftest.
Semeado pelo conftest: orgs 1 (Cliente Empresa), 2 (Cliente ONG Ativa), 3 (Empresa Doadora Ativa), 4 (Cliente Empresa INATIVA).
A fixture `cliente` NAO cria o vinculo de parceria; a fixture `c` (usada na maioria dos testes) cria o da org 3 (RN10).
Categorias base 1..6 (2 = Notebooks)."""
import sqlite3
from datetime import date, timedelta

import pytest

from tests.conftest import SENHA

S = "/api/v1/solicitacoes"
D = "/api/v1/doacoes"
E = "/api/v1/equipamentos"
CAT = "/api/v1/categorias"
HOJE = date.today()
ISO = HOJE.isoformat()
RECEBIMENTO = (HOJE - timedelta(days=10)).isoformat()
ORG_DOADORA = 3
ONG_ATIVA = 2
GRANDE = 10 ** 20
CHAVES = ["admin", "func", "empresa", "ong", "doadora"]


# ------------------------------------------------------------------ utilitarios
def _h(token):
    return {"Authorization": f"Bearer {token}"}


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


def _situacao_sol(cliente, id_sol):
    return _consulta(cliente, "SELECT situacao FROM SOLICITACAO WHERE id_solicitacao=?", (id_sol,))[0][0]


def _situacao_eq(cliente, id_eq):
    return _consulta(cliente, "SELECT situacao FROM EQUIPAMENTO WHERE id_equipamento=?", (id_eq,))[0][0]


@pytest.fixture()
def c(cliente):
    """cliente + vinculo de parceria Ativa 'Empresa Doadora' da org 3 (RN10, UC09 pre-condicao)."""
    _sql(cliente, "INSERT INTO PARCEIRO (id_organizacao, tipo_parceria, situacao_parceria) VALUES (?, 'Empresa Doadora', 'Ativa')",
         (ORG_DOADORA,))
    return cliente


@pytest.fixture()
def adm(c, token_de):
    return _h(token_de(c, "admin"))


@pytest.fixture()
def fun(c, token_de):
    return _h(token_de(c, "func"))


@pytest.fixture()
def doa(c, token_de):
    return _h(token_de(c, "doadora"))


@pytest.fixture()
def ong(c, token_de):
    return _h(token_de(c, "ong"))


@pytest.fixture()
def nova_conta(hash_senha):
    """Cria organizacao + usuario e devolve (id_organizacao, cabecalhos). Parceria ativa opcional (so Empresa Doadora)."""
    contador = [0]

    def _criar(cliente, perfil, nome, situacao="Ativa", parceria=None):
        contador[0] += 1
        n = 100 + contador[0] + sum(ord(ch) for ch in nome)
        id_org = _sql(cliente, "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao)"
                               " VALUES (?,?,?,?,?,?,?)",
                      (f"{n:014d}", nome, perfil, "11999999999", f"o{n}@org.com", "Rua Y, 2", "Ativa"))
        email = f"u{n}@teste.com"
        _sql(cliente, "INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (?,?,?,?,?)",
             (id_org, email, perfil, hash_senha, f"Nome {nome}"))
        if parceria:
            _sql(cliente, "INSERT INTO PARCEIRO (id_organizacao, tipo_parceria, situacao_parceria) VALUES (?,?,?)",
                 (id_org, "Empresa Doadora", parceria))
        r = cliente.post("/api/v1/auth/login", json={"email": email, "senha": SENHA})
        assert r.status_code == 200, r.text
        if situacao != "Ativa":  # inativada depois do login (organizacao inativa nao autentica)
            _sql(cliente, "UPDATE ORGANIZACAO SET situacao=? WHERE id_organizacao=?", (situacao, id_org))
        return id_org, _h(r.json()["access_token"])
    return _criar


_seq = [0]


def _ident():
    _seq[0] += 1
    return f"AV-{_seq[0]:05d}"


def _criar_sol(c, h, itens=None):
    itens = itens or [{"tipo": "Notebook", "modelo": "Dell Latitude 5420", "quantidade": 1}]
    r = c.post(S, json={"itens": itens}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _corpo_av(**kw):
    base = {"identificacao": _ident(), "id_categoria": 2, "condicao": "Bom", "data_recebimento": RECEBIMENTO, "valor": 1500.0}
    base.update(kw)
    return base


def _avaliar(c, h, sol, indice=0, **kw):
    """Cadastra uma unidade avaliada no item `indice` (UC10 passo 3, DP-41)."""
    id_item = sol["itens"][indice]["id_item_solicitacao"]
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{id_item}/equipamentos", json=_corpo_av(**kw), headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _destinar(c, h, sol, eq, destinacao, **kw):
    corpo = {"destinacao": destinacao, **kw}
    return c.put(f"{S}/{sol['id_solicitacao']}/equipamentos/{eq['id_equipamento']}/destinacao", json=corpo, headers=h)


def _doar(c, h, sol, eq, ong_id=ONG_ATIVA, data=None):
    r = _destinar(c, h, sol, eq, "Doação", id_organizacao_ong=ong_id, data_doacao=data or ISO)
    assert r.status_code == 200, r.text
    return r.json()


def _obter(c, h, id_sol):
    r = c.get(f"{S}/{id_sol}", headers=h)
    assert r.status_code == 200, r.text
    return r.json()


def _item_do_equip(sol_json, id_eq):
    for it in sol_json["itens"]:
        for e in it["equipamentos"]:
            if e["id_equipamento"] == id_eq:
                return e
    raise AssertionError("equipamento fora da solicitacao")


# ------------------------------------------------------------------ rotas e matriz de permissoes (RN03, RN04, RN05, RN15, RNF05)
def _rotas():
    """(metodo, caminho, corpo, perfis autorizados). Corpos validos: a permissao e o unico motivo de recusa."""
    av = {"identificacao": "X-1", "id_categoria": 2, "condicao": "Bom", "data_recebimento": "2026-01-01"}
    return [
        ("GET", S, None, {"admin", "func", "doadora"}),
        ("POST", S, {"itens": [{"tipo": "Notebook", "modelo": "M", "quantidade": 1}]}, {"doadora"}),
        ("GET", f"{S}/9999", None, {"admin", "func", "doadora"}),
        ("POST", f"{S}/9999/itens/9999/equipamentos", av, {"admin", "func"}),
        ("PUT", f"{S}/9999/equipamentos/9999/destinacao", {"destinacao": "Reciclagem"}, {"admin", "func"}),
        ("GET", f"{D}/ongs-elegiveis", None, {"admin", "func"}),
        ("GET", D, None, {"admin", "func", "ong"}),
        ("GET", f"{D}/9999", None, {"admin", "func", "ong"}),
    ]


@pytest.mark.parametrize("indice", range(8))
def test_sem_token_401_em_todas_as_rotas(cliente, indice):
    # RNF05
    metodo, url, corpo, _ = _rotas()[indice]
    _erro(cliente.request(metodo, url, json=corpo), 401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("indice", range(8))
def test_token_invalido_401_em_todas_as_rotas(cliente, indice):
    # RNF05
    metodo, url, corpo, _ = _rotas()[indice]
    _erro(cliente.request(metodo, url, json=corpo, headers=_h("token.invalido.xyz")), 401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("chave", CHAVES)
@pytest.mark.parametrize("indice", range(8))
def test_matriz_de_permissoes_por_rota_e_perfil(c, token_de, chave, indice):
    # RN03, RN04, RN05, RN15, UC09, UC10, UC11, UC19, UC20: autorizado nao recebe 401/403; proibido recebe 403 SEM_PERMISSAO
    metodo, url, corpo, autorizados = _rotas()[indice]
    r = c.request(metodo, url, json=corpo, headers=_h(token_de(c, chave)))
    if chave in autorizados:
        assert r.status_code not in (401, 403), f"{metodo} {url} {chave}: {r.status_code} {r.text}"
    else:
        _erro(r, 403, "SEM_PERMISSAO")


@pytest.mark.parametrize("chave", ["empresa", "ong"])
def test_perfis_sem_acesso_a_solicitacoes_nada_gravado(c, token_de, chave):
    # RN05, RN04, RNF05: Cliente Empresa e Cliente ONG nao criam nem leem solicitacoes
    antes = (_tab(c, "SOLICITACAO"), _tab(c, "ITEM_SOLICITACAO"), _tab(c, "EQUIPAMENTO"))
    h = _h(token_de(c, chave))
    corpo = {"itens": [{"tipo": "Notebook", "modelo": "M", "quantidade": 1}]}
    _erro(c.post(S, json=corpo, headers=h), 403, "SEM_PERMISSAO")
    _erro(c.get(S, headers=h), 403, "SEM_PERMISSAO")
    assert (_tab(c, "SOLICITACAO"), _tab(c, "ITEM_SOLICITACAO"), _tab(c, "EQUIPAMENTO")) == antes


@pytest.mark.parametrize("chave", ["admin", "func"])
def test_administrador_e_funcionario_nao_criam_solicitacao(c, token_de, chave):
    # UC09 ator Empresa Doadora, RN05: LEAF TI avalia, nao solicita
    _erro(c.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=_h(token_de(c, chave))),
          403, "SEM_PERMISSAO")
    assert _tab(c, "SOLICITACAO") == []


def test_doadora_nao_avalia_nem_destina_e_nada_muda(c, doa, adm):
    # UC10 ator Administrador/Funcionario, RN03, RN05, RN21
    sol = _criar_sol(c, doa)
    eq = _avaliar(c, adm, sol)
    antes = (_tab(c, "EQUIPAMENTO"), _tab(c, "DOACAO"), _situacao_sol(c, sol["id_solicitacao"]))
    id_item = sol["itens"][0]["id_item_solicitacao"]
    _erro(c.post(f"{S}/{sol['id_solicitacao']}/itens/{id_item}/equipamentos", json=_corpo_av(), headers=doa), 403, "SEM_PERMISSAO")
    _erro(_destinar(c, doa, sol, eq, "Venda"), 403, "SEM_PERMISSAO")
    assert (_tab(c, "EQUIPAMENTO"), _tab(c, "DOACAO"), _situacao_sol(c, sol["id_solicitacao"])) == antes


def test_funcionario_avalia_e_destina(c, doa, fun):
    # UC10, RN03: Funcionario tem o mesmo acesso do Administrador nesta rota
    sol = _criar_sol(c, doa)
    eq = _avaliar(c, fun, sol)
    r = _destinar(c, fun, sol, eq, "Venda")
    assert r.status_code == 200 and r.json()["situacao"] == "Avaliada"


def test_ong_nao_ve_solicitacoes_nem_ongs_elegiveis(c, ong):
    # RN04, RN15
    _erro(c.get(f"{D}/ongs-elegiveis", headers=ong), 403, "SEM_PERMISSAO")
    _erro(c.get(f"{S}/1", headers=ong), 403, "SEM_PERMISSAO")


def test_doadora_nao_ve_doacoes(c, doa):
    # RN05, RN15: Empresa Doadora nao consulta doacoes de ONG
    _erro(c.get(D, headers=doa), 403, "SEM_PERMISSAO")
    _erro(c.get(f"{D}/1", headers=doa), 403, "SEM_PERMISSAO")


# ------------------------------------------------------------------ UC09 fluxo principal (RF05, RF21, RN05, RN11, RN21)
def test_uc09_criar_solicitacao_201_com_formato_do_contrato(c, doa):
    # UC09 passos 3-5, RN05, RN11
    r = c.post(S, json={"itens": [{"tipo": "Notebook", "modelo": "Dell Latitude 5420", "quantidade": 10},
                                  {"tipo": "Monitor", "modelo": "LG 24", "quantidade": 3}]}, headers=doa)
    assert r.status_code == 201, r.text
    s = r.json()
    assert set(s) == {"id_solicitacao", "id_organizacao_doadora", "nome_organizacao", "data_solicitacao", "situacao",
                      "pendencias", "itens"}
    assert s["situacao"] == "Aguardando avaliação" and s["data_solicitacao"] == ISO
    assert s["id_organizacao_doadora"] == ORG_DOADORA and s["nome_organizacao"] == "Doadora SA"
    assert [(i["tipo"], i["modelo"], i["quantidade"]) for i in s["itens"]] == [
        ("Notebook", "Dell Latitude 5420", 10), ("Monitor", "LG 24", 3)]
    for i in s["itens"]:
        assert i["equipamentos"] == [] and i["quantidade_cadastrada"] == 0 and i["quantidade_avaliada"] == 0
        assert i["avaliado"] is False
    linhas = _consulta(c, "SELECT * FROM ITEM_SOLICITACAO WHERE id_solicitacao=?", (s["id_solicitacao"],))
    assert len(linhas) == 2


def test_uc09_organizacao_vem_do_token_nunca_do_corpo(c, doa, nova_conta):
    # UC09 passo 4, RN05, RN04: id_organizacao_doadora no corpo e ignorado
    outra, _ = nova_conta(c, "Empresa Doadora", "Outra Doadora", parceria="Ativa")
    r = c.post(S, json={"id_organizacao_doadora": outra, "itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=doa)
    assert r.status_code == 201, r.text
    assert r.json()["id_organizacao_doadora"] == ORG_DOADORA
    assert _consulta(c, "SELECT id_organizacao_doadora FROM SOLICITACAO")[0][0] == ORG_DOADORA


def test_uc09_registro_nao_disponibiliza_nada_no_catalogo(c, doa):
    # UC09, RN21: nenhum equipamento e criado pela solicitacao
    _criar_sol(c, doa, [{"tipo": "Notebook", "modelo": "M", "quantidade": 5}])
    assert _tab(c, "EQUIPAMENTO") == [] and _tab(c, "DOACAO") == []


def test_uc09_textos_sao_aparados(c, doa):
    # UC09 FE1 / contrato: texto sem espacos nas pontas
    s = _criar_sol(c, doa, [{"tipo": "  Notebook  ", "modelo": " Dell ", "quantidade": 2}])
    assert s["itens"][0]["tipo"] == "Notebook" and s["itens"][0]["modelo"] == "Dell"


def test_uc09_limites_validos_aceitos(c, doa):
    # UC09 FE1 (limites): 100 caracteres, quantidade 1 e 9999, 50 itens
    s = _criar_sol(c, doa, [{"tipo": "T" * 100, "modelo": "M" * 100, "quantidade": 1},
                            {"tipo": "x", "modelo": "y", "quantidade": 9999}])
    assert len(s["itens"]) == 2
    s50 = _criar_sol(c, doa, [{"tipo": f"t{i}", "modelo": "m", "quantidade": 1} for i in range(50)])
    assert len(s50["itens"]) == 50


def test_uc09_mesma_empresa_pode_criar_varias_solicitacoes(c, doa):
    # UC09: sem unicidade por organizacao
    a, b = _criar_sol(c, doa), _criar_sol(c, doa)
    assert a["id_solicitacao"] != b["id_solicitacao"]


@pytest.mark.parametrize("corpo,campo", [
    ({}, "itens"),
    ({"itens": []}, "itens"),
    ({"itens": "x"}, "itens"),
    ({"itens": [{"tipo": "N", "modelo": "M"}]}, "quantidade"),
    ({"itens": [{"modelo": "M", "quantidade": 1}]}, "tipo"),
    ({"itens": [{"tipo": "N", "quantidade": 1}]}, "modelo"),
    ({"itens": [{"tipo": "", "modelo": "M", "quantidade": 1}]}, "tipo"),
    ({"itens": [{"tipo": "   ", "modelo": "M", "quantidade": 1}]}, "tipo"),
    ({"itens": [{"tipo": "T" * 101, "modelo": "M", "quantidade": 1}]}, "tipo"),
    ({"itens": [{"tipo": "N", "modelo": "", "quantidade": 1}]}, "modelo"),
    ({"itens": [{"tipo": "N", "modelo": "M" * 101, "quantidade": 1}]}, "modelo"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": 0}]}, "quantidade"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": -3}]}, "quantidade"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": 10000}]}, "quantidade"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1.5}]}, "quantidade"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": "5"}]}, "quantidade"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": True}]}, "quantidade"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": None}]}, "quantidade"),
    ({"itens": [{"tipo": 7, "modelo": "M", "quantidade": 1}]}, "tipo"),
    ({"itens": [None]}, "*"),
    ({"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}] * 51}, "itens"),
])
def test_uc09_fe1_dados_invalidos_400_e_nada_gravado(c, doa, corpo, campo):
    # UC09 FE1, RNF04: o sistema nao registra a solicitacao; campos indica o problema
    r = c.post(S, json=corpo, headers=doa)
    e = _erro(r, 400, "DADOS_INVALIDOS")
    assert e["campos"] if campo == "*" else campo in e["campos"], e
    assert _tab(c, "SOLICITACAO") == [] and _tab(c, "ITEM_SOLICITACAO") == []


def test_uc09_fe1_um_item_invalido_nao_grava_os_validos(c, doa):
    # UC09 FE1: tudo ou nada na mesma transacao
    corpo = {"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}, {"tipo": "N", "modelo": "M", "quantidade": 0}]}
    _erro(c.post(S, json=corpo, headers=doa), 400, "DADOS_INVALIDOS")
    assert _tab(c, "SOLICITACAO") == [] and _tab(c, "ITEM_SOLICITACAO") == []


def test_uc09_fe1_json_invalido_e_corpo_ausente(c, doa):
    # UC09 FE1, RNF04
    r = c.post(S, content="{nao e json", headers={**doa, "Content-Type": "application/json"})
    _erro(r, 400, "DADOS_INVALIDOS")
    _erro(c.post(S, headers=doa), 400, "DADOS_INVALIDOS")
    assert _tab(c, "SOLICITACAO") == []


# ------------------------------------------------------------------ UC09 FE2/FE3 (RN05, RN10)
def test_uc09_fe3_sem_parceria_422_parceria_inativa(cliente, token_de):
    # UC09 FE3, RN10: sem vinculo de parceria, nada e registrado
    h = _h(token_de(cliente, "doadora"))
    e = _erro(cliente.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=h), 422, "PARCERIA_INATIVA")
    assert "parceria" in e["mensagem"].lower()
    assert _tab(cliente, "SOLICITACAO") == [] and _tab(cliente, "ITEM_SOLICITACAO") == []


def test_uc09_fe3_parceria_desativada_422(c, doa):
    # UC09 FE3, RN10
    _sql(c, "UPDATE PARCEIRO SET situacao_parceria='Inativa' WHERE id_organizacao=?", (ORG_DOADORA,))
    _erro(c.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=doa), 422, "PARCERIA_INATIVA")
    assert _tab(c, "SOLICITACAO") == []


def test_uc09_fe3_parceria_de_patrocinador_nao_basta(c, doa):
    # UC09 FE3, RN10: somente atuacao Empresa Doadora autoriza a solicitacao
    _sql(c, "UPDATE PARCEIRO SET tipo_parceria='Patrocinador em Potencial' WHERE id_organizacao=?", (ORG_DOADORA,))
    _erro(c.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=doa), 422, "PARCERIA_INATIVA")
    assert _tab(c, "SOLICITACAO") == []


def test_uc09_fe3_reativar_parceria_libera_novas_solicitacoes(c, doa):
    # UC09 FE3, RN10
    _sql(c, "UPDATE PARCEIRO SET situacao_parceria='Inativa'")
    _erro(c.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=doa), 422, "PARCERIA_INATIVA")
    _sql(c, "UPDATE PARCEIRO SET situacao_parceria='Ativa'")
    assert c.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=doa).status_code == 201


def test_rn10_desativar_parceria_preserva_solicitacoes_existentes(c, doa, adm):
    # RN10: "A desativacao da parceria preserva as solicitacoes ja registradas e impede novas"
    sol = _criar_sol(c, doa)
    _sql(c, "UPDATE PARCEIRO SET situacao_parceria='Inativa'")
    assert _obter(c, doa, sol["id_solicitacao"])["situacao"] == "Aguardando avaliação"
    assert c.get(S, headers=doa).json()["total"] == 1
    # a LEAF TI ainda consegue avaliar a solicitacao ja registrada
    assert c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos",
                  json=_corpo_av(), headers=adm).status_code == 201
    _erro(c.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=doa), 422, "PARCERIA_INATIVA")


def test_uc09_fe3_parceria_de_outra_organizacao_nao_vale(cliente, token_de, nova_conta):
    # UC09 FE3, RN10: o vinculo e verificado pela organizacao do token
    nova_conta(cliente, "Empresa Doadora", "Doadora Parceira", parceria="Ativa")
    h = _h(token_de(cliente, "doadora"))  # org 3 continua sem parceria
    _erro(cliente.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=h), 422, "PARCERIA_INATIVA")


def test_uc09_fe2_organizacao_inativa_barrada_com_403_conta_inativa(c, doa):
    # UC09 FE2, RN05, RN09: esclarecimento 4 do contrato - a conta de organizacao inativa recebe 403 CONTA_INATIVA
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ORG_DOADORA,))
    _erro(c.post(S, json={"itens": [{"tipo": "N", "modelo": "M", "quantidade": 1}]}, headers=doa), 403, "CONTA_INATIVA")
    _erro(c.get(S, headers=doa), 403, "CONTA_INATIVA")
    assert _tab(c, "SOLICITACAO") == []


def test_uc09_fe2_service_defende_com_422_organizacao_inativa(c):
    # UC09 FE2, RN05: o 422 permanece no service como defesa (esclarecimento 4)
    from app.db import get_conexao  # noqa: F401
    from app.erros import ErroApi
    from app.solicitacoes import schemas, service
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ORG_DOADORA,))
    con = sqlite3.connect(c.caminho_banco)
    con.row_factory = sqlite3.Row
    try:
        dados = schemas.SolicitacaoEntrada(itens=[{"tipo": "N", "modelo": "M", "quantidade": 1}])
        with pytest.raises(ErroApi) as exc:
            service.criar(con, {"perfil": "Empresa Doadora", "id_organizacao": ORG_DOADORA}, dados)
        assert exc.value.status == 422 and exc.value.codigo == "ORGANIZACAO_INATIVA"
    finally:
        con.close()
    assert _tab(c, "SOLICITACAO") == []


def test_uc09_ordem_400_antes_de_422(cliente, token_de):
    # contrato: ordem 400 -> 422 ORGANIZACAO_INATIVA -> 422 PARCERIA_INATIVA
    h = _h(token_de(cliente, "doadora"))  # sem parceria
    _erro(cliente.post(S, json={"itens": []}, headers=h), 400, "DADOS_INVALIDOS")


# ------------------------------------------------------------------ UC09 FA1 / UC20: consulta (RN04, RN05, RNF05)
def test_uc20_consultar_solicitacao_propria_sem_avaliacao_nao_inventa(c, doa):
    # UC20 FA1, UC09 FA1: pendente, sem condicao nem destinacao inventadas
    sol = _criar_sol(c, doa)
    s = _obter(c, doa, sol["id_solicitacao"])
    assert s["situacao"] == "Aguardando avaliação"
    assert s["itens"][0]["equipamentos"] == [] and s["itens"][0]["avaliado"] is False
    assert s["pendencias"], "deve informar o que falta"


def test_uc20_solicitacao_de_outra_empresa_404_sem_vazar(c, doa, nova_conta):
    # UC20 FE1, RN04, RN05, RNF05: outra organizacao e inexistente tem a mesma resposta
    _, h_outra = nova_conta(c, "Empresa Doadora", "Outra Doadora", parceria="Ativa")
    sol = _criar_sol(c, doa)
    de_outra = c.get(f"{S}/{sol['id_solicitacao']}", headers=h_outra)
    _erro(de_outra, 404, "NAO_ENCONTRADO")
    inexistente = c.get(f"{S}/987654", headers=h_outra)
    _erro(inexistente, 404, "NAO_ENCONTRADO")
    assert de_outra.json() == inexistente.json()


def test_uc20_inexistente_404_e_id_enorme_404(c, doa, adm):
    # UC20 FE1, RNF04
    for h in (doa, adm):
        _erro(c.get(f"{S}/987654", headers=h), 404, "NAO_ENCONTRADO")
        _erro(c.get(f"{S}/{GRANDE}", headers=h), 404, "NAO_ENCONTRADO")


def test_uc20_id_nao_numerico_400(c, doa):
    # RNF04
    _erro(c.get(f"{S}/abc", headers=doa), 400, "DADOS_INVALIDOS")


def test_uc20_lista_vazia_200(c, doa):
    # UC20 (lista sem registros) - tela informa que ainda nao ha solicitacoes
    r = c.get(S, headers=doa)
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_uc20_lista_traz_somente_as_da_propria_organizacao(c, doa, adm, nova_conta):
    # UC20 passo 2, RN04, RN05, RNF05
    _, h_outra = nova_conta(c, "Empresa Doadora", "Outra Doadora", parceria="Ativa")
    mina = _criar_sol(c, doa)
    deles = _criar_sol(c, h_outra)
    ids = [i["id_solicitacao"] for i in c.get(S, headers=doa).json()["items"]]
    assert ids == [mina["id_solicitacao"]]
    ids_outra = [i["id_solicitacao"] for i in c.get(S, headers=h_outra).json()["items"]]
    assert ids_outra == [deles["id_solicitacao"]]
    assert c.get(S, headers=adm).json()["total"] == 2


def test_uc20_filtro_de_organizacao_e_ignorado_para_empresa_doadora(c, doa, nova_conta):
    # contrato GET /solicitacoes (id_organizacao_doadora ignorado para Empresa Doadora), RN04, RNF05
    outra, h_outra = nova_conta(c, "Empresa Doadora", "Outra Doadora", parceria="Ativa")
    mina = _criar_sol(c, doa)
    _criar_sol(c, h_outra)
    r = c.get(f"{S}?id_organizacao_doadora={outra}", headers=doa)
    assert [i["id_solicitacao"] for i in r.json()["items"]] == [mina["id_solicitacao"]]


def test_uc10_passo1_admin_e_funcionario_veem_todas_e_filtram_por_empresa(c, doa, adm, fun, nova_conta):
    # UC10 passo 1
    outra, h_outra = nova_conta(c, "Empresa Doadora", "Outra Doadora", parceria="Ativa")
    a, b = _criar_sol(c, doa), _criar_sol(c, h_outra)
    for h in (adm, fun):
        assert c.get(S, headers=h).json()["total"] == 2
        r = c.get(f"{S}?id_organizacao_doadora={outra}", headers=h).json()
        assert [i["id_solicitacao"] for i in r["items"]] == [b["id_solicitacao"]]
    assert _obter(c, adm, a["id_solicitacao"])["id_organizacao_doadora"] == ORG_DOADORA


def test_uc20_resumo_da_lista_tem_campos_do_contrato(c, doa, adm):
    # UC20 passo 3, contrato SolicitacaoResumo
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": 3}, {"tipo": "Monitor", "modelo": "X", "quantidade": 2}])
    eq = _avaliar(c, adm, sol)
    _destinar(c, adm, sol, eq, "Venda")
    item = c.get(S, headers=doa).json()["items"][0]
    assert set(item) == {"id_solicitacao", "id_organizacao_doadora", "nome_organizacao", "data_solicitacao", "situacao",
                         "total_itens", "total_unidades", "unidades_avaliadas"}
    assert (item["total_itens"], item["total_unidades"], item["unidades_avaliadas"]) == (2, 5, 1)
    assert item["situacao"] == "Em avaliação"


def test_uc20_ordenacao_data_decrescente_depois_id_decrescente(c, doa):
    # contrato GET /solicitacoes (ordenacao)
    a, b, d = _criar_sol(c, doa), _criar_sol(c, doa), _criar_sol(c, doa)
    _sql(c, "UPDATE SOLICITACAO SET data_solicitacao='2026-01-10' WHERE id_solicitacao=?", (a["id_solicitacao"],))
    _sql(c, "UPDATE SOLICITACAO SET data_solicitacao='2026-03-10' WHERE id_solicitacao=?", (b["id_solicitacao"],))
    _sql(c, "UPDATE SOLICITACAO SET data_solicitacao='2026-03-10' WHERE id_solicitacao=?", (d["id_solicitacao"],))
    ids = [i["id_solicitacao"] for i in c.get(S, headers=doa).json()["items"]]
    assert ids == [d["id_solicitacao"], b["id_solicitacao"], a["id_solicitacao"]]


def test_uc20_filtros_situacao_e_periodo(c, doa, adm):
    # contrato GET /solicitacoes (situacao, data_de, data_ate)
    a, b = _criar_sol(c, doa), _criar_sol(c, doa)
    _sql(c, "UPDATE SOLICITACAO SET data_solicitacao='2026-01-10' WHERE id_solicitacao=?", (a["id_solicitacao"],))
    _avaliar(c, adm, b)
    ids = lambda q: [i["id_solicitacao"] for i in c.get(f"{S}?{q}", headers=doa).json()["items"]]  # noqa: E731
    assert ids("situacao=Aguardando avaliação") == [a["id_solicitacao"]]
    assert ids("situacao=Em avaliação") == [b["id_solicitacao"]]
    assert ids("situacao=Avaliada") == []
    assert ids("data_de=2026-01-01&data_ate=2026-01-31") == [a["id_solicitacao"]]
    assert ids(f"data_de={ISO}") == [b["id_solicitacao"]]
    assert ids(f"data_ate={ISO}") == [b["id_solicitacao"], a["id_solicitacao"]]


def test_uc20_periodo_invertido_devolve_lista_vazia_sem_erro(c, doa):
    # contrato esclarecimento 6
    _criar_sol(c, doa)
    r = c.get(f"{S}?data_de=2030-01-01&data_ate=2020-01-01", headers=doa)
    assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0


def test_uc20_paginacao(c, doa):
    # contrato GET /solicitacoes (page, size)
    for _ in range(5):
        _criar_sol(c, doa)
    p1 = c.get(f"{S}?page=1&size=2", headers=doa).json()
    p3 = c.get(f"{S}?page=3&size=2", headers=doa).json()
    p4 = c.get(f"{S}?page=4&size=2", headers=doa).json()
    assert (p1["total"], p1["page"], p1["size"], len(p1["items"])) == (5, 1, 2, 2)
    assert len(p3["items"]) == 1 and p4["items"] == []


@pytest.mark.parametrize("consulta", ["page=0", "size=0", "size=101", "page=x", "situacao=Cancelada", "data_de=ontem",
                                      "data_ate=2026-13-45", f"id_organizacao_doadora={GRANDE}", "id_organizacao_doadora=a"])
def test_uc20_parametros_de_consulta_invalidos_400(c, doa, adm, consulta):
    # contrato GET /solicitacoes (400), RNF04
    for h in (doa, adm):
        _erro(c.get(f"{S}?{consulta}", headers=h), 400, "DADOS_INVALIDOS")


def test_uc20_valor_omitido_para_empresa_doadora_e_presente_para_a_leaf(c, doa, adm):
    # UC20 passo 3, contrato EquipamentoVinculado (valor omitido para Empresa Doadora)
    sol = _criar_sol(c, doa)
    eq = _avaliar(c, adm, sol, valor=2345.67)
    paraDoadora = _item_do_equip(_obter(c, doa, sol["id_solicitacao"]), eq["id_equipamento"])
    assert "valor" not in paraDoadora
    paraAdmin = _item_do_equip(_obter(c, adm, sol["id_solicitacao"]), eq["id_equipamento"])
    assert paraAdmin["valor"] == 2345.67
    assert eq["valor"] == 2345.67  # resposta do POST de avaliacao (perfil interno)
    # tambem em resposta de destinacao (corpo igual ao GET), so para a LEAF TI
    r = _destinar(c, adm, sol, eq, "Venda").json()
    assert _item_do_equip(r, eq["id_equipamento"])["valor"] == 2345.67


def test_uc20_valor_omitido_para_doadora_mesmo_com_equipamento_sem_valor(c, doa, adm):
    # contrato: chave `valor` omitida (nao null) para Empresa Doadora
    sol = _criar_sol(c, doa)
    eq = _avaliar(c, adm, sol, valor=None, condicao="A avaliar")
    e = _item_do_equip(_obter(c, doa, sol["id_solicitacao"]), eq["id_equipamento"])
    assert "valor" not in e
    e2 = _item_do_equip(_obter(c, adm, sol["id_solicitacao"]), eq["id_equipamento"])
    assert e2["valor"] is None


def test_uc20_equipamento_vinculado_tem_campos_do_contrato(c, doa, adm):
    # UC20 passo 3, contrato EquipamentoVinculado
    sol = _criar_sol(c, doa)
    eq = _avaliar(c, adm, sol)
    e = _item_do_equip(_obter(c, doa, sol["id_solicitacao"]), eq["id_equipamento"])
    assert set(e) == {"id_equipamento", "identificacao", "id_categoria", "categoria_nome", "modelo", "condicao", "situacao",
                      "ativo", "data_recebimento", "destinacao", "id_organizacao_ong", "nome_ong", "data_doacao"}
    assert e["destinacao"] is None and e["categoria_nome"] == "Notebooks" and e["ativo"] is True


# ------------------------------------------------------------------ UC10 passo 3: avaliar (cadastrar unidade) (DP-41)
def test_uc10_avaliar_cria_equipamento_vinculado_e_muda_solicitacao_para_em_avaliacao(c, doa, adm):
    # UC10 passo 3 e 7, DP-40, DP-41, RN11, RN21
    sol = _criar_sol(c, doa, [{"tipo": "Notebook", "modelo": "Dell Latitude 5420", "quantidade": 2}])
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos",
               json=_corpo_av(identificacao="NB-1", modelo="IGNORADO"), headers=adm)
    assert r.status_code == 201, r.text
    e = r.json()
    assert e["modelo"] == "Dell Latitude 5420"  # modelo vem do item
    assert e["situacao"] == "Recebido" and e["condicao"] == "Bom" and e["destinacao"] is None
    assert e["categoria_nome"] == "Notebooks" and e["ativo"] is True
    linha = _consulta(c, "SELECT * FROM EQUIPAMENTO WHERE id_equipamento=?", (e["id_equipamento"],))[0]
    assert linha["id_item_solicitacao"] == sol["itens"][0]["id_item_solicitacao"]
    assert linha["origem"] == f"Solicitação {sol['id_solicitacao']}"
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"


def test_uc10_origem_informada_e_respeitada(c, doa, adm):
    # UC10 passo 3 (DP-41)
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, origem="Coleta Alfa")
    assert _consulta(c, "SELECT origem FROM EQUIPAMENTO WHERE id_equipamento=?", (e["id_equipamento"],))[0][0] == "Coleta Alfa"


@pytest.mark.parametrize("situacao", ["Recebido", "Em avaliação", "Em manutenção"])
def test_uc10_situacao_inicial_permitida(c, doa, adm, situacao):
    # UC10 passo 3 / FA2, contrato AvaliacaoEntrada.situacao
    sol = _criar_sol(c, doa)
    assert _avaliar(c, adm, sol, situacao=situacao)["situacao"] == situacao


def test_uc10_avaliar_nao_disponibiliza_no_catalogo(c, doa, adm):
    # RN21: avaliar cadastra a unidade em Recebido, nao Disponivel
    sol = _criar_sol(c, doa)
    _avaliar(c, adm, sol)
    assert _consulta(c, "SELECT COUNT(*) FROM EQUIPAMENTO WHERE situacao='Disponível'")[0][0] == 0


@pytest.mark.parametrize("mudanca,campo", [
    ({"identificacao": None}, "identificacao"),
    ({"identificacao": ""}, "identificacao"),
    ({"identificacao": "I" * 51}, "identificacao"),
    ({"id_categoria": None}, "id_categoria"),
    ({"id_categoria": "x"}, "id_categoria"),
    ({"id_categoria": GRANDE}, "id_categoria"),
    ({"condicao": None}, "condicao"),
    ({"condicao": "Excelente"}, "condicao"),
    ({"data_recebimento": None}, "data_recebimento"),
    ({"data_recebimento": "10/01/2026"}, "data_recebimento"),
    ({"data_recebimento": (HOJE + timedelta(days=1)).isoformat()}, "data_recebimento"),
    ({"valor": -1}, "valor"),
    ({"valor": "abc"}, "valor"),
    ({"valor": 10 ** 8}, "valor"),
    ({"valor": 1.234}, "valor"),
    ({"situacao": "Disponível"}, "situacao"),
    ({"situacao": "Doado"}, "situacao"),
    ({"situacao": "Vendido"}, "situacao"),
    ({"origem": ""}, "origem"),
    ({"origem": "o" * 101}, "origem"),
])
def test_uc10_avaliar_dados_invalidos_400_e_nada_gravado(c, doa, adm, mudanca, campo):
    # UC10 passo 3, RN11, RNF04: validacoes de entrada (reuso das regras do Modulo 3)
    sol = _criar_sol(c, doa)
    corpo = _corpo_av()
    corpo.update(mudanca)
    corpo = {k: v for k, v in corpo.items() if v is not None}
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos", json=corpo, headers=adm)
    e = _erro(r, 400, "DADOS_INVALIDOS")
    assert campo in e["campos"], e
    assert _tab(c, "EQUIPAMENTO") == []
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Aguardando avaliação"


def test_uc10_avaliar_valor_limite_aceito(c, doa, adm):
    # RN11 / DP-39: valor 0 e 9999999.99 sao validos
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": 2}])
    assert _avaliar(c, adm, sol, valor=0)["valor"] == 0
    assert _avaliar(c, adm, sol, valor=9999999.99)["valor"] == 9999999.99


def test_uc10_avaliar_item_inexistente_ou_de_outra_solicitacao_404(c, doa, adm):
    # UC10 passo 3, contrato (404)
    s1, s2 = _criar_sol(c, doa), _criar_sol(c, doa)
    item_s2 = s2["itens"][0]["id_item_solicitacao"]
    base = f"{S}/{s1['id_solicitacao']}/itens"
    _erro(c.post(f"{base}/{item_s2}/equipamentos", json=_corpo_av(), headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.post(f"{base}/987654/equipamentos", json=_corpo_av(), headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.post(f"{S}/987654/itens/{item_s2}/equipamentos", json=_corpo_av(), headers=adm), 404, "NAO_ENCONTRADO")
    assert _tab(c, "EQUIPAMENTO") == []


def test_uc10_avaliar_ids_enormes_na_rota_404(c, doa, adm):
    # RNF04
    sol = _criar_sol(c, doa)
    item = sol["itens"][0]["id_item_solicitacao"]
    _erro(c.post(f"{S}/{GRANDE}/itens/{item}/equipamentos", json=_corpo_av(), headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.post(f"{S}/{sol['id_solicitacao']}/itens/{GRANDE}/equipamentos", json=_corpo_av(), headers=adm), 404, "NAO_ENCONTRADO")


def test_uc10_item_completo_422_ao_exceder_quantidade(c, doa, adm):
    # UC10 passo 3 (DP-41), contrato ITEM_COMPLETO
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": 2}])
    _avaliar(c, adm, sol)
    _avaliar(c, adm, sol)
    antes = _tab(c, "EQUIPAMENTO")
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos", json=_corpo_av(), headers=adm)
    _erro(r, 422, "ITEM_COMPLETO")
    assert _tab(c, "EQUIPAMENTO") == antes


def test_uc10_item_completo_vem_antes_de_identificacao_duplicada(c, doa, adm):
    # contrato: ordem 400 -> 404 -> ITEM_COMPLETO -> regras do Modulo 3
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, identificacao="DUP-1")
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos",
               json=_corpo_av(identificacao="DUP-1"), headers=adm)
    _erro(r, 422, "ITEM_COMPLETO")
    assert e["identificacao"] == "DUP-1"


def test_uc10_item_completo_e_por_item_nao_por_solicitacao(c, doa, adm):
    # UC10 FA1: cada item tem seu limite
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "A", "quantidade": 1}, {"tipo": "M", "modelo": "B", "quantidade": 1}])
    _avaliar(c, adm, sol, 0)
    assert _avaliar(c, adm, sol, 1)["modelo"] == "B"


def test_uc10_identificacao_duplicada_409(c, doa, adm):
    # UC10 passo 3 / UC07 (reuso M3): identificacao unica
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": 2}])
    _avaliar(c, adm, sol, identificacao="UNICA-1")
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos",
               json=_corpo_av(identificacao="UNICA-1"), headers=adm)
    e = _erro(r, 409, "IDENTIFICACAO_DUPLICADA")
    assert "identificacao" in e["campos"]
    assert len(_tab(c, "EQUIPAMENTO")) == 1


@pytest.mark.parametrize("id_categoria", [999, 0, -1])
def test_uc10_categoria_inexistente_422(c, doa, adm, id_categoria):
    # RN11, RN08: categoria ativa obrigatoria
    sol = _criar_sol(c, doa)
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos",
               json=_corpo_av(id_categoria=id_categoria), headers=adm)
    _erro(r, 422, "CATEGORIA_INVALIDA")
    assert _tab(c, "EQUIPAMENTO") == []


def test_uc10_categoria_inativa_422(c, doa, adm):
    # RN11, RN08
    nova = c.post(CAT, json={"nome": "Categoria Parada"}, headers=adm).json()
    assert c.patch(f"{CAT}/{nova['id_categoria']}/situacao", json={"ativa": False}, headers=adm).status_code == 200
    sol = _criar_sol(c, doa)
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos",
               json=_corpo_av(id_categoria=nova["id_categoria"]), headers=adm)
    _erro(r, 422, "CATEGORIA_INVALIDA")


def test_uc10_fe1_sem_reuso_nao_pode_entrar_em_manutencao(c, doa, adm):
    # UC10 FE1, RN12: "Sem condicoes de reuso" so permite Recebido, Em avaliacao e Reciclagem
    sol = _criar_sol(c, doa)
    r = c.post(f"{S}/{sol['id_solicitacao']}/itens/{sol['itens'][0]['id_item_solicitacao']}/equipamentos",
               json=_corpo_av(condicao="Sem condições de reuso", situacao="Em manutenção"), headers=adm)
    _erro(r, 422, "SEM_CONDICOES_DE_REUSO")
    assert _tab(c, "EQUIPAMENTO") == []


def test_uc10_sem_reuso_em_avaliacao_e_aceito(c, doa, adm):
    # UC10 FE1, RN12
    sol = _criar_sol(c, doa)
    assert _avaliar(c, adm, sol, condicao="Sem condições de reuso", situacao="Em avaliação")["condicao"] == "Sem condições de reuso"


# ------------------------------------------------------------------ DP-40: ciclo de situacao da solicitacao
def test_dp40_ciclo_aguardando_em_avaliacao_avaliada(c, doa, adm):
    # UC10 passo 7 e FE2, DP-40: Aguardando avaliacao -> Em avaliacao -> Avaliada
    sol = _criar_sol(c, doa, [{"tipo": "Notebook", "modelo": "M", "quantidade": 2}])
    sid = sol["id_solicitacao"]
    assert _situacao_sol(c, sid) == "Aguardando avaliação"
    e1 = _avaliar(c, adm, sol)
    assert _situacao_sol(c, sid) == "Em avaliação"
    e2 = _avaliar(c, adm, sol)
    assert _situacao_sol(c, sid) == "Em avaliação"  # cadastrada mas sem destinacao
    r1 = _destinar(c, adm, sol, e1, "Venda").json()
    assert r1["situacao"] == "Em avaliação" and r1["pendencias"]
    assert r1["itens"][0]["quantidade_cadastrada"] == 2 and r1["itens"][0]["quantidade_avaliada"] == 1
    assert r1["itens"][0]["avaliado"] is False
    r2 = _destinar(c, adm, sol, e2, "Reciclagem").json()
    assert r2["situacao"] == "Avaliada" and r2["pendencias"] == []
    assert r2["itens"][0]["avaliado"] is True and r2["itens"][0]["quantidade_avaliada"] == 2
    assert _situacao_sol(c, sid) == "Avaliada"
    assert _obter(c, doa, sid)["situacao"] == "Avaliada"


def test_uc10_fe2_nao_conclui_com_unidade_ainda_nao_cadastrada(c, doa, adm):
    # UC10 FE2, DP-40/DP-41: todas as unidades cadastradas destinadas, mas faltam unidades -> continua Em avaliacao
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": 3}])
    e = _avaliar(c, adm, sol)
    r = _destinar(c, adm, sol, e, "Venda").json()
    assert r["situacao"] == "Em avaliação"
    assert any("faltam 2" in p for p in r["pendencias"]), r["pendencias"]


def test_uc10_fe2_nao_conclui_com_um_item_sem_nenhuma_unidade(c, doa, adm):
    # UC10 FE2: segundo item nao avaliado impede 'Avaliada'
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "A", "quantidade": 1}, {"tipo": "M", "modelo": "B", "quantidade": 1}])
    e = _avaliar(c, adm, sol, 0)
    r = _destinar(c, adm, sol, e, "Venda").json()
    assert r["situacao"] == "Em avaliação" and r["itens"][0]["avaliado"] and not r["itens"][1]["avaliado"]
    e2 = _avaliar(c, adm, sol, 1)
    assert _destinar(c, adm, sol, e2, "Reciclagem").json()["situacao"] == "Avaliada"


def test_uc10_fe2_condicao_a_avaliar_nao_conta_como_avaliada(c, doa, adm):
    # UC10 FE2, DP-41: equipamento sem condicao avaliada mantem a solicitacao Em avaliacao
    sol = _criar_sol(c, doa)
    # DP-54: a destinacao nao e mais aceita com 'A avaliar'; a condicao volta a 'A avaliar' depois (PUT do Modulo 3)
    e = _avaliar(c, adm, sol, condicao="Bom")
    assert _destinar(c, adm, sol, e, "Reciclagem").json()["situacao"] == "Avaliada"
    atual = c.get(f"{E}/{e['id_equipamento']}", headers=adm).json()
    assert c.put(f"{E}/{e['id_equipamento']}", json=_corpo_put(atual, condicao="A avaliar"), headers=adm).status_code == 200
    r = _obter(c, adm, sol["id_solicitacao"])
    assert r["situacao"] == "Em avaliação"
    assert r["itens"][0]["quantidade_avaliada"] == 0


def test_uc10_fa1_destinos_diferentes_na_mesma_solicitacao(c, doa, adm):
    # UC10 FA1, RN21: venda, doacao e reciclagem na mesma solicitacao
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": 3}])
    e1 = _avaliar(c, adm, sol)
    e2 = _avaliar(c, adm, sol)
    e3 = _avaliar(c, adm, sol, condicao="Sem condições de reuso", valor=None)
    _destinar(c, adm, sol, e1, "Venda")
    _doar(c, adm, sol, e2)
    r = _destinar(c, adm, sol, e3, "Reciclagem").json()
    assert r["situacao"] == "Avaliada"
    por_id = {e["id_equipamento"]: e for e in r["itens"][0]["equipamentos"]}
    assert por_id[e1["id_equipamento"]]["destinacao"] == "Venda" and por_id[e1["id_equipamento"]]["situacao"] == "Disponível"
    assert por_id[e2["id_equipamento"]]["destinacao"] == "Doação" and por_id[e2["id_equipamento"]]["situacao"] == "Doado"
    assert por_id[e3["id_equipamento"]]["destinacao"] == "Reciclagem"
    assert por_id[e3["id_equipamento"]]["situacao"] == "Destinado à reciclagem"


def test_uc10_fa2_recondicionamento_via_rotas_do_modulo3(c, doa, adm):
    # UC10 FA2, RF12: manutencao -> recondicionado -> destinacao; solicitacao fecha ao final
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, condicao="Necessita reparo", situacao="Em manutenção", valor=800)
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"
    assert c.patch(f"{E}/{e['id_equipamento']}/situacao", json={"situacao": "Recondicionado"}, headers=adm).status_code == 200
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"  # recondicionado ainda nao e destinado
    r = _destinar(c, adm, sol, e, "Venda")
    assert r.status_code == 200 and r.json()["situacao"] == "Avaliada"
    assert _situacao_eq(c, e["id_equipamento"]) == "Disponível"


# ------------------------------------------------------------------ DP-42: destinacao (UC10 passo 4-7, UC11)
def test_dp42_venda_marca_disponivel(c, doa, adm):
    # UC10 passo 4-5 (UC08), RN11, DP-42
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    r = _destinar(c, adm, sol, e, "Venda")
    assert r.status_code == 200
    eq = _item_do_equip(r.json(), e["id_equipamento"])
    assert eq["situacao"] == "Disponível" and eq["destinacao"] == "Venda"
    assert _situacao_eq(c, e["id_equipamento"]) == "Disponível"
    assert _tab(c, "DOACAO") == []


def test_dp42_reciclagem_marca_destinado(c, doa, adm):
    # UC10 passo 4-5, RN11, RN21, DP-42
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    r = _destinar(c, adm, sol, e, "Reciclagem")
    assert _item_do_equip(r.json(), e["id_equipamento"])["destinacao"] == "Reciclagem"
    assert _situacao_eq(c, e["id_equipamento"]) == "Destinado à reciclagem"


def test_dp42_doacao_marca_doado_e_grava_doacao_na_mesma_transacao(c, doa, adm):
    # UC11 passo 4-5, RN12, DP-42: situacao Doado + linha em DOACAO com ONG e data
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    data = (HOJE - timedelta(days=3)).isoformat()
    r = _destinar(c, adm, sol, e, "Doação", id_organizacao_ong=ONG_ATIVA, data_doacao=data)
    assert r.status_code == 200, r.text
    eq = _item_do_equip(r.json(), e["id_equipamento"])
    assert eq["destinacao"] == "Doação" and eq["situacao"] == "Doado"
    assert eq["id_organizacao_ong"] == ONG_ATIVA and eq["nome_ong"] == "ONG Cliente" and eq["data_doacao"] == data
    linhas = _consulta(c, "SELECT * FROM DOACAO")
    assert len(linhas) == 1
    assert (linhas[0]["id_equipamento"], linhas[0]["id_organizacao_ong"], linhas[0]["data_doacao"]) == (e["id_equipamento"], ONG_ATIVA, data)


def test_dp42_doacao_na_data_do_recebimento_e_hoje_sao_aceitas(c, doa, adm):
    # RN12: data nao futura e nao anterior ao recebimento (limites inclusivos)
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": 2}])
    e1, e2 = _avaliar(c, adm, sol), _avaliar(c, adm, sol)
    _doar(c, adm, sol, e1, data=RECEBIMENTO)
    _doar(c, adm, sol, e2, data=ISO)
    assert len(_tab(c, "DOACAO")) == 2


def test_dp42_destinacao_nao_recalcula_nada_sem_vinculo_avulso(c, adm):
    # UC10: equipamento avulso (sem item) nao pertence a nenhuma solicitacao -> 404 na rota do modulo 4
    sol_id = 1
    r = c.post(E, json={"identificacao": "AVULSO-1", "id_categoria": 2, "modelo": "M", "condicao": "Bom", "origem": "o",
                        "data_recebimento": RECEBIMENTO, "valor": 100}, headers=adm)
    eq = r.json()
    _erro(c.put(f"{S}/{sol_id}/equipamentos/{eq['id_equipamento']}/destinacao", json={"destinacao": "Venda"}, headers=adm),
          404, "NAO_ENCONTRADO")


# ------------------------------------------------------------------ UC10 FE1 / UC11 FE2: sem reuso (RN11, RN12, RN21)
@pytest.mark.parametrize("destinacao", ["Venda", "Doação"])
def test_uc10_fe1_sem_reuso_nao_pode_ser_venda_nem_doacao(c, doa, adm, destinacao):
    # UC10 FE1, UC11 FE2, RN11, RN12, RN21: 422 SEM_CONDICOES_DE_REUSO e nada muda
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, condicao="Sem condições de reuso", valor=900)
    extra = {"id_organizacao_ong": ONG_ATIVA, "data_doacao": ISO} if destinacao == "Doação" else {}
    _erro(_destinar(c, adm, sol, e, destinacao, **extra), 422, "SEM_CONDICOES_DE_REUSO")
    assert _situacao_eq(c, e["id_equipamento"]) == "Recebido" and _tab(c, "DOACAO") == []
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"


def test_uc10_fe1_sem_reuso_so_aceita_reciclagem(c, doa, adm):
    # UC10 FE1, UC11 FE2, RN21: a impossibilidade de reuso determina a reciclagem (nao a recusa)
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, condicao="Sem condições de reuso", valor=None)
    r = _destinar(c, adm, sol, e, "Reciclagem")
    assert r.status_code == 200 and r.json()["situacao"] == "Avaliada"


def test_uc10_condicao_a_avaliar_nao_pode_ser_venda_nem_doacao(c, doa, adm):
    # RN11/UC08 (DP-35, DP-54): sem condicao avaliada nao ha disponibilizacao nem doacao (agora CONDICAO_NAO_AVALIADA)
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, condicao="A avaliar", valor=500)
    _erro(_destinar(c, adm, sol, e, "Venda"), 422, "CONDICAO_NAO_AVALIADA")
    _erro(_destinar(c, adm, sol, e, "Doação", id_organizacao_ong=ONG_ATIVA, data_doacao=ISO), 422, "CONDICAO_NAO_AVALIADA")
    assert _situacao_eq(c, e["id_equipamento"]) == "Recebido" and _tab(c, "DOACAO") == []


@pytest.mark.parametrize("valor", [None, 0])
def test_uc10_venda_exige_valor_maior_que_zero(c, doa, adm, valor):
    # RN12/RF12 (DP-35): disponivel exige valor > 0
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, valor=valor)
    corpo = _erro(_destinar(c, adm, sol, e, "Venda"), 422, "TRANSICAO_INVALIDA")
    assert "valor" in corpo["campos"]
    assert _situacao_eq(c, e["id_equipamento"]) == "Recebido"


def test_uc11_doacao_nao_exige_valor(c, doa, adm):
    # UC11: so a venda exige valor
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, valor=None)
    assert _destinar(c, adm, sol, e, "Doação", id_organizacao_ong=ONG_ATIVA, data_doacao=ISO).status_code == 200


@pytest.mark.parametrize("destinacao", ["Venda", "Doação"])
def test_uc10_equipamento_inativo_nao_pode_ser_venda_nem_doacao(c, doa, adm, destinacao):
    # RN12 (inativos), DP-30: 422 EQUIPAMENTO_INATIVO
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    assert c.patch(f"{E}/{e['id_equipamento']}/ativo", json={"ativo": False}, headers=adm).status_code == 200
    extra = {"id_organizacao_ong": ONG_ATIVA, "data_doacao": ISO} if destinacao == "Doação" else {}
    _erro(_destinar(c, adm, sol, e, destinacao, **extra), 422, "EQUIPAMENTO_INATIVO")
    assert _situacao_eq(c, e["id_equipamento"]) == "Recebido" and _tab(c, "DOACAO") == []


def test_uc10_equipamento_inativo_pode_ser_reciclado(c, doa, adm):
    # RN12 / DP-38 (opcao A, decidida): so Disponivel e Doado sao bloqueados
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    c.patch(f"{E}/{e['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    assert _destinar(c, adm, sol, e, "Reciclagem").status_code == 200


def test_uc10_reativar_equipamento_libera_a_venda(c, doa, adm):
    # RN12, DP-30
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    c.patch(f"{E}/{e['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    _erro(_destinar(c, adm, sol, e, "Venda"), 422, "EQUIPAMENTO_INATIVO")
    c.patch(f"{E}/{e['id_equipamento']}/ativo", json={"ativo": True}, headers=adm)
    assert _destinar(c, adm, sol, e, "Venda").status_code == 200


# ------------------------------------------------------------------ UC11 FE1: doacao invalida (RN12)
def _antes_doacao_invalida(c, sol, e):
    return (_tab(c, "DOACAO"), _situacao_eq(c, e["id_equipamento"]), _situacao_sol(c, sol["id_solicitacao"]))


def test_uc11_fe1_ong_inexistente_422(c, doa, adm):
    # UC11 FE1, RN12
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    antes = _antes_doacao_invalida(c, sol, e)
    corpo = _erro(_destinar(c, adm, sol, e, "Doação", id_organizacao_ong=987654, data_doacao=ISO), 422, "DOACAO_INVALIDA")
    assert "id_organizacao_ong" in corpo["campos"]
    assert _antes_doacao_invalida(c, sol, e) == antes


@pytest.mark.parametrize("org", [1, 3, 4])
def test_uc11_fe1_organizacao_que_nao_e_cliente_ong_422(c, doa, adm, org):
    # UC11 FE1, RN12: precisa ser do tipo Cliente ONG
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    antes = _antes_doacao_invalida(c, sol, e)
    _erro(_destinar(c, adm, sol, e, "Doação", id_organizacao_ong=org, data_doacao=ISO), 422, "DOACAO_INVALIDA")
    assert _antes_doacao_invalida(c, sol, e) == antes


def test_uc11_fe1_ong_inativa_422(c, doa, adm, nova_conta):
    # UC11 FE1, RN12: ONG beneficiaria precisa estar ativa
    id_inativa, _ = nova_conta(c, "Cliente ONG", "ONG Parada", situacao="Inativa")
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    antes = _antes_doacao_invalida(c, sol, e)
    _erro(_destinar(c, adm, sol, e, "Doação", id_organizacao_ong=id_inativa, data_doacao=ISO), 422, "DOACAO_INVALIDA")
    assert _antes_doacao_invalida(c, sol, e) == antes


def test_uc11_data_futura_422(c, doa, adm):
    # RN12: data da doacao nao futura
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    antes = _antes_doacao_invalida(c, sol, e)
    corpo = _erro(_destinar(c, adm, sol, e, "Doação", id_organizacao_ong=ONG_ATIVA,
                            data_doacao=(HOJE + timedelta(days=1)).isoformat()), 422, "DOACAO_INVALIDA")
    assert "data_doacao" in corpo["campos"]
    assert _antes_doacao_invalida(c, sol, e) == antes


def test_uc11_data_anterior_ao_recebimento_422(c, doa, adm):
    # RN12: data da doacao nao anterior ao recebimento
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    antes = _antes_doacao_invalida(c, sol, e)
    corpo = _erro(_destinar(c, adm, sol, e, "Doação", id_organizacao_ong=ONG_ATIVA,
                            data_doacao=(HOJE - timedelta(days=11)).isoformat()), 422, "DOACAO_INVALIDA")
    assert "data_doacao" in corpo["campos"]
    assert _antes_doacao_invalida(c, sol, e) == antes


def test_uc11_falha_na_transacao_desfaz_situacao_doacao_e_solicitacao(c, doa, adm, monkeypatch):
    # UC11 / DP-42: "doacao gravada na mesma transacao" - falha no recalculo desfaz tudo (rollback)
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)

    def explode(*a, **k):
        raise RuntimeError("falha simulada")
    monkeypatch.setattr("app.solicitacoes.service.recalcular_situacao", explode)
    with pytest.raises(RuntimeError):
        _destinar(c, adm, sol, e, "Doação", id_organizacao_ong=ONG_ATIVA, data_doacao=ISO)
    assert _situacao_eq(c, e["id_equipamento"]) == "Recebido"
    assert _tab(c, "DOACAO") == []


def test_uc11_falha_na_transacao_da_venda_desfaz_situacao(c, doa, adm, monkeypatch):
    # UC10 passo 5-7 (DP-42): equipamento e solicitacao andam juntos
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)

    def explode(*a, **k):
        raise RuntimeError("falha simulada")
    monkeypatch.setattr("app.solicitacoes.service.recalcular_situacao", explode)
    with pytest.raises(RuntimeError):
        _destinar(c, adm, sol, e, "Venda")
    assert _situacao_eq(c, e["id_equipamento"]) == "Recebido"


# ------------------------------------------------------------------ UC11 FE1 / UC10: 400 da entrada de destinacao
@pytest.mark.parametrize("corpo", [
    {},
    {"destinacao": "Doacao"},
    {"destinacao": "venda"},
    {"destinacao": "Troca"},
    {"destinacao": None},
    {"destinacao": 3},
])
def test_uc10_destinacao_invalida_400(c, doa, adm, corpo):
    # UC10 passo 4, RNF04
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    r = c.put(f"{S}/{sol['id_solicitacao']}/equipamentos/{e['id_equipamento']}/destinacao", json=corpo, headers=adm)
    e = _erro(r, 400, "DADOS_INVALIDOS")
    assert "destinacao" in e["campos"]


@pytest.mark.parametrize("corpo,campos", [
    ({"destinacao": "Doação"}, {"id_organizacao_ong", "data_doacao"}),
    ({"destinacao": "Doação", "id_organizacao_ong": ONG_ATIVA}, {"data_doacao"}),
    ({"destinacao": "Doação", "data_doacao": ISO}, {"id_organizacao_ong"}),
    ({"destinacao": "Venda", "id_organizacao_ong": ONG_ATIVA}, {"id_organizacao_ong"}),
    ({"destinacao": "Venda", "data_doacao": ISO}, {"data_doacao"}),
    ({"destinacao": "Reciclagem", "id_organizacao_ong": ONG_ATIVA, "data_doacao": ISO}, {"id_organizacao_ong", "data_doacao"}),
    ({"destinacao": "Doação", "id_organizacao_ong": ONG_ATIVA, "data_doacao": "10/01/2026"}, {"data_doacao"}),
    ({"destinacao": "Doação", "id_organizacao_ong": ONG_ATIVA, "data_doacao": "2026-02-30"}, {"data_doacao"}),
    ({"destinacao": "Doação", "id_organizacao_ong": "abc", "data_doacao": ISO}, {"id_organizacao_ong"}),
    ({"destinacao": "Doação", "id_organizacao_ong": GRANDE, "data_doacao": ISO}, {"id_organizacao_ong"}),
])
def test_uc11_fe1_campos_da_doacao_400_e_nada_muda(c, doa, adm, corpo, campos):
    # UC11 FE1 (ONG/data ausentes), contrato PUT destinacao: Venda/Reciclagem rejeitam os campos de doacao
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    antes = _antes_doacao_invalida(c, sol, e)
    r = c.put(f"{S}/{sol['id_solicitacao']}/equipamentos/{e['id_equipamento']}/destinacao", json=corpo, headers=adm)
    resp = _erro(r, 400, "DADOS_INVALIDOS")
    assert campos <= set(resp["campos"]), resp
    assert _antes_doacao_invalida(c, sol, e) == antes


def test_uc10_destinacao_404_para_solicitacao_ou_equipamento_fora_dela(c, doa, adm):
    # UC10 passo 4, contrato (404): equipamento precisa estar vinculado a item da solicitacao
    s1, s2 = _criar_sol(c, doa), _criar_sol(c, doa)
    e2 = _avaliar(c, adm, s2)
    _erro(_destinar(c, adm, s1, e2, "Venda"), 404, "NAO_ENCONTRADO")  # equipamento da solicitacao 2
    _erro(c.put(f"{S}/{s1['id_solicitacao']}/equipamentos/987654/destinacao", json={"destinacao": "Venda"}, headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.put(f"{S}/987654/equipamentos/{e2['id_equipamento']}/destinacao", json={"destinacao": "Venda"}, headers=adm), 404, "NAO_ENCONTRADO")
    assert _situacao_eq(c, e2["id_equipamento"]) == "Recebido"


def test_uc10_destinacao_ids_enormes_na_rota_404(c, doa, adm):
    # RNF04
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    corpo = {"destinacao": "Venda"}
    _erro(c.put(f"{S}/{GRANDE}/equipamentos/{e['id_equipamento']}/destinacao", json=corpo, headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.put(f"{S}/{sol['id_solicitacao']}/equipamentos/{GRANDE}/destinacao", json=corpo, headers=adm), 404, "NAO_ENCONTRADO")


def test_uc10_400_vem_antes_de_404_na_destinacao(c, adm):
    # contrato: ordem 400 -> 404
    _erro(c.put(f"{S}/987654/equipamentos/987654/destinacao", json={"destinacao": "Troca"}, headers=adm), 400, "DADOS_INVALIDOS")


# ------------------------------------------------------------------ idempotencia e situacoes finais (esclarecimento 2; RN12)
def test_destinacao_venda_e_idempotente(c, doa, adm):
    # contrato esclarecimento 2: Venda vale se Disponivel ou Vendido
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    assert _destinar(c, adm, sol, e, "Venda").status_code == 200
    r = _destinar(c, adm, sol, e, "Venda")
    assert r.status_code == 200 and _situacao_eq(c, e["id_equipamento"]) == "Disponível"
    _sql(c, "UPDATE EQUIPAMENTO SET situacao='Vendido' WHERE id_equipamento=?", (e["id_equipamento"],))
    r = _destinar(c, adm, sol, e, "Venda")
    assert r.status_code == 200 and _situacao_eq(c, e["id_equipamento"]) == "Vendido"
    assert _item_do_equip(r.json(), e["id_equipamento"])["destinacao"] == "Venda"


def test_destinacao_doacao_e_idempotente_mesmo_com_ong_e_data_diferentes(c, doa, adm, nova_conta):
    # contrato esclarecimento 2: Doacao vale se Doado (200 sem alterar)
    outra_ong, _ = nova_conta(c, "Cliente ONG", "Outra ONG")
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    d1 = (HOJE - timedelta(days=4)).isoformat()
    _doar(c, adm, sol, e, ong_id=ONG_ATIVA, data=d1)
    r = _destinar(c, adm, sol, e, "Doação", id_organizacao_ong=outra_ong, data_doacao=ISO)
    assert r.status_code == 200
    linhas = _consulta(c, "SELECT * FROM DOACAO")
    assert len(linhas) == 1
    assert (linhas[0]["id_organizacao_ong"], linhas[0]["data_doacao"]) == (ONG_ATIVA, d1)
    assert _item_do_equip(r.json(), e["id_equipamento"])["nome_ong"] == "ONG Cliente"


def test_destinacao_reciclagem_e_idempotente(c, doa, adm):
    # contrato esclarecimento 2
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    _destinar(c, adm, sol, e, "Reciclagem")
    r = _destinar(c, adm, sol, e, "Reciclagem")
    assert r.status_code == 200 and _situacao_eq(c, e["id_equipamento"]) == "Destinado à reciclagem"


def test_doado_e_final_nao_vira_venda_nem_reciclagem(c, doa, adm):
    # RN12 (situacoes finais), RF12: 422 EQUIPAMENTO_FINALIZADO
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    _doar(c, adm, sol, e)
    _erro(_destinar(c, adm, sol, e, "Venda"), 422, "EQUIPAMENTO_FINALIZADO")
    _erro(_destinar(c, adm, sol, e, "Reciclagem"), 422, "EQUIPAMENTO_FINALIZADO")
    assert _situacao_eq(c, e["id_equipamento"]) == "Doado" and len(_tab(c, "DOACAO")) == 1


def test_vendido_e_final_nao_vira_doacao_nem_reciclagem(c, doa, adm):
    # RN12, RF12
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    _destinar(c, adm, sol, e, "Venda")
    _sql(c, "UPDATE EQUIPAMENTO SET situacao='Vendido' WHERE id_equipamento=?", (e["id_equipamento"],))
    _erro(_destinar(c, adm, sol, e, "Doação", id_organizacao_ong=ONG_ATIVA, data_doacao=ISO), 422, "EQUIPAMENTO_FINALIZADO")
    _erro(_destinar(c, adm, sol, e, "Reciclagem"), 422, "EQUIPAMENTO_FINALIZADO")
    assert _tab(c, "DOACAO") == []


@pytest.mark.parametrize("destinacao", ["Venda", "Doação"])
def test_reciclagem_e_final_nao_vira_venda_nem_doacao(c, doa, adm, destinacao):
    # RN12: "Equipamentos destinados a reciclagem nao podem ser disponibilizados para venda ou doacao"
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    _destinar(c, adm, sol, e, "Reciclagem")
    extra = {"id_organizacao_ong": ONG_ATIVA, "data_doacao": ISO} if destinacao == "Doação" else {}
    _erro(_destinar(c, adm, sol, e, destinacao, **extra), 422, "TRANSICAO_INVALIDA")
    assert _situacao_eq(c, e["id_equipamento"]) == "Destinado à reciclagem" and _tab(c, "DOACAO") == []


def test_disponivel_pode_virar_doacao_ou_reciclagem_na_avaliacao(c, doa, adm):
    # UC10 FA2 (atualiza a destinacao apos reavaliar): Disponivel -> Doado
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    _destinar(c, adm, sol, e, "Venda")
    r = _doar(c, adm, sol, e)
    assert _item_do_equip(r, e["id_equipamento"])["situacao"] == "Doado"


# ------------------------------------------------------------------ recalculo a partir das rotas do Modulo 3 (DP-40)
def test_dp40_recalculo_pelo_patch_de_situacao_do_modulo3(c, doa, adm):
    # DP-40: PATCH /equipamentos/{id}/situacao recalcula a solicitacao na mesma transacao
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"
    assert c.patch(f"{E}/{e['id_equipamento']}/situacao", json={"situacao": "Disponível"}, headers=adm).status_code == 200
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Avaliada"
    # e a doacao via M3 tambem
    sol2 = _criar_sol(c, doa)
    e2 = _avaliar(c, adm, sol2)
    r = c.patch(f"{E}/{e2['id_equipamento']}/situacao",
                json={"situacao": "Doado", "id_organizacao_ong": ONG_ATIVA, "data_doacao": ISO}, headers=adm)
    assert r.status_code == 200
    assert _situacao_sol(c, sol2["id_solicitacao"]) == "Avaliada"
    d = _obter(c, doa, sol2["id_solicitacao"])
    assert _item_do_equip(d, e2["id_equipamento"])["destinacao"] == "Doação"


def test_dp40_recalculo_pelo_put_do_modulo3_reabre_a_solicitacao(c, doa, adm):
    # DP-40: PUT /equipamentos/{id} (condicao volta a 'A avaliar') recalcula: Avaliada -> Em avaliacao
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    _destinar(c, adm, sol, e, "Reciclagem")
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Avaliada"
    corpo = {"identificacao": e["identificacao"], "id_categoria": 2, "modelo": e["modelo"], "condicao": "A avaliar",
             "origem": "o", "data_recebimento": RECEBIMENTO, "valor": 1500.0,
             "id_item_solicitacao": sol["itens"][0]["id_item_solicitacao"]}
    assert c.put(f"{E}/{e['id_equipamento']}", json=corpo, headers=adm).status_code == 200
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"
    assert _obter(c, adm, sol["id_solicitacao"])["pendencias"]


def test_dp40_post_de_equipamento_do_modulo3_com_vinculo_recalcula(c, doa, adm):
    # DP-40, UC07 passo 4: cadastrar equipamento ligado ao item leva a solicitacao para Em avaliacao
    sol = _criar_sol(c, doa)
    r = c.post(E, json={"identificacao": "M3-LIGADO", "id_categoria": 2, "modelo": "M", "condicao": "Bom", "origem": "o",
                        "data_recebimento": RECEBIMENTO, "valor": 10, "id_item_solicitacao": sol["itens"][0]["id_item_solicitacao"]},
               headers=adm)
    assert r.status_code == 201, r.text
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"
    assert _obter(c, adm, sol["id_solicitacao"])["itens"][0]["quantidade_cadastrada"] == 1


def test_dp40_desativar_equipamento_do_modulo3_nao_quebra_a_consulta(c, doa, adm):
    # DP-40 / DP-30: PATCH ativo recalcula sem erro e a consulta mostra ativo=false
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    assert c.patch(f"{E}/{e['id_equipamento']}/ativo", json={"ativo": False}, headers=adm).status_code == 200
    assert _item_do_equip(_obter(c, adm, sol["id_solicitacao"]), e["id_equipamento"])["ativo"] is False


def test_dp52_modulo3_nao_deveria_exceder_a_quantidade_do_item(c, doa, adm):
    # DP-52, UC07 passo 4, UC10: o POST /equipamentos recusa vinculo alem da quantidade (422 ITEM_COMPLETO)
    sol = _criar_sol(c, doa)
    item = sol["itens"][0]["id_item_solicitacao"]
    _avaliar(c, adm, sol)
    r = c.post(E, json={"identificacao": "M3-EXTRA", "id_categoria": 2, "modelo": "M", "condicao": "Bom", "origem": "o",
                        "data_recebimento": RECEBIMENTO, "valor": 10, "id_item_solicitacao": item}, headers=adm)
    assert r.status_code == 422


# ------------------------------------------------------------------ UC11 passo 2: ONGs elegiveis (RN12)
def test_uc11_ongs_elegiveis_somente_cliente_ong_ativa_ordenadas_por_nome(c, adm, fun, nova_conta):
    # UC11 passo 2, RN12
    nova_conta(c, "Cliente ONG", "Amigos do Bem")
    nova_conta(c, "Cliente ONG", "ONG Parada", situacao="Inativa")
    for h in (adm, fun):
        r = c.get(f"{D}/ongs-elegiveis", headers=h)
        assert r.status_code == 200
        nomes = [o["nome_razao_social"] for o in r.json()]
        assert nomes == ["Amigos do Bem", "ONG Cliente"]
        assert all(set(o) == {"id_organizacao", "nome_razao_social"} for o in r.json())


def test_uc11_ongs_elegiveis_lista_vazia_sem_ong_ativa(c, adm):
    # UC11 FE1: sem ONG ativa a lista vem vazia (a tela avisa)
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ONG_ATIVA,))
    r = c.get(f"{D}/ongs-elegiveis", headers=adm)
    assert r.status_code == 200 and r.json() == []


# ------------------------------------------------------------------ UC19: doacoes (RN04, RN12, RN15, RNF05)
def _doacao_pronta(c, doa, adm, ong_id=ONG_ATIVA, data=None, quantidade=1):
    sol = _criar_sol(c, doa, [{"tipo": "N", "modelo": "M", "quantidade": quantidade}])
    eqs = []
    for _ in range(quantidade):
        e = _avaliar(c, adm, sol)
        _doar(c, adm, sol, e, ong_id=ong_id, data=data)
        eqs.append(e)
    return sol, eqs


def test_uc19_lista_vazia_200_fa1(c, ong):
    # UC19 FA1: sem registros -> 200 e items []
    r = c.get(D, headers=ong)
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "page": 1, "size": 20}


def test_uc19_ong_ve_somente_as_proprias_doacoes(c, doa, adm, ong, nova_conta):
    # UC19 passo 2, RN04, RN15, RNF05
    outra, h_outra = nova_conta(c, "Cliente ONG", "Outra ONG")
    _, (e_minha,) = _doacao_pronta(c, doa, adm, ong_id=ONG_ATIVA)
    _, (e_dela,) = _doacao_pronta(c, doa, adm, ong_id=outra)
    r = c.get(D, headers=ong).json()
    assert r["total"] == 1 and [i["id_equipamento"] for i in r["items"]] == [e_minha["id_equipamento"]]
    r2 = c.get(D, headers=h_outra).json()
    assert [i["id_equipamento"] for i in r2["items"]] == [e_dela["id_equipamento"]]


def test_uc19_filtro_de_ong_e_ignorado_para_cliente_ong(c, doa, adm, ong, nova_conta):
    # contrato GET /doacoes (Cliente ONG somente as proprias), RN04, RNF05
    outra, _ = nova_conta(c, "Cliente ONG", "Outra ONG")
    _doacao_pronta(c, doa, adm, ong_id=ONG_ATIVA)
    _doacao_pronta(c, doa, adm, ong_id=outra)
    r = c.get(f"{D}?id_organizacao_ong={outra}", headers=ong).json()
    assert r["total"] == 1 and r["items"][0]["id_organizacao_ong"] == ONG_ATIVA


def test_uc19_admin_e_funcionario_veem_todas_e_filtram_por_ong(c, doa, adm, fun, nova_conta):
    # contrato GET /doacoes (filtro id_organizacao_ong)
    outra, _ = nova_conta(c, "Cliente ONG", "Outra ONG")
    _doacao_pronta(c, doa, adm, ong_id=ONG_ATIVA)
    _doacao_pronta(c, doa, adm, ong_id=outra)
    for h in (adm, fun):
        assert c.get(D, headers=h).json()["total"] == 2
        r = c.get(f"{D}?id_organizacao_ong={outra}", headers=h).json()
        assert r["total"] == 1 and r["items"][0]["nome_ong"] == "Outra ONG"


def test_uc19_item_da_lista_tem_campos_do_contrato(c, doa, adm, ong):
    # UC19 passo 3 (equipamento, situacao, data), contrato Doacao
    sol, (e,) = _doacao_pronta(c, doa, adm, data=(HOJE - timedelta(days=2)).isoformat())
    item = c.get(D, headers=ong).json()["items"][0]
    assert set(item) == {"id_doacao", "id_equipamento", "identificacao", "modelo", "categoria_nome", "condicao", "situacao",
                         "id_organizacao_ong", "nome_ong", "data_doacao", "id_solicitacao"}
    assert item["identificacao"] == e["identificacao"] and item["situacao"] == "Doado"
    assert item["data_doacao"] == (HOJE - timedelta(days=2)).isoformat()
    assert item["id_solicitacao"] == sol["id_solicitacao"] and item["nome_ong"] == "ONG Cliente"
    assert item["categoria_nome"] == "Notebooks" and item["condicao"] == "Bom"


def test_uc19_doacao_de_equipamento_avulso_tem_id_solicitacao_nulo(c, adm, ong):
    # contrato Doacao.id_solicitacao nullable (doacao feita pela rota do Modulo 3)
    r = c.post(E, json={"identificacao": "AVULSO-D", "id_categoria": 2, "modelo": "M", "condicao": "Bom", "origem": "o",
                        "data_recebimento": RECEBIMENTO, "valor": 10}, headers=adm).json()
    assert c.patch(f"{E}/{r['id_equipamento']}/situacao", json={"situacao": "Doado", "id_organizacao_ong": ONG_ATIVA,
                                                               "data_doacao": ISO}, headers=adm).status_code == 200
    assert c.get(D, headers=ong).json()["items"][0]["id_solicitacao"] is None


def test_uc19_ordenacao_por_data_decrescente_filtros_e_paginacao(c, doa, adm, ong):
    # contrato GET /doacoes (ordenacao, data_de, data_ate, page, size)
    datas = [(HOJE - timedelta(days=n)).isoformat() for n in (8, 2, 5)]
    eqs = []
    for d in datas:
        _, (e,) = _doacao_pronta(c, doa, adm, data=d)
        eqs.append(e["identificacao"])
    todas = c.get(D, headers=ong).json()["items"]
    assert [i["data_doacao"] for i in todas] == sorted(datas, reverse=True)
    assert [i["data_doacao"] for i in c.get(f"{D}?data_de={datas[2]}", headers=ong).json()["items"]] == [datas[1], datas[2]]
    assert [i["data_doacao"] for i in c.get(f"{D}?data_ate={datas[2]}", headers=ong).json()["items"]] == [datas[2], datas[0]]
    assert c.get(f"{D}?data_de={datas[1]}&data_ate={datas[0]}", headers=ong).json()["items"] == []  # invertido: vazio
    p = c.get(f"{D}?page=2&size=2", headers=ong).json()
    assert (p["total"], p["page"], p["size"], len(p["items"])) == (3, 2, 2, 1)


@pytest.mark.parametrize("consulta", ["page=0", "size=0", "size=101", "data_de=ontem", "data_ate=2026-99-99",
                                      f"id_organizacao_ong={GRANDE}", "id_organizacao_ong=a"])
def test_uc19_parametros_de_consulta_invalidos_400(c, ong, adm, consulta):
    # contrato GET /doacoes (400), RNF04
    for h in (ong, adm):
        _erro(c.get(f"{D}?{consulta}", headers=h), 400, "DADOS_INVALIDOS")


def test_uc19_detalhe_da_propria_doacao(c, doa, adm, ong):
    # UC19 passo 4
    _, (e,) = _doacao_pronta(c, doa, adm)
    id_doacao = c.get(D, headers=ong).json()["items"][0]["id_doacao"]
    r = c.get(f"{D}/{id_doacao}", headers=ong)
    assert r.status_code == 200
    assert r.json()["id_doacao"] == id_doacao and r.json()["id_equipamento"] == e["id_equipamento"]
    assert r.json()["data_doacao"] == ISO and r.json()["nome_ong"] == "ONG Cliente"


def test_uc19_fe1_doacao_de_outra_ong_404_sem_vazar(c, doa, adm, ong, nova_conta):
    # UC19 FE1, RN04, RN15, RNF05: "o sistema nega o acesso" (404 igual ao inexistente)
    outra, h_outra = nova_conta(c, "Cliente ONG", "Outra ONG")
    _doacao_pronta(c, doa, adm, ong_id=outra)
    id_dela = c.get(D, headers=h_outra).json()["items"][0]["id_doacao"]
    r = c.get(f"{D}/{id_dela}", headers=ong)
    _erro(r, 404, "NAO_ENCONTRADO")
    assert r.json() == c.get(f"{D}/987654", headers=ong).json()
    assert c.get(f"{D}/{id_dela}", headers=h_outra).status_code == 200


def test_uc19_detalhe_inexistente_e_id_enorme_404(c, ong, adm):
    # UC19 FE1, RNF04
    for h in (ong, adm):
        _erro(c.get(f"{D}/987654", headers=h), 404, "NAO_ENCONTRADO")
        _erro(c.get(f"{D}/{GRANDE}", headers=h), 404, "NAO_ENCONTRADO")


def test_uc19_detalhe_id_nao_numerico_400(c, ong):
    # RNF04: `ongs-elegiveis` e declarada antes de {id}, qualquer outro texto nao numerico e 400
    _erro(c.get(f"{D}/abc", headers=ong), 400, "DADOS_INVALIDOS")


def test_uc19_admin_ve_qualquer_doacao(c, doa, adm):
    # UC19 (visao interna), contrato GET /doacoes/{id}
    _doacao_pronta(c, doa, adm)
    id_doacao = c.get(D, headers=adm).json()["items"][0]["id_doacao"]
    assert c.get(f"{D}/{id_doacao}", headers=adm).status_code == 200


def test_uc19_ong_inativa_nao_acessa(c, ong):
    # UC19 pre-condicao (Cliente ONG ativa), RN09
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ONG_ATIVA,))
    _erro(c.get(D, headers=ong), 403, "CONTA_INATIVA")


def test_uc19_doacao_nova_aparece_imediatamente_para_a_ong(c, doa, adm, ong):
    # UC19 + UC11: a doacao registrada pela destinacao e visivel para a ONG beneficiada
    assert c.get(D, headers=ong).json()["total"] == 0
    _doacao_pronta(c, doa, adm, quantidade=2)
    assert c.get(D, headers=ong).json()["total"] == 2


def test_uc19_so_leitura_nao_ha_escrita_nem_exclusao(c, ong, adm):
    # DP-44, contrato: doacoes expostas somente para leitura; sem exclusao fisica (RN07/contrato)
    for metodo in ("post", "put", "patch", "delete"):
        r = getattr(c, metodo)(D, headers=ong)
        assert r.status_code in (404, 405), (metodo, r.status_code)
    for metodo in ("put", "patch", "delete"):
        r = getattr(c, metodo)(f"{D}/1", headers=adm)
        assert r.status_code in (404, 405), (metodo, r.status_code)
    for metodo in ("put", "patch", "delete"):
        r = getattr(c, metodo)(f"{S}/1", headers=adm)
        assert r.status_code in (404, 405), (metodo, r.status_code)  # DP-43: nao editavel nem cancelavel


# ------------------------------------------------------------------ RNF04/ids enormes em consultas e corpos
def test_ids_enormes_no_corpo_ou_na_consulta_400(c, adm):
    # RNF04
    _erro(c.get(f"{S}?id_organizacao_doadora={GRANDE}", headers=adm), 400, "DADOS_INVALIDOS")
    _erro(c.get(f"{D}?id_organizacao_ong={GRANDE}", headers=adm), 400, "DADOS_INVALIDOS")
    _erro(c.put(f"{S}/1/equipamentos/1/destinacao", json={"destinacao": "Doação", "id_organizacao_ong": GRANDE, "data_doacao": ISO},
                headers=adm), 400, "DADOS_INVALIDOS")


def test_id_no_limite_do_sqlite_nao_estoura(c, adm, doa, ong):
    # RNF04: 2^63-1 e aceito como id (404 por nao existir), 2^63 e 404 pelo limite
    maior = 2 ** 63 - 1
    for url in (f"{S}/{maior}", f"{D}/{maior}"):
        h = adm
        _erro(c.get(url, headers=h), 404, "NAO_ENCONTRADO")
    assert c.get(f"{S}?id_organizacao_doadora={maior}", headers=adm).json()["total"] == 0


# ------------------------------------------------------------------ sem exclusao e sem edicao da solicitacao (DP-43, RN21)
def test_solicitacao_nao_e_editavel_nem_cancelavel(c, doa):
    # DP-43, RN21: depois de criada nao ha PUT/PATCH/DELETE da solicitacao
    sol = _criar_sol(c, doa)
    for metodo in ("put", "patch", "delete"):
        r = getattr(c, metodo)(f"{S}/{sol['id_solicitacao']}", headers=doa)
        assert r.status_code in (404, 405), (metodo, r.status_code)
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Aguardando avaliação"


def test_banco_so_recebe_solicitacao_pelo_endpoint_e_nao_cria_doacao_sem_destinacao(c, doa, adm):
    # RN21, DP-36: avaliar e criar solicitacao nunca criam DOACAO
    sol = _criar_sol(c, doa)
    _avaliar(c, adm, sol)
    assert _tab(c, "DOACAO") == []


# ------------------------------------------------------------------ DP-52 (PUT), DP-53, DP-54
def _corpo_put(e, **kw):
    base = {"identificacao": e["identificacao"], "id_categoria": e["id_categoria"], "modelo": e["modelo"],
            "condicao": e["condicao"], "origem": e["origem"], "data_recebimento": e["data_recebimento"], "valor": e["valor"]}
    base.update(kw)
    return base


def test_dp53_put_sem_id_item_preserva_o_vinculo(c, doa, adm):
    # DP-53, UC07 FA1: campo omitido no PUT preserva o vinculo e a situacao da solicitacao
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    item = sol["itens"][0]["id_item_solicitacao"]
    r = c.put(f"{E}/{e['id_equipamento']}", json=_corpo_put(c.get(f"{E}/{e['id_equipamento']}", headers=adm).json(), modelo="Outro"),
              headers=adm)
    assert r.status_code == 200, r.text
    assert r.json()["id_item_solicitacao"] == item and r.json()["modelo"] == "Outro"
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"


def test_dp53_put_com_null_explicito_desvincula_e_recalcula(c, doa, adm):
    # DP-53, DP-40: null desvincula; solicitacao volta a 'Aguardando avaliacao'
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol)
    atual = c.get(f"{E}/{e['id_equipamento']}", headers=adm).json()
    r = c.put(f"{E}/{e['id_equipamento']}", json=_corpo_put(atual, id_item_solicitacao=None), headers=adm)
    assert r.status_code == 200, r.text
    assert r.json()["id_item_solicitacao"] is None
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Aguardando avaliação"


def test_dp52_put_mudando_de_item_cheio_422_e_mantendo_o_item_200(c, doa, adm):
    # DP-52: o PUT so confere vaga quando o item muda
    sol = _criar_sol(c, doa, [{"tipo": "Notebook", "modelo": "A", "quantidade": 1}, {"tipo": "Monitor", "modelo": "B", "quantidade": 1}])
    e1 = _avaliar(c, adm, sol, 0)
    e2 = _avaliar(c, adm, sol, 1)
    item1 = sol["itens"][0]["id_item_solicitacao"]
    atual2 = c.get(f"{E}/{e2['id_equipamento']}", headers=adm).json()
    r = c.put(f"{E}/{e2['id_equipamento']}", json=_corpo_put(atual2, id_item_solicitacao=item1), headers=adm)
    _erro(r, 422, "ITEM_COMPLETO")
    assert c.get(f"{E}/{e2['id_equipamento']}", headers=adm).json()["id_item_solicitacao"] == sol["itens"][1]["id_item_solicitacao"]
    atual1 = c.get(f"{E}/{e1['id_equipamento']}", headers=adm).json()
    assert c.put(f"{E}/{e1['id_equipamento']}", json=_corpo_put(atual1, id_item_solicitacao=item1), headers=adm).status_code == 200


def test_dp54_destinacao_com_condicao_a_avaliar_422_sem_gravar(c, doa, adm):
    # DP-54, UC10 passo 3-4, FE2: condicao 'A avaliar' bloqueia qualquer destinacao
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, condicao="A avaliar", valor=None)
    for destinacao, extra in (("Reciclagem", {}), ("Venda", {}), ("Doação", {"id_organizacao_ong": ONG_ATIVA, "data_doacao": ISO})):
        r = _destinar(c, adm, sol, e, destinacao, **extra)
        _erro(r, 422, "CONDICAO_NAO_AVALIADA")
        assert r.json()["campos"] == {"condicao": "A avaliar"}
    assert _situacao_eq(c, e["id_equipamento"]) == e["situacao"]
    assert _situacao_sol(c, sol["id_solicitacao"]) == "Em avaliação"


def test_dp54_reciclagem_com_condicao_bom_continua_permitida(c, doa, adm):
    sol = _criar_sol(c, doa)
    e = _avaliar(c, adm, sol, condicao="Bom")
    assert _destinar(c, adm, sol, e, "Reciclagem").status_code == 200
