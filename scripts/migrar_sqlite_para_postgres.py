"""Migra os dados do SQLite local (``precos.db``) para um PostgreSQL.

Uso (o destino vem de variável de ambiente, para não deixar senha no histórico do shell):

    # simulação (não grava nada) - padrão
    python scripts/migrar_sqlite_para_postgres.py

    # grava de verdade
    python scripts/migrar_sqlite_para_postgres.py --executar

O alvo é lido de ``DATABASE_URL_MIGRACAO`` e, se ela não existir, de ``DATABASE_URL``.

Garantias:
* o arquivo SQLite é aberto em **modo somente leitura** (nunca é alterado);
* os IDs das peças são preservados;
* todos os registros de ``historico_precos`` são copiados;
* a operação pode ser repetida sem duplicar dados (casa pela ``link`` da peça e por
  ``(peça, data, preço)`` no histórico).
"""

import argparse
import sqlite3
import sys
from datetime import datetime
from decimal import Decimal
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
if str(RAIZ) not in sys.path:
    sys.path.insert(0, str(RAIZ))

from sqlalchemy import create_engine, inspect, select  # noqa: E402
from sqlalchemy.engine import Engine  # noqa: E402
from sqlalchemy.exc import SQLAlchemyError  # noqa: E402

from app.database import Base, mascarar_url, normalizar_url  # noqa: E402
from app.models import HistoricoPreco, Peca  # noqa: E402

SQLITE_PADRAO = RAIZ / "precos.db"
VARIAVEIS_DESTINO = ("DATABASE_URL_MIGRACAO", "DATABASE_URL")

T_PECAS = Peca.__table__
T_HISTORICO = HistoricoPreco.__table__


def _texto(valor) -> str | None:
    if valor is None:
        return None
    return str(valor)


def _decimal(valor) -> Decimal | None:
    """Converte para Decimal com 2 casas.

    O SQLite guarda NUMERIC com afinidade e devolve inteiro quando o valor é exato
    (1000.00 vira 1000). Normalizar aqui evita chaves diferentes para o mesmo preço.
    """
    if valor is None:
        return None
    numero = Decimal(str(valor))
    try:
        return numero.quantize(Decimal("0.01"))
    except Exception:  # noqa: BLE001 — valor fora do esperado: devolve como veio
        return numero


def _data(valor) -> datetime | None:
    if valor is None:
        return None
    if isinstance(valor, datetime):
        return valor
    texto = str(valor).strip().replace("T", " ")
    try:
        return datetime.fromisoformat(texto)
    except ValueError:
        for formato in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(texto, formato)
            except ValueError:
                continue
    raise ValueError(f"data não reconhecida: {valor!r}")


def ler_origem(caminho: Path) -> tuple[list[dict], list[dict]]:
    """Lê peças e histórico do SQLite em modo somente leitura."""
    uri = f"file:{caminho.as_posix()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as con:
        con.row_factory = sqlite3.Row
        pecas = [dict(linha) for linha in con.execute("SELECT * FROM pecas ORDER BY id")]
        historico = [
            dict(linha) for linha in con.execute("SELECT * FROM historico_precos ORDER BY id")
        ]
    return pecas, historico


def _ajustar_sequencia(con, tabela: str) -> None:
    """Depois de inserir IDs explícitos, alinha a sequência do PostgreSQL."""
    if con.dialect.name != "postgresql":
        return
    sequencia = con.exec_driver_sql(
        f"SELECT pg_get_serial_sequence('{tabela}', 'id')"
    ).scalar()
    if sequencia:
        con.exec_driver_sql(
            f"SELECT setval('{sequencia}', COALESCE((SELECT MAX(id) FROM {tabela}), 1))"
        )


