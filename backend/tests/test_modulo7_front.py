"""Modulo 7 - front estatico do marketplace e das solicitacoes de doacao (leitura dos arquivos; node para o retorno seguro).
UC12, UC13, UC09 (Anunciar), UC11, UC19, novo UC "Solicitar doacao"; RN04, RN12, RN13; RNF01, RNF05, RNF06; DP-68 a DP-78.
Telas: hardware.html (lista), compra.html (detalhe), software.html (redireciona), app/doacoes/solicitacoes.html; scripts publico.js,
marketplace.js, produto.js, doacoes-solicitacoes.js; folha marketplace.css."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"
JS = FRONT / "js"
LISTA, DETALHE, SOFT = FRONT / "hardware.html", FRONT / "compra.html", FRONT / "software.html"
SOLIC = FRONT / "app" / "doacoes" / "solicitacoes.html"
J_PUB, J_LISTA, J_DET, J_SOL = JS / "publico.js", JS / "marketplace.js", JS / "produto.js", JS / "doacoes-solicitacoes.js"
CSS = FRONT / "css" / "marketplace.css"
PUBLICAS = [FRONT / "index.html", LISTA, DETALHE, FRONT / "quemsomos.html"]
JS_NOVOS = [J_PUB, J_LISTA, J_DET, J_SOL]
ARQUIVOS = [LISTA, DETALHE, SOLIC] + JS_NOVOS + [CSS]


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _sem_comentarios(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


def _srcs(p):
    return [s.split("/")[-1] for s in re.findall(r'<script[^>]+src="([^"]+)"', ler(p)) if not s.startswith("http")]


# ------------------------------------------------------------------ existencia, comentarios e aposentadoria do catalogo
@pytest.mark.parametrize("p", ARQUIVOS + [SOFT])
def test_arquivos_existem(p):
    assert p.is_file()


@pytest.mark.parametrize("p", ARQUIVOS)
def test_arquivos_citam_uc_e_dp(p):
    # CLAUDE.md: toda tela cita UC e decisao no comentario inicial
    inicio = ler(p)[:1800]
    assert re.search(r"\bUC\d+", inicio) and re.search(r"DP-(6[89]|7\d)", inicio), p.name
    if p.suffix != ".css":
        assert re.search(r"\bRN\d+", inicio) or p in (J_PUB,), p.name


def test_catalogo_foi_aposentado_e_o_menu_leva_ao_marketplace():
    # DP-78
    assert not (FRONT / "app" / "catalogo").exists() and not (JS / "catalogo.js").exists()
    m = re.search(r"\{\s*chave:\s*'catalogo'[^}]*\}", ler(JS / "layout.js"))
    assert m and "href: '../hardware.html'" in m.group(0)
    assert (FRONT / "hardware.html").is_file()
    for p in list(JS.glob("*.js")) + list((FRONT / "app").rglob("*.html")):
        assert "catalogo/index.html" not in ler(p), p.name


def test_software_html_apenas_redireciona_ao_marketplace():
    h = ler(SOFT)
    assert 'http-equiv="refresh"' in h and "hardware.html" in h and "product-card" not in h


# ------------------------------------------------------------------ sem produtos fixos, sem alert, sem fetch
def test_lista_e_detalhe_nao_tem_produtos_fixos_nem_quantidade_nem_ofertante():
    # DP-68: tudo vem da API
    for p in (LISTA, DETALHE):
        h = _sem_comentarios(ler(p))
        assert "GTX" not in h and "Ofertante" not in h and "Quantidade" not in h and "R$ " not in h, p.name
        assert "onclick=" not in h and "alert(" not in h
    assert 'id="grade"' in ler(LISTA) and 'id="form-filtros"' in ler(LISTA) and 'id="filtro-categoria"' in ler(LISTA)


@pytest.mark.parametrize("p", JS_NOVOS + [LISTA, DETALHE, SOLIC])
def test_sem_alert_nem_fetch_nem_eval(p):
    t = _sem_comentarios(ler(p))
    assert not re.search(r"\balert\s*\(|\bfetch\s*\(|XMLHttpRequest|eval\(|document\.write", t), p.name
    assert "/api/v1" not in t


@pytest.mark.parametrize("p", [LISTA, DETALHE, SOLIC])
def test_paginas_sem_script_inline(p):
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", _sem_comentarios(ler(p)))


def test_nenhum_js_alem_de_api_js_usa_fetch():
    com_fetch = [p.name for p in JS.glob("*.js") if p.name != "api.js" and re.search(r"\bfetch\s*\(", _sem_comentarios(ler(p)))]
    assert com_fetch == [], com_fetch


def test_scripts_nao_gravam_token():
    # RNF05: so api.js guarda o token (a selecao de produtos da ONG usa chave propria, sem segredo)
    for p in JS_NOVOS:
        t = _sem_comentarios(ler(p))
        assert "localStorage" not in t and "leafti.token" not in t and "document.cookie" not in t, p.name


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
@pytest.mark.parametrize("p", JS_NOVOS + [JS / "api.js", JS / "login.js", JS / "layout.js"])
def test_sintaxe_valida(p):
    r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr


# ------------------------------------------------------------------ scripts e estilos carregados
def test_ordem_dos_scripts():
    assert _srcs(LISTA) == ["api.js", "publico.js", "marketplace.js"]
    assert _srcs(DETALHE) == ["api.js", "publico.js", "produto.js"]
    assert _srcs(SOLIC) == ["api.js", "layout.js", "usuarios-comum.js", "equipamentos-comum.js", "doacoes-solicitacoes.js"]
    assert [s for s in _srcs(FRONT / "login.html") if s != "senha-olho.js"] == ["api.js", "publico.js", "login.js"]


@pytest.mark.parametrize("p", [LISTA, DETALHE, SOLIC])
def test_identidade_bootstrap_viewport_e_portugues(p):
    h = ler(p)
    assert "identidade.css" in h and "marketplace.css" in h and "bootstrap@5" in h
    assert 'lang="pt-BR"' in h and 'name="viewport"' in h and 'charset="UTF-8"' in h


def test_css_so_usa_cores_e_fontes_da_identidade():
    css = _sem_comentarios(ler(CSS))
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", css), "cor fora das variaveis da identidade"
    assert not re.search(r"font-family:(?!\s*var\()", css)
    for px in re.findall(r"font-size:\s*([\d.]+)(px|rem)", css):
        v = float(px[0]) * (16 if px[1] == "rem" else 1)
        assert v >= 16, px
    assert "992px" not in css or "@media" in css and "1280px" in css and "1920px" in css


# ------------------------------------------------------------------ cabecalho (Entrar / nome / Sair)
@pytest.mark.parametrize("p", PUBLICAS)
def test_paginas_publicas_tem_cabecalho_com_entrar_nome_sair(p):
    h = ler(p)
    assert 'id="area-usuario"' in h and "publico.js" in h and "api.js" in h, p.name
    assert 'href="login.html"' not in _sem_comentarios(h).replace("login.html?", "x"), p.name  # o link vem do JS, com retorno


def test_cabecalho_mostra_entrar_nome_e_sair():
    t = ler(J_PUB)
    assert ">Entrar<" in t and ">Sair<" in t and "u.nome" in t and "Api.sessao.limpar()" in t


# ------------------------------------------------------------------ rotas do contrato modulo-7
def test_lista_chama_rotas_do_contrato():
    t = ler(J_LISTA)
    assert "Api.getPublico('/marketplace/categorias')" in t and "Api.getPublico('/marketplace/produtos?' + q.join('&'))" in t
    assert "Api.post('/doacoes/solicitacoes', { ids_equipamentos: ids })" in t
    assert "id_categoria=" in t and "busca=" in t and "'size=' + TAMANHO" in t
    assert not re.search(r"Api\.(put|patch|delete)\(", t)


def test_detalhe_chama_rotas_do_contrato_e_envia_forma_de_pagamento():
    t = ler(J_DET)
    assert "Api.getPublico('/marketplace/produtos/' + id)" in t
    assert "Api.post('/vendas', { ids_equipamento: [produto.id_equipamento], forma_pagamento: sel.value })" in t
    assert "Api.post('/doacoes/solicitacoes', { ids_equipamentos: [produto.id_equipamento] })" in t
    for forma in ("Pix", "Boleto", "Transferência bancária", "Cartão de crédito"):
        assert forma in t


def test_solicitacoes_chama_rotas_do_contrato():
    t = ler(J_SOL)
    for rota in ("Api.get('/doacoes/solicitacoes?' + q.join('&'))", "Api.get('/doacoes/solicitacoes/' + id)",
                 "'/aprovar'", "'/recusar', { motivo: motivo }", "'/cancelar'"):
        assert rota in t, rota
    assert not re.search(r"Api\.\w+\(\s*'/equipamentos|Api\.delete", t)


def test_api_tem_leitura_publica_com_token_opcional():
    t = ler(JS / "api.js")
    assert "getPublico" in t and "semToken: true" in t and "e.status === 401" in t


# ------------------------------------------------------------------ acoes por perfil e valor (DP-74)
def test_acoes_por_perfil_no_detalhe():
    t = ler(J_DET)
    assert "perfil === 'Cliente Empresa'" in t and ">Comprar<" in t and "forma-pagamento" in t
    assert "perfil === 'Cliente ONG'" in t and "Solicitar doação" in t
    assert "perfil === 'Empresa Doadora'" in t and ">Anunciar<" in t and "app/solicitacoes/index.html" in t
    assert "Selecione a forma de pagamento" in t  # validacao local
    assert "ITEM_INDISPONIVEL" in t and "EQUIPAMENTO_RESERVADO" in t  # produto saiu do marketplace
    assert "Administrador e Funcionário só consultam" in t or "só consultam" in t.lower() or "consultando" in t


def test_visitante_e_levado_ao_login_com_retorno_ao_produto():
    assert "P.urlLogin()" in ler(J_DET)
    pub = ler(J_PUB)
    assert "'?retorno=' + encodeURIComponent(r)" in pub and "paginaAtual" in pub


def test_texto_no_lugar_do_valor_quando_nao_visivel():
    assert "Entre como Cliente Empresa para ver o valor e comprar" in ler(J_PUB)
    assert "TEXTO_SEM_VALOR" in ler(J_PUB)
    # DP-83: texto por perfil
    pub = ler(J_PUB)
    assert "Valor visível apenas para Cliente Empresa" in pub and "'Cliente ONG'" in pub
    assert "P.textoSemValor()" in ler(J_LISTA) and "P.textoSemValor()" in ler(J_DET)
    # M-01: contorno da marca em CSS carregado pelas páginas públicas
    assert ".btn-outline-leaf" in (FRONT / "css" / "identidade.css").read_text(encoding="utf-8")
    assert "i.valor != null" in ler(J_LISTA) and "produto.valor != null" in ler(J_DET)


def test_ong_pode_marcar_varios_produtos_e_o_limite_e_20():
    t = ler(J_LISTA)
    assert "LIMITE = 20" in t and "data-acao=\"sel\"" in t and "ids_equipamentos" in t
    h = ler(LISTA)
    for i in ("barra-solicitacao", "painel-solicitacao", "btn-enviar-solicitacao", "btn-revisar"):
        assert f'id="{i}"' in h


def test_login_usa_retorno_validado():
    t = ler(JS / "login.js")
    assert "Publico.retornoSeguro(" in t and "window.location.href = destino" in t
    assert "location.href = retorno" not in t


# ------------------------------------------------------------------ solicitacoes de doacao (area interna)
def test_recusa_exige_motivo_de_3_a_500():
    t = ler(J_SOL)
    assert "Informe o motivo da recusa" in t and "pelo menos 3 caracteres" in t and "no máximo 500" in t
    assert 'maxlength="500"' in ler(SOLIC) and 'id="motivo"' in ler(SOLIC)


def test_acoes_so_para_pendente_e_por_perfil():
    t = ler(J_SOL)
    bloco = t[t.index("if (s.situacao === 'Pendente')"):t.index("$('acoes-detalhe').innerHTML = acoes")]
    assert "estado.interno" in bloco and "btn-aprovar" in bloco and "btn-recusar" in bloco and "btn-cancelar" in bloco
    assert "motivo_recusa" in t and "decidido_por" in t and "SOLICITACAO_NAO_PENDENTE" in t


def test_ong_ve_solicitacoes_com_menu_proprio_e_interno_com_chave_de_solicitacoes():
    t = ler(J_SOL)
    assert "'solicitacoes'" in t and "'minhas_doacoes'" in t and "Layout.iniciar(" in t


@pytest.mark.parametrize("pagina,js,dinamicos", [
    (LISTA, J_LISTA, set()),
    (DETALHE, J_DET, {"form-compra", "forma-pagamento", "forma-pagamento-erro", "btn-comprar", "btn-solicitar"}),  # criados por perfil
    (SOLIC, J_SOL, set()),
])
def test_todo_id_buscado_pelo_script_existe_na_pagina(pagina, js, dinamicos):
    ids = set(re.findall(r'\bid="([^"]+)"', ler(pagina)))
    usados = set(re.findall(r"\$\('([^']+)'\)", ler(js)))
    assert usados - ids - dinamicos == set()


@pytest.mark.parametrize("p", [LISTA, DETALHE, SOLIC])
def test_ids_unicos_e_labels_associados(p):
    h = ler(p)
    ids = re.findall(r'\bid="([^"]+)"', h)
    assert len(ids) == len(set(ids))
    for tipo, i in re.findall(r'<(input|select|textarea)[^>]*\bid="([^"]+)"', h):
        assert f'for="{i}"' in h, f"{p.name}: {tipo}#{i} sem label"


# ------------------------------------------------------------------ retorno seguro (open redirect), executado no node
_NODE = r"""
const fs = require('fs'), vm = require('vm');
const ctx = { console, document: { addEventListener() {}, createElement() { let t=''; return { set textContent(v){t=String(v)}, get innerHTML(){return t} }; } },
  location: { pathname: '/frontend/compra.html', search: '?id=7' } };
