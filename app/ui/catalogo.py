"""Página de catálogo: filtros, pesquisa e grade de produtos."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from app.atributos import ATRIBUTOS_POR_CATEGORIA
from app.categorias import Categoria
from app.consultas import nome_contem_termo
from app.filtros import filtrar, valores_disponiveis
from app.ui.componentes import barra_pesquisa, grade_cards_html
from app.ui.dados import calcular_metricas, carregar_historico_completo, carregar_pecas
from app.ui.theme import formatar_brl

ORDENACOES = {
    "preco_asc": "Menor preço",
    "preco_desc": "Maior preço",
    "queda_7d": "Maior queda (7d)",
    "recentes": "Atualizados recentemente",
}

LIMITE_CARDS = 120


def sidebar_filtros(todas: pd.DataFrame) -> dict:
    """Filtros na barra lateral. Retorna um dicionário com as escolhas."""
    categorias = [c.value for c in Categoria if c.value in set(todas["categoria"])]
    extras = sorted(set(todas["categoria"]) - set(categorias))
    opcoes = ["Todas"] + categorias + extras

    with st.sidebar:
        st.markdown("### 🔎 Filtros")
        escolha = st.radio("Categoria", opcoes)
        categoria = None if escolha == "Todas" else escolha
        base = todas if categoria is None else todas[todas["categoria"] == categoria]

        lojas_escolhidas = st.multiselect(
            "Loja",
            valores_disponiveis(base, "loja"),
            key=f"loja::{categoria or 'todas'}",
            help="Mostra apenas as lojas que têm produtos nesta categoria.",
        )

        faixa = (0.0, 0.0)
        if not base.empty:
            minimo = int(base["preco_atual"].min())
            maximo = int(math.ceil(base["preco_atual"].max()))
            if maximo <= minimo:
                maximo = minimo + 1
            faixa = st.slider(
                "Faixa de preço (R$)",
                min_value=float(minimo),
                max_value=float(maximo),
                value=(float(minimo), float(maximo)),
                step=10.0,
            )

        filtros_atributos: dict[str, list[str]] = {}
        marcas = valores_disponiveis(base, "Marca")
        if marcas:
            escolhidas = st.multiselect("Marca", marcas, key=f"marca::{categoria or 'todas'}")
            if escolhidas:
                filtros_atributos["Marca"] = escolhidas

        if categoria:
            for atributo in ATRIBUTOS_POR_CATEGORIA.get(categoria, []):
                disponiveis = valores_disponiveis(base, atributo)
                if not disponiveis:
                    continue
                escolhidos = st.multiselect(
                    atributo, disponiveis, key=f"attr::{categoria}::{atributo}"
                )
                if escolhidos:
                    filtros_atributos[atributo] = escolhidos

        ordenar = st.selectbox("Ordenar por", list(ORDENACOES), format_func=ORDENACOES.get)
        somente_minimo = st.checkbox("Somente no menor preço histórico")

    return {
        "categoria": categoria,
        "lojas": lojas_escolhidas,
        "atributos": filtros_atributos,
        "preco_min": faixa[0],
        "preco_max": faixa[1],
        "somente_minimo": somente_minimo,
        "ordenar": ordenar,
    }


def _ordenar(df: pd.DataFrame, ordenar: str) -> pd.DataFrame:
    if ordenar == "preco_desc":
        return df.sort_values("preco_atual", ascending=False)
    if ordenar == "recentes":
        return df.sort_values("data_varredura", ascending=False)
    if ordenar == "queda_7d":
        return df.sort_values("variacao_7d", ascending=True, na_position="last")
    return df.sort_values("preco_atual")


def render() -> None:
    todas = carregar_pecas()
    historico = carregar_historico_completo()
    pecas = calcular_metricas(todas, historico)

    barra_pesquisa()

    filtros = sidebar_filtros(todas)

    termo = st.session_state.get("busca_termo", "").strip()
    exato = bool(st.session_state.get("busca_exato", True))

    df = pecas
    if termo:
        df = df[df["nome"].map(lambda nome: nome_contem_termo(nome, termo, exato))]

    df = filtrar(
        df,
        categoria=filtros["categoria"],
        lojas=filtros["lojas"],
        atributos=filtros["atributos"],
        preco_min=filtros["preco_min"],
        preco_max=filtros["preco_max"],
        somente_minimo=filtros["somente_minimo"],
    )
    df = _ordenar(df, filtros["ordenar"])

    if termo:
        st.markdown(f"#### Resultados para “{termo}”")
        st.caption(
            f"{len(df)} oferta(s) encontrada(s)"
            + (" (correspondência exata)" if exato else " (qualquer ordem de palavras)")
        )
    else:
        st.markdown("#### Catálogo de produtos")

    col1, col2, col3 = st.columns(3)
    col1.metric("Produtos encontrados", len(df))
    col2.metric("Lojas nos resultados", df["loja"].nunique() if not df.empty else 0)
    col3.metric(
        "Menor preço exibido",
        f"R$ {formatar_brl(df['preco_atual'].min())}" if not df.empty else "—",
    )

    if df.empty:
        st.info("Nenhum produto encontrado. Ajuste os filtros ou a pesquisa.")
        return

    if len(df) > LIMITE_CARDS:
        st.caption(f"Mostrando {LIMITE_CARDS} de {len(df)} produtos. Use os filtros para refinar.")

    st.markdown(grade_cards_html(df, LIMITE_CARDS), unsafe_allow_html=True)
