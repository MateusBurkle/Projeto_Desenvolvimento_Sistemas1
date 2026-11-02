"""Testes da API do Modulo 3 (Equipamentos e categorias): UC05, UC07, UC08.
Requisitos: RF07, RF08, RF11, RF12; RN01, RN07, RN08, RN11, RN12 (RN13/RN14/RN21 como borda); RNF04, RNF05.
Contrato: contratos/modulo-3.yaml v1.0.0 (DP-30 a DP-37). Contas ficticias do conftest.
Semeado pelo conftest: orgs 1 (Cliente Empresa), 2 (Cliente ONG Ativa), 3 (Empresa Doadora), 4 (Cliente Empresa INATIVA).
Categorias base 1..6 criadas na inicializacao (Computadores, Notebooks, Monitores, Periféricos, Placas de vídeo, Placas-mãe)."""
import sqlite3
from datetime import date, timedelta

import pytest

C = "/api/v1/categorias"
E = "/api/v1/equipamentos"
CHAVES = ["admin", "func", "empresa", "ong", "doadora"]
BASE = ["Computadores", "Notebooks", "Monitores", "Periféricos", "Placas de vídeo", "Placas-mãe"]
SITUACOES = ["Recebido", "Em avaliação", "Em manutenção", "Recondicionado", "Disponível", "Vendido", "Doado",
             "Destinado à reciclagem"]
CONDICOES = ["A avaliar", "Bom", "Regular", "Necessita reparo", "Sem condições de reuso"]
HOJE = date.today()
ONG_ATIVA = 2


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


_seq = [0]


def _corpo_eq(**kw):
    _seq[0] += 1
    base = {"identificacao": f"EQ-{_seq[0]:04d}", "id_categoria": 2, "modelo": "Dell Latitude 5420", "condicao": "Bom",
            "origem": "Empresa Doadora Alfa", "data_recebimento": (HOJE - timedelta(days=10)).isoformat(),
            "valor": 1500.0}
    base.update(kw)
    return base


def _criar_eq(cliente, h, **kw):
    r = cliente.post(E, json=_corpo_eq(**kw), headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _criar_cat(cliente, h, nome):
    r = cliente.post(C, json={"nome": nome}, headers=h)
    assert r.status_code == 201, r.text
    return r.json()


def _sit(cliente, h, id_eq, situacao, **kw):
    return cliente.patch(f"{E}/{id_eq}/situacao", json={"situacao": situacao, **kw}, headers=h)


def _disponivel(cliente, h, **kw):
    """Equipamento ja Disponivel (condicao Bom, valor > 0)."""
    eq = _criar_eq(cliente, h, **kw)
    r = _sit(cliente, h, eq["id_equipamento"], "Disponível")
    assert r.status_code == 200, r.text
    return r.json()


def _forcar_situacao(cliente, id_eq, situacao):
    _sql(cliente, "UPDATE EQUIPAMENTO SET situacao=? WHERE id_equipamento=?", (situacao, id_eq))


def _ong_inativa(cliente):
    return _sql(cliente, "INSERT INTO ORGANIZACAO (cnpj, nome_razao_social, tipo, telefone, email, endereco, situacao)"
                         " VALUES ('99999999999901','ONG Parada','Cliente ONG','11999999999','p@o.com','Rua 1','Inativa')")


# ------------------------------------------------------------------ rotas e matriz de permissoes (RN01, RNF05, DP-37)
def _rotas():
    """(metodo, caminho, corpo, perfis autorizados). Corpos validos: a permissao e o unico motivo de recusa."""
    eq = {"identificacao": "X-1", "id_categoria": 2, "modelo": "m", "condicao": "Bom", "origem": "o",
          "data_recebimento": "2026-01-01"}
    return [
        ("GET", C, None, {"admin", "func"}),
        ("POST", C, {"nome": "Categoria Matriz"}, {"admin"}),
        ("GET", f"{C}/1", None, {"admin", "func"}),
        ("PUT", f"{C}/1", {"nome": "Outro Nome"}, {"admin"}),
        ("PATCH", f"{C}/1/situacao", {"ativa": True}, {"admin"}),
        ("GET", E, None, {"admin", "func"}),
        ("POST", E, eq, {"admin", "func"}),
        ("GET", f"{E}/9999", None, {"admin", "func"}),
        ("PUT", f"{E}/9999", eq, {"admin", "func"}),
        ("PATCH", f"{E}/9999/situacao", {"situacao": "Recebido"}, {"admin", "func"}),
        ("PATCH", f"{E}/9999/ativo", {"ativo": True}, {"admin", "func"}),
    ]


@pytest.mark.parametrize("indice", range(11))
def test_sem_token_401_em_todas_as_rotas(cliente, indice):
    # RNF05, RN01
    metodo, url, corpo, _ = _rotas()[indice]
    _erro(cliente.request(metodo, url, json=corpo), 401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("indice", range(11))
def test_token_invalido_401_em_todas_as_rotas(cliente, indice):
    # RNF05
    metodo, url, corpo, _ = _rotas()[indice]
    _erro(cliente.request(metodo, url, json=corpo, headers=_h("token.invalido.xyz")), 401, "NAO_AUTENTICADO")


@pytest.mark.parametrize("chave", CHAVES)
@pytest.mark.parametrize("indice", range(11))
def test_matriz_de_permissoes_por_rota_e_perfil(cliente, token_de, chave, indice):
    # RN01, RN03, RF07, RF11, RF12, DP-37: autorizado nao recebe 401/403; proibido recebe 403 SEM_PERMISSAO
    metodo, url, corpo, autorizados = _rotas()[indice]
    r = cliente.request(metodo, url, json=corpo, headers=_h(token_de(cliente, chave)))
    if chave in autorizados:
        assert r.status_code not in (401, 403), f"{metodo} {url} {chave}: {r.status_code} {r.text}"
    else:
        _erro(r, 403, "SEM_PERMISSAO")


@pytest.mark.parametrize("chave", ["empresa", "ong", "doadora"])
def test_clientes_e_doadora_403_em_tudo_e_nada_gravado(cliente, token_de, chave):
    # RN01, RNF05, DP-37
    antes = (_tab(cliente, "CATEGORIA"), _tab(cliente, "EQUIPAMENTO"), _tab(cliente, "DOACAO"))
    h = _h(token_de(cliente, chave))
    for metodo, url, corpo, _ in _rotas():
        _erro(cliente.request(metodo, url, json=corpo, headers=h), 403, "SEM_PERMISSAO")
    assert (_tab(cliente, "CATEGORIA"), _tab(cliente, "EQUIPAMENTO"), _tab(cliente, "DOACAO")) == antes


def test_funcionario_nao_grava_categorias(cliente, fun):
    # RN01, RF07, DP-37: Funcionario so consulta categorias
    antes = _tab(cliente, "CATEGORIA")
    _erro(cliente.post(C, json={"nome": "Nova"}, headers=fun), 403, "SEM_PERMISSAO")
    _erro(cliente.put(f"{C}/7", json={"nome": "X"}, headers=fun), 403, "SEM_PERMISSAO")
    _erro(cliente.patch(f"{C}/1/situacao", json={"ativa": False}, headers=fun), 403, "SEM_PERMISSAO")
    assert _tab(cliente, "CATEGORIA") == antes


def test_funcionario_cadastra_e_atualiza_equipamentos(cliente, fun):
    # UC07, UC08, RF11, RF12, RN03
    eq = _criar_eq(cliente, fun)
    assert cliente.put(f"{E}/{eq['id_equipamento']}", json={k: eq[k] for k in (
        "identificacao", "id_categoria", "modelo", "condicao", "origem", "data_recebimento", "valor")} | {"modelo": "Novo"},
        headers=fun).status_code == 200
    assert _sit(cliente, fun, eq["id_equipamento"], "Em avaliação").status_code == 200
    assert cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=fun).status_code == 200


# ------------------------------------------------------------------ UC05: categorias base (RF08, DP-31)
def test_seis_categorias_base_existem_ativas_e_protegidas(cliente, adm):
    # UC05 passo 6, RF08
    r = cliente.get(C, headers=adm)
    assert r.status_code == 200
    por_nome = {c["nome"]: c for c in r.json()["items"]}
    assert set(BASE) <= set(por_nome)
    for n in BASE:
        assert por_nome[n]["ativa"] is True and por_nome[n]["protegida"] is True
        assert por_nome[n]["total_equipamentos"] == 0


def test_seed_das_categorias_base_e_idempotente(ambiente, hash_senha):
    # UC05 passo 6, RF08: reinicializar o banco nao duplica as seis categorias
    from fastapi.testclient import TestClient
    from app.main import criar_app
    for _ in range(2):
        with TestClient(criar_app()):
            pass
    con = sqlite3.connect(ambiente)
    nomes = [r[0] for r in con.execute("SELECT nome FROM CATEGORIA")]
    con.close()
    assert sorted(nomes) == sorted(BASE)


# ------------------------------------------------------------------ UC05: criar / listar / obter
def test_criar_categoria_201_nasce_ativa_nao_protegida(cliente, adm):
    # UC05 fluxo principal passo 4, RF07, RN07
    r = cliente.post(C, json={"nome": "  Servidores  "}, headers=adm)
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["nome"] == "Servidores" and d["ativa"] is True and d["protegida"] is False and d["total_equipamentos"] == 0
    assert set(d) == {"id_categoria", "nome", "ativa", "protegida", "total_equipamentos"}
    assert cliente.get(f"{C}/{d['id_categoria']}", headers=adm).json() == d
    assert _consulta(cliente, "SELECT ativa FROM CATEGORIA WHERE id_categoria=?", (d["id_categoria"],))[0][0] == 1


def test_categoria_nova_fica_disponivel_para_equipamento(cliente, adm):
    # UC05 passo 5, RN08
    cat = _criar_cat(cliente, adm, "Servidores")
    assert _criar_eq(cliente, adm, id_categoria=cat["id_categoria"])["nome_categoria"] == "Servidores"


@pytest.mark.parametrize("corpo", [{}, {"nome": ""}, {"nome": "   "}, {"nome": "x" * 81}, {"nome": 123}, {"nome": None}])
def test_criar_categoria_nome_invalido_400_e_nada_gravado(cliente, adm, corpo):
    # UC05 FE1, FE3, RNF04
    antes = _tab(cliente, "CATEGORIA")
    c = _erro(cliente.post(C, json=corpo, headers=adm), 400, "DADOS_INVALIDOS")
    assert "nome" in c["campos"]
    assert _tab(cliente, "CATEGORIA") == antes


def test_criar_categoria_nome_com_80_caracteres_aceito(cliente, adm):
    # UC05 passo 4: limite 80
    assert cliente.post(C, json={"nome": "x" * 80}, headers=adm).status_code == 201


@pytest.mark.parametrize("nome", ["Servidores", "SERVIDORES", "servidores", " servidores "])
def test_criar_categoria_duplicada_sem_diferenciar_caixa_409(cliente, adm, nome):
    # UC05 FE3, RN07, DP-31
    _criar_cat(cliente, adm, "Servidores")
    antes = _tab(cliente, "CATEGORIA")
    c = _erro(cliente.post(C, json={"nome": nome}, headers=adm), 409, "NOME_CATEGORIA_DUPLICADO")
    assert c["campos"] == {"nome": "duplicado"}
    assert _tab(cliente, "CATEGORIA") == antes


@pytest.mark.parametrize("nome", ["computadores", "NOTEBOOKS", "placas de vídeo", "PLACAS-MÃE"])
def test_criar_categoria_com_nome_de_base_sem_caixa_409(cliente, adm, nome):
    # UC05 FE3, RN07, DP-31
    _erro(cliente.post(C, json={"nome": nome}, headers=adm), 409, "NOME_CATEGORIA_DUPLICADO")


def test_listar_categorias_ordem_paginacao_e_filtros(cliente, adm):
    # UC05 FA1, RF08: ordenado por nome, {items,total,page,size}
    _criar_cat(cliente, adm, "Zeta")
    _criar_cat(cliente, adm, "Alfa")
    r = cliente.get(C, headers=adm).json()
    assert set(r) == {"items", "total", "page", "size"} and r["total"] == 8 and r["page"] == 1 and r["size"] == 20
    nomes = [c["nome"] for c in r["items"]]
    assert nomes == sorted(nomes, key=str.casefold)
    p = cliente.get(C, params={"page": 2, "size": 3}, headers=adm).json()
    assert len(p["items"]) == 3 and p["page"] == 2 and p["size"] == 3 and p["total"] == 8
    assert [c["nome"] for c in cliente.get(C, params={"q": "ALF"}, headers=adm).json()["items"]] == ["Alfa"]
    assert cliente.get(C, params={"q": "%"}, headers=adm).json()["total"] == 0  # curinga escapado


def test_listar_categorias_filtro_ativa(cliente, adm):
    # UC05 FA1, FA2
    cat = _criar_cat(cliente, adm, "Servidores")
    cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": False}, headers=adm)
    inativas = cliente.get(C, params={"ativa": "false"}, headers=adm).json()
    assert [c["nome"] for c in inativas["items"]] == ["Servidores"]
    assert cliente.get(C, params={"ativa": "true"}, headers=adm).json()["total"] == 6


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 0}, {"size": 101}, {"ativa": "talvez"}, {"q": "x" * 81}])
def test_listar_categorias_parametros_invalidos_400(cliente, adm, params):
    # RNF04, convencoes de paginacao
    _erro(cliente.get(C, params=params, headers=adm), 400, "DADOS_INVALIDOS")