def migrar(origem: Path, destino: Engine, executar: bool = False) -> dict:
    """Copia as peças e o histórico. Com ``executar=False`` apenas simula."""
    pecas, historico = ler_origem(origem)
    resumo = {
        "origem": str(origem),
        "pecas_origem": len(pecas),
        "historico_origem": len(historico),
        "pecas_inseridas": 0,
        "pecas_atualizadas": 0,
        "historico_inserido": 0,
        "historico_ignorado": 0,
        "dry_run": not executar,
    }

    if not executar:
        try:
            if inspect(destino).has_table(T_PECAS.name):
                with destino.connect() as con:
                    existentes = set(con.execute(select(T_PECAS.c.id, T_PECAS.c.link)).all())
                resumo["pecas_no_destino"] = len(existentes)
            else:
                resumo["pecas_no_destino"] = 0
        except SQLAlchemyError as erro:
            resumo["pecas_no_destino"] = None
            resumo["aviso"] = (
                f"não foi possível consultar o destino ({type(erro).__name__}); "
                "as contagens da origem foram lidas normalmente"
            )
        return resumo

    Base.metadata.create_all(destino)
    mapeamento: dict[int, int] = {}

    with destino.begin() as con:
        existentes = {
            link: pid
            for pid, link in con.execute(select(T_PECAS.c.id, T_PECAS.c.link)).all()
        }
        ids_em_uso = set(con.execute(select(T_PECAS.c.id)).scalars().all())

        for linha in pecas:
            dados = {
                "nome": _texto(linha["nome"]),
                "categoria": _texto(linha["categoria"]),
                "preco_atual": _decimal(linha["preco_atual"]),
                "menor_preco_historico": _decimal(linha["menor_preco_historico"]),
                "loja": _texto(linha["loja"]),
                "link": _texto(linha["link"]),
                "imagem_url": _texto(linha.get("imagem_url")),
                "data_varredura": _data(linha["data_varredura"]),
            }
            destino_id = existentes.get(dados["link"])
            if destino_id is not None:
                con.execute(T_PECAS.update().where(T_PECAS.c.id == destino_id).values(**dados))
                mapeamento[linha["id"]] = destino_id
                resumo["pecas_atualizadas"] += 1
                continue

            id_origem = linha["id"]
            if id_origem in ids_em_uso:
                resultado = con.execute(T_PECAS.insert().values(**dados))
                novo_id = resultado.inserted_primary_key[0]
            else:
                con.execute(T_PECAS.insert().values(id=id_origem, **dados))
                novo_id = id_origem
            ids_em_uso.add(novo_id)
            existentes[dados["link"]] = novo_id
            mapeamento[linha["id"]] = novo_id
            resumo["pecas_inseridas"] += 1

        _ajustar_sequencia(con, T_PECAS.name)

        ja_existe = {
            (pid, str(quando), str(preco))
            for pid, quando, preco in con.execute(
                select(T_HISTORICO.c.peca_id, T_HISTORICO.c.data_registro, T_HISTORICO.c.preco)
            ).all()
        }

        for linha in historico:
            peca_destino = mapeamento.get(linha["peca_id"])
            if peca_destino is None:
                resumo["historico_ignorado"] += 1
                continue
            quando = _data(linha["data_registro"])
            preco = _decimal(linha["preco"])
            chave = (peca_destino, str(quando), str(preco))
            if chave in ja_existe:
                resumo["historico_ignorado"] += 1
                continue
            con.execute(
                T_HISTORICO.insert().values(
                    peca_id=peca_destino, preco=preco, data_registro=quando
                )
            )
            ja_existe.add(chave)
            resumo["historico_inserido"] += 1

        _ajustar_sequencia(con, T_HISTORICO.name)

    return resumo


def resolver_destino(explicito: str | None) -> str:
    if explicito:
        return normalizar_url(explicito)
    import os

    for variavel in VARIAVEIS_DESTINO:
        valor = os.environ.get(variavel, "").strip()
        if valor:
            return normalizar_url(valor)
    return ""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Migra o SQLite local para PostgreSQL.")
    parser.add_argument("--origem", default=str(SQLITE_PADRAO), help="arquivo SQLite de origem")
    parser.add_argument(
        "--executar",
        action="store_true",
        help="grava de verdade; sem esta opção apenas simula",
    )
    args = parser.parse_args(argv)

    origem = Path(args.origem)
    if not origem.exists():
        print(f"Origem não encontrada: {origem}")
        return 1

    destino = resolver_destino(None)
    if not destino:
        print(
            "Defina DATABASE_URL_MIGRACAO (ou DATABASE_URL) com a URL do PostgreSQL.\n"
            "A URL não é aceita por argumento de linha de comando para não ficar no histórico."
        )
        return 1
    if not destino.startswith("postgresql"):
        print("O destino precisa ser PostgreSQL. Use DATABASE_URL apenas para o SQLite local.")
        return 1

    print(f"Origem : {origem}")
    print(f"Destino: {mascarar_url(destino)}")
    if not args.executar:
        print("Modo simulação (nada será gravado). Use --executar para valer.")

    engine = create_engine(destino, pool_pre_ping=True)
    try:
        resumo = migrar(origem, engine, executar=args.executar)
    finally:
        engine.dispose()

    for chave, valor in resumo.items():
        print(f"  {chave}: {valor}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
