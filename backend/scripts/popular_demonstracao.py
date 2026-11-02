"""Carga de dados de DEMONSTRACAO do LEAF TI (todos fictícios; só para apresentação local).

Uso (dentro de backend/, com o ambiente virtual ativo):
    python -m scripts.popular_demonstracao              # cria o que falta (idempotente)
    python -m scripts.popular_demonstracao --reiniciar  # apaga o arquivo de LEAF_DB_PATH (pede SIM) e recarrega

Cria tudo pela API (TestClient), respeitando as regras de negócio; não faz INSERT direto
(única exceção: o primeiro Administrador, pelo mesmo serviço do scripts.criar_admin).
Recusa rodar com LEAF_AMBIENTE=producao. Imagens: armazenamento/imagens/demo/ (enviadas pelo upload da API).
UC01-UC21, UC30 (cadastros, avaliação, doação, vendas, notas, solicitações de doação); RN10, RN12, RN13, RN14.
"""
import argparse
import os
import sys
from datetime import date, timedelta
from pathlib import Path

if os.environ.get("LEAF_AMBIENTE", "").strip().lower() == "producao":  # antes de importar a aplicação
    print("Recusado: LEAF_AMBIENTE=producao. Os dados de demonstração só podem ser usados localmente.")
    sys.exit(1)

from fastapi.testclient import TestClient  # noqa: E402

from app import db  # noqa: E402
from app.config import RAIZ_PROJETO, obter_configuracao  # noqa: E402
from app.main import app  # noqa: E402
from app.usuarios import service as usuarios_service  # noqa: E402
from scripts.popular_usuarios_teste import cnpj  # noqa: E402

# Exceção consciente do manifesto de publicação: senha FICTÍCIA de demonstração, única constante do código.
SENHA_DEMO_PADRAO = "Demo@Folha2026"
PASTA_IMAGENS = RAIZ_PROJETO / "armazenamento" / "imagens" / "demo"
API = "/api/v1"
TABELAS = ["USUARIO", "ORGANIZACAO", "PARCEIRO", "CATEGORIA", "EQUIPAMENTO", "SOLICITACAO", "ITEM_SOLICITACAO",
           "DOACAO", "VENDA", "ITEM_VENDA", "NOTA_FISCAL_SIMULADA", "SOLICITACAO_DOACAO", "ITEM_SOLICITACAO_DOACAO"]

HOJE = date.today()


def dia(n: int) -> str:
    """Data ISO de n dias atrás."""
    return (HOJE - timedelta(days=n)).isoformat()


class Falha(Exception):
    pass


