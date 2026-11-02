"""Modulo 6 - front estatico (leitura dos arquivos). UC22, UC23, UC24; RF16, RF17, RF18, RF21;
RN16, RN17, RN18, RN21; RNF01, RNF05, RNF06. Tela app/relatorios; script relatorios.js; folha relatorios.css."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.permissoes import MATRIZ_FUNCIONALIDADES

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"
PAG = FRONT / "app" / "relatorios" / "index.html"
JS = FRONT / "js" / "relatorios.js"
CSS = FRONT / "css" / "relatorios.css"


def ler(p):
    return p.read_text(encoding="utf-8", errors="replace")


def _sem_comentarios(t):
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"<!--.*?-->", "", t, flags=re.S)


@pytest.mark.parametrize("p", [PAG, JS, CSS])
def test_arquivos_existem(p):
    assert p.is_file()


@pytest.mark.parametrize("p", [PAG, JS])
def test_citam_uc_e_rn(p):
    ini = ler(p)[:1500]
    for x in ("UC22", "UC23", "UC24", "RN16", "RN17", "RN18", "RN21"):
        assert x in ini, (p.name, x)


def test_menu_relatorios_ligado_e_matriz_de_perfis():
    # RN17, RN03, RNF05
    m = re.search(r"\{\s*chave:\s*'relatorios'[^}]*\}", ler(FRONT / "js" / "layout.js")).group(0)
    assert "href: 'relatorios/index.html'" in m
    quem = {perfil for perfil, itens in MATRIZ_FUNCIONALIDADES.items() if "relatorios" in itens}
    assert quem == {"Administrador", "Funcionário"}


def test_pagina_carrega_scripts_e_e_responsiva_e_acessivel():
    h = ler(PAG)
    srcs = [s.split("/")[-1] for s in re.findall(r'<script[^>]+src="([^"]+)"', h) if not s.startswith("http")]
    assert srcs == ["api.js", "layout.js", "relatorios.js"]
    assert 'lang="pt-BR"' in h and 'name="viewport"' in h and "bootstrap@5" in h and "relatorios.css" in h
    assert 'class="pular-conteudo"' in h and 'id="conteudo-app"' in h and 'role="alert"' in h
    assert not re.search(r"<script(?![^>]*\bsrc=)[^>]*>\s*\S", h), "script inline"


def test_css_tem_ponto_de_quebra():
    assert "@media" in ler(CSS)


def test_todo_id_buscado_existe_na_pagina():
    ids = set(re.findall(r'\bid="([^"]+)"', ler(PAG)))
    usados = set(re.findall(r"\$\('([^']+)'\)", ler(JS)))
    # ids montados por concatenacao (campo + '-erro') nao entram; so literais
    assert usados - ids == set()
    todos = re.findall(r'\bid="([^"]+)"', ler(PAG))
    assert len(todos) == len(set(todos))


def test_campos_de_formulario_tem_label():
    h = ler(PAG)
    for tipo, i in re.findall(r'<(input|select|textarea)[^>]*\bid="([^"]+)"', h):
        assert f'for="{i}"' in h, i


def test_filtros_das_tres_telas_existem():
    # UC22 passo 2, UC23 passo 2, UC24 passo 1
    h = ler(PAG)
    for i in ("v-de", "v-ate", "e-cat", "e-sit", "e-de", "e-ate", "o-emp", "o-sit", "o-de", "o-ate",
              "res-vendas", "res-equip", "res-org"):
        assert f'id="{i}"' in h, i
    assert 'id="v-de"' in h and re.search(r'id="v-de"[^>]*required', h) and re.search(r'id="v-ate"[^>]*required', h)


def test_js_usa_somente_get_do_contrato_e_api_js():
    t = _sem_comentarios(ler(JS))
    assert not re.search(r"\bfetch\s*\(|XMLHttpRequest|/api/v1", t)
    assert re.findall(r"Api\.(post|put|patch|delete)\(", t) == []
    for rota in ("/relatorios/vendas?", "/relatorios/equipamentos?", "/relatorios/organizacoes-destinacoes?"):
        assert f"Api.get('{rota}" in t, rota
    for p in ("data_de=", "data_ate=", "id_categoria=", "situacao=", "id_organizacao_doadora="):
        assert p in t, p


def test_js_sem_armazenamento_de_sessao_nem_eval():
    t = _sem_comentarios(ler(JS))
    for x in ("localStorage", "sessionStorage", "document.cookie", "eval(", "document.write"):
        assert x not in t


def test_js_escapa_dados_da_api_em_innerhtml():
    # RNF05: campos da API em string HTML passam por esc()
    t = _sem_comentarios(ler(JS))
    assert "function esc" in t and "textContent" in t
    for campo in ("v.cliente", "i.identificacao", "e.identificacao", "s.empresa_doadora", "e.ong_beneficiada", "p)"):
        trechos = [m for m in re.finditer(re.escape(campo), t)]
        assert trechos, campo
    # nenhum campo de API concatenado sem esc/data/moeda: procura "' + x.campo +" sem esc
    cru = re.findall(r"'\s*\+\s*(?!esc\(|data\(|moeda\(|pagina|\(|estado|tipo|total|paginas|prefixo)([a-z]\.[a-z_]+)\s*\+", t)
    assert cru == [], cru


def test_uc22_fa1_fe1_tratados_no_front():
    t = ler(JS)
    assert "Nenhuma venda confirmada neste período" in t and "moeda(0)" in t  # FA1
    assert "Informe a data inicial" in t and "não pode ser posterior" in t and "Período inválido" in t  # FE1
    assert "PERIODO_INVALIDO" in t


def test_uc23_filtros_invalidos_e_origem_destinacao():
    t = ler(JS)
    assert "resumo_por_situacao" in t and "e.origem" in t and "e.destinacao" in t and "e.destino_detalhe" in t
    assert "Filtros inválidos" in t and "Nenhum equipamento encontrado" in t
    for s in ("Recebido", "Em avaliação", "Em manutenção", "Recondicionado", "Disponível", "Vendido", "Doado",
              "Destinado à reciclagem"):
        assert f"'{s}'" in t, s


def test_uc24_pendencias_reciclagem_e_doacao():
    t = ler(JS)
    assert "avaliacao_pendente" in t and "pendencias" in t and "Destinação pendente" in t  # FA1, FE1
    assert "ong_beneficiada" in t and "data_doacao" in t
    # FA2: ONG/data so quando destinacao e Doacao
    assert "e.destinacao === 'Doação'" in t
    for s in ("Aguardando avaliação", "Em avaliação", "Avaliada"):
        assert f"'{s}'" in t, s


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_javascript_tem_sintaxe_valida():
    r = subprocess.run(["node", "--check", str(JS)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0, r.stderr
