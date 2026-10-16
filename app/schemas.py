from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, PlainSerializer

Preco = Annotated[Decimal, PlainSerializer(float, return_type=float, when_used="json")]


class PecaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nome: str
    categoria: str
    preco_atual: Preco
    menor_preco_historico: Preco
    loja: str
    link: str
    imagem_url: str | None = None
    data_varredura: datetime


class HistoricoPrecoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    preco: Preco
    data_registro: datetime
