"""Testes da API do Modulo 7 (marketplace e solicitacao de doacao): UC12 ampliado, novo UC Solicitar doacao, UC11, UC19.
Contrato: contratos/modulo-7.yaml; DP-68 a DP-78 (substitui a DP-44). RN04, RN12, RN13, RN15, RNF05.
Semeado pelo conftest: orgs 1 (Cliente Empresa), 2 (Cliente ONG Ativa), 3 (Empresa Doadora), 4 (Empresa INATIVA)."""
import sqlite3
from datetime import date, timedelta

import pytest

B = "/api/v1"
M = f"{B}/marketplace"
S = f"{B}/doacoes/solicitacoes"
HOJE = date.today().isoformat()
GRANDE = 10 ** 20
ORG_ONG = 2
_seq = [0]


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _consulta(c, comando, params=()):
    con = sqlite3.connect(c.caminho_banco)
    try:
        return con.execute(comando, params).fetchall()
    finally:
        con.close()


def _sql(c, comando, params=()):
    con = sqlite3.connect(c.caminho_banco)
    con.execute("PRAGMA foreign_keys = ON")
    ultimo = con.execute(comando, params).lastrowid
    con.commit()
    con.close()
    return ultimo


def _eq(c, modelo="Dell Latitude", valor=1500.0, categoria=2, condicao="Bom", situacao="Disponível", ativo=1):
    _seq[0] += 1
    return _sql(c, "INSERT INTO EQUIPAMENTO (id_categoria, identificacao, modelo, condicao, origem, situacao, ativo, valor,"
                   " data_recebimento) VALUES (?,?,?,?,?,?,?,?,?)",
                (categoria, f"M7-{_seq[0]:05d}", modelo, condicao, "Origem Secreta", situacao, ativo, valor,
                 (date.today() - timedelta(days=30)).isoformat()))


def _erro(r, status, codigo):
    assert r.status_code == status, r.text
    corpo = r.json()
    assert set(corpo) == {"codigo", "mensagem", "campos"} and corpo["codigo"] == codigo
    return corpo


def _sit_eq(c, i):
    return _consulta(c, "SELECT situacao FROM EQUIPAMENTO WHERE id_equipamento=?", (i,))[0][0]


@pytest.fixture()
def c(cliente):
    return cliente


@pytest.fixture()
def H(c, token_de):
    return {k: _h(token_de(c, k)) for k in ("admin", "func", "empresa", "ong", "doadora")}


def _pedir(c, H, ids):
    r = c.post(S, json={"ids_equipamentos": ids}, headers=H["ong"])
    assert r.status_code == 201, r.text
    return r.json()


# ---------------------------------------------------------------- marketplace publico
def test_marketplace_publico_sem_valor_origem_nem_vinculos(c):
    # UC12 ampliado, DP-74: visitante ve o produto, sem valor, origem, identificacao
    e = _eq(c)
    r = c.get(f"{M}/produtos")
    assert r.status_code == 200 and r.json()["total"] == 1
    item = r.json()["items"][0]
    assert set(item) == {"id_equipamento", "modelo", "categoria", "id_categoria", "condicao", "imagem_url"}  # DP-90
    assert c.get(f"{M}/produtos/{e}").json() == item
    assert [x["nome"] for x in c.get(f"{M}/categorias").json()] == ["Notebooks"]


def test_marketplace_valor_so_para_cliente_empresa(c, H):
    # DP-74
    e = _eq(c, valor=1234.5)
    for k in ("ong", "doadora", "admin", "func"):
        assert "valor" not in c.get(f"{M}/produtos/{e}", headers=H[k]).json(), k
        assert "valor" not in c.get(f"{M}/produtos", headers=H[k]).json()["items"][0], k
    assert c.get(f"{M}/produtos/{e}", headers=H["empresa"]).json()["valor"] == 1234.5
    assert c.get(f"{M}/produtos", headers=H["empresa"]).json()["items"][0]["valor"] == 1234.5
    # token invalido = visitante, sem erro
    r = c.get(f"{M}/produtos/{e}", headers={"Authorization": "Bearer lixo"})
    assert r.status_code == 200 and "valor" not in r.json()


