"""Testes da migração SQLite -> SQLite (mesma engine que o PostgreSQL usa).

O script de migração é agnóstico de dialeto: a única parte específica de PostgreSQL
(o ajuste de sequência) só roda quando o dialeto é postgresql. Assim, esta bateria
comprova a lógica sem exigir um servidor PostgreSQL.
"""

import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import HistoricoPreco, Peca
from app.scrapers.base import ItemProduto
from app.servicos import salvar_itens

RAIZ = Path(__file__).resolve().parent.parent


def _carregar_script():
    caminho = RAIZ / "scripts" / "migrar_sqlite_para_postgres.py"
    spec = importlib.util.spec_from_file_location("migrar_sqlite", caminho)
    modulo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(modulo)
    return modulo


@pytest.fixture
def origem(tmp_path):
    """SQLite de origem com 2 peças (IDs 1 e 2) e histórico."""
    caminho = tmp_path / "origem.db"
    engine = create_engine(f"sqlite:///{caminho}")
    Base.metadata.create_all(engine)
    Sessao = sessionmaker(bind=engine)

    def item(link, preco, titulo):
        return ItemProduto(
            titulo=titulo,
            categoria="GPU",
            preco_avista=Decimal(preco),
            parcelamento=None,
            num_parcelas=None,
            valor_parcela=None,
            loja="LojaTeste",
            link=link,
        )

    with Sessao() as db:
        salvar_itens(db, [item("https://t/1", "1000.00", "RTX 4060 A")])
        salvar_itens(db, [item("https://t/2", "2000.00", "RX 7600 B")])
        salvar_itens(db, [item("https://t/1", "900.00", "RTX 4060 A")])
    engine.dispose()
    return caminho


@pytest.fixture
def destino(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'destino.db'}")
    yield engine
    engine.dispose()


def test_simulacao_nao_grava(origem, destino):
    modulo = _carregar_script()
    resumo = modulo.migrar(origem, destino, executar=False)

    assert resumo["dry_run"] is True
    assert resumo["pecas_origem"] == 2
    assert resumo["historico_origem"] == 3

    with destino.connect() as con:
        tabelas = con.dialect.has_table(con, "pecas")
    assert tabelas is False  # nada foi criado no destino


def test_migracao_preserva_ids_pecas_e_historico(origem, destino):
    modulo = _carregar_script()
    resumo = modulo.migrar(origem, destino, executar=True)

    assert resumo["pecas_inseridas"] == 2
    assert resumo["historico_inserido"] == 3

    with destino.connect() as con:
        pecas = con.execute(
            select(Peca.__table__.c.id, Peca.__table__.c.link).order_by(Peca.__table__.c.id)
        ).all()
        historico = con.execute(
            select(HistoricoPreco.__table__.c.peca_id).order_by(
                HistoricoPreco.__table__.c.id
            )
        ).all()

    assert [linha.id for linha in pecas] == [1, 2]
    assert [linha.link for linha in pecas] == ["https://t/1", "https://t/2"]
    assert len(historico) == 3


def test_migracao_e_repetivel_sem_duplicar(origem, destino):
    modulo = _carregar_script()
    modulo.migrar(origem, destino, executar=True)
    segundo = modulo.migrar(origem, destino, executar=True)

    assert segundo["pecas_inseridas"] == 0
    assert segundo["pecas_atualizadas"] == 2
    assert segundo["historico_inserido"] == 0
    assert segundo["historico_ignorado"] == 3

    Sessao = sessionmaker(bind=destino)
    with Sessao() as db:
        assert db.scalar(select(func.count()).select_from(Peca)) == 2
        assert db.scalar(select(func.count()).select_from(HistoricoPreco)) == 3


def test_migracao_preserva_preco_e_menor_preco(origem, destino):
    modulo = _carregar_script()
    modulo.migrar(origem, destino, executar=True)

    Sessao = sessionmaker(bind=destino)
    with Sessao() as db:
        peca = db.scalar(select(Peca).where(Peca.link == "https://t/1"))
        assert peca.preco_atual == Decimal("900.00")
        assert peca.menor_preco_historico == Decimal("900.00")
        assert peca.data_varredura is not None
        precos = [h.preco for h in peca.historico]
        assert precos == [Decimal("1000.00"), Decimal("900.00")]
