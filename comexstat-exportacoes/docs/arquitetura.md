# Arquitetura do pipeline

## Fonte e contrato

O pipeline usa `POST https://api-comexstat.mdic.gov.br/general`, documentado pela [especificação oficial OpenAPI](https://api-comexstat.mdic.gov.br/docs/doc.yaml). O pedido seleciona exportação, detalhe mensal, intervalo 2022-01 a 2025-12, seção e métricas `metricFOB`/`metricKG`. O campo de código de seção observado na resposta é `coNcmSecrom`; `section` contém o nome. Antes da consulta, é lido `/general/dates/updated`.

Uma extração de verificação para janeiro e fevereiro de 2022 retornou 42 registros com campos `coNcmSecrom`, `year`, `monthNumber`, `section`, `metricFOB` e `metricKG`. A consulta do escopo completo retornou 1.008 linhas para 48 meses, todas únicas na chave mês-seção. As métricas oficiais são “Valor US$ FOB” e “Quilograma Líquido” conforme o [endpoint de métricas](https://api-comexstat.mdic.gov.br/general/metrics?language=pt). A ordem retornada pela API não é assumida.

## Camadas

1. **Origem:** API pública do MDIC, com parâmetros registrados.
2. **Raw:** resposta JSON intacta em `data/raw/` e sidecar `.metadata.json` com endpoint, parâmetros, atualização da fonte, hora UTC de extração e contagem.
3. **Transformação:** normalização de nomes e tipos, construção da data mensal e verificação da chave mês-seção.
4. **DW:** PostgreSQL com dimensões conformadas a esta fato e tabela de auditoria da execução.
5. **Consumo:** notebook de EDA e Power BI conectado ao esquema dimensional.

## Modelo dimensional e granularidade

| Tabela | Função | Chave natural / relacionamento |
|---|---|---|
| `dim_tempo` | Calendário diário contínuo com atributos de mês, ano, trimestre e dia da semana | `data_calendario` única; `tempo_id` substituta |
| `dim_secao_produto` | Código e descrição da seção | `codigo_secao` única; `secao_id` substituta |
| `fato_exportacao_mensal` | Medidas de exportação | Uma linha por `(tempo_id, secao_id)` |
| `etl_execucao` | Auditoria da carga | Execução, fonte atualizada, intervalo, arquivo e quantidade |

As duas dimensões permitem filtrar e agrupar a fato sem repetir os textos descritivos em cada linha. A fato mensal aponta para o primeiro dia do mês na dimensão de calendário contínua, compatível com inteligência temporal do Power BI. As medidas são aditivas no recorte escolhido: `valor_fob_usd` e `quilograma_liquido`.

## Idempotência, falhas e rastreabilidade

- Extração rejeita status HTTP malsucedido, payload sem `success`, resposta sem lista ou conjunto vazio. Tenta novamente apenas falhas transitórias de conexão e status HTTP 429/5xx, com limite e espera exponencial.
- Cada resposta bruta possui nome exclusivo por período e horário UTC; os parâmetros e a versão da atualização ficam no sidecar.
- Transformação rejeita registro com campo ausente, mês inválido, métrica não numérica, negativa ou não finita, intervalo divergente, mês sem observação, seção inconsistente ou chave repetida.
- A carga usa transação PostgreSQL e `ON CONFLICT` nas chaves naturais; carregar o mesmo recorte atualiza valores sem duplicar a chave da fato.
- Erros são propagados e exibidos como falha da execução. Não há fallback silencioso para dados antigos.

## Execução e conexão

`python -m comex_pipeline.cli run` executa o fluxo completo. `extract` guarda uma extração sem carregar. `load --raw-file ...` reaproveita JSON arquivado e sidecar. `PG_DSN` é configurado no `.env`, ignorado pelo Git. PostgreSQL precisa estar instalado, rodando e com banco criado pelo usuário. Power BI Desktop deve apontar para o mesmo host, porta e banco; confirmar driver/conector e autenticação na máquina da apresentação.

## Limites conhecidos

- Escopo deliberadamente limitado a seção, não a NCM, país ou UF.
- A fonte pode mudar ou revisar valores; preservar JSON e metadados da consulta.
- Arquivos brutos não são versionados; guardar amostra fixture pequena para testes.
- A carga atual faz upsert, mas não apaga fatos que eventualmente deixarem de aparecer numa revisão futura da API. Se for necessário refletir remoções da fonte, implementar reconciliação/substituição controlada por período como melhoria separada.
