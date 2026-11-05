# Desenvolvimento — PromoTracker

Documentação interna para quem desenvolve ou opera o PromoTracker.

## Estrutura do projeto

```
app/
├── dashboard.py        # entrada do Streamlit (navegação entre páginas)
├── ui/                 # interface (tema, páginas e componentes)
│   ├── theme.py        # identidade visual (paleta, CSS, logotipo SVG)
│   ├── home.py         # dashboard inicial
│   ├── catalogo.py     # catálogo com filtros e cards
│   ├── produto.py      # página individual do produto + histórico
│   ├── componentes.py  # cards, busca e seções reutilizáveis
│   ├── dados.py        # leituras do banco (cache) e métricas derivadas
│   └── coleta_local.py # gatilho de coleta local (só com Playwright)
├── database.py         # engine do banco (SQLite local ou PostgreSQL)
├── models.py           # tabelas pecas, historico_precos e coletas
├── servicos.py         # gravação no banco (não importa Playwright)
├── coleta.py           # orquestra a coleta (usa Playwright) + CLI
├── consultas.py        # consultas e regra de busca por termo
├── filtros.py          # filtros e ordenação (pandas)
├── atributos.py        # extrai marca, chip, socket, interface etc.
├── categorias.py       # categorias monitoradas
├── main.py             # API FastAPI (opcional)
└── scrapers/           # um módulo por loja + base comum
scripts/
└── migrar_sqlite_para_postgres.py
.github/workflows/coleta.yml
tests/
```

## Instalação

```bash
python -m venv .venv
# ative o ambiente virtual
pip install -r requirements-dev.txt
playwright install chromium
```

Instalações parciais:

| Arquivo | Para quê |
| --- | --- |
| `requirements.txt` | **Interface** (Streamlit). É o que a nuvem usa. Sem Playwright. |
| `requirements-coleta.txt` | **Coletor** (Playwright + BeautifulSoup). |
| `requirements-api.txt` | **API** (FastAPI/Uvicorn). |
| `requirements-dev.txt` | Tudo acima + pytest. |

## Coleta pela linha de comando

```powershell
python -m app.coleta --listar                     # mostra o catálogo
python -m app.coleta                              # coleta o catálogo completo
python -m app.coleta --termo "RTX 4060" --exato   # um produto específico
```

Na interface, com Playwright instalado, aparece o botão **"Atualizar preços agora"** na
página inicial. Ele sobe a coleta em um **processo separado**, sem travar a tela. O log
sai em `coleta.log`.

## API (opcional)

```powershell
python -m uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
```

## Testes

```powershell
pytest -q
```

## Variáveis de ambiente

| Variável | Para que serve | Onde é usada |
| --- | --- | --- |
| `DATABASE_URL` | URL do banco. Ausente = SQLite local. | interface, coletor e API |
| `ADMIN_TOKEN` | Protege os endpoints de coleta da API. | `app/main.py` |
| `TEST_DATABASE_URL` | Faz os testes rodarem também contra um PostgreSQL real. | `tests/test_database.py` |
| `DATABASE_URL_MIGRACAO` | Destino da migração (tem prioridade sobre `DATABASE_URL`). | `scripts/migrar_sqlite_para_postgres.py` |

O Streamlit Community Cloud entrega segredos por `st.secrets`; `app/database.py` lê das
duas formas (ambiente e secrets), então funciona nos dois mundos.

## Migrar o banco local (`precos.db`) para o PostgreSQL

O script abre o SQLite em **modo somente leitura** (o arquivo local não é alterado) e é
**repetível**: rodar de novo não duplica dados — casa a peça pela `link` e o histórico por
`(peça, data, preço)`.

```powershell
# 1. Aponte o destino (a URL NÃO vai na linha de comando, para não ficar no histórico)
$env:DATABASE_URL_MIGRACAO = "postgresql://usuario:senha@host/banco?sslmode=require"

# 2. Simulação: mostra o que seria feito, sem gravar
python scripts\migrar_sqlite_para_postgres.py

# 3. Se estiver tudo certo, grave
python scripts\migrar_sqlite_para_postgres.py --executar
```

Recomendação: faça uma cópia de segurança manual do `precos.db` antes. O script não faz
backup nem remove nada.

## Confiabilidade dos coletores

- **Pausas aleatórias** de 4 a 9 segundos entre requisições e User-Agent real.
- **Timeout** por página e **tentativa automática** (2 tentativas) antes de desistir.
- **Detecção de bloqueio** (página de captcha/verificação) que interrompe a loja.
- **Preço inválido é ignorado** (nunca grava zero ou vazio).
- **Prevenção de duplicados** pela `link` da oferta e pelo `(peça, data, preço)` no
  histórico.
- **Preços antigos são preservados**: se uma loja falhar, o último preço válido continua
  no banco e o dashboard sinaliza "há N dias sem atualizar".

## Diagnóstico

| Sintoma | Causa provável / o que fazer |
| --- | --- |
| Tela mostra "Banco: SQLite local" quando deveria ser a nuvem | `DATABASE_URL` não chegou ao processo. Confira o Secret (Streamlit: em `st.secrets`). |
| `ModuleNotFoundError: psycopg` | Falta o driver: `pip install "psycopg[binary]"`. |
| `no such table: pecas` | O banco está vazio e o processo não criou as tabelas. Rode uma coleta ou a migração. |
| Coleta falha com `OperationalError` | Confira a URL (host/usuário/senha) e se o banco aceita conexões externas. |
| Botão de coleta não aparece | Playwright não está instalado — comportamento esperado na nuvem. |
| Loja retorna 0 itens | O site mudou o HTML (seletores) ou bloqueou o acesso. Veja o log (`coleta.log`). |
| Preços não atualizam na tela | A interface tem cache de 60 s. Espere ou recarregue. |
| "Sem quedas registradas" | Normal quando não há preço coletado há mais de 7 dias. Rode a coleta. |

## Segurança e termos de uso

- Os endpoints `POST /atualizacoes` e `GET /atualizacoes/ultima` **exigem** o cabeçalho
  `Authorization: Bearer <ADMIN_TOKEN>`. Sem `ADMIN_TOKEN` definido, respondem 503.
- `GET /pecas*` é leitura pública e não expõe segredo algum.
- O coletor respeita os sites: pausas aleatórias, User-Agent real e **para** a loja quando
  detecta bloqueio.
- Confira os **termos de uso de cada loja** antes de tornar a coleta pública ou aumentar o
  volume. Scraping automatizado pode ser restrito por contrato, mesmo de dados públicos.
