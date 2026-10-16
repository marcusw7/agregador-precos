"""O coletor precisa conseguir ser o PRIMEIRO processo em um banco vazio.

Sem isso, a coleta agendada falharia num PostgreSQL recém-criado (Neon/Supabase).
Este teste roda em processo separado, apontando DATABASE_URL para um arquivo novo,
e não acessa a internet.
"""

import sqlite3
import subprocess
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

CODIGO = """
import os
from decimal import Decimal

os.environ["DATABASE_URL"] = "sqlite:///{caminho}"

from app.coleta import garantir_esquema
from app.scrapers.base import ItemProduto
from app.servicos import abrir_sessao, salvar_itens

garantir_esquema()
garantir_esquema()  # precisa ser idempotente

item = ItemProduto(
    titulo="Placa de Teste RTX 4060",
    categoria="GPU",
    preco_avista=Decimal("1234.00"),
    parcelamento=None,
    num_parcelas=None,
    valor_parcela=None,
    loja="LojaTeste",
    link="https://teste/coletor-primeiro",
)
with abrir_sessao() as db:
    print(salvar_itens(db, [item]))
"""


def test_coletor_cria_tabelas_e_grava_em_banco_novo(tmp_path):
    alvo = tmp_path / "novo.db"
    codigo = CODIGO.format(caminho=str(alvo).replace("\\", "/"))

    saida = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=180,
    )
    assert saida.returncode == 0, saida.stderr
    assert "'novas': 1" in saida.stdout.replace('"', "'")

    with sqlite3.connect(alvo) as con:
        tabelas = {linha[0] for linha in con.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        assert {"pecas", "historico_precos"} <= tabelas
        assert con.execute("SELECT COUNT(*) FROM pecas").fetchone()[0] == 1
        assert con.execute("SELECT COUNT(*) FROM historico_precos").fetchone()[0] == 1
