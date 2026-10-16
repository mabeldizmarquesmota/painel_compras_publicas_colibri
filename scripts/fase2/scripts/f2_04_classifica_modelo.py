"""Fase 2, etapa 4: classificacao do modelo de aquisicao por item (seis categorias).
Executar a partir de Processado/:  python fase2/scripts/f2_04_classifica_modelo.py <arquivo_do_dicionario> <rotulo>
  ex.: python fase2/scripts/f2_04_classifica_modelo.py fase2/dicionario_modelo_aquisicao_v1.csv v1
Entradas: fase2/f2.duckdb (itens_escopo); dicionario (f2_03 e ajustes).
Regra: texto do item = descricao + descricao resumida + descricao detalhada + unidade de medida, em minusculas, sem
  acentos, espacos colapsados (o objeto da compra e normalizado da mesma forma). Classe = primeira, na ordem 1 a 6, com
  alguma subregra (coluna 'sub'; sem a coluna, subregra unica) em que ha inclusao, nenhuma exclusao no item, nenhuma
  'exclusao_objeto' no objeto, ao menos uma 'exige' (quando houver) e o tipo de item exigido (quando houver);
  sem classe = 7 (Nao identificado).
  A classificacao e do item (independe da categoria); cada item distinto e classificado uma vez.
Saidas: fase2/f2.duckdb, tabela modelo_item_<rotulo> (id_compra_item, ordem, classe, termo);
        fase2/tabelas/f2_04_modelo_contagem_<rotulo>.csv (itens distintos por classe)
"""
import csv
import re
import sys
import unicodedata

import duckdb

arq, rot = sys.argv[1], sys.argv[2]
dic = list(csv.DictReader(open(arq, encoding="utf-8"), delimiter=";"))
NOMES = {}
REG = {}  # (ordem, sub) -> regras
for r in dic:
    o = int(r["ordem"])
    NOMES[o] = r["classe"]
    d = REG.setdefault((o, r.get("sub") or "a"), {"inclusao": [], "exclusao": [], "exclusao_objeto": [], "exige": [], "material": None})
    if r["tipo"] == "material":
        d["material"] = r["expressao"]
    else:
        d[r["tipo"]].append(re.compile(r["expressao"]))
NOMES[7] = "Não identificado"


def norm(t):
    t = unicodedata.normalize("NFKD", (t or "").replace("\xa0", " ")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def classe(texto, mat, objeto):
    for o, sub in sorted(REG):
        d = REG[(o, sub)]
        if d["material"] and mat != d["material"]:
            continue
        hit = next((p.pattern for p in d["inclusao"] if p.search(texto)), None)
        if not hit or any(p.search(texto) for p in d["exclusao"]) or any(p.search(objeto) for p in d["exclusao_objeto"]):
            continue
        if d["exige"] and not any(p.search(texto) for p in d["exige"]):
            continue
        return o, hit
    return 7, ""


con = duckdb.connect("fase2/f2.duckdb")
itens = con.sql("""SELECT DISTINCT i.id_compra_item, concat_ws(' | ', i.descricao, i.descricao_resumida, i.descricao_detalhada, i.unidade_medida) AS t,
  i.material_ou_servico, b.objeto_compra
FROM itens_escopo i JOIN (SELECT DISTINCT id_compra, objeto_compra FROM compras_escopo) b USING (id_compra)""").fetchall()
out = []
for i, t, m, ob in itens:
    o, termo = classe(norm(t), m, norm(ob))
    out.append((i, o, NOMES[o], termo))
con.sql(f"CREATE OR REPLACE TABLE modelo_item_{rot} (id_compra_item VARCHAR, ordem INTEGER, classe VARCHAR, termo VARCHAR)")
con.executemany(f"INSERT INTO modelo_item_{rot} VALUES (?, ?, ?, ?)", out)
cont = con.sql(f"SELECT ordem, classe, count(*) FROM modelo_item_{rot} GROUP BY ALL ORDER BY 1").fetchall()
with open(f"fase2/tabelas/f2_04_modelo_contagem_{rot}.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ordem", "classe", "itens_distintos"])
    w.writerows(cont)
for c in cont:
    print(c)
con.close()
