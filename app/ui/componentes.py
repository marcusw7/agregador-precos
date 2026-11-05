"""Componentes visuais reutilizáveis (busca, cards, seções)."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.atributos import ATRIBUTOS_POR_CATEGORIA
from app.ui.dados import IMAGEM_PADRAO, numero_ou_none
from app.ui.theme import badge_variacao, esc, formatar_brl, formatar_data


def barra_pesquisa() -> None:
    """Barra de pesquisa global. Ao enviar, navega para o catálogo."""
    with st.form("busca_global"):
        c1, c2, c3 = st.columns([7, 1, 1])
        termo = c1.text_input(
            "Pesquisar produto",
            placeholder="Ex.: RTX 4060, Ryzen 7 7800X3D, SSD NVMe 1TB",
            key="campo_busca",
            label_visibility="collapsed",
        )
        c2.checkbox("Exato", value=True, key="campo_busca_exato")
        enviar = c3.form_submit_button("🔎 Buscar", type="primary", width="stretch")

    if enviar:
        st.session_state["busca_termo"] = (termo or "").strip()
        st.session_state["busca_exato"] = bool(st.session_state.get("campo_busca_exato", True))
        st.query_params["pagina"] = "catalogo"
        st.rerun()


def card_html(linha: pd.Series) -> str:
    """HTML de um card de produto."""
    pid = int(linha["id"])
    imagem = esc(linha["imagem_url"] or IMAGEM_PADRAO)
    nome = esc(linha["nome"])
    categoria = esc(linha["categoria"])
    loja = esc(linha["loja"])
    preco = formatar_brl(linha["preco_atual"])
    menor = formatar_brl(linha["menor_preco_historico"])

    marca = linha.get("Marca")
    partes = []
    if isinstance(marca, str) and marca:
        partes.append(marca)
    for atributo in ATRIBUTOS_POR_CATEGORIA.get(linha["categoria"], []):
        valor = linha.get(atributo)
        if isinstance(valor, str) and valor:
            partes.append(valor)
    # deduplica preservando a ordem
    vistas = []
    for parte in partes:
        if parte not in vistas:
            vistas.append(parte)
    detalhes = " · ".join(vistas)

    variacao = numero_ou_none(linha.get("variacao_7d"))
    dias = numero_ou_none(linha.get("dias_sem_atualizar"))

    no_minimo = float(linha["preco_atual"]) <= float(linha["menor_preco_historico"])

    badges = []
    if no_minimo:
        badges.append('<span class="pt-badge pt-badge-verde">Menor histórico</span>')
    badges.append(badge_variacao(variacao))
    if dias is not None and dias >= 3:
        badges.append(f'<span class="pt-badge pt-badge-ambar">há {int(dias)}d sem atualizar</span>')
    linha_badges = "".join(b for b in badges if b)

    detalhes_html = f'<div class="pt-card-meta">{esc(detalhes)}</div>' if detalhes else ""

    return f"""
    <a class="pt-card" href="?pagina=produto&amp;id={pid}">
      <div class="pt-card-media">
        <img src="{imagem}" loading="lazy" alt="{nome}" onerror="this.onerror=null;this.src='{IMAGEM_PADRAO}';"/>
      </div>
      <div><span class="pt-badge pt-badge-cat">{categoria}</span></div>
      <div class="pt-card-title">{nome}</div>
      {detalhes_html}
      <div><span class="pt-badge pt-badge-loja">🏪 {loja}</span></div>
      <div class="pt-card-price-row"><span class="pt-card-price">R$ {preco}</span></div>
      <div class="pt-card-min">Menor: R$ {menor}</div>
      <div>{linha_badges}</div>
      <div class="pt-card-foot"><span class="pt-card-min">✓ {formatar_data(linha["data_varredura"])}</span></div>
    </a>
    """


def grade_cards_html(df: pd.DataFrame, limite: int = 120) -> str:
    """Grade responsiva de cards a partir de um DataFrame."""
    if df.empty:
        return ""
    cards = "".join(card_html(linha) for _, linha in df.head(limite).iterrows())
    return f'<div class="pt-grid">{cards}</div>'


def secao(titulo: str, link: str | None = None, link_rotulo: str = "Ver tudo") -> None:
    """Título de seção com um link opcional à direita."""
    lado = f'<a href="{link}">{link_rotulo} →</a>' if link else ""
    st.html(
        f'<div class="pt-section"><h2>{esc(titulo)}</h2>{lado}</div>',
    )
