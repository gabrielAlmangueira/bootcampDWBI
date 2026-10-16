-- Cobertura e unicidade da granularidade da fato.
SELECT COUNT(*) AS linhas_fato,
       COUNT(DISTINCT (tempo_id, secao_id)) AS chaves_unicas
FROM fato_exportacao_mensal;

-- Intervalo temporal, seções e medidas agregadas.
SELECT MIN(t.data_calendario) AS primeira_data_fato,
       MAX(t.data_calendario) AS ultima_data_fato,
       COUNT(DISTINCT s.codigo_secao) AS secoes,
       SUM(f.valor_fob_usd) AS total_fob_usd,
       SUM(f.quilograma_liquido) AS total_kg
FROM fato_exportacao_mensal f
JOIN dim_tempo t USING (tempo_id)
JOIN dim_secao_produto s USING (secao_id)
WHERE t.numero_dia = 1;

-- Cobertura contínua da dimensão de calendário.
SELECT COUNT(*) AS dias_calendario,
       MIN(data_calendario) AS primeira_data,
       MAX(data_calendario) AS ultima_data
FROM dim_tempo;

-- Conferir últimas cargas e rastreabilidade dos arquivos brutos.
SELECT execucao_id, fonte_atualizada_em, periodo_inicio, periodo_fim,
       arquivo_bruto, linhas_carregadas, executado_em
FROM etl_execucao
ORDER BY executado_em DESC
LIMIT 10;
