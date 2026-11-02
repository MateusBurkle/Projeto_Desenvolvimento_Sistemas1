"""Testes do Modulo 0 (Fundacao): UC04 Acessar o sistema, UC28 Validar credenciais.
Requisitos: RF01, RN01, RN06, RN09, RNF03, RNF04, RNF05. Contrato: contratos/modulo-0.yaml.
Nao cobre usuario de cliente sem organizacao (DP-08 pendente)."""
import sqlite3
from datetime import datetime, timedelta, timezone

import jwt
import pytest
from fastapi import Depends

from tests.conftest import SEGREDO_TESTE, SENHA, USUARIOS, fazer_login

LOGIN = "/api/v1/auth/login"
ME = "/api/v1/auth/me"

MATRIZ = {
    "Administrador": ["usuarios", "organizacoes", "parceiros", "categorias", "equipamentos",
                      "solicitacoes", "vendas", "notas_fiscais", "relatorios", "solicitacoes_doacao", "meu_perfil"],
    "Funcionário": ["organizacoes", "equipamentos", "solicitacoes", "vendas", "relatorios", "solicitacoes_doacao", "meu_perfil"],
    "Cliente Empresa": ["catalogo", "minhas_compras", "minhas_notas_fiscais", "usuarios_organizacao", "meu_perfil"],
    "Cliente ONG": ["minhas_doacoes", "solicitacoes_doacao", "usuarios_organizacao", "meu_perfil"],
    "Empresa Doadora": ["minhas_solicitacoes", "meu_perfil"],
}
ATIVOS = ["admin", "func", "empresa", "ong", "doadora"]


def _erro_padrao(corpo):
    assert set(corpo.keys()) == {"codigo", "mensagem", "campos"}
    assert isinstance(corpo["mensagem"], str) and corpo["mensagem"]
    assert isinstance(corpo["campos"], dict)


def _token(usuario_id, perfil="Administrador", segredo=SEGREDO_TESTE, exp=None):
    agora = datetime.now(timezone.utc)
    claims = {"sub": str(usuario_id), "perfil": perfil, "id_organizacao": None, "iat": agora,
              "exp": exp or agora + timedelta(minutes=5)}
    return jwt.encode(claims, segredo, algorithm="HS256")


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _sql(cliente, comando, params=()):
    con = sqlite3.connect(cliente.caminho_banco)
    con.execute(comando, params)
    con.commit()
    con.close()


# ------------------------------------------------ UC04 fluxo principal / UC28 sucesso
@pytest.mark.parametrize("chave", ATIVOS)
def test_login_valido_por_perfil(cliente, chave):
    # UC04 fluxo principal, UC28 passo 3, RF01, RN01
    r = fazer_login(cliente, chave)
    assert r.status_code == 200
    corpo = r.json()
    perfil = USUARIOS[chave][0]
    assert corpo["token_type"] == "bearer"
    assert corpo["expires_in"] == 3600  # DP-04: 60 minutos
    assert corpo["access_token"]
    u = corpo["usuario"]
    assert u["perfil"] == perfil and u["email"] == USUARIOS[chave][3]
    assert u["funcionalidades"] == MATRIZ[perfil]  # RN01
    if perfil in ("Administrador", "Funcionário"):
        assert u["id_organizacao"] is None
    else:
        assert isinstance(u["id_organizacao"], int)


def test_token_emitido_tem_claims_do_contrato(cliente):
    # UC04 passo 4, DP-04: claims sub, perfil, id_organizacao, iat, exp (HS256, 60 min)
    corpo = fazer_login(cliente, "empresa").json()
    claims = jwt.decode(corpo["access_token"], SEGREDO_TESTE, algorithms=["HS256"])
    assert claims["sub"] == str(corpo["usuario"]["id_usuario"])
    assert claims["perfil"] == "Cliente Empresa"
    assert claims["id_organizacao"] == corpo["usuario"]["id_organizacao"]
    assert claims["exp"] - claims["iat"] == 3600
    assert jwt.get_unverified_header(corpo["access_token"])["alg"] == "HS256"
    assert set(claims) == {"sub", "perfil", "id_organizacao", "iat", "exp"}  # RNF03: sem senha/hash


