"""Modulo 3 - front estatico (leitura dos arquivos; nao toca no front). UC05, UC07, UC08;
RF07, RF08, RF11, RF12; RN01, RN07, RN08, RN11, RN12; RNF01, RNF04, RNF05, RNF06; DP-30 a DP-37."""
import re
from pathlib import Path

import pytest

from app.permissoes import MATRIZ_FUNCIONALIDADES

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"
JS = FRONT / "js"
CSS = FRONT / "css"
PAG_CAT = FRONT / "app" / "categorias" / "index.html"
PAG_EQ = FRONT / "app" / "equipamentos" / "index.html"
JS_CAT = JS / "categorias.js"
JS_EQ = JS / "equipamentos.js"
JS_COMUM = JS / "equipamentos-comum.js"
JS_MODULO = [JS_CAT, JS_EQ, JS_COMUM]
CSS_NOVOS = [CSS / "equipamentos.css"]
PAGINAS = [PAG_CAT, PAG_EQ]

SITUACOES = ["Recebido", "Em avaliação", "Em manutenção", "Recondicionado", "Disponível", "Vendido", "Doado",
             "Destinado à reciclagem"]
CONDICOES = ["A avaliar", "Bom", "Regular", "Necessita reparo", "Sem condições de reuso"]


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="replace")


# ------------------------------------------------------------------ existencia e comentarios UC/RN
@pytest.mark.parametrize("p", PAGINAS + JS_MODULO + CSS_NOVOS)
def test_telas_scripts_e_css_do_modulo_existem(p):
    # UC05, UC07, UC08
    assert p.is_file()


@pytest.mark.parametrize("p,ucs", [(PAG_CAT, ["UC05"]), (PAG_EQ, ["UC07", "UC08"]), (JS_CAT, ["UC05"]),
                                   (JS_EQ, ["UC07", "UC08"]), (JS_COMUM, ["UC05", "UC07", "UC08"]),
                                   (CSS / "equipamentos.css", ["UC05", "UC07", "UC08"])])
def test_arquivos_citam_uc_no_comentario_inicial(p, ucs):
    # CLAUDE.md: toda tela cita UC e RN no comentario
    inicio = ler(p)[:1500]
    for uc in ucs:
        assert uc in inicio, f"{p.name} sem {uc}"
    if p.suffix != ".css":  # o CSS cita so UC e RNF (nao ha regra de negocio nele)
        assert re.search(r"\bRN\d+|\bRF\d+", inicio), f"{p.name} sem RN/RF"


@pytest.mark.parametrize("p", [PAG_CAT, JS_CAT])
def test_categorias_cita_rn07_rn08(p):
    # UC05
    t = ler(p)[:1500]
    assert "RN07" in t and "RN08" in t


@pytest.mark.parametrize("p", [PAG_EQ, JS_EQ])
def test_equipamentos_cita_rn_de_equipamento(p):
    # UC07, UC08
    t = ler(p)[:1500]
    assert "RN08" in t and "RN11" in t and "RN12" in t


def test_paginas_carregam_scripts_na_ordem():
    # UC05, UC07 (guarda de rota via Layout, RNF05)
    srcs = [s.split("/")[-1] for s in re.findall(r'<script[^>]+src="([^"]+)"', ler(PAG_CAT)) if not s.startswith("http")]
    assert srcs == ["api.js", "layout.js", "usuarios-comum.js", "equipamentos-comum.js", "categorias.js"]
    srcs = [s.split("/")[-1] for s in re.findall(r'<script[^>]+src="([^"]+)"', ler(PAG_EQ)) if not s.startswith("http")]
    # organizacoes-comum.js fornece OrgUi.formatarCnpj para a lista de ONGs (UC08 passo 4)
    assert srcs == ["api.js", "layout.js", "usuarios-comum.js", "organizacoes-comum.js", "equipamentos-comum.js",
                    "equipamentos.js"]


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_carregam_a_folha_do_modulo(p):
    # RNF01
    assert "equipamentos.css" in ler(p)


def test_paginas_usam_layout_iniciar_com_a_chave_do_menu():
    # RN01, RNF05
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'categorias'", ler(JS_CAT))
    assert re.search(r"Layout\.iniciar\(\s*\{\s*chave:\s*'equipamentos'", ler(JS_EQ))


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
    # equipamentos-comum.js e so de apoio (formatacao e validacao)
    assert "Api." not in ler(JS_COMUM)