class Demo:
    def __init__(self, c: TestClient, senha: str):
        self.c, self.senha = c, senha
        self.tokens: dict = {}
        self.logins: list = []  # (email, perfil, organização)

    # ---- infraestrutura -------------------------------------------------
    def h(self, email: str) -> dict:
        if email not in self.tokens:
            r = self.c.post(f"{API}/auth/login", json={"email": email, "senha": self.senha})
            if r.status_code != 200:
                raise Falha(f"login de {email} falhou ({r.status_code}): {r.text}. "
                            "Se a senha de demonstração mudou, use --reiniciar.")
            self.tokens[email] = {"Authorization": "Bearer " + r.json()["access_token"]}
        return self.tokens[email]

    def chamar(self, metodo: str, caminho: str, email: str, esperado=(200, 201, 204), **kw):
        r = self.c.request(metodo, API + caminho, headers=self.h(email), **kw)
        if r.status_code not in esperado:
            raise Falha(f"{metodo} {caminho} -> {r.status_code}: {r.text}")
        return r

    # ---- cadastros -------------------------------------------------------
    def organizacao(self, nome, tipo, base, email, telefone, endereco) -> int:
        lista = self.chamar("GET", "/organizacoes?size=100", ADMIN).json()["items"]
        achada = next((o for o in lista if o["nome_razao_social"] == nome), None)
        if achada:
            return achada["id_organizacao"]
        r = self.chamar("POST", "/organizacoes", ADMIN, json={
            "nome_razao_social": nome, "tipo": tipo, "cnpj": cnpj(base), "telefone": telefone,
            "email": email, "endereco": endereco})
        return r.json()["id_organizacao"]

    def parceria(self, id_org, tipo, situacao="Ativa"):
        lista = self.chamar("GET", "/parceiros?size=100", ADMIN).json()["items"]
        p = next((x for x in lista if x["id_organizacao"] == id_org), None)
        if p is None:
            p = self.chamar("POST", "/parceiros", ADMIN, json={"id_organizacao": id_org, "tipo_parceria": tipo}).json()
        if situacao != p["situacao_parceria"]:
            self.chamar("PATCH", f"/parceiros/{p['id_parceiro']}/situacao", ADMIN, json={"situacao_parceria": situacao})

    def usuario(self, nome, email, perfil, id_org):
        r = self.chamar("POST", "/usuarios", ADMIN, esperado=(201, 409), json={
            "nome": nome, "email": email, "senha": self.senha, "perfil": perfil, "id_organizacao": id_org})
        self.logins.append((email, perfil))
        return r.status_code == 201

    def categoria(self, nome, ativa=True) -> int:
        lista = self.chamar("GET", "/categorias?size=100", ADMIN).json()["items"]
        cat = next((x for x in lista if x["nome"].casefold() == nome.casefold()), None)
        if cat is None:
            cat = self.chamar("POST", "/categorias", ADMIN, json={"nome": nome}).json()
        if cat["ativa"] != ativa:
            self.chamar("PATCH", f"/categorias/{cat['id_categoria']}/situacao", ADMIN, json={"ativa": ativa})
        return cat["id_categoria"]

    def equipamentos_existentes(self) -> dict:
        itens = self.chamar("GET", "/equipamentos?q=DEMO-&size=100", ADMIN).json()["items"]
        return {e["identificacao"]: e["id_equipamento"] for e in itens}

    def imagem(self, id_eq: int, arquivo: str):
        dados = (PASTA_IMAGENS / arquivo).read_bytes()
        self.chamar("PUT", f"/equipamentos/{id_eq}/imagem", ADMIN, files={"arquivo": (arquivo, dados, "image/jpeg")})

    def equipamento(self, ident, id_cat, modelo, cond, origem, recebido, valor=None, situacao=None, img=None) -> int:
        corpo = {"identificacao": ident, "id_categoria": id_cat, "modelo": modelo, "condicao": cond,
                 "origem": origem, "data_recebimento": recebido}
        if valor is not None:
            corpo["valor"] = valor
        if situacao:
            corpo["situacao"] = situacao
        id_eq = self.chamar("POST", "/equipamentos", ADMIN, json=corpo).json()["id_equipamento"]
        if img:
            self.imagem(id_eq, img)
        return id_eq


ADMIN = "admin@leafti.test"
ADMIN2 = "admin2@leafti.test"
FUNC = "funcionario@leafti.test"
EMPRESA = "empresa@leafti.test"
ONG = "ong@leafti.test"
DOADORA = "doadora@leafti.test"


def contar(conexao) -> dict:
    return {t: conexao.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in TABELAS}  # nomes fixos acima


