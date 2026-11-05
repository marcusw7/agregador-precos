# PromoTracker

Plataforma de **comparação e acompanhamento de preços de hardware**. Monitora **GPU, CPU,
placa-mãe, memória RAM, SSD, monitores e cadeiras** em cinco lojas brasileiras (KaBuM!,
Pichau, Terabyte, Patoloco e Amazon) e mantém o **histórico de preços** para você
acompanhar a evolução e identificar as melhores oportunidades.

## Funcionalidades

- **Dashboard** com estatísticas do monitoramento, status da coleta automática, maiores
  quedas de preço, melhores ofertas e produtos atualizados recentemente.
- **Catálogo** com filtros (categoria, fabricante, loja, faixa de preço, atributos) e
  ordenação (menor preço, maior queda em 7 dias, mais recentes).
- **Página do produto** com especificações, histórico de preços (7/30/90 dias/completo),
  menor/maior/média e comparação do mesmo produto entre lojas.
- **Coleta automática** a cada 6 horas via GitHub Actions, com registro de status e
  contadores de cada execução.
- **Histórico** persistente de preços por oferta (nunca inventa dados: sem registro, sem
  variação).

## Arquitetura

```
GitHub Actions (coletor)  ──►  PostgreSQL (Neon/Supabase)  ◄──  Streamlit (interface)
   Playwright + Chromium              dados                    sem navegador
```

Três peças independentes, que podem rodar em ambientes diferentes:

| Peça | Arquivo de entrada | Precisa de Playwright? |
| --- | --- | --- |
| Interface | `app/dashboard.py` | **Não** |
| Coletor | `app/coleta.py` (`python -m app.coleta`) | **Sim** |
| API (opcional) | `app/main.py` | Só para disparar coleta |

O banco é escolhido pela variável `DATABASE_URL`: sem ela, usa o **SQLite local**
(`precos.db`). Com ela apontando para PostgreSQL, usa o banco da nuvem.

## Estrutura

```
app/
├── dashboard.py        # entrada do Streamlit (navegação entre páginas)
├── ui/                 # interface PromoTracker (tema, páginas e componentes)
│   ├── theme.py        # identidade visual (paleta, CSS, logotipo SVG)
│   ├── home.py         # dashboard inicial
│   ├── catalogo.py     # catálogo com filtros e cards
│   ├── produto.py      # página individual do produto + histórico
│   ├── componentes.py  # cards, busca e seções reutilizáveis
│   ├── dados.py        # leituras do banco (cache) e métricas derivadas
│   └── coleta_local.py # gatilho de coleta local (só com Playwright)
├── database.py        # engine do banco (SQLite local ou PostgreSQL por DATABASE_URL)
├── models.py          # tabelas pecas, historico_precos e coletas
├── servicos.py        # gravação no banco (não importa Playwright)
├── coleta.py          # orquestra a coleta (usa Playwright) + linha de comando
├── consultas.py       # consultas e regra de busca por termo
├── filtros.py         # filtros e ordenação (pandas)
├── atributos.py       # extrai marca, chip, socket, interface etc. do título
├── categorias.py      # categorias monitoradas
├── main.py            # API FastAPI (opcional)
└── scrapers/          # um módulo por loja + base comum
scripts/
└── migrar_sqlite_para_postgres.py
.github/workflows/coleta.yml
tests/
```

## Requisitos

- Python 3.12 ou superior (testado com 3.14 no Windows).
- Node.js **não** é necessário.

## Execução local no Windows

```powershell
cd C:\Users\zynzg\agregador-precos

# 1. Ambiente virtual
python -m venv .venv
.\.venv\Scripts\Activate.ps1
# se o PowerShell bloquear: Set-ExecutionPolicy -Scope CurrentUser RemoteSigned

# 2. Instalação completa (interface + coleta + API + testes)
pip install -r requirements-dev.txt

# 3. Navegador usado pelo coletor
playwright install chromium

# 4. Interface (usa o SQLite local automaticamente)
streamlit run app/dashboard.py
```

Instalações parciais, se você quiser só uma parte:

| Arquivo | Para quê |
| --- | --- |
| `requirements.txt` | **Interface** (Streamlit). É o que a nuvem usa. Sem Playwright. |
| `requirements-coleta.txt` | **Coletor** (Playwright + BeautifulSoup). |
| `requirements-api.txt` | **API** (FastAPI/Uvicorn). |
| `requirements-dev.txt` | Tudo acima + pytest. |

### Coleta pela linha de comando

```powershell
python -m app.coleta --listar                     # mostra o catálogo
python -m app.coleta                              # coleta o catálogo completo
python -m app.coleta --termo "RTX 4060" --exato   # um produto específico
```

