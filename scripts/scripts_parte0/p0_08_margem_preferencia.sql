-- Valor homologado em itens elegiveis a margem de preferencia (NCMs cobertas por resolucao CICS)
-- comparado com o valor em que a margem foi aplicada no resultado.
-- Executar depois de p0_07, a partir de Processado/:  duckdb scripts_parte0/p0.duckdb < scripts_parte0/p0_08_margem_preferencia.sql
-- Entradas do Colibri (exportadas por p0_06b, somente leitura):
--   colibri_int_margem__ncm_prefixos.parquet: prefixo de NCM coberto por resolucao, com data de inicio e fim de vigencia
--   colibri_mrt_tradutor_catmat_ncm.parquet: CATMAT -> NCM (classificacao humana quando existe; sugestao de IA nos demais)
-- Regras:
--   NCM do item: codigo_NCM informado no item (so digitos, 8 posicoes); sem ele, subitem_ncm do tradutor pelo CATMAT
--   (cod_item_catalogo). Apenas itens de material (material_ou_servico = 'M').
--   Elegivel: NCM comeca com um prefixo de resolucao CICS e a data de publicacao da compra esta dentro da vigencia
--   (data_inicio <= data <= data_fim; data_fim nula = vigente).
--   Valor: soma do valor homologado dos resultados vigentes do item. Compras com valor excluido pela auditoria ficam fora.
--   Escopo seis categorias: compra com termo no objeto = todos os itens; so itens = itens classificados.
--   Margem aplicada: resultados com aplicacao_margem_preferencia = true.

CREATE OR REPLACE TABLE cics AS
SELECT prefixo_ncm, resolucao, tipo_margem, data_inicio, CAST(data_fim AS DATE) AS data_fim
FROM read_parquet('tabelas_parte0/colibri_int_margem__ncm_prefixos.parquet')
WHERE starts_with(resolucao, 'cics');

CREATE OR REPLACE TABLE trad AS
SELECT catmat, subitem_ncm, metodo_de_mapeamento FROM read_parquet('tabelas_parte0/colibri_mrt_tradutor_catmat_ncm.parquet')
WHERE subitem_ncm IS NOT NULL;

CREATE OR REPLACE TABLE itm AS
SELECT i.id_compra_item, i.id_compra, i.material_ou_servico,
  nullif(regexp_replace(coalesce(i.codigo_NCM, ''), '[^0-9]', '', 'g'), '') AS ncm_item,
  TRY_CAST(TRY_CAST(i.cod_item_catalogo AS DOUBLE) AS INTEGER) AS catmat
FROM read_parquet('itens_dedup.parquet') i;

CREATE OR REPLACE TABLE itm_ncm AS
SELECT x.id_compra_item, x.id_compra, x.material_ou_servico,
  CASE WHEN length(x.ncm_item) = 8 THEN x.ncm_item ELSE regexp_replace(t.subitem_ncm, '[^0-9]', '', 'g') END AS ncm,
  CASE WHEN length(x.ncm_item) = 8 THEN 'ncm_do_item' WHEN t.subitem_ncm IS NOT NULL THEN 'tradutor_' || t.metodo_de_mapeamento
       ELSE 'sem_ncm' END AS origem_ncm
FROM itm x LEFT JOIN trad t ON t.catmat = x.catmat;

CREATE OR REPLACE TABLE itm_val AS
SELECT id_compra_item, sum(v) AS v,
       sum(v) FILTER (WHERE lower(CAST(aplicacao_margem_preferencia AS VARCHAR)) IN ('true','t','1')) AS v_margem
FROM res WHERE v IS NOT NULL GROUP BY 1;

-- elegibilidade por data de publicacao da compra
CREATE OR REPLACE TABLE itm_eleg AS
SELECT n.id_compra_item, n.id_compra, n.material_ou_servico, n.ncm, n.origem_ncm,
  EXISTS (SELECT 1 FROM cics c WHERE starts_with(n.ncm, c.prefixo_ncm)
          AND b.data_pub >= c.data_inicio AND (c.data_fim IS NULL OR b.data_pub <= c.data_fim)) AS elegivel,
  b.ano, b.excl_h
FROM itm_ncm n JOIN bl b USING (id_compra)
WHERE n.material_ou_servico = 'M';