def test_categorias_js_aponta_para_rotas_do_contrato():
    # UC05 (somente via Api)
    t = ler(JS_CAT)
    for rota in ("Api.get('/categorias?'", "Api.get('/categorias/' +", "Api.post('/categorias'",
                 "Api.put('/categorias/' +", "'/situacao'"):
        assert rota in t, rota
    assert "Api.patch('/categorias/' + alvo.id + '/situacao', { ativa: alvo.nova })" in t


def test_equipamentos_js_aponta_para_rotas_do_contrato():
    # UC07, UC08
    t = ler(JS_EQ)
    for rota in ("Api.get('/categorias?size=100')", "Api.get('/equipamentos?'", "Api.get('/equipamentos/' +",
                 "Api.post('/equipamentos'", "Api.put('/equipamentos/' +", "'/situacao', corpo", "'/ativo', { ativo: alvo.novo }"):
        assert rota in t, rota
    assert "Api.patch('/equipamentos/' + eq.id_equipamento + '/situacao'" in t
    assert "Api.patch('/equipamentos/' + alvo.id + '/ativo'" in t


def test_lista_de_ongs_usa_apenas_cliente_ong_ativa_do_modulo_2():
    # UC08 passo 4, RN12 (M3)
    t = ler(JS_EQ)
    assert "'/organizacoes?tipo=' + encodeURIComponent('Cliente ONG') + '&situacao=Ativa" in t


def test_put_de_equipamento_nao_envia_situacao_nem_ativo():
    # contrato: PUT sem situacao/ativo; so o POST envia situacao
    t = ler(JS_EQ)
    assert t.count("corpo.situacao") == 1
    assert t.index("corpo.situacao") < t.index("Api.post('/equipamentos'")
    corpo = t[t.index("var corpo = {"):t.index("if (criando) { corpo.situacao")]
    assert "ativo" not in corpo and "situacao" not in corpo


def test_corpo_usa_nomes_das_colunas_do_banco():
    # convencoes: nomes de campos iguais as colunas
    t = ler(JS_EQ)
    corpo = t[t.index("var corpo = {"):t.index("if (criando) { corpo.situacao")]
    for campo in ("identificacao", "id_categoria", "modelo", "condicao", "origem", "data_recebimento", "valor",
                  "id_item_solicitacao"):
        assert campo + ":" in corpo, campo


def test_corpo_da_doacao_envia_id_organizacao_ong_e_data_doacao_so_se_doado():
    # UC08 passo 4, contrato SituacaoEntrada
    t = ler(JS_EQ)
    bloco = t[t.index("if (nova === 'Doado')"):t.index("var chaves = Object.keys(erros);", t.index("if (nova === 'Doado')"))]
    assert "corpo.id_organizacao_ong" in bloco and "corpo.data_doacao" in bloco
    assert t.count("corpo.id_organizacao_ong") == 1


# ------------------------------------------------------------------ menu e matriz (RN01, DP-37)
def _item_menu(chave):
    m = re.search(r"\{\s*chave:\s*'" + chave + r"'[^}]*\}", ler(JS / "layout.js"))
    assert m, f"item {chave} ausente do MENU"
    return m.group(0)


@pytest.mark.parametrize("chave,href", [("categorias", "categorias/index.html"), ("equipamentos", "equipamentos/index.html")])
def test_itens_do_menu_ligados_as_paginas(chave, href):
    # UC05, UC07, RN01
    assert f"href: '{href}'" in _item_menu(chave)
    assert (FRONT / "app" / href).is_file()


def test_matriz_de_funcionalidades_do_modulo():
    # DP-37, RN01, RN03: categorias so Administrador; equipamentos Administrador e Funcionario
    quem = lambda chave: {perfil for perfil, itens in MATRIZ_FUNCIONALIDADES.items() if chave in itens}  # noqa: E731
    assert quem("categorias") == {"Administrador"}
    assert quem("equipamentos") == {"Administrador", "Funcionário"}


def test_matriz_do_contrato_do_modulo_3_concorda_com_o_codigo():
    # RN01 (x-permissoes: menu)
    y = ler(RAIZ / "contratos" / "modulo-3.yaml")
    assert "`categorias` só Administrador; `equipamentos` Administrador e Funcionário" in y
    assert "categorias" in MATRIZ_FUNCIONALIDADES["Administrador"]
    assert "categorias" not in MATRIZ_FUNCIONALIDADES["Funcionário"]


