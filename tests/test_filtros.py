import pandas as pd
import pytest

from app.filtros import filtrar, valores_disponiveis


@pytest.fixture
def df():
    return pd.DataFrame(
        [
            {"nome": "RTX 4060 Ti ASUS", "categoria": "GPU", "loja": "KaBuM!", "preco_atual": 2500.0, "menor_preco_historico": 2400.0, "Marca": "ASUS", "Chip": "RTX 4060 Ti", "data_varredura": pd.Timestamp("2026-10-01")},
            {"nome": "RX 7600 ASRock", "categoria": "GPU", "loja": "Amazon", "preco_atual": 1800.0, "menor_preco_historico": 1800.0, "Marca": "ASRock", "Chip": "RX 7600", "data_varredura": pd.Timestamp("2026-10-02")},
            {"nome": "Ryzen 5 7600", "categoria": "CPU", "loja": "KaBuM!", "preco_atual": 1200.0, "menor_preco_historico": 1100.0, "Marca": "AMD", "Chip": None, "data_varredura": pd.Timestamp("2026-10-03")},
        ]
    )


def test_filtra_por_categoria(df):
    assert list(filtrar(df, categoria="GPU")["nome"]) == ["RX 7600 ASRock", "RTX 4060 Ti ASUS"]
    assert list(filtrar(df, categoria="CPU")["nome"]) == ["Ryzen 5 7600"]


def test_filtra_por_loja(df):
    assert list(filtrar(df, lojas=["Amazon"])["nome"]) == ["RX 7600 ASRock"]
    assert list(filtrar(df, lojas=["KaBuM!", "Amazon"])["nome"]) == [
        "Ryzen 5 7600",
        "RX 7600 ASRock",
        "RTX 4060 Ti ASUS",
    ]
    assert list(filtrar(df, categoria="GPU", lojas=["KaBuM!"])["nome"]) == ["RTX 4060 Ti ASUS"]


def test_filtra_por_marca_e_chip(df):
    por_marca = filtrar(df, categoria="GPU", atributos={"Marca": ["ASUS"]})
    assert list(por_marca["nome"]) == ["RTX 4060 Ti ASUS"]

    por_chip = filtrar(df, categoria="GPU", atributos={"Chip": ["RX 7600", "RTX 4060 Ti"]})
    assert len(por_chip) == 2

    sem_match = filtrar(df, categoria="GPU", atributos={"Marca": ["MSI"]})
    assert sem_match.empty


def test_filtra_faixa_de_preco(df):
    assert list(filtrar(df, preco_min=1500, preco_max=2000)["nome"]) == ["RX 7600 ASRock"]
    assert list(filtrar(df, preco_max=1300)["nome"]) == ["Ryzen 5 7600"]


def test_filtra_somente_no_menor_preco_historico(df):
    resultado = filtrar(df, somente_minimo=True)
    assert list(resultado["nome"]) == ["RX 7600 ASRock"]


def test_ordenacao(df):
    assert list(filtrar(df, ordenar="preco_asc")["nome"]) == ["Ryzen 5 7600", "RX 7600 ASRock", "RTX 4060 Ti ASUS"]
    assert list(filtrar(df, ordenar="preco_desc")["nome"]) == ["RTX 4060 Ti ASUS", "RX 7600 ASRock", "Ryzen 5 7600"]
    assert list(filtrar(df, ordenar="recentes")["nome"]) == ["Ryzen 5 7600", "RX 7600 ASRock", "RTX 4060 Ti ASUS"]


def test_valores_disponiveis_ignora_nulos(df):
    assert valores_disponiveis(df[df["categoria"] == "GPU"], "Marca") == ["ASRock", "ASUS"]
    assert valores_disponiveis(df, "Inexistente") == []
