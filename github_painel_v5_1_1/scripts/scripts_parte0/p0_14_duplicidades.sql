-- Republicacoes e duplicidades de compras.
-- Executar depois de p0_01 (tabela bl_completa), a partir de Processado/:  duckdb scripts_parte0/p0.duckdb < scripts_parte0/p0_14_duplicidades.sql
-- Entradas: base_limpa.parquet (via tabela bl de p0_01) e parquet/compras.parquet (campos de unidade, processo e datas,
--           com a mesma regra de versao de base_limpa: is_current = true, maior data_atualizacao, desempate por
--           data_inclusao e valido_de).
-- Criterio inicial:
--   chave = CNPJ do orgao (orgao_entidade_cnpj) + codigo da unidade compradora (unidade_orgao_codigo_unidade)
--         + numero do processo (processo, sem espacos nas pontas) + objeto normalizado (minusculas, sem acentos,
--           espacos extras reduzidos a um) + valor homologado bruto.
--   Duplicata so quando os cinco campos coincidem. Decisoes registradas em METODOLOGIA.md: valor homologado nulo nao
--   coincide com nada (compra sem homologacao nao e agrupada); campos de texto nulos ou vazios tambem nao agrupam.
--   Mantem-se a compra com data_atualizacao mais recente; empates por data_inclusao, valido_de e, por fim, id_compra
--   (maior). As demais sao removidas da base de analise.
--   Mesmos campos exceto o processo: listados, nao removidos.
--   Condicao adicional (regra adotada pela equipe de pesquisa, registrada em METODOLOGIA.md): os cinco campos sao condicao necessaria
--   ("so e duplicata quando"); a remocao exige tambem o mesmo conjunto de fornecedores vencedores (ni_fornecedor dos
--   resultados vigentes). Grupos com vencedores diferentes sao contratos distintos no mesmo processo (ex.:
--   credenciamento de pipeiros da Operacao Carro-Pipa), nao republicacoes. Compras sem resultado formam conjunto
--   proprio ('sem resultado'). O efeito da regra literal (so os cinco campos) e calculado e gravado para comparacao.
-- Saidas: tabelas_parte0/duplicidades_ids_removidos.csv, tabelas_parte0/duplicidades_regra_literal_cinco_campos.csv,
--         tabelas_parte0/possiveis_duplicidades_processo_diferente.csv, tabelas_parte0/duplicidades_caso_rio.csv

CREATE OR REPLACE TABLE cmp_campos AS
WITH r AS (
  SELECT id_compra, orgao_entidade_cnpj, unidade_orgao_codigo_unidade, processo, objeto_compra,
         data_atualizacao, data_inclusao, valido_de,
         row_number() OVER (PARTITION BY id_compra
           ORDER BY TRY_CAST(data_atualizacao AS TIMESTAMP) DESC NULLS LAST,
                    TRY_CAST(data_inclusao AS TIMESTAMP) DESC NULLS LAST,
                    TRY_CAST(valido_de AS TIMESTAMP) DESC NULLS LAST) AS rn
  FROM read_parquet('../parquet/compras.parquet') WHERE is_current = true
)
SELECT r.id_compra,
  nullif(trim(r.orgao_entidade_cnpj), '') AS cnpj,
  nullif(trim(r.unidade_orgao_codigo_unidade), '') AS unidade,
  nullif(trim(r.processo), '') AS processo,
  nullif(trim(regexp_replace(strip_accents(lower(coalesce(r.objeto_compra, ''))), '\s+', ' ', 'g')), '') AS objeto_norm,
  TRY_CAST(r.data_atualizacao AS TIMESTAMP) AS dt_atu, TRY_CAST(r.data_inclusao AS TIMESTAMP) AS dt_inc,
  TRY_CAST(r.valido_de AS TIMESTAMP) AS dt_val,
  b.valor_homologado, b.hom_limpo, b.ano, b.orgao
FROM r JOIN bl_completa b USING (id_compra) WHERE r.rn = 1;

CREATE OR REPLACE TABLE cmp_forn AS
SELECT id_compra, string_agg(DISTINCT ni_fornecedor, ',' ORDER BY ni_fornecedor) AS fornecedores
FROM read_parquet('resultados_dedup.parquet') WHERE TRY_CAST(valor_total_homologado AS DOUBLE) IS NOT NULL GROUP BY 1;

-- regra literal (so os cinco campos), para comparacao
CREATE OR REPLACE TABLE dup_literal AS
SELECT *, count(*) OVER w AS n_grupo,
  row_number() OVER (w ORDER BY dt_atu DESC NULLS LAST, dt_inc DESC NULLS LAST, dt_val DESC NULLS LAST, id_compra DESC) AS rk,
  dense_rank() OVER (ORDER BY cnpj, unidade, processo, objeto_norm, valor_homologado) AS grupo
FROM cmp_campos
WHERE cnpj IS NOT NULL AND unidade IS NOT NULL AND processo IS NOT NULL AND objeto_norm IS NOT NULL
  AND valor_homologado IS NOT NULL
WINDOW w AS (PARTITION BY cnpj, unidade, processo, objeto_norm, valor_homologado);
COPY (SELECT ano, count(DISTINCT grupo) FILTER (WHERE n_grupo > 1) AS n_grupos,
             count(*) FILTER (WHERE n_grupo > 1 AND rk > 1) AS compras_removidas_regra_literal,
             coalesce(sum(valor_homologado) FILTER (WHERE n_grupo > 1 AND rk > 1), 0) AS valor_bruto_removido_regra_literal
      FROM dup_literal GROUP BY ano ORDER BY ano)
  TO 'tabelas_parte0/duplicidades_regra_literal_cinco_campos.csv' (HEADER, DELIMITER ';');

