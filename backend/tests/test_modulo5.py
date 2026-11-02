"""Testes da API do Modulo 5 (Loja e vendas): UC12, UC13, UC14, UC15, UC16, UC17, UC18, UC21.
Requisitos: RF02, RF03, RF04, RF13, RF14, RF15, RF19, RF20; RN02, RN03, RN04, RN13, RN14, RN15, RN19, RN20; RNF03, RNF04, RNF05.
Contrato: contratos/modulo-5.yaml v1.0.0 (inclui esclarecimentos); DP-45 a DP-51. Contas ficticias do conftest.
Semeado pelo conftest: orgs 1 (Cliente Empresa), 2 (Cliente ONG), 3 (Empresa Doadora), 4 (Cliente Empresa INATIVA).
Equipamentos sao inseridos direto no banco (o Modulo 3 ja tem testes proprios); categorias base 1..6 (2 = Notebooks, 3 = Monitores)."""
import re
import sqlite3
import threading
from datetime import date, timedelta

import pytest

from tests.conftest import SENHA

B = "/api/v1"
V = f"{B}/vendas"
CAT = f"{B}/catalogo"
NF = f"{B}/notas-fiscais"
HOJE = date.today()
ISO = HOJE.isoformat()
GRANDE = 10 ** 20
CHAVES = ["admin", "func", "empresa", "ong", "doadora"]
FORMAS = ["Pix", "Boleto", "Transferência bancária", "Cartão de crédito"]
ORG_EMPRESA = 1
ORG_INATIVA = 4
MARCA = "SIMULADA – sem valor fiscal"


# ------------------------------------------------------------------ utilitarios
def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _consulta(c, comando, params=()):
    con = sqlite3.connect(c.caminho_banco)
    con.row_factory = sqlite3.Row
    try:
        return con.execute(comando, params).fetchall()
    finally:
        con.close()


def _sql(c, comando, params=()):
    con = sqlite3.connect(c.caminho_banco)
    con.execute("PRAGMA foreign_keys = ON")
    cur = con.execute(comando, params)
    con.commit()
    ultimo = cur.lastrowid
    con.close()
    return ultimo


def _tab(c, nome):
    return [tuple(r) for r in _consulta(c, f"SELECT * FROM {nome} ORDER BY 1")]


def _erro(r, status, codigo):
    assert r.status_code == status, r.text
    corpo = r.json()
    assert set(corpo) == {"codigo", "mensagem", "campos"}
    assert corpo["codigo"] == codigo
    assert corpo["mensagem"] and isinstance(corpo["campos"], dict)
    return corpo


_seq = [0]


def _eq(c, modelo="Dell Latitude 5420", valor=1500.0, categoria=2, condicao="Bom", situacao="Disponível", ativo=1, ident=None):
    """Insere um equipamento direto no banco (UC07 ja coberto no Modulo 3)."""
    _seq[0] += 1
    return _sql(c, "INSERT INTO EQUIPAMENTO (id_categoria, identificacao, modelo, condicao, origem, situacao, ativo, valor, data_recebimento)"
                   " VALUES (?,?,?,?,?,?,?,?,?)",
                (categoria, ident or f"EQ-{_seq[0]:05d}", modelo, condicao, "Doação", situacao, ativo, valor,
                 (HOJE - timedelta(days=30)).isoformat()))


def _eqs(c, n, **kw):
    return [_eq(c, **kw) for _ in range(n)]


def _sit_eq(c, i):
    return _consulta(c, "SELECT situacao FROM EQUIPAMENTO WHERE id_equipamento=?", (i,))[0][0]


def _venda_sql(c, org=ORG_EMPRESA, data=ISO, situacao="Confirmada", forma="Pix", itens=None, valor=100.0):
    """VENDA + ITEM_VENDA direto no banco (historico). `itens`: lista de ids ou None para criar 1 equipamento."""
    idv = _sql(c, "INSERT INTO VENDA (id_organizacao_cliente, data_venda, situacao, forma_pagamento) VALUES (?,?,?,?)",
               (org, data, situacao, forma))
    if itens is None:
        itens = [_eq(c, situacao="Vendido" if situacao == "Confirmada" else "Disponível", valor=valor)]
    for i in itens:
        _sql(c, "INSERT INTO ITEM_VENDA (id_venda, id_equipamento, valor) VALUES (?,?,?)", (idv, i, valor))
    return idv


@pytest.fixture()
def c(cliente):
    return cliente


@pytest.fixture()
def adm(c, token_de):
    return _h(token_de(c, "admin"))


@pytest.fixture()
def fun(c, token_de):
    return _h(token_de(c, "func"))


@pytest.fixture()
def emp(c, token_de):
    return _h(token_de(c, "empresa"))


@pytest.fixture()
def ong(c, token_de):
    return _h(token_de(c, "ong"))


@pytest.fixture()
def doa(c, token_de):
    return _h(token_de(c, "doadora"))


@pytest.fixture()
def todos(adm, fun, emp, ong, doa):
    return {"admin": adm, "func": fun, "empresa": emp, "ong": ong, "doadora": doa}


@pytest.fixture()
def emp2(c, hash_senha):
    """Segunda organizacao Cliente Empresa (Ativa), para isolamento por organizacao (RN04, RNF05)."""
    id_org = _sql(c, "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao)"
                     " VALUES (?,?,?,?,?,?,?)",
                  ("99999999999999", "Outra Empresa", "Cliente Empresa", "11999999999", "outra@org.com", "Rua Z, 3", "Ativa"))
    _sql(c, "INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (?,?,?,?,?)",
         (id_org, "outra@teste.com", "Cliente Empresa", hash_senha, "Nome Outra"))
    r = c.post(f"{B}/auth/login", json={"email": "outra@teste.com", "senha": SENHA})
    assert r.status_code == 200, r.text
    c.id_org2 = id_org
    return _h(r.json()["access_token"])


def _pedido(c, h, ids):
    r = c.post(V, json={"ids_equipamento": ids}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _confirmar(c, h, idv, data=ISO, forma="Pix"):
    return c.post(f"{V}/{idv}/confirmar", json={"data_venda": data, "forma_pagamento": forma}, headers=h)


def _confirmada(c, emp, adm, n=2, **kw):
    """Cria pedido do Cliente Empresa e confirma pelo Administrador; devolve (venda, ids)."""
    ids = _eqs(c, n, **kw)
    p = _pedido(c, emp, ids)
    r = _confirmar(c, adm, p["id_venda"])
    assert r.status_code == 200, r.text
    return r.json(), ids


# ================================================================== matriz perfil x rota (RN01, RN03, RN13, RN15, RN19, RN20)
# (metodo, rota, corpo, perfis autorizados)
ROTAS = [
    ("get", f"{CAT}", None, {"empresa"}),                                                         # UC12
    ("get", f"{CAT}/1", None, {"empresa"}),                                                       # UC12
    ("get", f"{V}", None, {"admin", "func", "empresa"}),                                          # UC18, UC21, RN15
    ("post", f"{V}", {"ids_equipamento": [1]}, {"empresa"}),                                      # UC13, RN13
    ("get", f"{V}/1", None, {"admin", "func", "empresa"}),                                        # UC14, UC18, UC21
    ("patch", f"{V}/1", {"forma_pagamento": "Pix"}, {"admin", "func"}),                           # UC14 FA1
    ("put", f"{V}/1/itens", {"ids_equipamento": [1]}, {"admin", "func", "empresa"}),              # UC13 FA1
    ("post", f"{V}/1/cancelar", None, {"admin", "func", "empresa"}),                              # UC13 FA1, UC14 FA2
    ("post", f"{V}/1/confirmar", {"data_venda": ISO, "forma_pagamento": "Pix"}, {"admin", "func"}),  # UC14, RN03
    ("post", f"{V}/1/nota-fiscal", None, {"admin"}),                                              # UC16, RN19
    ("get", f"{NF}", None, {"admin", "empresa"}),                                                 # UC17, RN20
    ("get", f"{NF}/1", None, {"admin", "empresa"}),                                               # UC17
    ("get", f"{NF}/1/download", None, {"admin", "empresa"}),                                      # UC17
]


def _chamar(c, metodo, rota, corpo, headers):
    kw = {"headers": headers}
    if corpo is not None:
        kw["json"] = corpo
    return getattr(c, metodo)(rota, **kw)


@pytest.mark.parametrize("metodo,rota,corpo,permitidos", ROTAS)
def test_matriz_perfil_x_rota_proibidos_recebem_403(c, todos, metodo, rota, corpo, permitidos):
    # RN01, RN03, RN13, RN15, RN19, RN20, RNF05: perfil sem autorizacao -> 403 SEM_PERMISSAO, antes de qualquer outra regra
    antes = {t: _tab(c, t) for t in ("VENDA", "ITEM_VENDA", "NOTA_FISCAL_SIMULADA")}
    for chave in CHAVES:
        if chave in permitidos:
            continue
        r = _chamar(c, metodo, rota, corpo, todos[chave])
        _erro(r, 403, "SEM_PERMISSAO")
    assert antes == {t: _tab(c, t) for t in antes}


@pytest.mark.parametrize("metodo,rota,corpo,permitidos", ROTAS)
def test_matriz_perfil_x_rota_autorizados_nao_recebem_403_nem_401(c, todos, metodo, rota, corpo, permitidos):
    # RN01: perfil autorizado passa pela guarda (resposta de negocio: 200/201/404/422, nunca 401/403)
    for chave in permitidos:
        r = _chamar(c, metodo, rota, corpo, todos[chave])
        assert r.status_code not in (401, 403, 500), (chave, r.status_code, r.text)


@pytest.mark.parametrize("metodo,rota,corpo,permitidos", ROTAS)
def test_sem_token_ou_token_invalido_da_401(c, metodo, rota, corpo, permitidos):
    # RNF05, UC04: NAO_AUTENTICADO
    _erro(_chamar(c, metodo, rota, corpo, {}), 401, "NAO_AUTENTICADO")
    _erro(_chamar(c, metodo, rota, corpo, _h("token.invalido.xyz")), 401, "NAO_AUTENTICADO")


def test_organizacao_inativada_apos_login_recebe_403_conta_inativa(c, emp):
    # UC13 FE2, UC12 pre-condicao, RN13: a conta da organizacao inativa e barrada pelo token (CONTA_INATIVA)
    ids = _eqs(c, 1)
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ORG_EMPRESA,))
    _erro(c.post(V, json={"ids_equipamento": ids}, headers=emp), 403, "CONTA_INATIVA")
    _erro(c.get(CAT, headers=emp), 403, "CONTA_INATIVA")
    assert _tab(c, "VENDA") == []


def test_criar_pedido_cliente_inativo_no_service_da_422_cliente_inativo(c):
    # UC13 FE2, RN13: defesa no service (a rota ja bloqueia pelo token); nada e gravado
    from app.db import conectar
    from app.erros import ErroApi
    from app.vendas import schemas, service
    ids = _eqs(c, 1)
    con = conectar()
    try:
        with pytest.raises(ErroApi) as exc:
            service.criar_pedido(con, {"id_organizacao": ORG_INATIVA, "perfil": "Cliente Empresa"},
                                 schemas.PedidoEntrada(ids_equipamento=ids))
    finally:
        con.close()
    assert exc.value.status == 422 and exc.value.codigo == "CLIENTE_INATIVO"
    assert _tab(c, "VENDA") == [] and _tab(c, "ITEM_VENDA") == []


