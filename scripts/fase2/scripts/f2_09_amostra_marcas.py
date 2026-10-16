"""Fase 2, etapa 9 (E): amostras de validacao de marca e tipo de vendedor (fichas para julgamento um a um).
Executar a partir de Processado/, depois de f2_08:  python fase2/scripts/f2_09_amostra_marcas.py <semente> [fichas_anteriores...]
Entradas: fase2/f2.duckdb (res_marca, res_tipo, itens_escopo, compras_escopo).
Regra: 100 compras com mencao a marca e 50 compras com vencedor classificado como empresa publica de TI, sorteadas por
  md5(id_compra || semente), sem compras de fichas anteriores. Cada ficha mostra o objeto, os itens com marca (trecho do
  texto em que a marca aparece e origem item/objeto) e os vencedores com o tipo atribuido.
Saida: fase2/validacao/fichas_marcas_<semente>.csv
"""
import csv
import re
import sys
import unicodedata

import duckdb

sem = sys.argv[1]
ant = set()
for a in sys.argv[2:]:
    ant |= {r["id_compra"] for r in csv.DictReader(open(a, encoding="utf-8"), delimiter=";")}
con = duckdb.connect("fase2/f2.duckdb", read_only=True)
dic = list(csv.DictReader(open("fase2/dicionario_marcas.csv", encoding="utf-8"), delimiter=";"))
RE = {}
for r in dic:
    if r["tipo"] == "inclusao":
        RE.setdefault(r["marca"], []).append(re.compile(r["expressao"]))


def norm(t):
    t = unicodedata.normalize("NFKD", (t or "").replace("\xa0", " ")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


def trecho(t, m):
    t = norm(t)
    for p in RE[m]:
        x = p.search(t)
        if x:
            return t[max(0, x.start() - 70): x.end() + 70]
    return ""


def sorteia(q, n):
    ids = [r[0] for r in con.sql(q).fetchall() if r[0] not in ant]
    return ids[:n]


grupos = [("marca", sorteia(f"SELECT DISTINCT id_compra FROM res_marca ORDER BY md5(id_compra || '{sem}')", 100)),
          ("empresa publica de TI", sorteia(f"SELECT DISTINCT id_compra FROM res_tipo WHERE tipo = 'Empresa pública de TI' ORDER BY md5(id_compra || '{sem}')", 50))]
out = []
for grupo, ids in grupos:
    for k, c in enumerate(ids):
        ob = con.sql(f"SELECT any_value(objeto_compra) FROM compras_escopo WHERE id_compra = '{c}'").fetchone()[0] or ""
        if grupo == "marca":
            its = con.sql(f"""SELECT m.marca, m.origem, any_value(concat_ws(' | ', i.descricao, i.descricao_resumida, i.descricao_detalhada)) AS t, sum(DISTINCT m.v) AS v
                FROM res_marca m JOIN (SELECT DISTINCT ON (id_compra_item) * FROM itens_escopo) i USING (id_compra_item)
                WHERE m.id_compra = '{c}' GROUP BY m.marca, m.origem ORDER BY v DESC""").fetchall()
            marc = " || ".join(f"{m} ({o}): ...{trecho(t if o == 'item' else ob, m)}..." for m, o, t, v in its)
            ven = " || ".join(f"{n} [{ni}] {m}: {tp}" for n, ni, m, tp in con.sql(
                f"SELECT DISTINCT nome_fornecedor, ni_fornecedor, marca, tipo FROM res_marca WHERE id_compra = '{c}' ORDER BY 1, 3").fetchall())
        else:
            marc = ""
            ven = " || ".join(f"{n} [{ni}]: {tp}" for n, ni, tp in con.sql(
                f"SELECT DISTINCT nome_fornecedor, ni_fornecedor, tipo FROM res_tipo WHERE id_compra = '{c}' ORDER BY 1").fetchall())
        out.append([grupo, k, c, re.sub(r"\s+", " ", ob)[:250], marc[:900], ven[:700], sem])
with open(f"fase2/validacao/fichas_marcas_{sem}.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["grupo", "ficha", "id_compra", "objeto", "marcas_e_trechos", "vencedores_e_tipos", "semente"])
    w.writerows(out)
print(len(out), "fichas")
