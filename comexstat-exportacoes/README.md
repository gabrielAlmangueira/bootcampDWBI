# Como mudou a composição das exportações brasileiras?

Pipeline demonstrativo que extrai estatísticas mensais de exportação do ComexStat/MDIC, transforma os dados em Python, carrega um modelo dimensional em PostgreSQL local e disponibiliza os indicadores para análise no Power BI.

## Escopo

- Fluxo: exportações brasileiras (`export`).
- Período: janeiro de 2022 a dezembro de 2025.
- Detalhamento: mês e seção de produto.
- Medidas: valor US$ FOB e quilograma líquido.
- Granularidade da fato: uma linha por mês e seção.
- Fonte oficial: [API ComexStat](https://api-comexstat.mdic.gov.br/docs/doc.yaml).

O projeto responde quais seções alteraram sua participação no valor exportado e em quais períodos. Ele descreve associações e variações temporais, não causalidade.

Na consulta validada em 15/10/2026, o recorte retornou 1.008 combinações únicas de mês-seção (48 meses e 21 seções). Como ponto de partida para a narrativa, o FOB anual passou de US$ 334,14 bi em 2022 para US$ 348,28 bi em 2025 (+4,23%); a seção “Animais vivos e produtos do reino animal” ganhou cerca de 1,72 ponto percentual de participação, enquanto “Metais comuns e suas obras” perdeu cerca de 1,44 p.p. Esses resultados precisam ser revalidados se a fonte revisar os dados. Veja as agregações e ressalvas em [métricas e storytelling](docs/metricas_e_storytelling.md).

## Arquitetura

```text
ComexStat API → JSON bruto + metadados → ETL Python → PostgreSQL dimensional → Power BI
```

- `src/comex_pipeline/`: configuração, extração, transformação, validação, carga e CLI.
- `sql/`: DDL do DW versionado.
- `data/raw/`: respostas e metadados locais; não versionados.
- `notebooks/`: EDA conectada ao DW.
- `powerbi/`: local para o `.pbix`.
- `docs/`: arquitetura, dicionário, qualidade, métricas e roteiro.

## Pré-requisitos

- Python 3.10 ou superior.
- PostgreSQL local instalado e em execução, com um banco vazio chamado `comex_dw` (ou outro nome configurado em `PG_DSN`).
- Power BI Desktop com o conector PostgreSQL disponível.

## Instalação e configuração (PowerShell)

```powershell
cd .\comexstat-exportacoes
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

Edite `.env` com a conexão local, por exemplo:

```text
PG_DSN=postgresql://postgres:SUA_SENHA@localhost:5432/comex_dw
```

Não versionar o `.env`. O pipeline não cria o banco PostgreSQL, mas cria suas tabelas na primeira carga.

## Executar o pipeline

```powershell
$env:PYTHONPATH = "src"
python -m comex_pipeline.cli run
```

Comandos isolados:

```powershell
python -m comex_pipeline.cli extract
python -m comex_pipeline.cli load --raw-file .\data\raw\CAMINHO_DO_JSON.json
```

Para rodar um período diferente, ajuste `COMEXSTAT_START` e `COMEXSTAT_END` no `.env`. O pipeline valida formato e ordem. A reexecução faz upsert da granularidade mês-seção; não duplica fatos.

## Testes

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Os testes usam respostas simuladas e não consultam a rede nem precisam de PostgreSQL. Para validar o carregamento de ponta a ponta, execute o comando `run` com PostgreSQL disponível e compare as consultas em `sql/002_quality_checks.sql` com os resultados do notebook.

## Próximos passos depois da carga

A carga local foi executada em 16/10/2026. A verificação encontrou 1.008 fatos, 21 seções, 1.461 dias de calendário, nenhuma chave repetida e nenhuma FK inválida. O notebook também foi executado contra o DW: 48 meses, sem nulos e sem duplicatas na granularidade mês-seção.

1. **Executar a EDA na interface:** abra a pasta do projeto no VS Code, abra `notebooks/01_analise_exploratoria.ipynb`, selecione o interpretador Python do ambiente que tem as dependências instaladas e escolha **Run All**. O `.env` deve estar ao lado do README e conter o mesmo `PG_DSN`; não copie credenciais para as células.
2. **Conectar o Power BI Desktop:** escolha **Obter dados > Banco de dados PostgreSQL**. Servidor: `localhost:5432`; banco: `comex_dw`; modo sugerido: Importar. Na primeira conexão, digite as credenciais do mesmo usuário PostgreSQL utilizado no `.env` na janela do Power BI (não as coloque no PBIX nem no Git).
3. Selecione as tabelas `dim_tempo`, `dim_secao_produto` e `fato_exportacao_mensal`. Relacione cada dimensão (1) à fato (*), por `tempo_id` e `secao_id`; mantenha filtro unidirecional dimensão → fato. Marque `dim_tempo` como tabela de datas pela coluna `data_calendario` e ordene `nome_mes` por `numero_mes`.
4. Crie as medidas DAX e visuais de referência em [métricas e storytelling](docs/metricas_e_storytelling.md). Confira o total anual com `sql/002_quality_checks.sql`, salve como `powerbi/exportacoes_brasil.pbix` e feche/reabra uma vez para validar que o relatório abre.

## Explorar no Power BI

Conecte o Power BI Desktop ao PostgreSQL local e selecione `dim_tempo`, `dim_secao_produto` e `fato_exportacao_mensal`. Crie/valide os relacionamentos com as chaves do modelo; medidas DAX e visuais sugeridos estão em [métricas e storytelling](docs/metricas_e_storytelling.md). Consulte [arquitetura](docs/arquitetura.md) e [qualidade e transformações](docs/qualidade_e_transformacoes.md) para configuração e decisões.

Na apresentação, demonstre extração e rastreabilidade, granularidade e esquema, validação dos totais, EDA e a pergunta respondida pelo dashboard.

## Notas de interpretação

- `valor_fob_usd` é expresso em dólares dos Estados Unidos FOB, conforme a métrica oficial.
- `quilograma_liquido` é quilograma líquido.
- FOB/kg pode ser analisado como razão descritiva agregada, não como preço unitário comparável.
- O intervalo é histórico e fixo para facilitar a reprodução; `/general/dates/updated` é registrado como metadado da execução.