# ================================================================== UC12 catalogo (RN13, DP-50)
def test_catalogo_lista_com_campos_do_contrato(c, emp):
    # UC12 passos 1-2, RN13
    a = _eq(c, modelo="Dell Latitude", valor=1500.5)
    r = c.get(CAT, headers=emp)
    assert r.status_code == 200
    j = r.json()
    assert set(j) == {"items", "total", "page", "size"} and j["total"] == 1 and j["page"] == 1 and j["size"] == 20
    item = j["items"][0]
    assert set(item) == {"id_equipamento", "identificacao", "id_categoria", "categoria_nome", "modelo", "condicao", "valor"}
    assert item["id_equipamento"] == a and item["categoria_nome"] == "Notebooks" and item["valor"] == 1500.5


def test_catalogo_vazio_da_200_com_lista_vazia(c, emp):
    # UC12 FE1: nenhum item disponivel -> 200 items [] (a tela informa)
    r = c.get(CAT, headers=emp)
    assert r.status_code == 200
    assert r.json() == {"items": [], "total": 0, "page": 1, "size": 20}


@pytest.mark.parametrize("campos", [
    {"ativo": 0},                                  # inativo
    {"situacao": "Recebido"}, {"situacao": "Em avaliação"}, {"situacao": "Em manutenção"}, {"situacao": "Recondicionado"},
    {"situacao": "Vendido"}, {"situacao": "Doado"}, {"situacao": "Destinado à reciclagem"},
    {"condicao": "A avaliar"}, {"condicao": "Sem condições de reuso"},
    {"valor": None}, {"valor": 0}, {"valor": -5},
])
def test_catalogo_exclui_equipamento_fora_das_regras(c, emp, campos):
    # UC12 passo 2, RN13, DP-50: so ativo, Disponivel, condicao apta, valor > 0
    ruim = _eq(c, **campos)
    bom = _eq(c, modelo="Bom")
    ids = [i["id_equipamento"] for i in c.get(CAT, headers=emp).json()["items"]]
    assert ids == [bom]
    _erro(c.get(f"{CAT}/{ruim}", headers=emp), 404, "NAO_ENCONTRADO")
    assert c.get(f"{CAT}/{bom}", headers=emp).status_code == 200


def test_catalogo_ordena_por_modelo_sem_caixa_depois_id(c, emp):
    # UC12 passo 1, contrato: ordenado por modelo, depois id
    b = _eq(c, modelo="beta")
    a2 = _eq(c, modelo="Alfa")
    a1 = _eq(c, modelo="alfa")
    z = _eq(c, modelo="Zeta")
    ids = [i["id_equipamento"] for i in c.get(CAT, headers=emp).json()["items"]]
    assert ids == [a2, a1, b, z]


def test_catalogo_filtra_por_categoria(c, emp):
    # UC12 passo 1 (filtro id_categoria)
    n = _eq(c, categoria=2)
    m = _eq(c, categoria=3)
    ids = lambda q: [i["id_equipamento"] for i in c.get(f"{CAT}?{q}", headers=emp).json()["items"]]  # noqa: E731
    assert ids("id_categoria=2") == [n] and ids("id_categoria=3") == [m] and ids("id_categoria=6") == []


def test_catalogo_busca_por_modelo_sem_diferenciar_caixa_e_acentos_de_caixa(c, emp):
    # UC12 (filtro q), DP-31/DP-50: busca por modelo, sem diferenciar caixa, inclusive com acento
    a = _eq(c, modelo="Notebook AÇÃO Pro")
    _eq(c, modelo="Monitor Samsung")
    ids = lambda q: [i["id_equipamento"] for i in c.get(CAT, params={"q": q}, headers=emp).json()["items"]]  # noqa: E731
    assert ids("ação") == [a] and ids("AÇÃO") == [a] and ids("  pro ") == [a] and ids("inexistente") == []


def test_catalogo_busca_trata_percentual_e_sublinhado_como_texto_literal(c, emp):
    # UC12 (filtro q), RNF04: curingas do LIKE nao podem vazar
    lit = _eq(c, modelo="Mod_100%")
    _eq(c, modelo="ModX1000")
    ids = lambda q: [i["id_equipamento"] for i in c.get(CAT, params={"q": q}, headers=emp).json()["items"]]  # noqa: E731
    assert ids("_100%") == [lit]
    assert ids("%") == [lit]
    assert ids("_") == [lit]


def test_catalogo_busca_com_aspas_e_barra_nao_quebra(c, emp):
    # RNF04: sem erro 500 nem injecao de SQL
    _eq(c, modelo="Normal")
    for q in ["' OR 1=1 --", "\\", "\"; DROP TABLE EQUIPAMENTO;--"]:
        r = c.get(CAT, params={"q": q}, headers=emp)
        assert r.status_code == 200 and r.json()["total"] == 0, (q, r.text)
    assert len(_tab(c, "EQUIPAMENTO")) == 1


def test_catalogo_paginacao(c, emp):
    # UC12, convencoes: {items,total,page,size}
    _eqs(c, 5)
    r = c.get(f"{CAT}?page=2&size=2", headers=emp).json()
    assert r["total"] == 5 and r["page"] == 2 and r["size"] == 2 and len(r["items"]) == 2
    assert len(c.get(f"{CAT}?page=3&size=2", headers=emp).json()["items"]) == 1
    assert c.get(f"{CAT}?page=9&size=2", headers=emp).json()["items"] == []


@pytest.mark.parametrize("q", ["page=0", "page=-1", "page=x", "size=0", "size=101", "size=x", f"id_categoria={GRANDE}",
                               "id_categoria=abc", "q=" + "a" * 151])
def test_catalogo_parametros_invalidos_da_400(c, emp, q):
    # UC12, RNF04: 400 DADOS_INVALIDOS
    _erro(c.get(f"{CAT}?{q}", headers=emp), 400, "DADOS_INVALIDOS")


def test_catalogo_item_inexistente_enorme_e_texto(c, emp):
    # UC12 FA1, RNF04
    _erro(c.get(f"{CAT}/99999", headers=emp), 404, "NAO_ENCONTRADO")
    _erro(c.get(f"{CAT}/{GRANDE}", headers=emp), 404, "NAO_ENCONTRADO")
    _erro(c.get(f"{CAT}/abc", headers=emp), 400, "DADOS_INVALIDOS")


def test_catalogo_item_detalhe_sucesso(c, emp):
    # UC12 passos 3-4
    a = _eq(c, modelo="Dell", valor=999.9)
    r = c.get(f"{CAT}/{a}", headers=emp)
    assert r.status_code == 200
    assert r.json()["id_equipamento"] == a and r.json()["valor"] == 999.9 and r.json()["condicao"] == "Bom"


def test_catalogo_so_leitura_metodos_de_escrita_nao_existem(c, emp):
    # UC12: catalogo nao altera nada
    a = _eq(c)
    for m in ("post", "put", "patch", "delete"):
        assert getattr(c, m)(f"{CAT}/{a}", headers=emp).status_code in (404, 405)


def test_catalogo_reservado_por_pedido_pendente_some_para_todos(c, emp, emp2):
    # UC12, UC13, DP-45, DP-50: o item em pedido Pendente nao aparece nem para a outra organizacao
    a, b = _eqs(c, 2)
    _pedido(c, emp, [a])
    ids = lambda h: [i["id_equipamento"] for i in c.get(CAT, headers=h).json()["items"]]  # noqa: E731
    assert ids(emp) == [b] and ids(emp2) == [b]
    _erro(c.get(f"{CAT}/{a}", headers=emp2), 404, "NAO_ENCONTRADO")
    assert _sit_eq(c, a) == "Disponível"  # continua Disponivel, so reservado


def test_catalogo_item_volta_apos_cancelar_e_some_apos_confirmar(c, emp, adm):
    # UC12, UC13 FA1, UC15, RN14: cancelar libera; confirmar vende
    a, b = _eqs(c, 2)
    p1 = _pedido(c, emp, [a])
    ids = lambda: sorted(i["id_equipamento"] for i in c.get(CAT, headers=emp).json()["items"])  # noqa: E731
    assert ids() == [b]
    assert c.post(f"{V}/{p1['id_venda']}/cancelar", headers=emp).status_code == 200
    assert ids() == sorted([a, b])
    p2 = _pedido(c, emp, [a])
    assert _confirmar(c, adm, p2["id_venda"]).status_code == 200
    assert ids() == [b]


# ================================================================== UC13 criar pedido (RN13, DP-45, DP-46, DP-48)
def test_criar_pedido_sucesso_grava_pendente_com_valores_congelados(c, emp):
    # UC13 passos 3-5, RN13, DP-45/46/48
    a = _eq(c, valor=1500.0)
    b = _eq(c, valor=800.25, modelo="Monitor", categoria=3)
    r = c.post(V, json={"ids_equipamento": [a, b]}, headers=emp)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["situacao"] == "Pendente" and j["forma_pagamento"] == "A definir" and j["data_venda"] == ISO
    assert j["id_organizacao_cliente"] == ORG_EMPRESA and j["nome_organizacao"] == "Empresa Cliente"
    assert j["quantidade"] == 2 and j["valor_total"] == 2300.25 and j["nota_fiscal"] is None
    assert [i["id_equipamento"] for i in j["itens"]] == [a, b]
    assert set(j["itens"][0]) == {"id_item_venda", "id_equipamento", "identificacao", "modelo", "categoria_nome", "condicao", "valor"}
    assert [i["valor"] for i in j["itens"]] == [1500.0, 800.25]
    assert _sit_eq(c, a) == "Disponível" and _sit_eq(c, b) == "Disponível"
    assert len(_tab(c, "VENDA")) == 1 and len(_tab(c, "ITEM_VENDA")) == 2
    # GET devolve o mesmo
    assert c.get(f"{V}/{j['id_venda']}", headers=emp).json() == j


def test_criar_pedido_organizacao_vem_do_token_e_ignora_o_corpo(c, emp, emp2):
    # UC13, RN04, RNF05: id_organizacao_cliente no corpo e ignorado
    a = _eq(c)
    r = c.post(V, json={"ids_equipamento": [a], "id_organizacao_cliente": c.id_org2, "situacao": "Confirmada",
                        "forma_pagamento": "Pix", "data_venda": "2020-01-01"}, headers=emp)
    assert r.status_code == 201, r.text
    j = r.json()
    assert j["id_organizacao_cliente"] == ORG_EMPRESA and j["situacao"] == "Pendente"
    assert j["forma_pagamento"] == "Pix" and j["data_venda"] == ISO  # DP-79: forma_pagamento agora é aceita


@pytest.mark.parametrize("corpo", [
    {}, {"ids_equipamento": []}, {"ids_equipamento": None}, {"ids_equipamento": "1"}, {"ids_equipamento": 1},
    {"ids_equipamento": [1, 1]}, {"ids_equipamento": [0]}, {"ids_equipamento": [-3]}, {"ids_equipamento": ["1"]},
    {"ids_equipamento": [1.5]}, {"ids_equipamento": [True]}, {"ids_equipamento": [None]}, {"ids_equipamento": [GRANDE]},
    {"ids_equipamento": list(range(1, 52))}, {"outro": [1]},
])
def test_criar_pedido_corpo_invalido_da_400_e_nao_grava(c, emp, corpo):
    # UC13 FE1 (quantidade invalida), RNF04: 1 a 50 ids, inteiros, sem repeticao
    _eqs(c, 3)
    j = _erro(c.post(V, json=corpo, headers=emp), 400, "DADOS_INVALIDOS")
    assert "ids_equipamento" in j["campos"]
    assert _tab(c, "VENDA") == [] and _tab(c, "ITEM_VENDA") == []


