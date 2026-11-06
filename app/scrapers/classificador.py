import re

from app.categorias import Categoria

EXCLUIR = re.compile(
    r"cooler|water\s*cooler|suporte|cabo|adaptador|notebook|kit\s+upgrade|"
    r"pc\s+gamer|computador|gaveta|dock|conversor|enclosure|bra[cç]o|"
    r"dissipador|heat\s*sink|heatsink|case\s+externo",
    re.IGNORECASE,
)

REGRAS: list[tuple[Categoria, re.Pattern]] = [
    (
        Categoria.PLACA_MAE,
        re.compile(
            r"placa[\s-]*m[aã]e|motherboard|\b[ABHXZ]\d{3}[A-Z]{0,2}\b.*\b(AM[45]|LGA\s?\d{3,4})\b",
            re.IGNORECASE,
        ),
    ),
    (
        Categoria.CPU,
        re.compile(
            r"processador|ryzen|core\s+i[3579]|athlon|pentium|celeron|threadripper",
            re.IGNORECASE,
        ),
    ),
    (
        Categoria.GPU,
        re.compile(
            r"placa\s+de\s+v[ií]deo|geforce|radeon|\brtx\b|\bgtx\b|\brx\s?\d{3,4}\b|\bgpu\b",
            re.IGNORECASE,
        ),
    ),
    (
        Categoria.MEMORIA_RAM,
        re.compile(r"mem[óo]ria|\bddr[345]\b|\bram\b", re.IGNORECASE),
    ),
    (
        Categoria.SSD,
        re.compile(r"\bssd\b|\bnvme\b", re.IGNORECASE),
    ),
    (
        Categoria.MONITOR,
        re.compile(r"\bmonitor(?:es)?\b|\bdisplay\b", re.IGNORECASE),
    ),
    (
        Categoria.CADEIRA,
        re.compile(r"\bcadeira\b", re.IGNORECASE),
    ),
    (
        Categoria.FONTE,
        re.compile(r"\bfonte\b|\bpsu\b|\b80\s*plus\b|\bpower\s*supply\b", re.IGNORECASE),
    ),
    (
        Categoria.GABINETE,
        re.compile(r"\bgabinete\b|\bcase\b|mid\s*tower|full\s*tower", re.IGNORECASE),
    ),
]


def classificar_categoria(titulo: str) -> Categoria | None:
    """Define a categoria pelo título do produto. Retorna None se não for uma das categorias ou for acessório."""
    if EXCLUIR.search(titulo):
        return None
    for categoria, padrao in REGRAS:
        if padrao.search(titulo):
            return categoria
    return None
