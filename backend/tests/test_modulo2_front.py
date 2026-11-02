"""Modulo 2 - front estatico (leitura dos arquivos; nao toca no front). UC01, UC06, UC25;
RF03, RF06, RF09, RF10; RN01, RN03, RN06, RN09, RN10; RNF01, RNF04, RNF05, RNF06; DP-06, DP-25."""
import re
from pathlib import Path

import pytest

from app.permissoes import MATRIZ_FUNCIONALIDADES

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"
JS = FRONT / "js"
CSS = FRONT / "css"
PAG_ORG = FRONT / "app" / "organizacoes" / "index.html"
PAG_PAR = FRONT / "app" / "parceiros" / "index.html"
JS_ORG = JS / "organizacoes.js"
JS_PAR = JS / "parceiros.js"
JS_COMUM = JS / "organizacoes-comum.js"
JS_MODULO = [JS_ORG, JS_PAR, JS_COMUM]
CSS_NOVOS = [CSS / "organizacoes.css"]
PAGINAS = [PAG_ORG, PAG_PAR]


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ existencia
@pytest.mark.parametrize("p", PAGINAS + JS_MODULO + CSS_NOVOS)
def test_telas_scripts_e_css_do_modulo_existem(p):
    # UC01, UC06
    assert p.is_file()


def test_paginas_carregam_scripts_na_ordem():
    # UC01, UC06 (RNF05: guarda de rota via Layout)
    for pag, js in ((PAG_ORG, "organizacoes.js"), (PAG_PAR, "parceiros.js")):
        srcs = re.findall(r'<script[^>]+src="([^"]+)"', ler(pag))
        locais = [s.split("/")[-1] for s in srcs if not s.startswith("http")]
        assert locais == ["api.js", "layout.js", "usuarios-comum.js", "organizacoes-comum.js", js], pag.name


def test_paginas_carregam_a_folha_do_modulo():
    # RNF01
    for pag in PAGINAS:
        assert "organizacoes.css" in ler(pag)


def test_paginas_usam_layout_iniciar_com_a_chave_do_menu():
    # RN01, RNF05
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'organizacoes'", ler(JS_ORG))
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'parceiros'", ler(JS_PAR))


def test_scripts_apontam_para_rotas_do_contrato():
    # UC01, UC06, UC25 (somente via Api)
    o, p = ler(JS_ORG), ler(JS_PAR)
    for rota in ("'/organizacoes?", "'/organizacoes'", "'/organizacoes/' +", "/contato'", "/situacao'"):
        assert rota in o, rota
    for metodo in ("Api.get", "Api.post", "Api.put", "Api.patch"):
        assert metodo in o, metodo
    for rota in ("'/parceiros?", "'/parceiros'", "'/parceiros/' +", "/situacao'", "sem_parceria=true"):
        assert rota in p, rota
    for metodo in ("Api.get", "Api.post", "Api.put", "Api.patch"):
        assert metodo in p, metodo


def test_parceiro_post_envia_id_organizacao_tipo_e_situacao_e_put_so_tipo_parceria():
    # UC06 FA1, DP-27
    p = ler(JS_PAR)
    assert re.search(r"Api\.put\('/parceiros/' \+ [^,]+,\s*\{\s*tipo_parceria:[^,}]+\}\s*\)", p)
    assert re.search(r"Api\.post\('/parceiros',\s*\{[^}]*id_organizacao[^}]*tipo_parceria[^}]*situacao_parceria", p)


# ------------------------------------------------------------------ fetch so em api.js
def test_nenhum_js_alem_de_api_js_usa_fetch():
    # RNF04
    com_fetch = [p.name for p in JS.glob("*.js") if p.name != "api.js" and re.search(r"\bfetch\s*\(", ler(p))]
    assert com_fetch == [], f"fetch fora de api.js: {com_fetch}"


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_sem_fetch_nem_xhr_inline(p):
    sem_externos = re.sub(r"<script[^>]+src=[^>]*>\s*</script>", "", ler(p))
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", sem_externos)


@pytest.mark.parametrize("p", JS_MODULO)
def test_scripts_do_modulo_sem_fetch_nem_url_da_api(p):
    t = ler(p)
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", t)
    assert "/api/v1" not in t


# ------------------------------------------------------------------ menu e matriz
def _item_menu(chave):
    m = re.search(r"\{\s*chave:\s*'" + chave + r"'[^}]*\}", ler(JS / "layout.js"))
    assert m, f"item {chave} ausente do MENU"
    return m.group(0)


