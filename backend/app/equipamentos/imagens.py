"""Armazenamento da imagem do equipamento (UC07, DP-84 a DP-87, DP-90). Arquivo em pasta fora do código,
nome gerado pelo sistema, tipo validado pelo CONTEÚDO (assinatura). Nunca usa nome nem caminho do cliente."""
import os
import re
import struct
import uuid
import zlib
from pathlib import Path

from fastapi.responses import FileResponse

from app.config import obter_configuracao
from app.erros import ErroApi

TAMANHO_MAX = 2 * 1024 * 1024  # 2 MB (DP-84)
PADRAO_NOME = re.compile(r"[0-9a-f]{32}\.(jpg|png|webp)")  # usado com fullmatch (sem aceitar "\n" final)
_MIME = {"jpg": "image/jpeg", "png": "image/png", "webp": "image/webp"}


def pasta() -> Path:
    return Path(obter_configuracao().imagens_dir).resolve()


def garantir_pasta() -> None:
    """DP-86: cria a pasta na inicialização."""
    pasta().mkdir(parents=True, exist_ok=True)


LADO_MAX = 20000  # px; evita bombas de descompressão no navegador (DP-84)


def _dim_ok(largura: int, altura: int) -> bool:
    return 0 < largura <= LADO_MAX and 0 < altura <= LADO_MAX


def _png_valido(d: bytes) -> bool:
    """Assinatura + IHDR (13 bytes) + chunks com CRC32 correto até IEND, sem bytes após IEND, ao menos um IDAT."""
    pos, n, idat, primeiro = 8, len(d), False, True
    while pos + 12 <= n:
        tam = struct.unpack(">I", d[pos:pos + 4])[0]
        tipo = d[pos + 4:pos + 8]
        fim = pos + 8 + tam
        if fim + 4 > n:
            return False
        if zlib.crc32(d[pos + 4:fim]) & 0xFFFFFFFF != struct.unpack(">I", d[fim:fim + 4])[0]:
            return False
        if primeiro:
            if tipo != b"IHDR" or tam != 13:
                return False
            if not _dim_ok(*struct.unpack(">II", d[pos + 8:pos + 16])):
                return False
            primeiro = False
        elif tipo == b"IHDR":
            return False
        elif tipo == b"IDAT":
            idat = True
        elif tipo == b"IEND":
            return tam == 0 and idat and fim + 4 == n
        pos = fim + 4
    return False


def _jpeg_valido(d: bytes) -> bool:
    """FFD8FF ... marcador SOF (C0-C2) com dimensões > 0, SOS (DA) e termina em FFD9."""
    n = len(d)
    if n < 4 or d[:3] != b"\xff\xd8\xff" or d[-2:] != b"\xff\xd9":
        return False
    pos, sof = 2, False
    while pos + 1 < n:
        if d[pos] != 0xFF:
            return False
        m = d[pos + 1]
        if m == 0xFF:  # preenchimento
            pos += 1
            continue
        if m == 0x01 or 0xD0 <= m <= 0xD8:  # marcadores sem tamanho
            pos += 2
            continue
        if m == 0xD9 or pos + 4 > n:
            return False
        tam = struct.unpack(">H", d[pos + 2:pos + 4])[0]
        if tam < 2 or pos + 2 + tam > n:
            return False
        if m in (0xC0, 0xC1, 0xC2):
            if tam < 8 or sof:
                return False
            altura, largura = struct.unpack(">HH", d[pos + 5:pos + 9])
            if not _dim_ok(largura, altura):
                return False
            sof = True
        elif m == 0xDA:
            return sof
        pos += 2 + tam
    return False


def _webp_valido(d: bytes) -> bool:
    """RIFF com tamanho == len-8, 'WEBP' e primeiro chunk VP8/VP8L/VP8X coerente e dentro do arquivo."""
    n = len(d)
    if n < 20 or d[:4] != b"RIFF" or d[8:12] != b"WEBP" or struct.unpack("<I", d[4:8])[0] != n - 8:
        return False
    tipo, tam = d[12:16], struct.unpack("<I", d[16:20])[0]
    if 20 + tam > n:
        return False
    c = d[20:20 + tam]
    if tipo == b"VP8X":
        if tam < 10:
            return False
        largura = int.from_bytes(c[4:7], "little") + 1
        altura = int.from_bytes(c[7:10], "little") + 1
    elif tipo == b"VP8L":
        if tam < 5 or c[0] != 0x2F:
            return False
        bits = int.from_bytes(c[1:5], "little")
        largura, altura = (bits & 0x3FFF) + 1, ((bits >> 14) & 0x3FFF) + 1
    elif tipo == b"VP8 ":
        if tam < 10 or c[3:6] != b"\x9d\x01\x2a":
            return False
        largura = struct.unpack("<H", c[6:8])[0] & 0x3FFF
        altura = struct.unpack("<H", c[8:10])[0] & 0x3FFF
    else:
        return False
    return _dim_ok(largura, altura)


def detectar_tipo(dados: bytes) -> str | None:
    """Detecta o tipo pela assinatura e valida a ESTRUTURA inteira do arquivo (DP-84), sem dependências externas."""
    if dados[:3] == b"\xff\xd8\xff":
        return "jpg" if _jpeg_valido(dados) else None
    if dados[:8] == b"\x89PNG\r\n\x1a\n":
        return "png" if _png_valido(dados) else None
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return "webp" if _webp_valido(dados) else None
    return None


def url_publica(nome: str | None) -> str | None:
    return None if not nome else f"/imagens/equipamentos/{nome}"


def salvar(dados: bytes) -> str:
    """Valida (tamanho, tipo) e grava de forma atômica (temporário + rename). Devolve o nome gerado."""
    if len(dados) > TAMANHO_MAX:
        raise ErroApi(422, "IMAGEM_MUITO_GRANDE", "A imagem deve ter no máximo 2 MB.", {"arquivo": "acima de 2 MB"})
    ext = detectar_tipo(dados)
    if ext is None:
        raise ErroApi(422, "IMAGEM_TIPO_INVALIDO", "Envie uma imagem JPG, PNG ou WebP.", {"arquivo": "tipo inválido"})
    garantir_pasta()
    nome = f"{uuid.uuid4().hex}.{ext}"
    destino = pasta() / nome
    temporario = pasta() / f"{uuid.uuid4().hex}.tmp"
    try:
        with open(temporario, "wb") as f:
            f.write(dados)
        os.replace(temporario, destino)
    finally:
        if temporario.exists():
            temporario.unlink(missing_ok=True)
    return nome


def apagar(nome: str | None) -> None:
    """DP-86: apaga o arquivo (só se o nome casa com o padrão gerado pelo sistema)."""
    if nome and PADRAO_NOME.fullmatch(nome):
        try:
            (pasta() / nome).unlink(missing_ok=True)
        except OSError:
            pass


def resposta_arquivo(nome: str) -> FileResponse:
    """GET público: qualquer nome fora do padrão (.., /, \\) ou inexistente -> 404."""
    caminho = pasta() / nome if PADRAO_NOME.fullmatch(nome) else None
    if caminho is None or not caminho.is_file():
        raise ErroApi(404, "NAO_ENCONTRADO", "Imagem não encontrada.")
    return FileResponse(caminho, media_type=_MIME[nome.rsplit(".", 1)[1]],
                        headers={"X-Content-Type-Options": "nosniff"})
