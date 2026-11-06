"""Coleta de preços (usa Playwright).

Este é o único módulo que precisa de navegador. Ele pode ser executado:

* pela interface, como **processo separado** (``python -m app.coleta ...``);
* pela API, em segundo plano;
* por um agendador (GitHub Actions), com ``python -m app.coleta``.

A interface **não** importa este módulo em tempo de execução.
"""

import argparse
import logging
import sys
from datetime import datetime

from app.consultas import nome_contem_termo
from app.database import Base, URL_BANCO, engine, mascarar_url, usar_postgres
from app.scrapers.catalogo import CATALOGO
from app.scrapers.coletor import coletar
from app.servicos import (
    abrir_sessao,
    iniciar_atualizacao,
    liberar_atualizacao,
    registrar_coleta,
    registrar_ultima_atualizacao,
    salvar_itens,
)

log = logging.getLogger("app.coleta")


def _resumo(inicio: datetime, itens, gravacao: dict) -> dict:
    return {
        "iniciada_em": inicio,
        "terminada_em": datetime.now(),
        "coletados": len(itens),
        **gravacao,
    }


def garantir_esquema() -> None:
    """Cria as tabelas quando ainda não existem.

    Necessário porque o coletor pode ser o primeiro processo a tocar um banco novo
    (PostgreSQL recém-criado no Neon/Supabase, por exemplo).
    """
    Base.metadata.create_all(engine)


def _registrar_erro(inicio: datetime, erro: Exception, termo: str | None = None) -> None:
    """Registra uma falha de coleta sem mascarar a exceção original."""
    try:
        with abrir_sessao() as db:
            registrar_coleta(
                db,
                iniciada_em=inicio,
                terminada_em=datetime.now(),
                status="erro",
                termo=termo,
                erro=f"{type(erro).__name__}: {erro}",
            )
    except Exception:  # noqa: BLE001 — o registro não pode esconder o erro real
        log.exception("Não foi possível registrar a falha da coleta")


def _resumo_falhas(falhas: dict[str, str]) -> str:
    """Resume as lojas que falharam para registro na coluna de erro."""
    return "Lojas com falha: " + ", ".join(
        f"{loja} ({motivo})" for loja, motivo in falhas.items()
    )


def atualizar_precos() -> dict:
    """Varre o catálogo completo e grava os preços."""
    garantir_esquema()
    inicio = datetime.now()
    itens: list = []
    gravacao: dict = {}
    falhas: dict[str, str] = {}
    try:
        itens = coletar(falhas=falhas)
        status = "parcial" if falhas else "ok"
        erro = _resumo_falhas(falhas) if falhas else None
        with abrir_sessao() as db:
            gravacao = salvar_itens(db, itens)
            registrar_coleta(
                db,
                iniciada_em=inicio,
                terminada_em=datetime.now(),
                status=status,
                coletados=len(itens),
                novas=gravacao["novas"],
                atualizadas=gravacao["atualizadas"],
                sem_preco=gravacao["sem_preco"],
                erro=erro,
            )
    except Exception as erro:  # noqa: BLE001 — registra e propaga
        _registrar_erro(inicio, erro)
        raise
    resumo = registrar_ultima_atualizacao(_resumo(inicio, itens, gravacao))
    log.info("Coleta do catálogo concluída: %s", resumo)
    return resumo


def pesquisar_produto(termo: str, exato: bool = False) -> dict:
    """Consulta as lojas por um produto específico e grava as ofertas encontradas."""
    termo = termo.strip()
    if not termo:
        raise ValueError("Informe o nome do produto")
    garantir_esquema()
    inicio = datetime.now()
    itens: list = []
    gravacao: dict = {}
    descartados = 0
    falhas: dict[str, str] = {}
    try:
        coletados = coletar(catalogo={"Pesquisa": [termo]}, falhas=falhas)
        itens = [item for item in coletados if nome_contem_termo(item.titulo, termo, exato)]
        descartados = len(coletados) - len(itens)
        status = "parcial" if falhas else "ok"
        erro = _resumo_falhas(falhas) if falhas else None
        with abrir_sessao() as db:
            gravacao = salvar_itens(db, itens)
            registrar_coleta(
                db,
                iniciada_em=inicio,
                terminada_em=datetime.now(),
                status=status,
                termo=termo,
                coletados=len(itens),
                novas=gravacao["novas"],
                atualizadas=gravacao["atualizadas"],
                sem_preco=gravacao["sem_preco"],
                descartados=descartados,
                erro=erro,
            )
    except Exception as erro:  # noqa: BLE001 — registra e propaga
        _registrar_erro(inicio, erro, termo=termo)
        raise
    resumo = _resumo(inicio, itens, gravacao)
    resumo.update({"termo": termo, "descartados": descartados})
    log.info("Coleta por termo concluída: %s", resumo)
    return resumo


def executar_atualizacao() -> dict | None:
    """Roda a coleta do catálogo respeitando a trava (uma por processo)."""
    if not iniciar_atualizacao():
        log.warning("Já existe uma coleta em andamento neste processo; ignorando.")
        return None
    try:
        return atualizar_precos()
    except Exception:
        log.exception("Falha na coleta de preços")
        raise
    finally:
        liberar_atualizacao()


def _montar_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m app.coleta",
        description="Coleta preços das lojas e grava no banco configurado em DATABASE_URL.",
    )
    parser.add_argument("--termo", help="coleta apenas este produto (ex.: 'RTX 4060')")
    parser.add_argument(
        "--exato",
        action="store_true",
        help="com --termo, exige correspondência exata ('RTX 4060' não traz 'RTX 4060 Ti')",
    )
    parser.add_argument("--listar", action="store_true", help="mostra o catálogo e encerra")
    return parser


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    args = _montar_parser().parse_args(argv)

    if args.listar:
        for categoria, termos in CATALOGO.items():
            print(f"{categoria}: {', '.join(termos)}")
        return 0

    log.info(
        "Banco em uso: %s",
        "PostgreSQL" if usar_postgres() else "SQLite local",
    )
    log.info("Destino: %s", mascarar_url(URL_BANCO))

    try:
        if args.termo:
            resumo = pesquisar_produto(args.termo, args.exato)
        else:
            resumo = executar_atualizacao()
            if resumo is None:
                print("Havia uma coleta em andamento; nada foi executado.")
                return 1
    except Exception as erro:  # noqa: BLE001 — queremos código de saída e mensagem curta
        log.error("Coleta falhou: %s", type(erro).__name__)
        return 1

    print(resumo)
    return 0


if __name__ == "__main__":
    sys.exit(main())