@pytest.mark.parametrize("chave,href", [("organizacoes", "organizacoes/index.html"),
                                        ("parceiros", "parceiros/index.html")])
def test_itens_do_menu_ligados_as_paginas(chave, href):
    # UC01, UC06, RN01
    assert f"href: '{href}'" in _item_menu(chave)
    assert (FRONT / "app" / href).is_file()


def test_nenhum_item_do_menu_aponta_para_pagina_inexistente():
    # com o Modulo 5 os itens de loja/vendas/notas ganharam link; todo link precisa de tela, e so Relatorios fica sem
    sem_link = []
    for chave, href in re.findall(r"chave:\s*'(\w+)'[^}]*?href:\s*(null|'[^']+')", ler(JS / "layout.js")):
        if href == "null":
            sem_link.append(chave)
        else:
            assert (FRONT / "app" / href.strip("'")).is_file(), f"{chave} -> {href}"
    assert sem_link == [], sem_link


def test_matriz_de_funcionalidades_paridade_com_menu_do_modulo():
    # RN01, RN03, RF03, RF10: organizacoes = Administrador e Funcionario; parceiros = so Administrador
    quem = lambda chave: {perfil for perfil, itens in MATRIZ_FUNCIONALIDADES.items() if chave in itens}  # noqa: E731
    assert quem("organizacoes") == {"Administrador", "Funcionário"}
    assert quem("parceiros") == {"Administrador"}
    chaves_menu = set(re.findall(r"chave:\s*'(\w+)'", ler(JS / "layout.js")))
    for itens in MATRIZ_FUNCIONALIDADES.values():
        assert set(itens) <= chaves_menu


def test_matriz_do_contrato_do_modulo_0_concorda_com_o_codigo():
    # RN01 (x-matriz-funcionalidades)
    y = (RAIZ / "contratos" / "modulo-0.yaml").read_text(encoding="utf-8")
    bloco = y[y.index("x-matriz-funcionalidades:"):]
    for perfil, itens in MATRIZ_FUNCIONALIDADES.items():
        m = re.search(r"^  " + re.escape(perfil) + r":[^\n]*\n((?:\s+-[^\n]*\n?)+)", bloco, re.M)
        assert m, perfil
        assert re.findall(r"^\s+-\s+(\w+)", m.group(1), re.M) == itens, perfil


def test_pagina_de_parceiros_nao_oferece_acao_ao_funcionario():
    # RN03: o Funcionario nao acessa parceiros (menu + guarda do Layout)
    assert "parceiros" not in MATRIZ_FUNCIONALIDADES["Funcionário"]
    assert "autorizado(usuario, chave)" in ler(JS / "layout.js")


# ------------------------------------------------------------------ exclusao so de organizacao (DP-63)
def test_organizacao_tem_exclusao_com_confirmacao():
    # DP-63, UC01: Excluir (Administrador) ao lado de Desativar, com modal; Api.delete so no clique de confirmar
    h = ler(PAG_ORG)
    assert 'id="modal-excluir"' in h and 'id="btn-confirmar-excluir"' in h and 'id="btn-nao-excluir"' in h
    js = ler(JS_ORG)
    assert 'data-acao="excluir"' in js and js.count("Api.delete(") == 1
    assert "ORGANIZACAO_EM_USO" in js and "ORGANIZACAO_COM_USUARIOS" in js and "excluir_usuarios=true" in js
    abrir = js[js.index("function abrirExclusao"):js.index("btn-confirmar-excluir').addEventListener")]
    assert "Api.delete(" not in abrir


def test_exclusao_lista_usuarios_sem_html_concatenado_e_trata_ultimo_admin():
    js = Path(__file__).resolve().parents[2].joinpath("frontend/js/organizacoes.js").read_text(encoding="utf-8")
    assert "campos.usuarios" in js and "Serão excluídos" in js and "usuário(s):" in js
    assert "createElement('li')" in js and "textContent = u.nome" in js
    assert "ALTERACAO_BLOQUEADA" in js and "único Administrador" in js


def test_parceiros_nao_tem_exclusao():
    # DP-63: a parceria so some junto com a organizacao
    t = re.sub(r"/\*.*?\*/", "", ler(JS_PAR), flags=re.S)
    assert "Api.delete" not in t and not re.search(r"data-acao=.excluir", t)


@pytest.mark.parametrize("p", [JS_ORG, JS_PAR])
def test_acoes_da_tabela_sao_editar_e_desativar_reativar(p):
    # UC01 FA2, UC06 FA2
    acoes = set(re.findall(r'data-acao="(\w+)"', ler(p)))
    assert acoes <= {"editar", "situacao", "ver", "excluir"}, acoes
    assert {"editar", "situacao"} <= acoes
    t = ler(p)
    assert "Desativar" in t and "Reativar" in t