def test_criar_pedido_json_malformado_e_sem_corpo_da_400(c, emp):
    # RNF04
    r = c.post(V, content="{nao-json", headers={**emp, "Content-Type": "application/json"})
    _erro(r, 400, "DADOS_INVALIDOS")
    _erro(c.post(V, headers=emp), 400, "DADOS_INVALIDOS")


def test_criar_pedido_com_50_itens_e_aceito(c, emp):
    # UC13, contrato: maximo 50
    ids = _eqs(c, 50)
    r = c.post(V, json={"ids_equipamento": ids}, headers=emp)
    assert r.status_code == 201 and r.json()["quantidade"] == 50


def test_criar_pedido_item_indisponivel_aponta_os_ids_e_nao_grava(c, emp):
    # UC13 FE1, RN13: ITEM_INDISPONIVEL com ids afetados em campos.ids_equipamento (ordenados)
    bom = _eq(c)
    inativo = _eq(c, ativo=0)
    vendido = _eq(c, situacao="Vendido")
    inexistente = 987654
    j = _erro(c.post(V, json={"ids_equipamento": [bom, vendido, inexistente, inativo]}, headers=emp), 422, "ITEM_INDISPONIVEL")
    afetados = sorted([inativo, vendido, inexistente])
    assert j["campos"] == {"ids_equipamento": "indisponíveis: " + ", ".join(map(str, afetados))}
    assert _tab(c, "VENDA") == [] and _tab(c, "ITEM_VENDA") == []  # o item bom NAO foi reservado
    assert c.get(f"{CAT}/{bom}", headers=emp).status_code == 200


@pytest.mark.parametrize("campos", [{"condicao": "A avaliar"}, {"condicao": "Sem condições de reuso"}, {"valor": None}, {"valor": 0},
                                    {"situacao": "Em manutenção"}, {"situacao": "Doado"}])
def test_criar_pedido_equipamento_fora_das_regras_do_catalogo_da_422(c, emp, campos):
    # UC13 FE1, RN13: cada equipamento e revalidado pelas regras do catalogo
    ruim = _eq(c, **campos)
    j = _erro(c.post(V, json={"ids_equipamento": [ruim]}, headers=emp), 422, "ITEM_INDISPONIVEL")
    assert str(ruim) in j["campos"]["ids_equipamento"]


def test_criar_pedido_equipamento_ja_reservado_por_outro_pedido_da_422(c, emp, emp2):
    # UC13 FE1, DP-45, concorrencia logica: dois pedidos pelo mesmo equipamento
    a = _eq(c)
    p = _pedido(c, emp, [a])
    j = _erro(c.post(V, json={"ids_equipamento": [a]}, headers=emp2), 422, "ITEM_INDISPONIVEL")
    assert j["campos"]["ids_equipamento"] == f"indisponíveis: {a}"
    j2 = _erro(c.post(V, json={"ids_equipamento": [a]}, headers=emp), 422, "ITEM_INDISPONIVEL")  # a propria org tambem
    assert str(a) in j2["campos"]["ids_equipamento"]
    assert len(_tab(c, "VENDA")) == 1 and len(_tab(c, "ITEM_VENDA")) == 1
    assert _consulta(c, "SELECT id_venda FROM ITEM_VENDA")[0][0] == p["id_venda"]


def test_criar_pedido_equipamento_vendido_nao_e_incluido_em_nova_venda(c, emp, emp2, adm):
    # RN13, RN14: equipamento confirmado/vendido nao entra em nova venda
    v, ids = _confirmada(c, emp, adm, n=1)
    _erro(c.post(V, json={"ids_equipamento": ids}, headers=emp2), 422, "ITEM_INDISPONIVEL")


def test_criar_pedidos_concorrentes_pelo_mesmo_equipamento_so_um_vence(c, emp, emp2):
    # UC13, RN13, DP-45: duas requisicoes simultaneas (BEGIN IMMEDIATE) -> exatamente um 201
    a = _eq(c)
    saidas = []

    def tentar(h):
        saidas.append(c.post(V, json={"ids_equipamento": [a]}, headers=h).status_code)

    ts = [threading.Thread(target=tentar, args=(h,)) for h in (emp, emp2, emp, emp2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(saidas) == [201, 422, 422, 422], saidas
    assert len(_tab(c, "ITEM_VENDA")) == 1 and len(_tab(c, "VENDA")) == 1


def test_criar_pedido_falha_no_meio_desfaz_a_venda_inteira(c, emp, monkeypatch):
    # UC13 passo 4, RN13: VENDA e ITEM_VENDA na mesma transacao (rollback total)
    from app.vendas import repository
    ids = _eqs(c, 3)
    original = repository.inserir_item
    chamadas = []

    def falha(con, idv, ide):
        chamadas.append(ide)
        if len(chamadas) == 2:
            raise RuntimeError("falha simulada")
        return original(con, idv, ide)

    monkeypatch.setattr(repository, "inserir_item", falha)
    with pytest.raises(RuntimeError):
        c.post(V, json={"ids_equipamento": ids}, headers=emp)
    assert _tab(c, "VENDA") == [] and _tab(c, "ITEM_VENDA") == []
    monkeypatch.setattr(repository, "inserir_item", original)  # (nao usar monkeypatch.undo: desfaz o ambiente do conftest)
    assert c.post(V, json={"ids_equipamento": ids}, headers=emp).status_code == 201  # nada ficou preso


# ================================================================== UC13 FA1 / UC14 FA1 alterar itens (DP-47)
def test_alterar_itens_cliente_troca_retira_libera_e_reserva(c, emp):
    # UC13 FA1, DP-47: retirados liberam, novos reservam; continua Pendente
    a, b, n = _eqs(c, 3)
    p = _pedido(c, emp, [a, b])
    r = c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [b, n]}, headers=emp)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["situacao"] == "Pendente" and sorted(i["id_equipamento"] for i in j["itens"]) == sorted([b, n])
    assert j["quantidade"] == 2 and j["valor_total"] == 3000.0
    cat = [i["id_equipamento"] for i in c.get(CAT, headers=emp).json()["items"]]
    assert cat == [a]  # a foi liberado; b e n reservados


def test_alterar_itens_mantem_valor_congelado_dos_itens_ja_presentes(c, emp):
    # UC13 FA1, DP-48: item mantido conserva o valor; item novo usa o valor atual
    a = _eq(c, valor=1000.0)
    n = _eq(c, valor=500.0)
    p = _pedido(c, emp, [a])
    _sql(c, "UPDATE EQUIPAMENTO SET valor=2000 WHERE id_equipamento=?", (a,))
    _sql(c, "UPDATE EQUIPAMENTO SET valor=700 WHERE id_equipamento=?", (n,))
    j = c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [a, n]}, headers=emp).json()
    valores = {i["id_equipamento"]: i["valor"] for i in j["itens"]}
    assert valores == {a: 1000.0, n: 700.0} and j["valor_total"] == 1700.0


def test_alterar_itens_nao_revalida_itens_ja_presentes(c, emp):
    # Contrato (esclarecimento 4): PUT nao revalida os itens ja presentes (a confirmacao revalida)
    a, n = _eqs(c, 2)
    p = _pedido(c, emp, [a])
    _sql(c, "UPDATE EQUIPAMENTO SET ativo=0 WHERE id_equipamento=?", (a,))
    r = c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [a, n]}, headers=emp)
    assert r.status_code == 200, r.text


def test_alterar_itens_mesmo_conjunto_e_idempotente(c, emp):
    # UC13 FA1
    a, b = _eqs(c, 2)
    p = _pedido(c, emp, [a, b])
    r = c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [b, a]}, headers=emp)
    assert r.status_code == 200 and r.json()["quantidade"] == 2


def test_alterar_itens_interno_pode_alterar_pedido_de_qualquer_organizacao(c, emp, adm, fun):
    # UC14 FA1, DP-47, RN03: Administrador e Funcionario
    a, b, d = _eqs(c, 3)
    p = _pedido(c, emp, [a])
    r = c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [a, b]}, headers=adm)
    assert r.status_code == 200 and r.json()["quantidade"] == 2
    r = c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [d]}, headers=fun)
    assert r.status_code == 200 and [i["id_equipamento"] for i in r.json()["itens"]] == [d]
    assert r.json()["id_organizacao_cliente"] == ORG_EMPRESA


def test_alterar_itens_de_outra_organizacao_da_404(c, emp, emp2):
    # UC18 FE1, RN04, RNF05: 404 sem vazar
    a, b = _eqs(c, 2)
    p = _pedido(c, emp, [a])
    antes = _tab(c, "ITEM_VENDA")
    j = _erro(c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [b]}, headers=emp2), 404, "NAO_ENCONTRADO")
    inexistente = _erro(c.put(f"{V}/99999/itens", json={"ids_equipamento": [b]}, headers=emp2), 404, "NAO_ENCONTRADO")
    assert j == inexistente  # mesma resposta: nao revela que o pedido existe
    assert _tab(c, "ITEM_VENDA") == antes


@pytest.mark.parametrize("corpo", [{"ids_equipamento": []}, {"ids_equipamento": [3, 3]}, {}, {"ids_equipamento": [0]},
                                   {"ids_equipamento": [GRANDE]}, {"ids_equipamento": list(range(1, 52))}])
def test_alterar_itens_corpo_invalido_da_400_minimo_um_item(c, emp, corpo):
    # UC13 FA1, DP-47: minimo 1 item (para desistir, cancelar)
    a = _eq(c)
    p = _pedido(c, emp, [a])
    _erro(c.put(f"{V}/{p['id_venda']}/itens", json=corpo, headers=emp), 400, "DADOS_INVALIDOS")
    assert len(_tab(c, "ITEM_VENDA")) == 1


def test_alterar_itens_novo_indisponivel_da_422_e_nada_muda(c, emp, emp2):
    # UC13 FA1, RN13: itens novos seguem as regras do catalogo
    a, b, ruim = _eqs(c, 2) + [_eq(c, ativo=0)]
    p = _pedido(c, emp, [a])
    _pedido(c, emp2, [b])
    antes = _tab(c, "ITEM_VENDA")
    j = _erro(c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [a, b, ruim]}, headers=emp), 422, "ITEM_INDISPONIVEL")
    assert j["campos"]["ids_equipamento"] == "indisponíveis: " + ", ".join(map(str, sorted([b, ruim])))
    assert _tab(c, "ITEM_VENDA") == antes


