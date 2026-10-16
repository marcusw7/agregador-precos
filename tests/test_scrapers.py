from decimal import Decimal

import pytest
from playwright.sync_api import TimeoutError as PlaywrightTimeout

from app.scrapers.amazon import AmazonScraper
from app.scrapers.base import BloqueioError, LojaScraper
from app.scrapers.classificador import classificar_categoria
from app.scrapers.kabum import KabumScraper
from app.scrapers.patoloco import PatolocoScraper
from app.scrapers.pichau import PichauScraper
from app.scrapers.terabyte import TerabyteScraper
from app.scrapers.utils import parse_parcelamento, parse_preco, slug_url

KABUM_HTML = """
<html><body>
  <a href="/produto/998334/placa-de-video-pcyes-rtx-3050">
    <img src="https://images.kabum.com.br/rtx3050.jpg"/>
    <span class="text-sm line-clamp-2">Placa de Vídeo PcYes RTX 3050 6Gb</span>
    <span class="text-xs text-gray-400 line-through">R$ 2.352,93</span>
    <span class="text-base font-semibold text-gray-800">1.399,99</span>
    <span class="text-xs text-gray-400 h-16">No PIX ou 10x de R$ 164,70</span>
  </a>
  <a href="/produto/459144/rx-7600">
    <span class="text-sm line-clamp-2">Placa de Vídeo RX 7600 Challenger</span>
    <span class="text-base font-semibold">R$</span>
    <span class="text-base font-semibold">1.909,99</span>
    <span class="text-xs text-gray-400 h-16">No PIX ou 10x de R$ 224,70</span>
  </a>
  <a href="/produto/714568/rtx-5070-ti">
    <img alt="Placa Gigabyte RTX 5070 Ti"/>
  </a>
  <a href="/produto/1/sem-nome">
    <span class="text-base font-semibold">999,00</span>
  </a>
</body></html>
"""

PICHAU_HTML = """
<html><body>
  <a href="/placa-de-video-pny-rtx-5050">
    <img src="/media/pny.png"/>
    <h2>Placa de Video PNY GeForce RTX 5050</h2>
    <span class="mui-3ij2mi-strikeThrough">R$ 2.988,22</span>
    <span class="mui-12athy2-price_vista">R$ 2.189,99</span>
    <p class="mui-e8l09r-price_parcelado_inline">Em até 12x de R$ 182,50 Sem juros</p>
  </a>
  <a href="/cupom">
    <span>Cupom sem título de produto</span>
  </a>
  <a href="/fonte-msi">
    <img src="/media/fonte.png"/>
    <h2>Fonte MSI MAG A650BN 650W 80 Plus Bronze</h2>
    <span class="mui-12athy2-price_vista">R$ 289,99</span>
  </a>
</body></html>
"""


def test_parse_preco():
    assert parse_preco("R$ 2.352,93") == Decimal("2352.93")
    assert parse_preco("1.399,99") == Decimal("1399.99")
    assert parse_preco("R$\xa0999,00") == Decimal("999.00")
    assert parse_preco("sem preço") is None
    assert parse_preco("") is None
    assert parse_preco(None) is None


def test_parse_parcelamento():
    assert parse_parcelamento("No PIX ou 10x de R$ 164,70") == (
        10,
        Decimal("164.70"),
        "10x de R$ 164,70",
    )
    assert parse_parcelamento("Sem parcelamento") == (None, None, None)


def test_classificador_por_titulo():
    assert classificar_categoria("Placa de Vídeo RX 7600 Challenger").value == "GPU"
    assert classificar_categoria("Processador AMD Ryzen 5 7600").value == "CPU"
    assert classificar_categoria("Placa Mãe Gigabyte B650 AM5").value == "Placa-mãe"
    assert classificar_categoria("Memoria 16GB DDR5 6000MHz").value == "Memória RAM"
    assert classificar_categoria("SSD 1TB NVMe M.2 2280 Kingston").value == "SSD"
    assert classificar_categoria("SSD SATA III 480GB 2.5").value == "SSD"
    assert classificar_categoria("HD 1TB Seagate Barracuda") is None
    assert classificar_categoria("Case Externo Para SSD M2 NVMe USB-C") is None
    assert classificar_categoria("Gaveta para SSD SATA 2.5") is None
    assert classificar_categoria("Fonte MSI MAG A650BN 650W") is None
    assert classificar_categoria("Cooler Para Processador LGA 1700") is None
    assert classificar_categoria("Teclado mecânico") is None


