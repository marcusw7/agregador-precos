"""Testes da camada de banco: SQLite sempre; PostgreSQL quando TEST_DATABASE_URL existir."""

import os
import subprocess
import sys
from decimal import Decimal
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from app.database import Base, criar_engine, mascarar_url, normalizar_url, url_do_ambiente
from app.models import HistoricoPreco, Peca
from app.servicos import salvar_itens

RAIZ = Path(__file__).resolve().parent.parent
ITEM = {
    "titulo": "Placa de Teste RTX 4060",
    "categoria": "GPU",
    "parcelamento": None,
    "num_parcelas": None,
    "valor_parcela": None,
    "loja": "LojaTeste",
}


# ---------------------------------------------------------------- funções puras
def test_normalizar_url_converte_formatos_dos_provedores():
    assert normalizar_url("postgres://u:p@h/db").startswith("postgresql+psycopg://")
    assert normalizar_url("postgresql://u:p@h/db").startswith("postgresql+psycopg://")
    assert normalizar_url("sqlite:///x.db") == "sqlite:///x.db"
    assert normalizar_url("  ") == ""


def test_mascarar_url_esconde_a_senha():
    mascarada = mascarar_url("postgres://usuario:segredo@host/db")
    assert "segredo" not in mascarada
    assert "usuario" in mascarada and "***" in mascarada
    assert mascarar_url("sqlite:///x.db") == "sqlite:///x.db"


def test_criar_engine_resolve_dialetos_sem_conectar():
    sqlite = criar_engine("sqlite:///arquivo-inexistente.db")
    assert sqlite.dialect.name == "sqlite"

    postgres = criar_engine(normalizar_url("postgres://u:p@localhost:5432/db"))
    assert postgres.dialect.name == "postgresql"
    assert postgres.url.drivername == "postgresql+psycopg"


def test_sem_variavel_de_ambiente_usa_sqlite_local():
    if os.environ.get("DATABASE_URL"):
        pytest.skip("DATABASE_URL definido no ambiente; o padrão local não se aplica")
    assert url_do_ambiente() == ""
    import app.database as database

    assert database.engine.dialect.name == "sqlite"
    assert database.usar_sqlite() and not database.usar_postgres()


def test_variavel_de_ambiente_e_honrada_em_processo_limpo():
    """Importa app.database num processo novo com DATABASE_URL definido."""
    codigo = (
        "import os;"
        "os.environ['DATABASE_URL']='postgres://u:p@localhost:5432/db';"
        "import app.database as d;"
        "print(d.engine.url.drivername, d.engine.dialect.name)"
    )
    saida = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "DATABASE_URL": ""},
    )
    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip() == "postgresql+psycopg postgresql"


def test_secrets_do_streamlit_sao_lidos_quando_nao_ha_variavel():
    """No Streamlit Cloud os segredos chegam por st.secrets, não por env."""
    codigo = (
        "import sys, types, os;"
        "os.environ.pop('DATABASE_URL', None);"
        "st = types.ModuleType('streamlit');"
        "st.secrets = {'DATABASE_URL': 'postgres://u:p@localhost:5432/db'};"
        "sys.modules['streamlit'] = st;"
        "import app.database as d;"
        "print(d.engine.url.drivername, d.engine.dialect.name)"
    )
    saida = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=120,
        env={**os.environ, "DATABASE_URL": ""},
    )
    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip() == "postgresql+psycopg postgresql"


def test_sem_streamlit_instalado_usa_variavel_de_ambiente():
    """O coletor não tem Streamlit e precisa continuar lendo a variável de ambiente."""
    codigo = (
        "import sys, os;"
        "sys.modules['streamlit'] = None;"  # força ImportError no import local
        "os.environ['DATABASE_URL'] = 'sqlite:///via-env.db';"
        "import app.database as d;"
        "print(d.engine.url.drivername)"
    )
    saida = subprocess.run(
        [sys.executable, "-c", codigo],
        cwd=RAIZ,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert saida.returncode == 0, saida.stderr
    assert saida.stdout.strip() == "sqlite"


# ---------------------------------------------------------------- CRUD (SQLite temporário)
@pytest.fixture
def engine_temporario(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'teste.db'}")
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def _item(link: str, preco: str):
    from app.scrapers.base import ItemProduto

    return ItemProduto(preco_avista=Decimal(preco), link=link, **ITEM)


def test_criacao_de_tabelas_e_historico(engine_temporario):
    Sessao = sessionmaker(bind=engine_temporario)
    with Sessao() as db:
        salvar_itens(db, [_item("https://teste/1", "1000.00")])
        salvar_itens(db, [_item("https://teste/1", "900.00")])

        peca = db.scalar(select(Peca).where(Peca.link == "https://teste/1"))
        assert peca.id == 1
        assert peca.preco_atual == Decimal("900.00")
        assert peca.menor_preco_historico == Decimal("900.00")

        registros = db.scalars(
            select(HistoricoPreco).where(HistoricoPreco.peca_id == peca.id)
        ).all()
        assert [r.preco for r in registros] == [Decimal("1000.00"), Decimal("900.00")]
        assert all(r.data_registro is not None for r in registros)


# ---------------------------------------------------------------- PostgreSQL real (opcional)
@pytest.fixture(scope="module")
def engine_postgres():
    url = os.environ.get("TEST_DATABASE_URL", "").strip()
    if not url:
        pytest.skip("TEST_DATABASE_URL não definido; teste de PostgreSQL não executado")
    if not url.startswith(("postgres://", "postgresql://", "postgresql+psycopg://")):
        pytest.skip("TEST_DATABASE_URL não aponta para PostgreSQL")
    engine = criar_engine(normalizar_url(url))
    Base.metadata.create_all(engine)
    yield engine
    engine.dispose()


def test_postgres_crud_e_historico(engine_postgres):
    from app.consultas import buscar_pecas
    from app.categorias import Categoria

    Sessao = sessionmaker(bind=engine_postgres)
    link = "https://teste-postgres/migracao"
    try:
        with Sessao() as db:
            salvar_itens(db, [_item(link, "1500.00")])
            salvar_itens(db, [_item(link, "1400.00")])

            peca = db.scalar(select(Peca).where(Peca.link == link))
            assert peca is not None
            assert peca.preco_atual == Decimal("1400.00")
            assert peca.menor_preco_historico == Decimal("1400.00")

            registros = db.scalars(
                select(HistoricoPreco).where(HistoricoPreco.peca_id == peca.id)
            ).all()
            assert len(registros) == 2

            encontradas = buscar_pecas(db, categoria=Categoria.GPU, loja="LojaTeste")
            assert link in [p.link for p in encontradas]
    finally:
        with Sessao() as db:
            peca = db.scalar(select(Peca).where(Peca.link == link))
            if peca is not None:
                db.delete(peca)  # cascade remove o histórico
                db.commit()