# ------------------------------------------------------------------ sem exclusao (RN07, UC07 FA2)
@pytest.mark.parametrize("p", PAGINAS + [JS_CAT, JS_EQ])
def test_nao_ha_botao_nem_acao_de_excluir(p):
    t = ler(p)
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    t = re.sub(r"<!--.*?-->", "", t, flags=re.S)
    t = re.sub(r"[^\n]*N[aã]o sao exclu[^\n]*", "", t)
    # a pagina de categorias explica que categorias nao sao excluidas; exclui apenas o texto explicativo
    t = re.sub(r"<p class=\"dica-campo\">.*?</p>", "", t, flags=re.S)
    # Pedido 1 (DP-84): "Remover imagem" e DELETE /equipamentos/{id}/imagem sao da imagem, nao do equipamento
    t = re.sub(r"(?i)remover[\w-]*|\w*\.remover|queriaRemover|removida|atualizarBotaoRemover", "", t) if p.name in ("index.html", "equipamentos.js") else t
    assert not re.search(r"\bexcluir|\bremover|\bapagar|\bdeletar|lixeira", t, re.I), p.name
    t = t.replace("Api.delete('/equipamentos/' + salvo.id_equipamento + '/imagem')", "")  # Pedido 1: DELETE da imagem
    assert not re.search(r"Api\.delete|data-acao=.excluir|modal-excluir|btn-excluir", t)


@pytest.mark.parametrize("p", [JS_CAT, JS_EQ])
def test_scripts_nao_chamam_delete(p):
    # Pedido 1: unico DELETE permitido e o da imagem (/imagem)
    assert "Api.delete" not in ler(p).replace("Api.delete('/equipamentos/' + salvo.id_equipamento + '/imagem')", "")
    assert not re.search(r"method:\s*['\"]DELETE", ler(p), re.I)


def test_acoes_da_tabela_de_categorias():
    # UC05 FA1, FA2
    acoes = set(re.findall(r'data-acao="(\w+)"', ler(JS_CAT)))
    assert acoes == {"renomear", "situacao"}
    t = ler(JS_CAT)
    assert "Desativar" in t and "Reativar" in t


def test_acoes_da_tabela_de_equipamentos():
    # UC07 FA1, FA2, UC08
    acoes = set(re.findall(r'data-acao="(\w+)"', ler(JS_EQ)))
    assert acoes == {"ver", "editar", "situacao", "ativo"}


@pytest.mark.parametrize("sufixo,pagina", [("situacao", PAG_CAT), ("ativo", PAG_EQ)])
def test_modal_de_confirmacao_de_desativacao(sufixo, pagina):
    # UC05 FA2, UC07 FA2: confirmacao antes de desativar
    h = ler(pagina)
    assert f'id="btn-confirmar-{sufixo}"' in h
    assert f'data-bs-dismiss="modal" id="btn-nao-{sufixo}"' in h


def test_categorias_patch_so_dentro_do_clique_de_confirmacao():
    # UC05 FA2: o botao da tabela so abre o modal
    t = ler(JS_CAT)
    assert t.count("/situacao'") == 1
    idx = t.index("btn-confirmar-situacao').addEventListener")
    assert "/situacao'" in t[idx:]
    abrir = t[t.index("function abrirSituacao"):idx]
    assert "Api." not in abrir and "modalSituacao.show()" in abrir


def test_equipamentos_patch_ativo_so_dentro_do_clique_de_confirmacao():
    # UC07 FA2
    t = ler(JS_EQ)
    assert t.count("/ativo'") == 1
    idx = t.index("btn-confirmar-ativo').addEventListener")
    assert "/ativo'" in t[idx:]
    abrir = t[t.index("function abrirAtivo"):idx]
    assert "Api." not in abrir and "modalAtivo.show()" in abrir


@pytest.mark.parametrize("p", PAGINAS + JS_MODULO)
def test_sem_confirm_nativo(p):
    assert not re.search(r"\bconfirm\s*\(", ler(p))


# ------------------------------------------------------------------ categorias base protegidas (UC05 passo 6, FE4)
def test_categoria_protegida_sem_acoes_de_renomear_ou_desativar():
    # UC05 FE4, RF08
    t = ler(JS_CAT)
    corpo = t[t.index("function botoes"):t.index("function linhaHtml")]
    assert corpo.index("if (c.protegida)") < corpo.index("data-acao=\"renomear\"")
    assert corpo.index("if (c.protegida)") < corpo.index("data-acao=\"situacao\"")
    assert "return '<span class=\"texto-sem-acao\">" in corpo
    assert "seloProtegida" in t