def test_kabum_extrai_campos_e_trata_ausencias():
    itens = KabumScraper().parse(KABUM_HTML)

    assert len(itens) == 3

    completo = itens[0]
    assert completo.titulo == "Placa de Vídeo PcYes RTX 3050 6Gb"
    assert completo.categoria == "GPU"
    assert completo.preco_avista == Decimal("1399.99")
    assert completo.num_parcelas == 10
    assert completo.valor_parcela == Decimal("164.70")
    assert completo.parcelamento == "10x de R$ 164,70"
    assert completo.loja == "KaBuM!"
    assert completo.imagem_url == "https://images.kabum.com.br/rtx3050.jpg"
    assert completo.link == "https://www.kabum.com.br/produto/998334/placa-de-video-pcyes-rtx-3050"

    preco_dividido = itens[1]
    assert preco_dividido.preco_avista == Decimal("1909.99")
    assert preco_dividido.imagem_url is None

    sem_preco = itens[2]
    assert sem_preco.titulo == "Placa Gigabyte RTX 5070 Ti"
    assert sem_preco.preco_avista is None
    assert sem_preco.parcelamento is None
    assert sem_preco.num_parcelas is None


def test_pichau_extrai_campos_e_filtra_categorias():
    itens = PichauScraper().parse(PICHAU_HTML)

    assert len(itens) == 1
    item = itens[0]
    assert item.titulo == "Placa de Video PNY GeForce RTX 5050"
    assert item.categoria == "GPU"
    assert item.preco_avista == Decimal("2189.99")
    assert item.num_parcelas == 12
    assert item.valor_parcela == Decimal("182.50")
    assert item.loja == "Pichau"
    assert item.imagem_url == "https://www.pichau.com.br/media/pny.png"
    assert item.link == "https://www.pichau.com.br/placa-de-video-pny-rtx-5050"


TERABYTE_HTML = """
<html><body>
  <div class="product-item__box">
    <a href="/produto/40180/placa-de-video-pny-rtx-pro-4000" class="product-item__image">
      <img src="https://img.terabyteshop.com.br/rtx-pro-4000.jpg"/>
    </a>
    <a class="product-item__name" href="/produto/40180/placa-de-video-pny-rtx-pro-4000">
      <h2>Placa de Vídeo PNY NVIDIA GeForce RTX 4060 8GB</h2>
    </a>
    <div class="product-item__old-price"><del><span>R$ 2.999,00</span></del></div>
    <div class="product-item__new-price"><span>R$ 2.149,99</span> <small>à vista no Pix</small></div>
    <div class="product-item__juros"><span>12x</span><small> de </small><span>R$ 214,99</span></div>
  </div>
  <div class="product-item__box">
    <a class="product-item__name" href="/produto/1/indisponivel"><h2>Placa de Vídeo RX 7600 Indisponível</h2></a>
  </div>
</body></html>
"""

PATOLOCO_HTML = """
<html><body>
  <article class="product">
    <a href="https://patoloco.com.br/placa-de-video-rtx-4060-ventus">
      <img src="https://patoloco.com.br/resize/rtx4060.jpeg"/>
    </a>
    <div class="product-info">
      <a href="https://patoloco.com.br/placa-de-video-rtx-4060-ventus">
        <h3 class="tit">Placa de Vídeo RTX 4060 VENTUS 2x Black OC MSI NVIDIA GeForce, 8GB</h3>
      </a>
    </div>
    <p class="price-old">R$ 2.100,00</p>
    <p class="price-new"><span>R$ 1.899,90</span> à vista no PIX ou boleto c/ 15% de desconto</p>
    <p class="price-installment">em até 12x de R$ 158,33</p>
  </article>
  <article class="product product-unavailable">
    <div class="product-info">
      <a href="https://patoloco.com.br/placa-de-video-rx-7600">
        <h3 class="tit">Placa de Vídeo RX 7600 Sem Estoque</h3>
      </a>
    </div>
    <p class="price-new">&nbsp;</p>
  </article>
</body></html>
"""


def test_terabyte_extrai_campos_com_link_do_nome():
    itens = TerabyteScraper().parse(TERABYTE_HTML)

    assert len(itens) == 2
    completo = itens[0]
    assert completo.titulo == "Placa de Vídeo PNY NVIDIA GeForce RTX 4060 8GB"
    assert completo.categoria == "GPU"
    assert completo.preco_avista == Decimal("2149.99")
    assert completo.num_parcelas == 12
    assert completo.valor_parcela == Decimal("214.99")
    assert completo.loja == "Terabyte"
    assert completo.imagem_url == "https://img.terabyteshop.com.br/rtx-pro-4000.jpg"
    assert completo.link == "https://www.terabyteshop.com.br/produto/40180/placa-de-video-pny-rtx-pro-4000"

    sem_preco = itens[1]
    assert sem_preco.preco_avista is None
    assert sem_preco.parcelamento is None


