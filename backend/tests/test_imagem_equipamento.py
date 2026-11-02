"""Testes da imagem do equipamento: UC07, UC12; DP-84 a DP-87, DP-90; RN01 (perfis), DP-74 (sem vazar origem).
Pasta de imagens temporaria (conftest define LEAF_IMAGENS_DIR); nunca a pasta real."""
import os
import sqlite3
import struct
import zlib
from datetime import date

import pytest

B = "/api/v1"
E = f"{B}/equipamentos"
def _chunk(tipo, corpo):
    return struct.pack(">I", len(corpo)) + tipo + corpo + struct.pack(">I", zlib.crc32(tipo + corpo) & 0xFFFFFFFF)


def _png(largura=1, altura=1, extra=0):
    """PNG valido gerado no teste; 'extra' acrescenta bytes num chunk tEXt (para o teste de 2 MB)."""
    ihdr = struct.pack(">IIBBBBB", largura, altura, 8, 0, 0, 0, 0)
    idat = zlib.compress((b"\x00" + b"\x00" * largura) * altura)
    texto = _chunk(b"tEXt", b"k\x00" + b"x" * (extra - 12 - 2)) if extra else b""
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", ihdr) + texto + _chunk(b"IDAT", idat) + _chunk(b"IEND", b"")


def _jpg(largura=1, altura=1):
    sof = b"\xff\xc0" + struct.pack(">HBHHB", 11, 8, altura, largura, 1) + b"\x01\x11\x00"
    sos = b"\xff\xda" + struct.pack(">HB", 8, 1) + b"\x01\x00\x00\x3f\x00"
    return b"\xff\xd8" + b"\xff\xe0\x00\x04\x00\x00" + sof + sos + b"\x00\x01\x02" + b"\xff\xd9"


def _webp(largura=1, altura=1):
    bits = (largura - 1) | ((altura - 1) << 14)
    corpo = b"\x2f" + struct.pack("<I", bits) + b"\x00\x00"  # VP8L, tamanho par (sem preenchimento)
    resto = b"WEBP" + b"VP8L" + struct.pack("<I", len(corpo)) + corpo
    return b"RIFF" + struct.pack("<I", len(resto)) + resto


def _webp_x(largura, altura):
    corpo = b"\x00" * 4 + (largura - 1).to_bytes(3, "little") + (altura - 1).to_bytes(3, "little")
    resto = b"WEBP" + b"VP8X" + struct.pack("<I", len(corpo)) + corpo
    return b"RIFF" + struct.pack("<I", len(resto)) + resto


PNG, JPG, WEBP = _png(), _jpg(), _webp()


def _h(token):
    return {"Authorization": f"Bearer {token}"}


def _novo(c, situacao="Disponível"):
    con = sqlite3.connect(c.caminho_banco)
    cur = con.execute(
        "INSERT INTO EQUIPAMENTO (id_categoria, identificacao, modelo, condicao, origem, situacao, ativo, valor,"
        " data_recebimento) VALUES (2, ?, 'Dell Latitude', 'Bom', 'Origem Secreta', ?, 1, 1500, ?)",
        (f"IMG-{os.urandom(3).hex()}", situacao, date.today().isoformat()))
    con.commit()
    i = cur.lastrowid
    con.close()
    return i


def _pasta(c):
    return os.environ["LEAF_IMAGENS_DIR"]


def _enviar(c, h, i, conteudo, nome="foto.png", tipo="image/png"):
    return c.put(f"{E}/{i}/imagem", headers=h, files={"arquivo": (nome, conteudo, tipo)})


@pytest.fixture()
def adm(cliente, token_de):
    return _h(token_de(cliente, "admin"))


def test_perfis_e_404(cliente, token_de, adm):
    i = _novo(cliente)
    r = cliente.put(f"{E}/{i}/imagem", files={"arquivo": ("a.png", PNG, "image/png")})
    assert r.status_code == 401
    for chave in ("empresa", "ong", "doadora"):
        h = _h(token_de(cliente, chave))
        assert _enviar(cliente, h, i, PNG).status_code == 403
        assert cliente.delete(f"{E}/{i}/imagem", headers=h).status_code == 403
    assert _enviar(cliente, adm, 99999, PNG).status_code == 404
    assert cliente.delete(f"{E}/99999/imagem", headers=adm).status_code == 404
    assert cliente.put(f"{E}/{i}/imagem", headers=adm).status_code == 400  # sem o campo