def test_renomear_categoria_protegida_bloqueado_antes_de_abrir_formulario():
    # UC05 FE4
    t = ler(JS_CAT)
    abrir = t[t.index("async function abrirRenomear"):t.index("form.addEventListener('submit'")]
    assert abrir.index("c.protegida") < abrir.index("modalForm.show()")
    assert "CATEGORIA_PROTEGIDA" in abrir


def test_dica_da_tela_de_categorias_menciona_as_seis_base_e_que_nao_exclui():
    # UC05 passo 6
    h = ler(PAG_CAT)
    for n in ("computadores", "notebooks", "monitores", "periféricos", "placas de vídeo", "placas-mãe"):
        assert n in h
    assert "apenas desativadas" in h


def test_formulario_de_categoria_tem_limite_de_80_e_rotulo():
    # UC05 passo 3, RNF04, RNF06
    h = ler(PAG_CAT)
    assert re.search(r'id="f-nome"[^>]*maxlength="80"', h)
    assert re.search(r'<label[^>]*for="f-nome"', h)
    assert "nome.length > 80" in ler(JS_CAT)


def test_categorias_tratam_fe1_fe2_fe3_fe4():
    # UC05 FE1 (nome ausente), FE2 (falha ao salvar), FE3 (duplicado), FE4 (protegida)
    t = ler(JS_CAT)
    assert "Informe o nome da categoria." in t
    assert "A alteração não foi concluída." in t
    assert "NOME_CATEGORIA_DUPLICADO" in t
    assert "CATEGORIA_PROTEGIDA" in t


# ------------------------------------------------------------------ equipamentos: formularios e listas fechadas
def _opcoes_js(nome):
    m = re.search(r"var " + nome + r" = \[(.*?)\];", ler(JS_COMUM), re.S)
    assert m, nome
    return re.findall(r"'([^']*)'", m.group(1))


def test_situacoes_do_front_sao_exatamente_as_oito_do_contrato():
    # RF12, contrato Situacao
    assert _opcoes_js("SITUACOES") == SITUACOES


def test_condicoes_do_front_sao_exatamente_as_cinco_do_contrato():
    # RF11 (M3), DP-32
    assert _opcoes_js("CONDICOES") == CONDICOES


def test_valores_do_front_coincidem_com_o_yaml_do_contrato():
    # contrato modulo-3.yaml (schemas Situacao e Condicao)
    y = ler(RAIZ / "contratos" / "modulo-3.yaml")
    sit = re.search(r"Situacao:\s*\n\s*type: string\s*\n\s*enum: \[(.*?)\]", y).group(1)
    con = re.search(r"Condicao:\s*\n\s*type: string\s*\n\s*enum: \[(.*?)\]", y).group(1)
    assert [x.strip() for x in sit.split(",")] == SITUACOES
    assert [x.strip() for x in con.split(",")] == CONDICOES


def test_situacao_inicial_no_cadastro_nao_oferece_vendido_nem_doado():
    # UC07 passo 3, DP-35
    t = ler(JS_EQ)
    assert "E.SITUACOES.filter(function (v) { return v !== 'Vendido' && v !== 'Doado'; })" in t


def test_situacoes_permitidas_do_front_nunca_oferecem_vendido():
    # UC08 passo 3 (M3), DP-35
    t = ler(JS_COMUM)
    corpo = t[t.index("function situacoesPermitidas"):t.index("function validarEquipamento")]
    assert "s !== 'Vendido'" in corpo


def test_front_espelha_regras_de_situacao_final_sem_reuso_inativo_valor():
    # UC08 FE2, FE3, RN12, DP-35 (conveniencia; a API valida)
    t = ler(JS_COMUM)
    corpo = t[t.index("function situacoesPermitidas"):t.index("function validarEquipamento")]
    assert "finalizado(eq)" in corpo
    assert "eq.situacao === 'Destinado à reciclagem'" in corpo
    assert "eq.condicao === SEM_REUSO" in corpo and "SIT_SEM_REUSO" in corpo
    assert "eq.condicao === 'A avaliar'" in corpo
    assert "!eq.ativo" in corpo
    assert "Number(eq.valor) > 0" in corpo
    assert _opcoes_js("SIT_SEM_REUSO") == ["Recebido", "Em avaliação", "Destinado à reciclagem"]


