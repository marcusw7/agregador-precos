import re
import unicodedata

TERMOS_PROMOCIONAIS = re.compile(
    r"\b(frete\s+gr[aá]tis|super\s+oferta|oferta[s]?|promo[cç][aã]o|imperd[ií]vel|"
    r"lan[cç]amento|mais\s+vendido|melhor\s+pre[cç]o|pronta\s+entrega|envio\s+imediato|"
    r"sem\s+juros|cupom|desconto)\b",
    re.IGNORECASE,
)
SEPARADORES_SOLTOS = re.compile(r"\s*[|•]\s*")
PONTUACAO_REPETIDA = re.compile(r"(\s*[,;]\s*){2,}")
BORDAS = re.compile(r"^[\s\-,;:/]+|[\s\-,;:/]+$")


def normalizar_titulo(titulo: str | None) -> str:
    """Remove termos promocionais e espaços/pontuação sobrando, mantendo o nome do produto e o SKU."""
    if not titulo:
        return ""
    texto = unicodedata.normalize("NFC", titulo).replace("\xa0", " ")
    texto = TERMOS_PROMOCIONAIS.sub(" ", texto)
    texto = SEPARADORES_SOLTOS.sub(" ", texto)
    texto = re.sub(r"\s+", " ", texto)
    texto = PONTUACAO_REPETIDA.sub(", ", texto)
    texto = re.sub(r"\s+([,;])", r"\1", texto)
    return BORDAS.sub("", texto)


def chave_comparacao(titulo: str | None) -> str:
    """Forma sem acentos, minúscula e só com letras/números, para casar o mesmo produto entre lojas."""
    texto = normalizar_titulo(titulo)
    sem_acento = unicodedata.normalize("NFKD", texto).encode("ascii", "ignore").decode()
    sem_acento = re.sub(r"[^a-z0-9]+", " ", sem_acento.lower())
    sem_acento = re.sub(r"(?<=[a-z])(?=[0-9])|(?<=[0-9])(?=[a-z])", " ", sem_acento)
    return sem_acento.strip()
