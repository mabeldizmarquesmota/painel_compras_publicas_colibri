-- Classificacao das compras e itens nas seis categorias, a partir de dicionario_termos.csv.
-- Executar depois de p0_01, p0_14 e p0_15 (bl = base sem duplicidades), a partir de Processado/:  duckdb scripts_parte0/p0.duckdb < scripts_parte0/p0_02_classificacao.sql
-- Mesma regra das etapas 4 (METODOLOGIA.md): texto normalizado com lower() e strip_accents();
--   compra: objeto_compra + informacao_complementar; item: descricao + descricao_detalhada + descricao_resumida.
--   match = algum termo de inclusao da categoria E nenhum termo de exclusao da categoria no mesmo texto.
-- O pre-filtro pela uniao de todos os termos de inclusao nao altera o resultado (e mais permissivo que cada categoria).

CREATE OR REPLACE TABLE dict AS
SELECT * FROM read_csv('dicionario_termos.csv', header=true, all_varchar=true);

CREATE OR REPLACE TABLE seg_patterns AS
WITH inc AS (
  SELECT segmento, any_value(camada) AS camada, string_agg(termo_regex, '|') AS inc_pattern
  FROM dict WHERE tipo = 'inclusao' GROUP BY segmento
), exc AS (
  SELECT segmento, string_agg(termo_regex, '|') AS exc_pattern
  FROM dict WHERE tipo = 'exclusao' GROUP BY segmento
)
SELECT inc.segmento, inc.camada, inc.inc_pattern, exc.exc_pattern FROM inc LEFT JOIN exc USING (segmento);

CREATE OR REPLACE TABLE mega AS SELECT string_agg(inc_pattern, '|') AS mega_pattern FROM seg_patterns;

-- ---------- nivel da compra (objeto) ----------
CREATE OR REPLACE TABLE obj_match AS
WITH t AS (
  SELECT id_compra,
         strip_accents(lower(coalesce(objeto_compra,'') || ' ' || coalesce(informacao_complementar,''))) AS txt
  FROM bl_completa  -- base completa, para permitir o resumo das duplicidades nas seis categorias (p0_16)
), pre AS (SELECT t.* FROM t, mega WHERE regexp_matches(t.txt, mega.mega_pattern))
SELECT DISTINCT p.id_compra, s.segmento
FROM pre p CROSS JOIN seg_patterns s
WHERE regexp_matches(p.txt, s.inc_pattern)
  AND NOT (s.exc_pattern IS NOT NULL AND regexp_matches(p.txt, s.exc_pattern));

-- ---------- nivel do item ----------
CREATE OR REPLACE TABLE item_match AS
WITH t AS (
  SELECT id_compra_item, id_compra,
         strip_accents(lower(coalesce(descricao,'') || ' ' || coalesce(descricao_detalhada,'') || ' ' || coalesce(descricao_resumida,''))) AS txt
  FROM read_parquet('itens_dedup.parquet')
), pre AS (SELECT t.* FROM t, mega WHERE regexp_matches(t.txt, mega.mega_pattern))
SELECT DISTINCT p.id_compra_item, p.id_compra, s.segmento
FROM pre p CROSS JOIN seg_patterns s
WHERE regexp_matches(p.txt, s.inc_pattern)
  AND NOT (s.exc_pattern IS NOT NULL AND regexp_matches(p.txt, s.exc_pattern));

-- ---------- compra x categoria ----------
-- local_match: objeto (so no objeto), item (so nos itens), ambos.
-- Compras classificadas apenas por itens cuja compra nao esta em base_limpa (sem ano e sem valor) ficam de fora.
CREATE OR REPLACE TABLE cat_compra AS
WITH pares AS (
  SELECT id_compra, segmento FROM obj_match
  UNION SELECT DISTINCT id_compra, segmento FROM item_match
)
SELECT p.id_compra, p.segmento,
  (o.id_compra IS NOT NULL) AS match_objeto,
  (i.id_compra IS NOT NULL) AS match_item,
  CASE WHEN o.id_compra IS NOT NULL AND i.id_compra IS NOT NULL THEN 'ambos'
       WHEN o.id_compra IS NOT NULL THEN 'objeto' ELSE 'item' END AS local_match
FROM pares p
JOIN bl USING (id_compra)
LEFT JOIN obj_match o ON o.id_compra = p.id_compra AND o.segmento = p.segmento
LEFT JOIN (SELECT DISTINCT id_compra, segmento FROM item_match) i ON i.id_compra = p.id_compra AND i.segmento = p.segmento;

-- ---------- comparacao com a classificacao anterior (etapa 4) ----------
CREATE OR REPLACE TABLE p0_comparacao_classificacao AS
WITH ant AS (SELECT DISTINCT id_compra, segmento FROM read_parquet('compras_segmentos.parquet')
             WHERE id_compra IN (SELECT id_compra FROM bl))
SELECT s.segmento,
  (SELECT count(*) FROM cat_compra c WHERE c.segmento = s.segmento) AS n_compras_atual,
  (SELECT count(*) FROM ant a WHERE a.segmento = s.segmento) AS n_compras_etapa4,
  (SELECT count(*) FROM cat_compra c WHERE c.segmento = s.segmento
      AND NOT EXISTS (SELECT 1 FROM ant a WHERE a.id_compra = c.id_compra AND a.segmento = c.segmento)) AS n_novas,
  (SELECT count(*) FROM ant a WHERE a.segmento = s.segmento
      AND NOT EXISTS (SELECT 1 FROM cat_compra c WHERE a.id_compra = c.id_compra AND a.segmento = c.segmento)) AS n_removidas
FROM seg_patterns s ORDER BY s.segmento;

COPY p0_comparacao_classificacao TO 'tabelas_parte0/p0_comparacao_classificacao_etapa4.csv' (HEADER, DELIMITER ';');
SELECT * FROM p0_comparacao_classificacao;
SELECT segmento, local_match, count(*) FROM cat_compra GROUP BY ALL ORDER BY ALL;