-- escopo das seis categorias (cada item uma vez)
CREATE OR REPLACE TABLE escopo_itens AS
SELECT DISTINCT i.id_compra_item FROM read_parquet('itens_dedup.parquet') i
WHERE i.id_compra IN (SELECT id_compra FROM cat_compra WHERE local_match IN ('objeto','ambos'))
UNION
SELECT DISTINCT m.id_compra_item FROM item_match m
JOIN cat_compra c ON c.id_compra = m.id_compra AND c.segmento = m.segmento AND c.local_match = 'item';

CREATE OR REPLACE TABLE p0_margem AS
WITH base AS (
  SELECT e.*, coalesce(v.v, 0) AS v, coalesce(v.v_margem, 0) AS v_margem,
         (e.id_compra_item IN (SELECT id_compra_item FROM escopo_itens)) AS seis_cat
  FROM itm_eleg e LEFT JOIN itm_val v USING (id_compra_item)
  WHERE NOT e.excl_h
), r AS (
  SELECT 'seis categorias' AS recorte, * FROM base WHERE seis_cat
  UNION ALL
  SELECT 'todas as compras', * FROM base
)
SELECT recorte,
  count(*) AS n_itens_material,
  count(*) FILTER (WHERE origem_ncm <> 'sem_ncm') AS n_itens_com_ncm,
  sum(v) AS valor_homologado_itens_material,
  count(*) FILTER (WHERE elegivel) AS n_itens_elegiveis,
  sum(v) FILTER (WHERE elegivel) AS valor_homologado_elegivel,
  sum(v_margem) AS valor_margem_aplicada,
  sum(v_margem) FILTER (WHERE elegivel) AS valor_margem_aplicada_em_elegiveis
FROM r GROUP BY 1;

-- valor total homologado das seis categorias sem dupla contagem (denominador de referencia)
CREATE OR REPLACE TABLE p0_margem_ano AS
SELECT e.ano, sum(coalesce(v.v,0)) FILTER (WHERE e.elegivel) AS valor_elegivel_seis_cat,
       sum(coalesce(v.v_margem,0)) AS valor_margem_aplicada_seis_cat
FROM itm_eleg e LEFT JOIN itm_val v USING (id_compra_item)
WHERE NOT e.excl_h AND e.id_compra_item IN (SELECT id_compra_item FROM escopo_itens)
GROUP BY 1 ORDER BY 1;

-- margem aplicada em todo o escopo das seis categorias (itens de material e servico)
CREATE OR REPLACE TABLE p0_margem_aplicada_total AS
SELECT sum(coalesce(v.v_margem,0)) AS valor_margem_aplicada_seis_cat_todos_itens,
       count(*) FILTER (WHERE v.v_margem > 0) AS n_itens_com_margem_aplicada
FROM escopo_itens s JOIN itm_val v USING (id_compra_item)
JOIN read_parquet('itens_dedup.parquet') i USING (id_compra_item)
JOIN bl b ON b.id_compra = i.id_compra WHERE NOT b.excl_h;

COPY p0_margem TO 'tabelas_parte0/p0_margem_preferencia.csv' (HEADER, DELIMITER ';');
COPY p0_margem_ano TO 'tabelas_parte0/p0_margem_preferencia_ano.csv' (HEADER, DELIMITER ';');
COPY p0_margem_aplicada_total TO 'tabelas_parte0/p0_margem_aplicada_seis_categorias.csv' (HEADER, DELIMITER ';');
SELECT * FROM p0_margem; SELECT * FROM p0_margem_ano; SELECT * FROM p0_margem_aplicada_total;

-- origem do NCM dos itens elegiveis (NCM informado no item ou tradutor CATMAT -> NCM, humano ou IA)
CREATE OR REPLACE TABLE p0_margem_origem_ncm AS
SELECT e.origem_ncm, count(*) AS n_itens_elegiveis, sum(coalesce(v.v,0)) AS valor_homologado_elegivel
FROM itm_eleg e LEFT JOIN itm_val v USING (id_compra_item)
WHERE NOT e.excl_h AND e.elegivel AND e.id_compra_item IN (SELECT id_compra_item FROM escopo_itens)
GROUP BY 1 ORDER BY 3 DESC;
COPY p0_margem_origem_ncm TO 'tabelas_parte0/p0_margem_preferencia_origem_ncm.csv' (HEADER, DELIMITER ';');
SELECT * FROM p0_margem_origem_ncm;
