import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag
from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Page
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from app.scrapers.classificador import classificar_categoria
from app.scrapers.utils import parse_parcelamento

log = logging.getLogger(__name__)

from app.scrapers.politica import espera_renderizacao_ms, pausa_aleatoria

TITULOS_BLOQUEIO = ("just a moment", "attention required", "access denied", "acesso negado")
URLS_BLOQUEIO = ("account-verification", "/captcha/", "captcha/wall", "suspicious-traffic")


class BloqueioError(Exception):
    """A loja respondeu com página de bloqueio ou desafio anti-bot."""


def _titulo_seguro(page: Page) -> str:
    try:
        return page.title()
    except PlaywrightError:
        return "?"


@dataclass
class ItemProduto:
    titulo: str
    categoria: str
    preco_avista: Decimal | None
    parcelamento: str | None
    num_parcelas: int | None
    valor_parcela: Decimal | None
    loja: str
    link: str
    imagem_url: str | None = None


class LojaScraper(ABC):
    nome_loja: str
    base_url: str
    seletor_card: str

    @abstractmethod
    def url_busca(self, termo: str) -> str:
        """URL da página de resultados para o termo pesquisado."""

    @abstractmethod
    def extrair_titulo(self, card: Tag) -> str | None:
        """Título do produto dentro do card, ou None se não encontrado."""

    @abstractmethod
    def extrair_preco_avista(self, card: Tag) -> Decimal | None:
        """Preço à vista dentro do card, ou None se não encontrado."""

    def urls_busca(self, termos: list[str], categoria: str) -> list[str]:
        """URLs a visitar para uma categoria. Por padrão, uma busca por termo.

        Lojas com páginas de categoria próprias podem sobrescrever para varrer a
        listagem da categoria em vez de depender da busca.
        """
        return [self.url_busca(termo) for termo in termos]

    def buscar(self, page: Page, url: str, tentativas: int = 2) -> list[ItemProduto]:
        for tentativa in range(1, tentativas + 1):
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                if self._bloqueada(page):
                    raise BloqueioError(f"{self.nome_loja}: página de bloqueio em {page.url!r}")
                page.wait_for_selector(self.seletor_card, timeout=15000)
                page.wait_for_timeout(espera_renderizacao_ms())
                return self.parse(page.content())
            except PlaywrightTimeout:
                if self._bloqueada(page):
                    raise BloqueioError(
                        f"{self.nome_loja}: bloqueio detectado após timeout ({page.url!r})"
                    )
                log.warning(
                    "%s: cards não apareceram em %r (tentativa %d/%d, título: %r)",
                    self.nome_loja, url, tentativa, tentativas, _titulo_seguro(page),
                )
            except PlaywrightError:
                log.exception("%s: erro do navegador ao buscar %r", self.nome_loja, url)
                return []
            if tentativa < tentativas:
                pausa_aleatoria(10, 20)
        return []

    def _bloqueada(self, page: Page) -> bool:
        titulo = _titulo_seguro(page).lower()
        marca_titulo = any(marca in titulo for marca in TITULOS_BLOQUEIO)
        try:
            url = (page.url or "").lower()
        except PlaywrightError:
            url = ""
        marca_url = any(marca in url for marca in URLS_BLOQUEIO)
        return marca_titulo or marca_url

    def parse(self, html: str) -> list[ItemProduto]:
        soup = BeautifulSoup(html, "html.parser")
        itens = []
        for card in soup.select(self.seletor_card):
            try:
                item = self._extrair_item(card)
            except Exception:
                log.exception("%s: erro ao extrair card, ignorado", self.nome_loja)
                continue
            if item:
                itens.append(item)
        return itens

    def extrair_link(self, card: Tag) -> str | None:
        """Link do produto. Por padrão, o próprio card é o link."""
        return card.get("href")

    def _extrair_item(self, card: Tag) -> ItemProduto | None:
        titulo = self.extrair_titulo(card)
        href = self.extrair_link(card)
        if not titulo or not href:
            log.debug("%s: card sem título ou link, ignorado", self.nome_loja)
            return None

        categoria = classificar_categoria(titulo)
        if categoria is None:
            log.debug("%s: fora das categorias monitoradas: %r", self.nome_loja, titulo)
            return None

        preco_avista = self.extrair_preco_avista(card)
        if preco_avista is None:
            log.debug("%s: preço à vista não encontrado para %r", self.nome_loja, titulo)

        num_parcelas, valor_parcela, parcelamento = parse_parcelamento(
            card.get_text(" ", strip=True)
        )
        if parcelamento is None:
            log.debug("%s: parcelamento não encontrado para %r", self.nome_loja, titulo)

        return ItemProduto(
            titulo=titulo,
            categoria=categoria.value,
            preco_avista=preco_avista,
            parcelamento=parcelamento,
            num_parcelas=num_parcelas,
            valor_parcela=valor_parcela,
            loja=self.nome_loja,
            link=urljoin(self.base_url, href),
            imagem_url=self._extrair_imagem(card),
        )

    def _extrair_imagem(self, card: Tag) -> str | None:
        for imagem in card.select("img"):
            src = imagem.get("src") or imagem.get("data-src")
            if src and not src.startswith("data:"):
                return urljoin(self.base_url, src)
        return None

    @staticmethod
    def _texto(card: Tag, seletor: str) -> str | None:
        elemento = card.select_one(seletor)
        if elemento is None:
            return None
        return elemento.get_text(" ", strip=True) or None
