"""Modulo 0 - integracao API+front, script criar_admin, front estatico e paridade de menu.
UC04 (Acessar o sistema), UC28 (Validar credenciais); RF01, RN01 a RN05, RNF01, RNF03, RNF05, RNF06; DP-04 a DP-11.
Somente leitura do codigo de producao e do front. Senhas deste arquivo sao ficticias."""
import re
import shutil
import socket
import sqlite3
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import pytest

from tests.conftest import USUARIOS, fazer_login

RAIZ = Path(__file__).resolve().parents[2]
FRONT = RAIZ / "frontend"
CSS = FRONT / "css"
JS = FRONT / "js"
SENHA_FICTICIA = "SenhaFicticia#2026"


def ler(caminho: Path) -> str:
    return caminho.read_text(encoding="utf-8", errors="replace")


def htmls():
    return sorted(p for p in FRONT.rglob("*.html") if "_original" not in p.parts)


# --------------------------------------------------------------------------------------------------
# 1) Integracao: a API serve o front
# --------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("caminho", ["/login.html", "/app/inicio.html", "/index.html", "/css/identidade.css", "/js/api.js"])
def test_api_serve_front_estatico(cliente, caminho):
    # UC04 (tela de acesso servida na mesma origem da API)
    assert cliente.get(caminho).status_code == 200, caminho


def test_login_html_servido_contem_formulario(cliente):
    # UC04, RN01
    r = cliente.get("/login.html")
    assert 'id="login-form"' in r.text and "Entrar" in r.text


def test_api_inexistente_retorna_404_json_padrao(cliente):
    # UC04 / RNF04: /api/* inexistente nao cai no front; formato {codigo, mensagem, campos}
    r = cliente.get("/api/v1/inexistente")
    assert r.status_code == 404
    assert r.headers["content-type"].startswith("application/json")
    corpo = r.json()
    assert corpo["codigo"] == "NAO_ENCONTRADO"
    assert isinstance(corpo["mensagem"], str) and corpo["mensagem"]
    assert corpo["campos"] == {}


def test_docs_e_openapi_disponiveis(cliente):
    # RNF04 (documentacao da API)
    assert cliente.get("/docs").status_code == 200
    esquema = cliente.get("/openapi.json")
    assert esquema.status_code == 200
    assert "/api/v1/auth/login" in esquema.json()["paths"]
    assert "/api/v1/auth/me" in esquema.json()["paths"]


@pytest.mark.parametrize("chave", list(USUARIOS))
def test_fluxo_ponta_a_ponta_login_e_me(cliente, chave):
    # UC04 fluxo principal passos 1-4 / UC28; RN01 a RN05; FE2 para organizacao inativa
    perfil = USUARIOS[chave][0]
    r = fazer_login(cliente, chave)
    if chave == "inativo":
        assert r.status_code == 403 and r.json()["codigo"] == "CONTA_INATIVA"
        return
    assert r.status_code == 200
    token = r.json()["access_token"]
    me = cliente.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    corpo = me.json()
    assert corpo["perfil"] == perfil
    assert corpo["email"] == USUARIOS[chave][3]
    assert corpo["funcionalidades"] == r.json()["usuario"]["funcionalidades"]
    assert "senha" not in corpo and "senha_hash" not in corpo


def test_me_sem_token_retorna_401(cliente):
    # RNF05
    r = cliente.get("/api/v1/auth/me")
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"


# --------------------------------------------------------------------------------------------------
# 2) Script criar_admin (DP-04, RF02/RN02, RNF03)
# --------------------------------------------------------------------------------------------------
@pytest.fixture()
def rodar_script(ambiente, monkeypatch):
    for v in ("LEAF_ADMIN_EMAIL", "LEAF_ADMIN_NOME", "LEAF_ADMIN_SENHA"):
        monkeypatch.delenv(v, raising=False)
    from scripts import criar_admin

    def _rodar(*args):
        monkeypatch.setattr(sys, "argv", ["criar_admin", *args])
        return criar_admin.main()
    _rodar.banco = ambiente
    return _rodar


def _usuarios(banco):
    if not Path(banco).exists():
        return []
    con = sqlite3.connect(banco)
    con.row_factory = sqlite3.Row
    try:
        return con.execute("SELECT * FROM USUARIO").fetchall()
    except sqlite3.OperationalError:
        return []
    finally:
        con.close()


