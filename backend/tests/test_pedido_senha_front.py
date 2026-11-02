"""Pedido 2 (DP-88) - botao de mostrar/ocultar senha: componente unico js/senha-olho.js.
UC01 (login), UC02/UC03 (usuarios), UC02 FA3 (exclusao da propria conta, DP-64)."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FRONT = Path(__file__).resolve().parents[2] / "frontend"
JS = FRONT / "js" / "senha-olho.js"
CSS = FRONT / "css" / "identidade.css"
PAGINAS = [FRONT / "login.html"]  # telas internas recebem o componente via layout.js


def ler(p: Path) -> str:
    return p.read_text(encoding="utf-8")


@pytest.mark.parametrize("p", PAGINAS, ids=lambda p: p.name)
def test_pagina_com_senha_carrega_o_componente(p):
    assert re.search(r'<script src="[./]*js/senha-olho\.js"', ler(p))


def test_layout_js_usa_o_componente_no_modal_dinamico():
    t = ler(FRONT / "js" / "layout.js")
    assert "senha-olho.js" in t and "SenhaOlho.aplicar" in t


def test_layout_iniciar_carrega_o_componente_em_toda_tela_interna():
    t = ler(FRONT / "js" / "layout.js")
    corpo = t[t.index("iniciar: async function"):]
    assert "carregarSenhaOlho()" in corpo  # DP-88: nao so no modal de exclusao


def test_nenhum_campo_de_senha_fica_sem_o_componente():
    cobertos = {"login.html", "index.html", "organizacao.html", "layout.js", "index.html"}
    achados = []
    for p in FRONT.rglob("*"):
        if p.suffix in (".html", ".js") and p != JS and re.search(r'type=["\\\']?password', ler(p)):
            achados.append(p)
            assert p.name in cobertos, f"{p} tem senha sem o componente"
            if p.suffix == ".html" and "app" not in p.parts:
                assert "senha-olho.js" in ler(p)
            if "app" in p.parts:
                assert "layout.js" in ler(p)
    assert len(achados) == 5


def test_script_tem_acessibilidade_e_svg():
    t = ler(JS)
    for s in ("Mostrar senha", "Ocultar senha", "aria-label", "aria-pressed", "botao.type = 'button'", "<svg", "pagehide", "'submit'"):
        assert s in t, s
    assert "autocomplete" not in t.replace("nao altera autocomplete", "")
    assert "localStorage" not in t and "sessionStorage" not in t


def test_css_do_componente_usa_variaveis_e_alvo_minimo():
    c = ler(CSS)
    bloco = c[c.index(".senha-olho {"):]
    assert "padding-right" in bloco and "focus-visible" in bloco and "min-width: 32px" in bloco
    assert not re.search(r"#[0-9a-fA-F]{3,6}\b", bloco)


@pytest.mark.skipif(shutil.which("node") is None, reason="node nao instalado")
def test_comportamento_do_toggle_no_node(tmp_path):
    harness = tmp_path / "h.js"
    harness.write_text(r"""
const fs = require('fs'); const assert = require('assert');
function el(tag){ const e={tag,attrs:{},children:[],listeners:{},parentNode:null,nodeType:1,className:'',innerHTML:'',type:'',ownerDocument:null,
  setAttribute(k,v){this.attrs[k]=String(v)}, getAttribute(k){return this.attrs[k]===undefined?null:this.attrs[k]},
  appendChild(c){if(c.parentNode){c.parentNode.children=c.parentNode.children.filter(x=>x!==c)} c.parentNode=this;this.children.push(c);return c},
  insertBefore(n,ref){n.parentNode=this;this.children.splice(this.children.indexOf(ref),0,n);return n},
  addEventListener(t,f){(this.listeners[t]=this.listeners[t]||[]).push(f)},
  querySelector(){return this.children.find(c=>c.tag==='input')||null}, matches(){return false}, form:null};
  e.ownerDocument=doc; return e; }
const doc = { readyState:'complete', body:null, createElement:el, addEventListener(){},
  _inputs:[], querySelectorAll(s){ return s==='.senha-olho-botao' ? this._btns() : this._inputs.filter(i=>i.type==='password'||i.attrs['data-senha-olho']==='1'); },
  _btns(){ return this._inputs.map(i=>i.parentNode&&i.parentNode.children[1]).filter(Boolean) } };
doc.body = el('body');
global.window = global; global.document = doc; global.MutationObserver = undefined;
const listeners = {}; global.addEventListener=(t,f)=>{listeners[t]=f};
eval(fs.readFileSync(process.argv[2],'utf8'));
const form = el('form'); const pai = el('div'); const inp = el('input'); inp.type='password'; inp.form=form; pai.appendChild(inp);
doc._inputs.push(inp);
SenhaOlho.aplicar(doc); SenhaOlho.aplicar(doc);   /* idempotente */
const btn = inp.parentNode.children[1];
assert.strictEqual(inp.parentNode.className,'senha-olho'); assert.strictEqual(inp.parentNode.children.length,2);
assert.strictEqual(btn.type,'button'); assert.strictEqual(inp.type,'password');
assert.strictEqual(btn.attrs['aria-label'],'Mostrar senha'); assert.strictEqual(btn.attrs['aria-pressed'],'false');
btn.listeners.click[0]();
assert.strictEqual(inp.type,'text'); assert.strictEqual(btn.attrs['aria-label'],'Ocultar senha'); assert.strictEqual(btn.attrs['aria-pressed'],'true');
form.listeners.submit[0]();
assert.strictEqual(inp.type,'password'); assert.strictEqual(btn.attrs['aria-label'],'Mostrar senha');
btn.listeners.click[0](); listeners.pagehide();
assert.strictEqual(inp.type,'password'); assert.strictEqual(btn.attrs['aria-pressed'],'false');
console.log('ok');
""", encoding="utf-8")
    r = subprocess.run(["node", str(harness), str(JS)], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "ok" in r.stdout, r.stderr