def test_listar_categorias_conta_total_equipamentos(cliente, adm):
    # UC05 FA1: total_equipamentos
    _criar_eq(cliente, adm, id_categoria=2)
    _criar_eq(cliente, adm, id_categoria=2)
    por_id = {c["id_categoria"]: c for c in cliente.get(C, headers=adm).json()["items"]}
    assert por_id[2]["total_equipamentos"] == 2 and por_id[1]["total_equipamentos"] == 0


def test_obter_categoria_inexistente_404(cliente, adm):
    # UC05 FA1
    _erro(cliente.get(f"{C}/9999", headers=adm), 404, "NAO_ENCONTRADO")


def test_id_categoria_nao_numerico_400(cliente, adm):
    # RNF04
    _erro(cliente.get(f"{C}/abc", headers=adm), 400, "DADOS_INVALIDOS")


# ------------------------------------------------------------------ UC05 FA1: renomear
def test_renomear_categoria_preserva_id_e_vinculos(cliente, adm):
    # UC05 FA1, RF07: o id nao muda e os equipamentos continuam vinculados
    cat = _criar_cat(cliente, adm, "Servidores")
    eq = _criar_eq(cliente, adm, id_categoria=cat["id_categoria"])
    r = cliente.put(f"{C}/{cat['id_categoria']}", json={"nome": "Servidores Rack"}, headers=adm)
    assert r.status_code == 200 and r.json()["nome"] == "Servidores Rack" and r.json()["id_categoria"] == cat["id_categoria"]
    assert r.json()["total_equipamentos"] == 1
    g = cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()
    assert g["id_categoria"] == cat["id_categoria"] and g["nome_categoria"] == "Servidores Rack"


def test_renomear_categoria_para_si_mesma_ou_so_caixa_200(cliente, adm):
    # UC05 FA1, DP-31: a duplicidade exclui o proprio registro
    cat = _criar_cat(cliente, adm, "Servidores")
    assert cliente.put(f"{C}/{cat['id_categoria']}", json={"nome": "Servidores"}, headers=adm).status_code == 200
    r = cliente.put(f"{C}/{cat['id_categoria']}", json={"nome": "SERVIDORES"}, headers=adm)
    assert r.status_code == 200 and r.json()["nome"] == "SERVIDORES"


def test_renomear_para_nome_de_outra_409(cliente, adm):
    # UC05 FE3, RN07
    a = _criar_cat(cliente, adm, "Alfa")
    _criar_cat(cliente, adm, "Beta")
    _erro(cliente.put(f"{C}/{a['id_categoria']}", json={"nome": "BETA"}, headers=adm), 409, "NOME_CATEGORIA_DUPLICADO")
    assert cliente.get(f"{C}/{a['id_categoria']}", headers=adm).json()["nome"] == "Alfa"