Na interface, com Playwright instalado, aparece o botão **"Atualizar preços agora"** na
página inicial. Ele sobe a coleta em um **processo separado**, sem travar a tela. O log
sai em `coleta.log`.

### API (opcional)

```powershell
python -m uvicorn app.main:app --reload     # http://127.0.0.1:8000/docs
```

### Testes

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

**Nunca** coloque a URL ou o token no código, no README ou em commits. Use variáveis de
ambiente (local) e Secrets (GitHub / Streamlit).

O Streamlit Community Cloud entrega segredos por `st.secrets`; `app/database.py` lê das
duas formas (ambiente e secrets), então funciona nos dois mundos.

## Publicar a interface no Streamlit Community Cloud

1. Suba o projeto para um repositório **privado** no GitHub (o `.gitignore` já deixa
   `precos.db`, `.env` e `coleta.log` de fora).
2. Acesse <https://share.streamlit.io> e faça login com o GitHub.
3. **New app** → escolha repositório, branch (`main`) e o arquivo principal:
   **`app/dashboard.py`**.
4. Em **Advanced settings → Secrets**, cole (trocando pelos seus dados):

   ```toml
   DATABASE_URL = "postgresql://usuario:senha@host/banco?sslmode=require"
   ```

5. **Deploy**. A instalação usará o `requirements.txt` da raiz do repositório.

Observações:
- Não crie um `requirements.txt` dentro de `app/`: a plataforma procura primeiro na pasta
  do arquivo principal e depois na raiz. O da raiz já é o correto (sem Playwright).
- O tema escuro é definido em `.streamlit/config.toml` e complementado pelo CSS em
  `app/ui/theme.py`.
- App do plano gratuito "dorme" após inatividade; a próxima visita reativa.

## Coleta automática (GitHub Actions)

O workflow está em `.github/workflows/coleta.yml` e roda **a cada 6 horas**
(`cron: "0 */6 * * *"`), além de permitir execução manual.

1. No GitHub: **Settings → Secrets and variables → Actions → New repository secret**.
2. Nome: `DATABASE_URL`. Valor: a mesma URL PostgreSQL (com `?sslmode=require`).
3. **Actions → Coleta de precos → Run workflow** para testar manualmente.
4. Para mudar a frequência, edite o bloco `schedule` do workflow. Evite intervalos muito
   curtos para não sobrecarregar os sites das lojas.

Cada execução grava uma linha na tabela `coletas` (status, horários, itens novos,
atualizados e erros), exibida no dashboard como **"Status da coleta automática"**.

O workflow tem `concurrency: coleta-precos` (duas coletas não rodam ao mesmo tempo),
`timeout-minutes: 45` e falha com mensagem clara se o segredo não existir. Ele **não**
comita nada: só grava no banco externo.

## Confiabilidade dos coletores

- **Pausas aleatórias** de 4 a 9 segundos entre requisições e User-Agent real.
- **Timeout** por página e **tentativa automática** (2 tentativas) antes de desistir.
- **Detecção de bloqueio** (página de captcha/verificação) que interrompe a loja.
- **Preço inválido é ignorado** (nunca grava zero ou vazio): ofertas sem preço à vista
  não entram no banco.
- **Prevenção de duplicados** pela `link` da oferta e pelo `(peça, data, preço)` no
  histórico.
- **Preços antigos são preservados**: se uma loja falhar, o último preço válido continua
  no banco e o dashboard sinaliza "há N dias sem atualizar".

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

Recomendação: faça uma cópia de segurança manual do `precos.db` antes (copiar o arquivo
para outro nome). O script não faz backup nem remove nada.

## Diagnóstico

| Sintoma | Causa provável / o que fazer |
| --- | --- |
| Tela mostra "Banco: SQLite local" quando deveria ser a nuvem | `DATABASE_URL` não chegou ao processo. Confira o Secret (Streamlit: em `st.secrets`) e se o nome está exatamente `DATABASE_URL`. |
| `ModuleNotFoundError: psycopg` | Falta o driver: `pip install "psycopg[binary]"`. |
| `no such table: pecas` | O banco está vazio e o processo não criou as tabelas. Interface, API e coletor já chamam `create_all`; rode uma coleta ou a migração. |
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
  detecta bloqueio. Não aumente a frequência sem necessidade.
- Confira os **termos de uso de cada loja** antes de tornar a coleta pública ou aumentar o
  volume. Scraping automatizado pode ser restrito por contrato, mesmo de dados públicos.

## Higiene do repositório

`precos.db` **não** deve ser removido: é o seu banco local. Ele já está no `.gitignore`.
