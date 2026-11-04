from decimal import Decimal
from typing import Literal

from sqlalchemy import select
from sqlalchemy.orm import Session

from categorias import Categoria
from models import Peca
from scrapers.normalizacao import chave_comparacao

ORDENACOES = {
    "preco_asc": Peca.preco_atual.asc(),
    "preco_desc": Peca.preco_atual.desc(),
    "recentes": Peca.data_varredura.desc(),
}


SUFIXOS_DE_VARIANTE = {"ti", "super", "xt", "xtx"}


def _e_sufixo_de_variante(token: str) -> bool:
    return token in SUFIXOS_DE_VARIANTE or (len(token) == 1 and token.isalpha())


def nome_contem_termo(nome: str, termo: str, exato: bool = False) -> bool:
    """Verifica se o nome corresponde ao termo, ignorando caixa e acentos.

    Modo normal: todas as palavras do termo aparecem no nome, em qualquer ordem.
    Modo exato: as palavras aparecem em sequência e não são seguidas de um sufixo de
    variante (Ti, Super, XT, ou uma letra como F/X), para que "RTX 4060" não traga
    "RTX 4060 Ti" nem "Ryzen 5 7600X" traga "Ryzen 5 7600".
    """
    tokens_nome = chave_comparacao(nome).split()
    tokens_termo = chave_comparacao(termo).split()
    if not tokens_termo:
        return False
    if not exato:
        return set(tokens_termo) <= set(tokens_nome)

    tamanho = len(tokens_termo)
    for inicio in range(len(tokens_nome) - tamanho + 1):
        if tokens_nome[inicio:inicio + tamanho] != tokens_termo:
            continue
        proximo = tokens_nome[inicio + tamanho] if inicio + tamanho < len(tokens_nome) else None
        if proximo is None or not _e_sufixo_de_variante(proximo):
            return True
    return False


def buscar_pecas(
    db: Session,
    categoria: Categoria | None = None,
    loja: str | None = None,
    preco_min: Decimal | None = None,
    preco_max: Decimal | None = None,
    somente_minimo_historico: bool = False,
    ordenar: Literal["preco_asc", "preco_desc", "recentes"] = "preco_asc",
    pagina: int = 1,
    tamanho: int = 50,
) -> list[Peca]:
    query = select(Peca)
    if categoria is not None:
        query = query.where(Peca.categoria == categoria.value)
    if loja:
        query = query.where(Peca.loja == loja)
    if preco_min is not None:
        query = query.where(Peca.preco_atual >= preco_min)
    if preco_max is not None:
        query = query.where(Peca.preco_atual <= preco_max)
    if somente_minimo_historico:
        query = query.where(Peca.preco_atual <= Peca.menor_preco_historico)

    query = (
        query.order_by(ORDENACOES[ordenar], Peca.id)
        .offset((pagina - 1) * tamanho)
        .limit(tamanho)
    )
    return list(db.scalars(query))
