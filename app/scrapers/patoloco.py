from decimal import Decimal
from urllib.parse import quote_plus, urljoin

from bs4 import Tag

from app.scrapers.base import LojaScraper
from app.scrapers.utils import parse_preco

CATEGORIAS = {
    "GPU": "/produtos/placa-de-video",
    "CPU": "/produtos/processadores",
    "Placa-mãe": "/produtos/placas-mae",
    "Memória RAM": "/produtos/memorias",
}


class PatolocoScraper(LojaScraper):
    nome_loja = "Patoloco"
    base_url = "https://patoloco.com.br"
    seletor_card = "article.product"

    def url_busca(self, termo: str) -> str:
        return f"{self.base_url}/busca/?buscar-por={quote_plus(termo)}"

    def urls_busca(self, termos: list[str], categoria: str) -> list[str]:
        """A busca da Patoloco devolve quase tudo indisponível e sem preço.

        As páginas de categoria listam os produtos à venda, então são usadas
        quando a categoria é conhecida.
        """
        caminho = CATEGORIAS.get(categoria)
        if caminho:
            return [urljoin(self.base_url, caminho)]
        return super().urls_busca(termos, categoria)

    def extrair_link(self, card: Tag) -> str | None:
        elemento = card.select_one(".product-info a[href]") or card.select_one("a[href]")
        return elemento["href"] if elemento is not None else None

    def extrair_titulo(self, card: Tag) -> str | None:
        return self._texto(card, "h3.tit")

    def extrair_preco_avista(self, card: Tag) -> Decimal | None:
        return parse_preco(self._texto(card, ".price-new"))