def test_patoloco_usa_preco_novo_e_ignora_preco_antigo():
    itens = PatolocoScraper().parse(PATOLOCO_HTML)

    assert len(itens) == 2
    item = itens[0]
    assert item.titulo == "Placa de Vídeo RTX 4060 VENTUS 2x Black OC MSI NVIDIA GeForce, 8GB"
    assert item.preco_avista == Decimal("1899.90")
    assert item.num_parcelas == 12
    assert item.valor_parcela == Decimal("158.33")
    assert item.loja == "Patoloco"
    assert item.imagem_url == "https://patoloco.com.br/resize/rtx4060.jpeg"
    assert item.link == "https://patoloco.com.br/placa-de-video-rtx-4060-ventus"

    indisponivel = itens[1]
    assert indisponivel.preco_avista is None


def test_url_busca_novas_lojas():
    assert TerabyteScraper().url_busca("RTX 4060") == (
        "https://www.terabyteshop.com.br/busca?str=RTX+4060"
    )
    assert PatolocoScraper().url_busca("ryzen 5 7600") == (
        "https://patoloco.com.br/busca/?buscar-por=ryzen+5+7600"
    )


def test_url_busca_kabum_remove_acentos_e_espacos():
    assert KabumScraper().url_busca("RX 7600") == "https://www.kabum.com.br/busca/rx-7600"
    assert PichauScraper().url_busca("Core i5 13400F") == (
        "https://www.pichau.com.br/search?q=Core+i5+13400F"
    )


class PaginaSemResultados:
    url = "https://exemplo.com/busca"

    def goto(self, *args, **kwargs):
        pass

    def wait_for_selector(self, *args, **kwargs):
        raise PlaywrightTimeout("timeout")

    def content(self):
        return ""

    def title(self):
        return "Busca vazia"

    def wait_for_timeout(self, *args, **kwargs):
        pass


def test_buscar_retorna_lista_vazia_em_timeout():
    scraper: LojaScraper = KabumScraper()
    assert scraper.buscar(PaginaSemResultados(), "https://exemplo.com/busca", tentativas=1) == []


class PaginaBloqueadaUrl:
    url = "https://www.kabum.com.br/account-verification?go=https%3A%2F%2Fbusca"

    def goto(self, *args, **kwargs):
        pass

    def title(self):
        return "KaBuM!"

    def wait_for_timeout(self, *args, **kwargs):
        pass


def test_bloqueio_detectado_pela_url():
    with pytest.raises(BloqueioError):
        KabumScraper().buscar(
            PaginaBloqueadaUrl(), "https://www.kabum.com.br/busca/rtx-4060", tentativas=1
        )


AMAZON_HTML = """
<html><body>
  <div data-component-type="s-search-result">
    <img src="https://m.media-amazon.com/images/I/x.jpg"/>
    <h2><span>Placa de Vídeo ASRock Radeon RX 7600 Challenger OC, 8GB, GDDR6</span></h2>
    <a class="a-link-normal s-no-outline" href="/ASRock-RX7600/dp/B0C626FFG2/ref=sr_1_2"></a>
    <span class="a-price"><span class="a-offscreen">R$ 1.899,90</span></span>
    <span>em até 12x de R$ 158,33 sem juros</span>
  </div>
  <div data-component-type="s-search-result">
    <h2><span>Fonte Corsair 650W 80 Plus Bronze</span></h2>
    <a href="/Fonte/dp/B000000000"></a>
    <span class="a-price"><span class="a-offscreen">R$ 399,90</span></span>
  </div>
</body></html>
"""

def test_amazon_extrai_campos_e_filtra_categoria():
    itens = AmazonScraper().parse(AMAZON_HTML)

    assert len(itens) == 1
    item = itens[0]
    assert item.titulo == "Placa de Vídeo ASRock Radeon RX 7600 Challenger OC, 8GB, GDDR6"
    assert item.categoria == "GPU"
    assert item.preco_avista == Decimal("1899.90")
    assert item.num_parcelas == 12
    assert item.valor_parcela == Decimal("158.33")
    assert item.loja == "Amazon"
    assert item.imagem_url == "https://m.media-amazon.com/images/I/x.jpg"
    assert item.link == "https://www.amazon.com.br/ASRock-RX7600/dp/B0C626FFG2/ref=sr_1_2"


def test_urls_busca_por_categoria_e_slug():
    assert slug_url("RTX 4060 Ti") == "rtx-4060-ti"
    assert KabumScraper().urls_busca(["RTX 4060"], "GPU") == [
        "https://www.kabum.com.br/busca/rtx-4060"
    ]
    assert PatolocoScraper().urls_busca(["RTX 4060"], "GPU") == [
        "https://patoloco.com.br/produtos/placa-de-video"
    ]
    assert PatolocoScraper().urls_busca(["RTX 4060"], "Desconhecida") == [
        "https://patoloco.com.br/busca/?buscar-por=RTX+4060"
    ]
    assert AmazonScraper().url_busca("RTX 4060") == "https://www.amazon.com.br/s?k=RTX+4060"
