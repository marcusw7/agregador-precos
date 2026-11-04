import html
import importlib.util
import math
import subprocess
import sys

import altair as alt
import pandas as pd
import streamlit as st
from sqlalchemy import select

from atributos import ATRIBUTOS_POR_CATEGORIA, TODOS_ATRIBUTOS, extrair_atributos
from categorias import Categoria
from consultas import nome_contem_termo
from database import BASE_DIR, SessionLocal, engine, Base, usar_postgres
from filtros import filtrar, valores_disponiveis
from models import HistoricoPreco, Peca

IMAGEM_PADRAO = "https://placehold.co/400x300/f1f5f9/64748b?text=Sem+foto"
LIMITE_CARDS = 120

ORDENACOES = {
    "preco_asc": "Menor preço",
    "preco_desc": "Maior preço",
    "recentes": "Mais recentes",
}

ESTILO = """
<style>
.card-img {
    width: 100%; height: 190px; object-fit: contain;
    background: #ffffff; border-radius: 10px; margin-bottom: 10px;
}
.card-cat {
    display: inline-block; font-size: 11px; font-weight: 600; letter-spacing: .04em;
    text-transform: uppercase; color: #475569; background: #e2e8f0;
    padding: 3px 8px; border-radius: 999px; margin-bottom: 6px;
}
.card-nome {
    font-size: 15px; font-weight: 600; color: #0f172a; line-height: 1.3;
    height: 40px; overflow: hidden; margin-bottom: 8px;
}
.badge-loja {
    display: inline-block; font-size: 12px; font-weight: 700; color: #ffffff;
    background: linear-gradient(90deg, #f97316, #ea580c);
    padding: 4px 10px; border-radius: 6px; margin-bottom: 10px;
}
.card-preco { font-size: 26px; font-weight: 800; color: #15803d; }
.card-min { font-size: 12px; color: #64748b; margin-bottom: 8px; }
.destaque-min { color: #15803d; font-weight: 700; }
.chip {
    display: inline-block; font-size: 12px; color: #1e293b; background: #e2e8f0;
    border-radius: 999px; padding: 3px 10px; margin: 0 6px 6px 0;
}
</style>
"""


def formatar_brl(valor: float) -> str:
    return f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def coletor_disponivel() -> bool:
    """True quando o Playwright está instalado (instalação do coletor).

    Na interface publicada (sem Playwright), o botão de coleta não aparece: quem coleta
    é o agendador (GitHub Actions).
    """
    try:
        return importlib.util.find_spec("playwright") is not None
    except ImportError:
        return False


def iniciar_coleta(termo: str | None, exato: bool) -> tuple[bool, str]:
    """Sobe a coleta em um processo separado para não bloquear a interface."""
    comando = [sys.executable, "-m", "app.coleta"]
    if termo:
        comando += ["--termo", termo]
        if exato:
            comando += ["--exato"]

    registro = BASE_DIR / "coleta.log"
    try:
        with open(registro, "ab") as saida:
            subprocess.Popen(
                comando,
                cwd=str(BASE_DIR),
                stdout=saida,
                stderr=subprocess.STDOUT,
                close_fds=True,
            )
    except OSError as erro:
        return False, str(erro)
    return True, str(registro)


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
def carregar_historico(peca_id: int) -> pd.DataFrame:
    with SessionLocal() as db:
        registros = db.scalars(
            select(HistoricoPreco)
            .where(HistoricoPreco.peca_id == peca_id)
            .order_by(HistoricoPreco.data_registro)
        ).all()
        return pd.DataFrame(
            [{"data": r.data_registro, "preco": float(r.preco)} for r in registros]
        )


def renderizar_card(linha: pd.Series) -> None:
    imagem = html.escape(linha["imagem_url"] or IMAGEM_PADRAO)
    nome = html.escape(linha["nome"])
    loja = html.escape(linha["loja"])
    categoria = html.escape(linha["categoria"])
    no_minimo = linha["preco_atual"] <= linha["menor_preco_historico"]
    classe_min = "destaque-min" if no_minimo else ""
    rotulo_min = "Menor preço histórico" if no_minimo else "Menor já registrado"

    marca = linha.get("Marca")
    chip = linha.get("Chip") or linha.get("Chipset") or linha.get("Modelo")
    detalhes = " · ".join(html.escape(str(v)) for v in (marca, chip) if isinstance(v, str))
    linha_detalhes = f'<div class="card-min">{detalhes}</div>' if detalhes else ""

    with st.container(border=True):
        st.markdown(
            f"""
            <img class="card-img" src="{imagem}" />
            <span class="card-cat">{categoria}</span>
            <div class="card-nome" title="{nome}">{nome}</div>
            {linha_detalhes}
            <span class="badge-loja">🏪 {loja}</span>
            <div class="card-preco">R$ {formatar_brl(linha['preco_atual'])}</div>
            <div class="card-min {classe_min}">{rotulo_min}: R$ {formatar_brl(linha['menor_preco_historico'])}</div>
            """,
            unsafe_allow_html=True,
        )
        st.link_button("Ir para a Loja ➜", linha["link"], use_container_width=True, type="primary")


