"""RNF04: ids fora da faixa do SQLite (> 2^63-1) devolvem 404/400, nunca 500 (modulos 1, 2 e 3)."""
import pytest

from tests.conftest import fazer_login  # noqa: F401

GRANDE = 10**20
B = "/api/v1"


@pytest.fixture()
def adm(cliente, token_de):
    return {"Authorization": f"Bearer {token_de(cliente, 'admin')}"}


@pytest.mark.parametrize("metodo,rota,corpo", [
    ("get", f"{B}/organizacoes/{GRANDE}", None),
    ("put", f"{B}/organizacoes/{GRANDE}", None),
    ("get", f"{B}/parceiros/{GRANDE}", None),
    ("put", f"{B}/parceiros/{GRANDE}", {"tipo_parceria": "Empresa Doadora"}),
    ("patch", f"{B}/parceiros/{GRANDE}/situacao", {"situacao_parceria": "Inativa"}),
    ("patch", f"{B}/organizacoes/{GRANDE}/situacao", {"situacao": "Inativa"}),
    ("get", f"{B}/usuarios/{GRANDE}", None),
    ("delete", f"{B}/usuarios/{GRANDE}", None),
])
def test_id_de_rota_enorme_da_404(cliente, adm, metodo, rota, corpo):
    r = getattr(cliente, metodo)(rota, headers=adm, **({"json": corpo} if corpo is not None else {}))
    assert r.status_code in (404, 400), (rota, r.status_code, r.text)


def test_filtro_usuarios_por_organizacao_enorme(cliente, adm):
    assert cliente.get(f"{B}/usuarios?id_organizacao={GRANDE}", headers=adm).status_code == 400


def test_criar_usuario_com_organizacao_enorme(cliente, adm):
    r = cliente.post(f"{B}/usuarios", headers=adm, json={
        "nome": "Teste Grande", "email": "grande@teste.com", "senha": "Senha@12345",
        "perfil": "Cliente Empresa", "id_organizacao": GRANDE})
    assert r.status_code in (400, 422), r.text


def test_criar_parceria_com_organizacao_enorme(cliente, adm):
    r = cliente.post(f"{B}/parceiros", headers=adm, json={"id_organizacao": GRANDE, "tipo_parceria": "Empresa Doadora"})
    assert r.status_code in (400, 422), r.text