def test_renomear_nome_invalido_400_e_inexistente_404(cliente, adm):
    # UC05 FE1, RNF04; ordem 400 -> 404
    cat = _criar_cat(cliente, adm, "Alfa")
    _erro(cliente.put(f"{C}/{cat['id_categoria']}", json={"nome": " "}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(cliente.put(f"{C}/9999", json={"nome": "Qualquer"}, headers=adm), 404, "NAO_ENCONTRADO")
    _erro(cliente.put(f"{C}/9999", json={"nome": ""}, headers=adm), 400, "DADOS_INVALIDOS")


@pytest.mark.parametrize("id_cat", range(1, 7))
def test_renomear_categoria_base_422_protegida(cliente, adm, id_cat):
    # UC05 FE4, RF08, DP-31
    antes = _tab(cliente, "CATEGORIA")
    c = _erro(cliente.put(f"{C}/{id_cat}", json={"nome": "Outro Nome"}, headers=adm), 422, "CATEGORIA_PROTEGIDA")
    assert "nome" in c["campos"]
    assert _tab(cliente, "CATEGORIA") == antes


def test_renomear_base_para_mesmo_nome_ainda_422(cliente, adm):
    # UC05 FE4: protegida tem precedencia sobre 409 (ordem 400 -> 404 -> 422 -> 409)
    _erro(cliente.put(f"{C}/1", json={"nome": "Computadores"}, headers=adm), 422, "CATEGORIA_PROTEGIDA")
    _erro(cliente.put(f"{C}/1", json={"nome": "Notebooks"}, headers=adm), 422, "CATEGORIA_PROTEGIDA")


def test_categoria_protegida_vale_para_base_mesmo_se_nome_com_outra_caixa(cliente, adm):
    # UC05 FE4, DP-31: protegida e calculada sem diferenciar caixa
    from app.categorias.service import eh_protegida
    assert all(eh_protegida(n.upper()) for n in BASE) and not eh_protegida("Servidores")


# ------------------------------------------------------------------ UC05 FA2: desativar / reativar (RN07)
def test_desativar_e_reativar_categoria(cliente, adm):
    # UC05 FA2, RN07
    cat = _criar_cat(cliente, adm, "Servidores")
    r = cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": False}, headers=adm)
    assert r.status_code == 200 and r.json()["ativa"] is False
    r = cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": True}, headers=adm)
    assert r.status_code == 200 and r.json()["ativa"] is True


def test_desativar_categoria_preserva_equipamentos_e_vinculos(cliente, adm):
    # UC05 FA2, RN07, RF07: sem exclusao e sem desvincular
    cat = _criar_cat(cliente, adm, "Servidores")
    eq = _criar_eq(cliente, adm, id_categoria=cat["id_categoria"])
    cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": False}, headers=adm)
    g = cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()
    assert g["id_categoria"] == cat["id_categoria"] and g["categoria_ativa"] is False
    assert cliente.get(f"{C}/{cat['id_categoria']}", headers=adm).json()["total_equipamentos"] == 1


def test_desativar_categoria_e_idempotente(cliente, adm):
    # UC05 FA2 (contrato: idempotente)
    cat = _criar_cat(cliente, adm, "Servidores")
    for _ in range(2):
        r = cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": False}, headers=adm)
        assert r.status_code == 200 and r.json()["ativa"] is False


@pytest.mark.parametrize("id_cat", range(1, 7))
def test_desativar_categoria_base_422_protegida(cliente, adm, id_cat):
    # UC05 FE4, RF08, DP-31
    c = _erro(cliente.patch(f"{C}/{id_cat}/situacao", json={"ativa": False}, headers=adm), 422, "CATEGORIA_PROTEGIDA")
    assert "ativa" in c["campos"]
    assert _consulta(cliente, "SELECT ativa FROM CATEGORIA WHERE id_categoria=?", (id_cat,))[0][0] == 1


def test_reativar_categoria_base_ja_ativa_e_200(cliente, adm):
    # UC05 FE4: so desativar e proibido; ativa=true e idempotente
    r = cliente.patch(f"{C}/1/situacao", json={"ativa": True}, headers=adm)
    assert r.status_code == 200 and r.json()["ativa"] is True


def test_situacao_categoria_invalida_400_e_inexistente_404(cliente, adm):
    # RNF04, UC05 FA2
    _erro(cliente.patch(f"{C}/7/situacao", json={}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(cliente.patch(f"{C}/7/situacao", json={"ativa": "talvez"}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(cliente.patch(f"{C}/9999/situacao", json={"ativa": False}, headers=adm), 404, "NAO_ENCONTRADO")


def test_nao_ha_rota_de_exclusao_de_categoria_nem_equipamento(cliente, adm):
    # UC05 FA2, UC07 FA2, RN07: apenas desativar
    cat = _criar_cat(cliente, adm, "Servidores")
    eq = _criar_eq(cliente, adm)
    assert cliente.delete(f"{C}/{cat['id_categoria']}", headers=adm).status_code in (404, 405)
    assert cliente.delete(f"{E}/{eq['id_equipamento']}", headers=adm).status_code in (404, 405)
    assert cliente.get(f"{C}/{cat['id_categoria']}", headers=adm).status_code == 200


# ------------------------------------------------------------------ UC07: criar equipamento
def test_criar_equipamento_201_padrao_recebido_ativo(cliente, adm):
    # UC07 fluxo principal, RF11, RN08
    corpo = _corpo_eq()
    r = cliente.post(E, json=corpo, headers=adm)
    assert r.status_code == 201, r.text
    d = r.json()
    assert set(d) == {"id_equipamento", "identificacao", "id_categoria", "nome_categoria", "categoria_ativa", "modelo",
                      "condicao", "origem", "situacao", "data_recebimento", "valor", "id_item_solicitacao", "ativo",
                      "doacao", "imagem", "imagem_url"}  # DP-87/DP-90
    assert d["situacao"] == "Recebido" and d["ativo"] is True and d["doacao"] is None and d["categoria_ativa"] is True
    assert d["nome_categoria"] == "Notebooks" and d["valor"] == 1500.0 and d["id_item_solicitacao"] is None
    for k in ("identificacao", "modelo", "condicao", "origem", "data_recebimento", "id_categoria"):
        assert d[k] == corpo[k]
    assert cliente.get(f"{E}/{d['id_equipamento']}", headers=adm).json() == d
    linha = _consulta(cliente, "SELECT ativo, situacao FROM EQUIPAMENTO WHERE id_equipamento=?", (d["id_equipamento"],))[0]
    assert tuple(linha) == (1, "Recebido")


def test_criar_equipamento_sem_valor_e_com_situacao_explicita(cliente, adm):
    # UC07 passo 3: valor opcional; situacao opcional
    corpo = _corpo_eq(situacao="Em avaliação")
    corpo.pop("valor")
    d = cliente.post(E, json=corpo, headers=adm).json()
    assert d["valor"] is None and d["situacao"] == "Em avaliação"


def test_criar_equipamento_trim_nas_pontas(cliente, adm):
    # UC07 FE1, RNF04
    d = _criar_eq(cliente, adm, identificacao="  AB-1  ", modelo="  M  ", origem="  O  ")
    assert (d["identificacao"], d["modelo"], d["origem"]) == ("AB-1", "M", "O")


@pytest.mark.parametrize("cond", CONDICOES)
def test_criar_aceita_as_cinco_condicoes(cliente, adm, cond):
    # UC07 passo 3, RF11 (M3), DP-32
    assert _criar_eq(cliente, adm, condicao=cond, valor=None)["condicao"] == cond


@pytest.mark.parametrize("cond", ["Excelente", "bom", "", "sem condicoes de reuso", None])
def test_criar_condicao_fora_da_lista_400(cliente, adm, cond):
    # UC07 FE1, DP-32
    c = _erro(cliente.post(E, json=_corpo_eq(condicao=cond), headers=adm), 400, "DADOS_INVALIDOS")
    assert "condicao" in c["campos"]


@pytest.mark.parametrize("campo", ["identificacao", "id_categoria", "modelo", "condicao", "origem", "data_recebimento"])
def test_criar_campo_obrigatorio_ausente_400_aponta_o_campo(cliente, adm, campo):
    # UC07 FE1, RNF04
    corpo = _corpo_eq()
    corpo.pop(campo)
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(cliente.post(E, json=corpo, headers=adm), 400, "DADOS_INVALIDOS")
    assert campo in c["campos"]
    assert _tab(cliente, "EQUIPAMENTO") == antes


@pytest.mark.parametrize("campo,valor", [
    ("identificacao", ""), ("identificacao", "   "), ("identificacao", "x" * 51),
    ("modelo", ""), ("modelo", "x" * 151), ("origem", ""), ("origem", "   "), ("origem", "x" * 101),
    ("id_categoria", "abc"), ("id_item_solicitacao", "abc"),
])
def test_criar_campos_texto_invalidos_400(cliente, adm, campo, valor):
    # UC07 FE1, DP-33, DP-34, RNF04
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(cliente.post(E, json=_corpo_eq(**{campo: valor}), headers=adm), 400, "DADOS_INVALIDOS")
    assert campo in c["campos"]
    assert _tab(cliente, "EQUIPAMENTO") == antes


def test_criar_limites_maximos_aceitos(cliente, adm):
    # DP-33, DP-34: 50 / 150 / 100
    d = _criar_eq(cliente, adm, identificacao="i" * 50, modelo="m" * 150, origem="o" * 100)
    assert len(d["identificacao"]) == 50 and len(d["modelo"]) == 150 and len(d["origem"]) == 100


@pytest.mark.parametrize("data", ["2026-13-01", "2026-02-30", "01/01/2026", "20260101", "ontem", "", "2026-1-1"])
def test_criar_data_recebimento_formato_invalido_400(cliente, adm, data):
    # UC07 FE1, DP-34 (ISO estrita)
    c = _erro(cliente.post(E, json=_corpo_eq(data_recebimento=data), headers=adm), 400, "DADOS_INVALIDOS")
    assert "data_recebimento" in c["campos"]


def test_criar_data_recebimento_futura_400_e_hoje_aceito(cliente, adm):
    # UC07 FE1, RF11 (M3): data nao futura
    amanha = (HOJE + timedelta(days=1)).isoformat()
    c = _erro(cliente.post(E, json=_corpo_eq(data_recebimento=amanha), headers=adm), 400, "DADOS_INVALIDOS")
    assert "data_recebimento" in c["campos"]
    assert _criar_eq(cliente, adm, data_recebimento=HOJE.isoformat())["data_recebimento"] == HOJE.isoformat()


@pytest.mark.parametrize("valor", [-1, -0.01, 1.001, 10.555, "abc", True])
def test_criar_valor_invalido_400(cliente, adm, valor):
    # UC07 FE1, RF11 (M3), DP-34: >= 0 e ate 2 casas
    c = _erro(cliente.post(E, json=_corpo_eq(valor=valor), headers=adm), 400, "DADOS_INVALIDOS")
    assert "valor" in c["campos"]


@pytest.mark.parametrize("valor", [0, 0.0, 0.01, 10, 1500.5, 999999.99])
def test_criar_valor_valido_aceito(cliente, adm, valor):
    # UC07 passo 3, DP-34: zero permitido no cadastro
    assert _criar_eq(cliente, adm, valor=valor)["valor"] == float(valor)


def test_criar_categoria_inexistente_ou_inativa_422(cliente, adm):
    # UC07 FE1, RN08, RF08
    c = _erro(cliente.post(E, json=_corpo_eq(id_categoria=9999), headers=adm), 422, "CATEGORIA_INVALIDA")
    assert "id_categoria" in c["campos"]
    cat = _criar_cat(cliente, adm, "Servidores")
    cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": False}, headers=adm)
    antes = _tab(cliente, "EQUIPAMENTO")
    _erro(cliente.post(E, json=_corpo_eq(id_categoria=cat["id_categoria"]), headers=adm), 422, "CATEGORIA_INVALIDA")
    assert _tab(cliente, "EQUIPAMENTO") == antes


def test_categoria_reativada_volta_a_ser_selecionavel(cliente, adm):
    # UC05 FA2, RN07, RN08
    cat = _criar_cat(cliente, adm, "Servidores")
    cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": False}, headers=adm)
    cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": True}, headers=adm)
    assert _criar_eq(cliente, adm, id_categoria=cat["id_categoria"])["categoria_ativa"] is True


@pytest.mark.parametrize("ident", ["NB-0001", "nb-0001", "Nb-0001", " NB-0001 "])
def test_identificacao_duplicada_sem_diferenciar_caixa_409(cliente, adm, ident):
    # UC07 FE1, RF11 (M3), DP-34
    _criar_eq(cliente, adm, identificacao="NB-0001")
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(cliente.post(E, json=_corpo_eq(identificacao=ident), headers=adm), 409, "IDENTIFICACAO_DUPLICADA")
    assert c["campos"] == {"identificacao": "duplicada"}
    assert _tab(cliente, "EQUIPAMENTO") == antes


def test_item_solicitacao_inexistente_422_e_existente_aceito(cliente, adm):
    # UC07 passo 4, DP-33
    c = _erro(cliente.post(E, json=_corpo_eq(id_item_solicitacao=777), headers=adm), 422, "ITEM_SOLICITACAO_INVALIDO")
    assert "id_item_solicitacao" in c["campos"]
    _sql(cliente, "INSERT INTO SOLICITACAO (id_solicitacao, id_organizacao_doadora, data_solicitacao, situacao)"
                  " VALUES (1, 3, '2026-01-01', 'Registrada')")
    _sql(cliente, "INSERT INTO ITEM_SOLICITACAO (id_item_solicitacao, id_solicitacao, tipo, modelo, quantidade)"
                  " VALUES (5, 1, 'Notebook', 'X', 1)")
    d = _criar_eq(cliente, adm, id_item_solicitacao=5)
    assert d["id_item_solicitacao"] == 5


def test_ordem_de_validacao_na_criacao_categoria_antes_de_item_antes_de_identificacao(cliente, adm):
    # contrato POST /equipamentos: 400 -> CATEGORIA_INVALIDA -> ITEM_SOLICITACAO_INVALIDO -> 409 -> situacao
    _criar_eq(cliente, adm, identificacao="DUP")
    _erro(cliente.post(E, json=_corpo_eq(identificacao="DUP", id_categoria=9999, id_item_solicitacao=777), headers=adm),
          422, "CATEGORIA_INVALIDA")
    _erro(cliente.post(E, json=_corpo_eq(identificacao="DUP", id_item_solicitacao=777), headers=adm),
          422, "ITEM_SOLICITACAO_INVALIDO")
    _erro(cliente.post(E, json=_corpo_eq(identificacao="DUP", situacao="Vendido"), headers=adm),
          409, "IDENTIFICACAO_DUPLICADA")


@pytest.mark.parametrize("sit", ["Vendido", "Doado"])
def test_criar_com_vendido_ou_doado_422_transicao_invalida(cliente, adm, sit):
    # UC07 passo 3, DP-35: Vendido e Doado nao sao aceitos na criacao
    antes = _tab(cliente, "EQUIPAMENTO")
    _erro(cliente.post(E, json=_corpo_eq(situacao=sit), headers=adm), 422, "TRANSICAO_INVALIDA")
    assert _tab(cliente, "EQUIPAMENTO") == antes


def test_criar_situacao_fora_da_lista_400(cliente, adm):
    # RF12, RNF04
    c = _erro(cliente.post(E, json=_corpo_eq(situacao="Inexistente"), headers=adm), 400, "DADOS_INVALIDOS")
    assert "situacao" in c["campos"]


@pytest.mark.parametrize("sit", ["Recebido", "Em avaliação", "Em manutenção", "Recondicionado", "Destinado à reciclagem"])
def test_criar_com_situacoes_permitidas(cliente, adm, sit):
    # UC07, RF12, DP-35
    assert _criar_eq(cliente, adm, situacao=sit)["situacao"] == sit


@pytest.mark.parametrize("sit", ["Disponível", "Recondicionado", "Em manutenção"])
def test_criar_sem_reuso_so_aceita_recebido_avaliacao_ou_reciclagem(cliente, adm, sit):
    # UC07 FE3, UC08 FE2, RN11, RN12
    antes = _tab(cliente, "EQUIPAMENTO")
    _erro(cliente.post(E, json=_corpo_eq(condicao="Sem condições de reuso", situacao=sit), headers=adm), 422,
          "SEM_CONDICOES_DE_REUSO")
    assert _tab(cliente, "EQUIPAMENTO") == antes


@pytest.mark.parametrize("sit", ["Recebido", "Em avaliação", "Destinado à reciclagem"])
def test_criar_sem_reuso_com_situacoes_permitidas(cliente, adm, sit):
    # UC07 FE3, RN12
    assert _criar_eq(cliente, adm, condicao="Sem condições de reuso", situacao=sit)["situacao"] == sit


def test_criar_disponivel_exige_condicao_avaliada_e_valor_positivo(cliente, adm):
    # RF12 (M3), DP-35
    c = _erro(cliente.post(E, json=_corpo_eq(condicao="A avaliar", situacao="Disponível"), headers=adm), 422,
              "TRANSICAO_INVALIDA")
    assert "condicao" in c["campos"]
    for v in (None, 0):
        c = _erro(cliente.post(E, json=_corpo_eq(valor=v, situacao="Disponível"), headers=adm), 422, "TRANSICAO_INVALIDA")
        assert "valor" in c["campos"]
    assert _criar_eq(cliente, adm, situacao="Disponível")["situacao"] == "Disponível"


# ------------------------------------------------------------------ UC07 FA1: consultar / listar / alterar
def test_obter_equipamento_inexistente_404(cliente, adm):
    # UC07 FA1
    _erro(cliente.get(f"{E}/9999", headers=adm), 404, "NAO_ENCONTRADO")


def test_listar_equipamentos_formato_e_ordem(cliente, adm):
    # UC07 FA1, contrato: data_recebimento desc, depois identificacao
    _criar_eq(cliente, adm, identificacao="B", data_recebimento="2026-01-01")
    _criar_eq(cliente, adm, identificacao="A", data_recebimento="2026-01-01")
    _criar_eq(cliente, adm, identificacao="C", data_recebimento="2026-03-01")
    r = cliente.get(E, headers=adm).json()
    assert set(r) == {"items", "total", "page", "size"} and r["total"] == 3
    assert [x["identificacao"] for x in r["items"]] == ["C", "A", "B"]


def test_listar_equipamentos_paginacao(cliente, adm):
    # UC07 FA1, convencoes
    for _ in range(5):
        _criar_eq(cliente, adm)
    r = cliente.get(E, params={"page": 2, "size": 2}, headers=adm).json()
    assert len(r["items"]) == 2 and r["page"] == 2 and r["size"] == 2 and r["total"] == 5


@pytest.mark.parametrize("params", [{"page": 0}, {"size": 101}, {"ativo": "x"}, {"situacao": "Inexistente"},
                                    {"condicao": "Ruim"}, {"data_recebimento_de": "01/01/2026"}, {"id_categoria": "a"}])
def test_listar_equipamentos_parametros_invalidos_400(cliente, adm, params):
    # RNF04
    _erro(cliente.get(E, params=params, headers=adm), 400, "DADOS_INVALIDOS")


def test_listar_equipamentos_filtros(cliente, adm):
    # UC07 FA1: id_categoria, situacao, condicao, ativo, q, periodo
    a = _criar_eq(cliente, adm, identificacao="NB-1", modelo="Dell XPS", id_categoria=2, data_recebimento="2026-01-10")
    b = _criar_eq(cliente, adm, identificacao="MN-1", modelo="LG 24", id_categoria=3, condicao="Regular",
                  data_recebimento="2026-02-10", situacao="Em avaliação")
    c = _criar_eq(cliente, adm, identificacao="MN-2", modelo="Samsung", id_categoria=3, data_recebimento="2026-03-10")
    cliente.patch(f"{E}/{c['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)

    def ids(**p):
        return sorted(x["id_equipamento"] for x in cliente.get(E, params=p, headers=adm).json()["items"])
    assert ids(id_categoria=3) == sorted([b["id_equipamento"], c["id_equipamento"]])
    assert ids(situacao="Em avaliação") == [b["id_equipamento"]]
    assert ids(condicao="Regular") == [b["id_equipamento"]]
    assert ids(ativo="false") == [c["id_equipamento"]]
    assert ids(ativo="true") == sorted([a["id_equipamento"], b["id_equipamento"]])
    assert ids(q="nb-1") == [a["id_equipamento"]]
    assert ids(q="XPS") == [a["id_equipamento"]]
    assert ids(q="%") == []
    assert ids(data_recebimento_de="2026-02-10") == sorted([b["id_equipamento"], c["id_equipamento"]])
    assert ids(data_recebimento_ate="2026-02-10") == sorted([a["id_equipamento"], b["id_equipamento"]])
    assert ids(data_recebimento_de="2026-02-10", data_recebimento_ate="2026-02-10") == [b["id_equipamento"]]


def _put_corpo(eq, **kw):
    base = {k: eq[k] for k in ("identificacao", "id_categoria", "modelo", "condicao", "origem", "data_recebimento",
                               "valor", "id_item_solicitacao")}
    base.update(kw)
    return base


def test_alterar_equipamento_200_nao_muda_situacao_nem_ativo(cliente, adm):
    # UC07 FA1
    eq = _criar_eq(cliente, adm)
    cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    corpo = _put_corpo(eq, modelo="Novo modelo", valor=2000.5, origem="Outra") | {"situacao": "Doado", "ativo": True}
    r = cliente.put(f"{E}/{eq['id_equipamento']}", json=corpo, headers=adm)
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["modelo"] == "Novo modelo" and d["valor"] == 2000.5 and d["origem"] == "Outra"
    assert d["situacao"] == "Recebido" and d["ativo"] is False


def test_alterar_equipamento_inexistente_404_e_invalido_400(cliente, adm):
    # UC07 FA1, FE1; ordem 400 -> 404
    eq = _criar_eq(cliente, adm)
    _erro(cliente.put(f"{E}/9999", json=_put_corpo(eq), headers=adm), 404, "NAO_ENCONTRADO")
    _erro(cliente.put(f"{E}/9999", json=_put_corpo(eq, modelo=""), headers=adm), 400, "DADOS_INVALIDOS")
    c = _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, valor=-1), headers=adm), 400, "DADOS_INVALIDOS")
    assert "valor" in c["campos"]


def test_alterar_identificacao_para_a_propria_com_outra_caixa_200(cliente, adm):
    # UC07 FA1: a identificacao e revalidada excluindo o proprio registro
    eq = _criar_eq(cliente, adm, identificacao="Ab-1")
    r = cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, identificacao="AB-1"), headers=adm)
    assert r.status_code == 200 and r.json()["identificacao"] == "AB-1"


def test_alterar_para_identificacao_de_outro_409(cliente, adm):
    # UC07 FE1, RF11 (M3)
    _criar_eq(cliente, adm, identificacao="UM")
    dois = _criar_eq(cliente, adm, identificacao="DOIS")
    _erro(cliente.put(f"{E}/{dois['id_equipamento']}", json=_put_corpo(dois, identificacao="um"), headers=adm),
          409, "IDENTIFICACAO_DUPLICADA")
    assert cliente.get(f"{E}/{dois['id_equipamento']}", headers=adm).json()["identificacao"] == "DOIS"


def test_alterar_categoria_para_inativa_422_e_manter_a_inativa_vinculada_200(cliente, adm):
    # UC07 FA1, RN08: so valida ATIVA quando a categoria muda
    cat = _criar_cat(cliente, adm, "Servidores")
    eq = _criar_eq(cliente, adm, id_categoria=cat["id_categoria"])
    cliente.patch(f"{C}/{cat['id_categoria']}/situacao", json={"ativa": False}, headers=adm)
    r = cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, modelo="Alterado"), headers=adm)
    assert r.status_code == 200 and r.json()["id_categoria"] == cat["id_categoria"] and r.json()["categoria_ativa"] is False
    outro = _criar_eq(cliente, adm)
    _erro(cliente.put(f"{E}/{outro['id_equipamento']}", json=_put_corpo(outro, id_categoria=cat["id_categoria"]),
                      headers=adm), 422, "CATEGORIA_INVALIDA")
    # trocar de categoria inativa para ativa e permitido
    r = cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, id_categoria=1), headers=adm)
    assert r.status_code == 200 and r.json()["id_categoria"] == 1


