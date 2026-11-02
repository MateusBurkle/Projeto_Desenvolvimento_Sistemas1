"""Testes da API do Modulo 6 (Relatorios): UC22, UC23, UC24; RF03, RF16, RF17, RF18, RF21;
RN03, RN16, RN17, RN18, RN21; RNF04, RNF05. Contrato: contratos/modulo-6.yaml; DP-57 a DP-60.
Semeado pelo conftest: orgs 1 (Cliente Empresa), 2 (Cliente ONG), 3 (Empresa Doadora), 4 (Cliente Empresa inativa).
Categorias base 1..6 (2 = Notebooks, 3 = Monitores). Dados inseridos direto no banco (somente leitura no modulo)."""
import sqlite3

import pytest

from tests.conftest import SENHA  # noqa: F401

B = "/api/v1/relatorios"
RV, RE, RO = f"{B}/vendas", f"{B}/equipamentos", f"{B}/organizacoes-destinacoes"
GRANDE = 10 ** 25
ORG_EMPRESA, ORG_ONG, ORG_DOADORA = 1, 2, 3
SIT_EQUIP = ["Recebido", "Em avaliação", "Em manutenção", "Recondicionado", "Disponível", "Vendido", "Doado",
             "Destinado à reciclagem"]
ROTAS = [(RV, {"data_de": "2026-01-01", "data_ate": "2026-12-31"}), (RE, {}), (RO, {})]


def _h(t):
    return {"Authorization": f"Bearer {t}"}


def _sql(c, comando, params=()):
    con = sqlite3.connect(c.caminho_banco)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.execute(comando, params)
    con.commit()
    ultimo = cur.lastrowid
    con.close()
    return ultimo


def _erro(r, status, codigo):
    assert r.status_code == status, r.text
    corpo = r.json()
    assert set(corpo) == {"codigo", "mensagem", "campos"}
    assert corpo["codigo"] == codigo and corpo["mensagem"] and isinstance(corpo["campos"], dict)
    return corpo


_seq = [0]


