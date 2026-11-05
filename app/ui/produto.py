"""Página de detalhe do produto: histórico, gráfico e comparação entre lojas."""

from __future__ import annotations

from datetime import datetime, timedelta

import altair as alt
import pandas as pd
import streamlit as st

from app.scrapers.normalizacao import chave_comparacao
from app.ui.dados import (
    IMAGEM_PADRAO,
    carregar_historico,
    catalogo_com_metricas,
    numero_ou_none,
)
from app.ui.theme import (
    COR_AMBAR,
    COR_MUDO,
    COR_PRIMARIA,
    COR_VERDE,
    esc,
    formatar_brl,
    formatar_data,
)

PERIODOS = {
    "7 dias": 7,
    "30 dias": 30,
    "90 dias": 90,
    "Completo": None,
}


def _grafico(historico: pd.DataFrame, periodo: str) -> alt.Chart | None:
    dados = historico.copy()
    dias = PERIODOS.get(periodo)
    if dias is not None:
        corte = datetime.now() - timedelta(days=dias)
        dados = dados[pd.to_datetime(dados["data"]) >= corte]
    if dados.empty:
        return None

    linha = (
        alt.Chart(dados)
        .mark_line(point=alt.OverlayMarkDef(size=70, filled=True), color=COR_PRIMARIA, strokeWidth=2.5)
        .encode(
            x=alt.X("data:T", title=None, axis=alt.Axis(format="%d/%m", grid=False, tickColor=COR_MUDO)),
            y=alt.Y(
                "preco:Q",
                title="Preço à vista (R$)",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(format=",.2f", gridColor="#262e3e", tickColor=COR_MUDO),
            ),
            tooltip=[
                alt.Tooltip("data:T", title="Data", format="%d/%m/%Y %H:%M"),
                alt.Tooltip("preco:Q", title="Preço (R$)", format=",.2f"),
            ],
        )
    )

    menor = dados["preco"].min()
    regra_min = (
        alt.Chart(pd.DataFrame({"y": [menor]}))
        .mark_rule(color=COR_VERDE, strokeDash=[4, 4])
        .encode(y="y:Q")
    )

    return (
        (linha + regra_min)
        .properties(height=360)
        .configure_view(strokeWidth=0)
        .configure_axis(labelColor=COR_MUDO, titleColor=COR_MUDO)
        .configure(padding={"left": 8, "top": 10, "right": 16, "bottom": 8})
    )


def _comparacao_lojas(peca: pd.Series, todas: pd.DataFrame) -> pd.DataFrame:
    """Outras ofertas do mesmo produto (título normalizado) em lojas diferentes."""
    chave = chave_comparacao(peca["nome"])
    chaves = todas["nome"].map(chave_comparacao)
    mesmo = todas[chaves == chave]
    if len(mesmo) <= 1:
        return mesmo.iloc[0:0]
    return mesmo.sort_values("preco_atual")


