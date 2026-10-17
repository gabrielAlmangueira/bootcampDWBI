# Dicionário de dados

## `dim_tempo`

| Coluna | Tipo | Significado |
|---|---|---|
| `tempo_id` | integer | Chave substituta do dia |
| `data_calendario` | date | Data contínua; a fato mensal se relaciona ao primeiro dia do mês |
| `ano` | smallint | Ano calendário |
| `numero_mes` | smallint | Mês de 1 a 12 |
| `nome_mes` | varchar | Nome do mês em português |
| `trimestre` | smallint | Trimestre calendário de 1 a 4 |
| `numero_dia` | smallint | Dia do mês |
| `dia_semana_numero` | smallint | Dia da semana ISO (1=segunda, 7=domingo) |

## `dim_secao_produto`

| Coluna | Tipo | Significado |
|---|---|---|
| `secao_id` | integer | Chave substituta |
| `codigo_secao` | varchar | Código da seção informado pelo ComexStat (ex.: algarismo romano) |
| `nome_secao` | text | Descrição da seção informada pela fonte |

## `fato_exportacao_mensal`

| Coluna | Tipo | Significado |
|---|---|---|
| `tempo_id` | integer | FK para `dim_tempo` |
| `secao_id` | integer | FK para `dim_secao_produto` |
| `valor_fob_usd` | numeric(20,2) | Métrica oficial `metricFOB`, dólares dos EUA FOB |
| `quilograma_liquido` | numeric(24,3) | Métrica oficial `metricKG`, quilograma líquido |

**Granularidade:** uma linha por mês e seção de produto. A chave primária é o par `(tempo_id, secao_id)`. As duas medidas são agregáveis por soma dentro desse recorte.

## `etl_execucao`

| Coluna | Tipo | Significado |
|---|---|---|
| `execucao_id` | bigint | Identificador da execução que carregou |
| `fonte_atualizada_em` | date | Data de atualização retornada pela API |
| `periodo_inicio` / `periodo_fim` | date | Primeiro e último dia do intervalo de meses consultado |
| `arquivo_bruto` | text | Caminho local para JSON que originou a carga |
| `linhas_carregadas` | integer | Linhas transformadas e submetidas à carga |
| `executado_em` | timestamptz | Instante da gravação no DW |

## Campos do payload de origem

| Campo API | Campo interno | Conversão |
|---|---|---|
| `year`, `monthNumber` | `data_calendario`, `ano`, `numero_mes` | Inteiros validados; a data da fato é o primeiro dia do mês |
| `coNcmSecrom` | `codigo_secao` | Texto preservado |
| `section` | `nome_secao` | Texto sem espaços externos |
| `metricFOB` | `valor_fob_usd` | Decimal não negativo |
| `metricKG` | `quilograma_liquido` | Decimal não negativo |

As definições das métricas vêm do [endpoint oficial do MDIC](https://api-comexstat.mdic.gov.br/general/metrics?language=pt). Não converter para reais nem assumir um câmbio implícito.