def _eq(c, categoria=2, situacao="Disponível", condicao="Bom", valor=100.0, recebido="2026-03-10", origem="Doação",
        item=None, ativo=1, modelo="Dell X"):
    _seq[0] += 1
    return _sql(c, "INSERT INTO EQUIPAMENTO (id_categoria, id_item_solicitacao, identificacao, modelo, condicao, origem,"
                   " situacao, ativo, valor, data_recebimento) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (categoria, item, f"EQ-{_seq[0]:05d}", modelo, condicao, origem, situacao, ativo, valor, recebido))


def _venda(c, data, situacao="Confirmada", valores=(100.0,), org=ORG_EMPRESA, forma="Pix"):
    idv = _sql(c, "INSERT INTO VENDA (id_organizacao_cliente, data_venda, situacao, forma_pagamento) VALUES (?,?,?,?)",
               (org, data, situacao, forma))
    ids = []
    for v in valores:
        e = _eq(c, situacao="Vendido" if situacao == "Confirmada" else "Disponível", valor=v)
        _sql(c, "INSERT INTO ITEM_VENDA (id_venda, id_equipamento, valor) VALUES (?,?,?)", (idv, e, v))
        ids.append(e)
    return idv, ids


def _solic(c, data="2026-05-01", situacao="Aguardando avaliação", itens=((("Notebook", "Dell", 2)),), org=ORG_DOADORA):
    ids = _sql(c, "INSERT INTO SOLICITACAO (id_organizacao_doadora, data_solicitacao, situacao) VALUES (?,?,?)",
               (org, data, situacao))
    its = [_sql(c, "INSERT INTO ITEM_SOLICITACAO (id_solicitacao, tipo, modelo, quantidade) VALUES (?,?,?,?)",
                (ids, t, m, q)) for t, m, q in itens]
    return ids, its


@pytest.fixture()
def c(cliente):
    return cliente


@pytest.fixture()
def tk(c, token_de):
    return {k: _h(token_de(c, k)) for k in ("admin", "func", "empresa", "ong", "doadora")}


@pytest.fixture()
def adm(tk):
    return tk["admin"]


# ------------------------------------------------------------------ perfis (RN17, RN03, RNF05)
@pytest.mark.parametrize("rota,params", ROTAS)
def test_sem_token_ou_token_invalido_da_401(c, rota, params):
    # RNF05
    assert c.get(rota, params=params).status_code == 401
    assert c.get(rota, params=params, headers=_h("lixo")).status_code == 401


@pytest.mark.parametrize("rota,params", ROTAS)
@pytest.mark.parametrize("perfil", ["empresa", "ong", "doadora"])
def test_perfis_externos_recebem_403(c, tk, rota, params, perfil):
    # RN17, RNF05
    r = c.get(rota, params=params, headers=tk[perfil])
    _erro(r, 403, r.json()["codigo"])


@pytest.mark.parametrize("rota,params", ROTAS)
@pytest.mark.parametrize("perfil", ["admin", "func"])
def test_administrador_e_funcionario_acessam(c, tk, rota, params, perfil):
    # RN17, RN03
    assert c.get(rota, params=params, headers=tk[perfil]).status_code == 200


def test_somente_leitura_outros_metodos_nao_permitidos(c, adm):
    # contrato: nenhuma escrita
    for rota in (RV, RE, RO):
        for m in (c.post, c.put, c.delete, c.patch):
            assert m(rota, headers=adm).status_code in (404, 405)


# ------------------------------------------------------------------ UC22 vendas (RN16)
def test_vendas_somente_confirmadas_e_campos_do_contrato(c, adm):
    # UC22 passo 4-5, RN16
    v1, ids = _venda(c, "2026-03-10", valores=(100.0, 250.5))
    _venda(c, "2026-03-11", situacao="Pendente", valores=(999.0,))
    _venda(c, "2026-03-12", situacao="Cancelada", valores=(888.0,))
    r = c.get(RV, params={"data_de": "2026-03-01", "data_ate": "2026-03-31"}, headers=adm)
    assert r.status_code == 200
    j = r.json()
    assert [v["id_venda"] for v in j["vendas"]] == [v1]
    v = j["vendas"][0]
    assert {"id_venda", "data_venda", "id_organizacao_cliente", "cliente", "forma_pagamento", "quantidade",
            "valor_total", "itens"} <= set(v)
    assert v["cliente"] == "Empresa Cliente" and v["quantidade"] == 2 and v["valor_total"] == 350.5
    assert {i["id_equipamento"] for i in v["itens"]} == set(ids)
    assert {"identificacao", "modelo", "categoria", "valor"} <= set(v["itens"][0])
    assert (j["total_vendas"], j["total_equipamentos"], j["valor_total"]) == (1, 2, 350.5)
    assert j["data_de"] == "2026-03-01" and j["data_ate"] == "2026-03-31"


def test_vendas_periodo_inclusivo_e_fora_excluido(c, adm):
    # RN16: data entre data_de e data_ate, inclusive
    a, _ = _venda(c, "2026-03-01")
    b, _ = _venda(c, "2026-03-31")
    _venda(c, "2026-02-28")
    _venda(c, "2026-04-01")
    j = c.get(RV, params={"data_de": "2026-03-01", "data_ate": "2026-03-31"}, headers=adm).json()
    assert [v["id_venda"] for v in j["vendas"]] == [a, b]


def test_vendas_mesmo_dia_e_ordenacao_por_data_e_id(c, adm):
    # contrato: ordenacao data_venda, id_venda crescentes
    v3, _ = _venda(c, "2026-03-20")
    v1, _ = _venda(c, "2026-03-05")
    v2, _ = _venda(c, "2026-03-05")
    j = c.get(RV, params={"data_de": "2026-03-05", "data_ate": "2026-03-20"}, headers=adm).json()
    assert [v["id_venda"] for v in j["vendas"]] == [v1, v2, v3]
    j = c.get(RV, params={"data_de": "2026-03-20", "data_ate": "2026-03-20"}, headers=adm).json()
    assert [v["id_venda"] for v in j["vendas"]] == [v3]


def test_vendas_total_e_soma_das_vendas_listadas(c, adm):
    # RN16
    _venda(c, "2026-06-01", valores=(10.10, 20.20))
    _venda(c, "2026-06-02", valores=(0.30,))
    _venda(c, "2026-06-03", situacao="Cancelada", valores=(5000.0,))
    j = c.get(RV, params={"data_de": "2026-06-01", "data_ate": "2026-06-30"}, headers=adm).json()
    assert round(sum(v["valor_total"] for v in j["vendas"]), 2) == j["valor_total"] == 30.6
    assert j["total_equipamentos"] == sum(v["quantidade"] for v in j["vendas"]) == 3


def test_vendas_periodo_sem_vendas_da_200_vazio_total_zero(c, adm):
    # UC22 FA1
    _venda(c, "2026-03-10", situacao="Pendente")
    r = c.get(RV, params={"data_de": "2026-01-01", "data_ate": "2026-12-31"}, headers=adm)
    assert r.status_code == 200
    j = r.json()
    assert j["vendas"] == [] and j["total_vendas"] == 0 and j["total_equipamentos"] == 0 and j["valor_total"] == 0


def test_vendas_funcionario_ve_o_mesmo_relatorio(c, tk):
    # RN03
    _venda(c, "2026-03-10")
    p = {"data_de": "2026-03-01", "data_ate": "2026-03-31"}
    assert c.get(RV, params=p, headers=tk["func"]).json() == c.get(RV, params=p, headers=tk["admin"]).json()


@pytest.mark.parametrize("params,campo", [
    ({}, "data_de"),
    ({"data_de": "2026-01-01"}, "data_ate"),
    ({"data_ate": "2026-01-01"}, "data_de"),
    ({"data_de": "", "data_ate": ""}, "data_de"),
    ({"data_de": "2026-13-01", "data_ate": "2026-12-31"}, "data_de"),
    ({"data_de": "2026-01-01", "data_ate": "2026-02-30"}, "data_ate"),
    ({"data_de": "abc", "data_ate": "2026-12-31"}, "data_de"),
    ({"data_de": "01/01/2026", "data_ate": "2026-12-31"}, "data_de"),
    ({"data_de": "2026-1-1", "data_ate": "2026-12-31"}, "data_de"),
    ({"data_de": "2026-12-31", "data_ate": "2026-01-01"}, "data_de"),  # invertido
])
def test_vendas_periodo_ausente_invalido_ou_invertido_da_400(c, adm, params, campo):
    # UC22 FE1
    corpo = _erro(c.get(RV, params=params, headers=adm), 400, "PERIODO_INVALIDO")
    assert campo in corpo["campos"]


# ------------------------------------------------------------------ UC23 equipamentos (RN17)
def test_equipamentos_sem_filtros_lista_todos_inclusive_inativos(c, adm):
    # UC23 FA1
    a = _eq(c)
    b = _eq(c, ativo=0, situacao="Recebido")
    j = c.get(RE, headers=adm).json()
    assert j["total"] == 2 and j["page"] == 1 and j["size"] == 20
    assert [i["id_equipamento"] for i in j["items"]] == [a, b]
    assert j["items"][1]["ativo"] is False and j["items"][0]["ativo"] is True
    campos = {"id_equipamento", "identificacao", "modelo", "id_categoria", "categoria", "condicao", "situacao", "ativo",
              "valor", "data_recebimento", "origem", "destinacao", "destino_detalhe", "data_destinacao"}
    assert campos <= set(j["items"][0])


def test_equipamentos_vazio_da_200(c, adm):
    j = c.get(RE, headers=adm).json()
    assert j["items"] == [] and j["total"] == 0 and j["resumo_por_situacao"] == {}


def test_equipamentos_filtra_por_categoria_situacao_e_periodo(c, adm):
    # UC23 passo 3-4
    e1 = _eq(c, categoria=2, situacao="Disponível", recebido="2026-03-10")
    e2 = _eq(c, categoria=3, situacao="Disponível", recebido="2026-03-10")
    e3 = _eq(c, categoria=2, situacao="Recebido", recebido="2026-03-10")
    e4 = _eq(c, categoria=2, situacao="Disponível", recebido="2026-04-10")
    ids = lambda p: [i["id_equipamento"] for i in c.get(RE, params=p, headers=adm).json()["items"]]  # noqa: E731
    assert ids({"id_categoria": 2}) == [e1, e3, e4]
    assert ids({"id_categoria": 3}) == [e2]
    assert ids({"situacao": "Recebido"}) == [e3]
    assert ids({"data_de": "2026-04-01"}) == [e4]
    assert ids({"data_ate": "2026-03-10"}) == [e1, e2, e3]  # inclusivo
    assert ids({"data_de": "2026-03-10", "data_ate": "2026-03-10"}) == [e1, e2, e3]
    assert ids({"id_categoria": 2, "situacao": "Disponível", "data_de": "2026-03-01", "data_ate": "2026-03-31"}) == [e1]


def test_equipamentos_categoria_inexistente_ou_enorme_da_200_vazio(c, adm):
    _eq(c)
    for cat in (999, 0, -5, GRANDE):
        r = c.get(RE, params={"id_categoria": cat}, headers=adm)
        assert r.status_code == 200 and r.json()["items"] == [] and r.json()["total"] == 0, cat


@pytest.mark.parametrize("params,campo", [
    ({"situacao": "Inexistente"}, "situacao"),
    ({"situacao": "disponível"}, "situacao"),
    ({"data_de": "2026-02-30"}, "data_de"),
    ({"data_ate": "xx"}, "data_ate"),
    ({"data_de": "2026-12-31", "data_ate": "2026-01-01"}, "data_de"),
])
def test_equipamentos_filtros_invalidos_da_400(c, adm, params, campo):
    # UC23 FE1
    assert campo in _erro(c.get(RE, params=params, headers=adm), 400, "FILTRO_INVALIDO")["campos"]


def test_equipamentos_origem_e_destinacoes(c, adm):
    # UC23 passo 4, DP-59
    _, (vend,) = _venda(c, "2026-03-10", valores=(77.0,))
    doado = _eq(c, situacao="Doado")
    _sql(c, "INSERT INTO DOACAO (id_equipamento, id_organizacao_ong, data_doacao) VALUES (?,?,?)", (doado, ORG_ONG, "2026-04-02"))
    recic = _eq(c, situacao="Destinado à reciclagem", condicao="Inservível", origem="Descarte")
    disp = _eq(c, situacao="Disponível")
    rec = _eq(c, situacao="Recebido", origem="Compra")
    por = {i["id_equipamento"]: i for i in c.get(RE, headers=adm).json()["items"]}
    assert por[vend]["destinacao"] == "Venda" and por[vend]["destino_detalhe"] == "Empresa Cliente"
    assert por[vend]["data_destinacao"] == "2026-03-10"
    assert por[doado]["destinacao"] == "Doação" and por[doado]["destino_detalhe"] == "ONG Cliente"
    assert por[doado]["data_destinacao"] == "2026-04-02"
    assert por[recic]["destinacao"] == "Reciclagem" and por[recic]["destino_detalhe"] is None
    assert por[disp]["destinacao"] == "Venda (disponível)"
    assert por[rec]["destinacao"] is None and por[rec]["destino_detalhe"] is None and por[rec]["data_destinacao"] is None
    assert por[recic]["origem"] == "Descarte" and por[rec]["origem"] == "Compra"


def test_equipamento_vendido_em_venda_cancelada_nao_mostra_cliente(c, adm):
    # RN16/DP-59: so venda Confirmada informa cliente
    idv, (e,) = _venda(c, "2026-03-10", situacao="Cancelada")
    _sql(c, "UPDATE EQUIPAMENTO SET situacao='Vendido' WHERE id_equipamento=?", (e,))
    it = c.get(RE, headers=adm).json()["items"][0]
    assert it["destino_detalhe"] is None


def test_equipamentos_resumo_conta_todos_os_filtrados_nao_so_a_pagina(c, adm):
    for _ in range(5):
        _eq(c, situacao="Disponível")
    for _ in range(3):
        _eq(c, situacao="Recebido")
    _eq(c, situacao="Vendido", categoria=3)
    j = c.get(RE, params={"id_categoria": 2, "size": 2}, headers=adm).json()
    assert len(j["items"]) == 2 and j["total"] == 8 and j["size"] == 2
    assert j["resumo_por_situacao"] == {"Disponível": 5, "Recebido": 3}
    j2 = c.get(RE, params={"id_categoria": 2, "size": 2, "page": 4}, headers=adm).json()
    assert len(j2["items"]) == 2 and j2["page"] == 4
    assert c.get(RE, params={"id_categoria": 2, "size": 2, "page": 9}, headers=adm).json()["items"] == []


def test_equipamentos_paginacao_ordenada_por_id(c, adm):
    ids = [_eq(c) for _ in range(5)]
    p1 = c.get(RE, params={"size": 3, "page": 1}, headers=adm).json()
    p2 = c.get(RE, params={"size": 3, "page": 2}, headers=adm).json()
    assert [i["id_equipamento"] for i in p1["items"] + p2["items"]] == ids


def test_equipamento_com_um_item_de_venda_nao_duplica_linhas(c, adm):
    # LEFT JOIN nao pode duplicar equipamento
    _venda(c, "2026-03-10", valores=(1.0, 2.0))
    j = c.get(RE, headers=adm).json()
    ids = [i["id_equipamento"] for i in j["items"]]
    assert len(ids) == len(set(ids)) == j["total"] == 2


# ------------------------------------------------------------------ UC24 organizacoes e destinacoes (RN18, RN21)
def test_org_lista_todas_as_solicitacoes_inclusive_sem_destinacao(c, adm):
    # UC24 passo 2-3, FA1, RN18
    s1, _ = _solic(c, data="2026-05-01", situacao="Aguardando avaliação")
    s2, _ = _solic(c, data="2026-05-02", situacao="Em avaliação")
    s3, _ = _solic(c, data="2026-05-03", situacao="Avaliada")
    j = c.get(RO, headers=adm).json()
    assert [s["id_solicitacao"] for s in j["items"]] == [s3, s2, s1]  # data desc
    assert j["total"] == 3 and j["page"] == 1 and j["size"] == 20
    s = j["items"][-1]
    assert s["empresa_doadora"] == "Doadora SA" and s["id_organizacao_doadora"] == ORG_DOADORA
    assert s["avaliacao_pendente"] is True and s["situacao"] == "Aguardando avaliação"
    assert s["itens"][0]["tipo"] == "Notebook" and s["itens"][0]["quantidade"] == 2
    assert s["itens"][0]["equipamentos_cadastrados"] == 0 and s["itens"][0]["equipamentos"] == []
    assert any("faltam 2 equipamentos" in p for p in s["pendencias"])


def test_org_ordem_por_data_e_id_decrescentes(c, adm):
    a, _ = _solic(c, data="2026-05-01")
    b, _ = _solic(c, data="2026-05-01")
    d, _ = _solic(c, data="2026-04-01")
    assert [s["id_solicitacao"] for s in c.get(RO, headers=adm).json()["items"]] == [b, a, d]


def test_org_pendencias_condicao_a_avaliar_e_destinacao_nao_registrada(c, adm):
    # UC24 FE1: nunca concluida
    s, (it,) = _solic(c, itens=[("Notebook", "Dell", 1)])
    e = _eq(c, condicao="A avaliar", situacao="Recebido", item=it)
    sol = c.get(RO, headers=adm).json()["items"][0]
    eq = sol["itens"][0]["equipamentos"][0]
    assert eq["destinacao"] is None and eq["ong_beneficiada"] is None and eq["data_doacao"] is None
    assert sol["avaliacao_pendente"] is True
    assert f"Equipamento {e}: condição a avaliar" in sol["pendencias"]
    assert f"Equipamento {e}: destinação não registrada" in sol["pendencias"]


@pytest.mark.parametrize("sit", ["Recebido", "Em avaliação", "Em manutenção", "Recondicionado"])
def test_org_situacoes_sem_destinacao_ficam_pendentes(c, adm, sit):
    s, (it,) = _solic(c, itens=[("Notebook", "Dell", 1)])
    e = _eq(c, condicao="Bom", situacao=sit, item=it)
    sol = c.get(RO, headers=adm).json()["items"][0]
    assert sol["avaliacao_pendente"] is True and sol["itens"][0]["equipamentos"][0]["destinacao"] is None
    assert sol["pendencias"] == [f"Equipamento {e}: destinação não registrada"]


def test_org_solicitacao_totalmente_destinada_nao_tem_pendencia(c, adm):
    s, (it,) = _solic(c, situacao="Avaliada", itens=[("Notebook", "Dell", 3)])
    e1 = _eq(c, situacao="Disponível", item=it)
    e2 = _eq(c, situacao="Vendido", item=it)
    e3 = _eq(c, situacao="Destinado à reciclagem", condicao="Inservível", item=it)
    sol = c.get(RO, headers=adm).json()["items"][0]
    assert sol["avaliacao_pendente"] is False and sol["pendencias"] == []
    assert sol["itens"][0]["equipamentos_cadastrados"] == 3
    d = {e["id_equipamento"]: e["destinacao"] for e in sol["itens"][0]["equipamentos"]}
    assert d == {e1: "Venda (disponível)", e2: "Venda", e3: "Reciclagem"}  # RN21: destinos diferentes


def test_org_reciclagem_sem_venda_nem_doacao(c, adm):
    # UC24 FA2
    s, (it,) = _solic(c, itens=[("Monitor", "LG", 1)])
    e = _eq(c, situacao="Destinado à reciclagem", condicao="Inservível", item=it)
    eq = c.get(RO, headers=adm).json()["items"][0]["itens"][0]["equipamentos"][0]
    assert eq["destinacao"] == "Reciclagem" and eq["ong_beneficiada"] is None and eq["data_doacao"] is None


def test_org_doacao_mostra_ong_e_data(c, adm):
    # UC24 passo 4, RF18
    s, (it,) = _solic(c, itens=[("Notebook", "Dell", 1)])
    e = _eq(c, situacao="Doado", item=it)
    _sql(c, "INSERT INTO DOACAO (id_equipamento, id_organizacao_ong, data_doacao) VALUES (?,?,?)", (e, ORG_ONG, "2026-06-15"))
    eq = c.get(RO, headers=adm).json()["items"][0]["itens"][0]["equipamentos"][0]
    assert eq["destinacao"] == "Doação" and eq["ong_beneficiada"] == "ONG Cliente" and eq["data_doacao"] == "2026-06-15"


def test_org_venda_nao_mostra_ong(c, adm):
    s, (it,) = _solic(c, itens=[("Notebook", "Dell", 1)])
    _eq(c, situacao="Vendido", item=it)
    eq = c.get(RO, headers=adm).json()["items"][0]["itens"][0]["equipamentos"][0]
    assert eq["destinacao"] == "Venda" and eq["ong_beneficiada"] is None


def test_org_filtros_empresa_situacao_periodo(c, adm, hash_senha):
    outra = _sql(c, "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao)"
                    " VALUES (?,?,?,?,?,?,?)", ("99999999999999", "Outra Doadora", "Empresa Doadora", "11999999999",
                                                "o@o.com", "Rua", "Ativa"))
    a, _ = _solic(c, data="2026-05-01", situacao="Avaliada")
    b, _ = _solic(c, data="2026-06-01", situacao="Em avaliação", org=outra)
    ids = lambda p: [s["id_solicitacao"] for s in c.get(RO, params=p, headers=adm).json()["items"]]  # noqa: E731
    assert ids({"id_organizacao_doadora": outra}) == [b]
    assert ids({"id_organizacao_doadora": ORG_DOADORA}) == [a]
    assert ids({"situacao": "Avaliada"}) == [a]
    assert ids({"data_de": "2026-06-01"}) == [b]
    assert ids({"data_ate": "2026-05-01"}) == [a]
    assert ids({"data_de": "2026-05-01", "data_ate": "2026-06-01"}) == [b, a]
    assert ids({"id_organizacao_doadora": GRANDE}) == [] and ids({"id_organizacao_doadora": 0}) == []


@pytest.mark.parametrize("params,campo", [
    ({"situacao": "Pendente"}, "situacao"),
    ({"data_de": "ontem"}, "data_de"),
    ({"data_ate": "2026-00-10"}, "data_ate"),
    ({"data_de": "2026-12-31", "data_ate": "2026-01-01"}, "data_de"),
])
def test_org_filtros_invalidos_da_400(c, adm, params, campo):
    # UC24 filtros; contrato FILTRO_INVALIDO
    assert campo in _erro(c.get(RO, params=params, headers=adm), 400, "FILTRO_INVALIDO")["campos"]


def test_org_paginacao_total_e_itens(c, adm):
    for i in range(5):
        _solic(c, data=f"2026-05-0{i + 1}")
    j = c.get(RO, params={"size": 2, "page": 3}, headers=adm).json()
    assert j["total"] == 5 and len(j["items"]) == 1 and j["page"] == 3
    assert c.get(RO, params={"size": 2, "page": 4}, headers=adm).json()["items"] == []


def test_org_equipamentos_de_outra_solicitacao_nao_vazam(c, adm):
    s1, (i1,) = _solic(c, itens=[("A", "a", 1)])
    s2, (i2,) = _solic(c, itens=[("B", "b", 1)])
    e = _eq(c, situacao="Disponível", item=i1)
    por = {s["id_solicitacao"]: s for s in c.get(RO, headers=adm).json()["items"]}
    assert [x["id_equipamento"] for x in por[s1]["itens"][0]["equipamentos"]] == [e]
    assert por[s2]["itens"][0]["equipamentos"] == []


def test_org_item_com_mais_equipamentos_que_o_informado_nao_gera_pendencia_negativa(c, adm):
    s, (it,) = _solic(c, itens=[("A", "a", 1)])
    _eq(c, item=it)
    _eq(c, item=it)
    sol = c.get(RO, headers=adm).json()["items"][0]
    assert not any("faltam" in p for p in sol["pendencias"])


# ------------------------------------------------------------------ robustez (RNF04): nunca 500
@pytest.mark.parametrize("rota,params", [
    (RV, {"data_de": "9999-12-31", "data_ate": "9999-12-31"}),
    (RV, {"data_de": "0001-01-01", "data_ate": "0001-01-01"}),
    (RV, {"data_de": "0000-01-01", "data_ate": "2026-01-01"}),
    (RV, {"data_de": "2026-01-01\x00", "data_ate": "2026-01-02"}),
    (RV, {"data_de": "٢٠٢٦-٠١-٠١", "data_ate": "2026-01-02"}),
    (RV, {"data_de": "2026-01-01' OR 1=1 --", "data_ate": "2026-01-02"}),
    (RE, {"id_categoria": GRANDE}), (RE, {"id_categoria": "abc"}), (RE, {"id_categoria": -GRANDE}),
    (RE, {"page": GRANDE}), (RE, {"page": 10 ** 9}), (RE, {"page": 10 ** 9 + 1}), (RE, {"page": 0}), (RE, {"page": -1}),
    (RE, {"size": 0}), (RE, {"size": 101}), (RE, {"size": GRANDE}), (RE, {"size": "x"}), (RE, {"page": 2 ** 63}),
    (RE, {"page": 2 ** 62, "size": 100}),
    (RE, {"data_de": "2026-02-30"}), (RE, {"situacao": "x" * 5000}), (RE, {"situacao": "'; DROP TABLE EQUIPAMENTO;--"}),
    (RO, {"id_organizacao_doadora": GRANDE}), (RO, {"id_organizacao_doadora": "x"}), (RO, {"page": GRANDE}),
    (RO, {"page": 10 ** 9}), (RO, {"page": 0}), (RO, {"size": 101}), (RO, {"size": GRANDE}),
    (RO, {"page": 2 ** 62, "size": 100}), (RO, {"data_de": "9999-99-99"}), (RO, {"situacao": "%"}),
])
def test_entradas_absurdas_nunca_dao_500(c, adm, rota, params):
    r = c.get(rota, params=params, headers=adm)
    assert r.status_code < 500, (rota, params, r.text)
    assert r.status_code in (200, 400), r.status_code
    if r.status_code == 400:
        assert r.json()["codigo"] in ("PERIODO_INVALIDO", "FILTRO_INVALIDO", "DADOS_INVALIDOS")


def test_page_e_size_invalidos_dao_400_dados_invalidos(c, adm):
    for rota in (RE, RO):
        for p in ({"page": 0}, {"size": 0}, {"size": 101}, {"page": "x"}):
            _erro(c.get(rota, params=p, headers=adm), 400, "DADOS_INVALIDOS")


def test_relatorios_nao_alteram_o_banco(c, adm):
    # contrato: somente leitura
    _venda(c, "2026-03-10")
    s, (it,) = _solic(c)
    antes = [tuple(r) for r in sqlite3.connect(c.caminho_banco).execute(
        "SELECT (SELECT COUNT(*) FROM VENDA),(SELECT COUNT(*) FROM EQUIPAMENTO),(SELECT COUNT(*) FROM SOLICITACAO),"
        "(SELECT COUNT(*) FROM DOACAO)")]
    c.get(RV, params={"data_de": "2026-01-01", "data_ate": "2026-12-31"}, headers=adm)
    c.get(RE, headers=adm)
    c.get(RO, headers=adm)
    depois = [tuple(r) for r in sqlite3.connect(c.caminho_banco).execute(
        "SELECT (SELECT COUNT(*) FROM VENDA),(SELECT COUNT(*) FROM EQUIPAMENTO),(SELECT COUNT(*) FROM SOLICITACAO),"
        "(SELECT COUNT(*) FROM DOACAO)")]
    assert antes == depois