def test_marketplace_exclui_nao_elegiveis_e_404(c):
    # RN13: so Disponivel, ativo, condicao apta, valor > 0
    ok = _eq(c)
    ruins = [_eq(c, situacao="Recebido"), _eq(c, ativo=0), _eq(c, condicao="A avaliar"), _eq(c, valor=None)]
    r = c.get(f"{M}/produtos")
    assert [i["id_equipamento"] for i in r.json()["items"]] == [ok]
    for e in ruins:
        _erro(c.get(f"{M}/produtos/{e}"), 404, "NAO_ENCONTRADO")
    _erro(c.get(f"{M}/produtos/{GRANDE}"), 404, "NAO_ENCONTRADO")


def test_marketplace_filtros_e_paginacao(c):
    a, b = _eq(c, modelo="Acer"), _eq(c, modelo="Samsung", categoria=3)
    assert c.get(f"{M}/produtos?id_categoria=3").json()["total"] == 1
    assert c.get(f"{M}/produtos?busca=ace").json()["items"][0]["id_equipamento"] == a
    j = c.get(f"{M}/produtos?size=1&page=2").json()
    assert j["total"] == 2 and j["items"][0]["id_equipamento"] == b and j["size"] == 1
    assert c.get(f"{M}/produtos?size=101").status_code == 400


# ---------------------------------------------------------------- perfis (401/403/404)
def test_perfis_solicitacoes(c, H):
    e = _eq(c)
    _erro(c.post(S, json={"ids_equipamentos": [e]}), 401, "NAO_AUTENTICADO")
    _erro(c.get(S), 401, "NAO_AUTENTICADO")
    for k in ("admin", "func", "empresa", "doadora"):
        _erro(c.post(S, json={"ids_equipamentos": [e]}, headers=H[k]), 403, "SEM_PERMISSAO")
    for k in ("empresa", "doadora"):
        _erro(c.get(S, headers=H[k]), 403, "SEM_PERMISSAO")
    sol = _pedir(c, H, [e])["id_solicitacao_doacao"]
    for k in ("ong", "empresa", "doadora"):
        _erro(c.patch(f"{S}/{sol}/aprovar", headers=H[k]), 403, "SEM_PERMISSAO")
        _erro(c.patch(f"{S}/{sol}/recusar", json={"motivo": "sem estoque"}, headers=H[k]), 403, "SEM_PERMISSAO")
    for k in ("admin", "func", "empresa", "doadora"):
        _erro(c.patch(f"{S}/{sol}/cancelar", headers=H[k]), 403, "SEM_PERMISSAO")
    _erro(c.get(f"{S}/{sol + 99}", headers=H["admin"]), 404, "NAO_ENCONTRADO")
    _erro(c.get(f"{S}/{GRANDE}", headers=H["admin"]), 404, "NAO_ENCONTRADO")
    assert c.get(f"{S}/{sol}", headers=H["func"]).status_code == 200


def test_ong_so_ve_as_proprias(c, H, hash_senha):
    # RN04, RN15, RNF05: outra ONG -> 404 no detalhe e lista vazia
    e = _eq(c)
    sol = _pedir(c, H, [e])["id_solicitacao_doacao"]
    org = _sql(c, "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao)"
                  " VALUES ('88888888888888','Outra ONG','Cliente ONG','1','o@o.com','Rua','Ativa')")
    _sql(c, "INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (?,?,?,?,?)",
         (org, "outra@ong.com", "Cliente ONG", hash_senha, "Outra"))
    from tests.conftest import SENHA
    tok = c.post(f"{B}/auth/login", json={"email": "outra@ong.com", "senha": SENHA}).json()["access_token"]
    h2 = _h(tok)
    assert c.get(S, headers=h2).json()["total"] == 0
    _erro(c.get(f"{S}/{sol}", headers=h2), 404, "NAO_ENCONTRADO")
    _erro(c.patch(f"{S}/{sol}/cancelar", headers=h2), 404, "NAO_ENCONTRADO")
    assert c.get(S, headers=H["ong"]).json()["total"] == 1