def render() -> None:
    todas = catalogo_com_metricas()

    st.html('<a class="pt-nav-link" href="?pagina=catalogo">← Voltar ao catálogo</a>')

    try:
        peca_id = int(st.query_params.get("id", "0") or 0)
    except (TypeError, ValueError):
        peca_id = 0

    if peca_id <= 0 or todas.empty or peca_id not in set(todas["id"]):
        st.warning("Produto não encontrado. Ele pode ter sido removido ou o link está incorreto.")
        return

    peca = todas[todas["id"] == peca_id].iloc[0]
    historico = carregar_historico(peca_id)

    imagem = peca["imagem_url"] or IMAGEM_PADRAO
    nome = esc(peca["nome"])
    categoria = esc(peca["categoria"])
    loja = esc(peca["loja"])

    # ---- Cabeçalho em duas colunas
    col_esq, col_dir = st.columns([2, 3], gap="large")

    with col_esq:
        st.html(
            f'<div class="pt-produto-img"><img src="{esc(imagem)}" alt="{nome}" '
            f'onerror="this.onerror=null;this.src=\'{IMAGEM_PADRAO}\';"/></div>'
        )

    with col_dir:
        st.html(f'<span class="pt-badge pt-badge-cat">{categoria}</span>')
        st.markdown(f"# {nome}")
        st.html(f'<span class="pt-badge pt-badge-loja">🏪 {loja}</span>')

        # Especificações
        specs = []
        for atributo in ["Marca", "Chip", "VRAM", "Modelo", "Socket", "Chipset", "Tipo", "Interface", "Capacidade", "Frequência", "Tamanho", "Resolução", "Taxa"]:
            valor = peca.get(atributo)
            if isinstance(valor, str) and valor:
                specs.append(f'<span class="pt-badge pt-badge-mudo">{esc(atributo)}: {esc(valor)}</span>')
        if specs:
            st.html(f'<div class="pt-spec">{"".join(specs)}</div>')

        st.html(f'<div class="pt-price-hero">R$ {formatar_brl(peca["preco_atual"])}</div>')

        menor_hist = float(peca["menor_preco_historico"])
        no_minimo = float(peca["preco_atual"]) <= menor_hist
        st.html(
            f'<div class="pt-card-min">Menor preço histórico: <b>R$ {formatar_brl(menor_hist)}</b>'
            f'{" — <span class=&quot;pt-badge pt-badge-verde&quot;>no menor preço</span>" if no_minimo else ""}</div>'
        )

        # Variação 7 dias
        linha = todas[todas["id"] == peca_id]
        if not linha.empty:
            variacao = numero_ou_none(linha.iloc[0].get("variacao_7d"))
            if variacao is not None:
                sinal = "▼" if variacao < 0 else ("▲" if variacao > 0 else "=")
                cor = COR_VERDE if variacao < 0 else ("#f87171" if variacao > 0 else COR_MUDO)
                variacao_txt = f"{variacao:+.1f}".replace(".", ",")
                st.html(f'Variação (7 dias): <b style="color:{cor}">{sinal} {variacao_txt}%</b>')

        st.html(f'<div class="pt-card-min">Última verificação: {formatar_data(peca["data_varredura"])}</div>')

        st.html(
            f'<a class="pt-btn pt-btn-primario" href="{esc(peca["link"])}" target="_blank" rel="noopener">'
            "Ir para a Loja ↗</a>"
        )

    st.divider()

    # ---- Histórico
    st.html('<div class="pt-section"><h2>📈 Histórico de preços</h2></div>')

    if historico.empty:
        st.info("Este produto ainda não tem histórico registrado.")
    else:
        periodo = st.segmented_control(
            "Período",
            options=list(PERIODOS),
            default="30 dias",
            label_visibility="collapsed",
        )
        periodo = periodo or "30 dias"

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Atual", f"R$ {formatar_brl(historico['preco'].iloc[-1])}")
        c2.metric("Menor registrado", f"R$ {formatar_brl(historico['preco'].min())}")
        c3.metric("Maior registrado", f"R$ {formatar_brl(historico['preco'].max())}")
        c4.metric("Média histórica", f"R$ {formatar_brl(historico['preco'].mean())}")

        grafico = _grafico(historico, periodo)
        if grafico is not None:
            st.altair_chart(grafico, width="stretch")
        else:
            st.caption("Sem registros no período selecionado.")

        if len(historico) == 1:
            st.caption("Ainda há só uma varredura para este produto. O gráfico ganha linhas nas próximas atualizações.")

    # ---- Comparação entre lojas
    comparacao = _comparacao_lojas(peca, todas)
    if len(comparacao) > 1:
        st.divider()
        st.html('<div class="pt-section"><h2>🏪 Ofertas do mesmo produto</h2></div>')
        tabela = comparacao[
            ["loja", "preco_atual", "menor_preco_historico", "data_varredura", "link"]
        ].rename(
            columns={
                "loja": "Loja",
                "preco_atual": "Preço à vista",
                "menor_preco_historico": "Menor histórico",
                "data_varredura": "Última varredura",
                "link": "Link",
            }
        )
        st.dataframe(
            tabela,
            hide_index=True,
            column_config={
                "Preço à vista": st.column_config.NumberColumn(format="R$ %.2f"),
                "Menor histórico": st.column_config.NumberColumn(format="R$ %.2f"),
                "Última varredura": st.column_config.DatetimeColumn(format="DD/MM/YYYY HH:mm"),
                "Link": st.column_config.LinkColumn("Link", display_text="Abrir"),
            },
        )

    st.html(f'<div class="pt-card-min" style="color:{COR_AMBAR}">Preços à vista; podem variar conforme a loja.</div>')
