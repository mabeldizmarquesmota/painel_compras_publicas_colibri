"""Fase 2, etapa 2 (A): existencia e preenchimento dos campos nas compras, itens e resultados das seis categorias.
Executar a partir de Processado/, depois de f2_01:  python fase2/scripts/f2_02_diagnostico_campos.py
Entrada: fase2/f2.duckdb (compras_escopo, itens_escopo, res_escopo); esquemas de base_limpa.parquet,
  itens_dedup.parquet e resultados_dedup.parquet (para registrar onde cada campo existe).
Regra: cada compra, item e resultado do escopo contado uma vez (uma compra ou item em duas categorias conta uma vez
  na linha "seis categorias"). Preenchido = valor nao nulo e nao vazio; para porte, valores validos sao ME, EPP e
  Demais ('Nao Informado' e 'Nao se aplica' contam como nao preenchidos); para natureza juridica, '0000' (nao
  informada) conta como nao preenchido; quantidade e valor unitario: numero > 0.
Saida: fase2/tabelas/f2_02_diagnostico_campos.csv (nivel; campo; existe; coluna; registros; preenchidos; pct)
       fase2/tabelas/f2_02_valores_porte_natureza.csv (distribuicao dos valores nos resultados do escopo)
"""
import csv

import duckdb

con = duckdb.connect("fase2/f2.duckdb", read_only=True)
cols = {n: {r[0] for r in con.sql(f"DESCRIBE SELECT * FROM read_parquet('{n}')").fetchall()}
        for n in ("base_limpa.parquet", "itens_dedup.parquet", "resultados_dedup.parquet")}

con.sql("CREATE TEMP TABLE c AS SELECT DISTINCT id_compra, objeto_compra FROM compras_escopo")
con.sql("""CREATE TEMP TABLE i AS SELECT DISTINCT id_compra_item, descricao, descricao_detalhada, descricao_resumida,
  material_ou_servico, cod_item_catalogo, codigo_classe, codigo_grupo, quantidade, valor_unitario_estimado FROM itens_escopo""")
con.sql("""CREATE TEMP TABLE r AS SELECT DISTINCT id_compra_item, ni_fornecedor, v, porte_fornecedor_nome, natureza_juridica_id,
  natureza_juridica_nome, quantidade_homologada, valor_unitario_homologado FROM res_escopo""")

cheio = lambda c: f"nullif(trim(CAST({c} AS VARCHAR)), '') IS NOT NULL"
pos = lambda c: f"TRY_CAST({c} AS DOUBLE) > 0"
CAMPOS = [  # nivel, campo, tabela, coluna, condicao de preenchimento
    ("compras", "porte do fornecedor", None, None, None),
    ("compras", "natureza jurídica do fornecedor", None, None, None),
    ("compras", "descrição (objeto da compra)", "c", "objeto_compra", cheio("objeto_compra")),
    ("itens", "porte do fornecedor", None, None, None),
    ("itens", "natureza jurídica do fornecedor", None, None, None),
    ("itens", "tipo de item (material/serviço)", "i", "material_ou_servico", "material_ou_servico IN ('M', 'S')"),
    ("itens", "código CATMAT/CATSER (item do catálogo)", "i", "cod_item_catalogo", cheio("cod_item_catalogo")),
    ("itens", "código da classe do catálogo", "i", "codigo_classe", cheio("codigo_classe")),
    ("itens", "código do grupo do catálogo", "i", "codigo_grupo", cheio("codigo_grupo")),
    ("itens", "descrição do item", "i", "descricao", cheio("descricao")),
    ("itens", "descrição detalhada do item", "i", "descricao_detalhada", cheio("descricao_detalhada")),
    ("itens", "descrição resumida do item", "i", "descricao_resumida", cheio("descricao_resumida")),
    ("itens", "alguma descrição (descrição, detalhada ou resumida)", "i", "descricao", "(" + cheio("descricao") + " OR " + cheio("descricao_detalhada") + " OR " + cheio("descricao_resumida") + ")"),
    ("itens", "quantidade", "i", "quantidade", pos("quantidade")),
    ("itens", "valor unitário estimado", "i", "valor_unitario_estimado", pos("valor_unitario_estimado")),
    ("resultados", "porte do fornecedor", "r", "porte_fornecedor_nome", "porte_fornecedor_nome IN ('ME', 'EPP', 'Demais')"),
    ("resultados", "natureza jurídica do fornecedor", "r", "natureza_juridica_id", cheio("natureza_juridica_id") + " AND natureza_juridica_id <> '0000'"),
    ("resultados", "quantidade homologada", "r", "quantidade_homologada", pos("quantidade_homologada")),
    ("resultados", "valor unitário homologado", "r", "valor_unitario_homologado", pos("valor_unitario_homologado")),
]
ARQ = {"compras": "base_limpa.parquet", "itens": "itens_dedup.parquet", "resultados": "resultados_dedup.parquet"}
out = []
for nivel, campo, t, col, cond in CAMPOS:
    if t is None:
        out.append([nivel, campo, "não", f"campo inexistente em {ARQ[nivel]}", "", "", ""])
        continue
    assert col in cols[ARQ[nivel]] or t == "c", col
    n, k = con.sql(f"SELECT count(*), count(*) FILTER (WHERE {cond}) FROM {t}").fetchone()
    out.append([nivel, campo, "sim", col, n, k, round(100 * k / n, 1)])
with open("fase2/tabelas/f2_02_diagnostico_campos.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["nivel", "campo", "existe", "coluna", "registros", "preenchidos", "pct_preenchido"])
    w.writerows(out)
dist = con.sql("""SELECT 'porte' AS campo, coalesce(porte_fornecedor_nome, '(nulo)') AS valor, count(*) AS resultados, sum(v) AS valor_homologado FROM r GROUP BY ALL
UNION ALL SELECT 'natureza_juridica', coalesce(natureza_juridica_id || ' ' || natureza_juridica_nome, '(nulo)'), count(*), sum(v) FROM r GROUP BY ALL
ORDER BY 1, 3 DESC""").fetchall()
with open("fase2/tabelas/f2_02_valores_porte_natureza.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["campo", "valor", "resultados", "valor_homologado"])
    w.writerows(dist)
for o in out:
    print(o)
for d in dist[:30]:
    print(d)
