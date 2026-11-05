"""Página de catálogo: filtros, pesquisa, paginação e grade de produtos."""

from __future__ import annotations

import math

import pandas as pd
import streamlit as st

from app.atributos import ATRIBUTOS_POR_CATEGORIA
from app.categorias import Categoria
from app.consultas import nome_contem_termo
from app.filtros import filtrar, valores_disponiveis
from app.ui.componentes import barra_pesquisa, grade_cards_html
from app.ui.dados import catalogo_com_metricas
from app.ui.theme import formatar_brl

ORDENACOES = {
    "preco_asc": "Menor preço",
    "preco_desc": "Maior preço",
    "queda_7d": "Maior queda (7d)",
    "recentes": "Atualizados recentemente",
}

TAMANHOS_PAGINA = [24, 48, 60, 120]
PAGINA_PADRAO = 24


def sidebar_filtros(pecas: pd.DataFrame) -> dict:
    """Filtros na barra lateral. Retorna um dicionário com as escolhas."""
    categorias = [c.value for c in Categoria if c.value in set(pecas["categoria"])]
    extras = sorted(set(pecas["categoria"]) - set(categorias))
    opcoes = ["Todas"] + categorias + extras

    with st.sidebar:
        st.markdown("### 🔎 Filtros")
        escolha = st.radio("Categoria", opcoes)
        categoria = None if escolha == "Todas" else escolha
        base = pecas if categoria is None else pecas[pecas["categoria"] == categoria]

        lojas_escolhidas = st.multiselect(
            "Loja",
            valores_disponiveis(base, "loja"),
            key=f"loja::{categoria or 'todas'}",
            placeholder="Todas as lojas",
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
                format="R$ %.0f",
                help="Arraste as extremidades para definir o intervalo.",
            )
            st.caption(
                f"Disponível: R$ {formatar_brl(minimo)} – R$ {formatar_brl(maximo)}"
            )

        filtros_atributos: dict[str, list[str]] = {}
        marcas = valores_disponiveis(base, "Marca")
        if marcas:
            escolhidas = st.multiselect(
                "Marca",
                marcas,
                key=f"marca::{categoria or 'todas'}",
                placeholder="Todas as marcas",
            )
            if escolhidas:
                filtros_atributos["Marca"] = escolhidas

        if categoria:
            for atributo in ATRIBUTOS_POR_CATEGORIA.get(categoria, []):
                disponiveis = valores_disponiveis(base, atributo)
                if not disponiveis:
                    continue
                escolhidos = st.multiselect(
                    atributo,
                    disponiveis,
                    key=f"attr::{categoria}::{atributo}",
                    placeholder=f"Selecionar {atributo.lower()}",
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


def _assinatura_filtros(filtros: dict, termo: str, exato: bool, por_pagina: int) -> tuple:
    """Identifica o estado dos filtros para resetar a paginação quando mudam."""
    atributos = tuple(
        sorted((k, tuple(sorted(v))) for k, v in filtros["atributos"].items())
    )
    return (
        filtros["categoria"],
        tuple(sorted(filtros["lojas"])),
        atributos,
        filtros["preco_min"],
        filtros["preco_max"],
        filtros["somente_minimo"],
        filtros["ordenar"],
        termo,
        exato,
        por_pagina,
    )


def _controles_pagina(total_paginas: int, pagina: int) -> None:
    """Botões de navegação entre páginas."""
    b1, b2, b3 = st.columns([1, 2, 1])
    if b1.button("◀ Anterior", disabled=pagina <= 1, width="stretch", key="pag_anterior"):
        st.session_state["pagina"] = pagina - 1
        st.rerun()
    b2.html(
        f"<div style='text-align:center;padding-top:9px;color:#94a3b8;font-size:14px'>"
        f"Página <b>{pagina}</b> de <b>{total_paginas}</b></div>"
    )
    if b3.button("Próxima ▶", disabled=pagina >= total_paginas, width="stretch", key="pag_proxima"):
        st.session_state["pagina"] = pagina + 1
        st.rerun()


def render() -> None:
    pecas = catalogo_com_metricas()

    barra_pesquisa()

    filtros = sidebar_filtros(pecas)

    termo = st.session_state.get("busca_termo", "").strip()
    exato = bool(st.session_state.get("busca_exato", True))
    por_pagina = int(st.session_state.get("por_pagina") or PAGINA_PADRAO)

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

    # Volta para a primeira página sempre que os filtros mudam.
    assinatura = _assinatura_filtros(filtros, termo, exato, por_pagina)
    if st.session_state.get("_assinatura") != assinatura:
        st.session_state["_assinatura"] = assinatura
        st.session_state["pagina"] = 1

    total = len(df)
    total_paginas = max(1, math.ceil(total / por_pagina))
    pagina = int(st.session_state.get("pagina", 1))
    pagina = min(max(1, pagina), total_paginas)
    st.session_state["pagina"] = pagina
    inicio = (pagina - 1) * por_pagina
    pagina_df = df.iloc[inicio : inicio + por_pagina]

    if termo:
        st.markdown(f"#### Resultados para “{termo}”")
        st.caption(
            f"{total} oferta(s) encontrada(s)"
            + (" (correspondência exata)" if exato else " (qualquer ordem de palavras)")
        )
    else:
        st.markdown("#### Catálogo de produtos")

    col1, col2, col3 = st.columns(3)
    col1.metric("Produtos encontrados", total)
    col2.metric("Lojas nos resultados", df["loja"].nunique() if not df.empty else 0)
    col3.metric(
        "Menor preço exibido",
        f"R$ {formatar_brl(df['preco_atual'].min())}" if not df.empty else "—",
    )

    if df.empty:
        st.info("Nenhum produto encontrado. Ajuste os filtros ou a pesquisa.")
        return

    # Barra superior: resumo do intervalo + itens por página
    c_info, c_tamanho = st.columns([3, 2], vertical_alignment="center")
    c_info.caption(
        f"Mostrando {inicio + 1}–{min(inicio + por_pagina, total)} de {total} produtos"
    )
    with c_tamanho:
        st.pills(
            "Itens por página",
            TAMANHOS_PAGINA,
            default=PAGINA_PADRAO,
            key="por_pagina",
            label_visibility="collapsed",
        )

    st.html(grade_cards_html(pagina_df, por_pagina))

    if total_paginas > 1:
        _controles_pagina(total_paginas, pagina)