# ---------------------------------------------------------------- criar / reserva
def test_criar_solicitacao_reserva_equipamento(c, H):
    # DP-69/70: nasce Pendente, equipamento continua Disponivel mas sai do marketplace e do catalogo
    e1, e2 = _eq(c), _eq(c)
    s = _pedir(c, H, [e1, e2])
    assert s["situacao"] == "Pendente" and s["data_solicitacao"] == HOJE and s["id_organizacao_ong"] == ORG_ONG
    assert [i["id_equipamento"] for i in s["itens"]] == [e1, e2]
    assert all("valor" not in i and "origem" not in i for i in s["itens"])
    assert _sit_eq(c, e1) == "Disponível"
    assert c.get(f"{M}/produtos").json()["total"] == 0
    _erro(c.get(f"{M}/produtos/{e1}"), 404, "NAO_ENCONTRADO")
    assert c.get(f"{B}/catalogo", headers=H["empresa"]).json()["total"] == 0
    assert c.get(S, headers=H["ong"]).json()["total"] == 1


def test_criar_validacoes(c, H):
    e = _eq(c)
    for corpo in ({}, {"ids_equipamentos": []}, {"ids_equipamentos": [e, e]}, {"ids_equipamentos": list(range(1, 22))},
                  {"ids_equipamentos": [GRANDE]}, {"ids_equipamentos": ["a"]}):
        _erro(c.post(S, json=corpo, headers=H["ong"]), 400, "DADOS_INVALIDOS")
    for ruim in (_eq(c, situacao="Recebido"), _eq(c, ativo=0), _eq(c, situacao="Vendido"), 99999):
        _erro(c.post(S, json={"ids_equipamentos": [e, ruim]}, headers=H["ong"]), 422, "EQUIPAMENTO_INDISPONIVEL")
    assert _consulta(c, "SELECT COUNT(*) FROM SOLICITACAO_DOACAO")[0][0] == 0  # nada gravado em erro


def test_ong_inativa_nao_solicita(c, H):
    e = _eq(c)
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ORG_ONG,))
    # conta inativa e barrada ja no login/sessao; o token emitido antes recebe CONTA_INATIVA (403)
    assert c.post(S, json={"ids_equipamentos": [e]}, headers=H["ong"]).status_code in (403, 422)


def test_concorrencia_mesmo_equipamento_so_uma_vence(c, H):
    # DP-70: segunda solicitacao do mesmo equipamento -> 422 EQUIPAMENTO_RESERVADO
    e = _eq(c)
    _pedir(c, H, [e])
    _erro(c.post(S, json={"ids_equipamentos": [e]}, headers=H["ong"]), 422, "EQUIPAMENTO_RESERVADO")
    assert _consulta(c, "SELECT COUNT(*) FROM SOLICITACAO_DOACAO")[0][0] == 1


def test_reserva_por_venda_pendente_e_vice_versa(c, H):
    # DP-70: venda Pendente reserva; solicitacao de doacao Pendente bloqueia pedido (422 EQUIPAMENTO_RESERVADO)
    e_venda, e_doa = _eq(c), _eq(c)
    r = c.post(f"{B}/vendas", json={"ids_equipamento": [e_venda]}, headers=H["empresa"])
    assert r.status_code == 201, r.text
    _erro(c.post(S, json={"ids_equipamentos": [e_venda]}, headers=H["ong"]), 422, "EQUIPAMENTO_RESERVADO")
    _pedir(c, H, [e_doa])
    _erro(c.post(f"{B}/vendas", json={"ids_equipamento": [e_doa]}, headers=H["empresa"]), 422, "EQUIPAMENTO_RESERVADO")
    # substituicao de itens tambem respeita a reserva
    e3 = _eq(c)
    venda = c.post(f"{B}/vendas", json={"ids_equipamento": [e3]}, headers=H["empresa"]).json()["id_venda"]
    resp = c.put(f"{B}/vendas/{venda}/itens", json={"ids_equipamento": [e3, e_doa]}, headers=H["empresa"])
    _erro(resp, 422, "EQUIPAMENTO_RESERVADO")


