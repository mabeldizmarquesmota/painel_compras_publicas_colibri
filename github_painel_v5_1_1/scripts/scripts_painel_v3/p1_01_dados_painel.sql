-- Painel, etapa 1: tabelas agregadas que alimentam cada KPI, grafico e tabela do painel.
-- Executar a partir de Processado/, depois dos scripts p0_01 a p0_19 (tabelas finais de p0_07):
--   duckdb scripts_parte0/p0.duckdb < scripts_painel_v3/p1_01_dados_painel.sql
-- Entradas (banco de trabalho scripts_parte0/p0.duckdb): bl (base limpa sem duplicidades), cat_compra, item_match, cat_valor,
--   compra_unica, cat_itens, res, res_cat_valid, itm_val, mg_itens (p0_19), cics; itens_dedup.parquet,
--   resultados_dedup.parquet; ipca_1737.csv (IPCA, numero-indice mensal, IBGE/SIDRA tabela 1737).
-- Regras gerais:
--   valor = homologado limpo (zero quando excluido pela auditoria ou sem homologacao), nominal;
--   ano = ano de publicacao da compra no PNCP;
--   deflacao: valor x (indice do ultimo mes disponivel / indice do mes de publicacao da compra);
--   soberania: 2a (compra_unica, sem dupla contagem) nos totais; 2b (cat_valor) por categoria.
-- Saidas: tabelas_painel_v3/*.csv (separador ';'), descritas no cabecalho de cada bloco.

-- ---------------------------------------------------------------- deflator
CREATE OR REPLACE TABLE ipca AS
SELECT CAST(mes_codigo AS INTEGER) AS mes, CAST(ipca_indice AS DOUBLE) AS indice
FROM read_csv('ipca_1737.csv', header=true, delim=',', all_varchar=true);
CREATE OR REPLACE TABLE ipca_base AS SELECT mes AS mes_base, indice AS indice_base FROM ipca ORDER BY mes DESC LIMIT 1;
CREATE OR REPLACE TABLE pb AS  -- base do painel: uma linha por compra
SELECT b.id_compra, b.ano, b.orgao, b.data_pub, b.srp = 'true' AS srp, b.situacao_homologado,
  CASE b.esfera_codigo WHEN 'F' THEN 'Federal' WHEN 'E' THEN 'Estadual' WHEN 'M' THEN 'Municipal'
                       WHEN 'D' THEN 'Distrital' ELSE 'Esfera não informada' END AS esfera,
  CASE b.poder_codigo WHEN 'E' THEN 'Executivo' WHEN 'L' THEN 'Legislativo' WHEN 'J' THEN 'Judiciário'
                      ELSE 'Poder não informado' END AS poder,
  CASE strip_accents(lower(b.modalidade))
       WHEN 'pregao - eletronico' THEN 'Pregão eletrônico' WHEN 'pregao - presencial' THEN 'Pregão presencial'
       WHEN 'concorrencia - eletronica' THEN 'Concorrência eletrônica' WHEN 'concorrencia - presencial' THEN 'Concorrência presencial'
       WHEN 'dispensa' THEN 'Dispensa' WHEN 'inexigibilidade' THEN 'Inexigibilidade'
       WHEN 'credenciamento' THEN 'Credenciamento' WHEN 'concurso' THEN 'Concurso'
       ELSE coalesce(b.modalidade, 'Modalidade não informada') END AS modalidade,
  b.amparo_legal_nome, b.amparo_legal_descricao, b.objeto_compra, b.informacao_complementar,
  CASE WHEN b.valor_homologado > 0 THEN b.valor_homologado ELSE 0 END AS hom_bruto,
  CASE WHEN b.excl_h OR coalesce(b.hom_limpo, 0) <= 0 THEN 0 ELSE b.hom_limpo END AS hom,
  i.indice_base / p.indice AS fator
FROM bl b
LEFT JOIN ipca p ON p.mes = year(b.data_pub) * 100 + month(b.data_pub)
CROSS JOIN ipca_base i;

CREATE OR REPLACE TABLE pn_controles AS
SELECT 'compras sem fator de deflacao' AS controle, count(*) AS n FROM pb WHERE fator IS NULL
UNION ALL SELECT 'compras com esfera fora de F/E/M/D (tratadas como nao informada)', count(*) FROM bl WHERE coalesce(esfera_codigo,'') NOT IN ('F','E','M','D')
UNION ALL SELECT 'compras na base do painel', count(*) FROM pb
UNION ALL SELECT 'compras na base limpa sem duplicidades (bl)', count(*) FROM bl;
COPY pn_controles TO 'tabelas_painel_v3/pn_controles.csv' (HEADER, DELIMITER ';');
COPY (SELECT mes_base, indice_base FROM ipca_base) TO 'tabelas_painel_v3/pn_ipca_base.csv' (HEADER, DELIMITER ';');

-- ---------------------------------------------------------------- aba compras publicas (KPIs e graficos 1 a 4)
-- pn_cubo_compras: ano x esfera x poder x modalidade. n_publicadas = compras da base; n_homologadas = compras com
-- homologado limpo valido (> 0); n_sem_homologacao = sem valor homologado; hom_bruto = homologado como extraido (> 0).
CREATE OR REPLACE TABLE pn_cubo_compras AS
SELECT ano, esfera, poder, modalidade,
  count(*) AS n_publicadas,
  count(*) FILTER (WHERE situacao_homologado = 'valido') AS n_homologadas,
  count(*) FILTER (WHERE situacao_homologado = 'sem_homologacao') AS n_sem_homologacao,
  count(*) FILTER (WHERE situacao_homologado = 'excluido_auditoria') AS n_valor_excluido,
  sum(hom_bruto) AS hom_bruto,
  sum(hom) AS hom_nominal,
  sum(hom * fator) AS hom_deflacionado
FROM pb GROUP BY ALL ORDER BY ALL;
COPY pn_cubo_compras TO 'tabelas_painel_v3/pn_cubo_compras.csv' (HEADER, DELIMITER ';');

-- ---------------------------------------------------------------- aba soberania digital
-- valores por compra e categoria com deflacao
CREATE OR REPLACE TABLE sv AS  -- 2b por compra x categoria
SELECT c.id_compra, c.segmento, c.local_match, p.ano, p.modalidade, p.orgao, p.esfera, p.srp, p.fator,
  c.v_2b, c.v_2b * p.fator AS v_2b_defl, c.v_2c, c.hom,
  coalesce(ci.s, 0) AS valor_itens_categoria
FROM cat_valor c JOIN pb p USING (id_compra) LEFT JOIN cat_itens ci USING (id_compra, segmento);
CREATE OR REPLACE TABLE su AS  -- 2a por compra
SELECT u.id_compra, p.ano, p.modalidade, p.srp, p.fator, u.v_2a, u.v_2a * p.fator AS v_2a_defl
FROM compra_unica u JOIN pb p USING (id_compra);

-- pn_soberania_ano: 2a (sem dupla contagem) e total homologado limpo por ano
CREATE OR REPLACE TABLE pn_soberania_ano AS
SELECT t.ano, coalesce(s.v, 0) AS soberania_2a_nominal, coalesce(s.vd, 0) AS soberania_2a_deflacionado,
  coalesce(s.n, 0) AS n_compras_seis_categorias, t.hom_nominal AS homologado_total_nominal,
  t.hom_deflacionado AS homologado_total_deflacionado
FROM (SELECT ano, sum(hom_nominal) hom_nominal, sum(hom_deflacionado) hom_deflacionado FROM pn_cubo_compras GROUP BY 1) t
LEFT JOIN (SELECT ano, sum(v_2a) v, sum(v_2a_defl) vd, count(*) n FROM su GROUP BY 1) s USING (ano)
ORDER BY ano;
COPY pn_soberania_ano TO 'tabelas_painel_v3/pn_soberania_ano.csv' (HEADER, DELIMITER ';');

-- pn_categoria_ano (grafico 5; KPIs quando uma categoria e filtrada): 2b por categoria e ano
CREATE OR REPLACE TABLE pn_categoria_ano AS
SELECT segmento AS categoria, ano, count(*) AS n_compras, sum(v_2b) AS valor_nominal, sum(v_2b_defl) AS valor_deflacionado,
  sum(v_2c) AS valor_compra_inteira_nominal
FROM sv GROUP BY ALL ORDER BY ALL;
COPY pn_categoria_ano TO 'tabelas_painel_v3/pn_categoria_ano.csv' (HEADER, DELIMITER ';');

-- pn_soberania_tres_regras (aba Sobre): 2a, 2b e 2c no periodo 2021 a 2026
CREATE OR REPLACE TABLE pn_soberania_tres_regras AS
SELECT (SELECT sum(v_2a) FROM su) AS regra_2a, (SELECT sum(v_2b) FROM sv) AS regra_2b, (SELECT sum(v_2c) FROM sv) AS regra_2c,
  (SELECT sum(hom) FROM pb) AS homologado_total, (SELECT sum(hom_bruto) FROM pb) AS homologado_bruto,
  (SELECT count(*) FROM su) AS n_compras_seis_categorias;
COPY pn_soberania_tres_regras TO 'tabelas_painel_v3/pn_soberania_tres_regras.csv' (HEADER, DELIMITER ';');

-- pn_modalidade_soberania (grafico 7): valor por modalidade; recorte 'todas' = 2a; categoria = 2b.
-- O total das compras publicas por modalidade sai de pn_cubo_compras.
CREATE OR REPLACE TABLE pn_modalidade_soberania AS
SELECT 'todas' AS recorte, ano, modalidade, sum(v_2a) AS valor_nominal, sum(v_2a_defl) AS valor_deflacionado, count(*) AS n_compras
FROM su GROUP BY ALL
UNION ALL
SELECT segmento, ano, modalidade, sum(v_2b), sum(v_2b_defl), count(*) FROM sv GROUP BY ALL
ORDER BY ALL;
COPY pn_modalidade_soberania TO 'tabelas_painel_v3/pn_modalidade_soberania.csv' (HEADER, DELIMITER ';');

-- pn_forma_contratacao (grafico 8): objeto proprio = termo no objeto (objeto ou ambos) ou itens da categoria com mais
-- da metade do homologado limpo da compra; nos demais casos, item de contratacao mais ampla. Valor 2b.
CREATE OR REPLACE TABLE pn_forma_contratacao AS
SELECT segmento AS categoria, ano,
  CASE WHEN local_match IN ('objeto', 'ambos') OR (hom > 0 AND valor_itens_categoria > 0.5 * hom)
       THEN 'Objeto próprio' ELSE 'Item de contratação mais ampla' END AS forma,
  count(*) AS n_compras, sum(v_2b) AS valor_nominal, sum(v_2b_defl) AS valor_deflacionado
FROM sv GROUP BY ALL ORDER BY ALL;
COPY pn_forma_contratacao TO 'tabelas_painel_v3/pn_forma_contratacao.csv' (HEADER, DELIMITER ';');

-- resultados das seis categorias (escopo de p0_07: compra com termo no objeto = todos os resultados; so itens =
-- resultados dos itens da categoria), sem compras com valor excluido, valor do resultado > 0
CREATE OR REPLACE TABLE forn_nome AS
SELECT ni, arg_max(nome, n) AS nome FROM (
  SELECT coalesce(nullif(trim(ni_fornecedor), ''), 'ND') AS ni, trim(nome_razao_social_fornecedor) AS nome, count(*) AS n
  FROM read_parquet('resultados_dedup.parquet') WHERE nullif(trim(nome_razao_social_fornecedor), '') IS NOT NULL
  GROUP BY 1, 2) GROUP BY 1;
CREATE OR REPLACE TABLE rc AS
SELECT r.segmento, p.ano, r.ni_fornecedor AS ni, p.orgao, p.esfera, r.v, r.v * p.fator AS v_defl, r.id_compra
FROM res_cat_valid r JOIN pb p USING (id_compra)
WHERE r.v > 0 AND p.hom > 0;

-- pn_fluxo (grafico 9, Sankey; tabela 1 de orgaos e tooltips): tabela fornecedor x categoria x orgao comprador, por
-- ano, com o valor homologado dos resultados (CNPJ vencedor) e a esfera do orgao
CREATE OR REPLACE TABLE pn_fluxo AS
SELECT rc.segmento AS categoria, rc.ano, rc.ni AS cnpj_fornecedor,
  coalesce(f.nome, CASE WHEN rc.ni = 'ND' THEN 'Fornecedor não identificado' ELSE rc.ni END) AS fornecedor,
  rc.orgao, rc.esfera, sum(rc.v) AS valor_nominal, sum(rc.v_defl) AS valor_deflacionado, count(DISTINCT rc.id_compra) AS n_compras
FROM rc LEFT JOIN forn_nome f ON f.ni = rc.ni
GROUP BY ALL ORDER BY ALL;
COPY pn_fluxo TO 'tabelas_painel_v3/pn_fluxo.csv' (HEADER, DELIMITER ';');

-- pn_concentracao (tabela 1): por categoria e ano, sobre os resultados com CNPJ identificado.
-- s_i = valor do fornecedor i / valor da categoria no ano; CR4 = soma dos 4 maiores s_i x 100; HHI = soma de s_i^2.
CREATE OR REPLACE TABLE fa AS
SELECT segmento AS categoria, ano, ni, sum(v) AS v, sum(v_defl) AS vd FROM rc WHERE ni <> 'ND' GROUP BY ALL;
CREATE OR REPLACE TABLE pn_concentracao AS
WITH t AS (SELECT categoria, ano, sum(v) AS tv, sum(vd) AS tvd FROM fa GROUP BY ALL),
s AS (SELECT f.*, f.v / t.tv AS s, f.vd / t.tvd AS sd,
        row_number() OVER (PARTITION BY f.categoria, f.ano ORDER BY f.v DESC, f.ni) AS rk,
        row_number() OVER (PARTITION BY f.categoria, f.ano ORDER BY f.vd DESC, f.ni) AS rkd
      FROM fa f JOIN t USING (categoria, ano))
SELECT categoria, ano, count(*) AS n_fornecedores,
  100 * sum(s) FILTER (WHERE rk <= 4) AS cr4_nominal, sum(s * s) AS hhi_nominal, sum(v) AS valor_nominal,
  100 * sum(sd) FILTER (WHERE rkd <= 4) AS cr4_deflacionado, sum(sd * sd) AS hhi_deflacionado, sum(vd) AS valor_deflacionado
FROM s GROUP BY ALL ORDER BY ALL;
COPY pn_concentracao TO 'tabelas_painel_v3/pn_concentracao.csv' (HEADER, DELIMITER ';');
COPY (SELECT segmento AS categoria, count(*) AS n_resultados_sem_cnpj, sum(v) AS valor_sem_cnpj FROM rc WHERE ni = 'ND' GROUP BY 1 ORDER BY 1)
  TO 'tabelas_painel_v3/pn_concentracao_sem_cnpj.csv' (HEADER, DELIMITER ';');

-- pn_perfil (tabela 2): por categoria e ano. Mediana do valor 2b por compra (compras com valor > 0); % do valor 2b em
-- compras por registro de precos (srp); % do valor em bens = valor dos resultados de itens de material / valor dos
-- resultados do escopo da categoria.
CREATE OR REPLACE TABLE itm_tipo AS
SELECT id_compra_item, material_ou_servico FROM read_parquet('itens_dedup.parquet');
CREATE OR REPLACE TABLE bens AS
SELECT r.segmento AS categoria, p.ano,
  sum(r.v) FILTER (WHERE t.material_ou_servico = 'M') AS v_bens, sum(r.v) AS v_total,
  sum(r.v * p.fator) FILTER (WHERE t.material_ou_servico = 'M') AS vd_bens, sum(r.v * p.fator) AS vd_total
FROM res_cat_valid r JOIN pb p USING (id_compra) LEFT JOIN itm_tipo t USING (id_compra_item)
WHERE r.v > 0 AND p.hom > 0 GROUP BY ALL;
CREATE OR REPLACE TABLE pn_perfil AS
SELECT s.categoria, s.ano, s.n_compras_valor_positivo, s.mediana_nominal, s.mediana_deflacionado,
  s.pct_srp_nominal, s.pct_srp_deflacionado,
  100 * b.v_bens / b.v_total AS pct_bens_nominal, 100 * b.vd_bens / b.vd_total AS pct_bens_deflacionado
FROM (SELECT segmento AS categoria, ano, count(*) FILTER (WHERE v_2b > 0) AS n_compras_valor_positivo,
        median(v_2b) FILTER (WHERE v_2b > 0) AS mediana_nominal, median(v_2b_defl) FILTER (WHERE v_2b > 0) AS mediana_deflacionado,
        100 * coalesce(sum(v_2b) FILTER (WHERE srp), 0) / sum(v_2b) AS pct_srp_nominal,
        100 * coalesce(sum(v_2b_defl) FILTER (WHERE srp), 0) / sum(v_2b_defl) AS pct_srp_deflacionado
      FROM sv GROUP BY ALL HAVING sum(v_2b) > 0) s
LEFT JOIN bens b USING (categoria, ano) ORDER BY ALL;
COPY pn_perfil TO 'tabelas_painel_v3/pn_perfil.csv' (HEADER, DELIMITER ';');
-- valores por compra (2b > 0), para a mediana e o percentual em registro de precos de periodos com mais de um ano
-- (tabela 2 em formato largo; a mediana nao se agrega entre anos)
COPY (SELECT segmento AS categoria, ano, v_2b AS valor_nominal, v_2b_defl AS valor_deflacionado, srp
      FROM sv WHERE v_2b > 0 ORDER BY ALL) TO 'tabelas_painel_v3/pn_perfil_valores_por_compra.csv' (HEADER, DELIMITER ';');
COPY (SELECT categoria, ano, v_bens AS valor_bens_nominal, v_total AS valor_resultados_nominal,
             vd_bens AS valor_bens_deflacionado, vd_total AS valor_resultados_deflacionado FROM bens ORDER BY ALL)
  TO 'tabelas_painel_v3/pn_perfil_bens.csv' (HEADER, DELIMITER ';');

-- pn_orgaos (tabela 3): valor 2b por categoria, ano e orgao comprador
CREATE OR REPLACE TABLE pn_orgaos AS
SELECT segmento AS categoria, ano, orgao, esfera, sum(v_2b) AS valor_nominal, sum(v_2b_defl) AS valor_deflacionado, count(*) AS n_compras
FROM sv WHERE v_2b > 0 GROUP BY ALL ORDER BY ALL;
COPY pn_orgaos TO 'tabelas_painel_v3/pn_orgaos.csv' (HEADER, DELIMITER ';');

-- ---------------------------------------------------------------- grafico 10: instrumentos de politica
-- Escopo de itens por categoria: compra com termo no objeto = todos os itens; so itens = itens da categoria.
CREATE OR REPLACE TABLE esc AS
SELECT DISTINCT c.segmento, i.id_compra, i.id_compra_item FROM cat_compra c
JOIN read_parquet('itens_dedup.parquet') i USING (id_compra) WHERE c.local_match IN ('objeto', 'ambos')
UNION
SELECT DISTINCT m.segmento, m.id_compra, m.id_compra_item FROM item_match m
JOIN cat_compra c ON c.id_compra = m.id_compra AND c.segmento = m.segmento AND c.local_match = 'item';
CREATE OR REPLACE TABLE esc_campos AS
SELECT e.*, i.margem_preferencia_normal AS mpn, i.margem_preferencia_adicional AS mpa, i.incentivo_produtivo_basico AS ppb
FROM esc e JOIN read_parquet('itens_dedup.parquet') i USING (id_compra_item);
-- flags por compra x categoria: margem prevista (normal ou adicional = true em algum item do escopo), PPB (true em
-- algum item do escopo), margem aplicada (aplicacao_margem_preferencia = true em algum resultado do escopo)
CREATE OR REPLACE TABLE flg AS
SELECT e.segmento, e.id_compra,
  bool_or(e.mpn = 'true' OR e.mpa = 'true') AS margem_prevista,
  bool_or(e.ppb = 'true') AS ppb,
  bool_or(r.aplicacao_margem_preferencia = 'true') AS margem_aplicada
FROM esc_campos e LEFT JOIN res r USING (id_compra_item) GROUP BY ALL;
CREATE OR REPLACE TABLE flg_u AS
SELECT id_compra, bool_or(margem_prevista) AS margem_prevista, bool_or(ppb) AS ppb, bool_or(margem_aplicada) AS margem_aplicada
FROM flg GROUP BY 1;
CREATE OR REPLACE TABLE pn_instrumentos AS
SELECT 'todas' AS recorte, u.ano,
  sum(u.v_2a) AS valor_nominal, sum(u.v_2a_defl) AS valor_deflacionado,
  sum(u.v_2a) FILTER (WHERE f.margem_prevista) AS margem_prevista_nominal, sum(u.v_2a_defl) FILTER (WHERE f.margem_prevista) AS margem_prevista_deflacionado,
  sum(u.v_2a) FILTER (WHERE f.margem_aplicada) AS margem_aplicada_nominal, sum(u.v_2a_defl) FILTER (WHERE f.margem_aplicada) AS margem_aplicada_deflacionado,
  sum(u.v_2a) FILTER (WHERE f.ppb) AS ppb_nominal, sum(u.v_2a_defl) FILTER (WHERE f.ppb) AS ppb_deflacionado
FROM su u LEFT JOIN flg_u f USING (id_compra) GROUP BY ALL
UNION ALL
SELECT s.segmento, s.ano, sum(s.v_2b), sum(s.v_2b_defl),
  sum(s.v_2b) FILTER (WHERE f.margem_prevista), sum(s.v_2b_defl) FILTER (WHERE f.margem_prevista),
  sum(s.v_2b) FILTER (WHERE f.margem_aplicada), sum(s.v_2b_defl) FILTER (WHERE f.margem_aplicada),
  sum(s.v_2b) FILTER (WHERE f.ppb), sum(s.v_2b_defl) FILTER (WHERE f.ppb)
FROM sv s LEFT JOIN flg f USING (segmento, id_compra) GROUP BY ALL
ORDER BY ALL;
COPY pn_instrumentos TO 'tabelas_painel_v3/pn_instrumentos.csv' (HEADER, DELIMITER ';');

-- preenchimento dos campos (itens e resultados do escopo das seis categorias, compras nao excluidas)
CREATE OR REPLACE TABLE pn_instrumentos_preenchimento AS
WITH it AS (SELECT DISTINCT e.id_compra_item, e.mpn, e.mpa, e.ppb FROM esc_campos e JOIN pb p USING (id_compra) WHERE p.hom > 0),
rs AS (SELECT DISTINCT r.id_compra_item, r.ni_fornecedor, r.v, r.aplicacao_margem_preferencia
       FROM res r JOIN (SELECT DISTINCT id_compra_item FROM esc) e USING (id_compra_item) JOIN pb p USING (id_compra) WHERE p.hom > 0)
SELECT 'margem de preferência prevista no edital' AS indicador, 'itens: margem_preferencia_normal e margem_preferencia_adicional' AS campo,
  count(*) AS n_registros, count(*) FILTER (WHERE nullif(trim(mpn), '') IS NOT NULL AND nullif(trim(mpa), '') IS NOT NULL) AS n_preenchidos,
  count(*) FILTER (WHERE mpn = 'true' OR mpa = 'true') AS n_verdadeiro FROM it
UNION ALL
SELECT 'margem de preferência aplicada no resultado', 'resultados: aplicacao_margem_preferencia', count(*),
  count(*) FILTER (WHERE nullif(trim(aplicacao_margem_preferencia), '') IS NOT NULL),
  count(*) FILTER (WHERE aplicacao_margem_preferencia = 'true') FROM rs
UNION ALL
SELECT 'exigência de Processo Produtivo Básico (PPB)', 'itens: incentivo_produtivo_basico', count(*),
  count(*) FILTER (WHERE nullif(trim(ppb), '') IS NOT NULL), count(*) FILTER (WHERE ppb = 'true') FROM it;
COPY pn_instrumentos_preenchimento TO 'tabelas_painel_v3/pn_instrumentos_preenchimento.csv' (HEADER, DELIMITER ';');

-- margem de preferencia por NCM (regra de p0_19): itens de material do escopo das seis categorias, compras nao
-- excluidas; NCM coberto por prefixo de resolucao CICS vigente na data da compra. Camada (a): NCM informado no item;
-- camada (b): NCM do item e, na falta, do tradutor CATMAT->NCM. Valor = homologado dos resultados do item (itm_val).
CREATE OR REPLACE TABLE ncm_seg AS
SELECT DISTINCT e.segmento, m.id_compra_item, m.id_compra, m.ano, m.elegivel, m.origem_ncm
FROM mg_itens m JOIN esc e USING (id_compra_item)
WHERE NOT m.excl_h AND m.material_ou_servico = 'M';
CREATE OR REPLACE TABLE pn_margem_ncm AS
WITH x AS (
  SELECT 'todas' AS recorte, id_compra_item, any_value(id_compra) AS id_compra, any_value(ano) AS ano,
         any_value(elegivel) AS elegivel, any_value(origem_ncm) AS origem_ncm FROM ncm_seg GROUP BY 2
  UNION ALL SELECT segmento, id_compra_item, id_compra, ano, elegivel, origem_ncm FROM ncm_seg)
SELECT x.recorte, x.ano,
  sum(coalesce(v.v, 0)) FILTER (WHERE x.elegivel AND x.origem_ncm = 'ncm_do_item') AS ncm_item_nominal,
  sum(coalesce(v.v, 0) * p.fator) FILTER (WHERE x.elegivel AND x.origem_ncm = 'ncm_do_item') AS ncm_item_deflacionado,
  sum(coalesce(v.v, 0)) FILTER (WHERE x.elegivel) AS ncm_item_tradutor_nominal,
  sum(coalesce(v.v, 0) * p.fator) FILTER (WHERE x.elegivel) AS ncm_item_tradutor_deflacionado,
  sum(coalesce(v.v_margem, 0)) AS margem_aplicada_material_nominal,
  sum(coalesce(v.v_margem, 0) * p.fator) AS margem_aplicada_material_deflacionado,
  sum(coalesce(v.v, 0)) AS valor_itens_material_nominal,
  sum(coalesce(v.v, 0) * p.fator) AS valor_itens_material_deflacionado
FROM x LEFT JOIN itm_val v USING (id_compra_item) JOIN pb p USING (id_compra)
GROUP BY ALL ORDER BY ALL;
COPY pn_margem_ncm TO 'tabelas_painel_v3/pn_margem_ncm.csv' (HEADER, DELIMITER ';');

-- nota: encomenda tecnologica e CPSI nas seis categorias. Busca por mencao explicita no amparo legal (nome e
-- descricao), na modalidade e no objeto/informacao complementar (texto em minusculas, sem acentos):
--   encomenda tecnologica: 'encomenda tecnologica'; CPSI: 'solucao inovadora', 'cpsi' ou 'lei complementar 182'.
-- Para transparencia, informa-se tambem o numero de compras com amparo no art. 75, V, da Lei 14.133/2021 (dispensa
-- para cumprimento da Lei 10.973/2004, que inclui a encomenda tecnologica), sem mencao explicita ao instrumento.
CREATE OR REPLACE TABLE enc AS
SELECT p.id_compra, p.ano, p.modalidade, p.amparo_legal_nome, p.hom, left(p.objeto_compra, 300) AS objeto,
  regexp_matches(t.txt, 'encomenda tecnologica') AS encomenda,
  regexp_matches(t.txt, 'solucao inovadora|\bcpsi\b|lei complementar (n[o.º]* ?)?182') AS cpsi,
  regexp_matches(strip_accents(lower(coalesce(p.amparo_legal_nome, ''))), 'art\. 75, v$') AS art75v
FROM pb p JOIN (
  SELECT id_compra, strip_accents(lower(coalesce(amparo_legal_nome,'') || ' ' || coalesce(amparo_legal_descricao,'') || ' '
         || modalidade || ' ' || coalesce(objeto_compra,'') || ' ' || coalesce(informacao_complementar,''))) AS txt
  FROM pb) t USING (id_compra)
WHERE p.id_compra IN (SELECT id_compra FROM cat_compra);
CREATE OR REPLACE TABLE pn_encomenda AS
SELECT 'encomenda tecnológica (menção explícita)' AS instrumento, count(*) FILTER (WHERE encomenda) AS n_compras,
  coalesce(sum(hom) FILTER (WHERE encomenda), 0) AS valor_nominal FROM enc
UNION ALL SELECT 'contrato público para solução inovadora (CPSI) (menção explícita)', count(*) FILTER (WHERE cpsi),
  coalesce(sum(hom) FILTER (WHERE cpsi), 0) FROM enc
UNION ALL SELECT 'dispensa com amparo no art. 75, V, da Lei 14.133/2021', count(*) FILTER (WHERE art75v),
  coalesce(sum(hom) FILTER (WHERE art75v), 0) FROM enc;
COPY pn_encomenda TO 'tabelas_painel_v3/pn_encomenda_cpsi.csv' (HEADER, DELIMITER ';');
COPY (SELECT id_compra, ano, modalidade, amparo_legal_nome, hom AS homologado_limpo, encomenda, cpsi, art75v, objeto
      FROM enc WHERE encomenda OR cpsi OR art75v ORDER BY 1) TO 'tabelas_painel_v3/pn_encomenda_cpsi_compras.csv' (HEADER, DELIMITER ';');

SELECT * FROM pn_controles;
SELECT * FROM pn_soberania_tres_regras;
SELECT * FROM pn_instrumentos_preenchimento;
SELECT recorte, sum(ncm_item_nominal), sum(ncm_item_tradutor_nominal), sum(margem_aplicada_material_nominal) FROM pn_margem_ncm GROUP BY 1 ORDER BY 1;
SELECT * FROM pn_encomenda;
