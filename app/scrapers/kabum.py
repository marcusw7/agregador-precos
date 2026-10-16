from decimal import Decimal

from bs4 import Tag

from app.scrapers.base import LojaScraper
from app.scrapers.utils import parse_preco, slug_url


class KabumScraper(LojaScraper):
    nome_loja = "KaBuM!"
    base_url = "https://www.kabum.com.br"
    seletor_card = 'a[href*="/produto/"]'

    def url_busca(self, termo: str) -> str:
        return f"{self.base_url}/busca/{slug_url(termo)}"

    def extrair_titulo(self, card: Tag) -> str | None:
        elemento = card.select_one("span.line-clamp-2")
        if elemento is not None:
            return elemento.get_text(" ", strip=True) or None
        imagem = card.select_one("img[alt]")
        if imagem is None:
            return None
        return imagem["alt"].strip() or None

    def extrair_preco_avista(self, card: Tag) -> Decimal | None:
        for elemento in card.select("span.text-base.font-semibold"):
            preco = parse_preco(elemento.get_text(" ", strip=True))
            if preco is not None:
                return preco
        return None
