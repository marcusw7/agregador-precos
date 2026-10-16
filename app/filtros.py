import pandas as pd


def valores_disponiveis(base: pd.DataFrame, atributo: str) -> list[str]:
    """Valores distintos de um atributo, para preencher os filtros."""
    if base.empty or atributo not in base.columns:
        return []
    return sorted(str(valor) for valor in base[atributo].dropna().unique())


def filtrar(
    df: pd.DataFrame,
    categoria: str | None = None,
    lojas: list[str] | None = None,
    atributos: dict[str, list[str]] | None = None,
    preco_min: float | None = None,
    preco_max: float | None = None,
    somente_minimo: bool = False,
    ordenar: str = "preco_asc",
) -> pd.DataFrame:
    """Aplica categoria, lojas, atributos (marca, chip, socket...), faixa de preço e ordenação."""
    resultado = df
    if categoria:
        resultado = resultado[resultado["categoria"] == categoria]
    if lojas:
        resultado = resultado[resultado["loja"].isin(lojas)]
    for atributo, escolhidos in (atributos or {}).items():
        if escolhidos:
            resultado = resultado[resultado[atributo].isin(escolhidos)]
    if preco_min is not None:
        resultado = resultado[resultado["preco_atual"] >= preco_min]
    if preco_max is not None:
        resultado = resultado[resultado["preco_atual"] <= preco_max]
    if somente_minimo:
        resultado = resultado[resultado["preco_atual"] <= resultado["menor_preco_historico"]]

    if ordenar == "preco_desc":
        return resultado.sort_values("preco_atual", ascending=False)
    if ordenar == "recentes":
        return resultado.sort_values("data_varredura", ascending=False)
    return resultado.sort_values("preco_atual")