def test_campos_do_formulario_de_equipamento():
    # UC07 passo 3
    campos = set(re.findall(r'<(?:input|select|textarea)[^>]*\bid="(f-[^"]+)"', ler(PAG_EQ)))
    assert {"f-identificacao", "f-categoria", "f-modelo", "f-condicao", "f-origem", "f-data", "f-valor", "f-item",
            "f-situacao"} <= campos


def test_limites_dos_campos_no_html():
    # UC07 passo 3, DP-33, DP-34
    h = ler(PAG_EQ)
    for i, n in (("f-identificacao", 50), ("f-modelo", 150), ("f-origem", 100)):
        assert re.search(rf'id="{i}"[^>]*maxlength="{n}"', h), i
    assert re.search(r'id="f-data"', h) and 'type="date"' in h


def test_validacao_no_cliente_replica_limites_e_data_nao_futura():
    # UC07 FE1, RNF04, DP-34
    t = ler(JS_COMUM)
    for trecho in ("ident.length > 50", "modelo.length > 150", "origem.length > 100", "v.data_recebimento > hojeIso()",
                   "no máximo 2 casas decimais", "não pode ser negativo", "não pode ser futura"):
        assert trecho in t, trecho


def test_data_de_doacao_validada_no_cliente_nao_futura_e_nao_anterior_ao_recebimento():
    # UC08 passo 4 (M3), RN12 (M3)
    t = ler(JS_EQ)
    assert "d > E.hojeIso()" in t and "d < eq.data_recebimento" in t
    assert "Selecione a ONG beneficiada." in t and "Informe a data da doação." in t  # UC08 FE1


def test_doacao_so_aparece_quando_situacao_doado():
    # UC08 passo 4
    t = ler(JS_EQ)
    assert "s.situacao.value === 'Doado'" in t
    assert "$('bloco-doacao').hidden = !doado" in t


def test_equipamento_finalizado_abre_somente_leitura():
    # UC07 FE2 (M3), RF12 (M3)
    t = ler(JS_EQ)
    assert "'leitura'" in t and "E.finalizado(eq)" in t
    assert "if (estado.modo === 'leitura') { return; }" in t
    assert "if (E.finalizado(eq))" in t  # lista: apenas Consultar
    assert "Atualizar situação" in t


def test_destinado_a_reciclagem_sem_botao_atualizar_situacao():
    # DP-35 (situacao final)
    t = ler(JS_EQ)
    assert "if (eq.situacao !== 'Destinado à reciclagem')" in t


def test_categoria_desativada_ja_vinculada_permanece_no_form_mas_nao_e_nova_escolha():
    # UC07 FA1, RN08
    t = ler(JS_EQ)
    assert "estado.catsAtivas.forEach(function (c) { f.categoria.appendChild" in t
    assert "(desativada, mantida neste registro)" in t


def test_novo_equipamento_recarrega_categorias():
    # UC05 passo 5
    t = ler(JS_EQ)
    corpo = t[t.index("$('btn-novo').addEventListener"):t.index("$('modal-form').addEventListener('shown.bs.modal'")]
    assert corpo.index("await carregarCategorias()") < corpo.index("prepararForm('criar'")


def test_mensagens_de_erro_do_contrato_em_portugues():
    # RNF04: codigos do x-codigos-erro do modulo 3
    y = ler(RAIZ / "contratos" / "modulo-3.yaml")
    codigos = set(re.findall(r"^  ([A-Z_]+): \"\d{3}\"", y[y.index("x-codigos-erro:"):], re.M))
    assert codigos
    m = re.search(r"var MSG = \{(.*?)\n  \};", ler(JS_COMUM), re.S).group(1)
    msgs = dict(re.findall(r"(\w+):\s*'((?:[^'\\]|\\.)*)'", m))
    palavras = r"\b(não|você|categoria|categorias|equipamento|equipamentos|identificação|item|situação|doação|dados|" \
               r"permissão|registro|mudança|imagem)\b"
    for cod in codigos | {"DADOS_INVALIDOS", "SEM_PERMISSAO", "NAO_ENCONTRADO"}:
        assert cod in msgs and msgs[cod].strip(), f"sem mensagem para {cod}"
        assert re.search(palavras, msgs[cod], re.I), cod


@pytest.mark.parametrize("js", [JS_CAT, JS_EQ])
def test_scripts_exibem_mensagem_do_erro_via_msgerro(js):
    # RNF04
    assert ler(js).count("E.msgErro(err)") >= 3


