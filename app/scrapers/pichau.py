from decimal import Decimal
from urllib.parse import quote_plus

from bs4 import Tag

from app.scrapers.base import LojaScraper
from app.scrapers.utils import parse_preco


class PichauScraper(LojaScraper):
    nome_loja = "Pichau"
    base_url = "https://www.pichau.com.br"
    seletor_card = "a[href]:has(h2)"

    def url_busca(self, termo: str) -> str:
        return f"{self.base_url}/search?q={quote_plus(termo)}"

    def extrair_titulo(self, card: Tag) -> str | None:
        return self._texto(card, "h2")

    def extrair_preco_avista(self, card: Tag) -> Decimal | None:
        return parse_preco(self._texto(card, '[class*="price_vista"]'))