@pytest.mark.parametrize("conteudo,ext,mime", [(PNG, "png", "image/png"), (JPG, "jpg", "image/jpeg"),
                                               (WEBP, "webp", "image/webp")])
def test_tipos_validos_e_get_publico(cliente, token_de, adm, conteudo, ext, mime):
    i = _novo(cliente)
    h = _h(token_de(cliente, "func"))
    r = _enviar(cliente, h, i, conteudo, nome="minha foto.txt", tipo="text/plain")  # extensão/tipo do cliente ignorados
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["imagem"].endswith("." + ext) and len(d["imagem"]) == 32 + 1 + len(ext)
    assert "minha" not in d["imagem"]
    assert d["imagem_url"] == f"/imagens/equipamentos/{d['imagem']}"
    g = cliente.get(f"{B}{d['imagem_url']}")  # público
    assert g.status_code == 200 and g.content == conteudo
    assert g.headers["content-type"].startswith(mime)
    assert g.headers["x-content-type-options"] == "nosniff"
    assert cliente.get(f"{E}/{i}", headers=adm).json()["imagem_url"] == d["imagem_url"]


@pytest.mark.parametrize("conteudo", [b"<html><script>alert(1)</script></html>", b"texto simples", b"MZ\x90\x00" + b"\x00" * 40,
                                      b"", b"RIFF\x00\x00\x00\x00WAVE"])
def test_extensao_enganosa_422(cliente, adm, conteudo):
    i = _novo(cliente)
    r = _enviar(cliente, adm, i, conteudo, nome="x.png", tipo="image/png")
    assert r.status_code == 422 and r.json()["codigo"] == "IMAGEM_TIPO_INVALIDO"
    assert r.json()["mensagem"] == "Envie uma imagem JPG, PNG ou WebP."
    assert cliente.get(f"{E}/{i}", headers=adm).json()["imagem"] is None


def test_limite_2mb(cliente, adm):
    i = _novo(cliente)
    limite = 2 * 1024 * 1024
    ok = _png(extra=limite - len(PNG))
    assert len(ok) == limite and _enviar(cliente, adm, i, ok).status_code == 200
    r = _enviar(cliente, adm, i, ok + b"\x00")  # 2 MB + 1
    assert r.status_code == 422 and r.json()["codigo"] == "IMAGEM_MUITO_GRANDE"
    assert r.json()["mensagem"] == "A imagem deve ter no máximo 2 MB."


def test_substituir_e_remover_apagam_arquivo(cliente, adm):
    i = _novo(cliente)
    a = _enviar(cliente, adm, i, PNG).json()["imagem"]
    assert os.path.isfile(os.path.join(_pasta(cliente), a))
    b = _enviar(cliente, adm, i, JPG).json()["imagem"]
    assert a != b
    assert not os.path.exists(os.path.join(_pasta(cliente), a))
    assert os.path.isfile(os.path.join(_pasta(cliente), b))
    assert not [f for f in os.listdir(_pasta(cliente)) if f.endswith(".tmp")]
    assert cliente.delete(f"{E}/{i}/imagem", headers=adm).status_code == 204
    assert not os.path.exists(os.path.join(_pasta(cliente), b))
    assert cliente.get(f"{E}/{i}", headers=adm).json()["imagem"] is None
    assert cliente.delete(f"{E}/{i}/imagem", headers=adm).status_code == 204  # idempotente
    assert cliente.get(f"{B}/imagens/equipamentos/{b}").status_code == 404


def test_vendido_doado_bloqueados(cliente, adm):
    for sit in ("Vendido", "Doado"):
        i = _novo(cliente, situacao=sit)
        r = _enviar(cliente, adm, i, PNG)
        assert r.status_code == 422 and r.json()["codigo"] == "EQUIPAMENTO_FINALIZADO"
        assert cliente.delete(f"{E}/{i}/imagem", headers=adm).status_code == 422


