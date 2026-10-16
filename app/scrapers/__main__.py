import json
import logging
from dataclasses import asdict

from app.scrapers.coletor import coletar


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    itens = coletar()
    print(json.dumps([asdict(item) for item in itens], ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