def test_alterar_item_solicitacao_inexistente_422(cliente, adm):
    # UC07 passo 4, DP-33
    eq = _criar_eq(cliente, adm)
    _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, id_item_solicitacao=999), headers=adm),
          422, "ITEM_SOLICITACAO_INVALIDO")


def test_alterar_condicao_para_sem_reuso_conforme_situacao(cliente, adm):
    # UC07 FE3, RN12, contrato PUT
    ok = _criar_eq(cliente, adm, situacao="Em avaliação")
    assert cliente.put(f"{E}/{ok['id_equipamento']}", json=_put_corpo(ok, condicao="Sem condições de reuso"),
                       headers=adm).status_code == 200
    em_man = _criar_eq(cliente, adm, situacao="Em manutenção")
    antes = _tab(cliente, "EQUIPAMENTO")
    _erro(cliente.put(f"{E}/{em_man['id_equipamento']}", json=_put_corpo(em_man, condicao="Sem condições de reuso"),
                      headers=adm), 422, "SEM_CONDICOES_DE_REUSO")
    assert _tab(cliente, "EQUIPAMENTO") == antes


def test_alterar_disponivel_exige_valor_positivo_e_condicao_apta(cliente, adm):
    # RF12 (M3), contrato PUT: 'Se o equipamento esta Disponivel, valor deve continuar > 0 e a condicao apta'
    eq = _disponivel(cliente, adm)
    c = _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, valor=0), headers=adm), 422, "TRANSICAO_INVALIDA")
    assert "valor" in c["campos"]
    _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, valor=None), headers=adm), 422, "TRANSICAO_INVALIDA")
    _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, condicao="A avaliar"), headers=adm), 422,
          "TRANSICAO_INVALIDA")
    _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, condicao="Sem condições de reuso"), headers=adm),
          422, "SEM_CONDICOES_DE_REUSO")
    assert cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()["valor"] == 1500.0


