-- Dedup de compras.parquet (mesma chave/regra do etapa2) para recuperar colunas extras
-- nao presentes em etapa2_compras_auditadas.parquet
COPY (
  WITH base AS (
    SELECT *
    FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/parquet/compras.parquet')
    WHERE is_current = true
  ),
  ranked AS (
    SELECT *,
      ROW_NUMBER() OVER (
        PARTITION BY id_compra
        ORDER BY TRY_CAST(data_atualizacao AS TIMESTAMP) DESC NULLS LAST,
                 TRY_CAST(data_inclusao AS TIMESTAMP) DESC NULLS LAST,
                 TRY_CAST(valido_de AS TIMESTAMP) DESC NULLS LAST
      ) AS rn
    FROM base
  )
  SELECT
    id_compra, amparo_legal_nome, amparo_legal_descricao, amparo_legal_codigo,
    srp, informacao_complementar, tipo_instrumento_convocatorio_nome,
    orcamento_sigiloso_codigo, orcamento_sigiloso_descricao,
    orgao_entidade_cnpj, orgao_entidade_razao_social, data_publicacao_pncp,
    contratacao_excluida, existe_resultado, situacao_compra_nome,
    valor_total_estimado, valor_total_homologado
  FROM ranked WHERE rn = 1
) TO 'C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/compras_extra_dedup.parquet' (FORMAT PARQUET);

SELECT count(*) AS n_compras_extra FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/compras_extra_dedup.parquet');
