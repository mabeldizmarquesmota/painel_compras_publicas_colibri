"""Painel v2, etapa 1b: compras de cada fluxo do grafico 9 (Sankey), para contar compras distintas em qualquer recorte.
Executar a partir de Processado/, depois de p1_01:  python scripts_painel_v3/p1_01b_fluxo_compras.py
Entrada: tabela rc do banco de trabalho scripts_parte0/p0.duckdb (resultados das seis categorias, criada por p1_01),
  aberto somente para leitura; tabelas_painel_v3/pn_fluxo.csv.
Regra: a mesma base do Sankey (pn_fluxo): resultados vigentes e nao cancelados das compras da categoria, valor do
  resultado > 0, compras sem valor excluido; fornecedor = CNPJ do vencedor; orgao = orgao comprador da compra.
  Uma linha por categoria x ano x fornecedor x orgao x esfera x compra (as mesmas chaves de pn_fluxo).
Controle: agrupada, a tabela reproduz linha a linha o numero de compras de pn_fluxo.csv (coluna n_compras).
Saida: tabelas_painel_v3/pn_fluxo_compras.csv
"""
import csv

import duckdb

TP = "tabelas_painel_v3/"
con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
linhas = con.sql("""
SELECT DISTINCT segmento AS categoria, ano, ni AS cnpj_fornecedor, orgao, esfera, id_compra
FROM rc ORDER BY ALL""").fetchall()
con.close()

# controle: mesmas chaves e mesmo numero de compras de pn_fluxo.csv
n = {}
for c, a, f, o, e, _ in linhas:
    n[(c, str(a), f, o, e)] = n.get((c, str(a), f, o, e), 0) + 1
fluxo = {(r["categoria"], r["ano"], r["cnpj_fornecedor"], r["orgao"], r["esfera"]): int(r["n_compras"])
         for r in csv.DictReader(open(TP + "pn_fluxo.csv", encoding="utf-8"), delimiter=";")}
assert n == fluxo, "pn_fluxo_compras nao reproduz pn_fluxo.csv"

with open(TP + "pn_fluxo_compras.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["categoria", "ano", "cnpj_fornecedor", "orgao", "esfera", "id_compra"])
    w.writerows(linhas)
print(len(linhas), "linhas;", len({x[5] for x in linhas}), "compras;", len(fluxo), "fluxos conferidos")
