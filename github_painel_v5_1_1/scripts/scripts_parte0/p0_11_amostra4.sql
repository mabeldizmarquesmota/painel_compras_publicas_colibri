-- Apos o ajuste do dicionario: amostra 4, independente das amostras 1 a 3, para medir a precisao
-- da classificacao final de ia, unica categoria ajustada de novo apos a amostra 3.
-- 150 compras por categoria, sorteio deterministico por hash(id_compra || segmento || 'amostra4'), excluidas as
-- compras das amostras 1 a 3. Data center e seguranca mantem a amostra 3; nuvem e plataformas, a 2; identidade, a 1.
-- Executar depois de p0_02 (classificacao final). Saida: validacao/fichas_revisao_amostra4.csv

CREATE OR REPLACE TABLE amostra1 AS
SELECT id_compra, segmento FROM read_csv('validacao/validacao_*.csv', header=true, all_varchar=true)
UNION SELECT id_compra, segmento FROM read_csv('validacao/fichas_revisao_amostra2.csv', delim=';', header=true, all_varchar=true)
UNION SELECT id_compra, segmento FROM read_csv('validacao/fichas_revisao_amostra3.csv', delim=';', header=true, all_varchar=true);

CREATE OR REPLACE TABLE amostra AS
SELECT id_compra, segmento, local_match FROM (
  SELECT c.*, row_number() OVER (PARTITION BY c.segmento ORDER BY hash(c.id_compra || c.segmento || 'amostra4'), c.id_compra) AS rk
  FROM cat_compra c
  WHERE c.segmento IN ('ia')
    AND NOT EXISTS (SELECT 1 FROM amostra1 a WHERE a.id_compra = c.id_compra AND a.segmento = c.segmento)
) WHERE rk <= 150;

CREATE OR REPLACE TABLE amostra_itens AS
SELECT m.id_compra, m.segmento, m.id_compra_item,
       strip_accents(lower(coalesce(i.descricao,'') || ' ' || coalesce(i.descricao_detalhada,'') || ' ' || coalesce(i.descricao_resumida,''))) AS txt,
       coalesce(i.descricao,'') AS descricao,
       coalesce(i.descricao_detalhada, i.descricao_resumida, '') AS descricao_det
FROM item_match m
JOIN amostra a ON a.id_compra = m.id_compra AND a.segmento = m.segmento
JOIN read_parquet('itens_dedup.parquet') i ON i.id_compra_item = m.id_compra_item;

CREATE OR REPLACE TABLE fichas4 AS
WITH obj AS (
  SELECT a.id_compra, a.segmento, a.local_match, b.ano, b.orgao, b.modalidade, b.hom_limpo,
         b.objeto_compra, b.informacao_complementar,
         strip_accents(lower(coalesce(b.objeto_compra,'') || ' ' || coalesce(b.informacao_complementar,''))) AS txt
  FROM amostra a JOIN bl b USING (id_compra)
), it AS (
  SELECT x.id_compra, x.segmento, count(*) AS n_itens_cat,
         string_agg(DISTINCT regexp_extract(x.txt, s.inc_pattern, 0), ' | ') AS termos_itens,
         string_agg(left(x.descricao || ' :: ' || x.descricao_det, 220), ' || ' ORDER BY x.id_compra_item)
           FILTER (WHERE x.rn <= 3) AS itens_exemplo
  FROM (SELECT *, row_number() OVER (PARTITION BY id_compra, segmento ORDER BY id_compra_item) AS rn FROM amostra_itens) x
  JOIN seg_patterns s USING (segmento)
  GROUP BY 1,2
)
SELECT o.segmento, o.id_compra, o.local_match, o.ano, o.orgao, o.modalidade, o.hom_limpo,
       CASE WHEN regexp_matches(o.txt, s.inc_pattern) THEN regexp_extract(o.txt, s.inc_pattern, 0) END AS termo_objeto,
       left(regexp_replace(coalesce(o.objeto_compra,''), '\s+', ' ', 'g'), 400) AS objeto,
       left(regexp_replace(coalesce(o.informacao_complementar,''), '\s+', ' ', 'g'), 200) AS info_compl,
       it.n_itens_cat, it.termos_itens,
       regexp_replace(coalesce(it.itens_exemplo,''), '\s+', ' ', 'g') AS itens_exemplo
FROM obj o JOIN seg_patterns s USING (segmento)
LEFT JOIN it USING (id_compra, segmento)
ORDER BY o.segmento, o.id_compra;

COPY (SELECT * FROM fichas4) TO 'validacao/fichas_revisao_amostra4.csv' (HEADER, DELIMITER ';');
SELECT segmento, count(*) FROM fichas4 GROUP BY 1 ORDER BY 1;