@pytest.mark.parametrize("email", ["ADMIN@TESTE.COM", "  admin@teste.com  ", " Admin@Teste.Com\t"])
def test_email_case_insensitive_e_com_espacos(cliente, email):
    # UC28 passo 1, contrato /auth/login
    r = cliente.post(LOGIN, json={"email": email, "senha": SENHA})
    assert r.status_code == 200
    assert r.json()["usuario"]["email"] == "admin@teste.com"


def test_senha_diferencia_maiusculas(cliente):
    # UC28 passo 2: a senha NAO e case-insensitive
    assert fazer_login(cliente, "admin", SENHA.lower()).status_code == 401


# ------------------------------------------------ UC04 FE1 / UC28 FE1
def test_401_email_inexistente_e_senha_errada_sao_identicos(cliente):
    # UC04 FE1, UC28 FE1, DP-05: nao revelar se o e-mail existe
    r_senha = cliente.post(LOGIN, json={"email": "admin@teste.com", "senha": "errada-errada"})
    r_email = cliente.post(LOGIN, json={"email": "nao-existe@teste.com", "senha": "errada-errada"})
    assert r_senha.status_code == r_email.status_code == 401
    assert r_senha.json() == r_email.json()
    assert r_senha.json()["codigo"] == "CREDENCIAIS_INVALIDAS"
    assert r_senha.json()["mensagem"] == "Não foi possível entrar. Verifique o e-mail e a senha."
    _erro_padrao(r_senha.json())


def test_401_email_inexistente_mesmo_com_senha_valida_de_outro_usuario(cliente):
    # UC28 FE1: conta nao encontrada
    r = cliente.post(LOGIN, json={"email": "fantasma@teste.com", "senha": SENHA})
    assert r.status_code == 401 and r.json()["codigo"] == "CREDENCIAIS_INVALIDAS"


def test_falha_nao_emite_token_nem_sessao(cliente):
    # UC04 FE1, UC28 FE1: sem sessao em falha
    for corpo_req in (
        {"email": "admin@teste.com", "senha": "errada-errada"},
        {"email": "x@teste.com", "senha": "qualquer"},
        {"email": "inativo@teste.com", "senha": SENHA},
        {"email": "invalido", "senha": SENHA},
    ):
        r = cliente.post(LOGIN, json=corpo_req)
        assert r.status_code in (400, 401, 403)
        assert "access_token" not in r.text and "usuario" not in r.json()


# ------------------------------------------------ UC04 FE2
def test_403_conta_inativa_com_senha_correta(cliente):
    # UC04 FE2, UC28 FE1, RN06, RN09, DP-02, DP-03, DP-05
    r = fazer_login(cliente, "inativo")
    assert r.status_code == 403
    assert r.json()["codigo"] == "CONTA_INATIVA"
    assert r.json()["mensagem"] == "Acesso negado. A conta ou a organização está inativa."
    _erro_padrao(r.json())
    assert "access_token" not in r.text


def test_conta_inativa_com_senha_errada_devolve_401_nao_403(cliente):
    # DP-05: 403 so apos senha correta
    r = fazer_login(cliente, "inativo", "senha-errada-123")
    assert r.status_code == 401 and r.json()["codigo"] == "CREDENCIAIS_INVALIDAS"
    ref = cliente.post(LOGIN, json={"email": "nao-existe@x.com", "senha": "senha-errada-123"})
    assert r.json() == ref.json()


@pytest.mark.parametrize("situacao", ["Inativa", "inativa", "Desativada", ""])
def test_situacao_diferente_de_ativa_bloqueia(cliente, situacao):
    # DP-03: so 'Ativa' libera acesso
    _sql(cliente, "UPDATE ORGANIZACAO SET situacao = ? WHERE nome_razao_social = 'ONG Cliente'", (situacao,))
    assert fazer_login(cliente, "ong").status_code == 403


def test_admin_e_funcionario_sempre_ativos_mesmo_com_orgs_inativas(cliente):
    # DP-02: Administrador/Funcionario sem organizacao sao sempre ativos
    _sql(cliente, "UPDATE ORGANIZACAO SET situacao = 'Inativa'")
    assert fazer_login(cliente, "admin").status_code == 200
    assert fazer_login(cliente, "func").status_code == 200
    assert fazer_login(cliente, "empresa").status_code == 403
    assert fazer_login(cliente, "doadora").status_code == 403