def test_alterar_vendido_ou_doado_422_finalizado_e_nada_muda(cliente, adm):
    # UC07 FE2 (M3), RF12 (M3), RN14: somente leitura
    for sit in ("Vendido", "Doado"):
        eq = _criar_eq(cliente, adm)
        _forcar_situacao(cliente, eq["id_equipamento"], sit)
        antes = _tab(cliente, "EQUIPAMENTO")
        _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, modelo="X"), headers=adm), 422,
              "EQUIPAMENTO_FINALIZADO")
        _erro(cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm), 422,
              "EQUIPAMENTO_FINALIZADO")
        assert _tab(cliente, "EQUIPAMENTO") == antes


def test_alterar_reciclagem_ainda_permite_editar_dados(cliente, adm):
    # UC07 FA1: so Vendido/Doado sao somente leitura
    eq = _criar_eq(cliente, adm, situacao="Destinado à reciclagem")
    assert cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, modelo="Corrigido"), headers=adm).status_code == 200


# ------------------------------------------------------------------ UC07 FA2: desativar / reativar equipamento
def test_desativar_e_reativar_equipamento_preserva_historico(cliente, adm):
    # UC07 FA2 (M3), DP-30 opcao A
    eq = _criar_eq(cliente, adm)
    r = cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    assert r.status_code == 200 and r.json()["ativo"] is False
    assert _consulta(cliente, "SELECT ativo FROM EQUIPAMENTO WHERE id_equipamento=?", (eq["id_equipamento"],))[0][0] == 0
    assert cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()["identificacao"] == eq["identificacao"]
    r = cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": True}, headers=adm)
    assert r.status_code == 200 and r.json()["ativo"] is True


