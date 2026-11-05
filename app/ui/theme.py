"""Identidade visual do PromoTracker.

Centraliza paleta, tipografia, logotipo (SVG) e o CSS global. As páginas importam
daqui para manter a aparência consistente.
"""

from __future__ import annotations

import html
from datetime import datetime

import streamlit as st

# --------------------------------------------------------------------------- #
# Paleta
# --------------------------------------------------------------------------- #
CORES = {
    "fundo": "#0e1117",
    "superficie": "#161b24",
    "superficie_2": "#1c2330",
    "borda": "#262e3e",
    "texto": "#e6e9ef",
    "texto_mudo": "#94a3b8",
    "primaria": "#6366f1",
    "violeta": "#8b5cf6",
    "verde": "#22c55e",
    "vermelho": "#f87171",
    "ambar": "#fbbf24",
}

COR_PRIMARIA = CORES["primaria"]
COR_VERDE = CORES["verde"]
COR_VERMELHO = CORES["vermelho"]
COR_AMBAR = CORES["ambar"]
COR_TEXTO = CORES["texto"]
COR_MUDO = CORES["texto_mudo"]

LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 248 40" width="248" height="40" role="img" aria-label="PromoTracker">
  <defs>
    <linearGradient id="ptgrad" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#6366f1"/>
      <stop offset="1" stop-color="#8b5cf6"/>
    </linearGradient>
  </defs>
  <rect x="0" y="0" width="40" height="40" rx="11" fill="url(#ptgrad)"/>
  <path d="M9 27 L16 20 L22 24 L31 13" stroke="#ffffff" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>
  <circle cx="31" cy="13" r="2.6" fill="#ffffff"/>
  <text x="50" y="27.5" font-family="Inter, Segoe UI, sans-serif" font-size="21" font-weight="800" fill="#e6e9ef" letter-spacing="-0.3">Promo<tspan fill="#8b5cf6">Tracker</tspan></text>
</svg>
"""

ESTILO = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

:root {
  --pt-bg: #0e1117;
  --pt-surface: #161b24;
  --pt-surface2: #1c2330;
  --pt-border: #262e3e;
  --pt-text: #e6e9ef;
  --pt-muted: #94a3b8;
  --pt-primary: #6366f1;
  --pt-violet: #8b5cf6;
  --pt-green: #22c55e;
  --pt-red: #f87171;
  --pt-amber: #fbbf24;
}

html, body, [class*="css"], .stApp {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
  color: var(--pt-text);
}

.stApp {
  background:
    radial-gradient(1100px 500px at 15% -10%, rgba(99, 102, 241, 0.14), transparent 60%),
    radial-gradient(900px 420px at 100% 0%, rgba(139, 92, 246, 0.12), transparent 55%),
    var(--pt-bg);
}

#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
header[data-testid="stHeader"] { background: transparent; }

/* Sidebar */
[data-testid="stSidebar"] {
  background: #10141c;
  border-right: 1px solid var(--pt-border);
}

/* Cabeçalho / marca */
.pt-navbar {
  display: flex; align-items: center; gap: 26px;
  padding: 8px 4px 18px 4px;
  border-bottom: 1px solid var(--pt-border);
  margin-bottom: 20px;
  flex-wrap: wrap;
}
.pt-brand { display: flex; align-items: center; gap: 10px; text-decoration: none; }
.pt-nav-links { display: flex; gap: 6px; margin-left: auto; flex-wrap: wrap; }
.pt-nav-link {
  display: inline-block; padding: 8px 16px; border-radius: 10px;
  color: var(--pt-muted); text-decoration: none; font-weight: 600; font-size: 14px;
  transition: all .15s ease;
}
.pt-nav-link:hover { color: var(--pt-text); background: var(--pt-surface2); }
.pt-nav-link.active { color: #fff; background: var(--pt-surface2); box-shadow: inset 0 0 0 1px var(--pt-border); }

/* Hero */
.pt-hero { margin: 6px 0 24px 0; }
.pt-hero h1 { font-size: 34px; font-weight: 800; letter-spacing: -0.5px; margin: 0 0 8px 0; }
.pt-hero p { color: var(--pt-muted); font-size: 16px; margin: 0; max-width: 720px; }

/* Estatísticas */
.pt-stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 26px; }
.pt-stat {
  background: var(--pt-surface); border: 1px solid var(--pt-border); border-radius: 14px; padding: 18px;
}
.pt-stat .pt-stat-label { color: var(--pt-muted); font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
.pt-stat .pt-stat-value { font-size: 26px; font-weight: 800; margin-top: 4px; }
.pt-stat .pt-stat-sub { color: var(--pt-muted); font-size: 12px; margin-top: 2px; }

/* Grade de cards */
.pt-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(270px, 1fr)); gap: 16px; }

/* Card de produto */
.pt-card {
  display: flex; flex-direction: column; gap: 8px;
  background: var(--pt-surface); border: 1px solid var(--pt-border); border-radius: 14px;
  padding: 14px; transition: border-color .15s ease, transform .15s ease;
  text-decoration: none; color: var(--pt-text);
}
.pt-card:hover { border-color: var(--pt-primary); transform: translateY(-2px); }
.pt-card-media { display: flex; align-items: center; justify-content: center; height: 170px; margin-bottom: 6px; }
.pt-card-media img { max-width: 100%; max-height: 170px; object-fit: contain; border-radius: 8px; }
.pt-card-title {
  font-size: 14px; font-weight: 600; line-height: 1.35; color: var(--pt-text);
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
  min-height: 38px;
}
.pt-card-meta { font-size: 12px; color: var(--pt-muted); }
.pt-card-price-row { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; margin-top: 2px; }
.pt-card-price { font-size: 22px; font-weight: 800; color: var(--pt-green); }
.pt-card-min { font-size: 12px; color: var(--pt-muted); }
.pt-card-foot { display: flex; align-items: center; justify-content: space-between; gap: 8px; margin-top: 2px; }

/* Badges */
.pt-badge {
  display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: .02em;
  padding: 3px 9px; border-radius: 999px; line-height: 1.4; white-space: nowrap;
}
.pt-badge-cat { color: #c7d2fe; background: rgba(99, 102, 241, 0.16); }
.pt-badge-loja { color: #fff; background: linear-gradient(90deg, #f97316, #ea580c); }
.pt-badge-verde { color: #86efac; background: rgba(34, 197, 94, 0.14); }
.pt-badge-vermelho { color: #fca5a5; background: rgba(248, 113, 113, 0.14); }
.pt-badge-ambar { color: #fcd34d; background: rgba(251, 191, 36, 0.14); }
.pt-badge-mudo { color: var(--pt-muted); background: rgba(148, 163, 184, 0.12); }

/* Botão */
.pt-btn {
  display: inline-flex; align-items: center; justify-content: center; gap: 6px;
  background: var(--pt-surface2); color: var(--pt-text); border: 1px solid var(--pt-border);
  padding: 8px 14px; border-radius: 10px; font-size: 13px; font-weight: 600; text-decoration: none;
  transition: all .15s ease;
}
.pt-btn:hover { border-color: var(--pt-primary); color: #fff; }
.pt-btn-primario { background: linear-gradient(135deg, #6366f1, #8b5cf6); color: #fff; border: none; }
.pt-btn-primario:hover { filter: brightness(1.08); color: #fff; }

/* Título de seção */
.pt-section { margin: 28px 0 12px 0; display: flex; align-items: baseline; justify-content: space-between; }
.pt-section h2 { font-size: 20px; font-weight: 800; letter-spacing: -0.3px; margin: 0; }
.pt-section a { color: var(--pt-muted); font-size: 13px; text-decoration: none; }
.pt-section a:hover { color: var(--pt-primary); }

/* Painel de produto */
.pt-produto { display: grid; grid-template-columns: 340px 1fr; gap: 26px; }
.pt-produto-img { background: var(--pt-surface); border: 1px solid var(--pt-border); border-radius: 16px; padding: 22px; display: flex; align-items: center; justify-content: center; }
.pt-produto-img img { max-width: 100%; max-height: 340px; object-fit: contain; }
.pt-spec { display: flex; flex-wrap: wrap; gap: 8px; margin: 12px 0; }
.pt-kv { display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid var(--pt-border); font-size: 14px; }
.pt-kv .pt-kv-k { color: var(--pt-muted); }
.pt-kv .pt-kv-v { font-weight: 700; }

/* Preço grande */
.pt-price-hero { font-size: 42px; font-weight: 800; color: var(--pt-green); line-height: 1; }

/* Responsivo */
@media (max-width: 820px) {
  .pt-produto { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .pt-hero h1 { font-size: 26px; }
  div[data-testid="stHorizontalBlock"] { flex-wrap: wrap; }
  div[data-testid="stHorizontalBlock"] > div[data-testid="stColumn"] {
    flex: 1 1 100% !important; width: 100% !important; min-width: 100% !important;
  }
}
"""