@pytest.mark.parametrize("p", PAGINAS)
def test_modal_de_confirmacao_de_desativacao(p):
    # UC01 FA2, UC06 FA2: confirmacao antes de desativar
    h = ler(p)
    assert 'id="modal-situacao"' in h and 'id="btn-confirmar-situacao"' in h and 'id="btn-nao-situacao"' in h
    assert 'data-bs-dismiss="modal" id="btn-nao-situacao"' in h


@pytest.mark.parametrize("js", [JS_ORG, JS_PAR])
def test_patch_situacao_so_dentro_do_clique_de_confirmacao(js):
    # UC01 FA2, UC06 FA2: o botao da tabela apenas abre o modal
    t = ler(js)
    assert t.count("/situacao'") == 1
    idx = t.index("btn-confirmar-situacao').addEventListener")
    assert "/situacao'" in t[idx:]
    abrir = t[t.index("function abrirSituacao"):idx]
    assert "Api." not in abrir and "modalSituacao.show()" in abrir


@pytest.mark.parametrize("p", PAGINAS + JS_MODULO)
def test_sem_confirm_nativo(p):
    assert not re.search(r"\bconfirm\s*\(", ler(p))


# ------------------------------------------------------------------ Funcionario (UC01 FA3)
def test_organizacoes_js_desabilita_campos_alem_do_contato_para_funcionario():
    # UC01 FA3, FE4, RN09: nome, CNPJ e tipo ficam travados no modo contato; so telefone/email/endereco editaveis
    t = ler(JS_ORG)
    assert "modo === 'contato'" in t
    assert re.search(r"\['nome',\s*'cnpj'\]\.forEach\(function \(k\) \{ f\[k\]\.readOnly = tudoLeitura \|\| soContato", t)
    assert re.search(r"f\.tipo\.disabled\s*=\s*tudoLeitura\s*\|\|\s*soContato", t)
    assert re.search(r"\['telefone',\s*'email',\s*'endereco'\]\.forEach\(function \(k\) \{ f\[k\]\.readOnly = tudoLeitura; \}", t)


def test_funcionario_so_envia_contato_via_patch_contato():
    # UC01 FA3, RF09
    t = ler(JS_ORG)
    assert re.search(r"Api\.patch\('/organizacoes/' \+ [^,]+ \+ '/contato',\s*contato\)", t)
    # o PUT completo e o POST so no ramo do Administrador (modos 'editar' / 'criar')
    assert "estado.admin ? 'editar'" in t


def test_funcionario_nao_ve_novo_cadastro_nem_desativar():
    # RN03, RN09: botoes de admin escondidos (conveniencia; a seguranca e do back-end)
    t = ler(JS_ORG)
    assert "$('btn-novo').hidden = !estado.admin" in t
    corpo = t[t.index("function botoes"):t.index("function linhaHtml")]
    assert corpo.index("if (estado.admin)") < corpo.index("btn-acao-situacao")
    assert corpo.index("btn-acao-situacao") < corpo.index("Editar contato")


def test_empresa_doadora_e_somente_leitura_para_funcionario():
    # UC01 FE4, DP-26
    t = ler(JS_ORG)
    assert "o.tipo !== 'Empresa Doadora'" in t
    assert "'leitura'" in t and "Consultar" in t


def test_aviso_de_perfil_na_pagina_de_organizacoes():
    # UC01 FA3
    assert 'id="aviso-perfil"' in ler(PAG_ORG)


def test_validacao_no_cliente_so_de_contato_para_funcionario():
    # UC01 FA3, RNF04
    assert "soContato: modo === 'contato'" in ler(JS_ORG)
    assert "opcoes.soContato" in ler(JS_COMUM)


# ------------------------------------------------------------------ formularios
def test_formulario_de_organizacao_tem_os_campos_do_uc01():
    # UC01 passo 2
    campos = set(re.findall(r'<(?:input|select|textarea)[^>]*\bid="(f-[^"]+)"', ler(PAG_ORG)))
    assert {"f-nome", "f-cnpj", "f-tipo", "f-telefone", "f-email", "f-endereco", "f-situacao"} <= campos


def _opcoes(bloco):
    """Valores das <option> (value="..." ou o texto), ignorando o placeholder vazio."""
    achados = []
    for attrs, texto in re.findall(r"<option([^>]*)>([^<]*)</option>", bloco):
        m = re.search(r'value="([^"]*)"', attrs)
        valor = m.group(1) if m else texto.strip()
        if valor:
            achados.append(valor)
    return achados


