from app.atributos import extrair_atributos, extrair_marca


def test_marca_prefere_fabricante_da_placa():
    assert extrair_marca("placa de video asrock amd radeon rx 7600") == "ASRock"
    assert extrair_marca("placa de video galax geforce rtx 5080") == "Galax"
    assert extrair_marca("placa de video pcyes nvidia rtx 3050") == "PCYes"
    assert extrair_marca("memoria kingston fury beast 16gb") == "Kingston"
    assert extrair_marca("produto sem marca conhecida xyz") is None


def test_atributos_gpu():
    atributos = extrair_atributos(
        "Placa de Vídeo ASRock Radeon RX 7600 Challenger OC, 8GB, GDDR6", "GPU"
    )
    assert atributos["Marca"] == "ASRock"
    assert atributos["Chip"] == "RX 7600"
    assert atributos["VRAM"] == "8GB"


def test_atributos_gpu_sufixo_e_sem_espaco():
    assert extrair_atributos("Placa de Video MSI RTX5060Ti Ventus 8GB", "GPU") == {
        "Marca": "MSI",
        "Chip": "RTX 5060 Ti",
        "VRAM": "8GB",
    }
    assert extrair_atributos("Placa de Video RTX 4060 Super 16GB", "GPU")["Chip"] == "RTX 4060 Super"


def test_atributos_cpu_modelo_socket_e_marca():
    amd = extrair_atributos("Processador AMD Ryzen 5 7600X, AM5, 6 núcleos", "CPU")
    assert amd["Marca"] == "AMD"
    assert amd["Modelo"] == "Ryzen 5 7600X"
    assert amd["Socket"] == "AM5"

    intel = extrair_atributos("Processador Intel Core i5-13400F LGA1700", "CPU")
    assert intel["Marca"] == "Intel"
    assert intel["Modelo"] == "Core i5 13400F"
    assert intel["Socket"] == "LGA 1700"

    sem_marca = extrair_atributos("Processador Ryzen 7 8700F AM5", "CPU")
    assert sem_marca["Marca"] == "AMD"


def test_atributos_placa_mae():
    atributos = extrair_atributos("Placa Mãe Gigabyte B650M DS3H, AMD AM5, DDR5", "Placa-mãe")
    assert atributos["Marca"] == "Gigabyte"
    assert atributos["Chipset"] == "B650M"
    assert atributos["Socket"] == "AM5"


def test_atributos_memoria():
    atributos = extrair_atributos("Memória Kingston Fury Beast, 16GB, 3200MHz, DDR4, CL16", "Memória RAM")
    assert atributos["Marca"] == "Kingston"
    assert atributos["Tipo"] == "DDR4"
    assert atributos["Capacidade"] == "16GB"
    assert atributos["Frequência"] == "3200MHz"


def test_atributos_ssd():
    nvme = extrair_atributos("SSD 1TB NVMe M.2 2280 Kingston NV3", "SSD")
    assert nvme["Marca"] == "Kingston"
    assert nvme["Interface"] == "NVMe"
    assert nvme["Capacidade"] == "1TB"

    sata = extrair_atributos("SSD 480GB SATA III 2.5 SanDisk", "SSD")
    assert sata["Marca"] == "SanDisk"
    assert sata["Interface"] == "SATA"
    assert sata["Capacidade"] == "480GB"

    pcie = extrair_atributos("SSD 2TB PCIe Gen4 Western Digital Black", "SSD")
    assert pcie["Marca"] == "Western Digital"
    assert pcie["Interface"] == "NVMe"
    assert pcie["Capacidade"] == "2TB"

    zerado = extrair_atributos("SSD 0512GB M.2 PCIE NVME KING KC3000", "SSD")
    assert zerado["Capacidade"] == "512GB"


def test_atributos_ssd_sem_interface_identificada():
    generico = extrair_atributos("SSD 512GB Kingston", "SSD")
    assert "Interface" not in generico
    assert generico["Capacidade"] == "512GB"


def test_categoria_desconhecida_traz_apenas_marca():
    atributos = extrair_atributos("Teclado Redragon Kumara", "Outros")
    assert atributos == {"Marca": "Redragon"}


def test_atributos_monitor():
    atributos = extrair_atributos("Monitor LG UltraGear 27 polegadas Full HD 144Hz", "Monitor")
    assert atributos["Marca"] == "LG"
    assert atributos["Tamanho"] == '27"'
    assert atributos["Resolução"] == "Full HD"
    assert atributos["Taxa"] == "144Hz"


def test_atributos_monitor_com_aspas_e_qhd():
    atributos = extrair_atributos('Monitor Gamer AOC Hero 24" Quad HD 165Hz', "Monitor")
    assert atributos["Marca"] == "AOC"
    assert atributos["Tamanho"] == '24"'
    assert atributos["Resolução"] == "QHD"
    assert atributos["Taxa"] == "165Hz"


def test_atributos_cadeira():
    atributos = extrair_atributos("Cadeira Gamer ThunderX3 TGC12", "Cadeira")
    assert atributos["Marca"] == "ThunderX3"
    assert atributos["Tipo"] == "Gamer"

    ergonomica = extrair_atributos("Cadeira Ergonômica de Escritório", "Cadeira")
    assert ergonomica["Tipo"] == "Ergonômica"
