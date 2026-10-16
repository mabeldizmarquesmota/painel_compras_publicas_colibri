"""Fase 2, etapa 10 (D): compras e valor por porte do fornecedor vencedor e categoria.
Executar a partir de Processado/, depois de f2_01:  python fase2/scripts/f2_10_porte.py
Entrada: fase2/f2.duckdb (res_venda: resultados das seis categorias na base do grafico 9, com porte_fornecedor_nome do PNCP).
Regra: porte como registrado no resultado (campo porte_fornecedor_nome do PNCP), com ME e EPP numa classe unica
  ('ME ou EPP'), porque a fonte quase nao registra EPP (frequencia do campo na base inteira em
  f2_10_porte_frequencia_base.csv); Demais; 'Nao Informado',
  'Nao se aplica' e vazio ficam em 'Porte nao informado'. Valor = valor homologado dos resultados; compras = compras com
  ao menos um resultado vencido por fornecedor do porte (uma compra com vencedores de portes diferentes conta em cada um).
  Linha 'Seis categorias' conta cada resultado uma vez.
Saidas: fase2/tabelas/f2_10_porte_categoria.csv; fase2/tabelas/f2_10_porte_frequencia_base.csv (todos os resultados da base)
"""
import csv

import duckdb

con = duckdb.connect("fase2/f2.duckdb", read_only=True)
# ME e EPP em classe unica: a fonte registra EPP em parcela muito pequena dos resultados (ver f2_10_porte_frequencia_base.csv)
P = "CASE WHEN porte_fornecedor_nome IN ('ME', 'EPP') THEN 'ME ou EPP' WHEN porte_fornecedor_nome = 'Demais' THEN 'Demais' ELSE 'Porte não informado' END"
rows = con.sql(f"""
WITH r AS (SELECT segmento, id_compra, id_compra_item, ni_fornecedor, v, {P} AS porte FROM res_venda),
c AS (SELECT segmento, porte, count(DISTINCT id_compra) AS compras, count(DISTINCT ni_fornecedor) AS fornecedores, sum(v) AS valor FROM r GROUP BY ALL),
t AS (SELECT segmento, sum(v) AS tv FROM r GROUP BY 1),
u AS (SELECT DISTINCT id_compra, id_compra_item, ni_fornecedor, v, porte FROM r),
g AS (SELECT 'Seis categorias' AS segmento, porte, count(DISTINCT id_compra) AS compras, count(DISTINCT ni_fornecedor) AS fornecedores, sum(v) AS valor FROM u GROUP BY ALL)
SELECT c.*, 100 * c.valor / t.tv FROM c JOIN t USING (segmento)
UNION ALL SELECT g.*, 100 * g.valor / (SELECT sum(v) FROM u) FROM g
ORDER BY 1, 2""").fetchall()
with open("fase2/tabelas/f2_10_porte_categoria.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["categoria", "porte", "compras", "fornecedores", "valor_homologado_resultados", "pct_do_valor"])
    w.writerows(rows)
for r in rows:
    print(r[0], r[1], r[2], r[3], round(r[4] / 1e6), round(r[5], 1))

freq = con.sql("""SELECT coalesce(porte_fornecedor_nome, '(vazio)') AS porte, count(*) AS resultados, 100.0 * count(*) / sum(count(*)) OVER () AS pct
  FROM read_parquet('resultados_dedup.parquet') GROUP BY 1 ORDER BY 2 DESC""").fetchall()
with open("fase2/tabelas/f2_10_porte_frequencia_base.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["porte_fornecedor_nome", "resultados", "pct_dos_resultados"])
    w.writerows(freq)
for r in freq:
    print(r)