def test_tipo_de_organizacao_so_oferece_os_tres_valores():
    # UC01 passo 3 (Patrocinador nao e tipo de organizacao, secao 6.2)
    h = ler(PAG_ORG)
    bloco = h[h.index('id="f-tipo"'):]
    bloco = bloco[:bloco.index("</select>")]
    assert _opcoes(bloco) == ["Cliente Empresa", "Cliente ONG", "Empresa Doadora"]


def test_situacao_so_oferece_ativa_e_inativa():
    # DP-03
    for pag, sid in ((PAG_ORG, "f-situacao"), (PAG_PAR, "f-situacao")):
        h = ler(pag)
        bloco = h[h.index(f'id="{sid}"'):]
        bloco = bloco[:bloco.index("</select>")]
        assert _opcoes(bloco) == ["Ativa", "Inativa"], pag.name


def test_atuacao_do_parceiro_so_oferece_os_dois_valores():
    # UC06 passo 3
    h = ler(PAG_PAR)
    bloco = h[h.index('id="f-atuacao"'):]
    bloco = bloco[:bloco.index("</select>")]
    assert _opcoes(bloco) == ["Empresa Doadora", "Patrocinador em Potencial"]


def test_script_de_organizacoes_nao_envia_situacao_no_put():
    # contrato: PUT sem situacao; so o POST leva
    t = ler(JS_ORG)
    assert t.count("completo.situacao") == 1
    assert t.index("completo.situacao") < t.index("Api.put")


def test_parceiros_carrega_so_organizacoes_ativas_sem_parceria():
    # UC06 passo 3/4, FE3
    assert "situacao=Ativa&sem_parceria=true" in ler(JS_PAR)


@pytest.mark.parametrize("p", PAGINAS)
def test_campos_dos_formularios_tem_rotulo_associado(p):
    # RNF06
    h = ler(p)
    ids = re.findall(r'<(?:input|select|textarea)[^>]*\bid="(f-[^"]+|filtro-[^"]+)"', h)
    assert ids
    for i in ids:
        assert re.search(rf'<label[^>]*for="{i}"', h), f"{p.name}: campo {i} sem label"


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_com_idioma_e_viewport(p):
    # RNF06
    h = ler(p)
    assert '<html lang="pt-BR"' in h or '<html lang="pt-br"' in h.lower()
    assert 'name="viewport"' in h


# ------------------------------------------------------------------ mensagens em portugues
CODIGOS_DO_CONTRATO = ["DADOS_INVALIDOS", "NAO_AUTENTICADO", "SEM_PERMISSAO", "CONTA_INATIVA", "NAO_ENCONTRADO",
                       "CNPJ_DUPLICADO", "PARCERIA_DUPLICADA", "TIPO_EM_USO", "ORGANIZACAO_INVALIDA",
                       "ATUACAO_INCOMPATIVEL", "OPERACAO_NAO_PERMITIDA", "ORGANIZACAO_EM_USO", "ORGANIZACAO_COM_USUARIOS", "ALTERACAO_BLOQUEADA"]


def _mensagens(arquivo, nome_var):
    t = ler(arquivo)
    m = re.search(r"var\s+" + nome_var + r"\s*=\s*\{(.*?)\n\s*\};", t, re.S)
    assert m, f"{nome_var} ausente em {arquivo.name}"
    return dict(re.findall(r"(\w+)\s*:\s*'((?:[^'\\]|\\.)*)'", m.group(1)))


def test_contrato_lista_os_mesmos_codigos_testados():
    # sincronia com contratos/modulo-2.yaml (x-codigos-erro)
    y = ler(RAIZ / "contratos" / "modulo-2.yaml")
    bloco = y[y.index("x-codigos-erro:"):]
    achados = set(re.findall(r"^\s+([A-Z_]+):", bloco, re.M))
    assert achados <= set(CODIGOS_DO_CONTRATO)


def test_todos_os_codigos_de_erro_do_contrato_tem_mensagem_em_portugues():
    # RNF04: api.js + usuarios-comum.js (M1) + organizacoes-comum.js (M2)
    msgs = {**_mensagens(JS / "api.js", "MENSAGENS"), **_mensagens(JS / "usuarios-comum.js", "MSG"),
            **_mensagens(JS_COMUM, "MSG")}
    palavras = r"\b(não|você|e-mail|organização|dados|permissão|sessão|conta|perfil|usuário|cnpj|vínculo|registro|" \
               r"atuação|tipo|operação)\b"
    for cod in CODIGOS_DO_CONTRATO:
        assert cod in msgs and msgs[cod].strip(), f"sem mensagem para {cod}"
        assert re.search(palavras, msgs[cod], re.I), cod