def test_alterar_itens_confirmada_e_cancelada_sao_somente_leitura(c, emp, adm):
    # UC13 FA1, UC14 FA1, DP-47: VENDA_NAO_PENDENTE (tem precedencia sobre ITEM_INDISPONIVEL)
    v, ids = _confirmada(c, emp, adm, n=1)
    novo = _eq(c)
    _erro(c.put(f"{V}/{v['id_venda']}/itens", json={"ids_equipamento": [novo]}, headers=emp), 422, "VENDA_NAO_PENDENTE")
    _erro(c.put(f"{V}/{v['id_venda']}/itens", json={"ids_equipamento": [novo]}, headers=adm), 422, "VENDA_NAO_PENDENTE")
    p = _pedido(c, emp, [novo])
    c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp)
    j = _erro(c.put(f"{V}/{p['id_venda']}/itens", json={"ids_equipamento": [987654]}, headers=emp), 422, "VENDA_NAO_PENDENTE")
    assert j["campos"] == {"situacao": "Cancelada"}
    assert [r[1] for r in _tab(c, "ITEM_VENDA")] == [v["id_venda"]]


def test_alterar_itens_ordem_400_antes_de_404_e_404_antes_de_422(c, emp, adm):
    # Contrato: ordem 400 -> 404 -> 422
    _erro(c.put(f"{V}/99999/itens", json={"ids_equipamento": []}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(c.put(f"{V}/99999/itens", json={"ids_equipamento": [1]}, headers=adm), 404, "NAO_ENCONTRADO")


def test_alterar_itens_id_enorme_ou_texto(c, adm):
    # RNF04
    _erro(c.put(f"{V}/{GRANDE}/itens", json={"ids_equipamento": [1]}, headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.put(f"{V}/abc/itens", json={"ids_equipamento": [1]}, headers=adm), 400, "DADOS_INVALIDOS")


# ================================================================== UC14 FA1 ajustar forma de pagamento
@pytest.mark.parametrize("quem", ["admin", "func"])
@pytest.mark.parametrize("forma", FORMAS)
def test_ajustar_forma_pagamento_pedido_pendente(c, todos, emp, quem, forma):
    # UC14 FA1, DP-46/47, RN03
    p = _pedido(c, emp, _eqs(c, 1))
    r = c.patch(f"{V}/{p['id_venda']}", json={"forma_pagamento": forma}, headers=todos[quem])
    assert r.status_code == 200, r.text
    assert r.json()["forma_pagamento"] == forma and r.json()["situacao"] == "Pendente"


@pytest.mark.parametrize("corpo", [{}, {"forma_pagamento": "Dinheiro"}, {"forma_pagamento": "A definir"}, {"forma_pagamento": ""},
                                   {"forma_pagamento": None}, {"forma_pagamento": 1}, {"forma_pagamento": "pix"}])
def test_ajustar_forma_pagamento_invalida_da_400(c, adm, emp, corpo):
    # UC14 FE1: forma fora da lista
    p = _pedido(c, emp, _eqs(c, 1))
    j = _erro(c.patch(f"{V}/{p['id_venda']}", json=corpo, headers=adm), 400, "DADOS_INVALIDOS")
    assert "forma_pagamento" in j["campos"]
    assert c.get(f"{V}/{p['id_venda']}", headers=adm).json()["forma_pagamento"] == "A definir"


def test_ajustar_forma_pagamento_ordem_400_404_422(c, adm, emp):
    # Contrato: 400 -> 404 -> 422
    _erro(c.patch(f"{V}/99999", json={"forma_pagamento": "X"}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(c.patch(f"{V}/99999", json={"forma_pagamento": "Pix"}, headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.patch(f"{V}/{GRANDE}", json={"forma_pagamento": "Pix"}, headers=adm), 404, "NAO_ENCONTRADO")
    v, _ = _confirmada(c, emp, adm, n=1)
    _erro(c.patch(f"{V}/{v['id_venda']}", json={"forma_pagamento": "Boleto"}, headers=adm), 422, "VENDA_NAO_PENDENTE")
    assert c.get(f"{V}/{v['id_venda']}", headers=adm).json()["forma_pagamento"] == "Pix"


def test_ajustar_forma_pagamento_pedido_cancelado_da_422(c, adm, emp):
    # UC14 FA1, DP-47
    p = _pedido(c, emp, _eqs(c, 1))
    c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp)
    _erro(c.patch(f"{V}/{p['id_venda']}", json={"forma_pagamento": "Pix"}, headers=adm), 422, "VENDA_NAO_PENDENTE")


# ================================================================== UC13 FA1 / UC14 FA2 cancelar
def test_cancelar_cliente_libera_equipamentos_e_apaga_itens(c, emp):
    # UC13 FA1, DP-45: Cancelada, itens [] quantidade 0 valor_total 0; linhas de ITEM_VENDA apagadas
    a, b = _eqs(c, 2)
    p = _pedido(c, emp, [a, b])
    r = c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp)
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["situacao"] == "Cancelada" and j["itens"] == [] and j["quantidade"] == 0 and j["valor_total"] == 0
    assert _tab(c, "ITEM_VENDA") == []
    assert len(_tab(c, "VENDA")) == 1  # a VENDA nunca e apagada
    assert _sit_eq(c, a) == "Disponível" and _sit_eq(c, b) == "Disponível"
    assert _tab(c, "NOTA_FISCAL_SIMULADA") == []
    # o equipamento pode ser pedido de novo
    assert c.post(V, json={"ids_equipamento": [a, b]}, headers=emp).status_code == 201


@pytest.mark.parametrize("quem", ["admin", "func"])
def test_cancelar_interno_cancela_pedido_pendente_de_qualquer_cliente(c, todos, emp, quem):
    # UC14 FA2, DP-47
    p = _pedido(c, emp, _eqs(c, 1))
    r = c.post(f"{V}/{p['id_venda']}/cancelar", headers=todos[quem])
    assert r.status_code == 200 and r.json()["situacao"] == "Cancelada"


def test_cancelar_pedido_de_outra_organizacao_da_404_e_nada_muda(c, emp, emp2):
    # UC18 FE1, RN04, RNF05
    p = _pedido(c, emp, _eqs(c, 1))
    antes = (_tab(c, "VENDA"), _tab(c, "ITEM_VENDA"))
    a = _erro(c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp2), 404, "NAO_ENCONTRADO")
    b = _erro(c.post(f"{V}/99999/cancelar", headers=emp2), 404, "NAO_ENCONTRADO")
    assert a == b
    assert (_tab(c, "VENDA"), _tab(c, "ITEM_VENDA")) == antes


def test_cancelar_e_idempotente(c, emp):
    # Contrato: ja Cancelada -> 200
    p = _pedido(c, emp, _eqs(c, 1))
    r1 = c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp)
    r2 = c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp)
    assert r1.status_code == 200 and r2.status_code == 200 and r1.json() == r2.json()


def test_cancelar_venda_confirmada_da_422_e_preserva_tudo(c, emp, adm):
    # UC14 FA2, DP-45/47: Confirmada nunca e apagada
    v, ids = _confirmada(c, emp, adm, n=2)
    j = _erro(c.post(f"{V}/{v['id_venda']}/cancelar", headers=adm), 422, "VENDA_NAO_PENDENTE")
    assert j["campos"] == {"situacao": "Confirmada"}
    _erro(c.post(f"{V}/{v['id_venda']}/cancelar", headers=emp), 422, "VENDA_NAO_PENDENTE")
    assert len(_tab(c, "ITEM_VENDA")) == 2 and all(_sit_eq(c, i) == "Vendido" for i in ids)
    assert c.get(f"{V}/{v['id_venda']}", headers=adm).json()["situacao"] == "Confirmada"


def test_cancelar_nao_gera_nota_nem_venda_confirmada(c, emp, adm):
    # UC14 FA2, UC16 FE1
    p = _pedido(c, emp, _eqs(c, 1))
    c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp)
    _erro(c.post(f"{V}/{p['id_venda']}/nota-fiscal", headers=adm), 422, "VENDA_NAO_CONFIRMADA")
    _erro(_confirmar(c, adm, p["id_venda"]), 422, "VENDA_NAO_PENDENTE")
    assert _tab(c, "NOTA_FISCAL_SIMULADA") == []


