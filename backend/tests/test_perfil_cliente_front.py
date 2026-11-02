"""Tela Meu perfil (DP-93 a DP-99): referencias de arquivo, matriz de menu e sintaxe em node."""
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from app.permissoes import MATRIZ_FUNCIONALIDADES

FRONT = Path(__file__).resolve().parents[2] / "frontend"


def ler(*p) -> str:
    return FRONT.joinpath(*p).read_text(encoding="utf-8")


def test_menu_meu_perfil_para_os_cinco_perfis():
    """DP-101, DP-102: Administrador e Funcionario tambem (depende da matriz do back-end)."""
    quem = {p for p, i in MATRIZ_FUNCIONALIDADES.items() if "meu_perfil" in i}
    assert quem == {"Administrador", "Funcionário", "Cliente Empresa", "Cliente ONG", "Empresa Doadora"}
    assert re.search(r"chave: 'meu_perfil'.*perfil/index\.html", ler("js", "layout.js"))


def test_pagina_referencias_e_rotas():
    h = ler("app", "perfil", "index.html")
    for s in ("js/api.js", "js/layout.js", "js/usuarios-comum.js", "js/organizacoes-comum.js", "js/senha-olho.js",
              "js/perfil.js", "css/identidade.css", "UC02", "UC06"):
        assert s in h
    assert "Para alterar CNPJ, tipo ou situação, fale com o Administrador." in h
    assert 'id="o-cnpj" readonly' in h and 'id="c-perfil" readonly' in h
    j = ler("js", "perfil.js")
    for s in ("'/usuarios/me'", "'/usuarios/me/senha'", "'/organizacao'", "Senha alterada.",
              "A nova senha não pode ser igual à atual.", "abrirExclusaoConta", "chave: 'meu_perfil'"):
        assert s in j
    assert "innerHTML" not in j and "alert(" not in j


def test_perfil_admin_funcionario_sem_organizacao():
    """DP-102: Administrador/Funcionario nao chamam GET /organizacao e nao veem a secao de organizacao."""
    j = ler("js", "perfil.js")
    i = j.index("'Administrador'")
    assert "return;" in j[i:i + 400] and j.index("carregarOrg();") > i
    h = ler("app", "perfil", "index.html")
    for s in ('id="secao-org"', 'id="grupo-org"', 'id="secao-excluir"'):
        assert s in h


def test_layout_mantem_exclusao_no_menu_so_sem_meu_perfil():
    t = ler("js", "layout.js")
    assert "indexOf('meu_perfil') === -1" in t and "usuario.perfil === 'Administrador'" in t and "abrirExclusaoConta" in t and "modal-excluir-conta" in t


def test_perfil_js_sintaxe_valida():
    if not shutil.which("node"):
        pytest.skip("node ausente")
    r = subprocess.run(["node", "--check", str(FRONT / "js" / "perfil.js")], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr


def test_correcoes_e2e_p01_a_p04():
    j, h, t = ler("js", "perfil.js"), ler("app", "perfil", "index.html"), ler("js", "layout.js")
    assert "$('c-org').value = org.nome_razao_social" in j  # P-01
    assert "col-md-4" not in h  # P-02
    assert 'id="s-nova" maxlength' not in h and "A senha deve ter de 8 a 128 caracteres." in j  # P-04
    assert "link-meu-perfil" in t  # P-03
