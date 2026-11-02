"""Cria um login de teste para cada perfil (com organizações e parceria) no banco configurado.
Uso (dentro de backend/): .venv\\Scripts\\python -m scripts.popular_usuarios_teste
Pode rodar mais de uma vez: o que já existe é pulado. UC01, UC02, UC03, UC06; RN10.
"""
import getpass
import os
import sys

from fastapi.testclient import TestClient

from app.main import app

ADMIN_EMAIL = os.environ.get("LEAF_ADMIN_EMAIL", "teste.admin@exemplo.test")  # admin de teste já criado
ADMIN_SENHA = os.environ.get("LEAF_ADMIN_SENHA") or ""
SENHA = ""  # definida em main(): senha dos usuários de teste (nunca gravada no repositório)


def cnpj(base: int) -> str:
    n = [int(c) for c in f"{base:012d}"]
    for k in (12, 13):
        w = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2] if k == 12 else [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        d = sum(a * b for a, b in zip(n, w)) % 11
        n.append(0 if d < 2 else 11 - d)
    x = "".join(map(str, n))
    return f"{x[:2]}.{x[2:5]}.{x[5:8]}/{x[8:12]}-{x[12:]}"


ORGS = [  # chave, nome, tipo, índice
    ("doadora", "Doadora Teste SA", "Empresa Doadora", 91),
    ("ong", "ONG Teste Esperança", "Cliente ONG", 92),
    ("empresa", "Compradora Teste Ltda", "Cliente Empresa", 93),
]
USUARIOS = [  # nome, e-mail, perfil, chave da organização
    ("Funcionário Teste", "teste.funcionario@exemplo.test", "Funcionário", None),
    ("Doadora Teste", "teste.doadora@exemplo.test", "Empresa Doadora", "doadora"),
    ("ONG Teste", "teste.ong@exemplo.test", "Cliente ONG", "ong"),
    ("Empresa Compradora Teste", "teste.empresa@exemplo.test", "Cliente Empresa", "empresa"),
]


def main() -> int:
    global ADMIN_SENHA, SENHA
    ADMIN_SENHA = ADMIN_SENHA or getpass.getpass("Senha do admin de teste: ")
    SENHA = os.environ.get("LEAF_SENHA_TESTE") or getpass.getpass("Senha para os usuários de teste (8 a 128): ")
    with TestClient(app) as c:
        r = c.post("/api/v1/auth/login", json={"email": ADMIN_EMAIL, "senha": ADMIN_SENHA})
        if r.status_code != 200:
            print("Erro: login do admin de teste falhou. Crie-o com scripts.criar_admin.")
            return 1
        h = {"Authorization": "Bearer " + r.json()["access_token"]}
        ids = {}
        for chave, nome, tipo, i in ORGS:
            r = c.post("/api/v1/organizacoes", headers=h, json={
                "nome_razao_social": nome, "tipo": tipo, "cnpj": cnpj(20000000 + i),
                "telefone": "(11) 91234-5678", "email": f"org{i}@exemplo.test",
                "endereco": "Rua Teste, 100, São Paulo"})
            if r.status_code == 201:
                ids[chave] = r.json()["id_organizacao"]
                print("Organização criada:", nome)
            else:  # já existe: procura pelo nome
                lista = c.get("/api/v1/organizacoes?size=100", headers=h).json().get("items", [])
                ids[chave] = next((o["id_organizacao"] for o in lista if o["nome_razao_social"] == nome), None)
                print("Organização já existia:", nome, "->", ids[chave])
        if ids.get("doadora"):
            r = c.post("/api/v1/parceiros", headers=h,
                       json={"id_organizacao": ids["doadora"], "tipo_parceria": "Empresa Doadora"})
            print("Parceria da doadora:", "criada" if r.status_code == 201 else "já existia ou não criada")
        for nome, email, perfil, chave in USUARIOS:
            r = c.post("/api/v1/usuarios", headers=h, json={
                "nome": nome, "email": email, "senha": SENHA, "perfil": perfil,
                "id_organizacao": ids.get(chave) if chave else None})
            print(("Usuário criado: " if r.status_code == 201 else f"Usuário pulado ({r.status_code}): ") + email)
    print("\nSenha de todos:", SENHA)
    return 0


if __name__ == "__main__":
    sys.exit(main())