def sidebar(todas: pd.DataFrame) -> dict:
    # Mostra no ecrã do Streamlit as colunas reais que o DataFrame recebeu
    st.write("Colunas disponíveis no DataFrame:", todas.columns.tolist())
    
    todas.columns = [str(col).lower() for col in todas.columns]
    
    categorias = [c.value for c in Categoria if c.value in set(todas["categoria"])]
    ...
    extras = sorted(set(todas["categoria"]) - set(categorias))
    opcoes = ["Todas"] + categorias + extras

    with st.sidebar:
        st.title("🔎 Filtros")
        escolha = st.radio("Categoria", opcoes)
        categoria = None if escolha == "Todas" else escolha
        base = todas if categoria is None else todas[todas["categoria"] == categoria]

        lojas_escolhidas = st.multiselect(
            "Loja",
            valores_disponiveis(base, "loja"),
            key=f"loja::{categoria or 'todas'}",
            help="Mostra apenas as lojas que têm produtos nesta categoria.",
        )

        if base.empty:
            faixa = (0.0, 0.0)
        else:
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

        st.divider()
        lojas = ", ".join(sorted(set(todas["loja"])))
        st.caption(f"Lojas: {lojas}. Preços à vista.")
        st.caption(f"Banco: {'PostgreSQL' if usar_postgres() else 'SQLite local'}")

    return {
        "categoria": categoria,
        "lojas": lojas_escolhidas,
        "atributos": filtros_atributos,
        "preco_min": faixa[0],
        "preco_max": faixa[1],
        "somente_minimo": somente_minimo,
        "ordenar": ordenar,
    }


def secao_historico(df: pd.DataFrame) -> None:
    st.subheader("📈 Histórico de preços")
    if df.empty:
        st.info("Nenhum produto corresponde aos filtros.")
        return

    opcoes = {f"{linha['nome'][:90]} · {linha['loja']}": int(linha["id"]) for _, linha in df.iterrows()}
    escolha = st.selectbox("Produto", list(opcoes.keys()))
    historico = carregar_historico(opcoes[escolha])

    if historico.empty:
        st.info("Este produto ainda não tem histórico registrado.")
        return
    if len(historico) == 1:
        st.caption("Ainda há só uma varredura para este produto. O gráfico ganha linhas nas próximas atualizações.")

    grafico = (
        alt.Chart(historico)
        .mark_line(point=alt.OverlayMarkDef(size=70), color="#f97316")
        .encode(
            x=alt.X("data:T", title="Data da varredura", axis=alt.Axis(format="%d/%m %H:%M")),
            y=alt.Y(
                "preco:Q",
                title="Preço à vista (R$)",
                scale=alt.Scale(zero=False),
                axis=alt.Axis(format=",.2f"),
            ),
            tooltip=[
                alt.Tooltip("data:T", title="Data", format="%d/%m/%Y %H:%M"),
                alt.Tooltip("preco:Q", title="Preço (R$)", format=",.2f"),
            ],
        )
        .properties(height=340)
    )
    st.altair_chart(grafico, use_container_width=True)