def test_cancelar_inexistente_enorme_e_texto(c, adm):
    # RNF04
    _erro(c.post(f"{V}/99999/cancelar", headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.post(f"{V}/{GRANDE}/cancelar", headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.post(f"{V}/abc/cancelar", headers=adm), 400, "DADOS_INVALIDOS")


# ================================================================== UC14 + UC15 confirmar (RN13, RN14)
@pytest.mark.parametrize("quem", ["admin", "func"])
def test_confirmar_marca_venda_confirmada_e_equipamentos_vendidos(c, todos, emp, quem):
    # UC14 passos 3-6, UC15 passo 2, RN03, RN14
    a = _eq(c, valor=1000.0)
    b = _eq(c, valor=250.5)
    p = _pedido(c, emp, [a, b])
    r = _confirmar(c, todos[quem], p["id_venda"], forma="Cartão de crédito")
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["situacao"] == "Confirmada" and j["forma_pagamento"] == "Cartão de crédito" and j["data_venda"] == ISO
    assert j["quantidade"] == 2 and j["valor_total"] == 1250.5 and j["nota_fiscal"] is None
    assert _sit_eq(c, a) == "Vendido" and _sit_eq(c, b) == "Vendido"
    assert c.get(CAT, headers=emp).json()["items"] == []  # UC15 passo 3: saem da disponibilidade


@pytest.mark.parametrize("forma", FORMAS)
def test_confirmar_aceita_cada_forma_de_pagamento(c, adm, emp, forma):
    # UC14 passo 3, DP-46
    p = _pedido(c, emp, _eqs(c, 1))
    assert _confirmar(c, adm, p["id_venda"], forma=forma).json()["forma_pagamento"] == forma


def test_confirmar_aceita_data_anterior_a_hoje_desde_que_nao_anterior_ao_pedido(c, adm, emp):
    # UC14 passo 3, DP-46
    p = _pedido(c, emp, _eqs(c, 1))
    _sql(c, "UPDATE VENDA SET data_venda=? WHERE id_venda=?", ((HOJE - timedelta(days=5)).isoformat(), p["id_venda"]))
    r = _confirmar(c, adm, p["id_venda"], data=(HOJE - timedelta(days=3)).isoformat())
    assert r.status_code == 200 and r.json()["data_venda"] == (HOJE - timedelta(days=3)).isoformat()


def test_confirmar_data_igual_a_do_pedido_e_aceita(c, adm, emp):
    # DP-46: nao anterior (igual vale)
    p = _pedido(c, emp, _eqs(c, 1))
    assert _confirmar(c, adm, p["id_venda"], data=p["data_venda"]).status_code == 200


def test_confirmar_data_anterior_a_do_pedido_da_400(c, adm, emp):
    # Contrato (esclarecimento 1): 400 DADOS_INVALIDOS com campos.data_venda; venda segue Pendente
    ids = _eqs(c, 1)
    p = _pedido(c, emp, ids)
    _sql(c, "UPDATE VENDA SET data_venda=? WHERE id_venda=?", ((HOJE - timedelta(days=5)).isoformat(), p["id_venda"]))
    j = _erro(_confirmar(c, adm, p["id_venda"], data=(HOJE - timedelta(days=6)).isoformat()), 400, "DADOS_INVALIDOS")
    assert "data_venda" in j["campos"]
    assert c.get(f"{V}/{p['id_venda']}", headers=adm).json()["situacao"] == "Pendente" and _sit_eq(c, ids[0]) == "Disponível"


@pytest.mark.parametrize("corpo", [
    {}, {"data_venda": ISO}, {"forma_pagamento": "Pix"},
    {"data_venda": "", "forma_pagamento": "Pix"}, {"data_venda": None, "forma_pagamento": "Pix"},
    {"data_venda": "31/10/2026", "forma_pagamento": "Pix"}, {"data_venda": "2026-13-01", "forma_pagamento": "Pix"},
    {"data_venda": "2026-02-30", "forma_pagamento": "Pix"}, {"data_venda": "ontem", "forma_pagamento": "Pix"},
    {"data_venda": "2026-1-5", "forma_pagamento": "Pix"}, {"data_venda": 20261031, "forma_pagamento": "Pix"},
    {"data_venda": (HOJE + timedelta(days=1)).isoformat(), "forma_pagamento": "Pix"},
    {"data_venda": "9999-12-31", "forma_pagamento": "Pix"},
    {"data_venda": ISO, "forma_pagamento": ""}, {"data_venda": ISO, "forma_pagamento": "Dinheiro"},
    {"data_venda": ISO, "forma_pagamento": "A definir"}, {"data_venda": ISO, "forma_pagamento": None},
    {"data_venda": ISO, "forma_pagamento": "PIX"},
])
def test_confirmar_dados_incompletos_ou_invalidos_da_400_e_nada_muda(c, adm, emp, corpo):
    # UC14 FE1 (dados incompletos), DP-46, RNF04
    ids = _eqs(c, 2)
    p = _pedido(c, emp, ids)
    antes = _tab(c, "VENDA")
    j = _erro(c.post(f"{V}/{p['id_venda']}/confirmar", json=corpo, headers=adm), 400, "DADOS_INVALIDOS")
    assert j["campos"]
    assert _tab(c, "VENDA") == antes and all(_sit_eq(c, i) == "Disponível" for i in ids)


def test_confirmar_sem_corpo_da_400(c, adm, emp):
    # UC14 FE1
    p = _pedido(c, emp, _eqs(c, 1))
    _erro(c.post(f"{V}/{p['id_venda']}/confirmar", headers=adm), 400, "DADOS_INVALIDOS")


def test_confirmar_inexistente_enorme_e_texto(c, adm):
    # RNF04
    _erro(_confirmar(c, adm, 99999), 404, "NAO_ENCONTRADO")
    _erro(_confirmar(c, adm, GRANDE), 404, "NAO_ENCONTRADO")
    _erro(_confirmar(c, adm, "abc"), 400, "DADOS_INVALIDOS")


def test_confirmar_ordem_400_antes_de_404(c, adm):
    # Contrato: 400 -> 404
    _erro(c.post(f"{V}/99999/confirmar", json={"data_venda": "x", "forma_pagamento": "Pix"}, headers=adm), 400, "DADOS_INVALIDOS")


def test_confirmar_idempotente_com_os_mesmos_dados(c, adm, emp):
    # Contrato (esclarecimento 3): ja Confirmada com os mesmos dados -> 200, sem alterar nada
    p = _pedido(c, emp, _eqs(c, 2))
    r1 = _confirmar(c, adm, p["id_venda"], forma="Boleto")
    antes = (_tab(c, "VENDA"), _tab(c, "ITEM_VENDA"), _tab(c, "EQUIPAMENTO"))
    r2 = _confirmar(c, adm, p["id_venda"], forma="Boleto")
    assert r1.status_code == 200 and r2.status_code == 200 and r1.json() == r2.json()
    assert (_tab(c, "VENDA"), _tab(c, "ITEM_VENDA"), _tab(c, "EQUIPAMENTO")) == antes


def test_confirmar_ja_confirmada_com_dados_diferentes_da_422(c, adm, emp):
    # Contrato (esclarecimento 3)
    p = _pedido(c, emp, _eqs(c, 1))
    _confirmar(c, adm, p["id_venda"], forma="Pix")
    _erro(_confirmar(c, adm, p["id_venda"], forma="Boleto"), 422, "VENDA_NAO_PENDENTE")
    # data diferente: tem precedencia VENDA_NAO_PENDENTE sobre o 400 de data anterior (esclarecimento 1)
    _sql(c, "UPDATE VENDA SET data_venda=? WHERE id_venda=?", (ISO, p["id_venda"]))
    _erro(_confirmar(c, adm, p["id_venda"], data=(HOJE - timedelta(days=9)).isoformat()), 422, "VENDA_NAO_PENDENTE")
    assert c.get(f"{V}/{p['id_venda']}", headers=adm).json()["forma_pagamento"] == "Pix"


def test_confirmar_pedido_cancelado_da_422(c, adm, emp):
    # UC14, DP-47
    p = _pedido(c, emp, _eqs(c, 1))
    c.post(f"{V}/{p['id_venda']}/cancelar", headers=emp)
    _erro(_confirmar(c, adm, p["id_venda"]), 422, "VENDA_NAO_PENDENTE")


def test_confirmar_cliente_inativo_da_422_e_nada_muda(c, adm, emp):
    # UC14 FE1, RN13: organizacao inativada depois do pedido
    ids = _eqs(c, 2)
    p = _pedido(c, emp, ids)
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ORG_EMPRESA,))
    j = _erro(_confirmar(c, adm, p["id_venda"]), 422, "CLIENTE_INATIVO")
    assert j["campos"] == {"id_organizacao_cliente": "inativa"}
    assert c.get(f"{V}/{p['id_venda']}", headers=adm).json()["situacao"] == "Pendente"
    assert all(_sit_eq(c, i) == "Disponível" for i in ids)


@pytest.mark.parametrize("mudanca", ["ativo=0", "situacao='Em manutenção'", "situacao='Recondicionado'", "condicao='A avaliar'",
                                     "condicao='Sem condições de reuso'", "situacao='Doado'"])
def test_confirmar_item_que_ficou_indisponivel_da_422_com_ids_e_nada_muda(c, adm, emp, mudanca):
    # UC14 passo 4 / FE1, RN13, UC15: revalida cada equipamento; nenhum vira Vendido
    a, b, d = _eqs(c, 3)
    p = _pedido(c, emp, [a, b, d])
    _sql(c, f"UPDATE EQUIPAMENTO SET {mudanca} WHERE id_equipamento=?", (b,))
    antes = _tab(c, "EQUIPAMENTO")
    j = _erro(_confirmar(c, adm, p["id_venda"]), 422, "ITEM_INDISPONIVEL")
    assert j["campos"] == {"ids_equipamento": f"indisponíveis: {b}"}
    assert _tab(c, "EQUIPAMENTO") == antes
    assert c.get(f"{V}/{p['id_venda']}", headers=adm).json()["situacao"] == "Pendente"


def test_confirmar_item_ja_vendido_em_outro_caminho_da_422(c, adm, emp):
    # RN14: equipamento ja Vendido nao pode ser vendido de novo
    a = _eq(c)
    p = _pedido(c, emp, [a])
    _sql(c, "UPDATE EQUIPAMENTO SET situacao='Vendido' WHERE id_equipamento=?", (a,))
    _erro(_confirmar(c, adm, p["id_venda"]), 422, "ITEM_INDISPONIVEL")


def test_confirmar_mantem_valor_congelado_do_pedido(c, adm, emp):
    # DP-48: mudar o preco do equipamento depois do pedido nao altera a venda
    a = _eq(c, valor=1000.0)
    p = _pedido(c, emp, [a])
    _sql(c, "UPDATE EQUIPAMENTO SET valor=5000 WHERE id_equipamento=?", (a,))
    j = _confirmar(c, adm, p["id_venda"]).json()
    assert j["valor_total"] == 1000.0 and j["itens"][0]["valor"] == 1000.0


def test_confirmar_falha_ao_atualizar_estoque_faz_rollback_total(c, adm, emp, monkeypatch):
    # UC15 FE1, RN14: falha no 2o equipamento -> venda segue Pendente, 1o equipamento volta a Disponivel
    from app.equipamentos import service as eq_service
    ids = _eqs(c, 3)
    p = _pedido(c, emp, ids)
    original = eq_service.mudar_situacao
    n = []

    def falha(con, ide, *a, **kw):
        n.append(ide)
        if len(n) == 2:
            raise RuntimeError("falha simulada no estoque")
        return original(con, ide, *a, **kw)

    monkeypatch.setattr(eq_service, "mudar_situacao", falha)
    antes = _tab(c, "VENDA")
    _erro(_confirmar(c, adm, p["id_venda"], forma="Boleto"), 422, "FALHA_ESTOQUE")
    assert len(n) == 2
    assert _tab(c, "VENDA") == antes  # Pendente, 'A definir', data original
    assert all(_sit_eq(c, i) == "Disponível" for i in ids)
    assert len(_tab(c, "ITEM_VENDA")) == 3  # continuam reservados
    # os itens seguem reservados: ninguem mais consegue pedi-los
    _erro(c.post(V, json={"ids_equipamento": ids[:1]}, headers=emp), 422, "ITEM_INDISPONIVEL")
    monkeypatch.setattr(eq_service, "mudar_situacao", original)
    r = _confirmar(c, adm, p["id_venda"], forma="Boleto")
    assert r.status_code == 200 and all(_sit_eq(c, i) == "Vendido" for i in ids)


def test_confirmar_erro_de_negocio_no_estoque_tambem_vira_falha_estoque(c, adm, emp, monkeypatch):
    # UC15 FE1: ErroApi levantado por mudar_situacao e convertido em FALHA_ESTOQUE com rollback
    from app.equipamentos import service as eq_service
    from app.erros import ErroApi
    ids = _eqs(c, 2)
    p = _pedido(c, emp, ids)

    def recusa(con, ide, *a, **kw):
        raise ErroApi(422, "TRANSICAO_INVALIDA", "x")

    monkeypatch.setattr(eq_service, "mudar_situacao", recusa)
    _erro(_confirmar(c, adm, p["id_venda"]), 422, "FALHA_ESTOQUE")
    assert c.get(f"{V}/{p['id_venda']}", headers=adm).json()["situacao"] == "Pendente"


def test_confirmar_pedido_sem_itens_nao_deve_gerar_venda_confirmada(c, adm):
    # RN13: venda vinculada a pelo menos um equipamento (pedido Pendente sem itens, so possivel por dados sujos)
    idv = _venda_sql(c, situacao="Pendente", forma="A definir", itens=[])
    r = _confirmar(c, adm, idv)
    assert r.status_code == 422, r.text
    assert c.get(f"{V}/{idv}", headers=adm).json()["situacao"] == "Pendente"


def test_confirmar_nao_toca_em_outros_pedidos(c, adm, emp, emp2):
    # UC15: so os equipamentos da venda confirmada viram Vendido
    a, b = _eqs(c, 2)
    p1 = _pedido(c, emp, [a])
    p2 = _pedido(c, emp2, [b])
    _confirmar(c, adm, p1["id_venda"])
    assert _sit_eq(c, a) == "Vendido" and _sit_eq(c, b) == "Disponível"
    assert c.get(f"{V}/{p2['id_venda']}", headers=adm).json()["situacao"] == "Pendente"


def test_confirmar_duas_requisicoes_simultaneas_so_uma_confirma_a_venda(c, adm, fun, emp):
    # UC14, UC15, RN14: concorrencia sobre o mesmo pedido -> 200 (primeira) e 200 idempotente/422, sem duplicar
    ids = _eqs(c, 2)
    p = _pedido(c, emp, ids)
    saidas = []

    def tentar(h, forma):
        saidas.append(_confirmar(c, h, p["id_venda"], forma=forma).status_code)

    ts = [threading.Thread(target=tentar, args=(adm, "Pix")), threading.Thread(target=tentar, args=(fun, "Boleto"))]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(saidas) == [200, 422], saidas  # formas diferentes: a segunda e recusada
    assert all(_sit_eq(c, i) == "Vendido" for i in ids)


