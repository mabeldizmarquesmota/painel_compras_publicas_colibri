-- Decomposicao do valor com margem de preferencia aplicada e elegivel em duas camadas.
-- Executar depois de p0_08 (tabelas cics, itm_ncm, itm_val, escopo_itens), a partir de Processado/.
-- Entradas: resultados vigentes (res), itens_dedup.parquet, bl (base sem duplicidades), tabelas de p0_08.
-- Regras:
--   Margem aplicada: homologado dos resultados com aplicacao_margem_preferencia = true (compras nao anuladas pela
--   auditoria). Elegivel: NCM (do item ou do tradutor) coberto por prefixo de resolucao CICS vigente na data de
--   publicacao da compra (mesma regra de p0_08, agora aplicada a itens de material e de servico).
--   Marco temporal: 01/09/2024, inicio da primeira resolucao CICS do historico do Colibri.
--   Camadas do elegivel nas seis categorias: (a) so NCM informado no item; (b) NCM do item e, na falta, do tradutor.
-- Saidas: tabelas_parte0/margem_aplicada_decomposicao.csv, margem_aplicada_fora_elegibilidade_top20.csv,
--         margem_elegivel_camadas.csv, margem_aplicada_fora_elegibilidade_causa.csv

CREATE OR REPLACE TABLE mg_itens AS
SELECT n.id_compra_item, n.id_compra, n.material_ou_servico, n.ncm, n.origem_ncm,
  b.data_pub, b.ano, b.excl_h, b.amparo_legal_nome, b.modalidade,
  EXISTS (SELECT 1 FROM cics c WHERE n.ncm IS NOT NULL AND starts_with(n.ncm, c.prefixo_ncm)
          AND b.data_pub >= c.data_inicio AND (c.data_fim IS NULL OR b.data_pub <= c.data_fim)) AS elegivel,
  (n.id_compra_item IN (SELECT id_compra_item FROM escopo_itens)) AS seis_cat
FROM itm_ncm n JOIN bl b USING (id_compra);

CREATE OR REPLACE TABLE mg_aplic AS
SELECT m.*, v.v_margem, v.v
FROM mg_itens m JOIN itm_val v USING (id_compra_item)
WHERE NOT m.excl_h AND coalesce(v.v_margem, 0) > 0;

CREATE OR REPLACE TABLE mg_decomp AS
SELECT 'total' AS dimensao, 'total' AS categoria, count(*) AS itens, sum(v_margem) AS valor_margem_aplicada FROM mg_aplic
UNION ALL SELECT 'elegibilidade', CASE WHEN elegivel THEN 'dentro da elegibilidade' ELSE 'fora da elegibilidade' END, count(*), sum(v_margem) FROM mg_aplic GROUP BY 2
UNION ALL SELECT 'ano', CAST(ano AS VARCHAR), count(*), sum(v_margem) FROM mg_aplic GROUP BY 2
UNION ALL SELECT 'periodo', CASE WHEN data_pub < DATE '2024-09-01' THEN 'antes de 01/09/2024' ELSE 'a partir de 01/09/2024' END, count(*), sum(v_margem) FROM mg_aplic GROUP BY 2
UNION ALL SELECT 'origem do NCM', origem_ncm, count(*), sum(v_margem) FROM mg_aplic GROUP BY 2
UNION ALL SELECT 'tipo de item', CASE material_ou_servico WHEN 'M' THEN 'material' WHEN 'S' THEN 'servico' ELSE 'nao informado' END, count(*), sum(v_margem) FROM mg_aplic GROUP BY 2
UNION ALL SELECT 'fora da elegibilidade x periodo',
  CASE WHEN data_pub < DATE '2024-09-01' THEN 'antes de 01/09/2024' ELSE 'a partir de 01/09/2024' END
  || ' | ' || CASE material_ou_servico WHEN 'M' THEN 'material' ELSE 'servico' END || ' | ' || origem_ncm,
  count(*), sum(v_margem) FROM mg_aplic WHERE NOT elegivel GROUP BY 2
ORDER BY dimensao, valor_margem_aplicada DESC;
COPY mg_decomp TO 'tabelas_parte0/margem_aplicada_decomposicao.csv' (HEADER, DELIMITER ';');

