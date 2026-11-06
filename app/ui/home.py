"""Página inicial: visão geral, estatísticas e destaques."""

from __future__ import annotations

import pandas as pd
import streamlit as st

from app.ui.componentes import barra_pesquisa, grade_cards_html, secao
from app.ui.coleta_local import coletor_disponivel, iniciar_coleta
from app.ui.dados import (
    carregar_coletas,
    catalogo_com_metricas,
    resumo_estatistico,
)
from app.ui.theme import (
    COR_VERDE,
    COR_VERMELHO,
    esc,
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

    if status == "ok":
        cor = COR_VERDE
        rotulo = "Concluída"
    elif status == "parcial":
        cor = "#fbbf24"
        rotulo = "Parcial (algumas lojas falharam)"
    else:
        cor = COR_VERMELHO
        rotulo = "Falhou"

    # Tempo de execução
    duracao = ""
    if pd.notna(ultima["iniciada_em"]) and pd.notna(ultima["terminada_em"]):
        segundos = (pd.to_datetime(ultima["terminada_em"]) - pd.to_datetime(ultima["iniciada_em"])).total_seconds()
        duracao = f" · {int(segundos // 60)}min {int(segundos % 60)}s"

    texto = (
        f"Última execução: <b style='color:{cor}'>{rotulo}</b> em "
        f"{formatar_data(ultima['iniciada_em'])}{duracao}"
    )
    if status in ("ok", "parcial"):
        novas = int(ultima["novas"]) if pd.notna(ultima["novas"]) else 0
        atualizadas = int(ultima["atualizadas"]) if pd.notna(ultima["atualizadas"]) else 0
        texto += f" · {novas} novas · {atualizadas} atualizadas"

    linhas = [texto]

    # Lojas com falha (quando parcial)
    if status in ("parcial", "erro") and ultima["erro"]:
        linhas.append(f"<span style='color:#fbbf24'>{esc(str(ultima['erro'])[:200])}</span>")

    # Última bem-sucedida (diferente da última execução, se a última falhou)
    bem_sucedidas = coletas[coletas["status"].isin(["ok", "parcial"])]
    if status not in ("ok", "parcial") and not bem_sucedidas.empty:
        ultima_ok = bem_sucedidas.iloc[0]
        linhas.append(
            f"Última bem-sucedida: {formatar_data(ultima_ok['iniciada_em'])}"
        )

    # Produtos desatualizados
    linhas.append(
        f"{resumo.get('desatualizados', 0)} produtos há 7+ dias sem atualização"
    )

    corpo = "".join(f"<div class='pt-stat-sub'>{l}</div>" for l in linhas)
    st.html(
        f"<div class='pt-stat' style='margin-bottom:20px'>"
        f"<div class='pt-stat-label'>Status da coleta automática</div>{corpo}"
        f"<div class='pt-stat-sub' style='margin-top:6px'>próxima: a cada 6 horas (GitHub Actions)</div></div>"
    )

    if coletor_disponivel():
        if st.button("⬇️ Atualizar preços agora (roda em segundo plano)"):
            iniciou, detalhe = iniciar_coleta()
            if iniciou:
                st.success(f"Coleta iniciada em segundo plano. Registro: {detalhe}")
            else:
                st.error(f"Não foi possível iniciar a coleta: {detalhe}")


def render() -> None:
    metricas = catalogo_com_metricas()
    coletas = carregar_coletas()
    resumo = resumo_estatistico(metricas, None, coletas)

    # Hero
    st.html(
        """
        <div class="pt-hero">
          <h1>Acompanhe e economize em hardware</h1>
          <p>Compare preços de GPU, CPU, placa-mãe, memória RAM, SSD, monitores e cadeiras entre lojas brasileiras,
             com histórico de preços e alertas de queda — tudo em um só lugar.</p>
        </div>
        """
    )

    barra_pesquisa()
    st.html(_estatisticas(resumo))
    _painel_coleta(coletas, resumo)

    if metricas.empty:
        st.info("Ainda não há produtos monitorados. Aguarde a primeira coleta automática.")
        return

    # Maiores quedas (7 dias)
    quedas = metricas[metricas["variacao_7d"].notna() & (metricas["variacao_7d"] < 0)]
    quedas = quedas.sort_values("variacao_7d").head(DESTAQUES)
    secao("📉 Maiores quedas (7 dias)", "?pagina=catalogo")
    if quedas.empty:
        st.caption("Sem quedas registradas nos últimos 7 dias (ou dados insuficientes).")
    else:
        st.html(grade_cards_html(quedas, DESTAQUES))

    # Melhores ofertas (no menor preço de verdade: preço variou e está no menor)
    melhores = metricas[
        (metricas["preco_atual"] <= metricas["menor_preco_historico"])
        & (metricas["n_registros"] >= 2)
        & (metricas["max_preco_historico"] > metricas["menor_preco_historico"])
    ]
    melhores = melhores.sort_values("preco_atual").head(DESTAQUES)
    secao("🟢 Melhores ofertas (no menor preço histórico)", "?pagina=catalogo")
    if melhores.empty:
        st.caption("Nenhum produto está no menor preço histórico no momento.")
    else:
        st.html(grade_cards_html(melhores, DESTAQUES))

    # Atualizados recentemente
    recentes = metricas.sort_values("data_varredura", ascending=False).head(DESTAQUES)
    secao("🕒 Atualizados recentemente", "?pagina=catalogo")
    st.html(grade_cards_html(recentes, DESTAQUES))
