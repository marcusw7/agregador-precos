from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.categorias import Categoria
from app.consultas import buscar_pecas
from app.database import Base
from app.models import HistoricoPreco, Peca
from app.scrapers.base import ItemProduto
from app.servicos import registrar_coleta, salvar_itens


@pytest.fixture
def db():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    sessao = sessionmaker(bind=engine)()
    yield sessao
    sessao.close()
    engine.dispose()


def item(link: str, preco: str | None, categoria: str = Categoria.GPU.value, titulo: str = "RTX 4060") -> ItemProduto:
    return ItemProduto(
        titulo=titulo,
        categoria=categoria,
        preco_avista=Decimal(preco) if preco is not None else None,
        parcelamento=None,
        num_parcelas=None,
        valor_parcela=None,
        loja="KaBuM!",
        link=link,
    )


def test_salvar_cria_e_depois_atualiza_menor_preco(db: Session):
    resumo = salvar_itens(db, [item("https://x/1", "2000.00")])
    assert resumo == {"novas": 1, "atualizadas": 0, "sem_preco": 0}

    resumo = salvar_itens(db, [item("https://x/1", "1800.00")])
    assert resumo == {"novas": 0, "atualizadas": 1, "sem_preco": 0}

    peca = db.scalar(select(Peca).where(Peca.link == "https://x/1"))
    assert peca.preco_atual == Decimal("1800.00")
    assert peca.menor_preco_historico == Decimal("1800.00")

    salvar_itens(db, [item("https://x/1", "2100.00")])
    db.refresh(peca)
    assert peca.preco_atual == Decimal("2100.00")
    assert peca.menor_preco_historico == Decimal("1800.00")


def test_salvar_registra_historico_de_precos(db: Session):
    salvar_itens(db, [item("https://x/1", "2000.00")])
    salvar_itens(db, [item("https://x/1", "1800.00")])
    salvar_itens(db, [item("https://x/1", "2100.00")])

    peca = db.scalar(select(Peca).where(Peca.link == "https://x/1"))
    precos = [h.preco for h in peca.historico]
    assert precos == [Decimal("2000.00"), Decimal("1800.00"), Decimal("2100.00")]


def test_salvar_ignora_sem_preco_e_deduplica_link(db: Session):
    itens = [
        item("https://x/1", "2000.00"),
        item("https://x/1", "1900.00"),
        item("https://x/2", None),
    ]
    resumo = salvar_itens(db, itens)

    assert resumo == {"novas": 1, "atualizadas": 0, "sem_preco": 1}
    assert db.query(Peca).count() == 1


def test_buscar_pecas_filtra_categoria_preco_e_minimo_historico(db: Session):
    salvar_itens(db, [
        item("https://x/1", "1000.00", Categoria.GPU.value, "GPU barata"),
        item("https://x/2", "3000.00", Categoria.GPU.value, "GPU cara"),
        item("https://x/3", "500.00", Categoria.CPU.value, "CPU"),
    ])
    salvar_itens(db, [item("https://x/1", "1200.00", Categoria.GPU.value, "GPU barata")])

    so_gpu = buscar_pecas(db, categoria=Categoria.GPU)
    assert [p.nome for p in so_gpu] == ["GPU barata", "GPU cara"]

    ate_2000 = buscar_pecas(db, categoria=Categoria.GPU, preco_max=Decimal("2000"))
    assert [p.nome for p in ate_2000] == ["GPU barata"]

    no_minimo = buscar_pecas(db, somente_minimo_historico=True)
    assert "GPU barata" not in [p.nome for p in no_minimo]
    assert "CPU" in [p.nome for p in no_minimo]

    decrescente = buscar_pecas(db, ordenar="preco_desc")
    assert [p.nome for p in decrescente][0] == "GPU cara"


def test_buscar_pecas_paginacao(db: Session):
    salvar_itens(db, [item(f"https://x/{i}", str(1000 + i)) for i in range(5)])

    pagina_2 = buscar_pecas(db, pagina=2, tamanho=2)
    assert [p.preco_atual for p in pagina_2] == [Decimal("1002.00"), Decimal("1003.00")]


def test_registrar_coleta_cria_linha_de_auditoria(db: Session):
    from datetime import datetime

    from app.models import Coleta

    inicio = datetime.now()
    coleta = registrar_coleta(
        db,
        iniciada_em=inicio,
        terminada_em=datetime.now(),
        status="ok",
        coletados=10,
        novas=2,
        atualizadas=8,
        sem_preco=0,
        descartados=3,
    )

    assert coleta.id is not None
    assert coleta.status == "ok"
    assert coleta.novas == 2
    registros = db.query(Coleta).all()
    assert len(registros) == 1


def test_registrar_coleta_de_erro(db: Session):
    from datetime import datetime

    coleta = registrar_coleta(
        db,
        iniciada_em=datetime.now(),
        terminada_em=datetime.now(),
        status="erro",
        erro="PlaywrightTimeout: timeout",
    )
    assert coleta.status == "erro"
    assert "PlaywrightTimeout" in coleta.erro
