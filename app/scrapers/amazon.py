from decimal import Decimal
from urllib.parse import quote_plus

from bs4 import Tag

from app.scrapers.base import LojaScraper
from app.scrapers.utils import parse_preco


class AmazonScraper(LojaScraper):
    nome_loja = "Amazon"
    base_url = "https://www.amazon.com.br"
    seletor_card = 'div[data-component-type="s-search-result"]'

    def url_busca(self, termo: str) -> str:
        return f"{self.base_url}/s?k={quote_plus(termo)}"

    def extrair_link(self, card: Tag) -> str | None:
        elemento = card.select_one('a[href*="/dp/"]')
        return elemento["href"] if elemento is not None else None

    def extrair_titulo(self, card: Tag) -> str | None:
        return self._texto(card, "h2")

    def extrair_preco_avista(self, card: Tag) -> Decimal | None:
        return parse_preco(self._texto(card, ".a-price .a-offscreen"))
