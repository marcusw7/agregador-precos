from decimal import Decimal
from urllib.parse import quote_plus

from bs4 import Tag

from app.scrapers.base import LojaScraper
from app.scrapers.utils import parse_preco


class TerabyteScraper(LojaScraper):
    nome_loja = "Terabyte"
    base_url = "https://www.terabyteshop.com.br"
    seletor_card = "div.product-item__box"

    def url_busca(self, termo: str) -> str:
        return f"{self.base_url}/busca?str={quote_plus(termo)}"

    def extrair_link(self, card: Tag) -> str | None:
        elemento = card.select_one("a.product-item__name[href]")
        return elemento["href"] if elemento is not None else None

    def extrair_titulo(self, card: Tag) -> str | None:
        return self._texto(card, "a.product-item__name h2")

    def extrair_preco_avista(self, card: Tag) -> Decimal | None:
        return parse_preco(self._texto(card, ".product-item__new-price span"))
