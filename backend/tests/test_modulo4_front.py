"""Modulo 4 - front estatico (leitura dos arquivos; nao toca no front). UC09, UC10, UC11, UC19, UC20;
RF04, RF05, RF10, RF12, RF21; RN04, RN05, RN10, RN11, RN12, RN15, RN21; RNF01, RNF04, RNF05, RNF06; DP-40 a DP-44."""
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
PAG_SOL = FRONT / "app" / "solicitacoes" / "index.html"
PAG_AVA = FRONT / "app" / "avaliacao" / "index.html"
PAG_DOA = FRONT / "app" / "doacoes" / "index.html"
JS_SOL = JS / "solicitacoes.js"
JS_AVA = JS / "avaliacao.js"
JS_DOA = JS / "doacoes.js"
JS_COMUM = JS / "solicitacoes-comum.js"
JS_MODULO = [JS_SOL, JS_AVA, JS_DOA, JS_COMUM]
CSS_NOVO = CSS / "solicitacoes.css"
PAGINAS = [PAG_SOL, PAG_AVA, PAG_DOA]
PAR_PAGINA_JS = [(PAG_SOL, JS_SOL), (PAG_AVA, JS_AVA), (PAG_DOA, JS_DOA)]

SITUACOES_SOL = ["Aguardando avaliação", "Em avaliação", "Avaliada"]
DESTINACOES = ["Venda", "Doação", "Reciclagem"]


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


