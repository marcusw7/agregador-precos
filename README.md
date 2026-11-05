# PromoTracker

> Comparação e acompanhamento de preços de hardware, com histórico e detecção de quedas.

## Sobre

O **PromoTracker** monitora preços de **GPU, CPU, placa-mãe, memória RAM, SSD, monitores e
cadeiras** em cinco lojas brasileiras — KaBuM!, Pichau, Terabyte, Patoloco e Amazon —
mantendo o histórico completo de cada oferta para que você acompanhe a evolução dos preços
e encontre o melhor momento para comprar.

Acesse em: <https://promotracker.streamlit.app/>

## Funcionalidades

- **Dashboard** — visão geral com estatísticas do monitoramento, status da coleta
  automática, maiores quedas de preço e melhores ofertas.
- **Catálogo com filtros** — categoria, fabricante, loja, faixa de preço e características
  do hardware (chip, socket, capacidade, resolução, taxa de atualização, etc.).
- **Página do produto** — especificações, histórico de preços (7/30/90 dias ou completo),
  menor/média/maior e comparação do mesmo produto entre lojas.
- **Atualização automática** — coleta a cada 6 horas com registro de cada execução.
- **Dados honestos** — variações e "menor preço histórico" só aparecem quando há dados
  reais suficientes; nada é inventado.

## Arquitetura

```
GitHub Actions (coleta)  ──►  PostgreSQL  ◄──  Streamlit (interface)
   Playwright + Chromium         dados          sem navegador
```

Três partes independentes:

| Parte | Responsabilidade |
| --- | --- |
| **Interface** (Streamlit) | Apresenta os preços salvos no banco. Não usa navegador. |
| **Coleta** (Playwright) | Varre as lojas e grava os preços, rodando de forma agendada. |
| **Banco de dados** | SQLite (local) ou PostgreSQL (produção), definido por `DATABASE_URL`. |

## Tecnologias

- **Python 3.12+**
- **Streamlit** — interface
- **Playwright** + **BeautifulSoup** — coleta de preços
- **SQLAlchemy** + **SQLite/PostgreSQL** — persistência
- **FastAPI** — API opcional
- **GitHub Actions** — agendamento da coleta

## Como executar

> Requer Python 3.12 ou superior. Node.js não é necessário.

```bash
# 1. Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate        # Linux/macOS
# .venv\Scripts\Activate.ps1     # Windows (PowerShell)

# 2. Instale as dependências
pip install -r requirements-dev.txt

# 3. Instale o navegador usado pela coleta
playwright install chromium

# 4. Execute a interface (usa SQLite local automaticamente)
streamlit run app/dashboard.py
```

A interface está disponível em <http://localhost:8501>.

## Implantação

### Streamlit Community Cloud (interface)

1. Conecte o repositório em <https://share.streamlit.io>.
2. Escolha o arquivo principal **`app/dashboard.py`**.
3. Em **Advanced settings → Secrets**, defina a URL do banco (substituindo pelos seus dados):

   ```toml
   DATABASE_URL = "postgresql://usuario:senha@host/banco?sslmode=require"
   ```

### GitHub Actions (coleta automática)

A coleta roda **a cada 6 horas** e grava direto no banco em produção.

1. Em **Settings → Secrets and variables → Actions**, adicione o secret `DATABASE_URL`
   (a mesma URL PostgreSQL).
2. Para testar, use **Actions → Coleta de preços → Run workflow**.

## Configuração

| Variável | Descrição |
| --- | --- |
| `DATABASE_URL` | URL do banco. Ausente = SQLite local. |
| `ADMIN_TOKEN` | Protege os endpoints administrativos da API. |

Segredos nunca devem ser versionados: use variáveis de ambiente (local) e **Secrets**
(GitHub / Streamlit).

## Privacidade e uso responsável

- O PromoTracker compara apenas **preços públicos** exibidos pelas lojas.
- A coleta respeita os sites (pausas entre requisições e respeito a bloqueios) e não
  armazena dados pessoais de usuários.

## Contribuindo

Contribuições são bem-vindas. Abra uma *issue* para relatar problemas ou sugerir melhorias.

---

Para detalhes internos de desenvolvimento (estrutura do projeto, migração de banco,
execução da coleta pela linha de comando e diagnóstico de problemas), consulte
[docs/DESENVOLVIMENTO.md](docs/DESENVOLVIMENTO.md).