# ------------------------------------------------ RNF04 / 400
@pytest.mark.parametrize("corpo, campo", [
    ({"senha": SENHA}, "email"),
    ({"email": "admin@teste.com"}, "senha"),
    ({"email": "sem-arroba", "senha": SENHA}, "email"),
    ({"email": "a@b", "senha": SENHA}, "email"),
    ({"email": "", "senha": SENHA}, "email"),
    ({"email": "admin@teste.com", "senha": ""}, "senha"),
    ({"email": "a" * 250 + "@teste.com", "senha": SENHA}, "email"),
    ({"email": "admin@teste.com", "senha": "x" * 129}, "senha"),
    ({"email": 123, "senha": SENHA}, "email"),
])
def test_400_dados_invalidos(cliente, corpo, campo):
    # RNF04, UC04 passo 2: campos obrigatorios/formato
    r = cliente.post(LOGIN, json=corpo)
    assert r.status_code == 400
    j = r.json()
    assert j["codigo"] == "DADOS_INVALIDOS"
    assert campo in j["campos"]
    _erro_padrao(j)


def test_400_corpo_vazio_e_json_invalido(cliente):
    # RNF04
    assert cliente.post(LOGIN, json={}).status_code == 400
    r = cliente.post(LOGIN, content="{nao e json", headers={"Content-Type": "application/json"})
    assert r.status_code == 400 and r.json()["codigo"] == "DADOS_INVALIDOS"
    r = cliente.post(LOGIN)
    assert r.status_code == 400 and r.json()["codigo"] == "DADOS_INVALIDOS"


def test_400_nao_ecoa_a_senha(cliente):
    # RNF03, contrato: a senha nunca e devolvida
    senha = "S3nh@-Secreta-" + "x" * 130  # mais de 128 caracteres: invalida
    r = cliente.post(LOGIN, json={"email": "sem-arroba", "senha": senha})
    assert r.status_code == 400
    assert senha not in r.text and "S3nh@-Secreta" not in r.text
    r = cliente.post(LOGIN, json={"email": 5, "senha": SENHA})
    assert r.status_code == 400 and SENHA not in r.text


def test_senha_nunca_ecoada_em_nenhuma_resposta_de_login(cliente):
    # RNF03
    for r in (fazer_login(cliente, "admin"), fazer_login(cliente, "admin", "Errada-Errada-1"),
              fazer_login(cliente, "inativo")):
        assert "Errada-Errada-1" not in r.text
        assert SENHA not in r.text


def test_bcrypt_considera_so_72_bytes():
    # DP-09(c): truncamento explicito documentado (pendente de decisao, apenas registra o comportamento)
    from app.seguranca import gerar_hash_senha, verificar_senha
    h = gerar_hash_senha("a" * 100)
    assert verificar_senha("a" * 72, h) is True


# ------------------------------------------------ /auth/me
@pytest.mark.parametrize("chave", ATIVOS)
def test_me_200_por_perfil(cliente, token_de, chave):
    # UC04 passo 4, RN01, RNF05
    r = cliente.get(ME, headers=_auth(token_de(cliente, chave)))
    assert r.status_code == 200
    j = r.json()
    perfil = USUARIOS[chave][0]
    assert j["perfil"] == perfil and j["email"] == USUARIOS[chave][3]
    assert j["funcionalidades"] == MATRIZ[perfil]
    assert set(j) == {"id_usuario", "nome", "email", "perfil", "id_organizacao", "funcionalidades"}


def test_me_sem_token_401(cliente):
    # RNF05, contrato /auth/me 401
    r = cliente.get(ME)
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"
    assert r.json()["mensagem"] == "Sessão inválida ou expirada. Entre novamente."
    _erro_padrao(r.json())


@pytest.mark.parametrize("cabecalho", ["Bearer lixo", "Bearer ", "Basic abc", "abc.def.ghi", "Bearer a.b.c"])
def test_me_token_malformado_401(cliente, cabecalho):
    # RNF05
    r = cliente.get(ME, headers={"Authorization": cabecalho})
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"


