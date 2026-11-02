"""Modulo 5 - front estatico (leitura dos arquivos; nao toca no front). UC12 a UC18, UC21;
RF04, RF13, RF14, RF15, RF19, RF20; RN04, RN13, RN14, RN15, RN19, RN20; RNF01, RNF04, RNF05, RNF06; DP-45 a DP-51.
Telas: app/compras, app/vendas, app/notas-fiscais; scripts compras.js, vendas.js, notas-fiscais.js
e vendas-comum.js; folha vendas.css."""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.permissoes import MATRIZ_FUNCIONALIDADES

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"
JS = FRONT / "js"
CSS = FRONT / "css"
PAG_COM = FRONT / "app" / "compras" / "index.html"
PAG_VEN = FRONT / "app" / "vendas" / "index.html"
PAG_NOT = FRONT / "app" / "notas-fiscais" / "index.html"
JS_COM, JS_VEN, JS_NOT = (JS / "compras.js", JS / "vendas.js", JS / "notas-fiscais.js")
JS_COMUM = JS / "vendas-comum.js"
JS_MODULO = [JS_COM, JS_VEN, JS_NOT, JS_COMUM]
CSS_NOVO = CSS / "vendas.css"
PAGINAS = [PAG_COM, PAG_VEN, PAG_NOT]
PAR_PAGINA_JS = [(PAG_COM, JS_COM), (PAG_VEN, JS_VEN), (PAG_NOT, JS_NOT)]
FORMAS = ["Pix", "Boleto", "Transferência bancária", "Cartão de crédito"]
SITUACOES = ["Pendente", "Confirmada", "Cancelada"]


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _sem_comentarios(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


def _item_menu(chave):
    m = re.search(r"\{\s*chave:\s*'" + chave + r"'[^}]*\}", ler(JS / "layout.js"))
    assert m, f"item {chave} ausente do MENU"
    return m.group(0)


# ------------------------------------------------------------------ existencia e comentarios UC/RN/DP
@pytest.mark.parametrize("p", PAGINAS + JS_MODULO + [CSS_NOVO])
def test_telas_scripts_e_css_do_modulo_existem(p):
    # UC12 a UC18, UC21
    assert p.is_file()


@pytest.mark.parametrize("p,ucs", [
    (PAG_COM, ["UC18", "UC13"]), (PAG_VEN, ["UC21", "UC14", "UC15", "UC16"]), (PAG_NOT, ["UC17"]),
    (JS_COM, ["UC18", "UC13"]), (JS_VEN, ["UC21", "UC14", "UC15", "UC16"]), (JS_NOT, ["UC17"]),
    (JS_COMUM, ["UC12", "UC13", "UC14", "UC15", "UC16", "UC17", "UC18", "UC21"]),
    (CSS_NOVO, ["UC12", "UC13", "UC14", "UC15", "UC16", "UC17", "UC18", "UC21"]),
])
def test_arquivos_citam_uc_no_comentario_inicial(p, ucs):
    # CLAUDE.md: toda tela cita UC e RN no comentario
    inicio = ler(p)[:1800]
    faixa = "UC12 a UC18, UC21" in inicio  # comum e css citam a faixa inteira do modulo
    for uc in ucs:
        assert uc in inicio or faixa, f"{p.name} sem {uc}"
    if p.suffix != ".css":
        assert re.search(r"\bRN\d+", inicio), f"{p.name} sem RN"


@pytest.mark.parametrize("p,rns", [
    (PAG_COM, ["RN04", "RN15"]), (JS_COM, ["RN04", "RN15"]),
    (PAG_VEN, ["RN03", "RN13", "RN14", "RN15", "RN19"]), (JS_VEN, ["RN03", "RN13", "RN14", "RN15", "RN19"]),
    (PAG_NOT, ["RN20"]), (JS_NOT, ["RN20"]),
])
def test_rns_do_modulo_citadas(p, rns):
    # UC12, UC14, UC17, UC18
    inicio = ler(p)[:1800]
    for rn in rns:
        assert rn in inicio, f"{p.name} sem {rn}"


@pytest.mark.parametrize("p", PAGINAS + [JS_COM, JS_VEN, JS_NOT, JS_COMUM])
def test_decisoes_dp_citadas(p):
    # CLAUDE.md: decisoes referenciadas (DP-45 a DP-51)
    assert re.search(r"DP-(4[5-9]|5[01])", ler(p)[:1800]), p.name


def test_paginas_carregam_scripts_na_ordem():
    # UC12 a UC21 (guarda de rota via Layout, RNF05)
    esperado = ["api.js", "layout.js", "usuarios-comum.js", "equipamentos-comum.js", "solicitacoes-comum.js", "vendas-comum.js"]
    for pagina, js in PAR_PAGINA_JS:
        srcs = [s.split("/")[-1] for s in re.findall(r'<script[^>]+src="([^"]+)"', ler(pagina)) if not s.startswith("http")]
        assert srcs == esperado + [js.name], (pagina.name, srcs)


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_carregam_a_folha_do_modulo_e_bootstrap(p):
    # RNF01
    h = ler(p)
    assert "vendas.css" in h and "bootstrap@5" in h and "identidade.css" in h


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_sao_responsivas_e_em_portugues(p):
    # RNF01
    h = ler(p)
    assert 'lang="pt-BR"' in h and 'name="viewport"' in h and 'charset="UTF-8"' in h


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_tem_link_de_pular_conteudo_e_regioes_ao_vivo(p):
    # RNF06 (acessibilidade): atalho, area principal focavel e mensagens aria-live
    h = ler(p)
    assert 'class="pular-conteudo"' in h and 'id="conteudo-app"' in h and 'tabindex="-1"' in h
    assert 'aria-live="polite"' in h


def test_vendas_css_tem_pontos_de_quebra_responsivos():
    # RNF01: 360 / 768 / 1200 px
    css = ler(CSS_NOVO)
    assert "@media" in css and "grade-catalogo" in css


# ------------------------------------------------------------------ guarda de rota e menu (RN01, RN04, RN13, RN15, RN19, RN20)
def test_telas_usam_layout_iniciar_com_a_chave_do_menu():
    # RN01, RNF05
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'minhas_compras'", ler(JS_COM))
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'vendas'", ler(JS_VEN))
    t = ler(JS_NOT)
    assert "'minhas_notas_fiscais'" in t and "'notas_fiscais'" in t and "Layout.iniciar(" in t


@pytest.mark.parametrize("chave,href", [("minhas_compras", "compras/index.html"),
                                        ("minhas_notas_fiscais", "notas-fiscais/index.html"), ("vendas", "vendas/index.html"),
                                        ("notas_fiscais", "notas-fiscais/index.html")])
def test_itens_do_menu_ligados_as_paginas_do_modulo(chave, href):
    # UC12, UC17, UC18, UC21
    assert f"href: '{href}'" in _item_menu(chave)
    assert (FRONT / "app" / href).is_file()


def test_nenhum_item_do_menu_aponta_para_pagina_inexistente_e_relatorios_segue_sem_link():
    # nao pode ligar menu a tela que nao existe; so Relatorios (UC22 a UC24) continua sem tela
    sem_link = []
    for chave, href in re.findall(r"chave:\s*'(\w+)'[^}]*?href:\s*(null|'[^']+')", ler(JS / "layout.js")):
        if href == "null":
            sem_link.append(chave)
        else:
            assert (FRONT / "app" / href.strip("'")).is_file(), f"{chave} -> {href}"
    assert sem_link == []


def test_matriz_de_funcionalidades_do_modulo_5():
    # RN03, RN04, RN13, RN15, RN19, RN20: quem enxerga cada item do menu
    quem = lambda chave: {perfil for perfil, itens in MATRIZ_FUNCIONALIDADES.items() if chave in itens}  # noqa: E731
    assert quem("catalogo") == {"Cliente Empresa"}
    assert quem("minhas_compras") == {"Cliente Empresa"}
    assert quem("minhas_notas_fiscais") == {"Cliente Empresa"}
    assert quem("vendas") == {"Administrador", "Funcionário"}
    assert quem("notas_fiscais") == {"Administrador"}  # Funcionario nao consulta notas (RN20)
    assert quem("minhas_compras").isdisjoint({"Cliente ONG", "Empresa Doadora"})  # RN13, RN15
    chaves_menu = set(re.findall(r"chave:\s*'(\w+)'", ler(JS / "layout.js")))
    for itens in MATRIZ_FUNCIONALIDADES.values():
        assert set(itens) <= chaves_menu


# ------------------------------------------------------------------ uso de api.js
def test_nenhum_js_alem_de_api_js_usa_fetch():
    # RNF04
    com_fetch = [p.name for p in JS.glob("*.js") if p.name != "api.js" and re.search(r"\bfetch\s*\(", ler(p))]
    assert com_fetch == [], com_fetch


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_sem_fetch_nem_xhr_inline(p):
    sem_externos = re.sub(r"<script[^>]+src=[^>]*>\s*</script>", "", ler(p))
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", sem_externos)
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", ler(p)), "script inline"


@pytest.mark.parametrize("p", JS_MODULO)
def test_scripts_do_modulo_sem_fetch_nem_url_da_api(p):
    t = ler(p)
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", t)
    assert "/api/v1" not in t


def test_comum_so_chama_a_api_para_baixar_a_nota():
    # vendas-comum.js e apoio; a unica chamada e o download autenticado (UC17 passo 5)
    chamadas = re.findall(r"Api\.(\w+)\(", _sem_comentarios(ler(JS_COMUM)))
    assert chamadas == ["baixar"]


def test_nenhum_script_do_modulo_grava_token_ou_segredo():
    # RNF05: so api.js lida com a sessao
    for p in JS_MODULO:
        t = _sem_comentarios(ler(p))
        assert "localStorage" not in t and "sessionStorage" not in t and "document.cookie" not in t, p.name


def test_nenhum_script_do_modulo_usa_innerhtml_com_dado_sem_escape_obvio():
    # RNF05: dados da API em innerHTML passam por U.esc / E.escAttr / formatadores
    for p in JS_MODULO:
        t = _sem_comentarios(ler(p))
        assert "eval(" not in t and "document.write" not in t and "new Function" not in t, p.name
        assert "outerHTML = ev" not in t


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
@pytest.mark.parametrize("p", JS_MODULO)
def test_javascript_do_modulo_tem_sintaxe_valida(p):
    # RNF01: node --check
    r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr


# ------------------------------------------------------------------ rotas do contrato (modulo-5.yaml)
def _chamadas(p):
    return [(m, r) for m, r in re.findall(r"Api\.(\w+)\(\s*'([^']*)'", ler(p))]


def test_compras_js_aponta_para_rotas_do_contrato():
    # UC18, UC13 FA1: GET /vendas, GET /vendas/{id}, PUT /vendas/{id}/itens, POST /vendas/{id}/cancelar, GET /catalogo
    t = ler(JS_COM)
    for rota in ("Api.get('/vendas?' + q.join('&'))", "Api.get('/vendas/' + id)", "'/itens', { ids_equipamento: ids }",
                 "'/cancelar')", "Api.get('/catalogo?size=100')"):
        assert rota in t, rota
    assert {m for m, _ in _chamadas(JS_COM)} == {"get", "put", "post"}
    # Cliente Empresa nao confirma, nao ajusta pagamento, nao emite nota
    assert "/confirmar" not in t and "/nota-fiscal" not in t and "Api.patch" not in t


def test_vendas_js_aponta_para_rotas_do_contrato():
    # UC21, UC14, UC15, UC16
    t = ler(JS_VEN)
    for rota in ("Api.get('/vendas?' + q.join('&'))", "Api.get('/vendas/' + id)", "'/confirmar', { data_venda: data, forma_pagamento: forma }",
                 "Api.patch('/vendas/' + estado.venda.id_venda, { forma_pagamento: forma })", "'/itens', { ids_equipamento: ids }",
                 "'/cancelar')", "'/nota-fiscal')"):
        assert rota in t, rota
    assert {m for m, _ in _chamadas(JS_VEN)} <= {"get", "post", "put", "patch"}


def test_notas_js_aponta_para_rotas_do_contrato_e_so_le():
    # UC17: so leitura (a emissao fica em Vendas); download via Api.baixar
    t = ler(JS_NOT)
    assert "Api.get('/notas-fiscais?' + q.join('&'))" in t and "Api.get('/notas-fiscais/' + id)" in t
    assert re.findall(r"Api\.(post|put|patch|delete)\(", t) == []
    assert "/nota-fiscal'" not in t
    assert "Api.baixar('/notas-fiscais/' + idNota + '/download')" in ler(JS_COMUM)


def test_nenhuma_tela_do_modulo_usa_delete_nem_altera_equipamento_direto():
    # Contrato: "Sem outros DELETE"; a venda baixa o estoque no back-end (RN14, UC15), nunca o front
    for p in JS_MODULO:
        t = _sem_comentarios(ler(p))
        assert "Api.delete" not in t, p.name
        assert not re.search(r"Api\.\w+\(\s*'/equipamentos", t), p.name


def test_filtros_do_historico_usam_nomes_dos_parametros_do_contrato():
    # UC21 passo 3, UC17: situacao, id_organizacao_cliente, data_de, data_ate
    t = ler(JS_VEN)
    for p in ("id_organizacao_cliente=", "situacao=", "data_de=", "data_ate="):
        assert p in t, p
    n = ler(JS_NOT)
    for p in ("id_organizacao_cliente=", "data_de=", "data_ate="):
        assert p in n, p
    c = ler(JS_COM)
    assert "situacao=" in c and "id_organizacao_cliente" not in c  # UC18: organizacao e do token (RN15)


# ------------------------------------------------------------------ valores do contrato
def test_formas_e_situacoes_iguais_as_do_contrato():
    # UC14 FE1 (DP-46): valores exatos de FormaPagamento e SituacaoVenda
    t = ler(JS_COMUM)
    formas = re.search(r"var FORMAS = \[(.*?)\];", t).group(1)
    assert re.findall(r"'([^']+)'", formas) == FORMAS
    sit = re.search(r"var SITUACOES = \[(.*?)\];", t).group(1)
    assert re.findall(r"'([^']+)'", sit) == SITUACOES
    y = (RAIZ / "contratos" / "modulo-5.yaml").read_text(encoding="utf-8")
    assert "enum: [Pix, Boleto, Transferência bancária, Cartão de crédito]" in y
    assert "enum: [Pendente, Confirmada, Cancelada]" in y


def test_mensagens_por_codigo_de_erro_do_contrato_em_portugues():
    # UC13 FE1/FE2, UC14 FE1, UC15 FE1, UC16 FE1/FE2, UC17 FE1
    t = ler(JS_COMUM)
    for codigo in ("ITEM_INDISPONIVEL", "CLIENTE_INATIVO", "VENDA_NAO_PENDENTE", "FALHA_ESTOQUE", "VENDA_NAO_CONFIRMADA",
                   "VENDA_INCONSISTENTE", "NAO_ENCONTRADO", "SEM_PERMISSAO"):
        assert re.search(codigo + r":\s*'[^']*[a-záéíóúãõç][^']*'", t), codigo


# ------------------------------------------------------------------ ids de elementos usados pelos scripts
@pytest.mark.parametrize("pagina,js,dinamicos", [
    (PAG_COM, JS_COM, {"btn-alterar", "btn-cancelar"}),  # criados em desenharDetalhe (so Pendente)
    (PAG_VEN, JS_VEN, set()),
    (PAG_NOT, JS_NOT, set()),
])
def test_todo_id_buscado_pelo_script_existe_na_pagina(pagina, js, dinamicos):
    # RNF01: script e HTML consistentes (evita tela quebrada)
    ids = set(re.findall(r'\bid="([^"]+)"', ler(pagina)))
    usados = set(re.findall(r"\$\('([^']+)'\)", ler(js)))
    assert usados - ids - dinamicos == set()


@pytest.mark.parametrize("p", PAGINAS)
def test_ids_da_pagina_nao_se_repetem(p):
    ids = re.findall(r'\bid="([^"]+)"', ler(p))
    assert len(ids) == len(set(ids))


@pytest.mark.parametrize("p", PAGINAS)
def test_campos_de_formulario_tem_label_associada(p):
    # RNF06: cada input/select/textarea com id tem <label for>
    h = ler(p)
    for tipo, i in re.findall(r'<(input|select|textarea)[^>]*\bid="([^"]+)"', h):
        assert f'for="{i}"' in h, f"{p.parent.name}: {tipo}#{i} sem label"


def test_compras_so_oferece_alterar_e_cancelar_enquanto_pendente():
    # UC13 FA1, DP-47: Confirmada/Cancelada somente leitura
    js = ler(JS_COM)
    bloco = js[js.index("function desenharDetalhe"):js.index("async function abrirDetalhe")]
    assert "v.situacao === 'Pendente'" in bloco and "btn-alterar" in bloco and "btn-cancelar" in bloco
    assert "somente leitura" in bloco
    assert "v.nota_fiscal" in bloco and "btn-baixar" in bloco  # UC17 a partir da compra


def test_compras_nega_acesso_a_pedido_de_outra_organizacao_sem_revelar_dados():
    # UC18 FE1, RN04, RNF05
    js = ler(JS_COM)
    assert "err.status === 404" in js and "não pertence à sua organização" in js
    h = ler(PAG_COM)
    assert 'id="filtro-situacao"' in h
    assert "filtro-cliente" not in h  # filtro de organizacao e do historico geral (UC21)


def test_compras_pede_confirmacao_antes_de_cancelar():
    # UC13 FA1: cancelamento e irreversivel (libera os equipamentos)
    h = ler(PAG_COM)
    assert 'id="painel-cancelar"' in h and 'id="btn-confirmar-cancelar"' in h and 'id="btn-desistir-cancelar"' in h


def test_historico_geral_tem_filtros_de_periodo_cliente_e_situacao():
    # UC21 passo 3, RF15
    h = ler(PAG_VEN)
    for i in ("filtro-cliente", "filtro-situacao", "filtro-de", "filtro-ate"):
        assert f'id="{i}"' in h, i
    assert h.count('type="date"') >= 3  # filtros + data da venda
    js = ler(JS_VEN)
    assert "S.validarPeriodo(de, ate)" in js
    assert "Ainda não há vendas registradas" in js and "Nenhuma venda encontrada" in js


def test_vendas_confirmacao_valida_data_e_forma_no_cliente_e_aplica_erros_do_servidor():
    # UC14 passo 3 / FE1, DP-46
    js = ler(JS_VEN)
    bloco = js[js.index("painel-confirmar').addEventListener"):js.index("ajustar forma de pagamento")]
    for trecho in ("Informe a data da venda", "não pode ser futura", "anterior à data do pedido", "Selecione a forma de pagamento",
                   "aplicarCamposDaApi", "FALHA_ESTOQUE" if "FALHA_ESTOQUE" in bloco else "erroNoDetalhe"):
        assert trecho in bloco, trecho
    h = ler(PAG_VEN)
    assert 'id="c-data"' in h and 'id="c-forma"' in h and 'id="btn-confirmar-venda"' in h


def test_vendas_acoes_do_pedido_pendente_e_so_pendente():
    # UC14 FA1, FA2: confirmar, ajustar pagamento, trocar itens, cancelar
    js = ler(JS_VEN)
    bloco = js[js.index("function desenharDetalhe"):js.index("async function abrirDetalhe")]
    pend = bloco[bloco.index("v.situacao === 'Pendente'"):bloco.index("v.situacao === 'Confirmada'")]
    for ac in ("confirmar", "pagamento", "itens", "cancelar"):
        assert f'data-ac="{ac}"' in pend, ac
    assert "nota" not in pend.replace("Nota", "")  # nao emite nota de pedido pendente (UC16 FE1)


def test_vendas_emissao_de_nota_so_para_administrador_e_venda_confirmada():
    # UC16, RN19: Funcionario nao emite
    js = ler(JS_VEN)
    bloco = js[js.index("function desenharDetalhe"):js.index("async function abrirDetalhe")]
    conf = bloco[bloco.index("v.situacao === 'Confirmada'"):]
    assert "estado.admin && !v.nota_fiscal" in conf and 'data-ac="nota"' in conf
    assert "estado.admin && v.nota_fiscal" in conf and 'data-ac="baixar"' in conf  # FA1: mostra a existente
    assert "estado.admin = usuario.perfil === 'Administrador'" in js
    assert "emitida pelo Administrador" in conf


def test_vendas_funcionario_nao_recebe_link_para_a_tela_de_notas():
    # RN20: Funcionario nao consulta notas -> detalhe sem link (semLinkNota)
    assert "V.detalheHtml(v, true, !estado.admin)" in ler(JS_VEN)
    comum = ler(JS_COMUM)
    assert "semLinkNota" in comum and "notas-fiscais/index.html?id=" in comum


def test_vendas_erros_de_itens_indisponiveis_apontam_os_ids_e_marcam_a_tela():
    # UC14 FE1, UC13 FE1
    js = ler(JS_VEN)
    assert "V.idsIndisponiveis(err)" in js and "V.marcarIndisponiveis(" in js
    assert "atualizarAposErro" in js and "VENDA_NAO_PENDENTE" in js


def test_vendas_pede_confirmacao_para_cancelar_e_para_emitir_nota():
    # UC14 FA2, UC16 passo 3
    h = ler(PAG_VEN)
    for i in ("painel-cancelar", "btn-confirmar-cancelar", "painel-nota", "btn-confirmar-nota", "painel-pagamento", "painel-editor"):
        assert f'id="{i}"' in h, i


def test_notas_tela_diferencia_administrador_de_cliente_e_trata_404():
    # UC17 passo 2, FE1, RN20
    js = ler(JS_NOT)
    assert "estado.admin = usuario.perfil === 'Administrador'" in js
    assert "bloco-filtro-cliente" in js and "Minhas notas fiscais" in js
    assert "err.status === 404" in js and "não está vinculada a você" in js
    h = ler(PAG_NOT)
    assert 'id="bloco-filtro-cliente"' in h and "SIMULADA" in h and "valor fiscal" in h  # aviso fixo (DP-49)
    assert 'id="btn-baixar"' in h


def test_download_usa_api_baixar_e_nao_link_direto_sem_token():
    # UC17 passo 5, RNF05: o arquivo exige Authorization, entao nao pode ser <a href> para a API
    comum = _sem_comentarios(ler(JS_COMUM))
    assert "Api.baixar(" in comum and "URL.createObjectURL" in comum and "a.download" in comum
    for p in PAGINAS:
        assert "/download" not in re.sub(r"<!--.*?-->", "", ler(p), flags=re.S)
    api = ler(JS / "api.js")
    assert "baixar:" in api and "Authorization" in api and "blob" in api


# ------------------------------------------------------------------ comportamento dos auxiliares (executa vendas-comum.js no node)
_NODE_SCRIPT = r"""
const fs = require('fs'), vm = require('vm');
const base = process.argv[2];
const elementos = () => { let t = ''; return {
  set textContent(v) { t = String(v); },
  get innerHTML() { return t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'); } }; };
const ctx = { console, document: { addEventListener() {}, createElement: elementos } };
ctx.window = ctx;
vm.createContext(ctx);
for (const f of ['usuarios-comum.js', 'equipamentos-comum.js', 'solicitacoes-comum.js', 'vendas-comum.js'])
  vm.runInContext(fs.readFileSync(base + '/' + f, 'utf8'), ctx, { filename: f });
const V = ctx.VendasUi;
const venda = { id_venda: 7, nome_organizacao: '<img src=x onerror=1>', data_venda: '2026-10-31', situacao: 'Pendente',
  forma_pagamento: 'A definir', quantidade: 1, valor_total: 10, possui_nota: true, nota_fiscal: { id_nota: 3, numero: 'NFS-2026-000001', data_emissao: '2026-10-31' },
  itens: [{ id_equipamento: 5, identificacao: '<b>ID</b>', modelo: '"M"', categoria_nome: 'Cat', condicao: 'Bom', valor: 10 }] };
console.log(JSON.stringify({
  ids: V.idsIndisponiveis({ campos: { ids_equipamento: 'indisponíveis: 12, 15' } }),
  idsVazio: V.idsIndisponiveis({ campos: {} }),
  idsSemErro: V.idsIndisponiveis(null),
  lerIds: V.lerIds('1, 2;3  x 0 -4 1.5 99999999999999999999'),
  msgApi: V.msgErro({ codigo: 'ITEM_INDISPONIVEL', mensagem: 'da API' }),
  msgLocal: V.msgErro({ codigo: 'FALHA_ESTOQUE' }),
  msgDesconhecida: V.msgErro({ codigo: 'XYZ' }),
  linha: V.linhaVenda(venda, true),
  linhaSemCliente: V.linhaVenda(venda, false),
  detalhe: V.detalheHtml(venda, true, false),
  detalheSemLink: V.detalheHtml(venda, true, true),
  selo: V.seloVenda('Confirmada'),
  formas: V.FORMAS, situacoes: V.SITUACOES
}));
"""


@pytest.fixture(scope="module")
def saida_node(tmp_path_factory):
    if shutil.which("node") is None:
        pytest.skip("node nao instalado")
    script = tmp_path_factory.mktemp("node") / "rodar.js"
    script.write_text(_NODE_SCRIPT, encoding="utf-8")
    r = subprocess.run(["node", str(script), str(JS)], capture_output=True, text=True, timeout=60, encoding="utf-8")
    assert r.returncode == 0, r.stderr
    return json.loads(r.stdout)


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_ids_indisponiveis_e_leitura_de_ids_digitados(saida_node):
    # UC13 FE1, UC14 FA1 (RNF04: ids positivos de ate 18 digitos, sem texto)
    assert saida_node["ids"] == [12, 15] and saida_node["idsVazio"] == [] and saida_node["idsSemErro"] == []
    assert saida_node["lerIds"] == {"ids": [1, 2, 3], "invalidos": ["x", "0", "-4", "1.5", "99999999999999999999"]}


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_mensagens_de_erro_preferem_a_da_api_e_caem_para_o_texto_local(saida_node):
    # UC13 FE1, UC15 FE1
    assert saida_node["msgApi"] == "da API"
    assert "estoque" in saida_node["msgLocal"].lower()
    assert saida_node["msgDesconhecida"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_tabelas_e_detalhe_escapam_dados_da_api(saida_node):
    # RNF05: nome da organizacao, identificacao e modelo vindos da API nao viram HTML
    for chave in ("linha", "detalhe", "detalheSemLink"):
        t = saida_node[chave]
        assert "<img src=x" not in t, chave
    assert "&lt;img src=x onerror=1&gt;" in saida_node["linha"]
    assert "&lt;b&gt;ID&lt;/b&gt;" in saida_node["detalhe"]
    assert "<b>ID</b>" not in saida_node["detalhe"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_linha_do_historico_mostra_data_formatada_nota_e_botao_de_detalhe(saida_node):
    # UC18 passo 3, UC21 passo 4
    t = saida_node["linha"]
    assert "31/10/2026" in t and "Emitida" in t and 'data-acao="ver"' in t and 'data-id="7"' in t and "R$" in t
    assert "Empresa" not in saida_node["linhaSemCliente"] and saida_node["linhaSemCliente"].count("<td") == saida_node["linha"].count("<td") - 1


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_detalhe_link_da_nota_so_quando_permitido(saida_node):
    # UC17, RN20: com link para o Administrador/Cliente; sem link para o Funcionario
    assert "../notas-fiscais/index.html?id=3" in saida_node["detalhe"]
    assert "../notas-fiscais/index.html" not in saida_node["detalheSemLink"] and "NFS-2026-000001" in saida_node["detalheSemLink"]
    assert "A definir" in saida_node["detalhe"] and "Quantidade: 1 item" in saida_node["detalhe"]


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_selo_de_situacao_tem_texto_alem_da_cor(saida_node):
    # RNF06: nunca so cor
    assert "Confirmada" in saida_node["selo"] and "✔" in saida_node["selo"]
    assert saida_node["formas"] == FORMAS and saida_node["situacoes"] == SITUACOES