def test_ativo_equipamento_idempotente_invalido_e_inexistente(cliente, adm):
    # UC07 FA2, RNF04
    eq = _criar_eq(cliente, adm)
    for _ in range(2):
        assert cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm).status_code == 200
    _erro(cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": "x"}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(cliente.patch(f"{E}/9999/ativo", json={"ativo": False}, headers=adm), 404, "NAO_ENCONTRADO")


def test_equipamento_inativo_continua_consultavel_e_editavel(cliente, adm):
    # UC07 FA2, contrato (equipamento inativo)
    eq = _criar_eq(cliente, adm)
    cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    assert cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).status_code == 200
    assert cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, modelo="Ainda edita"), headers=adm).status_code == 200


def test_inativo_nao_pode_ficar_disponivel_422_equipamento_inativo(cliente, adm):
    # UC07 FA2, UC08 FE3, RN12 (M3), RN13
    eq = _criar_eq(cliente, adm)
    cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], "Disponível"), 422, "EQUIPAMENTO_INATIVO")
    assert "ativo" in c["campos"]
    assert _tab(cliente, "EQUIPAMENTO") == antes
    cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": True}, headers=adm)
    assert _sit(cliente, adm, eq["id_equipamento"], "Disponível").status_code == 200


def test_inativo_nao_pode_ser_doado_e_nenhuma_doacao_gravada(cliente, adm):
    # UC07 FA2, RN12 (M3)
    eq = _criar_eq(cliente, adm)
    cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    _erro(_sit(cliente, adm, eq["id_equipamento"], "Doado", id_organizacao_ong=ONG_ATIVA, data_doacao=HOJE.isoformat()),
          422, "EQUIPAMENTO_INATIVO")
    assert _tab(cliente, "DOACAO") == []


def test_inativo_pode_receber_situacoes_de_processamento(cliente, adm):
    # UC08 FA1, contrato: so Disponivel e Doado sao bloqueados
    eq = _criar_eq(cliente, adm)
    cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm)
    for s in ("Em manutenção", "Recondicionado", "Destinado à reciclagem"):
        assert _sit(cliente, adm, eq["id_equipamento"], s).status_code == 200


# ------------------------------------------------------------------ UC08: situacao (RF12, RN12, DP-35)
def test_atualizar_situacao_200_e_persiste(cliente, adm):
    # UC08 fluxo principal, RF12
    eq = _criar_eq(cliente, adm)
    r = _sit(cliente, adm, eq["id_equipamento"], "Em avaliação")
    assert r.status_code == 200 and r.json()["situacao"] == "Em avaliação" and r.json()["doacao"] is None
    assert cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()["situacao"] == "Em avaliação"


@pytest.mark.parametrize("sit", ["Em avaliação", "Em manutenção", "Recondicionado", "Disponível", "Destinado à reciclagem"])
def test_situacoes_permitidas_entre_nao_finais(cliente, adm, sit):
    # UC08 passo 3, FA1, DP-35: demais mudancas sao livres
    eq = _criar_eq(cliente, adm)
    assert _sit(cliente, adm, eq["id_equipamento"], sit).json()["situacao"] == sit


def test_voltar_de_disponivel_para_avaliacao_e_livre(cliente, adm):
    # UC08 FA1, DP-35
    eq = _disponivel(cliente, adm)
    assert _sit(cliente, adm, eq["id_equipamento"], "Em manutenção").status_code == 200
    assert _sit(cliente, adm, eq["id_equipamento"], "Recebido").status_code == 200


def test_vendido_nao_e_definido_pela_api_422(cliente, adm):
    # UC08 passo 3 (M3), RN14, DP-35
    eq = _criar_eq(cliente, adm)
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], "Vendido"), 422, "TRANSICAO_INVALIDA")
    assert "situacao" in c["campos"]
    assert _tab(cliente, "EQUIPAMENTO") == antes


def test_situacao_invalida_400_inexistente_404(cliente, adm):
    # UC08, RNF04
    eq = _criar_eq(cliente, adm)
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], "Inexistente"), 400, "DADOS_INVALIDOS")
    assert "situacao" in c["campos"]
    _erro(cliente.patch(f"{E}/{eq['id_equipamento']}/situacao", json={}, headers=adm), 400, "DADOS_INVALIDOS")
    _erro(_sit(cliente, adm, 9999, "Recebido"), 404, "NAO_ENCONTRADO")
    _erro(_sit(cliente, adm, 9999, "Inexistente"), 400, "DADOS_INVALIDOS")  # 400 antes de 404