# ---------------------------------------------------------------- aprovar / recusar / cancelar
def test_aprovar_executa_uc11(c, H):
    e1, e2 = _eq(c), _eq(c)
    sol = _pedir(c, H, [e1, e2])["id_solicitacao_doacao"]
    r = c.patch(f"{S}/{sol}/aprovar", headers=H["func"])
    assert r.status_code == 200, r.text
    j = r.json()
    assert j["situacao"] == "Aprovada" and j["decidido_por"] == "Nome func" and j["data_decisao"] == HOJE
    assert _sit_eq(c, e1) == _sit_eq(c, e2) == "Doado"
    linhas = _consulta(c, "SELECT id_equipamento, id_organizacao_ong, data_doacao FROM DOACAO ORDER BY 1")
    assert linhas == [(e1, ORG_ONG, HOJE), (e2, ORG_ONG, HOJE)]
    assert c.get(f"{B}/doacoes", headers=H["ong"]).json()["total"] == 2  # UC19
    _erro(c.patch(f"{S}/{sol}/aprovar", headers=H["admin"]), 422, "SOLICITACAO_NAO_PENDENTE")


def test_aprovar_falha_em_um_item_desfaz_tudo(c, H):
    e1, e2 = _eq(c), _eq(c)
    sol = _pedir(c, H, [e1, e2])["id_solicitacao_doacao"]
    _sql(c, "UPDATE EQUIPAMENTO SET situacao='Em manutenção' WHERE id_equipamento=?", (e2,))
    _erro(c.patch(f"{S}/{sol}/aprovar", headers=H["admin"]), 422, "EQUIPAMENTO_INDISPONIVEL")
    assert _sit_eq(c, e1) == "Disponível"
    assert _consulta(c, "SELECT COUNT(*) FROM DOACAO")[0][0] == 0
    assert c.get(f"{S}/{sol}", headers=H["admin"]).json()["situacao"] == "Pendente"


def test_aprovar_com_ong_inativa(c, H):
    e = _eq(c)
    sol = _pedir(c, H, [e])["id_solicitacao_doacao"]
    _sql(c, "UPDATE ORGANIZACAO SET situacao='Inativa' WHERE id_organizacao=?", (ORG_ONG,))
    _erro(c.patch(f"{S}/{sol}/aprovar", headers=H["admin"]), 422, "ORGANIZACAO_INVALIDA")
    assert _sit_eq(c, e) == "Disponível"


def test_recusar_exige_motivo_e_libera_reserva(c, H):
    e = _eq(c)
    sol = _pedir(c, H, [e])["id_solicitacao_doacao"]
    for corpo in ({}, {"motivo": ""}, {"motivo": "ab"}, {"motivo": "x" * 501}):
        corpo_erro = _erro(c.patch(f"{S}/{sol}/recusar", json=corpo, headers=H["admin"]), 400, "DADOS_INVALIDOS")
        assert "motivo" in corpo_erro["campos"]
    r = c.patch(f"{S}/{sol}/recusar", json={"motivo": "Sem perfil adequado"}, headers=H["admin"])
    assert r.status_code == 200
    j = r.json()
    assert (j["situacao"], j["motivo_recusa"], j["decidido_por"], j["data_decisao"]) == (
        "Recusada", "Sem perfil adequado", "Nome admin", HOJE)
    assert c.get(f"{S}/{sol}", headers=H["ong"]).json()["motivo_recusa"] == "Sem perfil adequado"  # DP-73
    assert _sit_eq(c, e) == "Disponível"
    assert c.get(f"{M}/produtos").json()["total"] == 1  # liberado
    _pedir(c, H, [e])  # pode ser pedido de novo
    _erro(c.patch(f"{S}/{sol}/recusar", json={"motivo": "outra vez"}, headers=H["admin"]), 422, "SOLICITACAO_NAO_PENDENTE")


