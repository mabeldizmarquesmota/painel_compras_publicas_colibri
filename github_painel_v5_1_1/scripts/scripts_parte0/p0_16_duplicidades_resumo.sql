-- Duplicidades removidas por ano, no total e nas seis categorias.
-- Executar depois de p0_02 (classificacao), a partir de Processado/.
-- Entradas: dup_remover (p0_14); obj_match (p0_02, calculado sobre a base completa) e item_match (p0_02).
-- Regra: uma compra removida pertence as seis categorias quando o objeto ou algum item casa com o dicionario vigente.
-- Saida: tabelas_parte0/duplicidades_removidas.csv

CREATE OR REPLACE TABLE dup_resumo AS
WITH d AS (
  SELECT d.*, (d.id_compra IN (SELECT id_compra FROM obj_match UNION SELECT id_compra FROM item_match)) AS seis_cat
  FROM dup_remover d
)
SELECT ano, 'todas as compras' AS recorte, count(DISTINCT grupo) AS n_grupos, count(*) AS compras_removidas,
       coalesce(sum(valor_homologado), 0) AS valor_homologado_bruto_removido,
       coalesce(sum(hom_limpo) FILTER (WHERE hom_limpo > 0), 0) AS valor_homologado_limpo_removido
FROM d GROUP BY ano
UNION ALL
SELECT ano, 'seis categorias', count(DISTINCT grupo), count(*), coalesce(sum(valor_homologado), 0),
       coalesce(sum(hom_limpo) FILTER (WHERE hom_limpo > 0), 0)
FROM d WHERE seis_cat GROUP BY ano
ORDER BY recorte DESC, ano;
COPY dup_resumo TO 'tabelas_parte0/duplicidades_removidas.csv' (HEADER, DELIMITER ';');
SELECT * FROM dup_resumo;
