import random
import time

from playwright.sync_api import Browser

PAUSA_MIN_S = 4.0
PAUSA_MAX_S = 9.0
RENDERIZACAO_MIN_MS = 1500
RENDERIZACAO_MAX_MS = 3500


def pausa_aleatoria(minimo: float = PAUSA_MIN_S, maximo: float = PAUSA_MAX_S) -> float:
    espera = random.uniform(minimo, maximo)
    time.sleep(espera)
    return espera


def espera_renderizacao_ms() -> int:
    return random.randint(RENDERIZACAO_MIN_MS, RENDERIZACAO_MAX_MS)


def opcoes_contexto(navegador: Browser) -> dict:
    """User-Agent de Chrome/Windows com a versão real do Chromium em uso, para não divergir do navegador."""
    versao_maior = navegador.version.split(".")[0]
    return {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            f"(KHTML, like Gecko) Chrome/{versao_maior}.0.0.0 Safari/537.36"
        ),
        "locale": "pt-BR",
        "timezone_id": "America/Sao_Paulo",
        "viewport": {"width": 1366, "height": 900},
        "extra_http_headers": {
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        },
    }
