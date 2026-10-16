"""Fase 2, etapa 1: base de trabalho das novas classificacoes (escopo das seis categorias).
Executar a partir de Processado/:  python fase2/scripts/f2_01_base_escopo.py
Entradas: scripts_parte0/p0.duckdb, anexado SOMENTE PARA LEITURA (tabelas bl, bv, cat_compra, item_match, cat_valor,
  compra_unica, res_cat_valid); itens_dedup.parquet e resultados_dedup.parquet (Processado/).
Regras (as mesmas do painel; nada e recalculado de outro modo):
  - escopo de itens de cada compra x categoria: termo no objeto (objeto ou ambos) = todos os itens da compra;
    termo so nos itens = itens classificados na categoria (item_match);
  - valor do item = soma do valor homologado dos resultados vigentes do item (mesma fonte de p0_07);
  - resultados do escopo = res_cat_valid (p0_07), com porte, natureza juridica e nome do fornecedor lidos de
    resultados_dedup.parquet; base "quem vende" = resultados com valor > 0 em compras com homologado limpo > 0
    (a mesma base do grafico 9 do painel).
Controles: soma e contagem dos resultados reproduzem res_cat_valid e o total do grafico 9 (pn_fluxo).
Saidas: fase2/f2.duckdb (tabelas itens_escopo, compras_escopo, res_escopo); fase2/tabelas/f2_01_controles.csv
"""
import csv
import os

import duckdb

os.makedirs("fase2/tabelas", exist_ok=True)
con = duckdb.connect("fase2/f2.duckdb")
con.sql("ATTACH 'scripts_parte0/p0.duckdb' AS p (READ_ONLY)")

con.sql("""
CREATE OR REPLACE TABLE itens AS
SELECT id_compra, id_compra_item, descricao, descricao_detalhada, descricao_resumida, material_ou_servico,
  cod_item_catalogo, codigo_classe, codigo_grupo, quantidade, valor_unitario_estimado, valor_total, unidade_medida
FROM read_parquet('itens_dedup.parquet')""")

con.sql("""
CREATE OR REPLACE TABLE res_item AS  -- valor do item: soma dos resultados vigentes (como item_val em p0_07)
SELECT id_compra_item, sum(TRY_CAST(valor_total_homologado AS DOUBLE)) AS v
FROM read_parquet('resultados_dedup.parquet') WHERE TRY_CAST(valor_total_homologado AS DOUBLE) IS NOT NULL GROUP BY 1""")

con.sql("""
CREATE OR REPLACE TABLE compras_escopo AS
SELECT v.segmento, v.id_compra, v.local_match, v.ano, v.hom, v.v_2b,
  b.objeto_compra, b.informacao_complementar, b.orgao, b.modalidade
FROM p.cat_valor v JOIN p.bl b USING (id_compra)""")

con.sql("""
CREATE OR REPLACE TABLE itens_escopo AS
WITH esc AS (
  SELECT c.segmento, i.id_compra, i.id_compra_item FROM p.cat_compra c JOIN itens i USING (id_compra)
  WHERE c.local_match IN ('objeto', 'ambos')
  UNION
  SELECT m.segmento, m.id_compra, m.id_compra_item FROM p.cat_compra c
  JOIN p.item_match m ON m.id_compra = c.id_compra AND m.segmento = c.segmento WHERE c.local_match = 'item')
SELECT e.segmento, e.id_compra, e.id_compra_item, i.descricao, i.descricao_detalhada, i.descricao_resumida,
  i.material_ou_servico, i.cod_item_catalogo, i.codigo_classe, i.codigo_grupo, i.unidade_medida,
  TRY_CAST(i.quantidade AS DOUBLE) AS quantidade, TRY_CAST(i.valor_unitario_estimado AS DOUBLE) AS valor_unitario_estimado,
  TRY_CAST(i.valor_total AS DOUBLE) AS valor_total_estimado, coalesce(r.v, 0) AS v_resultados
FROM esc e JOIN itens i USING (id_compra_item) LEFT JOIN res_item r USING (id_compra_item)""")

