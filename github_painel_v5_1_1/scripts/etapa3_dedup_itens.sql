-- Dedup de itens por id_compra_item, mantendo maior data_atualizacao, desempate por valido_de
COPY (
  WITH base AS (
    SELECT *
    FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/parquet/itens.parquet')
    WHERE is_current = true
  ),
  ranked AS (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY id_compra_item
        ORDER BY TRY_CAST(data_atualizacao AS TIMESTAMP) DESC NULLS LAST,
                 TRY_CAST(valido_de AS TIMESTAMP) DESC NULLS LAST
      ) AS rn
    FROM base
  )
  SELECT * EXCLUDE (rn) FROM ranked WHERE rn = 1
) TO 'C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/itens_dedup.parquet' (FORMAT PARQUET);

SELECT count(*) AS n_itens_dedup FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/itens_dedup.parquet');
