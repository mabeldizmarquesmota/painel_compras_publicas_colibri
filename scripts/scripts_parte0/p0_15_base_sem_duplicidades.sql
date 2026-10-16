-- Base de analise sem duplicidades e totais homologados por ano.
-- Executar depois de p0_01 e p0_14, a partir de Processado/:
--   duckdb scripts_parte0/p0.duckdb < scripts_parte0/p0_15_base_sem_duplicidades.sql
-- Entradas: tabelas bs e bl_completa (p0_01) e dup_remover (p0_14).
-- Regra: as compras de dup_remover (republicacoes: cinco campos iguais e mesmos vencedores) saem da base de analise.
--        base_limpa.parquet nao e alterado; a exclusao e feita aqui e vale para todos os scripts seguintes (tabela bl).
-- Saidas: tabelas_parte0/p0_totais_homologados_ano.csv e tabelas_parte0/p0_exclusoes_por_motivo_ano.csv
--         (mesmas definicoes de p0_01, agora sem duplicidades); tabela bl.

CREATE OR REPLACE TABLE bl AS
SELECT * FROM bl_completa WHERE id_compra NOT IN (SELECT id_compra FROM dup_remover);

CREATE OR REPLACE TABLE bs_dedup AS
SELECT * FROM bs WHERE id_compra NOT IN (SELECT id_compra FROM dup_remover);

CREATE OR REPLACE TABLE p0_totais_ano AS
SELECT ano,
  count(*) AS n_compras_publicadas,
  count(*) FILTER (WHERE situacao_homologado = 'valido') AS n_compras_homologado_valido,
  count(*) FILTER (WHERE situacao_homologado = 'sem_homologacao') AS n_compras_sem_homologacao,
  count(*) FILTER (WHERE situacao_homologado = 'excluido_auditoria') AS n_compras_homologado_excluido,
  sum(valor_homologado) FILTER (WHERE valor_homologado > 0) AS homologado_bruto,
  sum(valor_homologado) FILTER (WHERE situacao_homologado = 'excluido_auditoria') AS homologado_excluido,
  sum(hom_limpo_recalc) FILTER (WHERE hom_limpo_recalc > 0) AS homologado_limpo
FROM bs_dedup GROUP BY ano ORDER BY ano;

CREATE OR REPLACE TABLE p0_exclusoes_motivo AS
SELECT ano,
  CASE WHEN coalesce(validacao_csv,'') = 'erro_provavel' AND NOT coalesce(flag_valor_suspeito,false) THEN 'revisao_manual_erro_provavel'
       WHEN regra_1_valor_preenchimento THEN 'regra_1_valor_preenchimento'
       WHEN regra_2_divergencia_estimado_homologado THEN 'regra_2_divergencia (sem regra 1)'
       ELSE 'regra_3_inconsistencia_itens (sem regras 1 e 2)' END AS motivo_principal,
  count(*) AS n_compras, sum(valor_homologado) AS valor_homologado_bruto_excluido
FROM bs_dedup WHERE situacao_homologado = 'excluido_auditoria'
GROUP BY ALL ORDER BY ano, motivo_principal;

COPY p0_totais_ano TO 'tabelas_parte0/p0_totais_homologados_ano.csv' (HEADER, DELIMITER ';');
COPY p0_exclusoes_motivo TO 'tabelas_parte0/p0_exclusoes_por_motivo_ano.csv' (HEADER, DELIMITER ';');
SELECT (SELECT count(*) FROM bl_completa) AS compras_base_completa, (SELECT count(*) FROM bl) AS compras_sem_duplicidades;
SELECT * FROM p0_totais_ano;
