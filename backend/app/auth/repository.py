"""SQL do módulo de acesso (consultas parametrizadas)."""
import sqlite3

_SELECT_USUARIO = """
    SELECT u.id_usuario, u.id_organizacao, u.email, u.perfil, u.senha_hash, u.nome,
           o.situacao AS situacao_organizacao
      FROM USUARIO u
      LEFT JOIN ORGANIZACAO o ON o.id_organizacao = u.id_organizacao
"""


def buscar_por_email(conexao: sqlite3.Connection, email: str):
    """UC28 passo 1: consulta a conta pelo e-mail (já normalizado)."""
    return conexao.execute(_SELECT_USUARIO + " WHERE lower(u.email) = ?", (email,)).fetchone()


def buscar_por_id(conexao: sqlite3.Connection, id_usuario: int):
    return conexao.execute(_SELECT_USUARIO + " WHERE u.id_usuario = ?", (id_usuario,)).fetchone()
