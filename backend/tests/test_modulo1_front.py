"""Modulo 1 - front estatico (leitura dos arquivos; nao toca no front). UC02, UC03, UC26, UC27;
RF01, RF02, RF04; RN02, RN04; RNF01, RNF04, RNF05, RNF06; DP-12 (resolvida)."""
import re
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"
JS = FRONT / "js"
CSS = FRONT / "css"
PAG_ADMIN = FRONT / "app" / "usuarios" / "index.html"
PAG_ORG = FRONT / "app" / "usuarios" / "organizacao.html"
JS_MODULO = ["usuarios.js", "usuarios-comum.js", "usuarios-organizacao.js"]
CSS_NOVOS = ["usuarios.css"]


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _htmls():
    return sorted(p for p in FRONT.rglob("*.html") if "_original" not in p.parts)


# ------------------------------------------------------------------ telas existem
@pytest.mark.parametrize("p", [PAG_ADMIN, PAG_ORG])
def test_telas_do_modulo_existem(p):
    # UC02, UC03
    assert p.is_file()


@pytest.mark.parametrize("nome", JS_MODULO)
def test_scripts_do_modulo_existem(nome):
    # UC02, UC03
    assert (JS / nome).is_file()


def test_pagina_admin_carrega_api_layout_e_scripts_na_ordem():
    # UC02 (RNF05: guarda de rota via Layout)
    srcs = re.findall(r'<script[^>]+src="([^"]+)"', ler(PAG_ADMIN))
    locais = [s.split("/")[-1] for s in srcs if not s.startswith("http")]
    assert locais == ["api.js", "layout.js", "usuarios-comum.js", "usuarios.js"]


def test_pagina_organizacao_carrega_api_layout_e_scripts_na_ordem():
    # UC03
    srcs = re.findall(r'<script[^>]+src="([^"]+)"', ler(PAG_ORG))
    locais = [s.split("/")[-1] for s in srcs if not s.startswith("http")]
    assert locais == ["api.js", "layout.js", "usuarios-comum.js", "usuarios-organizacao.js"]


def test_paginas_do_modulo_usam_layout_iniciar_com_a_chave_do_menu():
    # RN01, RNF05
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'usuarios'", ler(JS / "usuarios.js"))
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'usuarios_organizacao'", ler(JS / "usuarios-organizacao.js"))


def test_scripts_apontam_para_rotas_do_contrato():
    # UC02, UC03, UC27 (somente via Api)
    adm = ler(JS / "usuarios.js")
    for rota in ("/usuarios", "/usuarios/perfis-atribuiveis", "/usuarios/opcoes-organizacao"):
        assert f"'{rota}" in adm, rota
    for metodo in ("Api.get", "Api.post", "Api.put", "Api.delete"):
        assert metodo in adm, metodo
    assert "'/organizacao/usuarios" in ler(JS / "usuarios-organizacao.js")
    assert "Api.post" in ler(JS / "usuarios-organizacao.js")


# ------------------------------------------------------------------ fetch so em api.js
def test_nenhum_js_do_front_alem_de_api_js_usa_fetch():
    # RNF04, DP-12 (resolvida): api.js e o unico lugar com fetch
    com_fetch = [p.name for p in JS.glob("*.js") if p.name != "api.js" and re.search(r"\bfetch\s*\(", ler(p))]
    assert com_fetch == [], f"fetch fora de api.js: {com_fetch}"


@pytest.mark.parametrize("p", [PAG_ADMIN, PAG_ORG])
def test_paginas_sem_fetch_nem_xhr_inline(p):
    # RNF04
    sem_externos = re.sub(r"<script[^>]+src=[^>]*>\s*</script>", "", ler(p))
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", sem_externos)


@pytest.mark.parametrize("nome", JS_MODULO)
def test_scripts_do_modulo_sem_fetch_nem_url_da_api(nome):
    # RNF04
    t = ler(JS / nome)
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", t)
    assert "/api/v1" not in t


# ------------------------------------------------------------------ menu
def _item_menu(chave):
    layout = ler(JS / "layout.js")
    m = re.search(r"\{\s*chave:\s*'" + chave + r"'[^}]*\}", layout)
    assert m, f"item {chave} ausente do MENU"
    return m.group(0)


@pytest.mark.parametrize("chave,href", [("usuarios", "usuarios/index.html"),
                                        ("usuarios_organizacao", "usuarios/organizacao.html")])
def test_itens_do_menu_ligados_as_paginas(chave, href):
    # UC02, UC03, RN01
    item = _item_menu(chave)
    assert f"href: '{href}'" in item
    assert (FRONT / "app" / href).is_file()


def test_itens_de_outros_modulos_so_tem_link_quando_a_tela_existe():
    # nao pode ligar menu a tela que nao existe; a partir do Modulo 5 so Relatorios (UC22 a UC24) segue sem link
    layout = ler(JS / "layout.js")
    sem_link = []
    for chave, href in re.findall(r"chave:\s*'(\w+)'[^}]*?href:\s*(null|'[^']+')", layout):
        if href == "null":
            sem_link.append(chave)
        else:
            alvo = FRONT / "app" / href.strip("'")
            assert alvo.is_file(), f"{chave} aponta para {href} inexistente"
    assert sem_link == [], sem_link