def test_criar_admin_cria_administrador_com_email_normalizado_e_hash_bcrypt(rodar_script):
    # DP-04, RNF03
    cod = rodar_script("--email", "  Chefe@Exemplo.COM ", "--nome", " Fulana Teste ", "--senha", SENHA_FICTICIA)
    assert cod == 0
    linhas = _usuarios(rodar_script.banco)
    assert len(linhas) == 1
    u = linhas[0]
    assert u["perfil"] == "Administrador"
    assert u["email"] == "chefe@exemplo.com"
    assert u["nome"] == "Fulana Teste"
    assert u["id_organizacao"] is None
    assert u["senha_hash"].startswith(("$2a$", "$2b$", "$2y$"))
    assert SENHA_FICTICIA not in u["senha_hash"]
    import bcrypt
    assert bcrypt.checkpw(SENHA_FICTICIA.encode(), u["senha_hash"].encode())


def test_criar_admin_nao_imprime_a_senha(rodar_script, capsys):
    # RNF03
    rodar_script("--email", "a@exemplo.com", "--nome", "A", "--senha", SENHA_FICTICIA)
    saida = capsys.readouterr()
    assert SENHA_FICTICIA not in saida.out + saida.err


def test_criar_admin_admin_criado_consegue_logar(rodar_script):
    # UC04, DP-04
    from fastapi.testclient import TestClient
    from app.main import criar_app
    assert rodar_script("--email", "Novo@Exemplo.com", "--nome", "Novo", "--senha", SENHA_FICTICIA) == 0
    with TestClient(criar_app()) as c:
        r = c.post("/api/v1/auth/login", json={"email": "novo@exemplo.com", "senha": SENHA_FICTICIA})
        assert r.status_code == 200
        assert r.json()["usuario"]["perfil"] == "Administrador"


@pytest.mark.parametrize("senha", ["1234567", "abc", "a"])
def test_criar_admin_rejeita_senha_menor_que_8(rodar_script, senha, capsys):
    # DP-09 (minimo 8), RNF03
    assert rodar_script("--email", "a@exemplo.com", "--nome", "A", "--senha", senha) == 1
    assert "senha" in capsys.readouterr().out.lower()
    assert _usuarios(rodar_script.banco) == []


def test_criar_admin_senha_digitada_vazia_e_rejeitada(rodar_script, monkeypatch):
    # DP-09: sem --senha o script pergunta no terminal; vazio e rejeitado
    import getpass
    monkeypatch.setattr(getpass, "getpass", lambda *_a, **_k: "")
    assert rodar_script("--email", "a@exemplo.com", "--nome", "A") == 1
    assert _usuarios(rodar_script.banco) == []


def test_criar_admin_rejeita_senha_maior_que_128(rodar_script):
    # DP-09
    assert rodar_script("--email", "a@exemplo.com", "--nome", "A", "--senha", "x" * 129) == 1


def test_criar_admin_aceita_senha_de_8_caracteres(rodar_script):
    # DP-09 (limite)
    assert rodar_script("--email", "a@exemplo.com", "--nome", "A", "--senha", "abcdefgh") == 0


@pytest.mark.parametrize("email", ["", "semarroba", "a@b", "a b@c.com"])
def test_criar_admin_rejeita_email_invalido(rodar_script, email, capsys):
    # DP-09 (regex simples de e-mail)
    args = ["--nome", "A", "--senha", SENHA_FICTICIA]
    if email:
        args += ["--email", email]
    assert rodar_script(*args) == 1
    assert "e-mail" in capsys.readouterr().out.lower()


def test_criar_admin_rejeita_nome_vazio(rodar_script):
    # DP-04
    assert rodar_script("--email", "a@exemplo.com", "--nome", "  ", "--senha", SENHA_FICTICIA) == 1


def test_criar_admin_nao_duplica_email_ignorando_caixa(rodar_script, capsys):
    # DP-04, RF01 (e-mail unico sem diferenciar caixa)
    assert rodar_script("--email", "dup@exemplo.com", "--nome", "A", "--senha", SENHA_FICTICIA) == 0
    assert rodar_script("--email", "DUP@Exemplo.com", "--nome", "B", "--senha", SENHA_FICTICIA) == 1
    assert "e-mail" in capsys.readouterr().out.lower()
    assert len(_usuarios(rodar_script.banco)) == 1


