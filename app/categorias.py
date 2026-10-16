from enum import Enum


class Categoria(str, Enum):
    GPU = "GPU"
    CPU = "CPU"
    PLACA_MAE = "Placa-mãe"
    MEMORIA_RAM = "Memória RAM"
    SSD = "SSD"