def test_situacao_idempotente_quando_igual_a_atual_e_nao_final(cliente, adm):
    # contrato PATCH situacao: idempotente (200)
    eq = _criar_eq(cliente, adm)
    r = _sit(cliente, adm, eq["id_equipamento"], "Recebido")
    assert r.status_code == 200 and r.json()["situacao"] == "Recebido"


@pytest.mark.parametrize("final", ["Destinado à reciclagem", "Doado", "Vendido"])
@pytest.mark.parametrize("nova", ["Recebido", "Disponível", "Em avaliação"])
def test_situacao_final_nao_muda_mais_422(cliente, adm, final, nova):
    # UC08 FE3 (M3), RF12 (M3), DP-35
    eq = _criar_eq(cliente, adm)
    _forcar_situacao(cliente, eq["id_equipamento"], final)
    antes = _tab(cliente, "EQUIPAMENTO")
    r = _sit(cliente, adm, eq["id_equipamento"], nova)
    assert r.status_code == 422
    assert r.json()["codigo"] in ("TRANSICAO_INVALIDA", "EQUIPAMENTO_FINALIZADO")
    if final == "Destinado à reciclagem":
        assert r.json()["codigo"] == "TRANSICAO_INVALIDA"
    assert _tab(cliente, "EQUIPAMENTO") == antes


def test_final_repetir_a_mesma_situacao_final_tambem_422(cliente, adm):
    # contrato: idempotente so quando nao e final
    eq = _criar_eq(cliente, adm, situacao="Destinado à reciclagem")
    _erro(_sit(cliente, adm, eq["id_equipamento"], "Destinado à reciclagem"), 422, "TRANSICAO_INVALIDA")


@pytest.mark.parametrize("sit", ["Em manutenção", "Recondicionado", "Disponível", "Doado"])
def test_sem_condicoes_de_reuso_bloqueia_situacoes_422(cliente, adm, sit):
    # UC08 FE2, UC11 FE2, RN11, RN12
    eq = _criar_eq(cliente, adm, condicao="Sem condições de reuso", valor=100)
    extra = {"id_organizacao_ong": ONG_ATIVA, "data_doacao": HOJE.isoformat()} if sit == "Doado" else {}
    antes = _tab(cliente, "EQUIPAMENTO")
    _erro(_sit(cliente, adm, eq["id_equipamento"], sit, **extra), 422, "SEM_CONDICOES_DE_REUSO")
    assert _tab(cliente, "EQUIPAMENTO") == antes and _tab(cliente, "DOACAO") == []


@pytest.mark.parametrize("sit", ["Em avaliação", "Destinado à reciclagem"])
def test_sem_condicoes_de_reuso_permite_avaliacao_e_reciclagem(cliente, adm, sit):
    # UC08 FE2, RN12
    eq = _criar_eq(cliente, adm, condicao="Sem condições de reuso")
    assert _sit(cliente, adm, eq["id_equipamento"], sit).status_code == 200


def test_apenas_sem_reuso_impede_venda_ou_doacao_outras_condicoes_ok(cliente, adm):
    # RN11 (M3): somente a condicao Sem condicoes de reuso impede
    for cond in ("Bom", "Regular", "Necessita reparo"):
        eq = _criar_eq(cliente, adm, condicao=cond)
        assert _sit(cliente, adm, eq["id_equipamento"], "Disponível").status_code == 200, cond


def test_disponivel_exige_condicao_avaliada_422(cliente, adm):
    # RF12 (M3), DP-35
    eq = _criar_eq(cliente, adm, condicao="A avaliar")
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], "Disponível"), 422, "TRANSICAO_INVALIDA")
    assert "condicao" in c["campos"]


@pytest.mark.parametrize("valor", [None, 0])
def test_disponivel_exige_valor_maior_que_zero_422(cliente, adm, valor):
    # RF12 (M3), DP-35
    eq = _criar_eq(cliente, adm, valor=valor)
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], "Disponível"), 422, "TRANSICAO_INVALIDA")
    assert "valor" in c["campos"]


def test_disponivel_indica_tudo_o_que_falta(cliente, adm):
    # contrato: TRANSICAO_INVALIDA com campos indicando o que falta
    eq = _criar_eq(cliente, adm, condicao="A avaliar", valor=None)
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], "Disponível"), 422, "TRANSICAO_INVALIDA")
    assert {"condicao", "valor"} <= set(c["campos"])


# ------------------------------------------------------------------ UC08 passo 4 / DP-36: doacao
def _doar(cliente, h, id_eq, ong=ONG_ATIVA, data=None):
    return _sit(cliente, h, id_eq, "Doado", id_organizacao_ong=ong, data_doacao=data or HOJE.isoformat())


def test_doar_grava_doacao_na_mesma_operacao_200(cliente, adm):
    # UC08 passo 4, UC11, RN12, DP-36
    eq = _criar_eq(cliente, adm)
    r = _doar(cliente, adm, eq["id_equipamento"], data=HOJE.isoformat())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["situacao"] == "Doado"
    assert d["doacao"]["id_organizacao_ong"] == ONG_ATIVA and d["doacao"]["nome_ong"] == "ONG Cliente"
    assert d["doacao"]["data_doacao"] == HOJE.isoformat() and isinstance(d["doacao"]["id_doacao"], int)
    assert set(d["doacao"]) == {"id_doacao", "id_organizacao_ong", "nome_ong", "data_doacao"}
    linhas = _consulta(cliente, "SELECT id_equipamento, id_organizacao_ong, data_doacao FROM DOACAO")
    assert [tuple(x) for x in linhas] == [(eq["id_equipamento"], ONG_ATIVA, HOJE.isoformat())]
    assert cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()["doacao"] == d["doacao"]


def test_doar_com_data_igual_ao_recebimento_aceito(cliente, adm):
    # RN12 (M3): nao anterior ao recebimento (igual vale)
    eq = _criar_eq(cliente, adm, data_recebimento="2026-02-01")
    assert _doar(cliente, adm, eq["id_equipamento"], data="2026-02-01").status_code == 200


def test_doar_depois_equipamento_fica_finalizado_e_nao_edita(cliente, adm):
    # RF12 (M3): doado nao pode mais ser alterado
    eq = _criar_eq(cliente, adm)
    _doar(cliente, adm, eq["id_equipamento"])
    _erro(_sit(cliente, adm, eq["id_equipamento"], "Recebido"), 422, "EQUIPAMENTO_FINALIZADO")
    _erro(cliente.put(f"{E}/{eq['id_equipamento']}", json=_put_corpo(eq, modelo="X"), headers=adm), 422,
          "EQUIPAMENTO_FINALIZADO")
    assert len(_tab(cliente, "DOACAO")) == 1


@pytest.mark.parametrize("extra,campo", [
    ({}, "id_organizacao_ong"),
    ({"id_organizacao_ong": ONG_ATIVA}, "data_doacao"),
    ({"data_doacao": "2026-01-01"}, "id_organizacao_ong"),
])
def test_doado_sem_ong_ou_data_400_e_nada_muda(cliente, adm, extra, campo):
    # UC08 FE1, RN12: sem ONG e data a situacao doado nao e registrada
    eq = _criar_eq(cliente, adm)
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], "Doado", **extra), 400, "DADOS_INVALIDOS")
    assert campo in c["campos"]
    assert _tab(cliente, "EQUIPAMENTO") == antes and _tab(cliente, "DOACAO") == []


@pytest.mark.parametrize("sit", ["Em avaliação", "Disponível", "Destinado à reciclagem"])
def test_campos_de_doacao_com_outra_situacao_400(cliente, adm, sit):
    # contrato PATCH situacao: ausentes quando nao e Doado
    eq = _criar_eq(cliente, adm)
    c = _erro(_sit(cliente, adm, eq["id_equipamento"], sit, id_organizacao_ong=ONG_ATIVA,
                   data_doacao=HOJE.isoformat()), 400, "DADOS_INVALIDOS")
    assert {"id_organizacao_ong", "data_doacao"} <= set(c["campos"])
    assert _tab(cliente, "DOACAO") == []