# ================================================================== UC16 emitir nota fiscal simulada (RN19, DP-49)
def _nota(c, adm, idv):
    r = c.post(f"{V}/{idv}/nota-fiscal", headers=adm)
    assert r.status_code in (200, 201), r.text
    return r.json()


def test_emitir_nota_201_com_numero_data_e_dados_da_venda(c, adm, emp):
    # UC16 passos 2-5, RN19, DP-49
    v, ids = _confirmada(c, emp, adm, n=2)
    r = c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm)
    assert r.status_code == 201, r.text
    j = r.json()
    assert set(j) == {"id_nota", "numero", "data_emissao", "simulada", "venda"}
    assert j["numero"] == f"NFS-{HOJE.year}-000001" and j["data_emissao"] == ISO and j["simulada"] is True
    assert j["venda"]["id_venda"] == v["id_venda"] and j["venda"]["id_organizacao_cliente"] == ORG_EMPRESA
    assert j["venda"]["quantidade"] == 2 and j["venda"]["valor_total"] == v["valor_total"]
    assert [i["id_equipamento"] for i in j["venda"]["itens"]] == ids
    # a venda passa a exibir a nota (RN20: permanece vinculada)
    d = c.get(f"{V}/{v['id_venda']}", headers=adm).json()
    assert d["nota_fiscal"] == {"id_nota": j["id_nota"], "numero": j["numero"], "data_emissao": ISO}


def test_emitir_nota_numeracao_sequencial_e_unica(c, adm, emp):
    # UC16 passo 4, RN19: NFS-AAAA-NNNNNN unico
    numeros = []
    for _ in range(3):
        v, _ids = _confirmada(c, emp, adm, n=1)
        numeros.append(_nota(c, adm, v["id_venda"])["numero"])
    assert numeros == [f"NFS-{HOJE.year}-00000{i}" for i in (1, 2, 3)]
    assert len(set(r[2] for r in _tab(c, "NOTA_FISCAL_SIMULADA"))) == 3
    assert all(re.fullmatch(r"NFS-\d{4}-\d{6}", n) for n in numeros)


def test_emitir_nota_sequencia_continua_do_maior_numero_do_ano_e_ignora_outros_anos(c, adm, emp):
    # RN19: sequencia por ano
    v0 = _venda_sql(c)
    _sql(c, "INSERT INTO NOTA_FISCAL_SIMULADA (id_venda, numero, data_emissao) VALUES (?,?,?)", (v0, f"NFS-{HOJE.year}-000009", ISO))
    v1 = _venda_sql(c)
    _sql(c, "INSERT INTO NOTA_FISCAL_SIMULADA (id_venda, numero, data_emissao) VALUES (?,?,?)", (v1, "NFS-2019-000500", "2019-05-05"))
    v, _ = _confirmada(c, emp, adm, n=1)
    assert _nota(c, adm, v["id_venda"])["numero"] == f"NFS-{HOJE.year}-000010"


def test_emitir_nota_repetida_devolve_a_existente_com_200_sem_duplicar(c, adm, emp):
    # UC16 FA1: nota existente -> 200, mesma nota
    v, _ = _confirmada(c, emp, adm, n=1)
    r1 = c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm)
    r2 = c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm)
    r3 = c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm)
    assert (r1.status_code, r2.status_code, r3.status_code) == (201, 200, 200)
    assert r1.json()["id_nota"] == r2.json()["id_nota"] == r3.json()["id_nota"] and r1.json()["numero"] == r2.json()["numero"]
    assert len(_tab(c, "NOTA_FISCAL_SIMULADA")) == 1


def test_emitir_nota_simultanea_gera_uma_so(c, adm, emp):
    # UC16, RN19: duas emissoes ao mesmo tempo -> uma 201 e uma 200
    v, _ = _confirmada(c, emp, adm, n=1)
    saidas = []
    ts = [threading.Thread(target=lambda: saidas.append(c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm).status_code))
          for _ in range(3)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert sorted(saidas) == [200, 200, 201], saidas
    assert len(_tab(c, "NOTA_FISCAL_SIMULADA")) == 1


def test_emitir_notas_de_vendas_diferentes_simultaneas_tem_numeros_unicos(c, adm, emp):
    # RN19: numero unico mesmo com concorrencia
    vs = [_confirmada(c, emp, adm, n=1)[0]["id_venda"] for _ in range(4)]
    saidas = []
    ts = [threading.Thread(target=lambda i=i: saidas.append(c.post(f"{V}/{i}/nota-fiscal", headers=adm).status_code)) for i in vs]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert saidas == [201] * 4 or sorted(saidas) == [201] * 4, saidas
    numeros = [r[2] for r in _tab(c, "NOTA_FISCAL_SIMULADA")]
    assert len(numeros) == 4 and len(set(numeros)) == 4


@pytest.mark.parametrize("situacao", ["Pendente", "Cancelada"])
def test_emitir_nota_venda_nao_confirmada_da_422(c, adm, situacao):
    # UC16 FE1, RN19
    idv = _venda_sql(c, situacao=situacao, forma="A definir", itens=None)
    j = _erro(c.post(f"{V}/{idv}/nota-fiscal", headers=adm), 422, "VENDA_NAO_CONFIRMADA")
    assert j["campos"] == {"situacao": situacao}
    assert _tab(c, "NOTA_FISCAL_SIMULADA") == []


def test_emitir_nota_venda_sem_itens_da_422_inconsistente(c, adm):
    # UC16 FE2 (esclarecimento 2): venda sem itens
    idv = _venda_sql(c, situacao="Confirmada", itens=[])
    _erro(c.post(f"{V}/{idv}/nota-fiscal", headers=adm), 422, "VENDA_INCONSISTENTE")
    assert _tab(c, "NOTA_FISCAL_SIMULADA") == []


@pytest.mark.parametrize("valor", [0, -10])
def test_emitir_nota_item_com_valor_invalido_da_422_inconsistente(c, adm, valor):
    # UC16 FE2 (esclarecimento 2): item com valor <= 0
    idv = _venda_sql(c, situacao="Confirmada", valor=valor)
    _erro(c.post(f"{V}/{idv}/nota-fiscal", headers=adm), 422, "VENDA_INCONSISTENTE")
    assert _tab(c, "NOTA_FISCAL_SIMULADA") == []


def test_emitir_nota_falha_ao_gravar_nao_deixa_nota_pela_metade(c, adm, emp, monkeypatch):
    # UC16 passo 4, RN19: rollback; nova tentativa funciona e usa 000001
    from app.notas_fiscais import repository
    v, _ = _confirmada(c, emp, adm, n=1)
    original = repository.inserir

    def falha(*a, **kw):
        raise RuntimeError("falha simulada")

    monkeypatch.setattr(repository, "inserir", falha)
    with pytest.raises(RuntimeError):
        c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm)
    assert _tab(c, "NOTA_FISCAL_SIMULADA") == []
    monkeypatch.setattr(repository, "inserir", original)
    assert c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm).json()["numero"] == f"NFS-{HOJE.year}-000001"


def test_emitir_nota_somente_administrador(c, adm, fun, emp, ong, doa):
    # UC16, RN19: Funcionario, Cliente Empresa e demais -> 403; nada e emitido
    v, _ = _confirmada(c, emp, adm, n=1)
    for h in (fun, emp, ong, doa):
        _erro(c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=h), 403, "SEM_PERMISSAO")
    assert _tab(c, "NOTA_FISCAL_SIMULADA") == []
    assert c.post(f"{V}/{v['id_venda']}/nota-fiscal", headers=adm).status_code == 201


