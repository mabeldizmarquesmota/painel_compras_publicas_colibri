-- Valores de soberania digital, preenchimento de pais de origem e teste de robustez.
-- Executar depois de p0_01 e p0_02 (classificacao final), a partir de Processado/:
--   duckdb scripts_parte0/p0.duckdb < scripts_parte0/p0_07_soberania.sql
-- Regras (valor homologado limpo, nominal; ano = ano de publicacao da compra):
--   2a) sem dupla contagem: cada compra uma vez. Compra com termo no objeto de qualquer categoria: valor
--       homologado limpo integral. Compra com termo so nos itens: soma do valor homologado dos resultados vigentes
--       dos itens classificados (cada item uma vez), limitada ao homologado limpo da compra.
--   2b) categoria a categoria: mesma regra dentro de cada categoria (objeto: compra inteira; so itens: itens da
--       categoria, limitados ao homologado da compra). Uma compra pode entrar em mais de uma categoria.
--   2c) compra inteira em cada categoria identificada (inclusive quando o termo esta so nos itens).
-- Compras com valor excluido pela auditoria (excl_h) ou sem homologado limpo positivo valem zero.

CREATE OR REPLACE TABLE res AS
SELECT id_compra, id_compra_item,
       coalesce(nullif(trim(ni_fornecedor), ''), 'ND') AS ni_fornecedor,
       TRY_CAST(valor_total_homologado AS DOUBLE) AS v,
       pais_origem_produto_servico_id, aplicacao_margem_preferencia
FROM read_parquet('resultados_dedup.parquet');

CREATE OR REPLACE TABLE item_val AS
SELECT id_compra_item, sum(v) AS v FROM res
WHERE v IS NOT NULL AND id_compra_item IN (SELECT id_compra_item FROM item_match)
GROUP BY 1;

-- valor base da compra (zero quando excluida ou sem homologado limpo positivo)
CREATE OR REPLACE TABLE bv AS
SELECT id_compra, ano, CASE WHEN excl_h OR coalesce(hom_limpo, 0) <= 0 THEN 0 ELSE hom_limpo END AS hom
FROM bl;

-- ---------- 2b e 2c: compra x categoria ----------
CREATE OR REPLACE TABLE cat_itens AS
SELECT m.id_compra, m.segmento, sum(coalesce(iv.v, 0)) AS s
FROM item_match m LEFT JOIN item_val iv USING (id_compra_item)
GROUP BY 1, 2;

CREATE OR REPLACE TABLE cat_valor AS
SELECT c.id_compra, c.segmento, c.local_match, b.ano, b.hom,
  CASE WHEN c.local_match IN ('objeto', 'ambos') THEN b.hom
       ELSE least(coalesce(ci.s, 0), b.hom) END AS v_2b,
  b.hom AS v_2c,
  CASE WHEN c.local_match IN ('objeto', 'ambos') THEN b.hom ELSE 0 END AS v_so_objeto
FROM cat_compra c
JOIN bv b USING (id_compra)
LEFT JOIN cat_itens ci USING (id_compra, segmento);

-- ---------- 2a: compra unica ----------
CREATE OR REPLACE TABLE c_obj AS SELECT DISTINCT id_compra FROM cat_compra WHERE local_match IN ('objeto', 'ambos');
CREATE OR REPLACE TABLE d_itens AS
SELECT i.id_compra, sum(coalesce(iv.v, 0)) AS s
FROM (SELECT DISTINCT id_compra_item, id_compra FROM item_match
      WHERE id_compra NOT IN (SELECT id_compra FROM c_obj)
        AND id_compra IN (SELECT id_compra FROM cat_compra)) i
LEFT JOIN item_val iv USING (id_compra_item)
GROUP BY 1;
CREATE OR REPLACE TABLE compra_unica AS
SELECT b.id_compra, b.ano, 'objeto' AS base_valor, b.hom AS v_2a
FROM bv b WHERE b.id_compra IN (SELECT id_compra FROM c_obj)
UNION ALL
SELECT b.id_compra, b.ano, 'item', least(d.s, b.hom)
FROM d_itens d JOIN bv b USING (id_compra);

-- ---------- Saidas ----------
CREATE OR REPLACE TABLE tot_ano AS SELECT ano, sum(hom) AS hom_total FROM bv GROUP BY 1;

CREATE OR REPLACE TABLE p0_soberania_tres_regras AS
SELECT 'total 2021 a 2026' AS recorte,
  (SELECT sum(v_2a) FROM compra_unica) AS regra_2a_sem_dupla_contagem,
  (SELECT sum(v_2b) FROM cat_valor) AS regra_2b_soma_das_categorias,
  (SELECT sum(v_2c) FROM cat_valor) AS regra_2c_compra_inteira_em_cada_categoria,
  (SELECT sum(hom_total) FROM tot_ano) AS homologado_limpo_total,
  (SELECT count(*) FROM compra_unica) AS n_compras_distintas,
  (SELECT count(*) FROM compra_unica WHERE v_2a > 0) AS n_compras_valor_positivo;

CREATE OR REPLACE TABLE p0_soberania_ano AS
SELECT t.ano, coalesce(u.v, 0) AS regra_2a, coalesce(u.n, 0) AS n_compras, t.hom_total,
       coalesce(u.v, 0) / t.hom_total AS participacao_2a