# ------------------------------------------------------------------ organizacao.html (UC03 FE2)
@pytest.mark.parametrize("campo", ["f-perfil", "f-org", "perfil", "id_organizacao", "organizacao"])
def test_organizacao_html_sem_campos_de_perfil_ou_organizacao(campo):
    # UC03 FE2, RN02, RN04: perfil e organizacao sao herdados, nao digitados
    h = ler(PAG_ORG)
    assert not re.search(rf'<(input|select|textarea)[^>]*\bid="{campo}"', h)
    assert not re.search(rf'<(input|select|textarea)[^>]*\bname="{campo}"', h)


def test_organizacao_html_so_tem_nome_email_senha():
    # UC03 passo 2
    campos = re.findall(r'<(?:input|select|textarea)[^>]*\bid="(f-[^"]+)"', ler(PAG_ORG))
    assert sorted(campos) == ["f-email", "f-nome", "f-senha"]


def test_organizacao_js_nao_envia_perfil_nem_organizacao():
    # UC03 FE2, RN02
    js = ler(JS / "usuarios-organizacao.js")
    corpo = re.search(r"Api\.post\([^;]*;", js, re.S).group(0)
    assert "perfil" not in corpo and "id_organizacao" not in corpo


# ------------------------------------------------------------------ exclusao com confirmacao (UC02 FA3)
def test_modal_de_exclusao_com_confirmacao():
    # UC02 FA3
    h = ler(PAG_ADMIN)
    assert 'id="modal-excluir"' in h
    assert 'id="btn-confirmar-excluir"' in h and 'id="btn-nao-excluir"' in h
    assert re.search(r'id="btn-nao-excluir"', h) and "data-bs-dismiss=\"modal\"" in h


def test_exclusao_so_chama_api_dentro_do_clique_de_confirmacao():
    # UC02 FA3: o botao da tabela apenas abre o modal
    js = ler(JS / "usuarios.js")
    assert js.count("Api.delete(") == 1
    trecho = js[js.index("btn-confirmar-excluir').addEventListener"):]
    assert "Api.delete(" in trecho
    abrir = js[js.index("async function abrirExclusao"):js.index("btn-confirmar-excluir').addEventListener")]
    assert "Api.delete(" not in abrir and "modalExcluir.show()" in abrir


def test_html_nao_usa_confirm_nativo():
    # UC02 FA3: confirmacao acessivel em modal Bootstrap
    for p in (PAG_ADMIN, PAG_ORG):
        assert "confirm(" not in ler(p)
    for n in JS_MODULO:
        assert not re.search(r"\bconfirm\s*\(", ler(JS / n))


# ------------------------------------------------------------------ login sem cadastro (RF01)
def test_login_sem_registre_se_nem_link_para_cadastro():
    # RF01 (o login nao realiza cadastro)
    h = ler(FRONT / "login.html")
    assert not re.search(r"registre-?\s*se", h, re.I)
    assert "cadastro.html" not in h


def test_login_nao_carrega_scripts_legados():
    # RF01, DP-12
    h = ler(FRONT / "login.html")
    assert "scripts.js" not in h
    assert "cadastro.js" not in h


def test_js_scripts_removido():
    # DP-12 (resolvida)
    assert not (JS / "scripts.js").exists()


def test_nenhuma_pagina_ou_script_referencia_scripts_js():
    # DP-12
    for p in _htmls():
        assert "scripts.js" not in ler(p), p.name
    for p in JS.glob("*.js"):
        assert "scripts.js" not in ler(p), p.name


# ------------------------------------------------------------------ mensagens dos codigos de erro
CODIGOS_DO_CONTRATO = ["DADOS_INVALIDOS", "NAO_AUTENTICADO", "SEM_PERMISSAO", "CONTA_INATIVA", "NAO_ENCONTRADO",
                       "EMAIL_DUPLICADO", "ORGANIZACAO_INVALIDA", "VINCULO_INVALIDO", "ALTERACAO_BLOQUEADA",
                       "OPERACAO_NAO_PERMITIDA", "SENHA_INVALIDA", "SENHA_IGUAL_ATUAL"]


def _mensagens(arquivo, nome_var):
    t = ler(arquivo)
    m = re.search(r"var\s+" + nome_var + r"\s*=\s*\{(.*?)\n\s*\};", t, re.S)
    assert m, f"{nome_var} ausente em {arquivo.name}"
    return dict(re.findall(r"(\w+)\s*:\s*'((?:[^'\\]|\\.)*)'", m.group(1)))


def test_contrato_lista_os_mesmos_codigos_testados():
    # sincronia com contratos/modulo-1.yaml (x-codigos-erro)
    y = ler(RAIZ / "contratos" / "modulo-1.yaml")
    bloco = y[y.index("x-codigos-erro:"):]
    achados = set(re.findall(r"^\s+([A-Z_]+):", bloco, re.M))
    assert achados <= set(CODIGOS_DO_CONTRATO)