def test_emitir_nota_inexistente_enorme_e_texto(c, adm):
    # UC16, RNF04
    _erro(c.post(f"{V}/99999/nota-fiscal", headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.post(f"{V}/{GRANDE}/nota-fiscal", headers=adm), 404, "NAO_ENCONTRADO")
    _erro(c.post(f"{V}/abc/nota-fiscal", headers=adm), 400, "DADOS_INVALIDOS")


def test_nota_nao_altera_equipamentos_nem_valores_da_venda(c, adm, emp):
    # UC16, RN19: cliente, equipamentos e valores correspondem a venda
    v, ids = _confirmada(c, emp, adm, n=2)
    antes = (_tab(c, "EQUIPAMENTO"), _tab(c, "ITEM_VENDA"))
    _nota(c, adm, v["id_venda"])
    assert (_tab(c, "EQUIPAMENTO"), _tab(c, "ITEM_VENDA")) == antes


# ================================================================== UC17 consultar e baixar nota (RN20)
@pytest.fixture()
def duas_notas(c, adm, emp, emp2):
    """Uma nota da org 1 e uma da org 2. Devolve (nota1, nota2)."""
    v1, _ = _confirmada(c, emp, adm, n=1)
    ids = _eqs(c, 1)
    p2 = _pedido(c, emp2, ids)
    assert _confirmar(c, adm, p2["id_venda"]).status_code == 200
    return _nota(c, adm, v1["id_venda"]), _nota(c, adm, p2["id_venda"])


def test_notas_lista_administrador_ve_todas_e_cliente_so_as_proprias(c, adm, emp, emp2, duas_notas):
    # UC17 passos 1-2, RN20, RNF05
    n1, n2 = duas_notas
    j = c.get(NF, headers=adm).json()
    assert j["total"] == 2 and {i["id_nota"] for i in j["items"]} == {n1["id_nota"], n2["id_nota"]}
    assert set(j["items"][0]) == {"id_nota", "id_venda", "numero", "data_emissao", "id_organizacao_cliente", "nome_organizacao", "valor_total"}
    assert [i["id_nota"] for i in c.get(NF, headers=emp).json()["items"]] == [n1["id_nota"]]
    assert [i["id_nota"] for i in c.get(NF, headers=emp2).json()["items"]] == [n2["id_nota"]]


def test_notas_lista_filtro_de_organizacao_vale_para_admin_e_e_ignorado_para_cliente(c, adm, emp, emp2, duas_notas):
    # UC17 (contrato): id_organizacao_cliente ignorado para Cliente Empresa
    n1, n2 = duas_notas
    assert [i["id_nota"] for i in c.get(f"{NF}?id_organizacao_cliente={c.id_org2}", headers=adm).json()["items"]] == [n2["id_nota"]]
    assert c.get(f"{NF}?id_organizacao_cliente=77", headers=adm).json()["total"] == 0
    assert [i["id_nota"] for i in c.get(f"{NF}?id_organizacao_cliente={c.id_org2}", headers=emp).json()["items"]] == [n1["id_nota"]]


def test_notas_lista_filtro_de_periodo_ordem_e_paginacao(c, adm, emp):
    # UC17, contrato: data_de/data_ate sobre data_emissao; ordenado por data_emissao desc, id desc
    vs = [_venda_sql(c) for _ in range(4)]
    datas = ["2026-01-10", "2026-03-10", "2026-03-10", "2026-05-10"]
    ids = [_sql(c, "INSERT INTO NOTA_FISCAL_SIMULADA (id_venda, numero, data_emissao) VALUES (?,?,?)", (v, f"NFS-2026-00000{i}", d))
           for i, (v, d) in enumerate(zip(vs, datas), start=1)]
    lista = lambda q="": [i["id_nota"] for i in c.get(f"{NF}?{q}", headers=adm).json()["items"]]  # noqa: E731
    assert lista() == [ids[3], ids[2], ids[1], ids[0]]
    assert lista("data_de=2026-03-10") == [ids[3], ids[2], ids[1]]
    assert lista("data_ate=2026-03-10") == [ids[2], ids[1], ids[0]]
    assert lista("data_de=2026-03-10&data_ate=2026-03-10") == [ids[2], ids[1]]
    assert lista("data_de=2026-06-01&data_ate=2026-01-01") == []  # de > ate -> vazio
    p = c.get(f"{NF}?page=2&size=3", headers=adm).json()
    assert p["total"] == 4 and p["page"] == 2 and len(p["items"]) == 1


@pytest.mark.parametrize("q", ["data_de=31/10/2026", "data_ate=abc", "data_de=2026-02-30", "page=0", "size=0", "size=101",
                               f"id_organizacao_cliente={GRANDE}", "id_organizacao_cliente=x"])
def test_notas_lista_parametros_invalidos_da_400(c, adm, q):
    # UC17, RNF04
    _erro(c.get(f"{NF}?{q}", headers=adm), 400, "DADOS_INVALIDOS")


def test_notas_lista_vazia_da_200(c, adm, emp):
    # UC17 passo 2
    assert c.get(NF, headers=adm).json() == {"items": [], "total": 0, "page": 1, "size": 20}
    assert c.get(NF, headers=emp).json()["items"] == []


def test_nota_detalhe_administrador_e_cliente_da_venda(c, adm, emp, duas_notas):
    # UC17 passos 3-4, FA1, RN20
    n1, _ = duas_notas
    a = c.get(f"{NF}/{n1['id_nota']}", headers=adm)
    b = c.get(f"{NF}/{n1['id_nota']}", headers=emp)
    assert a.status_code == 200 and b.status_code == 200 and a.json() == b.json() == n1 | {"venda": a.json()["venda"]}
    assert a.json()["simulada"] is True and a.json()["venda"]["itens"]


def test_nota_de_outra_organizacao_da_404_sem_vazar(c, emp, emp2, duas_notas):
    # UC17 FE1, RN20, RNF05: 404 identico ao de nota inexistente (download tambem)
    n1, n2 = duas_notas
    for rota in (f"{NF}/{n2['id_nota']}", f"{NF}/{n2['id_nota']}/download"):
        proibido = _erro(c.get(rota, headers=emp), 404, "NAO_ENCONTRADO")
        inexistente = _erro(c.get(rota.replace(str(n2["id_nota"]), "99999"), headers=emp), 404, "NAO_ENCONTRADO")
        assert proibido == inexistente
    assert emp2  # a organizacao 2 so enxerga a sua
    _erro(c.get(f"{NF}/{n1['id_nota']}", headers=emp2), 404, "NAO_ENCONTRADO")
    _erro(c.get(f"{NF}/{n1['id_nota']}/download", headers=emp2), 404, "NAO_ENCONTRADO")


def test_nota_funcionario_nao_consulta_nem_baixa(c, fun, duas_notas):
    # UC17, RN20: Funcionario -> 403
    n1, _ = duas_notas
    _erro(c.get(NF, headers=fun), 403, "SEM_PERMISSAO")
    _erro(c.get(f"{NF}/{n1['id_nota']}", headers=fun), 403, "SEM_PERMISSAO")
    _erro(c.get(f"{NF}/{n1['id_nota']}/download", headers=fun), 403, "SEM_PERMISSAO")


def test_nota_inexistente_enorme_e_texto(c, adm):
    # UC17 FE1, RNF04
    for sufixo in ("", "/download"):
        _erro(c.get(f"{NF}/99999{sufixo}", headers=adm), 404, "NAO_ENCONTRADO")
        _erro(c.get(f"{NF}/{GRANDE}{sufixo}", headers=adm), 404, "NAO_ENCONTRADO")
        _erro(c.get(f"{NF}/abc{sufixo}", headers=adm), 400, "DADOS_INVALIDOS")


def test_download_html_com_cabecalhos_e_marca_simulada(c, adm, emp, duas_notas):
    # UC17 passo 5, RN20, DP-49 (esclarecimento 7)
    n1, _ = duas_notas
    for h in (adm, emp):
        r = c.get(f"{NF}/{n1['id_nota']}/download", headers=h)
        assert r.status_code == 200, r.text
        assert r.headers["content-type"].replace(" ", "").lower() == "text/html;charset=utf-8"
        assert r.headers["content-disposition"] == f'attachment; filename="{n1["numero"]}.html"'
        assert r.headers["x-content-type-options"] == "nosniff"
        csp = r.headers["content-security-policy"]
        assert "default-src 'none'" in csp and "script-src" not in csp.replace("default-src", "")
        t = r.text
        assert MARCA in t and n1["numero"] in t and "Empresa Cliente" in t
        assert t.lstrip().lower().startswith("<!doctype html>") and 'lang="pt-BR"' in t and "<script" not in t.lower()
        for i in n1["venda"]["itens"]:
            assert i["identificacao"] in t and i["modelo"] in t


def test_download_valores_e_totais_batem_com_a_venda(c, adm, emp):
    # UC17, RN19/RN20: cliente, equipamentos e valores da venda
    a = _eq(c, valor=1234.5, modelo="Modelo A")
    b = _eq(c, valor=10.0, modelo="Modelo B")
    p = _pedido(c, emp, [a, b])
    _confirmar(c, adm, p["id_venda"])
    n = _nota(c, adm, p["id_venda"])
    t = c.get(f"{NF}/{n['id_nota']}/download", headers=adm).text
    assert "R$ 1.234,50" in t and "R$ 10,00" in t and "R$ 1.244,50" in t and "Quantidade: 2" in t


def test_download_escapa_html_contra_injecao(c, adm, emp):
    # UC17, RNF05: nome da organizacao, identificacao, modelo e condicao com marcacao nao viram HTML
    xss = '<script>alert(1)</script>'
    img = '"><img src=x onerror=alert(2)>'
    a = _eq(c, modelo=xss, ident=f"ID{img}", condicao=img)
    _sql(c, "UPDATE ORGANIZACAO SET nome_razao_social=? WHERE id_organizacao=?", (xss + " & Cia", ORG_EMPRESA))
    p = _pedido(c, emp, [a])
    _confirmar(c, adm, p["id_venda"])
    n = _nota(c, adm, p["id_venda"])
    t = c.get(f"{NF}/{n['id_nota']}/download", headers=emp).text
    assert "<script>alert(1)</script>" not in t and "<img src=x" not in t
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in t and "&amp; Cia" in t
    assert "&quot;&gt;&lt;img" in t or "&#x27;" in t or "&lt;img" in t


def test_download_nao_altera_dados(c, adm, duas_notas):
    # UC17: consulta e somente leitura
    antes = [_tab(c, t) for t in ("VENDA", "ITEM_VENDA", "NOTA_FISCAL_SIMULADA", "EQUIPAMENTO")]
    c.get(f"{NF}/{duas_notas[0]['id_nota']}/download", headers=adm)
    c.get(f"{NF}/{duas_notas[0]['id_nota']}", headers=adm)
    assert antes == [_tab(c, t) for t in ("VENDA", "ITEM_VENDA", "NOTA_FISCAL_SIMULADA", "EQUIPAMENTO")]


def test_notas_nao_tem_rotas_de_escrita_alem_da_emissao(c, adm, duas_notas):
    # Contrato: "Sem outros DELETE"; nota nao se altera
    i = duas_notas[0]["id_nota"]
    for m in ("put", "patch", "delete", "post"):
        assert getattr(c, m)(f"{NF}/{i}", headers=adm).status_code in (404, 405)
    assert c.delete(f"{V}/1", headers=adm).status_code in (404, 405)


# ================================================================== UC18 / UC21 historicos (RN15, DP-51)
@pytest.fixture()
def historico(c, emp2):
    """5 vendas: 3 da org 1 e 2 da org 2, datas e situacoes variadas. Devolve dict nome -> id."""
    h = {}
    h["a"] = _venda_sql(c, ORG_EMPRESA, "2026-01-10", "Confirmada", "Pix")
    h["b"] = _venda_sql(c, ORG_EMPRESA, "2026-02-10", "Cancelada", "A definir", itens=[])
    h["c"] = _venda_sql(c, c.id_org2, "2026-02-10", "Pendente", "A definir")
    h["d"] = _venda_sql(c, c.id_org2, "2026-03-15", "Confirmada", "Boleto", valor=200.0)
    h["e"] = _venda_sql(c, ORG_EMPRESA, "2026-03-20", "Pendente", "A definir", itens=_eqs(c, 2), valor=50.0)
    return h


def _ids_lista(c, h, q=""):
    r = c.get(f"{V}?{q}", headers=h)
    assert r.status_code == 200, r.text
    return [i["id_venda"] for i in r.json()["items"]]


@pytest.mark.parametrize("quem", ["admin", "func"])
def test_historico_geral_ve_todas_as_situacoes_ordenado_por_data_e_id_desc(c, todos, historico, quem):
    # UC21 passos 2, FA1, RN15: sem filtros; data_venda desc, depois id desc
    h = historico
    assert _ids_lista(c, todos[quem]) == [h["e"], h["d"], h["c"], h["b"], h["a"]]
    j = c.get(V, headers=todos[quem]).json()
    assert j["total"] == 5 and j["page"] == 1 and j["size"] == 20
    assert {i["situacao"] for i in j["items"]} == {"Pendente", "Confirmada", "Cancelada"}


def test_historico_resumo_tem_campos_do_contrato(c, adm, historico):
    # UC21 passo 4 (VendaResumo)
    h = historico
    j = c.get(V, headers=adm).json()
    e = next(i for i in j["items"] if i["id_venda"] == h["e"])
    assert set(e) == {"id_venda", "id_organizacao_cliente", "nome_organizacao", "data_venda", "situacao", "forma_pagamento",
                      "quantidade", "valor_total", "possui_nota"}
    assert e["quantidade"] == 2 and e["valor_total"] == 100.0 and e["possui_nota"] is False and e["nome_organizacao"] == "Empresa Cliente"
    b = next(i for i in j["items"] if i["id_venda"] == h["b"])
    assert b["quantidade"] == 0 and b["valor_total"] == 0 and b["situacao"] == "Cancelada"


def test_historico_possui_nota_acompanha_a_emissao(c, adm, emp):
    # UC21, UC16: possui_nota
    v, _ = _confirmada(c, emp, adm, n=1)
    assert c.get(V, headers=adm).json()["items"][0]["possui_nota"] is False
    _nota(c, adm, v["id_venda"])
    assert c.get(V, headers=adm).json()["items"][0]["possui_nota"] is True


def test_historico_filtros_situacao_organizacao_e_periodo(c, adm, fun, historico):
    # UC21 passo 3, RF15: periodo, Cliente Empresa e situacao (inclusive combinados)
    h = historico
    o2 = c.id_org2
    for quem in (adm, fun):
        assert _ids_lista(c, quem, "situacao=Pendente") == [h["e"], h["c"]]
        assert _ids_lista(c, quem, "situacao=Confirmada") == [h["d"], h["a"]]
        assert _ids_lista(c, quem, "situacao=Cancelada") == [h["b"]]
        assert _ids_lista(c, quem, f"id_organizacao_cliente={o2}") == [h["d"], h["c"]]
        assert _ids_lista(c, quem, f"id_organizacao_cliente={ORG_EMPRESA}") == [h["e"], h["b"], h["a"]]
        assert _ids_lista(c, quem, "id_organizacao_cliente=555") == []
        assert _ids_lista(c, quem, "data_de=2026-02-10") == [h["e"], h["d"], h["c"], h["b"]]
        assert _ids_lista(c, quem, "data_ate=2026-02-10") == [h["c"], h["b"], h["a"]]
        assert _ids_lista(c, quem, "data_de=2026-02-10&data_ate=2026-03-15") == [h["d"], h["c"], h["b"]]
        assert _ids_lista(c, quem, f"situacao=Pendente&id_organizacao_cliente={o2}&data_de=2026-02-01&data_ate=2026-02-28") == [h["c"]]


def test_historico_periodo_invertido_da_lista_vazia(c, adm, historico):
    # Contrato: data_de > data_ate -> lista vazia (200)
    j = c.get(f"{V}?data_de=2026-12-31&data_ate=2026-01-01", headers=adm).json()
    assert j["items"] == [] and j["total"] == 0


def test_historico_paginacao(c, adm, historico):
    # UC21, convencoes
    j = c.get(f"{V}?page=2&size=2", headers=adm).json()
    assert j["total"] == 5 and j["page"] == 2 and j["size"] == 2 and len(j["items"]) == 2
    assert len(c.get(f"{V}?page=3&size=2", headers=adm).json()["items"]) == 1
    assert c.get(f"{V}?page=4&size=2", headers=adm).json()["items"] == []


@pytest.mark.parametrize("q", ["situacao=Outra", "situacao=pendente", "data_de=hoje", "data_ate=2026-02-30", "data_de=31/12/2026",
                               "page=0", "page=x", "size=0", "size=101", f"id_organizacao_cliente={GRANDE}", "id_organizacao_cliente=abc"])
def test_historico_parametros_invalidos_da_400(c, adm, q):
    # UC21, RNF04
    _erro(c.get(f"{V}?{q}", headers=adm), 400, "DADOS_INVALIDOS")


def test_historico_vazio_da_200(c, adm, emp):
    # UC21 FA1, UC18
    assert c.get(V, headers=adm).json() == {"items": [], "total": 0, "page": 1, "size": 20}
    assert c.get(V, headers=emp).json()["items"] == []


def test_historico_cliente_ve_apenas_a_propria_organizacao(c, emp, emp2, historico):
    # UC18 passo 2, RN15, RN04, RNF05
    h = historico
    assert _ids_lista(c, emp) == [h["e"], h["b"], h["a"]]
    assert _ids_lista(c, emp2) == [h["d"], h["c"]]


def test_historico_cliente_ignora_filtro_de_organizacao(c, emp, emp2, historico):
    # UC18 (contrato): id_organizacao_cliente ignorado para Cliente Empresa; os demais filtros valem
    h = historico
    assert _ids_lista(c, emp, f"id_organizacao_cliente={c.id_org2}") == [h["e"], h["b"], h["a"]]
    assert _ids_lista(c, emp, "id_organizacao_cliente=999") == [h["e"], h["b"], h["a"]]
    assert _ids_lista(c, emp, "situacao=Pendente") == [h["e"]]
    assert _ids_lista(c, emp, "data_de=2026-02-01&data_ate=2026-03-01") == [h["b"]]


@pytest.mark.parametrize("chave", ["ong", "doadora"])
def test_historico_geral_cliente_ong_e_empresa_doadora_proibidos(c, todos, historico, chave):
    # UC21 FE1, RN15: Cliente ONG e Empresa Doadora -> 403
    _erro(c.get(V, headers=todos[chave]), 403, "SEM_PERMISSAO")
    _erro(c.get(f"{V}/{historico['a']}", headers=todos[chave]), 403, "SEM_PERMISSAO")


@pytest.mark.parametrize("quem", ["admin", "func", "empresa"])
def test_detalhe_da_venda_propria_ou_interno(c, todos, historico, quem):
    # UC14 passo 2, UC18 passo 4, UC21 passo 5
    r = c.get(f"{V}/{historico['e']}", headers=todos[quem])
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["id_venda"] == historico["e"] and j["quantidade"] == 2 and j["valor_total"] == 100.0 and len(j["itens"]) == 2
    assert set(j) == {"id_venda", "id_organizacao_cliente", "nome_organizacao", "data_venda", "situacao", "forma_pagamento",
                      "quantidade", "valor_total", "itens", "nota_fiscal"}


def test_detalhe_de_outra_organizacao_da_404_identico_ao_inexistente(c, emp, emp2, historico):
    # UC18 FE1, RN04, RNF05
    h = historico
    prib = _erro(c.get(f"{V}/{h['c']}", headers=emp), 404, "NAO_ENCONTRADO")
    inex = _erro(c.get(f"{V}/99999", headers=emp), 404, "NAO_ENCONTRADO")
    assert prib == inex
    _erro(c.get(f"{V}/{h['a']}", headers=emp2), 404, "NAO_ENCONTRADO")


def test_detalhe_id_enorme_negativo_e_texto(c, adm, emp):
    # RNF04
    for h in (adm, emp):
        _erro(c.get(f"{V}/{GRANDE}", headers=h), 404, "NAO_ENCONTRADO")
        _erro(c.get(f"{V}/99999", headers=h), 404, "NAO_ENCONTRADO")
        _erro(c.get(f"{V}/-1", headers=h), 404, "NAO_ENCONTRADO")
        _erro(c.get(f"{V}/abc", headers=h), 400, "DADOS_INVALIDOS")


def test_cliente_ve_o_proprio_pedido_pendente_e_cancelado_no_historico(c, emp):
    # UC18 passo 3: data, situacao, itens e valores (pedidos e compras)
    a, b = _eqs(c, 2)
    p1 = _pedido(c, emp, [a])
    p2 = _pedido(c, emp, [b])
    c.post(f"{V}/{p2['id_venda']}/cancelar", headers=emp)
    j = c.get(V, headers=emp).json()
    assert {i["id_venda"]: i["situacao"] for i in j["items"]} == {p1["id_venda"]: "Pendente", p2["id_venda"]: "Cancelada"}


# ================================================================== RNF04 ids enormes em corpo e consulta
def test_ids_enormes_nunca_dao_500(c, adm, emp):
    # RNF04: rota -> 404; corpo/consulta -> 400
    assert c.get(f"{V}?id_organizacao_cliente={GRANDE}", headers=adm).status_code == 400
    assert c.get(f"{NF}?id_organizacao_cliente={GRANDE}", headers=adm).status_code == 400
    assert c.get(f"{CAT}?id_categoria={GRANDE}", headers=emp).status_code == 400
    assert c.post(V, json={"ids_equipamento": [GRANDE]}, headers=emp).status_code == 400
    assert c.put(f"{V}/1/itens", json={"ids_equipamento": [GRANDE]}, headers=adm).status_code == 400
    # limite exato do banco (2^63-1) e aceito pelo schema e vira ITEM_INDISPONIVEL (nao 500)
    r = c.post(V, json={"ids_equipamento": [2 ** 63 - 1]}, headers=emp)
    _erro(r, 422, "ITEM_INDISPONIVEL")
    _erro(c.post(V, json={"ids_equipamento": [2 ** 63]}, headers=emp), 400, "DADOS_INVALIDOS")
    for rota in (f"{V}/{2**63}", f"{V}/{2**63}/itens", f"{NF}/{2**63}", f"{CAT}/{2**63}"):
        assert c.get(rota, headers=adm if "catalogo" not in rota else emp).status_code in (404, 405), rota


# ================================================================== RN13 / RN14 / RN15 integradas
def test_rn13_cliente_ong_e_demais_perfis_nao_compram(c, ong, doa, fun, adm):
    # RN13: Cliente ONG nao realiza compra; criar pedido e so do Cliente Empresa
    a = _eq(c)
    for h in (ong, doa, fun, adm):
        _erro(c.post(V, json={"ids_equipamento": [a]}, headers=h), 403, "SEM_PERMISSAO")
    assert _tab(c, "VENDA") == []


def test_rn14_equipamento_vendido_fica_indisponivel_para_novas_vendas_e_alteracoes(c, adm, emp, emp2):
    # RN14: apos a confirmacao, indisponivel para nova venda, troca de itens e catalogo
    v, ids = _confirmada(c, emp, adm, n=1)
    _erro(c.post(V, json={"ids_equipamento": ids}, headers=emp2), 422, "ITEM_INDISPONIVEL")
    outro = _pedido(c, emp2, _eqs(c, 1))
    _erro(c.put(f"{V}/{outro['id_venda']}/itens", json={"ids_equipamento": ids}, headers=adm), 422, "ITEM_INDISPONIVEL")
    _erro(c.get(f"{CAT}/{ids[0]}", headers=emp2), 404, "NAO_ENCONTRADO")


def test_fluxo_completo_pedido_confirmacao_nota_e_consultas(c, adm, fun, emp, emp2):
    # UC12 a UC18, UC21: ponta a ponta
    a, b = _eq(c, valor=1000.0), _eq(c, valor=500.0)
    assert {i["id_equipamento"] for i in c.get(CAT, headers=emp).json()["items"]} == {a, b}
    p = _pedido(c, emp, [a, b])
    assert c.patch(f"{V}/{p['id_venda']}", json={"forma_pagamento": "Pix"}, headers=fun).status_code == 200
    v = _confirmar(c, fun, p["id_venda"], forma="Transferência bancária").json()
    assert v["situacao"] == "Confirmada" and v["valor_total"] == 1500.0
    _erro(c.post(f"{V}/{p['id_venda']}/nota-fiscal", headers=fun), 403, "SEM_PERMISSAO")
    n = _nota(c, adm, p["id_venda"])
    assert c.get(f"{NF}/{n['id_nota']}", headers=emp).status_code == 200
    assert c.get(f"{NF}/{n['id_nota']}/download", headers=emp).status_code == 200
    assert _ids_lista(c, emp) == [p["id_venda"]] == _ids_lista(c, adm) == _ids_lista(c, fun)
    assert _ids_lista(c, emp2) == []
    assert c.get(CAT, headers=emp).json()["items"] == []


def test_criar_pedido_com_forma_pagamento_opcional(c, emp):
    # UC13, DP-79: forma_pagamento opcional no POST; omitida = 'A definir'; inválida = 400
    a, b, d = _eq(c), _eq(c), _eq(c)
    r = c.post(V, json={"ids_equipamento": [a], "forma_pagamento": "Pix"}, headers=emp)
    assert r.status_code == 201 and r.json()["forma_pagamento"] == "Pix" and r.json()["situacao"] == "Pendente"
    r = c.post(V, json={"ids_equipamento": [b]}, headers=emp)
    assert r.status_code == 201 and r.json()["forma_pagamento"] == "A definir"
    r = c.post(V, json={"ids_equipamento": [d], "forma_pagamento": "Dinheiro"}, headers=emp)
    assert r.status_code == 400 and r.json()["codigo"] == "DADOS_INVALIDOS" and "forma_pagamento" in r.json()["campos"]