COPY (
  SELECT row_number() OVER (ORDER BY a.v_margem DESC) AS posicao, a.id_compra_item, a.v_margem AS valor_margem_aplicada,
    a.ncm, a.origem_ncm, CASE a.material_ou_servico WHEN 'M' THEN 'material' ELSE 'servico' END AS tipo_item,
    a.data_pub AS data_publicacao, a.amparo_legal_nome, a.modalidade,
    left(regexp_replace(coalesce(i.descricao,'') || ' :: ' || coalesce(i.descricao_detalhada, ''), '\s+', ' ', 'g'), 200) AS descricao_item
  FROM mg_aplic a JOIN read_parquet('itens_dedup.parquet') i USING (id_compra_item)
  WHERE NOT a.elegivel ORDER BY a.v_margem DESC LIMIT 20
) TO 'tabelas_parte0/margem_aplicada_fora_elegibilidade_top20.csv' (HEADER, DELIMITER ';');

CREATE OR REPLACE TABLE mg_camadas AS
SELECT 'seis categorias' AS recorte,
  sum(coalesce(v.v, 0)) FILTER (WHERE m.elegivel AND m.origem_ncm = 'ncm_do_item') AS elegivel_a_ncm_do_item,
  sum(coalesce(v.v, 0)) FILTER (WHERE m.elegivel) AS elegivel_b_ncm_do_item_mais_tradutor,
  count(*) FILTER (WHERE m.elegivel AND m.origem_ncm = 'ncm_do_item') AS itens_a,
  count(*) FILTER (WHERE m.elegivel) AS itens_b,
  sum(coalesce(v.v_margem, 0)) AS margem_aplicada_seis_cat
FROM mg_itens m LEFT JOIN itm_val v USING (id_compra_item)
WHERE m.seis_cat AND NOT m.excl_h AND m.material_ou_servico = 'M';
COPY mg_camadas TO 'tabelas_parte0/margem_elegivel_camadas.csv' (HEADER, DELIMITER ';');

SELECT * FROM mg_decomp;
SELECT * FROM mg_camadas;

-- causa do valor com margem aplicada fora da elegibilidade CICS: NCM coberto por resolucao CIIA-PAC vigente na data
-- da compra (historico int_margem__ncm_prefixos), NCM coberto por CICS fora da vigencia, ou item sem NCM
CREATE OR REPLACE TABLE ciiapac AS
SELECT prefixo_ncm, resolucao, data_inicio, CAST(data_fim AS DATE) AS data_fim
FROM read_parquet('tabelas_parte0/colibri_int_margem__ncm_prefixos.parquet') WHERE starts_with(resolucao, 'ciiapac');
CREATE OR REPLACE TABLE mg_causa AS
SELECT a.*,
  CASE WHEN a.ncm IS NULL OR a.origem_ncm = 'sem_ncm' THEN 'item sem NCM (nem informado nem no tradutor)'
       WHEN EXISTS (SELECT 1 FROM ciiapac c WHERE starts_with(a.ncm, c.prefixo_ncm)
                    AND a.data_pub >= c.data_inicio AND (c.data_fim IS NULL OR a.data_pub <= c.data_fim))
         THEN 'NCM coberto por resolucao CIIA-PAC vigente'
       WHEN EXISTS (SELECT 1 FROM ciiapac c WHERE starts_with(a.ncm, c.prefixo_ncm))
         THEN 'NCM coberto por resolucao CIIA-PAC, fora da vigencia'
       WHEN EXISTS (SELECT 1 FROM cics c WHERE starts_with(a.ncm, c.prefixo_ncm))
         THEN 'NCM coberto por resolucao CICS, fora da vigencia'
       ELSE 'NCM sem cobertura CICS nem CIIA-PAC' END AS causa
FROM mg_aplic a WHERE NOT a.elegivel;
COPY (SELECT causa, origem_ncm, count(*) AS itens, sum(v_margem) AS valor_margem_aplicada
      FROM mg_causa GROUP BY ALL ORDER BY valor_margem_aplicada DESC)
  TO 'tabelas_parte0/margem_aplicada_fora_elegibilidade_causa.csv' (HEADER, DELIMITER ';');
SELECT causa, origem_ncm, count(*), sum(v_margem) FROM mg_causa GROUP BY ALL ORDER BY 4 DESC;