@pytest.mark.parametrize("data", ["2026-13-40", "01/01/2026", "hoje"])
def test_data_doacao_formato_invalido_400(cliente, adm, data):
    # UC08 FE1, RNF04
    eq = _criar_eq(cliente, adm)
    c = _erro(_doar(cliente, adm, eq["id_equipamento"], data=data), 400, "DADOS_INVALIDOS")
    assert "data_doacao" in c["campos"]


def test_doacao_data_futura_422(cliente, adm):
    # UC08 passo 4 (M3), RN12 (M3)
    eq = _criar_eq(cliente, adm)
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(_doar(cliente, adm, eq["id_equipamento"], data=(HOJE + timedelta(days=1)).isoformat()), 422, "DOACAO_INVALIDA")
    assert "data_doacao" in c["campos"]
    assert _tab(cliente, "EQUIPAMENTO") == antes and _tab(cliente, "DOACAO") == []


def test_doacao_data_anterior_ao_recebimento_422(cliente, adm):
    # UC08 passo 4 (M3), RN12 (M3)
    eq = _criar_eq(cliente, adm, data_recebimento="2026-02-01")
    c = _erro(_doar(cliente, adm, eq["id_equipamento"], data="2026-01-31"), 422, "DOACAO_INVALIDA")
    assert "data_doacao" in c["campos"]
    assert _tab(cliente, "DOACAO") == []


@pytest.mark.parametrize("ong", [9999, 1, 3])
def test_doacao_ong_inexistente_ou_tipo_errado_422(cliente, adm, ong):
    # UC08 passo 4 (M3), RN12 (M3): so Cliente ONG (1 = Cliente Empresa, 3 = Empresa Doadora)
    eq = _criar_eq(cliente, adm)
    antes = _tab(cliente, "EQUIPAMENTO")
    c = _erro(_doar(cliente, adm, eq["id_equipamento"], ong=ong), 422, "DOACAO_INVALIDA")
    assert "id_organizacao_ong" in c["campos"]
    assert _tab(cliente, "EQUIPAMENTO") == antes and _tab(cliente, "DOACAO") == []


def test_doacao_ong_inativa_422(cliente, adm):
    # UC08 passo 4 (M3), RN12 (M3)
    eq = _criar_eq(cliente, adm)
    c = _erro(_doar(cliente, adm, eq["id_equipamento"], ong=_ong_inativa(cliente)), 422, "DOACAO_INVALIDA")
    assert "id_organizacao_ong" in c["campos"]
    assert _tab(cliente, "DOACAO") == []


def test_doado_exige_condicao_avaliada_422(cliente, adm):
    # contrato: 'Doado' exige condicao que permita reuso (mesmos criterios)
    eq = _criar_eq(cliente, adm, condicao="A avaliar")
    _erro(_doar(cliente, adm, eq["id_equipamento"]), 422, "TRANSICAO_INVALIDA")
    assert _tab(cliente, "DOACAO") == []


def test_doacao_e_a_situacao_na_mesma_transacao_rollback_se_doacao_falha(cliente, adm):
    # DP-36: se a gravacao da DOACAO falhar, a situacao nao muda (mesma transacao)
    eq = _criar_eq(cliente, adm)
    _sql(cliente, "INSERT INTO DOACAO (id_equipamento, id_organizacao_ong, data_doacao) VALUES (?,?,?)",
         (eq["id_equipamento"], ONG_ATIVA, "2026-01-01"))  # forca UNIQUE(id_equipamento)
    r = _doar(cliente, adm, eq["id_equipamento"])
    assert r.status_code == 422 and r.json()["codigo"] == "DOACAO_INVALIDA"
    assert cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()["situacao"] == "Recebido"
    assert len(_tab(cliente, "DOACAO")) == 1


def test_ordem_422_finalizado_antes_de_dados_de_doacao(cliente, adm):
    # contrato: 400 -> 404 -> 422 (finalizado, transicao, condicao, ativo, doacao)
    eq = _criar_eq(cliente, adm)
    _forcar_situacao(cliente, eq["id_equipamento"], "Doado")
    _erro(_doar(cliente, adm, eq["id_equipamento"], ong=9999), 422, "EQUIPAMENTO_FINALIZADO")


def test_servico_mudar_situacao_reaproveitavel_com_commit_false(cliente, adm):
    # DP-36, UC10/UC11: a logica e reaproveitavel pelo Modulo 4 (commit=False deixa a transacao com o chamador)
    from app.db import conectar
    from app.equipamentos import service
    eq = _criar_eq(cliente, adm)
    con = conectar()
    try:
        service.mudar_situacao(con, eq["id_equipamento"], "Doado", ONG_ATIVA, HOJE.isoformat(), commit=False)
        con.rollback()
    finally:
        con.close()
    assert cliente.get(f"{E}/{eq['id_equipamento']}", headers=adm).json()["situacao"] == "Recebido"
    assert _tab(cliente, "DOACAO") == []


def test_servico_permitir_vendido_e_o_unico_caminho_para_vendido(cliente, adm):
    # RN14, DP-35: Modulo 5 usa permitir_vendido=True
    from app.db import conectar
    from app.equipamentos import service
    eq = _disponivel(cliente, adm)
    con = conectar()
    try:
        assert service.mudar_situacao(con, eq["id_equipamento"], "Vendido", permitir_vendido=True)["situacao"] == "Vendido"
    finally:
        con.close()
    _erro(cliente.patch(f"{E}/{eq['id_equipamento']}/ativo", json={"ativo": False}, headers=adm), 422,
          "EQUIPAMENTO_FINALIZADO")


# ------------------------------------------------------------------ erros no formato padrao (convencoes)
def test_corpo_json_invalido_400_formato_padrao(cliente, adm):
    # RNF04, convencoes
    r = cliente.post(E, content="{nao e json", headers={**adm, "Content-Type": "application/json"})
    _erro(r, 400, "DADOS_INVALIDOS")


def test_erro_de_validacao_nao_ecoa_valores_enviados(cliente, adm):
    # RNF04
    r = cliente.post(E, json=_corpo_eq(condicao="VALOR-SECRETO-XYZ"), headers=adm)
    assert "VALOR-SECRETO-XYZ" not in r.text


def test_nenhuma_resposta_de_erro_vaza_traceback(cliente, adm):
    # RNF04
    for url in (f"{C}/9999", f"{E}/9999"):
        assert "Traceback" not in cliente.get(url, headers=adm).text


# ------------------------------------------------------------------ robustez: numeros fora da faixa (RNF04)
# Corrigido (RNF04): numeros fora da faixa devolvem 400/404 e nao 500.


def test_id_enorme_na_url_nao_deve_dar_500(cliente, adm):
    # RNF04: id > 2^63 deveria ser 404 ou 400
    r = cliente.get(f"{E}/{10**20}", headers=adm)
    assert r.status_code in (400, 404)


def test_id_categoria_enorme_no_corpo_nao_deve_dar_500(cliente, adm):
    # UC07 FE1, RN08: deveria ser 400 ou 422 CATEGORIA_INVALIDA
    r = cliente.post(E, json=_corpo_eq(id_categoria=10**20), headers=adm)
    assert r.status_code in (400, 422)


def test_valor_enorme_nao_deve_dar_500(cliente, adm):
    # UC07 FE1, DP-34: valor 1e30 deveria ser 400
    r = cliente.post(E, json=_corpo_eq(valor=1e30), headers=adm)
    assert r.status_code == 400


def test_valor_teto_dp39(cliente, adm):
    assert cliente.post(E, json=_corpo_eq(valor=9999999.99), headers=adm).status_code == 201
    assert cliente.post(E, json=_corpo_eq(valor=10000000), headers=adm).status_code == 400


def test_id_organizacao_ong_enorme_nao_deve_dar_500(cliente, adm):
    # UC08 passo 4: deveria ser 400 ou 422 DOACAO_INVALIDA
    eq = _criar_eq(cliente, adm)
    r = _sit(cliente, adm, eq["id_equipamento"], "Doado", id_organizacao_ong=10**20, data_doacao=HOJE.isoformat())
    assert r.status_code in (400, 422)
