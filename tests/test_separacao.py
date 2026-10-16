"""Garante a separação entre interface e coleta.

A interface (Streamlit) e a API **não** podem exigir Playwright. Estes testes
verificam isso de verdade, importando os módulos em processos separados.
"""

import ast
import subprocess
import sys
from pathlib import Path

import pytest

RAIZ = Path(__file__).resolve().parent.parent

PROIBIDOS = ("playwright", "app.coleta", "app.scrapers.coletor", "app.scrapers.base")


def _rodar(codigo: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=180,
    )


def _modulos_proibidos(codigo_import: str) -> list[str]:
    codigo = (
        f"{codigo_import}\n"
        "import sys\n"
        "print('\\n'.join(sorted(\n"
        "    m for m in sys.modules\n"
        "    if m.startswith('playwright') or m in ('app.coleta', 'app.scrapers.coletor', 'app.scrapers.base')\n"
        ")))"
    )
    saida = _rodar(codigo)
    assert saida.returncode == 0, saida.stderr
    return [linha for linha in saida.stdout.split() if linha]


@pytest.mark.parametrize(
    "importacao",
    [
        "import app.servicos",
        "import app.consultas",
        "import app.filtros",
        "import app.atributos",
        "import app.models",
        "import app.database",
        "import app.main",  # a API sobe sem Playwright
    ],
)
def test_interface_e_api_nao_carregam_playwright(importacao):
    assert _modulos_proibidos(importacao) == []


def test_coletor_realmente_carrega_playwright():
    """Contraprova: o módulo do coletor precisa mesmo do Playwright."""
    proibidos = _modulos_proibidos("import app.coleta")
    assert any(m.startswith("playwright") for m in proibidos)
    assert "app.scrapers.coletor" in proibidos


def test_dashboard_nao_importa_coletor_no_topo():
    arvore = ast.parse((RAIZ / "app" / "dashboard.py").read_text(encoding="utf-8"))
    importados: list[str] = []
    for no in arvore.body:
        if isinstance(no, ast.Import):
            importados += [alias.name for alias in no.names]
        elif isinstance(no, ast.ImportFrom) and no.module:
            importados.append(no.module)

    for modulo in importados:
        assert "playwright" not in modulo
        assert modulo != "app.coleta"
        assert modulo != "app.scrapers.coletor"
        assert modulo != "app.scrapers.base"


def test_servicos_usa_apenas_tipagem_para_item_produto():
    """O import de ItemProduto em servicos.py precisa estar sob TYPE_CHECKING."""
    fonte = (RAIZ / "app" / "servicos.py").read_text(encoding="utf-8")
    assert "TYPE_CHECKING" in fonte
    arvore = ast.parse(fonte)
    for no in arvore.body:
        if isinstance(no, ast.ImportFrom) and no.module == "app.scrapers.base":
            raise AssertionError("app.servicos não pode importar app.scrapers.base no topo")