def test_mensagens_do_modulo_2_cobrem_seus_codigos_especificos():
    # UC01 FE1/FE3/FE4, UC06 FE2/FE3, UC25 FE1
    msgs = _mensagens(JS_COMUM, "MSG")
    for cod in ("CNPJ_DUPLICADO", "TIPO_EM_USO", "OPERACAO_NAO_PERMITIDA", "PARCERIA_DUPLICADA",
                "ATUACAO_INCOMPATIVEL", "ORGANIZACAO_INVALIDA", "DADOS_INVALIDOS", "SEM_PERMISSAO", "NAO_ENCONTRADO"):
        assert cod in msgs, cod


@pytest.mark.parametrize("js", [JS_ORG, JS_PAR])
def test_scripts_exibem_mensagem_do_erro_via_msgerro(js):
    # RNF04: cada erro e mostrado ao usuario
    t = ler(js)
    assert t.count("O.msgErro(err)") >= 3


def test_tratamento_dos_erros_especificos_por_tela():
    # UC25 FE1 (CNPJ_DUPLICADO), UC01 FE3 (TIPO_EM_USO), UC06 FE2/FE3
    o, p = ler(JS_ORG), ler(JS_PAR)
    assert "CNPJ_DUPLICADO" in o and "TIPO_EM_USO" in o
    assert "NAO_ENCONTRADO" in o and "NAO_ENCONTRADO" in p


def test_validacao_do_cnpj_no_cliente_exige_14_digitos():
    # UC25 passo 2
    t = ler(JS_COMUM)
    assert "digitos(c).length !== 14" in t
    assert "[10, 11].indexOf(digitos(t).length)" in t


# ------------------------------------------------------------------ RNF01 / RNF06 / identidade
def _px(valor):
    m = re.fullmatch(r"([\d.]+)(rem|em|px)", valor.strip())
    if not m:
        return None
    n = float(m.group(1))
    return n if m.group(2) == "px" else n * 16


@pytest.mark.parametrize("p", CSS_NOVOS)
def test_css_novo_sem_fonte_abaixo_de_16px(p):
    # RNF01
    for valor in re.findall(r"font-size\s*:\s*([^;}]+)", ler(p)):
        px = _px(valor)
        if px is not None:
            assert px >= 16, f"{p.name}: font-size {valor}"
        else:
            assert not re.search(r"\b(small|smaller|x-small|xx-small)\b", valor), f"{p.name}: {valor}"


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_sem_small_nem_fonte_pequena(p):
    # RNF01
    h = ler(p)
    assert not re.search(r"<small|class=\"[^\"]*\b(small|fs-6|fs-7)\b|font-size\s*:\s*0?\.\d+(rem|em)", h, re.I)
    for valor in re.findall(r"font-size\s*:\s*([^;}\"]+)", h):
        px = _px(valor)
        assert px is None or px >= 16


@pytest.mark.parametrize("p", JS_MODULO)
def test_scripts_nao_geram_html_com_fonte_pequena(p):
    # RNF01
    assert not re.search(r"<small|\bfont-size\b|class=\\?\"[^\"]*\bsmall\b", ler(p), re.I)


def test_sem_vermelho_padrao_do_bootstrap_nas_telas_do_modulo():
    # DP-06 revista: #dc3545 proibido
    for p in PAGINAS + JS_MODULO + CSS_NOVOS:
        assert "#dc3545" not in ler(p).lower(), p.name
        assert "btn-danger" not in ler(p), p.name


def test_desativar_nao_usa_vermelho_reservado_a_erros():
    # DP-06 revista: vermelho so para erros
    css = ler(CSS / "organizacoes.css")
    assert "#9b1c1c" not in css.lower() and "--leaf-erro" not in css
    assert "btn-acao-situacao" in css


def test_estado_nunca_so_por_cor():
    # RNF06: selo de situacao com texto e simbolo
    t = ler(JS_COMUM)
    assert re.search(r"function seloSituacao", t) and "U.esc(s)" in t


def test_sem_innerhtml_de_dado_sem_escape_nas_linhas():
    # RNF04/seguranca: dados da API passam por U.esc nas linhas da tabela
    t = ler(JS_ORG)
    linha = t[t.index("function linhaHtml"):t.index("async function carregar")]
    assert "U.esc(o.nome_razao_social)" in linha and "U.esc(o.email)" in linha
