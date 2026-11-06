from enum import Enum


class Categoria(str, Enum):
    GPU = "GPU"
    CPU = "CPU"
    PLACA_MAE = "Placa-mãe"
    MEMORIA_RAM = "Memória RAM"
    SSD = "SSD"
    MONITOR = "Monitor"
    CADEIRA = "Cadeira"
    FONTE = "Fonte"
    GABINETE = "Gabinete"
