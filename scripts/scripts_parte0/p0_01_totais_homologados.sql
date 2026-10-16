-- Recalculo das colunas limpas e totais homologados por ano (base completa, antes da
-- remocao de duplicidades; os totais finais, sem duplicidades, sao gravados por p0_15).
-- Executar a partir de Processado/:  duckdb p0.duckdb < scripts_parte0/p0_01_totais_homologados.sql
-- Entradas: base_limpa.parquet (compras vigentes deduplicadas, com flags das regras automaticas 1 a 3)
--           auditoria_revisao_manual_proposta.csv (revisao manual das compras acima de R$ 1 bi)
-- Regra (METODOLOGIA.md, "Correcao 29/09/2026"): valor homologado limpo = NULL quando
--   flag_valor_suspeito = true (regras 1 a 3) OU validacao_proposta = 'erro_provavel'.
-- As colunas limpas sao recalculadas aqui a partir das flags e do CSV e comparadas com as gravadas.

CREATE OR REPLACE TABLE aud AS
SELECT id_compra, validacao_proposta AS validacao_csv
FROM read_csv('auditoria_revisao_manual_proposta.csv', header=true, all_varchar=true);

CREATE OR REPLACE TABLE b0 AS
SELECT b.*, a.validacao_csv
FROM read_parquet('base_limpa.parquet') b
LEFT JOIN aud a USING (id_compra);

-- regra de exclusao recalculada
CREATE OR REPLACE TABLE b AS
SELECT *,
  (coalesce(flag_valor_suspeito, false) OR coalesce(validacao_csv, '') = 'erro_provavel') AS excl_h_recalc,
  CASE WHEN coalesce(flag_valor_suspeito, false) OR coalesce(validacao_csv, '') = 'erro_provavel'
       THEN NULL ELSE valor_homologado END AS hom_limpo_recalc
FROM b0;

-- ---------- Controles de consistencia (todos devem retornar 0) ----------
CREATE OR REPLACE TABLE p0_controles AS
SELECT 'ids_csv_ausentes_na_base' AS controle,
       (SELECT count(*) FROM aud WHERE id_compra NOT IN (SELECT id_compra FROM b)) AS n
UNION ALL SELECT 'validacao_csv_diferente_da_gravada',
       (SELECT count(*) FROM b WHERE coalesce(validacao_csv,'#') <> coalesce(validacao_proposta,'#'))
UNION ALL SELECT 'flag_diferente_da_uniao_das_regras',
       (SELECT count(*) FROM b WHERE coalesce(flag_valor_suspeito,false) <>
            (coalesce(regra_1_valor_preenchimento,false) OR coalesce(regra_2_divergencia_estimado_homologado,false)
             OR coalesce(regra_3_inconsistencia_itens,false)))
UNION ALL SELECT 'homologado_limpo_recalculado_diferente_do_gravado',
       (SELECT count(*) FROM b WHERE hom_limpo_recalc IS DISTINCT FROM valor_homologado_limpo)
UNION ALL SELECT 'excluido_recalculado_diferente_do_gravado',
       (SELECT count(*) FROM b WHERE excl_h_recalc <> coalesce(excluido_homologado,false))
UNION ALL SELECT 'ano_diferente_do_ano_de_publicacao',
       (SELECT count(*) FROM b WHERE ano <> year(TRY_CAST(left(data_publicacao_pncp,10) AS DATE)))
UNION ALL SELECT 'id_compra_duplicado',
       (SELECT count(*) - count(DISTINCT id_compra) FROM b);

-- ---------- Situacao do valor homologado por compra ----------
-- valido: homologado limpo > 0
-- sem_homologacao: homologado bruto nulo ou zero (compra publicada sem homologacao registrada)
-- excluido_auditoria: homologado bruto > 0, mas excluido pelas regras 1 a 3 ou pela revisao manual
CREATE OR REPLACE TABLE bs AS
SELECT *,
  CASE WHEN hom_limpo_recalc > 0 THEN 'valido'
       WHEN coalesce(valor_homologado, 0) <= 0 THEN 'sem_homologacao'
       ELSE 'excluido_auditoria' END AS situacao_homologado
FROM b;

CREATE OR REPLACE TABLE p0_totais_ano AS
SELECT ano,
  count(*) AS n_compras_publicadas,
  count(*) FILTER (WHERE situacao_homologado = 'valido') AS n_compras_homologado_valido,
  count(*) FILTER (WHERE situacao_homologado = 'sem_homologacao') AS n_compras_sem_homologacao,
  count(*) FILTER (WHERE situacao_homologado = 'excluido_auditoria') AS n_compras_homologado_excluido,
  sum(valor_homologado) FILTER (WHERE valor_homologado > 0) AS homologado_bruto,
  sum(valor_homologado) FILTER (WHERE situacao_homologado = 'excluido_auditoria') AS homologado_excluido,
  sum(hom_limpo_recalc) FILTER (WHERE hom_limpo_recalc > 0) AS homologado_limpo
FROM bs GROUP BY ano ORDER BY ano;

-- exclusoes por motivo (para a trilha dos numeros)
CREATE OR REPLACE TABLE p0_exclusoes_motivo AS
SELECT ano,
  CASE WHEN coalesce(validacao_csv,'') = 'erro_provavel' AND NOT coalesce(flag_valor_suspeito,false) THEN 'revisao_manual_erro_provavel'
       WHEN regra_1_valor_preenchimento THEN 'regra_1_valor_preenchimento'
       WHEN regra_2_divergencia_estimado_homologado THEN 'regra_2_divergencia (sem regra 1)'
       ELSE 'regra_3_inconsistencia_itens (sem regras 1 e 2)' END AS motivo_principal,
  count(*) AS n_compras, sum(valor_homologado) AS valor_homologado_bruto_excluido
FROM bs WHERE situacao_homologado = 'excluido_auditoria'
GROUP BY ALL ORDER BY ano, motivo_principal;

COPY p0_controles TO 'tabelas_parte0/p0_controles_base_limpa.csv' (HEADER, DELIMITER ';');
COPY p0_totais_ano TO 'tabelas_parte0/p0_totais_homologados_ano_base_completa.csv' (HEADER, DELIMITER ';');
COPY p0_exclusoes_motivo TO 'tabelas_parte0/p0_exclusoes_por_motivo_ano_base_completa.csv' (HEADER, DELIMITER ';');

-- base completa (antes da remocao de duplicidades); a base de trabalho bl e criada por p0_15
CREATE OR REPLACE TABLE bl_completa AS
SELECT id_compra, ano, orgao, esfera_codigo, poder_codigo, modalidade, objeto_compra,
       informacao_complementar, srp, amparo_legal_nome, amparo_legal_descricao,
       TRY_CAST(left(data_publicacao_pncp,10) AS DATE) AS data_pub,
       valor_homologado, hom_limpo_recalc AS hom_limpo, excl_h_recalc AS excl_h, situacao_homologado
FROM bs;

SELECT * FROM p0_controles;
SELECT * FROM p0_totais_ano;
