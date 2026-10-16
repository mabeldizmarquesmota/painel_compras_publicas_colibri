"""Fase 2, etapa 5: amostra de validacao do modelo de aquisicao (fichas para julgamento um a um).
Executar a partir de Processado/:
  python fase2/scripts/f2_05_amostra_modelo.py <rotulo_classificacao> <semente> [classes] [fichas_anteriores...]
  ex.: python fase2/scripts/f2_05_amostra_modelo.py v1 f2_modelo_a1
Entradas: fase2/f2.duckdb (modelo_item_<rotulo>, itens_escopo, compras_escopo).
Regra: por classe, 100 itens distintos (ou todos, se houver menos), em ordem de md5(id_compra_item || semente);
  semente fixa e registrada. Itens que ja estiveram em fichas anteriores (arquivos passados como argumento) nao
  entram (amostra independente). 'classes' = lista de ordens separadas por virgula (padrao: 1 a 7).
Saida: fase2/validacao/fichas_modelo_<semente>.csv (uma linha por item; colunas de julgamento vazias)
"""
import csv
import os
import sys

import duckdb

rot, semente = sys.argv[1], sys.argv[2]
classes = [int(x) for x in sys.argv[3].split(",")] if len(sys.argv) > 3 and sys.argv[3] else list(range(1, 8))
anteriores = set()
for a in sys.argv[4:]:
    anteriores |= {r["id_compra_item"] for r in csv.DictReader(open(a, encoding="utf-8"), delimiter=";")}
con = duckdb.connect("fase2/f2.duckdb", read_only=True)
con.sql("CREATE TEMP TABLE ant (id_compra_item VARCHAR)")
if anteriores:
    con.executemany("INSERT INTO ant VALUES (?)", [(x,) for x in anteriores])
rows = con.sql(f"""
WITH it AS (SELECT DISTINCT ON (id_compra_item) id_compra_item, id_compra, material_ou_servico, unidade_medida,
              concat_ws(' | ', descricao, descricao_resumida, descricao_detalhada) AS texto FROM itens_escopo ORDER BY id_compra_item, segmento),
ob AS (SELECT DISTINCT ON (id_compra) id_compra, objeto_compra FROM compras_escopo ORDER BY id_compra, segmento),
s AS (SELECT m.ordem, m.classe, m.termo, it.*, ob.objeto_compra,
        row_number() OVER (PARTITION BY m.ordem ORDER BY md5(m.id_compra_item || '{semente}')) AS k
      FROM modelo_item_{rot} m JOIN it USING (id_compra_item) JOIN ob USING (id_compra)
      WHERE m.id_compra_item NOT IN (SELECT id_compra_item FROM ant) AND m.ordem IN ({','.join(map(str, classes))}))
SELECT ordem, classe, id_compra_item, id_compra, material_ou_servico, unidade_medida, termo,
  left(regexp_replace(texto, '\\s+', ' ', 'g'), 400), left(regexp_replace(objeto_compra, '\\s+', ' ', 'g'), 160)
FROM s WHERE k <= 100 ORDER BY ordem, k""").fetchall()
os.makedirs("fase2/validacao", exist_ok=True)
with open(f"fase2/validacao/fichas_modelo_{semente}.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ordem", "classe", "id_compra_item", "id_compra", "material_ou_servico", "unidade_medida", "termo", "texto_item",
                "objeto_compra", "semente"])
    w.writerows([list(r) + [semente] for r in rows])
print(len(rows), "fichas")
