import re
import unicodedata

from categorias import Categoria
from scrapers.normalizacao import normalizar_titulo

SUFIXOS = {"ti": "Ti", "super": "Super", "xt": "XT", "xtx": "XTX"}

MARCAS: dict[str, list[str]] = {
    "ASUS": ["asus"],
    "MSI": ["msi"],
    "Gigabyte": ["gigabyte"],
    "Galax": ["galax"],
    "PNY": ["pny"],
    "ASRock": ["asrock"],
    "Zotac": ["zotac"],
    "Colorful": ["colorful"],
    "Palit": ["palit"],
    "Inno3D": ["inno3d", "inno 3d"],
    "PCYes": ["pcyes"],
    "Duex": ["duex"],
    "Gainward": ["gainward"],
    "EVGA": ["evga"],
    "Sapphire": ["sapphire"],
    "XFX": ["xfx"],
    "PowerColor": ["powercolor", "power color"],
    "Biostar": ["biostar"],
    "Kingston": ["kingston"],
    "Corsair": ["corsair"],
    "XPG": ["xpg"],
    "ADATA": ["adata"],
    "Crucial": ["crucial"],
    "Redragon": ["redragon"],
    "Husky": ["husky"],
    "Rise Mode": ["rise mode"],
    "Mancer": ["mancer"],
    "Thermaltake": ["thermaltake"],
    "DeepCool": ["deepcool"],
    "Cougar": ["cougar"],
    "NZXT": ["nzxt"],
    "Super Flower": ["super flower"],
    "AMD": ["amd"],
    "Intel": ["intel"],
    "Samsung": ["samsung"],
    "Western Digital": ["western digital", "wd"],
    "Seagate": ["seagate"],
    "SanDisk": ["sandisk", "san disk"],
    "Lexar": ["lexar"],
    "Hikvision": ["hikvision"],
    "Silicon Power": ["silicon power"],
    "Team Group": ["team group", "teamgroup"],
    "Netac": ["netac"],
}

GPU_CHIP = re.compile(r"\b(rtx|gtx)\s?(\d{4})\s?(ti|super|xt)?\b")
RX_CHIP = re.compile(r"\brx\s?(\d{3,4})\s?(xtx|xt)?\b")
RYZEN = re.compile(r"\bryzen\s?([3579])?\s?(\d{4,5}[a-z]{0,2})?\b")
INTEL = re.compile(r"\b(i[3579])\s?-?\s?(\d{4,5}[a-z]{0,2})\b")
SOCKET = re.compile(r"\b(am5|am4|am3\+?|lga\s?\d{4}|fm2\+?)\b")
CHIPSET = re.compile(r"\b([abhxz]\d{3}[a-z]{0,2})\b")
DDR = re.compile(r"\b(ddr[345])\b")
CAPACIDADE = re.compile(r"\b(\d{1,3})\s?gb\b")
CAPACIDADE_DISCO = re.compile(r"\b(\d{1,4})\s?(tb|gb)\b")
FREQUENCIA = re.compile(r"\b(\d{3,4})\s?mhz\b")

ATRIBUTOS_POR_CATEGORIA: dict[str, list[str]] = {
    Categoria.GPU.value: ["Chip", "VRAM"],
    Categoria.CPU.value: ["Modelo", "Socket"],
    Categoria.PLACA_MAE.value: ["Chipset", "Socket"],
    Categoria.MEMORIA_RAM.value: ["Tipo", "Capacidade", "Frequência"],
    Categoria.SSD.value: ["Interface", "Capacidade"],
}

TODOS_ATRIBUTOS = [
    "Marca",
    "Chip",
    "VRAM",
    "Modelo",
    "Socket",
    "Chipset",
    "Tipo",
    "Interface",
    "Capacidade",
    "Frequência",
]


def _numero(valor: str) -> str:
    """Remove zeros à esquerda de códigos como '0512' (SKU) para virar capacidade real."""
    return valor.lstrip("0") or "0"


