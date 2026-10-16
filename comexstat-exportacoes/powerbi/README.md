# Power BI

Crie `exportacoes_brasil.pbix` nesta pasta usando Power BI Desktop. Conecte pelo conector PostgreSQL ao mesmo host/porta/banco de `PG_DSN` e selecione `dim_tempo`, `dim_secao_produto` e `fato_exportacao_mensal`.

Configure os relacionamentos:

- `dim_tempo[tempo_id]` (1) → `fato_exportacao_mensal[tempo_id]` (*)
- `dim_secao_produto[secao_id]` (1) → `fato_exportacao_mensal[secao_id]` (*)

Marque `dim_tempo` como tabela de datas com `data_calendario`. Ordene `nome_mes` por `numero_mes`. A dimensão contém todos os dias e os fatos mensais se relacionam com o primeiro dia de cada mês.

Medidas de referência, validações, resultados e decisões de storytelling estão em `../docs/metricas_e_storytelling.md`. Confirme os totais contra PostgreSQL antes de salvar/publicar o relatório. Não salve credenciais no `.pbix`.