def carregar(d: Demo):
    # ---------- organizações e parcerias (UC01, UC06; RN10) ----------
    ids = {}
    orgs = [  # chave, nome, tipo, base do CNPJ, e-mail, telefone, endereço
        ("ce_a", "Horizonte Tecnologia Ltda", "Cliente Empresa", 50000001, "contato@horizonte.test", "(11) 4000-1001", "Av. Exemplo, 100, São Paulo - SP"),
        ("ce_b", "Aurora Escritórios Ltda", "Cliente Empresa", 50000002, "contato@aurora.test", "(21) 4000-1002", "Rua das Flores, 25, Rio de Janeiro - RJ"),
        ("ong_a", "ONG Conecta Futuro", "Cliente ONG", 50000003, "contato@conectafuturo.test", "(31) 94000-1003", "Rua da Esperança, 42, Belo Horizonte - MG"),
        ("ong_b", "ONG Bytes do Bem", "Cliente ONG", 50000004, "contato@bytesdobem.test", "(41) 94000-1004", "Praça Central, 7, Curitiba - PR"),
        ("ed_a", "Recicla Corp Doadora S.A.", "Empresa Doadora", 50000005, "contato@reciclacorp.test", "(11) 4000-1005", "Av. Industrial, 900, Campinas - SP"),
        ("ed_b", "Verde Digital Ltda", "Empresa Doadora", 50000006, "contato@verdedigital.test", "(51) 4000-1006", "Rua do Comércio, 18, Porto Alegre - RS"),
        ("ed_c", "Nimbus Antiga Doadora Ltda", "Empresa Doadora", 50000007, "contato@nimbus.test", "(61) 4000-1007", "SQS 100, Bloco A, Brasília - DF"),
    ]
    for chave, nome, tipo, base, email, tel, end in orgs:
        ids[chave] = d.organizacao(nome, tipo, base, email, tel, end)
    d.parceria(ids["ed_a"], "Empresa Doadora")                     # UC09 exige parceria ativa (RN10)
    d.parceria(ids["ed_b"], "Patrocinador em Potencial")           # o outro tipo de parceria
    d.parceria(ids["ed_c"], "Empresa Doadora", situacao="Inativa")  # parceria Inativa
    d.chamar("PATCH", f"/organizacoes/{ids['ed_c']}/situacao", ADMIN, json={"situacao": "Inativa"})  # organização Inativa (RN06)

    # ---------- usuários (UC02, RN02) ----------
    d.usuario("Administradora Demo 2", ADMIN2, "Administrador", None)  # 2º admin: demonstra a proteção do último (DP-65)
    d.usuario("Funcionário Demo", FUNC, "Funcionário", None)
    d.usuario("Cliente Empresa Demo", EMPRESA, "Cliente Empresa", ids["ce_a"])
    d.usuario("Cliente ONG Demo", ONG, "Cliente ONG", ids["ong_a"])
    d.usuario("Empresa Doadora Demo", DOADORA, "Empresa Doadora", ids["ed_a"])

    # ---------- categorias (UC05, RF08): 6 base + 2 ativas + 1 inativa ----------
    cat = {n: d.categoria(n) for n in ("Computadores", "Notebooks", "Monitores", "Periféricos", "Placas de vídeo", "Placas-mãe")}
    cat["Impressoras"] = d.categoria("Impressoras")
    cat["Servidores"] = d.categoria("Servidores")
    d.categoria("Cabos e Acessórios (descontinuada)", ativa=False)

    existentes = d.equipamentos_existentes()

    # ---------- bloco A: solicitações de avaliação e equipamentos vindos delas (UC09, UC10, UC11; RN03, RN10) ----------
    if "DEMO-NB-001" not in existentes:
        # Aguardando avaliação (sem equipamentos)
        d.chamar("POST", "/solicitacoes", DOADORA, json={"itens": [
            {"tipo": "Notebook", "modelo": "Lenovo ThinkPad E14", "quantidade": 3},
            {"tipo": "Monitor", "modelo": "Dell P2422H", "quantidade": 2}]})
        # Em avaliação (1 de 2 unidades registrada, condição ainda 'A avaliar', sem destinação)
        s2 = d.chamar("POST", "/solicitacoes", DOADORA, json={"itens": [
            {"tipo": "Desktop", "modelo": "HP ProDesk 600 G4", "quantidade": 2}]}).json()
        d.chamar("POST", f"/solicitacoes/{s2['id_solicitacao']}/itens/{s2['itens'][0]['id_item_solicitacao']}/equipamentos",
                 FUNC, json={"identificacao": "DEMO-DT-001", "id_categoria": cat["Computadores"], "condicao": "A avaliar",
                             "data_recebimento": dia(8), "situacao": "Em avaliação"})
        # Avaliada (todas as unidades avaliadas e destinadas: Venda, Doação e Reciclagem)
        s3 = d.chamar("POST", "/solicitacoes", DOADORA, json={"itens": [
            {"tipo": "Notebook", "modelo": "Dell Latitude 5420", "quantidade": 2},
            {"tipo": "Placa de vídeo", "modelo": "GTX 960 2GB", "quantidade": 1}]}).json()
        sid = s3["id_solicitacao"]
        i_nb, i_gpu = (it["id_item_solicitacao"] for it in s3["itens"])

        def avaliar(item, ident, id_cat, cond, rec, valor, img=None):
            corpo = {"identificacao": ident, "id_categoria": id_cat, "condicao": cond,
                     "origem": f"Solicitação {sid}", "data_recebimento": rec}
            if valor is not None:
                corpo["valor"] = valor
            eid = d.chamar("POST", f"/solicitacoes/{sid}/itens/{item}/equipamentos", FUNC, json=corpo).json()["id_equipamento"]
            if img:
                d.imagem(eid, img)
            return eid

        e1 = avaliar(i_nb, "DEMO-NB-001", cat["Notebooks"], "Bom", dia(30), 1800.00, "demo-notebook-1.jpg")
        e2 = avaliar(i_nb, "DEMO-NB-002", cat["Notebooks"], "Bom", dia(30), 2200.00, "demo-notebook-2.jpg")
        e3 = avaliar(i_gpu, "DEMO-GPU-001", cat["Placas de vídeo"], "Sem condições de reuso", dia(30), None)
        ong_a = ids["ong_a"]
        d.chamar("PUT", f"/solicitacoes/{sid}/equipamentos/{e1}/destinacao", FUNC, json={"destinacao": "Venda"})
        d.chamar("PUT", f"/solicitacoes/{sid}/equipamentos/{e2}/destinacao", FUNC,  # doação direta (UC11)
                 json={"destinacao": "Doação", "id_organizacao_ong": ong_a, "data_doacao": dia(5)})
        d.chamar("PUT", f"/solicitacoes/{sid}/equipamentos/{e3}/destinacao", FUNC, json={"destinacao": "Reciclagem"})

    # ---------- bloco B: equipamentos cadastrados direto, solicitações de doação e vendas ----------
    if "DEMO-MB-001" not in existentes:
        e = {}

        def eq(chave, *a, **k):
            e[chave] = d.equipamento(*a, **k)

        eq("mb1", "DEMO-MB-001", cat["Placas-mãe"], "Placa-mãe ASUS Prime B450", "Necessita reparo", "Doação de pessoa jurídica", dia(20), situacao="Em manutenção", img="demo-placa-mae.jpg")
        eq("dt2", "DEMO-DT-002", cat["Computadores"], "Desktop Dell OptiPlex 3050", "Regular", "Troca de parque tecnológico", dia(25), 700.00, "Recondicionado", img="demo-desktop.jpg")
        eq("nb3", "DEMO-NB-003", cat["Notebooks"], "Notebook Acer Aspire 3", "A avaliar", "Entrega no balcão", dia(2))  # sem imagem
        eq("mb2", "DEMO-MB-002", cat["Placas-mãe"], "Placa-mãe Gigabyte H61", "Sem condições de reuso", "Descarte de laboratório", dia(40), situacao="Destinado à reciclagem")
        eq("mon1", "DEMO-MON-001", cat["Monitores"], "Monitor LG 22 polegadas", "Bom", "Empresa Doadora Recicla Corp", dia(15), 450.00, "Disponível", "demo-monitor-1.jpg")
        eq("mon2", "DEMO-MON-002", cat["Monitores"], "Monitor Samsung 24 polegadas", "Regular", "Empresa Doadora Recicla Corp", dia(15), 380.00, "Disponível", "demo-monitor-2.jpg")
        eq("tec", "DEMO-PER-001", cat["Periféricos"], "Kit teclado e mouse USB", "Bom", "Campanha de arrecadação", dia(12), 90.00, "Disponível", "demo-teclado.jpg")
        eq("nb4", "DEMO-NB-004", cat["Notebooks"], "Notebook HP ProBook 440", "Bom", "Empresa Doadora Recicla Corp", dia(18), 1500.00, "Disponível", "demo-notebook-1.jpg")
        eq("nb5", "DEMO-NB-005", cat["Notebooks"], "Notebook Positivo Motion", "Bom", "Campanha de arrecadação", dia(18), 1200.00, "Disponível", "demo-notebook-2.jpg")
        eq("mon3", "DEMO-MON-003", cat["Monitores"], "Monitor Dell 19 polegadas", "Regular", "Troca de parque tecnológico", dia(22), 300.00, "Disponível", "demo-monitor-1.jpg")
        eq("imp", "DEMO-IMP-001", cat["Impressoras"], "Impressora multifuncional jato de tinta", "Bom", "Entrega no balcão", dia(10), 250.00, "Disponível", "demo-impressora.jpg")
        eq("gpu2", "DEMO-GPU-002", cat["Placas de vídeo"], "Placa de vídeo GTX 1050 Ti", "Regular", "Empresa Doadora Recicla Corp", dia(14), 600.00, "Disponível", "demo-placa-video.jpg")

        # Solicitações de doação (UC30): Recusada, Cancelada, Aprovada (gera doação, UC11) e Pendente (reserva o item)
        def pedir_doacao(ids_eq):
            return d.chamar("POST", f"{'/doacoes/solicitacoes'}", ONG, json={"ids_equipamentos": ids_eq}).json()["id_solicitacao_doacao"]

        sd = pedir_doacao([e["mon3"]])
        d.chamar("PATCH", f"/doacoes/solicitacoes/{sd}/recusar", FUNC, json={"motivo": "Equipamento reservado para outra instituição."})
        sd = pedir_doacao([e["mon3"]])
        d.chamar("PATCH", f"/doacoes/solicitacoes/{sd}/cancelar", ONG)
        sd = pedir_doacao([e["nb5"]])
        d.chamar("PATCH", f"/doacoes/solicitacoes/{sd}/aprovar", FUNC)
        pedir_doacao([e["nb4"]])  # fica Pendente

        # Vendas e pedidos (UC13, UC14, UC16; RN13, RN14, RN19)
        def pedido(ids_eq, forma=None):
            corpo = {"ids_equipamento": ids_eq}
            if forma:
                corpo["forma_pagamento"] = forma
            return d.chamar("POST", "/vendas", EMPRESA, json=corpo).json()["id_venda"]

        def confirmar(vid, forma, nota):
            d.chamar("POST", f"/vendas/{vid}/confirmar", FUNC, json={"data_venda": HOJE.isoformat(), "forma_pagamento": forma})
            if nota:
                d.chamar("POST", f"/vendas/{vid}/nota-fiscal", ADMIN)

        confirmar(pedido([e["mon2"], e["gpu2"]], "Pix"), "Pix", True)
        confirmar(pedido([e["tec"]], "Cartão de crédito"), "Cartão de crédito", True)
        pedido([e["mon1"]])                                  # Pendente, forma 'A definir'
        pedido([e["imp"]], "Transferência bancária")         # Pendente com forma informada
        v = pedido([e["mon3"]], "Boleto")                    # Cancelada (libera o equipamento)
        d.chamar("POST", f"/vendas/{v}/cancelar", EMPRESA)

    # ---------- bloco C: vitrine do marketplace (equipamentos Disponíveis, sem pedido nem doação) ----------
    if "DEMO-VIT-001" not in existentes:
        cat["Redes"] = d.categoria("Redes")
        cat["Armazenamento"] = d.categoria("Armazenamento")
        vitrine = [  # ident, categoria, modelo, condição, origem, dias, valor, imagem
            ("DEMO-VIT-001", "Notebooks", "Notebook Lenovo IdeaPad 3", "Bom", "Empresa Doadora Recicla Corp", 9, 1650.00, "demo-notebook-1.jpg"),
            ("DEMO-VIT-002", "Notebooks", "Notebook Dell Inspiron 15", "Regular", "Troca de parque tecnológico", 11, 1100.00, "demo-notebook-2.jpg"),
            ("DEMO-VIT-003", "Computadores", "Desktop Lenovo ThinkCentre M720", "Bom", "Troca de parque tecnológico", 13, 950.00, "demo-desktop.jpg"),
            ("DEMO-VIT-004", "Computadores", "Desktop HP EliteDesk 800 G3", "Bom", "Empresa Doadora Recicla Corp", 16, 1050.00, "demo-desktop.jpg"),
            ("DEMO-VIT-005", "Monitores", "Monitor AOC 21,5 polegadas", "Bom", "Campanha de arrecadação", 7, 420.00, "demo-monitor-2.jpg"),
            ("DEMO-VIT-006", "Monitores", "Monitor Philips 23 polegadas", "Regular", "Entrega no balcão", 6, 350.00, "demo-monitor-1.jpg"),
            ("DEMO-VIT-007", "Periféricos", "Teclado mecânico Redragon", "Bom", "Campanha de arrecadação", 5, 140.00, "demo-teclado.jpg"),
            ("DEMO-VIT-008", "Periféricos", "Mouse óptico Logitech M90", "Bom", "Entrega no balcão", 4, 35.00, "demo-teclado.jpg"),
            ("DEMO-VIT-009", "Placas de vídeo", "Placa de vídeo RX 570 4GB", "Regular", "Empresa Doadora Recicla Corp", 19, 700.00, "demo-placa-video.jpg"),
            ("DEMO-VIT-010", "Placas-mãe", "Placa-mãe MSI B360M", "Regular", "Descarte de laboratório", 21, 320.00, "demo-placa-mae.jpg"),
            ("DEMO-VIT-011", "Impressoras", "Impressora laser Brother HL-1202", "Bom", "Entrega no balcão", 8, 380.00, "demo-impressora.jpg"),
            ("DEMO-VIT-012", "Servidores", "Servidor Dell PowerEdge T110", "Regular", "Troca de parque tecnológico", 30, 1900.00, "demo-desktop.jpg"),
            ("DEMO-VIT-013", "Redes", "Roteador TP-Link Archer C6", "Bom", "Campanha de arrecadação", 3, 150.00, "demo-roteador.jpg"),
            ("DEMO-VIT-014", "Armazenamento", "SSD Kingston 240GB", "Bom", "Entrega no balcão", 2, 120.00, "demo-ssd.jpg"),
        ]
        for ident, nome_cat, modelo, cond, origem, dias, valor, img in vitrine:
            d.equipamento(ident, cat[nome_cat], modelo, cond, origem, dia(dias), valor, "Disponível", img)
    else:
        # Banco já populado: anexa a foto aos itens da vitrine que ainda estão sem imagem (não altera outros dados).
        fotos = {"DEMO-VIT-013": "demo-roteador.jpg", "DEMO-VIT-014": "demo-ssd.jpg"}
        for e in d.chamar("GET", "/equipamentos?q=DEMO-VIT&size=100", ADMIN).json()["items"]:
            if e["identificacao"] in fotos and not e.get("imagem"):
                d.imagem(e["id_equipamento"], fotos[e["identificacao"]])


