"""Pedido 1 (DP-84 a DP-86, DP-90) - imagem do produto no front-end. UC07 (equipamento), UC12/UC13 (marketplace)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FRONT = Path(__file__).resolve().parents[2] / "frontend"


def ler(*partes) -> str:
    return FRONT.joinpath(*partes).read_text(encoding="utf-8")


def test_formulario_tem_seletor_previa_e_remocao():
    h = ler("app", "equipamentos", "index.html")
    assert 'type="file"' in h and 'accept="image/jpeg,image/png,image/webp"' in h
    assert "Escolher imagem" in h and "Remover imagem" in h and 'id="previa-imagem"' in h


def test_equipamentos_js_fluxo_de_imagem():
    t = ler("js", "equipamentos.js")
    for s in ("createObjectURL", "revokeObjectURL", "Api.enviarArquivo", "'arquivo'", "/imagem", "Api.delete",
              "foi salvo, mas a imagem"):
        assert s in t, s
    assert "alert(" not in t


def test_api_envia_multipart_sem_content_type_manual():
    t = ler("js", "api.js")
    assert "enviarArquivo" in t and "instanceof FormData" in t and "urlImagem" in t
    assert "/imagens/equipamentos/" in t


def test_mensagens_de_validacao_no_cliente():
    t = ler("js", "equipamentos-comum.js")
    assert "A imagem deve ter no máximo 2 MB." in t and "Envie uma imagem JPG, PNG ou WebP." in t


def test_marketplace_usa_imagem_url_com_alt_lazy_e_icone_padrao():
    m, p, c = ler("js", "marketplace.js"), ler("js", "produto.js"), ler("compra.html")
    for t in (m, p):
        assert "imagem_url" in t and "Api.urlImagem" in t and ".alt = " in t
    assert "loading = 'lazy'" in m
    assert "fa-microchip" in m and "fa-microchip" in c  # icone padrao permanece
    css = ler("css", "marketplace.css")
    assert "object-fit: cover" in css


def test_css_sem_cores_fora_da_identidade():
    css = ler("css", "equipamentos.css")
    bloco = css[css.index("UC07 (DP-84)"):]
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", bloco)


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_validacao_de_tipo_e_tamanho_no_node(tmp_path):
    h = tmp_path / "h.js"
    h.write_text(r"""
const fs = require('fs'); const assert = require('assert');
global.window = global; global.document = {}; global.sessionStorage = {};
eval(fs.readFileSync(process.argv[2], 'utf8'));
const V = global.EquipUi.validarImagem;
assert.strictEqual(V(null), '');
assert.strictEqual(V({type: 'image/png', size: 100}), '');
assert.strictEqual(V({type: 'image/webp', size: 2 * 1024 * 1024}), '');
assert.strictEqual(V({type: 'image/jpeg', size: 2 * 1024 * 1024 + 1}), 'A imagem deve ter no máximo 2 MB.');
assert.strictEqual(V({type: 'image/gif', size: 10}), 'Envie uma imagem JPG, PNG ou WebP.');
assert.strictEqual(V({type: 'application/pdf', size: 10}), 'Envie uma imagem JPG, PNG ou WebP.');
console.log('ok');
""", encoding="utf-8")
    r = subprocess.run(["node", str(h), str(FRONT / "js" / "equipamentos-comum.js")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr


def test_sem_imagem_nao_quebra_e_rotulo_na_mesma_linha():
    """DP-105: 'Sem imagem' em uma linha; no cartao, rotulo 'Imagem:' e valor lado a lado."""
    c = ler("css", "equipamentos.css")
    assert re.search(r"\.tabela-equip \.texto-sem-acao\s*\{[^}]*white-space:\s*nowrap", c)
    assert re.search(r'td\[data-rotulo="Imagem"\]\s*\{[^}]*white-space:\s*nowrap', c)
    assert re.search(r'max-width: 991\.98px\)\s*\{\s*\.tabela-equip td\[data-rotulo="Imagem"\]\s*\{[^}]*display:\s*flex', c)
    assert "width: 56px; height: 56px" in c
