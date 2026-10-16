"""Camada de acesso ao banco.

O banco é escolhido pela variável de ambiente ``DATABASE_URL``:

* se ela **não** estiver definida, usa o SQLite local (``precos.db`` na raiz do projeto),
  mantendo o funcionamento atual no Windows;
* se estiver definida com uma URL PostgreSQL (Neon, Supabase, etc.), usa esse banco.

Nenhuma credencial fica no código: a URL vem sempre do ambiente.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

VARIAVEL_URL = "DATABASE_URL"

BASE_DIR = Path(__file__).resolve().parent.parent
SQLITE_PADRAO = f"sqlite:///{BASE_DIR / 'precos.db'}"

DIALETO_POSTGRES = "postgresql+psycopg"


def normalizar_url(url: str) -> str:
    """Aceita as URLs que os provedores costumam entregar e escolhe o driver psycopg (v3).

    ``postgres://...`` e ``postgresql://...`` viram ``postgresql+psycopg://...``.
    URLs já explícitas (``sqlite://``, ``postgresql+psycopg://``) são mantidas.
    """
    limpa = (url or "").strip()
    if limpa.startswith("postgres://"):
        return DIALETO_POSTGRES + "://" + limpa[len("postgres://") :]
    if limpa.startswith("postgresql://"):
        return DIALETO_POSTGRES + "://" + limpa[len("postgresql://") :]
    return limpa


def mascarar_url(url: str) -> str:
    """Devolve a URL sem a senha, para poder aparecer em log ou em tela com segurança."""
    if not url:
        return ""
    try:
        partes = urlsplit(url)
    except ValueError:
        return "<url inválida>"
    if not partes.password:
        return url
    host = partes.hostname or ""
    porta = f":{partes.port}" if partes.port else ""
    usuario = partes.username or ""
    return urlunsplit(
        (partes.scheme, f"{usuario}:***@{host}{porta}", partes.path, partes.query, partes.fragment)
    )


def _valor_secreto(nome: str) -> str:
    """Lê um segredo do ``st.secrets`` quando o Streamlit estiver disponível.

    O Streamlit Community Cloud publica segredos em ``st.secrets`` (não em variáveis de
    ambiente). O import é feito dentro da função justamente para que o coletor — que não
    instala Streamlit — continue funcionando apenas com variáveis de ambiente.
    """
    try:
        import streamlit as st  # import local de propósito
    except ImportError:
        return ""
    try:
        valor = st.secrets.get(nome, "")
    except Exception:  # noqa: BLE001 — sem secrets.toml, entre outros
        return ""
    return str(valor or "")


def url_do_ambiente() -> str:
    """URL configurada no ambiente ou nos secrets. Vazio significa 'usar o SQLite local'."""
    definida = os.environ.get(VARIAVEL_URL, "").strip() or _valor_secreto(VARIAVEL_URL).strip()
    return normalizar_url(definida) if definida else ""


def usar_postgres() -> bool:
    return URL_BANCO.startswith("postgresql")


def usar_sqlite() -> bool:
    return URL_BANCO.startswith("sqlite")


def criar_engine(url: str):
    """Cria o engine adequado ao dialeto, sem abrir conexão."""
    if url.startswith("sqlite"):
        return create_engine(url, connect_args={"check_same_thread": False})
    if url.startswith("postgresql"):
        # pool_pre_ping evita erros com conexões ociosas encerradas por provedores gerenciados.
        return create_engine(url, pool_pre_ping=True)
    return create_engine(url)


URL_BANCO = url_do_ambiente() or SQLITE_PADRAO

engine = criar_engine(URL_BANCO)
SessionLocal = sessionmaker(bind=engine, autoflush=False)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
