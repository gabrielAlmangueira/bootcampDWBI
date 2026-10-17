# Qualidade, transformação e reconciliação

## Regras de transformação

1. Exigir envelope `success=true` e `data.list` não vazio.
2. Exigir `year`, `monthNumber`, `coNcmSecrom`, `section`, `metricFOB` e `metricKG` em cada registro.
3. Converter ano/mês em data do primeiro dia do mês; recusar mês inválido ou fora do período configurado.
4. Converter métricas para `Decimal`; recusar texto não numérico, valor infinito/NaN ou número negativo. Valores ausentes não são convertidos para zero.
5. Preservar código e descrição da seção. Divergência de descrição para o mesmo código dentro do lote falha para inspeção.
6. A chave candidata da fato é `(data_calendario do primeiro dia do mês, codigo_secao)`. Qualquer duplicata interrompe a execução; não agregar silenciosamente.
7. Todos os meses solicitados precisam estar presentes no conjunto. A ausência pode representar falha ou cobertura inesperada e deve ser investigada.

## Controles na origem, transformação e DW

- HTTP: checar código de status, resposta JSON e flag `success`.
- Esquema: campos obrigatórios e tipos de container validados antes da carga.
- Domínio: período mensal válido, métricas finitas e não negativas, códigos/textos de seção não vazios.
- Chaves: unicidade da seção na dimensão, unicidade do mês na dimensão, PK/FK e chave composta na fato.
- Reexecução: `ON CONFLICT` atualiza dimensão e fato; validar que contagem da chave da fato não aumenta após reprocessar o mesmo lote.
- Reconciliação: comparar número de registros únicos e somas FOB/peso do raw transformado com a fato do intervalo; pequenas diferenças de escala devem ser investigadas, não toleradas sem regra.

Consulta sugerida após a carga:

```sql
SELECT COUNT(*) AS linhas,
       COUNT(DISTINCT (t.data_calendario, s.codigo_secao)) AS chaves,
       SUM(f.valor_fob_usd) AS total_fob_usd,
       SUM(f.quilograma_liquido) AS total_kg
FROM fato_exportacao_mensal f
JOIN dim_tempo t USING (tempo_id)
JOIN dim_secao_produto s USING (secao_id)
WHERE t.numero_dia = 1;
```

## Outliers e tratamento analítico

No notebook, inspecionar distribuição, percentis e série temporal por seção. Marcar extremos como candidatos à investigação, comparar com raw e confirmar unidade/chave antes de classificá-los como erro. Não remover valores válidos para melhorar visualização; usar escalas ou recortes visuais quando necessário. Não usar FOB/kg como preço, pois a mistura de mercadorias em cada seção muda ao longo do tempo.

## Resultado esperado e resposta a falhas

Um teste de qualidade passa apenas se esquema, cobertura mensal, chaves e domínios passam. Erro de API, coluna ausente, duplicata ou chave inválida bloqueia a carga. Uma nova extração deve produzir novo arquivo bruto para preservar a trilha de auditoria; corrigir entrada ou regra e reexecutar com logs visíveis.
