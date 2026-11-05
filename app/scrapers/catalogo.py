from app.categorias import Categoria

CATALOGO: dict[str, list[str]] = {
    Categoria.GPU.value: ["RTX 4060", "RX 7600"],
    Categoria.CPU.value: ["Ryzen 5 7600", "Core i5 13400F"],
    Categoria.PLACA_MAE.value: ["placa mae B650 AM5", "placa mae B760 LGA1700"],
    Categoria.MEMORIA_RAM.value: ["memoria DDR5 16GB 6000", "memoria DDR4 16GB 3200"],
    Categoria.SSD.value: ["SSD NVMe 1TB", "SSD SATA 480GB"],
    Categoria.MONITOR.value: ["monitor 144hz", "monitor 27 polegadas"],
    Categoria.CADEIRA.value: ["cadeira gamer", "cadeira ergonomica"],
}
