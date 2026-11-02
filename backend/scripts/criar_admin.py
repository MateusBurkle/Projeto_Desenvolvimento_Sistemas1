"""Carga inicial do primeiro Administrador (DP-04, RF02/RN02).

Uso (dentro de backend/, com o ambiente virtual ativo):
    python -m scripts.criar_admin --email EMAIL --nome "Nome" [--senha SENHA]
ou variáveis de ambiente LEAF_ADMIN_EMAIL, LEAF_ADMIN_NOME, LEAF_ADMIN_SENHA.
Sem --senha/variável, a senha é pedida no terminal (sem eco). Nada é fixo no código.
"""
import argparse
import getpass
import os
import re
import sys

from app import db
from app.usuarios import service


def main() -> int:
    p = argparse.ArgumentParser(description="Cria o Administrador inicial.")
    p.add_argument("--email", default=os.environ.get("LEAF_ADMIN_EMAIL"))
    p.add_argument("--nome", default=os.environ.get("LEAF_ADMIN_NOME"))
    p.add_argument("--senha", default=os.environ.get("LEAF_ADMIN_SENHA"))
    a = p.parse_args()

    if not a.email or not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", a.email.strip()):
        print("Erro: informe um e-mail válido (--email ou LEAF_ADMIN_EMAIL).")
        return 1
    if not a.nome or not a.nome.strip():
        print("Erro: informe o nome (--nome ou LEAF_ADMIN_NOME).")
        return 1
    senha = a.senha or getpass.getpass("Senha do Administrador: ")
    if len(senha) < 8 or len(senha) > 128:
        print("Erro: a senha deve ter de 8 a 128 caracteres.")
        return 1

    db.inicializar_banco()
    conexao = db.conectar()
    try:
        id_usuario = service.criar_administrador_inicial(conexao, a.nome, a.email, senha)
    except ValueError as erro:
        print(f"Erro: {erro}")
        return 1
    finally:
        conexao.close()
    print(f"Administrador criado (id_usuario={id_usuario}, e-mail={service.normalizar_email(a.email)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