def test_cancelar_pela_ong_libera_reserva_e_e_final(c, H):
    e = _eq(c)
    sol = _pedir(c, H, [e])["id_solicitacao_doacao"]
    r = c.patch(f"{S}/{sol}/cancelar", headers=H["ong"])
    assert r.status_code == 200 and r.json()["situacao"] == "Cancelada" and r.json()["data_decisao"] == HOJE
    assert c.get(f"{M}/produtos").json()["total"] == 1
    _erro(c.patch(f"{S}/{sol}/cancelar", headers=H["ong"]), 422, "SOLICITACAO_NAO_PENDENTE")
    _erro(c.patch(f"{S}/{sol}/aprovar", headers=H["admin"]), 422, "SOLICITACAO_NAO_PENDENTE")


def test_listar_filtra_por_situacao(c, H):
    a, b = _eq(c), _eq(c)
    s1, s2 = _pedir(c, H, [a])["id_solicitacao_doacao"], _pedir(c, H, [b])["id_solicitacao_doacao"]
    c.patch(f"{S}/{s1}/cancelar", headers=H["ong"])
    assert c.get(f"{S}?situacao=Pendente", headers=H["admin"]).json()["total"] == 1
    assert c.get(f"{S}?situacao=Cancelada", headers=H["ong"]).json()["items"][0]["id_solicitacao_doacao"] == s1
    assert c.get(f"{S}?situacao=Xis", headers=H["admin"]).status_code == 400
    assert s2


# ---------------------------------------------------------------- DP-63 e DDL
def test_organizacao_com_solicitacao_de_doacao_tem_historico(c, H):
    # DP-63: SOLICITACAO_DOACAO conta como historico -> ORGANIZACAO_EM_USO
    _pedir(c, H, [_eq(c)])
    _erro(c.delete(f"{B}/organizacoes/{ORG_ONG}", headers=H["admin"]), 422, "ORGANIZACAO_EM_USO")


def test_ddl_criado_sem_alterar_sql_oficial(c):
    tabelas = {l[0] for l in _consulta(c, "SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"SOLICITACAO_DOACAO", "ITEM_SOLICITACAO_DOACAO"} <= tabelas
    from pathlib import Path
    sql = (Path(__file__).resolve().parents[2] / "banco" / "Codigo_Modelo_Fisico.sql").read_text(encoding="utf-8")
    # O SQL oficial passou a incluir as tabelas (DP-75 levada ao modelo pelo Cowork)
    assert "CREATE TABLE IF NOT EXISTS SOLICITACAO_DOACAO" in sql


def test_solicitacao_devolve_campos_esperados_pelo_front(c, H):
    # Novo UC Solicitar doação, DP-77: nome_organizacao, itens, situação, decisão (doacoes-solicitacoes.js)
    s = _pedir(c, H, [_eq(c)])
    assert s["nome_organizacao"] == s["nome_ong"] and s["nome_organizacao"]
    for k in ("id_solicitacao_doacao", "situacao", "motivo_recusa", "decidido_por", "data_decisao", "data_solicitacao", "itens"):
        assert k in s
    assert set(s["itens"][0]) == {"id_equipamento", "modelo", "categoria", "condicao"}
    item = c.get(S, headers=H["func"]).json()["items"][0]
    assert item["nome_organizacao"] == s["nome_organizacao"]
    rec = c.patch(f"{S}/{s['id_solicitacao_doacao']}/recusar", json={"motivo": "sem estoque"}, headers=H["func"]).json()
    assert rec["motivo_recusa"] == "sem estoque" and rec["decidido_por"] and rec["data_decisao"]


def test_menu_solicitacoes_doacao_por_perfil(c, H):
    # DP-80: chave de menu para ONG, Administrador e Funcionário
    for k, esperado in (("ong", True), ("admin", True), ("func", True), ("empresa", False), ("doadora", False)):
        f = c.get(f"{B}/auth/me", headers=H[k]).json()["funcionalidades"]
        assert ("solicitacoes_doacao" in f) is esperado, k