def test_tratamento_dos_erros_especificos_por_tela():
    # UC07 FE1, FE2, FE3; UC08 FE1 a FE3
    t = ler(JS_EQ)
    for cod in ("IDENTIFICACAO_DUPLICADA", "CATEGORIA_INVALIDA", "ITEM_SOLICITACAO_INVALIDO", "SEM_CONDICOES_DE_REUSO",
                "TRANSICAO_INVALIDA", "EQUIPAMENTO_INATIVO", "DOACAO_INVALIDA", "EQUIPAMENTO_FINALIZADO", "NAO_ENCONTRADO"):
        assert cod in t, cod


def test_erros_da_api_sao_mapeados_para_os_campos_pelo_nome_da_coluna():
    # RNF04
    t = ler(JS_EQ)
    assert "var mapaApi = { identificacao: f.identificacao, id_categoria: f.categoria" in t
    assert "id_organizacao_ong: s.ong, data_doacao: s.data" in t


# ------------------------------------------------------------------ acessibilidade e identidade (RNF01, RNF06)
@pytest.mark.parametrize("p", PAGINAS)
def test_campos_dos_formularios_tem_rotulo_associado(p):
    # RNF06
    h = ler(p)
    ids = re.findall(r'<(?:input|select|textarea)[^>]*\bid="((?:f|s|filtro)-[^"]+)"', h)
    assert ids
    for i in ids:
        assert re.search(rf'<label[^>]*for="{i}"', h), f"{p.name}: campo {i} sem label"


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_com_idioma_e_viewport(p):
    # RNF06
    h = ler(p)
    assert '<html lang="pt-BR"' in h
    assert 'name="viewport"' in h


@pytest.mark.parametrize("p", PAGINAS)
def test_paginas_tem_regioes_vivas_titulos_e_pular_conteudo(p):
    # RNF06
    h = ler(p)
    assert 'aria-live="polite"' in h and "pular-conteudo" in h and "<h1" in h
    assert h.count('class="modal fade"') >= 2 and "aria-labelledby" in h


def test_tabelas_com_caption_e_scope():
    # RNF06
    for p in PAGINAS:
        h = ler(p)
        assert "<caption" in h and 'scope="col"' in h


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
    # DP-06 revista
    for p in PAGINAS + JS_MODULO + CSS_NOVOS:
        assert "#dc3545" not in ler(p).lower(), p.name
        assert "btn-danger" not in ler(p), p.name


def test_estado_nunca_so_por_cor():
    # RNF06: selos com texto e icone
    t = ler(JS_COMUM)
    for trecho in ("function seloSituacao", "function seloAtivo", "function seloCategoria", "function seloProtegida"):
        assert trecho in t
    assert "Protegida" in t and "Inativa" in t and "Inativo" in t


def test_cada_situacao_tem_icone():
    # RNF06
    t = ler(JS_COMUM)
    bloco = t[t.index("var ICONE_SIT"):t.index("function seloSituacao")]
    for s in SITUACOES:
        assert f"'{s}':" in bloco, s


@pytest.mark.parametrize("p,funcao_ini,funcao_fim,campos", [
    (JS_CAT, "function linhaHtml", "async function carregar(", ["c.nome"]),
    (JS_EQ, "function linhaHtml", "async function carregar(", ["eq.identificacao", "eq.nome_categoria", "eq.modelo", "eq.origem"]),
])
def test_dados_da_api_passam_por_escape_nas_linhas(p, funcao_ini, funcao_fim, campos):
    # RNF04/seguranca
    t = ler(p)
    linha = t[t.index(funcao_ini):t.index(funcao_fim)]
    for c in campos:
        assert f"U.esc({c})" in linha, c


def test_nome_da_ong_escapado_na_lista_e_na_doacao():
    # seguranca (XSS)
    t = ler(JS_EQ)
    assert "U.esc(eq.doacao.nome_ong)" in t
    assert "o.nome_razao_social + ' (CNPJ '" in t  # vai por textContent (opcao()), sem innerHTML
    assert "o.textContent = texto" in t


def test_front_sem_comentarios_de_rota_exposta_a_segredos():
    # seguranca: nenhum segredo ou token fixo nos arquivos do modulo
    for p in PAGINAS + JS_MODULO:
        t = ler(p)
        assert not re.search(r"Bearer\s+[A-Za-z0-9._-]{20,}|senha\s*[:=]\s*['\"][^'\"]+['\"]", t), p.name
