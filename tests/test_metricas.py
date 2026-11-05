"""Testes das métricas derivadas (variação de 7 dias) e do registro de coletas."""

from datetime import datetime, timedelta

import pandas as pd
import pytest

from app.ui.dados import calcular_metricas


def _pecas(ids_precos: list[tuple[int, float]], agora: datetime) -> pd.DataFrame:
    return pd.DataFrame(
        {
            "id": [pid for pid, _ in ids_precos],
            "nome": [f"Produto {pid}" for pid, _ in ids_precos],
            "categoria": ["GPU"] * len(ids_precos),
            "preco_atual": [preco for _, preco in ids_precos],
            "menor_preco_historico": [preco for _, preco in ids_precos],
            "loja": ["LojaTeste"] * len(ids_precos),
            "link": [f"https://x/{pid}" for pid, _ in ids_precos],
            "imagem_url": [None] * len(ids_precos),
            "data_varredura": [agora] * len(ids_precos),
        }
    )


def test_variacao_7d_usa_preco_de_7_dias_atras():
    agora = datetime.now()
    pecas = _pecas([(1, 900.0), (2, 1200.0)], agora)
    historico = pd.DataFrame(
        {
            "peca_id": [1, 1, 2],
            "data": [agora - timedelta(days=10), agora, agora],
            "preco": [1000.0, 900.0, 1200.0],
        }
    )

    resultado = calcular_metricas(pecas, historico)

    linha_1 = resultado[resultado["id"] == 1].iloc[0]
    # caiu de 1000 (10 dias atrás) para 900 → -10%
    assert abs(linha_1["variacao_7d"] + 10.0) < 0.01

    linha_2 = resultado[resultado["id"] == 2].iloc[0]
    # sem registro há 7 dias ou mais → variação desconhecida (não inventa dado)
    assert pd.isna(linha_2["variacao_7d"])


def test_variacao_7d_sem_historico_fica_vazia():
    agora = datetime.now()
    pecas = _pecas([(1, 900.0)], agora)
    resultado = calcular_metricas(pecas, pd.DataFrame(columns=["peca_id", "data", "preco"]))
    assert pd.isna(resultado.iloc[0]["variacao_7d"])


def test_dias_sem_atualizar_contados():
    agora = datetime.now()
    pecas = _pecas([(1, 900.0)], agora - timedelta(days=4))
    resultado = calcular_metricas(pecas, pd.DataFrame(columns=["peca_id", "data", "preco"]))
    assert resultado.iloc[0]["dias_sem_atualizar"] == 4


def test_pecas_vazias_nao_quebram():
    resultado = calcular_metricas(
        pd.DataFrame(),
        pd.DataFrame(columns=["peca_id", "data", "preco"]),
    )
    assert resultado.empty or "variacao_7d" in resultado.columns
