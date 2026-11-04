"""Serviços de banco (sem Playwright).

Este módulo é importado pela interface (Streamlit) e pela API. Por isso ele **não**
importa nada de ``app.coleta`` nem de ``app.scrapers.coletor`` — assim a interface
roda sem Playwright/Chromium instalados.
"""

import logging
import threading
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import select
from sqlalchemy.orm import Session

from database import SessionLocal
from models import HistoricoPreco, Peca
from scrapers.normalizacao import normalizar_titulo

if TYPE_CHECKING:  # apenas para tipagem: não importa Playwright em tempo de execução
    from scrapers.base import ItemProduto

log = logging.getLogger(__name__)

_trava = threading.Lock()
_ultima_atualizacao: dict | None = None


def salvar_itens(db: Session, itens: "list[ItemProduto]") -> dict:
    """Grava/atualiza ofertas e acrescenta um registro de histórico por oferta."""
    agora = datetime.now()
    por_link = {item.link: item for item in itens}
    novas = atualizadas = sem_preco = 0

    for item in por_link.values():
        if item.preco_avista is None:
            sem_preco += 1
            continue

        peca = db.scalar(select(Peca).where(Peca.link == item.link))
        if peca is None:
            peca = Peca(
                nome=normalizar_titulo(item.titulo),
                categoria=item.categoria,
                preco_atual=item.preco_avista,
                menor_preco_historico=item.preco_avista,
                loja=item.loja,
                link=item.link,
                imagem_url=item.imagem_url,
                data_varredura=agora,
            )
            db.add(peca)
            novas += 1
        else:
            peca.nome = normalizar_titulo(item.titulo)
            peca.categoria = item.categoria
            peca.preco_atual = item.preco_avista
            peca.menor_preco_historico = min(peca.menor_preco_historico, item.preco_avista)
            peca.loja = item.loja
            peca.imagem_url = item.imagem_url or peca.imagem_url
            peca.data_varredura = agora
            atualizadas += 1

        peca.historico.append(HistoricoPreco(preco=item.preco_avista, data_registro=agora))

    db.commit()
    return {"novas": novas, "atualizadas": atualizadas, "sem_preco": sem_preco}


def abrir_sessao() -> Session:
    """Sessão nova, para quem precisa gravar sem passar pela injeção do FastAPI."""
    return SessionLocal()


def registrar_ultima_atualizacao(resumo: dict) -> dict:
    global _ultima_atualizacao
    _ultima_atualizacao = resumo
    return resumo


def iniciar_atualizacao() -> bool:
    """Reserva a atualização. Retorna False se já houver uma em andamento neste processo."""
    return _trava.acquire(blocking=False)


def liberar_atualizacao() -> None:
    if _trava.locked():
        _trava.release()


def atualizacao_em_andamento() -> bool:
    return _trava.locked()


def obter_ultima_atualizacao() -> dict | None:
    return _ultima_atualizacao
