import re
import unicodedata
from decimal import Decimal


def slug_url(texto: str) -> str:
    """Transforma 'RTX 4060 Ti' em 'rtx-4060-ti' para usar na URL de busca."""
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", sem_acento.lower()).strip("-")

PRECO_RE = re.compile(r"\d{1,3}(?:\.\d{3})*,\d{2}")
PARCELA_RE = re.compile(
    r"(\d{1,2})\s*x\s+de\s+R\$\s*(\d{1,3}(?:\.\d{3})*,\d{2})",
    re.IGNORECASE,
)


def normalizar_espacos(texto: str) -> str:
    return texto.replace("\xa0", " ")


def parse_preco(texto: str | None) -> Decimal | None:
    """Converte 'R$ 2.352,93' (ou '1.399,99') em Decimal('2352.93')."""
    if not texto:
        return None
    match = PRECO_RE.search(normalizar_espacos(texto))
    if not match:
        return None
    return Decimal(match.group(0).replace(".", "").replace(",", "."))


def parse_parcelamento(texto: str | None) -> tuple[int | None, Decimal | None, str | None]:
    """Extrai (num_parcelas, valor_parcela, texto_original) de '10x de R$ 164,70'."""
    if not texto:
        return None, None, None
    match = PARCELA_RE.search(normalizar_espacos(texto))
    if not match:
        return None, None, None
    return int(match.group(1)), parse_preco(match.group(2)), match.group(0)