def _sem_comentarios(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


# ------------------------------------------------------------------ existencia e comentarios UC/RN
@pytest.mark.parametrize("p", PAGINAS + JS_MODULO + [CSS_NOVO])
def test_telas_scripts_e_css_do_modulo_existem(p):
    # UC09, UC10, UC11, UC19, UC20
    assert p.is_file()


@pytest.mark.parametrize("p,ucs", [
    (PAG_SOL, ["UC09", "UC20"]), (PAG_AVA, ["UC10", "UC11"]), (PAG_DOA, ["UC19"]),
    (JS_SOL, ["UC09", "UC20"]), (JS_AVA, ["UC10", "UC11"]), (JS_DOA, ["UC19"]),
    (JS_COMUM, ["UC09", "UC10", "UC11", "UC19", "UC20"]), (CSS_NOVO, ["UC09", "UC10", "UC11", "UC19", "UC20"]),
])
def test_arquivos_citam_uc_no_comentario_inicial(p, ucs):
    # CLAUDE.md: toda tela cita UC e RN no comentario
    inicio = ler(p)[:1800]
    for uc in ucs:
        assert uc in inicio, f"{p.name} sem {uc}"
    if p.suffix != ".css":
        assert re.search(r"\bRN\d+", inicio), f"{p.name} sem RN"


@pytest.mark.parametrize("p,rns", [
    (PAG_SOL, ["RN05", "RN10", "RN21"]), (JS_SOL, ["RN05", "RN10", "RN21"]),
    (PAG_AVA, ["RN03", "RN11", "RN12", "RN21"]), (JS_AVA, ["RN03", "RN11", "RN12", "RN21"]),
    (PAG_DOA, ["RN04", "RN12", "RN15"]), (JS_DOA, ["RN04", "RN12", "RN15"]),
])
def test_rns_do_modulo_citadas(p, rns):
    # UC09, UC10, UC19
    inicio = ler(p)[:1800]
    for rn in rns:
        assert rn in inicio, f"{p.name} sem {rn}"


@pytest.mark.parametrize("p", [PAG_SOL, PAG_AVA, PAG_DOA, JS_SOL, JS_AVA, JS_DOA])
def test_decisoes_dp_citadas(p):
    # CLAUDE.md: decisoes referenciadas
    assert re.search(r"DP-4[0-4]", ler(p)[:1800]), p.name


def test_paginas_carregam_scripts_na_ordem():
    # UC09, UC10, UC19 (guarda de rota via Layout, RNF05)
    esperado = ["api.js", "layout.js", "usuarios-comum.js", "equipamentos-comum.js", "solicitacoes-comum.js"]
    for pagina, js in PAR_PAGINA_JS:
        srcs = [s.split("/")[-1] for s in re.findall(r'<script[^>]+src="([^"]+)"', ler(pagina)) if not s.startswith("http")]
        assert srcs == esperado + [js.name], (pagina.name, srcs)


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_carregam_a_folha_do_modulo_e_bootstrap(p):
    # RNF01
    h = ler(p)
    assert "solicitacoes.css" in h and "bootstrap@5" in h


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_sao_responsivas_e_em_portugues(p):
    # RNF01
    h = ler(p)
    assert 'lang="pt-BR"' in h and 'name="viewport"' in h


def test_paginas_usam_layout_iniciar_com_a_chave_do_menu():
    # RN01, RNF05: a tela Minhas solicitacoes pede `minhas_solicitacoes`; avaliacao pede `solicitacoes`
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'minhas_solicitacoes'", ler(JS_SOL))
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'solicitacoes'", ler(JS_AVA))
    assert "'minhas_doacoes'" in ler(JS_DOA) and "Layout.iniciar(" in ler(JS_DOA)


# ------------------------------------------------------------------ uso de api.js
def test_nenhum_js_alem_de_api_js_usa_fetch():
    # RNF04
    com_fetch = [p.name for p in JS.glob("*.js") if p.name != "api.js" and re.search(r"\bfetch\s*\(", ler(p))]
    assert com_fetch == [], com_fetch


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_sem_fetch_nem_xhr_inline(p):
    sem_externos = re.sub(r"<script[^>]+src=[^>]*>\s*</script>", "", ler(p))
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", sem_externos)


@pytest.mark.parametrize("p", JS_MODULO)
def test_scripts_do_modulo_sem_fetch_nem_url_da_api(p):
    t = ler(p)
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", t)
    assert "/api/v1" not in t


def test_comum_nao_chama_a_api():
    # solicitacoes-comum.js e so de apoio (selos, tabelas, validacao)
    assert "Api." not in _sem_comentarios(ler(JS_COMUM))


def test_nenhum_script_do_modulo_grava_token_ou_segredo():
    # RNF05: so api.js lida com a sessao
    for p in JS_MODULO:
        t = _sem_comentarios(ler(p))
        assert "localStorage" not in t and "sessionStorage" not in t, p.name


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
@pytest.mark.parametrize("p", JS_MODULO)
def test_javascript_do_modulo_tem_sintaxe_valida(p):
    # RNF01: node --check
    r = subprocess.run(["node", "--check", str(p)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr


# ------------------------------------------------------------------ rotas do contrato
def test_solicitacoes_js_aponta_para_rotas_do_contrato():
    # UC09, UC20: so as rotas de GET/POST /solicitacoes e GET /solicitacoes/{id}
    t = ler(JS_SOL)
    for rota in ("Api.get('/solicitacoes?'", "Api.get('/solicitacoes/' + id)", "Api.post('/solicitacoes', { itens: v.itens })"):
        assert rota in t, rota
    chamadas = re.findall(r"Api\.(\w+)\(\s*'([^']*)'", t)
    assert {m for m, _ in chamadas} == {"get", "post"}
    assert all(r.startswith("/solicitacoes") for _, r in chamadas)


def test_avaliacao_js_aponta_para_rotas_do_contrato():
    # UC10, UC11
    t = ler(JS_AVA)
    for rota in ("Api.get('/solicitacoes?'", "Api.get('/solicitacoes/' + id)", "Api.get('/solicitacoes/' + estado.sol.id_solicitacao)",
                 "'/itens/' + item.id_item_solicitacao + '/equipamentos', corpo", "'/destinacao', corpo",
                 "Api.get('/doacoes/ongs-elegiveis')", "Api.get('/categorias?size=100')", "Api.get('/organizacoes?tipo='"):
        assert rota in t, rota
    assert "Api.post('/solicitacoes/' + solId + '/itens/'" in t
    assert "Api.put('/solicitacoes/' + solId + '/equipamentos/' + eq.id_equipamento + '/destinacao', corpo)" in t


def test_doacoes_js_aponta_para_rotas_do_contrato_e_so_le():
    # UC19, DP-44: somente leitura
    t = ler(JS_DOA)
    assert "Api.get('/doacoes?'" in t and "Api.get('/doacoes/' + id)" in t
    assert re.findall(r"Api\.(post|put|patch|delete)\(", t) == []


def test_nenhuma_tela_do_modulo_altera_equipamento_pelo_modulo_3():
    # UC10 FA2: recondicionamento e feito na tela de Equipamentos, nao aqui
    for p in (JS_SOL, JS_AVA, JS_DOA):
        assert not re.search(r"Api\.\w+\(\s*'/equipamentos", ler(p)) and "Api.patch" not in ler(p) and "Api.delete" not in ler(p), p.name


def test_corpos_usam_nomes_das_colunas_do_banco():
    # convencoes: nomes de campos iguais as colunas
    t = ler(JS_AVA)
    corpo = t[t.index("var corpo = { identificacao"):t.index("if (u.origem.value.trim())")]
    for campo in ("identificacao", "id_categoria", "condicao", "data_recebimento", "situacao"):
        assert campo + ":" in corpo, campo
    assert "organizacao" not in corpo
    assert "corpo.id_organizacao_ong" in t and "corpo.data_doacao" in t
    assert t.count("corpo.id_organizacao_ong") == 1  # so no ramo Doacao
    assert "{ itens: v.itens }" in ler(JS_SOL) and "id_organizacao_doadora" not in ler(JS_SOL)  # organizacao vem do token (RN05)


def test_corpo_da_unidade_nao_envia_modelo_nem_item():
    # UC10 passo 3 (DP-41): `modelo` vem do item no back-end
    t = ler(JS_AVA)
    corpo = t[t.index("var corpo = { identificacao"):t.index("if (u.origem.value.trim())")]
    assert "modelo" not in corpo and "id_item_solicitacao" not in corpo


def test_ong_e_data_so_no_ramo_doacao():
    # UC11 passo 3, contrato DestinacaoEntrada
    t = ler(JS_AVA)
    ramo = t[t.index("var corpo = { destinacao: sel.value };"):t.index("var btn = $('btn-salvar-dest')")]
    assert "if (sel.value === 'Doação')" in ramo
    assert ramo.index("corpo.id_organizacao_ong") > ramo.index("if (sel.value === 'Doação')")


# ------------------------------------------------------------------ valores do contrato
def _lista_js(nome):
    m = re.search(r"var " + nome + r" = \[(.*?)\];", ler(JS_COMUM), re.S)
    assert m, nome
    return re.findall(r"'([^']*)'", m.group(1))


def test_situacoes_e_destinacoes_do_front_sao_as_do_contrato():
    # DP-40, DP-42, contrato SituacaoSolicitacao e Destinacao
    assert _lista_js("SITUACOES") == SITUACOES_SOL
    assert _lista_js("DESTINACOES") == DESTINACOES


def test_valores_do_front_coincidem_com_o_yaml():
    # contrato modulo-4.yaml
    y = ler(RAIZ / "contratos" / "modulo-4.yaml")
    sit = re.search(r"SituacaoSolicitacao:\s*\n\s*type: string\s*\n\s*enum: \[(.*?)\]", y).group(1)
    des = re.search(r"Destinacao:\s*\n\s*type: string\s*\n\s*enum: \[(.*?)\]", y).group(1)
    assert [x.strip() for x in sit.split(",")] == SITUACOES_SOL
    assert [x.strip() for x in des.split(",")] == DESTINACOES


def test_situacao_inicial_da_unidade_so_oferece_as_tres_do_contrato():
    # UC10 passo 3, contrato AvaliacaoEntrada.situacao
    t = ler(JS_AVA)
    assert "['Recebido', 'Em avaliação', 'Em manutenção'].forEach" in t
    assert "Disponível" not in t[t.index("['Recebido', 'Em avaliação', 'Em manutenção']"):][:200]


def test_condicoes_vem_da_lista_do_modulo_3():
    # UC10 passo 3: mesmas condicoes do M3 (DP-32)
    assert "E.CONDICOES.forEach" in ler(JS_AVA)


# ------------------------------------------------------------------ mensagens por codigo de erro do contrato (UC09 FE2/FE3, UC10, UC11)
@pytest.mark.parametrize("codigo", ["ORGANIZACAO_INATIVA", "PARCERIA_INATIVA", "ITEM_COMPLETO", "SEM_CONDICOES_DE_REUSO",
                                    "TRANSICAO_INVALIDA", "EQUIPAMENTO_INATIVO", "EQUIPAMENTO_FINALIZADO", "DOACAO_INVALIDA",
                                    "CATEGORIA_INVALIDA", "IDENTIFICACAO_DUPLICADA", "NAO_ENCONTRADO"])
def test_front_tem_mensagem_em_portugues_para_cada_erro_do_contrato(codigo):
    # UC09 FE2/FE3, UC10 FE1, UC11 FE1/FE2
    t = ler(JS_COMUM)
    assert re.search(r"\b" + codigo + r":\s*'[^']*[a-zà-ú]", t), codigo


def test_mensagem_de_parceria_igual_a_do_contrato():
    # UC09 FE3: "precisa de vinculo de parceria ativo"
    assert "A Empresa Doadora precisa de vínculo de parceria ativo para solicitar avaliação." in ler(JS_COMUM)


def test_mensagem_da_api_tem_prioridade_sobre_a_local():
    # convencoes: mensagens da API (portugues) primeiro
    t = ler(JS_COMUM)
    assert "(err && err.mensagem) || MSG[err && err.codigo]" in t


# ------------------------------------------------------------------ UC09: tela Nova solicitacao
def test_nova_solicitacao_tem_validacao_do_cliente_igual_ao_contrato():
    # UC09 FE1, DP-43, RNF04: tipo/modelo 1-100, quantidade 1-9999, ate 50 itens
    t = ler(JS_SOL)
    assert "MAX_ITENS = 50" in t
    assert t.count('maxlength="100"') >= 2
    assert 'min="1" max="9999"' in t
    assert "Number(q) < 1 || Number(q) > 9999" in t
    assert "t.length > 100" in t and "m.length > 100" in t
    assert "Informe o tipo do equipamento." in t and "Informe o modelo do equipamento." in t and "Informe a quantidade." in t


def test_nova_solicitacao_nao_envia_se_ha_erro_e_avisa():
    # UC09 FE1: nao registra e pede correcao
    t = ler(JS_SOL)
    sub = t[t.index("$('form-nova').addEventListener('submit'"):]
    assert sub.index("if (v.erros)") < sub.index("Api.post(")
    assert "A solicitação ainda não foi registrada." in sub
    assert "return;" in sub[sub.index("if (v.erros)"):sub.index("Api.post(")]


def test_nova_solicitacao_trata_fe2_e_fe3_sem_registrar():
    # UC09 FE2, FE3: erro da API aparece e informa que nada foi registrado
    t = ler(JS_SOL)
    assert "ORGANIZACAO_INATIVA" in t and "PARCERIA_INATIVA" in t
    assert "A solicitação não foi registrada." in t


def test_botao_de_enviar_evita_duplo_envio():
    # UC09 (idempotencia no cliente)
    t = ler(JS_SOL)
    assert "btn.disabled = true" in t and "btn.disabled = false" in t


def test_pagina_de_solicitacoes_informa_que_nao_edita_nem_cancela_e_nao_disponibiliza():
    # DP-43, RN21
    h = ler(PAG_SOL)
    assert "não pode ser editada nem cancelada" in h
    assert "não coloca nada à venda nem em doação" in h


@pytest.mark.parametrize("id_", ["form-nova", "itens-form", "btn-add-item", "btn-enviar", "btn-cancelar-nova", "btn-nova",
                                 "vista-lista", "vista-nova", "vista-detalhe", "itens-detalhe", "aviso-detalhe", "cab-detalhe",
                                 "filtro-situacao", "filtro-de", "filtro-ate", "form-filtros"])
def test_pagina_de_solicitacoes_tem_os_elementos(id_):
    # UC09, UC20
    assert f'id="{id_}"' in ler(PAG_SOL)


def test_filtros_da_empresa_nao_enviam_organizacao():
    # UC20, RN04, RN05: a empresa nao escolhe organizacao (a API ignora e o isolamento e do back-end)
    assert "id_organizacao_doadora" not in ler(JS_SOL)
    assert 'id="filtro-org"' not in ler(PAG_SOL)


# ------------------------------------------------------------------ UC20: somente leitura, sem valor, FA1 e FE1
def test_empresa_doadora_ve_detalhe_sem_valor_nem_acoes():
    # UC20 passo 3, contrato (valor omitido para Empresa Doadora)
    t = ler(JS_SOL)
    assert "S.cartaoItem(it, i, {})" in t
    assert "valor: true" not in t and "acoes:" not in t and "rodape:" not in t
    assert not re.search(r"data-acao=\"(unidade|destinar)\"", t)


def test_comum_so_mostra_coluna_valor_quando_a_opcao_e_passada():
    # UC20: a coluna Valor e opcional
    t = ler(JS_COMUM)
    assert "opcoes.valor ? '<th scope=\"col\">Valor</th>' : ''" in t
    assert "opcoes.acoes ? '<th scope=\"col\">Ações</th>' : ''" in t


def test_tela_da_leaf_mostra_valor_e_acoes():
    # UC10 passo 3-4
    t = ler(JS_AVA)
    assert "{ valor: true, acoes: acoesEquipamento, rodape: rodapeItem }" in t


def test_uc20_fa1_pendente_sem_inventar_avaliacao():
    # UC20 FA1
    t = ler(JS_SOL)
    assert "sol.situacao === 'Aguardando avaliação'" in t
    assert "Ainda não há condição avaliada nem destinação registrada" in t
    c = ler(JS_COMUM)
    assert "Nenhuma unidade deste item foi avaliada ainda." in c
    assert "Pendente" in c and "Ainda não avaliada" in t


def test_uc20_fe1_mensagem_de_acesso_negado_sem_revelar_existencia():
    # UC20 FE1: 404 -> "nao existe ou nao pertence"
    t = ler(JS_SOL)
    assert "err.status === 404" in t and "não pertence à sua organização" in t


def test_destinacao_sem_registro_aparece_como_pendente():
    # UC20 passo 3, FA1
    c = ler(JS_COMUM)
    assert "if (!d) { return '<span class=\"selo-situacao selo-dest-pendente\">" in c


def test_selos_tem_texto_e_icone_nunca_so_cor():
    # RNF06
    c = ler(JS_COMUM)
    for icone in ("'○'", "'◐'", "'✔'", "'◆'", "'♥'", "'♻'"):
        assert icone in c, icone
    assert "esc(s)" in c and "esc(d)" in c


def test_doacao_mostra_ong_e_data_no_resultado():
    # UC20 passo 3, UC11
    c = ler(JS_COMUM)
    assert "ONG: " in c and "eq.nome_ong" in c and "eq.data_doacao" in c


def test_pendencias_vem_da_api():
    # UC10 FE2: texto da API, nada inventado
    c = ler(JS_COMUM)
    assert "sol.pendencias" in c and "Pendências para concluir a avaliação" in c


# ------------------------------------------------------------------ UC10 / UC11: tela de avaliacao
def test_avaliacao_trata_item_completo_e_atualiza_o_detalhe():
    # UC10 passo 3 (DP-41), contrato ITEM_COMPLETO
    t = ler(JS_AVA)
    assert "ITEM_COMPLETO" in t
    assert "(item.quantidade_cadastrada || 0) >= item.quantidade" in t  # esconde "Cadastrar unidade" quando completo


def test_avaliacao_tem_acoes_apenas_cadastrar_unidade_e_destinar():
    # UC10 passos 3-5
    assert set(re.findall(r'data-acao="(\w+)"', ler(JS_AVA))) == {"abrir", "unidade", "destinar"}


def test_destinacao_oferece_exatamente_venda_doacao_reciclagem():
    # UC10 passo 4, DP-42
    t = ler(JS_AVA)
    for rotulo in ("'Venda':", "'Doação':", "'Reciclagem':"):
        assert rotulo in t
    assert "S.DESTINACOES.map" in t


def test_sem_reuso_so_permite_reciclagem_na_tela():
    # UC10 FE1, UC11 FE2, RN11, RN12, RN21 (conveniencia; a API valida)
    t = ler(JS_AVA)
    bloco = t[t.index("function destinacoesPermitidas"):t.index("var DESC_DEST")]
    assert "E.SEM_REUSO" in bloco and "só pode ser destinado à reciclagem" in bloco
    assert "'Reciclagem': null" in bloco  # reciclagem nunca e bloqueada
    assert "'Doação': motivoReuso" in bloco and "'Venda': motivoReuso" in bloco


def test_tela_bloqueia_venda_sem_valor_e_inativo():
    # RN12 (inativos), DP-35 (valor > 0)
    t = ler(JS_AVA)
    bloco = t[t.index("function destinacoesPermitidas"):t.index("var DESC_DEST")]
    assert "eq.ativo === false" in bloco and "Number(eq.valor) > 0" in bloco and "'A avaliar'" in bloco


def test_equipamento_em_situacao_final_nao_tem_acao():
    # RN12: vendido, doado e reciclagem sao finais
    t = ler(JS_AVA)
    assert "var FINAIS = ['Vendido', 'Doado', 'Destinado à reciclagem']" in t
    assert "Situação final: sem ações" in t


def test_doacao_pede_ong_elegivel_e_data_e_valida_no_cliente():
    # UC11 passos 2-3, FE1, RN12
    t = ler(JS_AVA)
    assert "Api.get('/doacoes/ongs-elegiveis')" in t
    assert "Selecione a ONG beneficiária." in t and "Informe a data da doação." in t
    assert "A data da doação não pode ser futura." in t
    assert "A data da doação não pode ser anterior ao recebimento" in t
    h = ler(PAG_AVA)
    assert 'id="d-ong"' in h and 'id="d-data"' in h and 'id="bloco-doacao"' in h


def test_doacao_sem_ong_ativa_avisa_uc11_fe1():
    # UC11 FE1
    t = ler(JS_AVA)
    assert "Nenhuma ONG ativa disponível" in t and "Não há ONG ativa cadastrada" in t


def test_destinacao_nao_e_enviada_se_validacao_da_doacao_falha():
    # UC11 FE1: nao conclui a destinacao
    t = ler(JS_AVA)
    sub = t[t.index("$('form-dest').addEventListener('submit'"):]
    assert sub.index("if (erros)") < sub.index("Api.put(")
    assert "A destinação não foi registrada." in sub


def test_avaliacao_valida_o_formulario_da_unidade_com_as_regras_do_modulo_3():
    # UC10 passo 3 (reuso das regras UC07 FE1, RN12)
    t = ler(JS_AVA)
    assert "E.validarEquipamento(v, { criando: true })" in t
    assert "A unidade não foi cadastrada." in t


def test_avaliacao_mostra_a_empresa_na_lista_e_filtra_por_empresa():
    # UC10 passo 1
    t = ler(JS_AVA)
    assert "Empresa Doadora" in t and "id_organizacao_doadora=" in t
    assert 'id="filtro-org"' in ler(PAG_AVA)


def test_avaliacao_botoes_de_acao_tem_aria_label():
    # RNF06
    t = ler(JS_AVA)
    assert "aria-label=\"' + (eq.destinacao ? 'Alterar' : 'Definir')" in t
    assert "aria-label=\"Cadastrar unidade do item" in t


def test_avaliacao_modais_acessiveis():
    # RNF06
    h = ler(PAG_AVA)
    for m in ("modal-unidade", "modal-dest"):
        assert re.search(r'id="' + m + r'"[^>]*aria-labelledby="' + m + r'-titulo"', h)
        assert 'id="' + m + '-titulo"' in h
    assert 'role="radiogroup"' in h or "<fieldset" in h


def test_avaliacao_envia_destinacao_somente_com_clique_no_formulario():
    # UC10 passo 4-7: nada e enviado ao abrir o modal
    t = ler(JS_AVA)
    abrir = t[t.index("function abrirDestinacao"):t.index("$('dest-opcoes').addEventListener('change'")]
    assert "Api." not in abrir and "modalDest.show()" in abrir


# ------------------------------------------------------------------ UC19: tela de doacoes
def test_doacoes_fa1_lista_vazia_tem_mensagem():
    # UC19 FA1
    assert "Ainda não há doações ou equipamentos destinados" in ler(JS_DOA)


def test_doacoes_fe1_mensagem_de_acesso_negado():
    # UC19 FE1
    t = ler(JS_DOA)
    assert "err.status === 404" in t and "não pertence à sua ONG" in t


def test_doacoes_mostra_equipamento_situacao_e_data():
    # UC19 passo 3
    t = ler(JS_DOA)
    for campo in ("d.identificacao", "d.situacao", "d.data_doacao", "d.condicao"):
        assert campo in t
    for coluna in ("Equipamento", "Situação", "Data da doação"):
        assert coluna in t


def test_doacoes_cliente_ong_nao_envia_filtro_de_ong():
    # UC19, RN04, RN15: filtro de ONG so na visao interna
    t = ler(JS_DOA)
    assert "estado.interno && fl.ong" in t


def test_doacoes_visao_interna_so_para_admin_e_funcionario():
    # UC19 (visao interna), RN15
    t = ler(JS_DOA)
    assert "perfil0 === 'Administrador' || perfil0 === 'Funcionário'" in t
    assert "id-ong" not in t  # sem ids soltos
    assert 'id="bloco-filtro-ong" hidden' in ler(PAG_DOA).replace("\n", " ") or "bloco-filtro-ong" in ler(PAG_DOA)


def test_doacoes_link_para_solicitacao_de_origem_so_na_visao_interna():
    # UC19, UC10
    t = ler(JS_DOA)
    assert "estado.interno && d.id_solicitacao" in t and "../avaliacao/index.html?id=" in t


@pytest.mark.parametrize("id_", ["vista-lista", "vista-detalhe", "form-filtros", "filtro-de", "filtro-ate", "tabela", "corpo-tabela",
                                 "cab-tabela", "vazio-lista", "btn-voltar", "corpo-detalhe", "paginacao"])
def test_pagina_de_doacoes_tem_os_elementos(id_):
    # UC19
    assert f'id="{id_}"' in ler(PAG_DOA)


def test_doacoes_nao_tem_botoes_de_escrita():
    # DP-44: somente leitura
    h = _sem_comentarios(ler(PAG_DOA))
    assert not re.search(r'type="submit"[^>]*>\s*(Salvar|Registrar|Excluir|Cadastrar)', h)
    assert "form-doacao" not in h


# ------------------------------------------------------------------ elementos referenciados pelo JS existem no HTML
def _ids_usados(js: str):
    return set(re.findall(r"\$\('([\w-]+)'\)", js))


@pytest.mark.parametrize("pagina,js", PAR_PAGINA_JS)
def test_todo_id_usado_no_js_existe_na_pagina(pagina, js):
    # UC09, UC10, UC19: evita tela quebrada por id ausente
    h = ler(pagina)
    ausentes = sorted(i for i in _ids_usados(ler(js)) if f'id="{i}"' not in h)
    assert ausentes == [], ausentes


@pytest.mark.parametrize("pagina", PAGINAS)
def test_ids_da_pagina_sao_unicos(pagina):
    ids = re.findall(r'\bid="([^"]+)"', _sem_comentarios(ler(pagina)))
    repetidos = sorted({i for i in ids if ids.count(i) > 1})
    assert repetidos == [], repetidos


@pytest.mark.parametrize("pagina", PAGINAS)
def test_campos_do_formulario_tem_rotulo(pagina):
    # RNF06: todo input/select visivel tem <label for>
    h = _sem_comentarios(ler(pagina))
    for m in re.finditer(r"<(input|select|textarea)\b[^>]*\bid=\"([^\"]+)\"[^>]*>", h):
        if 'type="radio"' in m.group(0):
            continue
        assert re.search(r'<label[^>]*\bfor="' + re.escape(m.group(2)) + '"', h), m.group(2)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_paginas_tem_um_h1_por_vista_e_regioes_aria_live(pagina):
    # RNF06
    h = _sem_comentarios(ler(pagina))
    assert h.count("<h1") >= 2
    assert 'aria-live="polite"' in h


def test_formularios_usam_novalidate_para_mensagens_proprias_em_portugues():
    # RNF06: mensagens do sistema em portugues, nao as do navegador
    for p in PAGINAS:
        for f in re.findall(r"<form\b[^>]*>", ler(p)):
            assert "novalidate" in f, (p.name, f)


# ------------------------------------------------------------------ menu e matriz (RN01, RN03, RN04, RN05)
def _item_menu(chave):
    m = re.search(r"\{\s*chave:\s*'" + chave + r"'[^}]*\}", ler(JS / "layout.js"))
    assert m, f"item {chave} ausente do MENU"
    return m.group(0)


@pytest.mark.parametrize("chave,href", [("minhas_doacoes", "doacoes/index.html"),
                                        ("minhas_solicitacoes", "solicitacoes/index.html"),
                                        ("solicitacoes", "avaliacao/index.html")])
def test_itens_do_menu_ligados_as_paginas(chave, href):
    # UC09, UC10, UC19, UC20, RN01
    assert f"href: '{href}'" in _item_menu(chave)
    assert (FRONT / "app" / href).is_file()


def test_matriz_de_funcionalidades_do_modulo():
    # RN01, RN03, RN04, RN05
    quem = lambda chave: {perfil for perfil, itens in MATRIZ_FUNCIONALIDADES.items() if chave in itens}  # noqa: E731
    assert quem("minhas_solicitacoes") == {"Empresa Doadora"}
    assert quem("minhas_doacoes") == {"Cliente ONG"}
    assert quem("solicitacoes") == {"Administrador", "Funcionário"}


def test_matriz_do_contrato_do_modulo_4_nao_contradiz_o_codigo():
    # RN01: contrato cita Empresa Doadora/Cliente ONG/Admin/Funcionario nas rotas
    y = ler(RAIZ / "contratos" / "modulo-4.yaml")
    assert "Empresa Doadora vê somente solicitações da própria" in y
    assert "Cliente ONG vê somente doações da própria" in y


# ------------------------------------------------------------------ sem exclusao nem edicao de solicitacao (DP-43, RN21)
@pytest.mark.parametrize("p", PAGINAS + JS_MODULO)
def test_nao_ha_botao_nem_acao_de_excluir_ou_cancelar_solicitacao(p):
    t = _sem_comentarios(ler(p))
    t = re.sub(r"<p class=\"dica-campo\">.*?</p>", "", t, flags=re.S)
    t = re.sub(r"[^\n]*não pode ser editada nem cancelada[^\n]*", "", t)
    t = re.sub(r"'[^'\n]*Remover[^'\n]*'", "", t)  # "Remover" item na linha do formulario de nova solicitacao
    assert not re.search(r"\bexcluir|\bapagar|\bdeletar|lixeira|cancelar solicitação", t, re.I), p.name
    assert not re.search(r"Api\.delete|data-acao=.excluir|modal-excluir|btn-excluir", t)


def test_nenhuma_tela_edita_solicitacao():
    # DP-43: nao ha PUT/PATCH de /solicitacoes/{id}
    for p in (JS_SOL, JS_AVA):
        t = ler(p)
        assert not re.search(r"Api\.(put|patch)\('/solicitacoes/' \+ \w+\s*[,)]", t), p.name


# ------------------------------------------------------------------ seguranca de apresentacao (RNF05)
@pytest.mark.parametrize("p", [JS_SOL, JS_AVA, JS_DOA, JS_COMUM])
def test_texto_livre_da_api_passa_por_esc_ao_virar_html(p):
    # RNF05: campos de texto livre (tipo, modelo, identificacao, nomes) nunca entram crus no innerHTML
    t = _sem_comentarios(ler(p))
    for campo in ("nome_organizacao", "nome_ong", "identificacao", "modelo", "tipo"):
        for m in re.finditer(r"\+\s*((?:s|d|eq|it|item|sol)\.%s)\s*\+" % campo, t):
            ctx = t[max(0, m.start() - 40):m.start()]
            linha = t[t.rfind(chr(10), 0, m.start()) + 1:t.find(chr(10), m.end())]
            if "textContent" in linha or "dataset" in linha:  # textContent nao interpreta HTML
                continue
            assert "esc(" in ctx or "escAttr(" in ctx, f"{p.name}: {m.group(1)} sem escape"


def test_nenhum_script_usa_eval_nem_document_write():
    # RNF05
    for p in JS_MODULO:
        assert not re.search(r"\beval\s*\(|document\.write\s*\(|new Function\s*\(", ler(p)), p.name


# ------------------------------------------------------------------ front x contrato: chaves de erro 400 aninhado
def test_front_marca_o_campo_com_a_chave_curta_devolvida_pela_api():
    # UC09 FE1: o front deveria aceitar tambem a chave curta (tipo|modelo|quantidade)
    t = ler(JS_SOL)
    trecho = t[t.index("function aplicarCamposApi"):t.index("$('form-nova').addEventListener('submit'")]
    assert re.search(r"\^\(\?:itens\\\.\(\\d\+\)\\\.\)\?", trecho) or "campos[campo]" in trecho or "data-campo=\"' + k" in trecho