con.sql("""
CREATE OR REPLACE TABLE res_escopo AS
WITH r AS (
  SELECT id_compra, id_compra_item, coalesce(nullif(trim(ni_fornecedor), ''), 'ND') AS ni_fornecedor,
    TRY_CAST(valor_total_homologado AS DOUBLE) AS v, pais_origem_produto_servico_id, aplicacao_margem_preferencia,
    trim(nome_razao_social_fornecedor) AS nome_fornecedor, porte_fornecedor_nome, natureza_juridica_id, natureza_juridica_nome,
    quantidade_homologada, valor_unitario_homologado
  FROM read_parquet('resultados_dedup.parquet')),
esc AS (
  SELECT c.segmento, r.* FROM p.cat_compra c JOIN r USING (id_compra) WHERE c.local_match IN ('objeto', 'ambos')
  UNION ALL
  SELECT m.segmento, r.* FROM p.cat_compra c JOIN p.item_match m ON m.id_compra = c.id_compra AND m.segmento = c.segmento
  JOIN r ON r.id_compra_item = m.id_compra_item WHERE c.local_match = 'item'),
-- linhas identicas nas colunas de res_cat (p0_07 usa UNION, que as funde) entram uma vez
d AS (SELECT * FROM esc QUALIFY row_number() OVER (PARTITION BY segmento, id_compra, id_compra_item, ni_fornecedor, v,
        pais_origem_produto_servico_id, aplicacao_margem_preferencia ORDER BY nome_fornecedor, porte_fornecedor_nome, natureza_juridica_id) = 1)
SELECT d.*, b.ano, b.orgao FROM d JOIN p.bl b USING (id_compra) WHERE NOT b.excl_h""")

# base "quem vende" (grafico 9): valor > 0 e compra com homologado limpo > 0
con.sql("""
CREATE OR REPLACE TABLE res_venda AS
SELECT r.* FROM res_escopo r JOIN p.bv b USING (id_compra) WHERE r.v > 0 AND b.hom > 0""")

ctl = []
a = con.sql("SELECT count(*), sum(v) FROM res_escopo").fetchone()
b = con.sql("SELECT count(*), sum(v) FROM p.res_cat_valid").fetchone()
ctl.append(["resultados do escopo (linhas; soma)", f"{a[0]}; {a[1]:.2f}", f"{b[0]}; {b[1]:.2f}", "p0.res_cat_valid"])
v9 = sum(float(r["valor_nominal"]) for r in csv.DictReader(open("tabelas_painel_v2/pn_fluxo.csv", encoding="utf-8"), delimiter=";"))
a = con.sql("SELECT sum(v), count(DISTINCT id_compra), count(DISTINCT ni_fornecedor), count(DISTINCT orgao) FROM res_venda").fetchone()
ctl.append(["base quem vende = grafico 9 (soma; compras; fornecedores; orgaos)", f"{a[0]:.2f}; {a[1]}; {a[2]}; {a[3]}", f"{v9:.2f}; 15207; 5369; 1693", "tabelas_painel_v2/pn_fluxo.csv"])
a = con.sql("SELECT sum(v_2b), count(*) FROM compras_escopo").fetchone()
b = con.sql("SELECT sum(v_2b), count(*) FROM p.cat_valor").fetchone()
ctl.append(["compras x categoria (soma 2b; linhas)", f"{a[0]:.2f}; {a[1]}", f"{b[0]:.2f}; {b[1]}", "p0.cat_valor"])
a = con.sql("SELECT count(*), count(DISTINCT id_compra_item), count(DISTINCT id_compra) FROM itens_escopo").fetchone()
ctl.append(["itens do escopo (pares item x categoria; itens; compras)", f"{a[0]}; {a[1]}; {a[2]}", "-", "itens_dedup.parquet"])
for c in ctl:
    print(c)
assert ctl[0][1] == ctl[0][2], "res_escopo nao reproduz res_cat_valid"
assert abs(float(ctl[1][1].split(";")[0]) - v9) < 1 and ctl[1][1].split("; ")[1:] == ["15207", "5369", "1693"]
assert ctl[2][1] == ctl[2][2]
with open("fase2/tabelas/f2_01_controles.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["controle", "fase2", "referencia", "fonte_referencia"])
    w.writerows(ctl)
con.close()