def test_criar_admin_le_variaveis_de_ambiente(ambiente, monkeypatch):
    # DP-04 (nada fixo no codigo): defaults do argparse vem de LEAF_ADMIN_*
    monkeypatch.setenv("LEAF_ADMIN_EMAIL", "env@exemplo.com")
    monkeypatch.setenv("LEAF_ADMIN_NOME", "Env")
    monkeypatch.setenv("LEAF_ADMIN_SENHA", SENHA_FICTICIA)
    from scripts import criar_admin
    monkeypatch.setattr(sys, "argv", ["criar_admin"])
    assert criar_admin.main() == 0
    assert _usuarios(ambiente)[0]["email"] == "env@exemplo.com"


def test_criar_admin_nao_tem_credenciais_fixas():
    # DP-04, RNF03
    codigo = ler(Path(__file__).resolve().parents[1] / "scripts" / "criar_admin.py")
    assert not re.search(r"default\s*=\s*['\"][^'\"]+@", codigo)


# --------------------------------------------------------------------------------------------------
# 3) Front estatico (leitura dos arquivos)
# --------------------------------------------------------------------------------------------------
def test_login_tem_campo_email_com_rotulo_e_sem_usuario():
    # UC04 passo 2 / DP-07
    h = ler(FRONT / "login.html")
    assert re.search(r'<input[^>]*type="email"[^>]*id="email"|<input[^>]*id="email"[^>]*type="email"', h)
    assert re.search(r'<label[^>]*for="email"[^>]*>\s*E-mail\s*</label>', h)
    assert not re.search(r"\bUsu[aá]rio\b", h)


def test_login_tem_botao_entrar_e_campo_senha_password():
    # UC04 passo 3 / DP-07
    h = ler(FRONT / "login.html")
    assert re.search(r'<button[^>]*type="submit"[^>]*>\s*Entrar\s*</button>', h)
    assert "Autenticar" not in h
    assert re.search(r'<input[^>]*type="password"', h)


def test_login_rotulos_associados_aos_campos():
    # RNF06 (acessibilidade)
    h = ler(FRONT / "login.html")
    for campo in ("email", "senha"):
        assert f'for="{campo}"' in h and f'id="{campo}"' in h


def test_fetch_somente_em_api_js_nos_arquivos_carregados_pelas_paginas():
    # UC04, RNF04 (um unico ponto de acesso a API). Considera os .js referenciados pelas paginas.
    usados = set()
    for h in htmls():
        texto = ler(h)
        for src in re.findall(r'<script[^>]+src="([^"]+)"', texto):
            if not src.startswith("http"):
                usados.add((h.parent / src).resolve())
        sem_externos = re.sub(r"<script[^>]+src=[^>]*>\s*</script>", "", texto)
        assert not re.search(r"\bfetch\s*\(", sem_externos), h.name
    assert (JS / "api.js").resolve() in usados
    for js in usados:
        if js.name != "api.js":
            assert not re.search(r"\bfetch\s*\(|XMLHttpRequest", ler(js)), js.name


def test_nenhum_js_do_front_alem_de_api_js_usa_fetch():
    # UC04, RNF04: api.js e o unico lugar com fetch (inclui js/scripts.js legado, mesmo orfao)
    com_fetch = [p.name for p in JS.glob("*.js") if p.name != "api.js" and re.search(r"\bfetch\s*\(", ler(p))]
    assert com_fetch == [], f"fetch fora de api.js: {com_fetch}"


def test_api_js_usa_base_api_v1_e_nenhum_outro_arquivo_a_repete():
    # UC04
    assert re.search(r"BASE\s*=\s*'/api/v1'", ler(JS / "api.js"))
    for p in list(JS.glob("*.js")) + htmls():
        if p.name != "api.js":
            assert "/api/v1" not in ler(p), p.name


def test_sessao_so_e_guardada_apos_sucesso_do_login():
    # UC04 FE1/FE2 (sem sessao em falha)
    api = ler(JS / "api.js")
    corpo_login = api[api.index("login: async function"):api.index("me: async function")]
    assert corpo_login.index("await requisicao") < corpo_login.index("sessao.salvar(")
    assert "try" not in corpo_login  # erro propaga antes de salvar
    login = ler(JS / "login.js")
    assert "sessao.salvar" not in login
    assert "Api.sessao.limpar()" in login.split("catch")[1]
    for p in JS.glob("*.js"):
        if p.name != "api.js":
            assert "sessao.salvar" not in ler(p), p.name


