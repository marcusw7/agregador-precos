"""Página inicial: visão geral, estatísticas e destaques."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui.componentes import barra_pesquisa, grade_cards_html, secao
from app.ui.coleta_local import coletor_disponivel, iniciar_coleta
from app.ui.dados import (
    calcular_metricas,
    carregar_coletas,
    carregar_historico_completo,
    carregar_pecas,
    numero_ou_none,
    resumo_estatistico,
)
from app.ui.theme import (
    COR_AMBAR,
    COR_VERDE,
    COR_VERMELHO,
    esc,
    formatar_brl,
    formatar_data,
)

DESTAQUES = 8


def _estatisticas(resumo: dict) -> str:
    ultima = formatar_data(resumo["ultima_varredura"])
    return f"""
    <div class="pt-stats">
      <div class="pt-stat"><div class="pt-stat-label">Produtos monitorados</div>
        <div class="pt-stat-value">{resumo['total']}</div>
        <div class="pt-stat-sub">em {resumo['categorias']} categorias</div></div>
      <div class="pt-stat"><div class="pt-stat-label">Lojas</div>
        <div class="pt-stat-value">{resumo['lojas']}</div>
        <div class="pt-stat-sub">fontes monitoradas</div></div>
      <div class="pt-stat"><div class="pt-stat-label">No menor preço</div>
        <div class="pt-stat-value" style="color:{COR_VERDE}">{resumo['no_minimo']}</div>
        <div class="pt-stat-sub">melhores oportunidades</div></div>
      <div class="pt-stat"><div class="pt-stat-label">Última atualização</div>
        <div class="pt-stat-value" style="font-size:20px">{ultima}</div>
        <div class="pt-stat-sub">varredura mais recente</div></div>
    </div>
    """


def _painel_coleta(coletas: pd.DataFrame, resumo: dict) -> None:
    if coletas.empty:
        st.caption("🕒 Nenhuma coleta automática registrada ainda. A primeira execução criará este registro.")
        return

    ultima = coletas.iloc[0]
    status = ultima["status"]
    cor = COR_VERDE if status == "ok" else COR_VERMELHO
    rotulo = "Concluída" if status == "ok" else "Falhou"

    texto = (
        f"Última coleta: <b style='color:{cor}'>{rotulo}</b> em "
        f"{formatar_data(ultima['iniciada_em'])}"
    )
    if status == "ok":
        novas = int(ultima["novas"]) if pd.notna(ultima["novas"]) else 0
        atualizadas = int(ultima["atualizadas"]) if pd.notna(ultima["atualizadas"]) else 0
        texto += f" · {novas} novas · {atualizadas} atualizadas"
    else:
        erro = str(ultima["erro"] or "")[:120]
        if erro:
            texto += f" · <span title='{esc(erro)}'>erro</span>"

    st.markdown(
        f"<div class='pt-stat' style='margin-bottom:20px'><div class='pt-stat-label'>Status da coleta automática</div>"
        f"<div class='pt-stat-sub'>{texto} · próxima: a cada 6 horas (GitHub Actions)</div></div>",
        unsafe_allow_html=True,
    )

    if coletor_disponivel():
        if st.button("⬇️ Atualizar preços agora (roda em segundo plano)"):
            iniciou, detalhe = iniciar_coleta()
            if iniciou:
                st.success(f"Coleta iniciada em segundo plano. Registro: {detalhe}")
            else:
                st.error(f"Não foi possível iniciar a coleta: {detalhe}")


def render() -> None:
    todas = carregar_pecas()
    historico = carregar_historico_completo()
    coletas = carregar_coletas()
    metricas = calcular_metricas(todas, historico)
    resumo = resumo_estatistico(todas, historico, coletas)

    # Hero
    st.markdown(
        """
        <div class="pt-hero">
          <h1>Acompanhe e economize em hardware</h1>
          <p>Compare preços de GPU, CPU, placa-mãe, memória RAM e SSD entre lojas brasileiras,
             com histórico de preços e alertas de queda — tudo em um só lugar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    barra_pesquisa()
    st.markdown(_estatisticas(resumo), unsafe_allow_html=True)
    _painel_coleta(coletas, resumo)

    if todas.empty:
        st.info("Ainda não há produtos monitorados. Aguarde a primeira coleta automática.")
        return

    # Maiores quedas (7 dias)
    quedas = metricas[metricas["variacao_7d"].notna() & (metricas["variacao_7d"] < 0)]
    quedas = quedas.sort_values("variacao_7d").head(DESTAQUES)
    secao("📉 Maiores quedas (7 dias)", "?pagina=catalogo")
    if quedas.empty:
        st.caption("Sem quedas registradas nos últimos 7 dias (ou dados insuficientes).")
    else:
        st.markdown(grade_cards_html(quedas, DESTAQUES), unsafe_allow_html=True)

    # Melhores ofertas (no menor histórico)
    melhores = metricas[metricas["preco_atual"] <= metricas["menor_preco_historico"]]
    melhores = melhores.sort_values("preco_atual").head(DESTAQUES)
    secao("🟢 Melhores ofertas (no menor preço histórico)", "?pagina=catalogo")
    if melhores.empty:
        st.caption("Nenhum produto está no menor preço histórico no momento.")
    else:
        st.markdown(grade_cards_html(melhores, DESTAQUES), unsafe_allow_html=True)

    # Atualizados recentemente
    recentes = metricas.sort_values("data_varredura", ascending=False).head(DESTAQUES)
    secao("🕒 Atualizados recentemente", "?pagina=catalogo")
    st.markdown(grade_cards_html(recentes, DESTAQUES), unsafe_allow_html=True)
