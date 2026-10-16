import logging

from playwright.sync_api import sync_playwright

from app.scrapers.amazon import AmazonScraper
from app.scrapers.base import BloqueioError, ItemProduto, LojaScraper
from app.scrapers.catalogo import CATALOGO
from app.scrapers.kabum import KabumScraper
from app.scrapers.patoloco import PatolocoScraper
from app.scrapers.pichau import PichauScraper
from app.scrapers.politica import opcoes_contexto, pausa_aleatoria
from app.scrapers.terabyte import TerabyteScraper

log = logging.getLogger(__name__)

LOJAS: list[LojaScraper] = [
    KabumScraper(),
    PichauScraper(),
    TerabyteScraper(),
    PatolocoScraper(),
    AmazonScraper(),
]


def coletar(
    catalogo: dict[str, list[str]] | None = None,
    lojas: list[LojaScraper] | None = None,
) -> list[ItemProduto]:
    catalogo = CATALOGO if catalogo is None else catalogo
    lojas = LOJAS if lojas is None else lojas
    resultados: list[ItemProduto] = []

    with sync_playwright() as p:
        navegador = p.chromium.launch(headless=True)
        contexto = navegador.new_context(**opcoes_contexto(navegador))
        pagina = contexto.new_page()
        try:
            for loja in lojas:
                bloqueada = False
                for categoria, termos in catalogo.items():
                    if bloqueada:
                        break
                    for url in loja.urls_busca(termos, categoria):
                        try:
                            itens = loja.buscar(pagina, url)
                        except BloqueioError:
                            log.error(
                                "%s bloqueou as requisições; coleta desta loja interrompida",
                                loja.nome_loja,
                            )
                            bloqueada = True
                            break
                        except Exception:
                            log.exception("%s: falha inesperada em %r", loja.nome_loja, url)
                            continue
                        log.info("%s | %s | %s: %d itens", loja.nome_loja, categoria, url, len(itens))
                        resultados.extend(itens)
                        pausa_aleatoria()
        finally:
            navegador.close()

    return resultados