ctx.window = ctx; vm.createContext(ctx);
vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), ctx);
const P = ctx.Publico;
const entradas = JSON.parse(process.argv[3]);
console.log(JSON.stringify({ r: entradas.map(e => P.retornoSeguro(e)), ent: P.urlLogin('compra.html?id=7'), ruim: P.urlLogin('//evil.com') }));
"""

OK = ["compra.html?id=7", "hardware.html", "hardware.html?id_categoria=2&busca=placa", "app/solicitacoes/index.html"]
RUINS = ["http://evil.com", "https://evil.com/x.html", "//evil.com", "///evil.com", "/\\evil.com", "\\\\evil.com", "javascript:alert(1)",
         "JaVaScRiPt:alert(1)", "data:text/html,x", "compra.html\\..\\x", "/app/inicio.html", "../x.html", "a/../b.html", "login.html:80",
         "hardware.html\n", "", None, 5, "compra.php", "compra.html#x", "vbscript:x", "x.html?a=http://evil.com"]


@pytest.fixture(scope="module")
def retorno(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node nao instalado")
    s = tmp_path_factory.mktemp("n") / "r.js"
    s.write_text(_NODE, encoding="utf-8")
    r = subprocess.run(["node", str(s), str(J_PUB), json.dumps(OK + RUINS)], capture_output=True, text=True, timeout=60, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_retorno_aceita_so_caminho_relativo_de_pagina_html(retorno):
    # DP-68: aceita apenas o caminho relativo conhecido
    assert retorno["r"][: len(OK)] == OK


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_retorno_rejeita_open_redirect(retorno):
    # http://, //, javascript:, barra invertida, "..", nao string
    rejeitados = retorno["r"][len(OK):]
    # unico item "ruim" de lista que a regra aceita seria um caminho relativo valido; nenhum dos casos acima o e,
    # exceto "x.html?a=http://evil.com" (':' e '//' na query) que tambem deve cair
    assert rejeitados == [None] * len(RUINS), list(zip(RUINS, rejeitados))


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_url_de_login_leva_retorno_codificado_e_descarta_o_perigoso(retorno):
    assert retorno["ent"] == "login.html?retorno=compra.html%3Fid%3D7"
    assert retorno["ruim"] == "login.html"


def test_index_sem_formulario_morto_nem_alert():
    # DP-82: modal estatico removido; sem action="#" nem alert(
    html = (FRONT / "index.html").read_text(encoding="utf-8")
    assert 'action="#"' not in html and "alert(" not in html
    assert "modalAnunciar" not in html and "app/solicitacoes/index.html" in html
