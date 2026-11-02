# Pedido 3 / DP-89: classe única da logo do cabeçalho nas 5 páginas públicas.
from pathlib import Path
import pytest

FRONT = Path(__file__).resolve().parents[2] / "frontend"
PAGINAS = ["index.html", "hardware.html", "compra.html", "quemsomos.html", "login.html"]


@pytest.mark.parametrize("pagina", PAGINAS)
def test_logo_usa_classe_unica(pagina):
    html = (FRONT / pagina).read_text(encoding="utf-8")
    assert 'src="images/logosemfundo.png" alt="Logo da LEAF TI" class="logo-cabecalho"' in html
    assert "identidade.css" in html


def test_classe_definida_uma_vez():
    css = (FRONT / "css" / "identidade.css").read_text(encoding="utf-8")
    assert css.count(".logo-cabecalho {") == 2  # base + mobile
