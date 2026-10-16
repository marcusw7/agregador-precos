from app import coleta
from app.consultas import nome_contem_termo


def test_nome_contem_termo_ignora_caixa_e_acentos():
    assert nome_contem_termo("Placa de Vídeo RTX 4060 Ti 8GB", "rtx 4060 ti")
    assert nome_contem_termo("PLACA DE VIDEO ASUS RTX 4060", "Rtx 4060")


def test_nome_contem_termo_modo_normal_aceita_qualquer_ordem():
    assert nome_contem_termo("Placa de Vídeo RTX 4060 8GB", "rtx 4060 ti") is False
    assert nome_contem_termo("GeForce 8GB RTX 4060", "rtx 4060")
    assert nome_contem_termo("Placa de Vídeo RTX 4060 Ti 8GB", "rtx 4060")


def test_modo_exato_nao_aceita_variantes_de_sufixo():
    assert nome_contem_termo("Placa de Vídeo RTX 4060 Ti 8GB", "RTX 4060", exato=True) is False
    assert nome_contem_termo("Placa de Vídeo RTX 4060 Super", "RTX 4060", exato=True) is False
    assert nome_contem_termo("Ryzen 5 7600X AM5", "Ryzen 5 7600", exato=True) is False
    assert nome_contem_termo("Core i5 13400F LGA1700", "Core i5 13400", exato=True) is False


def test_modo_exato_aceita_produto_correto_e_exige_sequencia():
    assert nome_contem_termo("Placa de Vídeo RTX 4060 8GB GDDR6", "RTX 4060", exato=True)
    assert nome_contem_termo("Placa de Vídeo RTX 4060 Ti 8GB", "RTX 4060 Ti", exato=True)
    assert nome_contem_termo("Ryzen 5 7600 AM5 sem cooler", "Ryzen 5 7600", exato=True)
    assert nome_contem_termo("GeForce 8GB RTX 4060", "RTX 4060", exato=True)
    assert nome_contem_termo("RTX 5060 e RTX 4060 Ti", "RTX 4060", exato=True) is False


def test_pesquisar_produto_rejeita_termo_vazio():
    try:
        coleta.pesquisar_produto("   ")
    except ValueError:
        return
    raise AssertionError("termo vazio deveria levantar ValueError")


def test_pesquisar_produto_usa_termo_no_catalogo(monkeypatch):
    chamadas = {}

    def coletar_falso(catalogo=None, lojas=None):
        chamadas["catalogo"] = catalogo
        return []

    monkeypatch.setattr(coleta, "coletar", coletar_falso)
    resumo = coleta.pesquisar_produto("  RTX 4060 Ti ", exato=True)

    assert chamadas["catalogo"] == {"Pesquisa": ["RTX 4060 Ti"]}
    assert resumo["termo"] == "RTX 4060 Ti"
    assert resumo["coletados"] == 0