def _texto(titulo: str) -> str:
    """Minúsculo, sem acentos, mantendo letras e números juntos (para casar 'b650' e 'am5')."""
    sem_acento = unicodedata.normalize("NFKD", normalizar_titulo(titulo))
    sem_acento = sem_acento.encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9+]+", " ", sem_acento.lower())


def extrair_marca(texto: str) -> str | None:
    for nome, apelidos in MARCAS.items():
        for apelido in apelidos:
            if re.search(rf"\b{re.escape(apelido)}\b", texto):
                return nome
    return None


def _chip_gpu(texto: str) -> str | None:
    casamento = GPU_CHIP.search(texto)
    if casamento:
        sufixo = casamento.group(3)
        base = f"{casamento.group(1).upper()} {casamento.group(2)}"
        return f"{base} {SUFIXOS.get(sufixo, sufixo.upper())}" if sufixo else base
    casamento = RX_CHIP.search(texto)
    if casamento:
        sufixo = casamento.group(2)
        base = f"RX {casamento.group(1)}"
        return f"{base} {SUFIXOS.get(sufixo, sufixo.upper())}" if sufixo else base
    return None


def _modelo_cpu(texto: str) -> str | None:
    casamento = RYZEN.search(texto)
    if casamento and casamento.group(2):
        partes = ["Ryzen"]
        if casamento.group(1):
            partes.append(casamento.group(1))
        partes.append(casamento.group(2).upper())
        return " ".join(partes)
    casamento = INTEL.search(texto)
    if casamento:
        return f"Core {casamento.group(1)} {casamento.group(2).upper()}"
    return None


def _interface_ssd(texto: str) -> str | None:
    if re.search(r"\bnvme\b|\bpcie\b", texto):
        return "NVMe"
    if re.search(r"\bsata\b", texto):
        return "SATA"
    return None


def _socket(texto: str) -> str | None:
    casamento = SOCKET.search(texto)
    if not casamento:
        return None
    valor = casamento.group(1).upper().replace(" ", "")
    if valor.startswith("LGA"):
        return f"LGA {valor[3:]}"
    return valor


def extrair_atributos(titulo: str, categoria: str) -> dict[str, str]:
    texto = _texto(titulo)
    atributos: dict[str, str] = {}

    marca = extrair_marca(texto)
    if marca:
        atributos["Marca"] = marca

    if categoria == Categoria.GPU.value:
        chip = _chip_gpu(texto)
        if chip:
            atributos["Chip"] = chip
        capacidade = CAPACIDADE.search(texto)
        if capacidade:
            atributos["VRAM"] = f"{capacidade.group(1)}GB"
    elif categoria == Categoria.CPU.value:
        modelo = _modelo_cpu(texto)
        if modelo:
            atributos["Modelo"] = modelo
        socket = _socket(texto)
        if socket:
            atributos["Socket"] = socket
        if "Marca" not in atributos:
            if re.search(r"\bryzen\b|\bamd\b|athlon|threadripper", texto):
                atributos["Marca"] = "AMD"
            elif re.search(r"\bintel\b|core|\bi[3579]\b", texto):
                atributos["Marca"] = "Intel"
    elif categoria == Categoria.PLACA_MAE.value:
        chipset = CHIPSET.search(texto)
        if chipset:
            atributos["Chipset"] = chipset.group(1).upper()
        socket = _socket(texto)
        if socket:
            atributos["Socket"] = socket
    elif categoria == Categoria.MEMORIA_RAM.value:
        tipo = DDR.search(texto)
        if tipo:
            atributos["Tipo"] = tipo.group(1).upper()
        capacidade = CAPACIDADE.search(texto)
        if capacidade:
            atributos["Capacidade"] = f"{_numero(capacidade.group(1))}GB"
        frequencia = FREQUENCIA.search(texto)
        if frequencia:
            atributos["Frequência"] = f"{frequencia.group(1)}MHz"
    elif categoria == Categoria.SSD.value:
        interface = _interface_ssd(texto)
        if interface:
            atributos["Interface"] = interface
        capacidade = CAPACIDADE_DISCO.search(texto)
        if capacidade:
            atributos["Capacidade"] = f"{_numero(capacidade.group(1))}{capacidade.group(2).upper()}"

    return atributos