def test_me_token_expirado_401(cliente):
    # RNF05, DP-04
    exp = datetime.now(timezone.utc) - timedelta(minutes=1)
    r = cliente.get(ME, headers=_auth(_token(1, exp=exp)))
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"


def test_me_token_assinatura_errada_401(cliente):
    # RNF05
    r = cliente.get(ME, headers=_auth(_token(1, segredo="outro-segredo-qualquer-com-32-bytes!!")))
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"


def test_me_token_alg_none_401(cliente):
    # RNF05: token sem assinatura nao e aceito
    claims = {"sub": "1", "perfil": "Administrador", "exp": datetime.now(timezone.utc) + timedelta(minutes=5)}
    r = cliente.get(ME, headers=_auth(jwt.encode(claims, None, algorithm="none")))
    assert r.status_code == 401


def test_me_token_sem_exp_ou_sub_401(cliente):
    # RNF05, DP-04: exp e sub obrigatorios
    sem_exp = jwt.encode({"sub": "1"}, SEGREDO_TESTE, algorithm="HS256")
    sem_sub = jwt.encode({"exp": datetime.now(timezone.utc) + timedelta(minutes=5)}, SEGREDO_TESTE, algorithm="HS256")
    assert cliente.get(ME, headers=_auth(sem_exp)).status_code == 401
    assert cliente.get(ME, headers=_auth(sem_sub)).status_code == 401


def test_me_usuario_inexistente_401(cliente):
    # RNF05: token valido de usuario removido/inexistente
    r = cliente.get(ME, headers=_auth(_token(99999)))
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"


def test_me_organizacao_desativada_depois_do_login_403(cliente, token_de):
    # UC04 FE2, RN06, RN09: /auth/me reavalia a conta a cada chamada
    token = token_de(cliente, "empresa")
    assert cliente.get(ME, headers=_auth(token)).status_code == 200
    _sql(cliente, "UPDATE ORGANIZACAO SET situacao = 'Inativa' WHERE nome_razao_social = 'Empresa Cliente'")
    r = cliente.get(ME, headers=_auth(token))
    assert r.status_code == 403 and r.json()["codigo"] == "CONTA_INATIVA"
    _erro_padrao(r.json())


def test_me_usa_perfil_do_banco_e_nao_o_do_token(cliente):
    # RN01, RNF05: perfil forjado no claim nao eleva privilegio
    id_func = fazer_login(cliente, "func").json()["usuario"]["id_usuario"]
    r = cliente.get(ME, headers=_auth(_token(id_func, perfil="Administrador")))
    assert r.status_code == 200 and r.json()["perfil"] == "Funcionário"


# ------------------------------------------------ RNF03 senha
def test_respostas_nunca_contem_senha_ou_hash(cliente):
    # RNF03, contrato UsuarioSessao
    con = sqlite3.connect(cliente.caminho_banco)
    hashes = [h for (h,) in con.execute("SELECT senha_hash FROM USUARIO")]
    con.close()
    for chave in ATIVOS:
        r1 = fazer_login(cliente, chave)
        r2 = cliente.get(ME, headers=_auth(r1.json()["access_token"]))
        for r in (r1, r2):
            assert "senha" not in r.text.lower()
            assert "hash" not in r.text.lower()
            assert SENHA not in r.text
            assert not any(h in r.text for h in hashes)


def test_senha_hash_no_banco_e_bcrypt_e_nao_contem_a_senha(cliente):
    # RNF03: consulta direta ao banco nao revela a senha
    con = sqlite3.connect(cliente.caminho_banco)
    linhas = con.execute("SELECT senha_hash FROM USUARIO").fetchall()
    con.close()
    assert len(linhas) == len(USUARIOS)
    for (h,) in linhas:
        assert h.startswith(("$2b$", "$2a$", "$2y$")) and len(h) == 60
        assert SENHA not in h