@pytest.mark.parametrize("nome", ["..", "%2e%2e%2fleaf_ti.db", "..%2f..%2fleaf_ti.db", "..%5cx.png", "x.png",
                                  "A" * 32 + ".png", "0" * 32 + ".gif", "0" * 32 + ".png",
                                  "0" * 32 + ".png%0a"])
def test_path_traversal_get_404(cliente, nome):
    assert cliente.get(f"{B}/imagens/equipamentos/{nome}").status_code == 404
    assert cliente.get(f"{B}/imagens/equipamentos/").status_code == 404  # sem listar diretório


def test_lista_sem_imagem_null_e_marketplace_sem_vazar(cliente, adm):
    i = _novo(cliente)
    assert cliente.get(f"{E}/{i}", headers=adm).json()["imagem_url"] is None
    p = cliente.get(f"{B}/marketplace/produtos/{i}")
    assert p.status_code == 200 and p.json()["imagem_url"] is None
    url = _enviar(cliente, adm, i, WEBP).json()["imagem_url"]
    lista = cliente.get(f"{E}?size=100", headers=adm).json()["items"]
    assert [x for x in lista if x["id_equipamento"] == i][0]["imagem_url"] == url
    p = cliente.get(f"{B}/marketplace/produtos/{i}").json()
    assert p["imagem_url"] == url
    assert set(p) <= {"id_equipamento", "modelo", "categoria", "id_categoria", "condicao", "valor", "imagem_url"}
    assert "Origem Secreta" not in cliente.get(f"{B}/marketplace/produtos").text
    assert "imagem" not in {k for k in p if k == "imagem"}


def _invalidas():
    png = _png()
    corrompido = bytearray(png)
    corrompido[20] ^= 0xFF  # dentro do IHDR: CRC deixa de bater
    webp = bytearray(WEBP)
    webp[4] += 2  # tamanho do RIFF errado
    return {
        "png_truncado": png[:len(png) // 2],
        "png_so_cabecalho": png[:8],
        "png_lixo_apos_iend": png + b"lixo",
        "png_lixo_apos_assinatura": b"\x89PNG\r\n\x1a\n" + b"\x00" * 32,
        "png_crc_corrompido": bytes(corrompido),
        "png_dimensao_absurda": _png(largura=20001),
        "png_sem_idat": png.replace(b"IDAT", b"IDAX"),
        "jpg_3_bytes": b"\xff\xd8\xff",
        "jpg_sem_eoi": JPG[:-2],
        "jpg_sem_sos": JPG.replace(b"\xff\xda", b"\xff\xfe"),
        "jpg_dimensao_zero": _jpg(largura=0),
        "jpg_dimensao_absurda": _jpg(altura=20001),
        "webp_12_bytes": b"RIFF\x04\x00\x00\x00WEBP",
        "webp_riff_tamanho_errado": bytes(webp),
        "webp_chunk_alem_do_arquivo": WEBP[:-3],
        "webp_chunk_desconhecido": WEBP.replace(b"VP8L", b"ABCD"),
        "webp_dimensao_absurda": _webp_x(20001, 1),
    }


@pytest.mark.parametrize("nome", list(_invalidas()))
def test_estrutura_invalida_422_e_nada_gravado(cliente, adm, nome):
    i = _novo(cliente)
    antes = sorted(os.listdir(_pasta(cliente))) if os.path.isdir(_pasta(cliente)) else []
    r = _enviar(cliente, adm, i, _invalidas()[nome])
    assert r.status_code == 422 and r.json()["codigo"] == "IMAGEM_TIPO_INVALIDO"
    assert r.json()["mensagem"] == "Envie uma imagem JPG, PNG ou WebP."
    assert cliente.get(f"{E}/{i}", headers=adm).json()["imagem"] is None
    depois = sorted(os.listdir(_pasta(cliente))) if os.path.isdir(_pasta(cliente)) else []
    assert antes == depois


def test_imagens_validas_maiores_aceitas(cliente, adm):
    i = _novo(cliente)
    for img in (_png(200, 3), _jpg(20000, 20000), _webp(16384, 1), _webp_x(20000, 20000)):
        assert _enviar(cliente, adm, i, img).status_code == 200
