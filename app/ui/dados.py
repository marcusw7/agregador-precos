"""Camada de dados compartilhada pelas páginas do PromoTracker.

Centraliza as leituras do banco (com cache) e o cálculo de métricas derivadas
(como a variação percentual de 7 dias), evitando duplicação entre as páginas.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

import pandas as pd
import streamlit as st
from sqlalchemy import select

from app.atributos import TODOS_ATRIBUTOS, extrair_atributos
from app.database import SessionLocal
from app.models import Coleta, HistoricoPreco, Peca

IMAGEM_PADRAO = "https://placehold.co/400x300/161b24/94a3b8?text=Sem+foto"


@st.cache_data(ttl=60)
def carregar_pecas() -> pd.DataFrame:
    """Todas as ofertas salvas, com os atributos (marca, chip, socket...) derivados do título."""
    with SessionLocal() as db:
        pecas = db.scalars(select(Peca).order_by(Peca.preco_atual)).all()
        registros = [
            {
                "id": p.id,
                "nome": p.nome,
                "categoria": p.categoria,
                "preco_atual": float(p.preco_atual),
                "menor_preco_historico": float(p.menor_preco_historico),
                "loja": p.loja,
                "link": p.link,
                "imagem_url": p.imagem_url,
                "data_varredura": p.data_varredura,
            }
            for p in pecas
        ]

    df = pd.DataFrame(registros)
    if df.empty:
        return df

    atributos = pd.DataFrame(
        [extrair_atributos(nome, categoria) for nome, categoria in zip(df["nome"], df["categoria"])]
    ).reindex(columns=TODOS_ATRIBUTOS)
    return pd.concat([df.reset_index(drop=True), atributos.reset_index(drop=True)], axis=1)


@st.cache_data(ttl=60)
def carregar_historico_completo() -> pd.DataFrame:
    """Todo o histórico de preços (peca_id, data, preco)."""
    with SessionLocal() as db:
        registros = db.scalars(
            select(HistoricoPreco).order_by(HistoricoPreco.data_registro)
        ).all()
        return pd.DataFrame(
            [
                {"peca_id": r.peca_id, "data": r.data_registro, "preco": float(r.preco)}
                for r in registros
            ]
        )


@st.cache_data(ttl=60)
def carregar_historico(peca_id: int) -> pd.DataFrame:
    """Histórico de preços de uma peça específica."""
    with SessionLocal() as db:
        registros = db.scalars(
            select(HistoricoPreco)
            .where(HistoricoPreco.peca_id == peca_id)
            .order_by(HistoricoPreco.data_registro)
        ).all()
        return pd.DataFrame(
            [{"data": r.data_registro, "preco": float(r.preco)} for r in registros]
        )


@st.cache_data(ttl=60)
def carregar_coletas(limite: int = 20) -> pd.DataFrame:
    """Últimas execuções do coletor (status e contadores)."""
    with SessionLocal() as db:
        coletas = db.scalars(
            select(Coleta).order_by(Coleta.iniciada_em.desc()).limit(limite)
        ).all()
        return pd.DataFrame(
            [
                {
                    "id": c.id,
                    "iniciada_em": c.iniciada_em,
                    "terminada_em": c.terminada_em,
                    "status": c.status,
                    "termo": c.termo,
                    "coletados": c.coletados,
                    "novas": c.novas,
                    "atualizadas": c.atualizadas,
                    "sem_preco": c.sem_preco,
                    "descartados": c.descartados,
                    "erro": c.erro,
                }
                for c in coletas
            ]
        )


def numero_ou_none(valor) -> float | None:
    """Converte NaN do pandas em None, para exibição segura."""
    if valor is None:
        return None
    try:
        if pd.isna(valor):
            return None
    except (TypeError, ValueError):
        pass
    return float(valor)


def calcular_metricas(pecas: pd.DataFrame, historico: pd.DataFrame) -> pd.DataFrame:
    """Adiciona variação percentual (7 dias) e dias sem atualizar.

    A variação compara o preço atual com o último preço registrado há 7 dias ou
    mais. Quando não há dado suficiente, permanece ``None`` (não inventamos nada).
    """
    if pecas.empty:
        pecas = pecas.copy()
        pecas["variacao_7d"] = None
        pecas["dias_sem_atualizar"] = 0
        return pecas

    agora = datetime.now()
    corte = agora - timedelta(days=7)

    pecas = pecas.copy()
    pecas["dias_sem_atualizar"] = (agora - pd.to_datetime(pecas["data_varredura"])).dt.days

    if historico.empty:
        pecas["variacao_7d"] = None
        return pecas

    historico = historico.copy()
    historico["data"] = pd.to_datetime(historico["data"])
    antigo = historico[historico["data"] <= corte]
    if antigo.empty:
        pecas["variacao_7d"] = None
        return pecas

    base = antigo.sort_values("data").groupby("peca_id").tail(1)
    base = base.drop_duplicates("peca_id", keep="last").set_index("peca_id")["preco"]

    preco_base = pecas["id"].map(base)
    variacao = (pecas["preco_atual"] - preco_base) / preco_base * 100.0
    variacao = variacao.where(preco_base.notna())
    pecas["variacao_7d"] = variacao.where(~variacao.isin([math.inf, -math.inf]))
    return pecas


def resumo_estatistico(pecas: pd.DataFrame, historico: pd.DataFrame, coletas: pd.DataFrame) -> dict:
    """Números para o topo do dashboard."""
    total = len(pecas)
    lojas = pecas["loja"].nunique() if total else 0
    categorias = pecas["categoria"].nunique() if total else 0

    ultima_varredura = None
    if total and pecas["data_varredura"].notna().any():
        ultima_varredura = pd.to_datetime(pecas["data_varredura"]).max()

    ultima_coleta = None
    if not coletas.empty:
        ultima = coletas.iloc[0]
        ultima_coleta = {
            "status": ultima["status"],
            "iniciada_em": ultima["iniciada_em"],
            "terminada_em": ultima["terminada_em"],
            "novas": int(ultima["novas"]) if pd.notna(ultima["novas"]) else 0,
            "atualizadas": int(ultima["atualizadas"]) if pd.notna(ultima["atualizadas"]) else 0,
        }

    no_minimo = 0
    if total:
        no_minimo = int((pecas["preco_atual"] <= pecas["menor_preco_historico"]).sum())

    return {
        "total": total,
        "lojas": lojas,
        "categorias": categorias,
        "ultima_varredura": ultima_varredura,
        "ultima_coleta": ultima_coleta,
        "no_minimo": no_minimo,
    }
