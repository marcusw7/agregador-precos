from app.categorias import Categoria

# Termos pesquisados em cada loja. Mantido enxuto de propósito: cada termo vira
# uma busca por loja, então o total de requisições cresce rápido. Termos genéricos
# o bastante para casar variações de nomenclatura, mas específicos para não trazer
# acessórios ou produtos fora da categoria.
CATALOGO: dict[str, list[str]] = {
    Categoria.GPU.value: [
        "RTX 4060",
        "RTX 4060 Ti",
        "RTX 4070 Super",
        "RX 7600",
        "RX 7800 XT",
    ],
    Categoria.CPU.value: [
        "Ryzen 5 5600",
        "Ryzen 7 7800X3D",
        "Core i5 12400F",
        "Core i7 14700K",
    ],
    Categoria.PLACA_MAE.value: [
        "placa mae B550 AM4",
        "placa mae B650 AM5",
        "placa mae B760 LGA1700",
    ],
    Categoria.MEMORIA_RAM.value: [
        "memoria DDR5 16GB 6000",
        "memoria DDR5 32GB 6000",
        "memoria DDR4 16GB 3200",
    ],
    Categoria.SSD.value: [
        "SSD NVMe 1TB",
        "SSD NVMe 2TB",
        "SSD SATA 480GB",
    ],
    Categoria.FONTE.value: [
        "fonte 650W 80 Plus",
        "fonte 750W 80 Plus Gold",
        "fonte 850W",
    ],
    Categoria.GABINETE.value: [
        "gabinete gamer mid tower",
        "gabinete gamer ATX",
    ],
    Categoria.MONITOR.value: [
        "monitor 144hz",
        "monitor 165hz",
        "monitor 27 polegadas",
    ],
    Categoria.CADEIRA.value: [
        "cadeira gamer",
        "cadeira ergonomica",
    ],
}
