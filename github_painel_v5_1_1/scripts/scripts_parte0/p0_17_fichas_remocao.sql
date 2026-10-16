-- Fichas das compras removidas pelo ajuste do dicionario, para julgar remocao indevida.
-- Executar depois de p0_02 (classificacao vigente), a partir de Processado/, trocando __ROTULO__ pelo rotulo da amostra:
--   sed 's/__ROTULO__/remocao1/g' scripts_parte0/p0_17_fichas_remocao.sql | duckdb scripts_parte0/p0.duckdb
-- Entradas: compras_segmentos.parquet e itens_seg_match.parquet (classificacao da etapa 4, dicionario original),
--           cat_compra e item_match (classificacao vigente), dicionario_termos_v1_original.csv, itens_dedup.parquet.
-- Regra: removida = par compra x categoria presente na etapa 4 e ausente da classificacao vigente, compra na base de
--        analise (bl, sem duplicidades). Amostra: 100 por categoria (todas, se houver menos), ordenadas por
--        hash(id_compra || segmento || rotulo), excluidas compras ja sorteadas em amostras de remocao anteriores
--        (tabela rem_sorteadas, acumulada a cada execucao). Semente = rotulo (ex.: 'remocao1').
-- Saida: validacao/remocao_fichas_<rotulo>.csv (objeto, termo que classificava a compra no dicionario original,
--        itens de exemplo e o trecho que hoje a exclui).

CREATE OR REPLACE TABLE dict_v1 AS SELECT * FROM read_csv('dicionario_termos_v1_original.csv', header=true, all_varchar=true);
CREATE OR REPLACE TABLE inc_v1 AS
SELECT segmento, string_agg(termo_regex, '|') AS inc_pattern FROM dict_v1 WHERE tipo = 'inclusao' GROUP BY 1;

CREATE OR REPLACE TABLE rem_pares AS
WITH ant AS (SELECT DISTINCT id_compra, segmento, local_match FROM read_parquet('compras_segmentos.parquet'))
SELECT a.* FROM ant a
WHERE a.id_compra IN (SELECT id_compra FROM bl)
  AND NOT EXISTS (SELECT 1 FROM cat_compra c WHERE c.id_compra = a.id_compra AND c.segmento = a.segmento);

CREATE TABLE IF NOT EXISTS rem_sorteadas (id_compra VARCHAR, segmento VARCHAR, amostra VARCHAR);
DELETE FROM rem_sorteadas WHERE amostra = '__ROTULO__';  -- permite reexecutar a mesma amostra
CREATE OR REPLACE TABLE rem_ja AS SELECT id_compra, segmento FROM rem_sorteadas;

CREATE OR REPLACE TABLE rem_amostra AS
SELECT * FROM (
  SELECT r.*, row_number() OVER (PARTITION BY r.segmento ORDER BY hash(r.id_compra || r.segmento || '__ROTULO__'), r.id_compra) AS rk
  FROM rem_pares r
  WHERE NOT EXISTS (SELECT 1 FROM rem_ja j WHERE j.id_compra = r.id_compra AND j.segmento = r.segmento)
) WHERE rk <= 100;

CREATE OR REPLACE TABLE rem_itens AS
SELECT m.id_compra, m.segmento, m.id_compra_item,
  strip_accents(lower(coalesce(i.descricao,'') || ' ' || coalesce(i.descricao_detalhada,'') || ' ' || coalesce(i.descricao_resumida,''))) AS txt,
  left(coalesce(i.descricao,'') || ' :: ' || coalesce(i.descricao_detalhada, i.descricao_resumida, ''), 200) AS desc_item
FROM (SELECT DISTINCT id_compra_item, id_compra, segmento FROM read_parquet('itens_seg_match.parquet')) m
JOIN rem_amostra a USING (id_compra, segmento)
JOIN read_parquet('itens_dedup.parquet') i ON i.id_compra_item = m.id_compra_item;

CREATE OR REPLACE TABLE rem_fichas AS
WITH o AS (
  SELECT a.id_compra, a.segmento, a.local_match AS local_match_etapa4, a.rk, b.ano, b.orgao, b.hom_limpo, b.objeto_compra,
    strip_accents(lower(coalesce(b.objeto_compra,'') || ' ' || coalesce(b.informacao_complementar,''))) AS txt
  FROM rem_amostra a JOIN bl b USING (id_compra)
), it AS (
  SELECT x.id_compra, x.segmento,
    string_agg(DISTINCT regexp_extract(x.txt, v.inc_pattern, 0), ' | ') AS termo_itens,
    string_agg(DISTINCT CASE WHEN s.exc_pattern IS NOT NULL AND regexp_matches(x.txt, s.exc_pattern)
                        THEN regexp_extract(x.txt, s.exc_pattern, 0) END, ' | ') AS exclusao_itens,
    string_agg(x.desc_item, ' || ' ORDER BY x.id_compra_item) FILTER (WHERE x.rn <= 3) AS itens_exemplo
  FROM (SELECT *, row_number() OVER (PARTITION BY id_compra, segmento ORDER BY id_compra_item) AS rn FROM rem_itens) x
  JOIN inc_v1 v USING (segmento) JOIN seg_patterns s USING (segmento)
  GROUP BY 1, 2
)
SELECT o.segmento, o.rk AS ordem, o.id_compra, o.local_match_etapa4, o.ano, o.orgao, o.hom_limpo,
  left(regexp_replace(coalesce(o.objeto_compra,''), '\s+', ' ', 'g'), 400) AS objeto,
  CASE WHEN regexp_matches(o.txt, v.inc_pattern) THEN regexp_extract(o.txt, v.inc_pattern, 0) END AS termo_objeto,
  it.termo_itens,
  CASE WHEN s.exc_pattern IS NOT NULL AND regexp_matches(o.txt, s.exc_pattern) THEN left(regexp_extract(o.txt, s.exc_pattern, 0), 120) END AS exclusao_objeto,
  left(it.exclusao_itens, 200) AS exclusao_itens,
  regexp_replace(coalesce(it.itens_exemplo, ''), '\s+', ' ', 'g') AS itens_exemplo,
  '__ROTULO__' AS amostra
FROM o JOIN inc_v1 v USING (segmento) JOIN seg_patterns s USING (segmento)
LEFT JOIN it USING (id_compra, segmento)
ORDER BY o.segmento, o.rk;

INSERT INTO rem_sorteadas SELECT id_compra, segmento, '__ROTULO__' FROM rem_amostra;
COPY rem_fichas TO 'validacao/remocao_fichas___ROTULO__.csv' (HEADER, DELIMITER ';');
SELECT segmento, count(*) AS removidas_na_base FROM rem_pares GROUP BY 1 ORDER BY 1;
SELECT segmento, count(*) AS fichas FROM rem_fichas GROUP BY 1 ORDER BY 1;