def test_todos_os_codigos_de_erro_do_contrato_tem_mensagem_em_portugues():
    # RNF04: api.js (comuns) + usuarios-comum.js (do modulo)
    msgs = {**_mensagens(JS / "api.js", "MENSAGENS"), **_mensagens(JS / "usuarios-comum.js", "MSG")}
    for cod in CODIGOS_DO_CONTRATO:
        assert cod in msgs and msgs[cod].strip(), f"sem mensagem para {cod}"
        assert re.search(r"[a-zçãáéíóúâêô]", msgs[cod]) and re.search(r"\b(não|você|e-mail|organização|dados|"
                                                                      r"permissão|sessão|conta|perfil|usuário)\b",
                                                                      msgs[cod], re.I), cod


def test_mensagens_do_modulo_cobrem_os_codigos_especificos_do_modulo1():
    # UC02 FE1-FE4, UC03 FE2, UC27
    msgs = _mensagens(JS / "usuarios-comum.js", "MSG")
    for cod in ("EMAIL_DUPLICADO", "ORGANIZACAO_INVALIDA", "VINCULO_INVALIDO", "ALTERACAO_BLOQUEADA",
                "OPERACAO_NAO_PERMITIDA", "SEM_PERMISSAO", "CONTA_INATIVA", "NAO_ENCONTRADO", "DADOS_INVALIDOS"):
        assert cod in msgs, cod


# ------------------------------------------------------------------ RNF01 / RNF06 / identidade
def _px(valor):
    m = re.fullmatch(r"([\d.]+)(rem|em|px)", valor.strip())
    if not m:
        return None
    n = float(m.group(1))
    return n if m.group(2) == "px" else n * 16


@pytest.mark.parametrize("nome", CSS_NOVOS)
def test_css_novo_sem_fonte_abaixo_de_16px(nome):
    # RNF01
    for valor in re.findall(r"font-size\s*:\s*([^;}]+)", ler(CSS / nome)):
        px = _px(valor)
        if px is not None:
            assert px >= 16, f"{nome}: font-size {valor}"
        else:
            assert not re.search(r"\b(small|smaller|x-small|xx-small)\b", valor), f"{nome}: {valor}"


@pytest.mark.parametrize("p", [PAG_ADMIN, PAG_ORG])
def test_paginas_do_modulo_sem_small_nem_fonte_pequena(p):
    # RNF01
    h = ler(p)
    assert not re.search(r"<small|class=\"[^\"]*\b(small|fs-6|fs-7)\b|font-size\s*:\s*0?\.\d+(rem|em)", h, re.I)
    for valor in re.findall(r"font-size\s*:\s*([^;}\"]+)", h):
        px = _px(valor)
        assert px is None or px >= 16


@pytest.mark.parametrize("nome", JS_MODULO)
def test_scripts_do_modulo_nao_geram_html_com_fonte_pequena(nome):
    # RNF01
    t = ler(JS / nome)
    assert not re.search(r"<small|\bfont-size\b|class=\\?\"[^\"]*\bsmall\b", t, re.I)


def test_sem_vermelho_padrao_do_bootstrap_nas_telas_do_modulo():
    # DP-06 revista: #dc3545 proibido
    arquivos = [PAG_ADMIN, PAG_ORG] + [JS / n for n in JS_MODULO] + [CSS / n for n in CSS_NOVOS]
    for p in arquivos:
        assert "#dc3545" not in ler(p).lower(), p.name


def test_token_de_erro_so_declarado_em_identidade_css():
    # DP-06 revista
    for p in [PAG_ADMIN, PAG_ORG] + [JS / n for n in JS_MODULO] + [CSS / n for n in CSS_NOVOS]:
        assert "#9b1c1c" not in ler(p).lower(), p.name


@pytest.mark.parametrize("p", [PAG_ADMIN, PAG_ORG])
def test_campos_dos_formularios_tem_rotulo_associado(p):
    # RNF06
    h = ler(p)
    ids = re.findall(r'<(?:input|select|textarea)[^>]*\bid="(f-[^"]+|filtro-[^"]+)"', h)
    assert ids
    for i in ids:
        assert re.search(rf'<label[^>]*for="{i}"', h), f"{p.name}: campo {i} sem label"


@pytest.mark.parametrize("p", [PAG_ADMIN, PAG_ORG])
def test_paginas_com_idioma_e_viewport(p):
    # RNF06, responsividade
    h = ler(p)
    assert '<html lang="pt-BR"' in h or '<html lang="pt-br"' in h.lower()
    assert 'name="viewport"' in h


def test_senha_com_dica_de_8_a_128():
    # RN02 M1, RNF04
    for p in (PAG_ADMIN, PAG_ORG):
        h = ler(p)
        assert 'maxlength="128"' in h and "8 a 128" in h


def test_scripts_nao_gravam_senha_no_storage_nem_no_console():
    # RNF03
    for n in JS_MODULO:
        t = ler(JS / n)
        assert not re.search(r"(sessionStorage|localStorage)", t)
        assert not re.search(r"console\.\w+\([^)]*senha", t, re.I)
