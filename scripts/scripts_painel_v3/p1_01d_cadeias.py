"""Painel v3, etapa 1d: base da Tabela 2 (maiores cadeias fornecedor -> objeto -> orgao comprador).
Executar a partir de Processado/, depois de p1_01 e p1_01b:  python scripts_painel_v3/p1_01d_cadeias.py
Entradas: scripts_parte0/p0.duckdb (somente leitura: rc, res_cat_valid, pb, bl, forn_nome); resultados_dedup.parquet (porte).
Regras (a mesma base do grafico 11, pn_fluxo):
  - resultados vigentes e nao cancelados das compras da categoria, valor do resultado > 0, compras sem valor excluido;
  - fornecedor agrupado pela raiz do CNPJ (8 primeiros digitos; CPF e codigos que nao sao CNPJ ficam como estao);
    nome da raiz = nome do CNPJ de maior valor na base; porte da raiz = porte do PNCP de maior valor nos resultados da
    raiz na base ('ME ou EPP', 'Demais' ou 'Não informado');
  - objeto = objeto da compra registrado no PNCP (texto livre), com espacos repetidos reduzidos a um.
Controle: agrupada por categoria x ano x CNPJ x orgao x esfera, a tabela reproduz valor e numero de compras de pn_fluxo.csv.
Saidas: tabelas_painel_v3/pn_cadeias_compras.csv (categoria; ano; cnpj_fornecedor; raiz_cnpj; orgao; esfera; id_compra;
  valor_nominal; valor_deflacionado), pn_cadeias_objetos.csv (id_compra; objeto), pn_fornecedor_raiz.csv (raiz_cnpj; nome; porte)
"""
import csv

import duckdb

TP = "tabelas_painel_v3/"
con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
RAIZ = "CASE WHEN regexp_full_match(ni, '[0-9]{14}') THEN substr(ni, 1, 8) ELSE ni END"
cad = con.sql(f"""
SELECT segmento, ano, ni, {RAIZ} AS raiz, orgao, esfera, id_compra, sum(v), sum(v_defl)
FROM rc GROUP BY ALL ORDER BY ALL""").fetchall()
obj = con.sql(r"""
SELECT id_compra, trim(regexp_replace(objeto_compra, '\s+', ' ', 'g')) FROM bl WHERE id_compra IN (SELECT id_compra FROM rc) ORDER BY 1""").fetchall()
raiz = con.sql(f"""
WITH r AS (SELECT {RAIZ} AS raiz, ni, sum(v) AS v FROM rc GROUP BY ALL),
nome AS (SELECT r.raiz, arg_max(coalesce(f.nome, CASE WHEN r.ni = 'ND' THEN 'Fornecedor não identificado' ELSE r.ni END), r.v) AS nome
         FROM r LEFT JOIN forn_nome f ON f.ni = r.ni GROUP BY 1),
po AS (SELECT CASE WHEN regexp_full_match(c.ni_fornecedor, '[0-9]{{14}}') THEN substr(c.ni_fornecedor, 1, 8) ELSE c.ni_fornecedor END AS raiz,
         CASE WHEN d.porte_fornecedor_nome IN ('ME', 'EPP') THEN 'ME ou EPP' WHEN d.porte_fornecedor_nome = 'Demais' THEN 'Demais' ELSE 'Não informado' END AS porte,
         sum(c.v) AS v
       FROM res_cat_valid c JOIN pb p USING (id_compra)
       LEFT JOIN (SELECT DISTINCT id_compra_item, ni_fornecedor, porte_fornecedor_nome FROM read_parquet('resultados_dedup.parquet')) d
         ON d.id_compra_item = c.id_compra_item AND d.ni_fornecedor = c.ni_fornecedor
       WHERE c.v > 0 AND p.hom > 0 GROUP BY ALL)
SELECT nome.raiz, nome.nome, coalesce((SELECT arg_max(porte, v) FROM po WHERE po.raiz = nome.raiz), 'Não informado')
FROM nome ORDER BY 1""").fetchall()
con.close()

# controle com pn_fluxo.csv
fl = {(r["categoria"], r["ano"], r["cnpj_fornecedor"], r["orgao"], r["esfera"]): (float(r["valor_nominal"]), int(r["n_compras"]))
      for r in csv.DictReader(open(TP + "pn_fluxo.csv", encoding="utf-8"), delimiter=";")}
ag = {}
for c, a, ni, rz, o, e, comp, v, vd in cad:
    k = (c, str(a), ni, o, e)
    x = ag.setdefault(k, [0.0, set()])
    x[0] += v
    x[1].add(comp)
assert set(ag) == set(fl) and all(abs(ag[k][0] - fl[k][0]) < 0.01 and len(ag[k][1]) == fl[k][1] for k in fl), "cadeias nao reproduzem pn_fluxo"
assert {x[6] for x in cad} == {x[0] for x in obj} and all(x[1] for x in obj)


def grava(nome, cab, rows):
    with open(TP + nome, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)


grava("pn_cadeias_compras.csv", ["categoria", "ano", "cnpj_fornecedor", "raiz_cnpj", "orgao", "esfera", "id_compra", "valor_nominal", "valor_deflacionado"], cad)
grava("pn_cadeias_objetos.csv", ["id_compra", "objeto"], obj)
grava("pn_fornecedor_raiz.csv", ["raiz_cnpj", "nome", "porte"], raiz)
print(len(cad), "linhas;", len(obj), "compras;", len(raiz), "raizes de CNPJ;", len(fl), "fluxos conferidos com pn_fluxo")