FROM tot_ano t
LEFT JOIN (SELECT ano, sum(v_2a) v, count(*) n FROM compra_unica GROUP BY 1) u USING (ano)
ORDER BY ano;

CREATE OR REPLACE TABLE p0_categoria_ano AS
SELECT segmento AS categoria, ano, count(*) AS n_compras,
  count(*) FILTER (WHERE v_2b > 0) AS n_compras_valor_positivo,
  sum(v_2b) AS valor_2b, sum(v_2c) AS valor_2c, sum(v_so_objeto) AS valor_so_objeto
FROM cat_valor GROUP BY 1, 2 ORDER BY 1, 2;

CREATE OR REPLACE TABLE p0_categoria_total AS
SELECT segmento AS categoria, count(*) AS n_compras,
  count(*) FILTER (WHERE local_match IN ('objeto','ambos')) AS n_compras_termo_no_objeto,
  sum(v_2b) AS valor_2b, sum(v_2c) AS valor_2c, sum(v_so_objeto) AS valor_so_objeto
FROM cat_valor GROUP BY 1 ORDER BY valor_2b DESC;

-- item 7: robustez (a) so termo no objeto x (b) objeto e itens (criterio adotado = 2b)
CREATE OR REPLACE TABLE p0_robustez AS
SELECT categoria, valor_so_objeto AS valor_a_so_objeto,
  rank() OVER (ORDER BY valor_so_objeto DESC) AS posicao_a,
  valor_2b AS valor_b_objeto_e_itens,
  rank() OVER (ORDER BY valor_2b DESC) AS posicao_b
FROM p0_categoria_total ORDER BY posicao_b;

-- item 5: preenchimento de pais_origem_produto_servico_id nos resultados das seis categorias
-- escopo: compra com termo no objeto = todos os resultados da compra; so itens = resultados dos itens da categoria
CREATE OR REPLACE TABLE res_cat AS
SELECT DISTINCT c.segmento, r.id_compra, r.id_compra_item, r.ni_fornecedor, r.v, r.pais_origem_produto_servico_id,
       r.aplicacao_margem_preferencia
FROM cat_compra c JOIN res r USING (id_compra)
WHERE c.local_match IN ('objeto', 'ambos')
UNION
SELECT m.segmento, r.id_compra, r.id_compra_item, r.ni_fornecedor, r.v, r.pais_origem_produto_servico_id,
       r.aplicacao_margem_preferencia
FROM cat_compra c
JOIN item_match m ON m.id_compra = c.id_compra AND m.segmento = c.segmento
JOIN res r ON r.id_compra_item = m.id_compra_item
WHERE c.local_match = 'item';

CREATE OR REPLACE TABLE res_cat_valid AS
SELECT x.* FROM res_cat x JOIN bl b USING (id_compra) WHERE NOT b.excl_h;

CREATE OR REPLACE TABLE p0_pais_origem AS
WITH u AS (  -- resultados distintos das seis categorias (um resultado em duas categorias conta uma vez)
  SELECT DISTINCT id_compra_item, ni_fornecedor, v, pais_origem_produto_servico_id FROM res_cat_valid)
SELECT 'seis categorias (resultados distintos)' AS recorte, count(*) AS n_resultados,
  count(*) FILTER (WHERE nullif(trim(CAST(pais_origem_produto_servico_id AS VARCHAR)), '') IS NOT NULL) AS n_preenchido,
  100.0 * count(*) FILTER (WHERE nullif(trim(CAST(pais_origem_produto_servico_id AS VARCHAR)), '') IS NOT NULL) / count(*) AS pct_preenchido
FROM u
UNION ALL
SELECT segmento, count(*),
  count(*) FILTER (WHERE nullif(trim(CAST(pais_origem_produto_servico_id AS VARCHAR)), '') IS NOT NULL),
  100.0 * count(*) FILTER (WHERE nullif(trim(CAST(pais_origem_produto_servico_id AS VARCHAR)), '') IS NOT NULL) / count(*)
FROM res_cat_valid GROUP BY segmento;

COPY p0_soberania_tres_regras TO 'tabelas_parte0/p0_soberania_tres_regras.csv' (HEADER, DELIMITER ';');
COPY p0_soberania_ano TO 'tabelas_parte0/p0_soberania_ano.csv' (HEADER, DELIMITER ';');
COPY p0_categoria_ano TO 'tabelas_parte0/p0_categoria_ano.csv' (HEADER, DELIMITER ';');
COPY p0_categoria_total TO 'tabelas_parte0/p0_categoria_total.csv' (HEADER, DELIMITER ';');
COPY p0_robustez TO 'tabelas_parte0/p0_robustez_categorias.csv' (HEADER, DELIMITER ';');
COPY p0_pais_origem TO 'tabelas_parte0/p0_preenchimento_pais_origem.csv' (HEADER, DELIMITER ';');

SELECT * FROM p0_soberania_tres_regras;
SELECT * FROM p0_soberania_ano;
SELECT * FROM p0_categoria_total;
SELECT * FROM p0_robustez;
SELECT * FROM p0_pais_origem;