def test_carga_inicial_do_admin_grava_somente_hash(ambiente):
    # RNF03, DP-04: carga inicial grava bcrypt e e-mail normalizado; rejeita e-mail duplicado
    from app.auth import service
    from app.db import conectar, inicializar_banco
    inicializar_banco()
    con = conectar()
    try:
        service.criar_administrador_inicial(con, " Fulano ", " ADM@Teste.COM ", "SenhaQualquer99")
        row = con.execute("SELECT email, perfil, senha_hash, id_organizacao, nome FROM USUARIO").fetchone()
        assert row["email"] == "adm@teste.com" and row["perfil"] == "Administrador"
        assert row["id_organizacao"] is None and row["nome"] == "Fulano"
        assert row["senha_hash"].startswith("$2") and "SenhaQualquer99" not in row["senha_hash"]
        with pytest.raises(ValueError):
            service.criar_administrador_inicial(con, "Outro", "adm@teste.com", "OutraSenha99")
    finally:
        con.close()


def test_hashes_do_mesmo_texto_diferem_por_sal():
    # RNF03: hash com sal
    from app.seguranca import gerar_hash_senha
    assert gerar_hash_senha("abc12345") != gerar_hash_senha("abc12345")


# ------------------------------------------------ e-mail unico (banco)
def test_email_unico_no_banco(cliente):
    # RF01 (e-mail unico), USUARIO.email UNIQUE
    con = sqlite3.connect(cliente.caminho_banco)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (NULL,?,?,?,?)",
                    ("admin@teste.com", "Administrador", "x", "Dup"))
    con.close()


def test_perfil_invalido_rejeitado_pelo_banco(cliente):
    # RF02 (todo usuario deve ter perfil valido), CHECK de USUARIO.perfil
    con = sqlite3.connect(cliente.caminho_banco)
    with pytest.raises(sqlite3.IntegrityError):
        con.execute("INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (NULL,?,?,?,?)",
                    ("novo@teste.com", "Hacker", "x", "Novo"))
    con.close()


def test_email_duplicado_por_caixa_nao_derruba_o_login(cliente, hash_senha):
    # RF01: UNIQUE do SQLite e sensivel a caixa (divergencia potencial a registrar para o Modulo 1).
    # Aqui so se garante que o login nao quebra (sem 500) quando existem 'a@x' e 'A@x'.
    _sql(cliente, "INSERT INTO USUARIO (id_organizacao, email, perfil, senha_hash, nome) VALUES (NULL,?,?,?,?)",
         ("ADMIN@teste.com", "Administrador", hash_senha, "Duplicado"))
    assert cliente.post(LOGIN, json={"email": "admin@teste.com", "senha": SENHA}).status_code in (200, 401)


# ------------------------------------------------ exigir_perfis (RN01, RNF05)
@pytest.fixture()
def cliente_rotas(cliente):
    from app.dependencias import exigir_perfis
    app = cliente.app

    @app.get("/api/v1/_teste/admin")
    def so_admin(u: dict = Depends(exigir_perfis("Administrador"))):
        return {"ok": True}

    @app.get("/api/v1/_teste/interno")
    def interno(u: dict = Depends(exigir_perfis("Administrador", "Funcionário"))):
        return {"ok": True}

    return cliente


PERMITIDOS = {
    "/api/v1/_teste/admin": {"admin"},
    "/api/v1/_teste/interno": {"admin", "func"},
}


@pytest.mark.parametrize("rota", list(PERMITIDOS))
@pytest.mark.parametrize("chave", ATIVOS)
def test_exigir_perfis_autorizado_e_proibido(cliente_rotas, token_de, rota, chave):
    # RN01, RNF05: perfil autorizado passa; demais 403 SEM_PERMISSAO
    r = cliente_rotas.get(rota, headers=_auth(token_de(cliente_rotas, chave)))
    if chave in PERMITIDOS[rota]:
        assert r.status_code == 200
    else:
        assert r.status_code == 403
        assert r.json()["codigo"] == "SEM_PERMISSAO"
        _erro_padrao(r.json())


@pytest.mark.parametrize("rota", list(PERMITIDOS))
def test_exigir_perfis_sem_token_401(cliente_rotas, rota):
    # RNF05
    r = cliente_rotas.get(rota)
    assert r.status_code == 401 and r.json()["codigo"] == "NAO_AUTENTICADO"


def test_exigir_perfis_org_desativada_403_conta_inativa(cliente_rotas, token_de):
    # RN06, RN09: conta inativa tem prioridade sobre perfil
    token = token_de(cliente_rotas, "doadora")
    _sql(cliente_rotas, "UPDATE ORGANIZACAO SET situacao = 'Inativa'")
    r = cliente_rotas.get("/api/v1/_teste/admin", headers=_auth(token))
    assert r.status_code == 403 and r.json()["codigo"] == "CONTA_INATIVA"


