-- Base limpa: junta etapa2_compras_auditadas + colunas extras de compras + auditoria manual proposta
-- Aplica regras de limpeza de valor conforme validacao_proposta

CREATE OR REPLACE TABLE aud AS
SELECT id_compra, validacao_proposta, justificativa
FROM read_csv_auto('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/auditoria_revisao_manual_proposta.csv', types={'id_compra':'VARCHAR'});

CREATE OR REPLACE TABLE e2 AS
SELECT * FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/etapa2_compras_auditadas.parquet');

CREATE OR REPLACE TABLE extra AS
SELECT * FROM read_parquet('C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/compras_extra_dedup.parquet');

CREATE OR REPLACE TABLE joined AS
SELECT
  e2.*,
  extra.amparo_legal_nome, extra.amparo_legal_descricao, extra.amparo_legal_codigo,
  extra.srp, extra.informacao_complementar, extra.tipo_instrumento_convocatorio_nome,
  extra.orcamento_sigiloso_codigo, extra.orcamento_sigiloso_descricao,
  extra.orgao_entidade_cnpj, extra.orgao_entidade_razao_social, extra.data_publicacao_pncp,
  extra.existe_resultado, extra.situacao_compra_nome,
  aud.validacao_proposta, aud.justificativa
FROM e2
LEFT JOIN extra ON e2.id_compra = extra.id_compra
LEFT JOIN aud ON e2.id_compra = aud.id_compra;

-- Regra duplicacao_estimado: manter valor_estimado apenas na 1a ocorrencia por (ano, orgao, valor_estimado)
-- entre as compras marcadas duplicacao_estimado; demais ocorrencias mesmo valor/ano/orgao tem valor_estimado_limpo = NULL
CREATE OR REPLACE TABLE ranked AS
SELECT *,
  CASE WHEN validacao_proposta = 'duplicacao_estimado' THEN
    ROW_NUMBER() OVER (PARTITION BY validacao_proposta, ano, orgao, valor_estimado ORDER BY id_compra)
  ELSE NULL END AS dup_rank
FROM joined;

CREATE OR REPLACE TABLE base_limpa AS
SELECT
  *,
  CASE
    WHEN validacao_proposta = 'erro_provavel' THEN NULL
    WHEN validacao_proposta = 'erro_estimado' THEN NULL
    WHEN validacao_proposta = 'duplicacao_estimado' AND dup_rank > 1 THEN NULL
    ELSE valor_estimado
  END AS valor_estimado_limpo,
  CASE
    WHEN validacao_proposta = 'erro_provavel' THEN NULL
    ELSE valor_homologado
  END AS valor_homologado_limpo
FROM ranked;

COPY (SELECT * EXCLUDE (dup_rank) FROM base_limpa)
  TO 'C:/Users/mabel/OneDrive/Desktop/colibri_baixado_duckdb/Processado/base_limpa.parquet' (FORMAT PARQUET);

SELECT count(*) AS n, count(validacao_proposta) AS n_auditadas FROM base_limpa;
SELECT validacao_proposta, count(*), sum(valor_estimado), sum(valor_estimado_limpo), sum(valor_homologado), sum(valor_homologado_limpo)
FROM base_limpa GROUP BY 1 ORDER BY 1;
