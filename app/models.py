from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class Peca(Base):
    __tablename__ = "pecas"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255), index=True)
    categoria: Mapped[str] = mapped_column(String(100), index=True)
    preco_atual: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    menor_preco_historico: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    loja: Mapped[str] = mapped_column(String(100), index=True)
    link: Mapped[str] = mapped_column(String(500), unique=True)
    imagem_url: Mapped[str | None] = mapped_column(String(500))
    data_varredura: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    historico: Mapped[list["HistoricoPreco"]] = relationship(
        back_populates="peca",
        cascade="all, delete-orphan",
        order_by="HistoricoPreco.data_registro",
    )


class HistoricoPreco(Base):
    __tablename__ = "historico_precos"

    id: Mapped[int] = mapped_column(primary_key=True)
    peca_id: Mapped[int] = mapped_column(ForeignKey("pecas.id", ondelete="CASCADE"), index=True)
    preco: Mapped[Decimal] = mapped_column(Numeric(10, 2))
    data_registro: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, index=True)

    peca: Mapped[Peca] = relationship(back_populates="historico")