# ------------------------------------------------ matriz de funcionalidades
def test_matriz_confere_com_contrato():
    # RN01..RN05: matriz do codigo = x-matriz-funcionalidades do contrato
    from app.permissoes import MATRIZ_FUNCIONALIDADES
    assert MATRIZ_FUNCIONALIDADES == MATRIZ


def test_matriz_rn02_rn03_so_admin_gerencia_usuarios_e_notas_fiscais():
    # RN02, RN03
    from app.permissoes import MATRIZ_FUNCIONALIDADES
    for perfil, itens in MATRIZ_FUNCIONALIDADES.items():
        if perfil != "Administrador":
            assert "usuarios" not in itens and "notas_fiscais" not in itens


def test_cliente_ong_nao_tem_funcionalidade_de_compra():
    # RN04 (contrato): ONG nao compra
    from app.permissoes import MATRIZ_FUNCIONALIDADES
    assert not {"catalogo", "minhas_compras"} & set(MATRIZ_FUNCIONALIDADES["Cliente ONG"])


def test_funcionalidades_perfil_desconhecido_vazia():
    # RN01
    from app.permissoes import funcionalidades_do_perfil
    assert funcionalidades_do_perfil("Hacker") == []


def test_funcionalidades_devolvidas_sao_copia():
    # RN01: alterar o retorno nao corrompe a matriz global
    from app.permissoes import MATRIZ_FUNCIONALIDADES, funcionalidades_do_perfil
    f = funcionalidades_do_perfil("Cliente ONG")
    f.append("usuarios")
    assert "usuarios" not in MATRIZ_FUNCIONALIDADES["Cliente ONG"]


# ------------------------------------------------ formato de erro padrao
def test_erro_404_formato_padrao(cliente):
    # docs/CONVENCOES.md, x-codigos-erro
    r = cliente.get("/api/v1/inexistente")
    assert r.status_code == 404 and r.json()["codigo"] == "NAO_ENCONTRADO"
    _erro_padrao(r.json())


def test_erro_405_formato_padrao(cliente):
    # docs/CONVENCOES.md, x-codigos-erro
    r = cliente.get(LOGIN)
    assert r.status_code == 405 and r.json()["codigo"] == "METODO_NAO_PERMITIDO"
    _erro_padrao(r.json())
    assert cliente.post(ME).status_code == 405


def test_erro_500_formato_padrao(cliente):
    # x-codigos-erro ERRO_INTERNO: sem vazar detalhes
    from fastapi.testclient import TestClient

    @cliente.app.get("/api/v1/_teste/boom")
    def boom():
        raise RuntimeError("segredo-interno")

    with TestClient(cliente.app, raise_server_exceptions=False) as c2:
        r = c2.get("/api/v1/_teste/boom")
    assert r.status_code == 500 and r.json()["codigo"] == "ERRO_INTERNO"
    assert "segredo-interno" not in r.text
    _erro_padrao(r.json())


def test_todos_os_erros_do_modulo_seguem_formato(cliente):
    # RNF04, convencoes
    respostas = [
        cliente.post(LOGIN, json={}),
        fazer_login(cliente, "admin", "errada-errada"),
        fazer_login(cliente, "inativo"),
        cliente.get(ME),
    ]
    for r in respostas:
        assert r.status_code >= 400
        _erro_padrao(r.json())


# ------------------------------------------------ configuracao (RNF05, DP-04)
def test_producao_exige_segredo_jwt(monkeypatch):
    # RNF05: sem segredo em producao a aplicacao nao sobe
    from app.config import obter_configuracao
    monkeypatch.setenv("LEAF_AMBIENTE", "producao")
    monkeypatch.delenv("LEAF_JWT_SECRET", raising=False)
    with pytest.raises(RuntimeError):
        obter_configuracao()


def test_token_expira_conforme_configuracao(cliente, monkeypatch):
    # DP-04: LEAF_TOKEN_MINUTOS controla a validade
    monkeypatch.setenv("LEAF_TOKEN_MINUTOS", "1")
    assert fazer_login(cliente, "admin").json()["expires_in"] == 60