def aplicar_tema() -> None:
    """Aplica o CSS global. Chame uma única vez, logo após set_page_config."""
    st.markdown(f"<style>{ESTILO}</style>", unsafe_allow_html=True)


def logotipo() -> str:
    """HTML do logotipo (SVG inline)."""
    return LOGO_SVG


def navbar(pagina_ativa: str) -> None:
    """Barra de navegação superior com a marca e links (via query param)."""
    links = [
        ("inicio", "Início"),
        ("catalogo", "Catálogo"),
    ]
    itens = "".join(
        f'<a class="pt-nav-link{" active" if chave == pagina_ativa else ""}" href="?pagina={chave}">{rotulo}</a>'
        for chave, rotulo in links
    )
    st.markdown(
        f"""
        <div class="pt-navbar">
          <a class="pt-brand" href="?pagina=inicio">{LOGO_SVG}</a>
          <div class="pt-nav-links">{itens}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def formatar_brl(valor: float | None) -> str:
    """Formata um valor como moeda brasileira (1.234,56)."""
    if valor is None:
        return "—"
    return f"{float(valor):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def formatar_pct(valor: float | None, casas: int = 1) -> str:
    """Formata uma variação percentual (ex.: -5,2%)."""
    if valor is None:
        return "—"
    return f"{valor:+,.{casas}f}".replace(".", ",") + "%"


def formatar_data(data: datetime | None) -> str:
    if data is None:
        return "—"
    return data.strftime("%d/%m/%Y %H:%M")


def badge_variacao(variacao: float | None) -> str:
    """Badge de variação percentual. Retorna '' quando não há dado suficiente."""
    if variacao is None:
        return ""
    if variacao < -0.05:
        return f'<span class="pt-badge pt-badge-verde">▼ {formatar_pct(variacao)} (7d)</span>'
    if variacao > 0.05:
        return f'<span class="pt-badge pt-badge-vermelho">▲ {formatar_pct(variacao)} (7d)</span>'
    return f'<span class="pt-badge pt-badge-mudo">= {formatar_pct(variacao)} (7d)</span>'


def esc(texto: object) -> str:
    """Escape de HTML para dados vindos do banco."""
    return html.escape("" if texto is None else str(texto))
