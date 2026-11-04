"""API de leitura e disparo de coleta.

Leitura (``GET /pecas*``) é pública e não expõe segredo algum.
Os endpoints de coleta (``/atualizacoes*``) são administrativos e exigem o token
definido na variável de ambiente ``ADMIN_TOKEN``.

O módulo **não** importa o coletor em tempo de execução: o import é feito dentro do
handler, para que a API suba mesmo sem Playwright instalado.
"""

import logging
import os
import secrets
from contextlib import asynccontextmanager
from decimal import Decimal
from typing import Annotated, Literal

from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Query
from sqlalchemy.orm import Session

from import models
from categorias import Categoria
from consultas import buscar_pecas
from database import Base, engine, get_db, usar_postgres
from schemas import HistoricoPrecoOut, PecaOut
from servicos import (
    atualizacao_em_andamento,
    iniciar_atualizacao,
    liberar_atualizacao,
    obter_ultima_atualizacao,
)

log = logging.getLogger(__name__)

VARIAVEL_TOKEN = "ADMIN_TOKEN"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    log.info("Banco em uso: %s", "PostgreSQL" if usar_postgres() else "SQLite local")
    yield


app = FastAPI(title="Agregador de Preços de Hardware", lifespan=lifespan)


def token_configurado() -> str:
    return os.environ.get(VARIAVEL_TOKEN, "").strip()


def exigir_admin(
    authorization: Annotated[str | None, Header()] = None,
    x_admin_token: Annotated[str | None, Header()] = None,
) -> None:
    """Autoriza endpoints administrativos comparando o token em tempo constante."""
    esperado = token_configurado()
    if not esperado:
        raise HTTPException(
            status_code=503,
            detail=(
                "Coleta administrativa desabilitada: defina a variável de ambiente "
                f"{VARIAVEL_TOKEN} para habilitar este endpoint."
            ),
        )

    recebido = ""
    if authorization and authorization.lower().startswith("bearer "):
        recebido = authorization[len("bearer ") :].strip()
    elif x_admin_token:
        recebido = x_admin_token.strip()

    if not recebido or not secrets.compare_digest(recebido, esperado):
        raise HTTPException(status_code=401, detail="Não autorizado")
    # Nunca registramos o conteúdo do token.
    log.info("Endpoint administrativo autorizado.")


def _rodar_coleta() -> None:
    """Executa a coleta já reservada e libera a trava ao final."""
    try:
        from app.coleta import atualizar_precos  # import tardio: exige Playwright
    except ImportError:
        log.error("Coletor não instalado neste ambiente; coleta não executada.")
        liberar_atualizacao()
        return
    try:
        atualizar_precos()
    except Exception:
        log.exception("Falha na atualização de preços")
    finally:
        liberar_atualizacao()


@app.get("/")
def raiz():
    return {
        "status": "ok",
        "banco": "postgresql" if usar_postgres() else "sqlite",
        "coleta_administrativa": bool(token_configurado()),
    }


@app.get("/pecas", response_model=list[PecaOut])
def listar_pecas(
    categoria: Categoria | None = None,
    loja: str | None = None,
    preco_min: Decimal | None = Query(None, ge=0),
    preco_max: Decimal | None = Query(None, ge=0),
    somente_minimo_historico: bool = False,
    ordenar: Literal["preco_asc", "preco_desc", "recentes"] = "preco_asc",
    pagina: int = Query(1, ge=1),
    tamanho: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return buscar_pecas(
        db,
        categoria=categoria,
        loja=loja,
        preco_min=preco_min,
        preco_max=preco_max,
        somente_minimo_historico=somente_minimo_historico,
        ordenar=ordenar,
        pagina=pagina,
        tamanho=tamanho,
    )


@app.get("/pecas/{peca_id}", response_model=PecaOut)
def obter_peca(peca_id: int, db: Session = Depends(get_db)):
    peca = db.get(models.Peca, peca_id)
    if peca is None:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    return peca


@app.get("/pecas/{peca_id}/historico", response_model=list[HistoricoPrecoOut])
def historico_peca(peca_id: int, db: Session = Depends(get_db)):
    peca = db.get(models.Peca, peca_id)
    if peca is None:
        raise HTTPException(status_code=404, detail="Peça não encontrada")
    return peca.historico


@app.post("/atualizacoes", status_code=202, dependencies=[Depends(exigir_admin)])
def disparar_atualizacao(background_tasks: BackgroundTasks):
    if not iniciar_atualizacao():
        raise HTTPException(status_code=409, detail="Já existe uma atualização em andamento")
    background_tasks.add_task(_rodar_coleta)
    return {"status": "iniciada"}


@app.get("/atualizacoes/ultima", dependencies=[Depends(exigir_admin)])
def status_atualizacao():
    return {
        "em_andamento": atualizacao_em_andamento(),
        "ultima": obter_ultima_atualizacao(),
    }
