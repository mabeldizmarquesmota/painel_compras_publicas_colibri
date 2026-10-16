"""Fase 2, etapa 7 (B): valor, itens e compras por modelo de aquisicao e categoria, com as regras de soma do painel.
Executar a partir de Processado/, depois de f2_04 (rotulo v3) e f2_06:  python fase2/scripts/f2_07_modelo_valores.py
Entradas: fase2/f2.duckdb (itens_escopo, compras_escopo, modelo_item_v3); p0.duckdb anexado somente para leitura
  (compra_unica: valor sem dupla contagem); fase2/tabelas/f2_06_situacao_classes.csv.
Regras:
  - por categoria (regra do painel por categoria, 2b): o valor de cada compra x categoria (v_2b) e repartido entre as
    classes dos itens do escopo da categoria na proporcao do valor homologado dos resultados de cada item; sem valor de
    resultado em nenhum item, na proporcao do valor total estimado do item; sem nenhum dos dois, ou sem itens no escopo,
    o valor fica em 'Sem itens com valor para repartir'. A soma por categoria reproduz o painel.
  - total sem dupla contagem (2a): o mesmo, com o valor v_2a de cada compra repartido entre os itens distintos do escopo
    da compra em todas as categorias. A soma reproduz o KPI do painel.
  - itens = pares item x categoria do escopo; compras = compras com ao menos um item da classe no escopo da categoria.
  - classe 4 calculada, mas marcada 'fora do painel' (f2_06).
Saidas: fase2/tabelas/f2_07_modelo_categoria.csv; fase2/tabelas/f2_07_modelo_total_sem_dupla_contagem.csv;
        fase2/tabelas/f2_07_controles.csv
"""
import csv

import duckdb

con = duckdb.connect("fase2/f2.duckdb")
con.sql("ATTACH 'scripts_parte0/p0.duckdb' AS p (READ_ONLY)")
sit = {int(r["ordem"]): r["situacao"] for r in csv.DictReader(open("fase2/tabelas/f2_06_situacao_classes.csv", encoding="utf-8"), delimiter=";")}
SEM = "Sem itens com valor para repartir"
con.sql("""
CREATE OR REPLACE TEMP TABLE it AS
SELECT e.segmento, e.id_compra, e.id_compra_item, m.ordem, m.classe, e.v_resultados AS vr, coalesce(e.valor_total_estimado, 0) AS ve
FROM itens_escopo e JOIN modelo_item_v3 m USING (id_compra_item)""")
# repartição 2b por compra x categoria
con.sql(f"""
CREATE OR REPLACE TABLE modelo_valor_cat AS
WITH tot AS (SELECT segmento, id_compra, sum(greatest(vr, 0)) AS svr, sum(greatest(ve, 0)) AS sve FROM it GROUP BY ALL),
pes AS (SELECT it.*, CASE WHEN t.svr > 0 THEN greatest(it.vr, 0) / t.svr WHEN t.sve > 0 THEN greatest(it.ve, 0) / t.sve END AS w
        FROM it JOIN tot t USING (segmento, id_compra))
SELECT c.segmento, c.id_compra, coalesce(p.ordem, 0) AS ordem, coalesce(p.classe, '{SEM}') AS classe, p.id_compra_item,
  c.v_2b * coalesce(p.w, 1) AS valor
FROM compras_escopo c LEFT JOIN pes p ON p.segmento = c.segmento AND p.id_compra = c.id_compra AND p.w IS NOT NULL""")
# repartição 2a por compra (itens distintos de todas as categorias)
con.sql(f"""
CREATE OR REPLACE TABLE modelo_valor_2a AS
WITH di AS (SELECT DISTINCT id_compra, id_compra_item, ordem, classe, vr, ve FROM it),
tot AS (SELECT id_compra, sum(greatest(vr, 0)) AS svr, sum(greatest(ve, 0)) AS sve FROM di GROUP BY 1),
pes AS (SELECT di.*, CASE WHEN t.svr > 0 THEN greatest(di.vr, 0) / t.svr WHEN t.sve > 0 THEN greatest(di.ve, 0) / t.sve END AS w
        FROM di JOIN tot t USING (id_compra))
SELECT u.id_compra, coalesce(p.ordem, 0) AS ordem, coalesce(p.classe, '{SEM}') AS classe, p.id_compra_item, u.v_2a * coalesce(p.w, 1) AS valor
FROM p.compra_unica u LEFT JOIN pes p ON p.id_compra = u.id_compra AND p.w IS NOT NULL""")