def principal() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # console do Windows
    p = argparse.ArgumentParser(description="Carrega dados fictícios de demonstração do LEAF TI.")
    p.add_argument("--reiniciar", action="store_true", help="apaga o banco de LEAF_DB_PATH (após digitar SIM) e recarrega")
    a = p.parse_args()

    if os.environ.get("LEAF_AMBIENTE", "").strip().lower() == "producao":
        print("Recusado: LEAF_AMBIENTE=producao. Os dados de demonstração só podem ser usados localmente.")
        return 1
    senha = os.environ.get("LEAF_DEMO_SENHA") or SENHA_DEMO_PADRAO
    if not 8 <= len(senha) <= 128:
        print("Erro: LEAF_DEMO_SENHA deve ter de 8 a 128 caracteres.")
        return 1

    if a.reiniciar:
        caminho = os.environ.get("LEAF_DB_PATH", "").strip()
        if not caminho:
            print("Erro: --reiniciar exige LEAF_DB_PATH definido (nunca apaga o banco padrão sem você indicar).")
            return 1
        arq = Path(caminho)
        if arq.exists():
            if input(f"Isto APAGA o arquivo {arq.resolve()}. Digite SIM para confirmar: ").strip() != "SIM":
                print("Cancelado. Nada foi apagado.")
                return 1
            arq.unlink()
            for sufixo in ("-wal", "-shm", "-journal"):
                Path(str(arq) + sufixo).unlink(missing_ok=True)
            print("Banco apagado.")

    print("Banco:", obter_configuracao().caminho_banco)
    db.inicializar_banco()
    conexao = db.conectar()
    try:
        antes = contar(conexao)
        # Primeiro Administrador (mesmo serviço do scripts.criar_admin); se já existir, é pulado.
        try:
            usuarios_service.criar_administrador_inicial(conexao, "Administrador Demo", ADMIN, senha)
        except ValueError:
            pass
        try:
            with TestClient(app) as c:
                d = Demo(c, senha)
                carregar(d)
        except Falha as erro:
            print("ERRO:", erro)
            return 1
        depois = contar(conexao)
    finally:
        conexao.close()

    print("\nResumo (criado nesta execução / total):")
    for t in TABELAS:
        print(f"  {t:<26}{depois[t] - antes[t]:>4} / {depois[t]}")
    print("\nLogins de demonstração (senha: %s)" % senha)
    print(f"  {'E-mail':<28}{'Perfil':<18}Organização")
    for email, perfil, org in [(ADMIN, "Administrador", "-"), (ADMIN2, "Administrador", "-"), (FUNC, "Funcionário", "-"),
                               (EMPRESA, "Cliente Empresa", "Horizonte Tecnologia Ltda"),
                               (ONG, "Cliente ONG", "ONG Conecta Futuro"),
                               (DOADORA, "Empresa Doadora", "Recicla Corp Doadora S.A.")]:
        print(f"  {email:<28}{perfil:<18}{org}")
    print("\nDados fictícios, só para demonstração local. Não use em produção.")
    return 0


if __name__ == "__main__":
    sys.exit(principal())
