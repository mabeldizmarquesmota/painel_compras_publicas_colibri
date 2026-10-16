-- Dedup de resultados: chave (id_compra_item, sequencial_resultado, ni_fornecedor)
-- mantendo maior data efetiva entre varias colunas de data (mesma regra do METODOLOGIA.md)
-- Filtro: sem cancelamento (data_cancelamento nulo ou vazio)
COPY (
  WITH base AS (
    SELECT *,
      GREATEST(
        COALESCE(TRY_CAST(data_atualizacao AS TIMESTAMP), TIMESTAMP '1900-01-01'),
        COALESCE(TRY_CAST(data_atualizacao_pncp AS TIMESTAMP), TIMESTAMP '1900-01-01'),
        COALESCE(TRY_CAST(valido_de AS TIMESTAMP), TIMESTAMP '1900-01-01'),
        COALESCE(TRY_CAST(data_resultado_pncp AS TIMESTAMP), TIMESTAMP '1900-01-01'),
        COALESCE(TRY_CAST(data_resultado AS TIMESTAMP), TIMESTAMP '1900-01-01'),
        COALESCE(TRY_CAST(data_inclusao_pncp AS TIMESTAMP), TIMESTAMP '1900-01-01'),
        COALESCE(TRY_CAST(data_inclusao AS TIMESTAMP), TIMESTAMP '1900-01-01')
      ) AS data_efetiva
    FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/parquet/resultados.parquet')
    WHERE is_current = true
      AND (data_cancelamento IS NULL OR trim(data_cancelamento) = '')
  ),
  ranked AS (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY id_compra_item, sequencial_resultado, ni_fornecedor
        ORDER BY data_efetiva DESC
      ) AS rn
    FROM base
  )
  SELECT * EXCLUDE (rn, data_efetiva) FROM ranked WHERE rn = 1
) TO 'C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/resultados_dedup.parquet' (FORMAT PARQUET);

SELECT count(*) AS n_resultados_dedup FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/resultados_dedup.parquet');