ctl = []
for seg, a, b in con.sql("""SELECT c.segmento, (SELECT sum(valor) FROM modelo_valor_cat m WHERE m.segmento = c.segmento), sum(c.v_2b)
                            FROM compras_escopo c GROUP BY 1 ORDER BY 1""").fetchall():
    ctl.append([f"soma por categoria = painel (2b), {seg}", round(a, 2), round(b, 2), "sim" if abs(a - b) < 1 else "não"])
a = con.sql("SELECT sum(valor) FROM modelo_valor_2a").fetchone()[0]
b = con.sql("SELECT sum(v_2a) FROM p.compra_unica").fetchone()[0]
ctl.append(["total sem dupla contagem = KPI do painel (2a)", round(a, 2), round(b, 2), "sim" if abs(a - b) < 1 else "não"])
assert all(c[3] == "sim" for c in ctl), ctl

cat = con.sql("""
WITH v AS (SELECT segmento, ordem, classe, sum(valor) AS valor, count(DISTINCT id_compra) FILTER (WHERE id_compra_item IS NOT NULL) AS compras_valor
           FROM modelo_valor_cat GROUP BY ALL),
n AS (SELECT segmento, ordem, count(*) AS itens, count(DISTINCT id_compra) AS compras FROM it GROUP BY ALL),
t AS (SELECT segmento, sum(valor) AS tv FROM modelo_valor_cat GROUP BY 1)
SELECT v.segmento, v.ordem, v.classe, coalesce(n.itens, 0), coalesce(n.compras, (SELECT count(DISTINCT id_compra) FROM modelo_valor_cat x
  WHERE x.segmento = v.segmento AND x.ordem = 0)), v.valor, 100 * v.valor / t.tv
FROM v JOIN t USING (segmento) LEFT JOIN n ON n.segmento = v.segmento AND n.ordem = v.ordem ORDER BY 1, 2""").fetchall()
tot = con.sql("""
WITH v AS (SELECT ordem, classe, sum(valor) AS valor FROM modelo_valor_2a GROUP BY ALL),
n AS (SELECT ordem, count(DISTINCT id_compra_item) AS itens, count(DISTINCT id_compra) AS compras FROM it GROUP BY 1)
SELECT v.ordem, v.classe, coalesce(n.itens, 0), coalesce(n.compras, (SELECT count(DISTINCT id_compra) FROM modelo_valor_2a WHERE ordem = 0)),
  v.valor, 100 * v.valor / (SELECT sum(valor) FROM modelo_valor_2a)
FROM v LEFT JOIN n USING (ordem) ORDER BY 1""").fetchall()
st = lambda o: "sem classe" if o == 0 else sit[o]
with open("fase2/tabelas/f2_07_modelo_categoria.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["categoria", "ordem", "classe", "situacao", "itens", "compras", "valor_homologado_nominal", "pct_da_categoria"])
    w.writerows([[r[0], r[1], r[2], st(r[1])] + list(r[3:]) for r in cat])
with open("fase2/tabelas/f2_07_modelo_total_sem_dupla_contagem.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ordem", "classe", "situacao", "itens_distintos", "compras", "valor_homologado_nominal", "pct_do_total"])
    w.writerows([[r[0], r[1], st(r[0])] + list(r[2:]) for r in tot])
with open("fase2/tabelas/f2_07_controles.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["controle", "fase2", "painel", "igual"])
    w.writerows(ctl)
for c in ctl:
    print(c)
for r in tot:
    print(r)
con.close()