def test_token_em_sessionstorage_e_nao_localstorage():
    # DP-04 / DP-07
    api = ler(JS / "api.js")
    assert "sessionStorage" in api
    assert "localStorage" not in api


def test_api_js_nao_guarda_senha():
    # RNF03
    api = ler(JS / "api.js")
    trechos = re.findall(r"setItem\([^)]*\)", api)
    assert not any("senha" in t.lower() for t in trechos)


def _arquivos_do_projeto():
    ignorar = {".venv", "__pycache__", "relatorios", "_original", ".git", "node_modules", ".pytest_cache"}
    binarios = {".db", ".png", ".jpg", ".gif", ".ico", ".zip", ".docx", ".pyc", ".sqlite", ".svg", ".webp"}
    for p in RAIZ.rglob("*"):
        if not p.is_file() or ignorar & set(p.relative_to(RAIZ).parts):
            continue
        if p.suffix.lower() in binarios or p.resolve() == Path(__file__).resolve():
            continue
        yield p


def test_nenhuma_senha_ou_email_real_no_repositorio():
    # RNF03 / DP-04. Termos montados por concatenacao para este arquivo nao se autodenunciar.
    # admin@leafti.com.br (exemplo do contrato) e tratado no teste seguinte.
    senha_real = "LEAFTI" + "2026"
    email_real = re.compile(r"admin@leafti\.com(?!\.br)", re.I)
    achados = []
    for p in _arquivos_do_projeto():
        t = ler(p)
        if senha_real.lower() in t.lower() or email_real.search(t):
            achados.append(str(p.relative_to(RAIZ)))
    assert achados == []


def test_email_admin_do_dominio_leafti_so_aparece_como_exemplo_no_contrato():
    # RNF03. O contrato usa um e-mail de exemplo; qualquer outro arquivo com ele e suspeito.
    padrao = re.compile("admin@leafti" + r"\.com\.br", re.I)
    achados = {p.relative_to(RAIZ).as_posix() for p in _arquivos_do_projeto() if padrao.search(ler(p))}
    assert achados <= {"contratos/modulo-0.yaml"}, achados


def _luminancia(hexa: str) -> float:
    h = hexa.lstrip("#")
    canais = []
    for i in (0, 2, 4):
        c = int(h[i:i + 2], 16) / 255
        canais.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * canais[0] + 0.7152 * canais[1] + 0.0722 * canais[2]


