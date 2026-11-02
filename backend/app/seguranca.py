"""Hash de senha (bcrypt, RNF03) e token JWT HS256 (DP-04). Nunca registra senha nem hash em log."""
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import obter_configuracao


def _bytes_senha(senha: str) -> bytes:
    # bcrypt considera só os 72 primeiros bytes; truncamos de forma explícita e consistente.
    return senha.encode("utf-8")[:72]


def gerar_hash_senha(senha: str) -> str:
    return bcrypt.hashpw(_bytes_senha(senha), bcrypt.gensalt()).decode("ascii")


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        return bcrypt.checkpw(_bytes_senha(senha), senha_hash.encode("ascii"))
    except ValueError:
        return False


# Hash descartável (mesmo custo dos hashes reais) para igualar o tempo quando o e-mail não existe.
HASH_FALSO = gerar_hash_senha("senha-descartavel-para-igualar-tempo")


def criar_token(id_usuario: int, perfil: str, id_organizacao: int | None) -> tuple[str, int]:
    """Gera o JWT. Claims: sub, perfil, id_organizacao, iat, exp. Devolve (token, segundos de validade)."""
    cfg = obter_configuracao()
    agora = datetime.now(timezone.utc)
    claims = {
        "sub": str(id_usuario),
        "perfil": perfil,
        "id_organizacao": id_organizacao,
        "iat": agora,
        "exp": agora + timedelta(minutes=cfg.token_minutos),
    }
    return jwt.encode(claims, cfg.jwt_segredo, algorithm=cfg.jwt_algoritmo), cfg.token_minutos * 60


def decodificar_token(token: str) -> dict | None:
    """Devolve os claims ou None se o token for inválido/expirado."""
    cfg = obter_configuracao()
    try:
        claims = jwt.decode(token, cfg.jwt_segredo, algorithms=[cfg.jwt_algoritmo], options={"require": ["exp", "sub"]})
        int(claims["sub"])
        return claims
    except (jwt.PyJWTError, ValueError, TypeError):
        return None
