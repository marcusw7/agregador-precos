import sys
from pathlib import Path

# O Streamlit Community Cloud executa ``app/dashboard.py`` adicionando ao ``sys.path``
# apenas a pasta do script (``app/``), e não a raiz do repositório. Sem este ajuste,
# ``from app... import ...`` falha com ``ModuleNotFoundError: No module named 'app'``.
_RAIZ = Path(__file__).resolve().parent.parent
if str(_RAIZ) not in sys.path:
    sys.path.insert(0, str(_RAIZ))

import streamlit as st
from sqlalchemy.exc import SQLAlchemyError

from app.database import Base, engine, usar_postgres
from app.ui import catalogo, home, produto
from app.ui.theme import aplicar_tema, navbar

PAGINAS = ("inicio", "catalogo", "produto")
FAVICON = _RAIZ / "app" / "assets" / "favicon.png"


def _preparar() -> None:
    """Configura a página e aplica o tema. Também garante o esquema do banco."""
    st.set_page_config(
        page_title="PromoTracker",
        page_icon=str(FAVICON),
        layout="wide",
        initial_sidebar_state="auto",
    )
    aplicar_tema()

    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as erro:
        st.error(
            "Não foi possível conectar ao banco de dados. Verifique a variável "
            "`DATABASE_URL` (ou o Secret no Streamlit Cloud) e se o banco aceita "
            f"conexões externas. Detalhe: {type(erro).__name__}"
        )
        st.stop()


def main() -> None:
    _preparar()

    pagina = st.query_params.get("pagina", "catalogo")
    if pagina not in PAGINAS:
        pagina = "catalogo"

    navbar(pagina)

    with st.sidebar:
        st.caption(f"Banco: {'PostgreSQL' if usar_postgres() else 'SQLite local'}")

    if pagina == "inicio":
        home.render()
    elif pagina == "produto":
        produto.render()
    else:
        catalogo.render()


if __name__ == "__main__":
    main()
