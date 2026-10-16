import pytest

from app.scrapers.base import BloqueioError
from app.scrapers.kabum import KabumScraper
from app.scrapers.normalizacao import chave_comparacao, normalizar_titulo
from app.scrapers.politica import opcoes_contexto, pausa_aleatoria


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ("Placa de Vídeo RX 7600 Challenger ASRock,  8GB GDDR6", "Placa de Vídeo RX 7600 Challenger ASRock, 8GB GDDR6"),
        ("Placa de Vídeo RTX 4060  Frete Grátis  Oferta Imperdível", "Placa de Vídeo RTX 4060"),
        ("Processador Ryzen 5 7600 | Promoção | Lançamento", "Processador Ryzen 5 7600"),
        ("Placa Mãe B650 AM5 - Frete Grátis, Sem Juros", "Placa Mãe B650 AM5"),
        ("Memória 16GB DDR5 - 90-GA41ZZ-00UANF", "Memória 16GB DDR5 - 90-GA41ZZ-00UANF"),
        ("  Memória\xa0\xa016GB   DDR4  ", "Memória 16GB DDR4"),
    ],
)
def test_normalizar_titulo_remove_promocionais_e_espacos(bruto, esperado):
    assert normalizar_titulo(bruto) == esperado


def test_normalizar_titulo_vazio():
    assert normalizar_titulo(None) == ""
    assert normalizar_titulo("   ") == ""


def test_chave_comparacao_casa_mesmo_produto_entre_lojas():
    kabum = "Placa de Vídeo RX 7600 Challenger ASRock  Frete Grátis"
    pichau = "PLACA DE VIDEO RX 7600 CHALLENGER ASROCK!"
    assert chave_comparacao(kabum) == chave_comparacao(pichau)


def test_opcoes_contexto_usam_chrome_windows_e_pt_br():
    class NavegadorFalso:
        version = "153.0.8010.12"

    opcoes = opcoes_contexto(NavegadorFalso())
    assert "Windows NT 10.0" in opcoes["user_agent"]
    assert "Chrome/153.0.0.0" in opcoes["user_agent"]
    assert opcoes["locale"] == "pt-BR"
    assert "pt-BR" in opcoes["extra_http_headers"]["Accept-Language"]


def test_pausa_aleatoria_respeita_limites():
    espera = pausa_aleatoria(0, 0.01)
    assert 0 <= espera <= 0.01


class PaginaBloqueada:
    url = "https://www.kabum.com.br/busca/rtx-4060"

    def goto(self, *args, **kwargs):
        pass

    def title(self):
        return "Just a moment..."

    def wait_for_timeout(self, *args, **kwargs):
        pass


def test_buscar_levanta_bloqueio_em_pagina_de_desafio():
    with pytest.raises(BloqueioError):
        KabumScraper().buscar(PaginaBloqueada(), "https://www.kabum.com.br/busca/rtx-4060", tentativas=1)