-- grupos com os cinco campos iguais e os mesmos fornecedores vencedores (regra adotada)
CREATE OR REPLACE TABLE dup_rank AS
SELECT *, count(*) OVER w AS n_grupo,
  row_number() OVER (w ORDER BY dt_atu DESC NULLS LAST, dt_inc DESC NULLS LAST, dt_val DESC NULLS LAST, id_compra DESC) AS rk,
  dense_rank() OVER (ORDER BY cnpj, unidade, processo, objeto_norm, valor_homologado, fornecedores) AS grupo
FROM (SELECT c.*, coalesce(f.fornecedores, 'sem resultado') AS fornecedores
      FROM cmp_campos c LEFT JOIN cmp_forn f USING (id_compra))
WHERE cnpj IS NOT NULL AND unidade IS NOT NULL AND processo IS NOT NULL AND objeto_norm IS NOT NULL
  AND valor_homologado IS NOT NULL
WINDOW w AS (PARTITION BY cnpj, unidade, processo, objeto_norm, valor_homologado, fornecedores);

CREATE OR REPLACE TABLE dup_remover AS
SELECT id_compra, grupo, ano, valor_homologado, hom_limpo FROM dup_rank WHERE n_grupo > 1 AND rk > 1;

COPY (SELECT d.id_compra, d.grupo, k.id_compra AS id_compra_mantida, d.ano, d.valor_homologado
      FROM dup_remover d JOIN dup_rank k ON k.grupo = d.grupo AND k.rk = 1 ORDER BY d.grupo, d.id_compra)
  TO 'tabelas_parte0/duplicidades_ids_removidos.csv' (HEADER, DELIMITER ';');

-- mesmos campos exceto o processo, com processos diferentes: so listar
CREATE OR REPLACE TABLE dup_proc_dif AS
WITH g AS (
  SELECT cnpj, unidade, objeto_norm, valor_homologado, count(DISTINCT processo) AS n_processos, count(*) AS n_compras
  FROM cmp_campos
  WHERE cnpj IS NOT NULL AND unidade IS NOT NULL AND objeto_norm IS NOT NULL AND valor_homologado IS NOT NULL
    AND id_compra NOT IN (SELECT id_compra FROM dup_remover)
  GROUP BY ALL HAVING count(DISTINCT coalesce(processo, '#nulo')) > 1
)
SELECT dense_rank() OVER (ORDER BY c.cnpj, c.unidade, c.objeto_norm, c.valor_homologado) AS grupo,
       c.id_compra, c.ano, c.orgao, c.cnpj, c.unidade, c.processo, c.valor_homologado, c.hom_limpo,
       c.dt_atu AS data_atualizacao, left(c.objeto_norm, 300) AS objeto_normalizado
FROM cmp_campos c JOIN g USING (cnpj, unidade, objeto_norm, valor_homologado)
ORDER BY c.valor_homologado DESC, grupo, c.id_compra;
COPY dup_proc_dif TO 'tabelas_parte0/possiveis_duplicidades_processo_diferente.csv' (HEADER, DELIMITER ';');

-- caso nominal: tres compras do Municipio do Rio de Janeiro citadas na secao 11 do relatorio
CREATE OR REPLACE TABLE dup_caso_rio AS
SELECT c.id_compra, c.cnpj, c.unidade, c.processo, c.valor_homologado, c.dt_atu AS data_atualizacao,
  left(c.objeto_norm, 200) AS objeto_normalizado,
  CASE WHEN c.id_compra IN (SELECT id_compra FROM dup_remover) THEN 'removida (duplicata dos cinco campos)'
       WHEN c.id_compra IN (SELECT id_compra FROM dup_rank WHERE n_grupo > 1) THEN 'mantida (versao mais recente do grupo)'
       WHEN c.id_compra IN (SELECT id_compra FROM dup_literal WHERE n_grupo > 1) THEN 'mantida (cinco campos iguais, fornecedores diferentes)'
       ELSE 'mantida (nenhuma outra compra coincide nos cinco campos)' END AS decisao
FROM cmp_campos c
WHERE c.id_compra IN ('98600106000022027', '98600106000042027', '98600106000062027')
ORDER BY c.id_compra;
COPY dup_caso_rio TO 'tabelas_parte0/duplicidades_caso_rio.csv' (HEADER, DELIMITER ';');

-- resumo por ano, todas as compras (o recorte das seis categorias e calculado em p0_16, depois da classificacao)
CREATE OR REPLACE TABLE dup_resumo AS
SELECT ano, 'todas as compras' AS recorte, count(DISTINCT grupo) AS n_grupos, count(*) AS compras_removidas,
       coalesce(sum(valor_homologado), 0) AS valor_homologado_bruto_removido,
       coalesce(sum(hom_limpo) FILTER (WHERE hom_limpo > 0), 0) AS valor_homologado_limpo_removido
FROM dup_remover GROUP BY ano ORDER BY ano;

SELECT * FROM dup_resumo;
SELECT * FROM dup_caso_rio;
SELECT count(DISTINCT grupo) AS grupos_processo_diferente, count(*) AS compras FROM dup_proc_dif;
