"""Gatilho de coleta local (apenas quando o Playwright está instalado).

No Streamlit Cloud (interface publicada) o Playwright não está instalado, então quem
coleta é o agendador (GitHub Actions). Esta função só aparece em execução local.
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

from app.database import BASE_DIR


def coletor_disponivel() -> bool:
    """True quando o Playwright está instalado (instalação do coletor)."""
    try:
        return importlib.util.find_spec("playwright") is not None
    except ImportError:
        return False


def iniciar_coleta() -> tuple[bool, str]:
    """Sobe a coleta do catálogo em um processo separado, sem travar a interface."""
    comando = [sys.executable, "-m", "app.coleta"]
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