def secao_pesquisa(todas: pd.DataFrame, termo: str, exato: bool) -> None:
    df = todas[todas["nome"].map(lambda nome: nome_contem_termo(nome, termo, exato))]

    st.subheader(f"🔍 Resultados para “{termo}”")
    modo = "correspondência exata" if exato else "qualquer ordem de palavras"
    st.caption(f"Pesquisa por {modo}, considerando todas as ofertas salvas e sem os filtros laterais.")
    if df.empty:
        st.info(
            "Nenhuma oferta salva para este produto. Rode uma coleta (ou aguarde a próxima) "
            "para trazer ofertas das lojas."
        )
        return

    melhor = df.sort_values("preco_atual").iloc[0]
    col1, col2, col3 = st.columns(3)
    col1.metric("Menor preço", f"R$ {formatar_brl(melhor['preco_atual'])}")
    col2.metric("Loja com menor preço", melhor["loja"])
    col3.metric("Ofertas encontradas", len(df))

    st.markdown("#### Comparação entre lojas")
    tabela = df.sort_values("preco_atual")[
        ["loja", "Marca", "nome", "preco_atual", "menor_preco_historico", "data_varredura", "link"]
    ].rename(
        columns={
            "loja": "Loja",
            "nome": "Produto",
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

    st.markdown("#### Ofertas")
    colunas = st.columns(3)
    for indice, (_, linha) in enumerate(df.sort_values("preco_atual").head(LIMITE_CARDS).iterrows()):
        with colunas[indice % 3]:
            renderizar_card(linha)

    st.divider()
    secao_historico(df)


def main() -> None:
    st.set_page_config(page_title="Agregador de Hardware", page_icon="🖥️", layout="wide")
    st.markdown(ESTILO, unsafe_allow_html=True)
    Base.metadata.create_all(bind=engine)

    todas = carregar_pecas()
    filtros = sidebar(todas)

    st.title("🖥️ Agregador de Preços de Hardware")
    st.caption("Compare preços de GPU, CPU, placa-mãe, memória RAM e SSD entre lojas brasileiras.")

    with st.form("form_pesquisa"):
        st.text_input(
            "Pesquisar produto específico",
            placeholder="Ex.: RTX 4060 Ti, Ryzen 7 7800X3D, SSD NVMe 1TB",
            key="campo_termo",
        )
        st.checkbox(
            "Correspondência exata (“RTX 4060” não mostra “RTX 4060 Ti”)",
            value=True,
            key="campo_exato",
        )
        consultar = st.form_submit_button("🔎 Consultar ofertas salvas", type="primary")

    if consultar:
        st.session_state["termo_aplicado"] = st.session_state.get("campo_termo", "").strip()
        st.session_state["exato_aplicado"] = st.session_state.get("campo_exato", True)

    termo = st.session_state.get("termo_aplicado", "")
    exato = st.session_state.get("exato_aplicado", True)

    if termo:
        if coletor_disponivel():
            if st.button("⬇️ Atualizar preços nas lojas (roda em segundo plano)"):
                iniciou, detalhe = iniciar_coleta(termo, exato)
                if iniciou:
                    st.success(
                        "Coleta iniciada em segundo plano. Ela grava direto no banco, sem "
                        f"bloquear esta tela. Registro: {detalhe}"
                    )
                else:
                    st.error(f"Não foi possível iniciar a coleta: {detalhe}")
        else:
            st.info(
                "A coleta não está disponível nesta instalação (sem Playwright). Neste "
                "ambiente, quem coleta é o agendador configurado no repositório."
            )
        secao_pesquisa(todas, termo, exato)
        return

    df = filtrar(todas, **filtros)
    lojas = df["loja"].nunique() if not df.empty else 0
    col1, col2, col3 = st.columns(3)
    col1.metric("Produtos encontrados", len(df))
    col2.metric("Lojas nos resultados", lojas)
    col3.metric("Menor preço exibido", f"R$ {formatar_brl(df['preco_atual'].min())}" if not df.empty else "—")

    ativos = []
    if filtros["categoria"]:
        ativos.append(filtros["categoria"])
    if filtros["lojas"]:
        ativos.append(f"Loja: {', '.join(filtros['lojas'])}")
    for atributo, escolhidos in filtros["atributos"].items():
        ativos.append(f"{atributo}: {', '.join(escolhidos)}")
    if ativos:
        chips = "".join(f'<span class="chip">{html.escape(item)}</span>' for item in ativos)
        st.markdown(chips, unsafe_allow_html=True)

    st.divider()

    if df.empty:
        st.info("Nenhum produto encontrado com esses filtros. Ajuste a categoria, a marca ou a faixa de preço.")
    else:
        if len(df) > LIMITE_CARDS:
            st.caption(f"Mostrando {LIMITE_CARDS} de {len(df)} produtos. Use os filtros para refinar.")
        colunas = st.columns(3)
        for indice, (_, linha) in enumerate(df.head(LIMITE_CARDS).iterrows()):
            with colunas[indice % 3]:
                renderizar_card(linha)

    st.divider()
    secao_historico(df)


main()