def _contraste(a: str, b: str) -> float:
    la, lb = sorted((_luminancia(a), _luminancia(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def _bloco_css(css: str, seletor: str) -> str:
    m = re.search(re.escape(seletor) + r"\s*\{([^}]*)\}", css)
    assert m, f"bloco {seletor} ausente"
    return m.group(1)


def test_tokens_de_erro_declarados():
    # DP-06 revista: vermelho de erro permitido via token
    css = ler(CSS / "identidade.css")
    assert re.search(r"--leaf-erro\s*:\s*#9B1C1C\b", css, re.I)
    assert re.search(r"--leaf-erro-tint\s*:\s*#FDF0F0\b", css, re.I)


@pytest.mark.parametrize("fundo", ["#FDF0F0", "#FFFFFF"])
def test_contraste_do_vermelho_de_erro_minimo_4_5(fundo):
    # DP-06 revista, RNF06: contraste calculado >= 4,5:1
    assert _contraste("#9B1C1C", fundo) >= 4.5


def test_alert_danger_usa_token_e_tem_icone_e_prefixo_erro():
    # DP-06 revista, RNF06: informacao nao depende so de cor
    css = ler(CSS / "identidade.css")
    bloco = _bloco_css(css, ".alert-danger")
    assert "var(--leaf-erro)" in bloco and "var(--leaf-erro-tint)" in bloco
    m = re.search(r"\.alert-danger::before\s*\{[^}]*content\s*:\s*\"([^\"]*)\"", css)
    assert m, ".alert-danger::before ausente"
    assert "Erro:" in m.group(1)
    assert "26A0" in m.group(1).upper()  # icone de alerta


def test_alert_warning_continua_amarelo():
    # DP-11a: avisos nao criticos mantem amarelo
    css = ler(CSS / "identidade.css")
    bloco = _bloco_css(css, ".alert-warning")
    assert "var(--leaf-yellow)" in bloco and "var(--leaf-yellow-tint)" in bloco
    assert "leaf-erro" not in bloco


def test_login_js_usa_danger_para_erros_e_warning_para_sessao_expirada():
    # UC04 FE1/FE2, DP-06 revista, DP-11a
    js = ler(JS / "login.js")
    for codigo in ("CREDENCIAIS_INVALIDAS", "CONTA_INATIVA", "DADOS_INVALIDOS"):
        assert codigo in js, codigo
    assert "alert-danger" in js and "alert-warning" in js
    # tipo padrao (erros da API) e danger; so o tipo 'aviso' vira warning
    assert re.search(r"tipo\s*===\s*'aviso'\s*\?\s*'alert-warning'\s*:\s*'alert-danger'", js)
    # erros da API chamam mostrarAviso sem tipo 'aviso'
    catch = js.split("catch (err)")[1]
    assert "'aviso'" not in catch
    assert "mostrarAviso(err.mensagem" in catch
    # sessao expirada (leafti.aviso) usa 'aviso' -> warning
    assert re.search(r"mostrarAviso\(guardado,\s*'aviso'\)", js)
    assert 'class="alert alert-danger' in ler(FRONT / "login.html")


def test_vermelho_padrao_do_bootstrap_continua_proibido():
    # DP-06 revista: so o token --leaf-erro; #dc3545 proibido
    for p in list(CSS.glob("*.css")) + htmls() + list(JS.glob("*.js")):
        assert "#dc3545" not in ler(p).lower(), p.name
    # o token #9B1C1C so e declarado em identidade.css
    for p in list(CSS.glob("*.css")) + htmls() + list(JS.glob("*.js")):
        if p.name != "identidade.css":
            assert "#9b1c1c" not in ler(p).lower(), p.name


def test_logo_claro_existe_com_canal_alfa_e_original_preservado():
    # DP-11(b): variante para fundo escuro; original mantido
    import struct
    imgs = FRONT / "images"
    claro, original = imgs / "logosemfundo-claro.png", imgs / "logosemfundo.png"
    assert claro.exists() and original.exists()
    dados = claro.read_bytes()
    assert dados[:8] == b"\x89PNG\r\n\x1a\n"
    tipo_cor = struct.unpack(">B", dados[25:26])[0]  # IHDR: color type
    assert tipo_cor in (4, 6) or b"tRNS" in dados, f"sem canal alfa (color type {tipo_cor})"
    layout = ler(JS / "layout.js")
    assert "logosemfundo-claro.png" in layout
    assert not re.search(r"logosemfundo\.png", layout)


def test_variaveis_de_identidade_declaradas():
    # DP-10, DP-11, docs/IDENTIDADE_VISUAL.md
    css = ler(CSS / "identidade.css")
    esperado = {
        "--leaf-green": "#76D356", "--leaf-green-dark": "#31573F", "--leaf-blue": "#4A90E2",
        "--leaf-gray": "#505050", "--leaf-white": "#FFFFFF", "--leaf-yellow": "#FFC300",
        "--leaf-green-tint": "#F3F8F1", "--leaf-green-tint-2": "#D9E6DD",
        "--leaf-green-dark-hover": "#24402F", "--leaf-yellow-tint": "#FFF6D6",
    }
    for nome, cor in esperado.items():
        assert re.search(rf"{re.escape(nome)}\s*:\s*{cor}\b", css, re.I), nome


def test_fontes_playfair_e_source_sans():
    # IDENTIDADE_VISUAL (tipografia)
    css = ler(CSS / "identidade.css")
    assert "Playfair+Display" in css and "Source+Sans+3" in css
    assert re.search(r"--font-titulo\s*:\s*'Playfair Display'", css)
    assert re.search(r"--font-texto\s*:\s*'Source Sans 3'", css)


def test_fonte_base_minima_16px():
    # RNF01
    css = ler(CSS / "identidade.css")
    assert re.search(r"--bs-body-font-size\s*:\s*1rem", css)
    assert re.search(r"body\s*\{[^}]*font-size\s*:\s*1rem", css)


def _px(valor: str):
    m = re.fullmatch(r"([\d.]+)(rem|em|px)", valor.strip())
    if not m:
        return None
    n = float(m.group(1))
    return n if m.group(2) == "px" else n * 16


def test_nenhum_font_size_abaixo_de_16px_nos_css_do_modulo():
    # RNF01 (menu, selo "Em breve", rodape, campos, mensagens)
    for nome in ("identidade.css", "app.css", "login.css"):
        for valor in re.findall(r"font-size\s*:\s*([^;}]+)", ler(CSS / nome)):
            px = _px(valor)
            if px is not None:
                assert px >= 16, f"{nome}: font-size {valor}"


def test_menu_e_selo_sem_small_nem_fonte_menor():
    # RNF01: itens do menu e selo "Em breve"
    layout = ler(JS / "layout.js")
    assert not re.search(r"<small|\bsmall\b|font-size", layout, re.I)
    app_css = ler(CSS / "app.css")
    assert re.search(r"\.app \.navbar \.badge\s*\{[^}]*font-size\s*:\s*1rem", app_css)
    for h in (FRONT / "login.html", FRONT / "app" / "inicio.html"):
        assert not re.search(r"<small|class=\"[^\"]*\bsmall\b|font-size\s*:\s*0?\.\d+(rem|em)", ler(h), re.I), h.name


def test_alvos_de_toque_minimos_44px():
    # RNF06
    assert "min-height: 44px" in ler(CSS / "app.css")
    assert "min-height: 44px" in ler(CSS / "login.css")


def test_imagens_com_alt():
    # RNF06 (alt presente; vazio so se decorativa)
    for h in htmls():
        for tag in re.findall(r"<img\b[^>]*>", ler(h), re.I):
            assert re.search(r'\balt\s*=\s*"[^"]*"', tag), f"{h.name}: {tag}"
    for tag in re.findall(r"<img\b[^>]*>", ler(JS / "layout.js")):
        assert "alt=" in tag


def test_viewport_em_todos_os_htmls():
    # RNF06 (responsividade)
    for h in htmls():
        assert re.search(r'<meta\s+name="viewport"\s+content="[^"]*width=device-width', ler(h)), h.name


def test_html_lang_pt_br_nas_telas_do_modulo():
    # RNF04 (mensagens em portugues)
    for h in (FRONT / "login.html", FRONT / "app" / "inicio.html"):
        assert 'lang="pt-BR"' in ler(h)


def test_navbar_expand_xl_no_layout():
    # RNF06 (menu recolhido ate 1199px)
    layout = ler(JS / "layout.js")
    assert "navbar-expand-xl" in layout
    for ruim in ("navbar-expand-lg", "navbar-expand-md", "navbar-expand-sm"):
        assert ruim not in layout


def test_fundo_do_login_sem_imagem_pesada():
    # DP-07, DP-10
    assert "backgroundlindo" not in ler(CSS / "login.css")
    assert "backgroundlindo" not in ler(FRONT / "login.html")
    assert "backgroundlindo" not in ler(CSS / "identidade.css")
    assert not re.search(r"background(-image)?\s*:[^;]*url\(", ler(CSS / "login.css"))


def test_login_carrega_identidade_antes_do_css_da_tela_e_sem_legado():
    # DP-07
    h = ler(FRONT / "login.html")
    assert h.index("identidade.css") < h.index("login.css")
    assert "styles.css" not in h and "reset.css" not in h


def test_recursos_locais_referenciados_existem():
    # RNF04 (sem imagem/script/css quebrado nas telas do modulo)
    for h in (FRONT / "login.html", FRONT / "app" / "inicio.html"):
        for ref in re.findall(r'(?:src|href)="([^"#]+)"', ler(h)):
            if ref.startswith(("http", "mailto:")) or ref.endswith(".html"):
                continue
            assert (h.parent / ref).resolve().exists(), f"{h.name}: {ref}"


def test_inicio_usa_layout_e_guarda_de_rota():
    # UC04 passo 4, RNF05
    h = ler(FRONT / "app" / "inicio.html")
    assert "layout.js" in h and "Layout.iniciar" in h
    layout = ler(JS / "layout.js")
    assert "Api.sessao.ativa()" in layout and "urlLogin" in layout


def test_layout_esconde_itens_nao_permitidos_e_tem_botao_sair():
    # RN01, UC04
    layout = ler(JS / "layout.js")
    # UC04, RN01: o menu esconde o que o perfil nao tem (aceita a forma m.chave ou x.m.chave apos reordenacao do M1)
    assert re.search(r"permitidas\.indexOf\((?:x\.)?m\.chave\) !== -1", layout)
    assert "btn-sair" in layout and "Sair" in layout


def test_layout_itens_em_breve_sem_link():
    # UC04 passo 4 (modulos futuros)
    layout = ler(JS / "layout.js")
    assert "Em breve" in layout and "aria-disabled" in layout


# --------------------------------------------------------------------------------------------------
# 4) Paridade menu x matriz de permissoes (RN01 a RN05)
# --------------------------------------------------------------------------------------------------
def _chaves_do_menu():
    layout = ler(JS / "layout.js")
    ini = layout.index("var MENU = [")
    bloco = layout[ini:layout.index("];", ini)]
    return re.findall(r"chave:\s*'([a-z_]+)'", bloco)


def _chaves_da_matriz():
    from app.permissoes import MATRIZ_FUNCIONALIDADES
    return {c for lista in MATRIZ_FUNCIONALIDADES.values() for c in lista}


def test_chaves_do_menu_existem_na_matriz():
    # RN01
    assert set(_chaves_do_menu()) <= _chaves_da_matriz()


def test_chaves_da_matriz_aparecem_no_menu():
    # RN01 (nenhuma funcionalidade fica sem item de menu)
    assert _chaves_da_matriz() <= set(_chaves_do_menu())


def test_menu_sem_chaves_duplicadas():
    # RN01
    chaves = _chaves_do_menu()
    assert chaves and len(chaves) == len(set(chaves))


def test_matriz_do_backend_presente_no_contrato():
    # RN02 a RN05 (contrato x codigo)
    contrato = ler(RAIZ / "contratos" / "modulo-0.yaml")
    from app.permissoes import MATRIZ_FUNCIONALIDADES
    for perfil, chaves in MATRIZ_FUNCIONALIDADES.items():
        assert perfil in contrato
        for c in chaves:
            assert c in contrato, f"{c} ausente do contrato"


def test_me_devolve_somente_chaves_conhecidas_pelo_menu(cliente, token_de):
    # RN01, UC04 passo 4
    menu = set(_chaves_do_menu())
    for chave in ("admin", "func", "empresa", "ong", "doadora"):
        t = token_de(cliente, chave)
        me = cliente.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {t}"}).json()
        assert set(me["funcionalidades"]) <= menu


# --------------------------------------------------------------------------------------------------
# 5) E2E opcional com Edge/Chrome headless (pulado se indisponivel)
# --------------------------------------------------------------------------------------------------
def _navegador():
    candidatos = [
        shutil.which("msedge"), shutil.which("chrome"), shutil.which("google-chrome"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    ]
    return next((c for c in candidatos if c and Path(c).exists()), None)


@pytest.fixture()
def servidor(ambiente):
    uvicorn = pytest.importorskip("uvicorn")
    from app.main import criar_app
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        porta = s.getsockname()[1]
    srv = uvicorn.Server(uvicorn.Config(criar_app(), host="127.0.0.1", port=porta, log_level="warning"))
    th = threading.Thread(target=srv.run, daemon=True)
    th.start()
    for _ in range(100):
        if srv.started:
            break
        time.sleep(0.1)
    yield f"http://127.0.0.1:{porta}"
    srv.should_exit = True
    th.join(timeout=5)


def _dump_dom(exe, url):
    with tempfile.TemporaryDirectory() as perfil:
        r = subprocess.run(
            [exe, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={perfil}",
             "--virtual-time-budget=8000", "--dump-dom", url],
            capture_output=True, text=True, timeout=60, encoding="utf-8", errors="replace")
    return r.stdout


@pytest.mark.e2e
def test_e2e_navegador_login_renderiza_e_area_logada_exige_sessao(servidor):
    # UC04, RNF05: tela de login renderiza; /app/inicio.html sem sessao redireciona ao login
    exe = _navegador()
    if not exe:
        pytest.skip("Chrome/Edge headless indisponivel")
    dom = _dump_dom(exe, servidor + "/login.html")
    if "login-form" not in dom:
        pytest.skip("Navegador nao devolveu o DOM (ambiente sem suporte a --dump-dom)")
    assert "E-mail" in dom and "Entrar" in dom
    dom2 = _dump_dom(exe, servidor + "/app/inicio.html")
    assert "login-form" in dom2
