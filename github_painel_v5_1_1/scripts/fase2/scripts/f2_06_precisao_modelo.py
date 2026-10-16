"""Fase 2, etapa 6: precisao do modelo de aquisicao por classe e rodada de validacao; situacao final de cada classe.
Executar a partir de Processado/:  python fase2/scripts/f2_06_precisao_modelo.py
Entradas: fase2/validacao/julgamentos_modelo_f2_modelo_a1.csv, _a2.csv, _a3.csv (julgamentos um a um);
  fase2/f2.duckdb (modelo_item_v1, v2, v3) para conferir a versao do dicionario medida em cada rodada.
Regra (E): precisao = itens pertinentes / itens julgados, por classe e rodada. Classe abaixo de 80% tem o dicionario
  ajustado e e medida em nova amostra independente (sem itens de amostras anteriores). Classe que nao atinge 80% apos
  dois ajustes fica fora do painel. A precisao final de cada classe e a da ultima rodada em que a classe foi medida;
  a rodada vale para a versao final quando a regra da classe nao mudou depois dela (ver METODOLOGIA_fase2.md).
Saida: fase2/tabelas/f2_06_precisao_modelo.csv (classe; rodada; dicionario; julgados; pertinentes; precisao_pct)
       fase2/tabelas/f2_06_situacao_classes.csv (classe; precisao_final_pct; rodada_final; situacao; motivo)
"""
import csv

RODADAS = [("a1", "v1"), ("a2", "v2"), ("a3", "v3")]
NOMES = {1: "Acréscimo a licença existente", 2: "Subscrição ou serviço", 3: "Licenciamento de direitos permanentes de uso", 4: "Suporte e manutenção de licença",
         5: "Desenvolvimento e serviços técnicos", 6: "Equipamentos e infraestrutura física", 7: "Não identificado"}
linhas = []
res = {}
for rod, dic in RODADAS:
    j = list(csv.DictReader(open(f"fase2/validacao/julgamentos_modelo_f2_modelo_{rod}.csv", encoding="utf-8"), delimiter=";"))
    for o in sorted({int(r["ordem"]) for r in j}):
        rr = [r for r in j if int(r["ordem"]) == o]
        k = sum(r["pertinente"] == "sim" for r in rr)
        p = 100 * k / len(rr)
        linhas.append([o, NOMES[o], rod, dic, len(rr), k, round(p, 1)])
        res[(o, rod)] = p
# classe 4, versao 3: todos os 47 itens ja estavam nas amostras 1 e 2 (nao ha amostra independente);
# precisao na propria amostra de ajuste, so como informacao
import duckdb  # noqa: E402

con = duckdb.connect("fase2/f2.duckdb", read_only=True)
v3_4 = {r[0] for r in con.sql("SELECT id_compra_item FROM modelo_item_v3 WHERE ordem = 4").fetchall()}
jul = {}
for rod, _ in RODADAS[:2]:
    for r in csv.DictReader(open(f"fase2/validacao/julgamentos_modelo_f2_modelo_{rod}.csv", encoding="utf-8"), delimiter=";"):
        if r["ordem"] == "4" or r["id_compra_item"] in v3_4:
            jul.setdefault(r["id_compra_item"], (r["ordem"], r["pertinente"], r["motivo"]))
# itens da classe 4 v3 julgados em outra classe: pertinentes para a classe 4 quando o motivo aponta a classe 4
k4 = sum(1 for i in v3_4 if jul[i][1] == "sim" and jul[i][0] == "4" or (jul[i][0] != "4" and "classe 4" in jul[i][2]))
assert v3_4 <= set(jul), "item da classe 4 v3 sem julgamento anterior"
linhas.append([4, NOMES[4], "a1+a2 (mesmos itens do ajuste)", "v3", len(v3_4), k4, round(100 * k4 / len(v3_4), 1)])
FINAL = {1: "a1", 2: "a2", 3: "a3", 5: "a2", 6: "a2", 7: "a3"}
sit = []
for o in range(1, 8):
    if o == 4:
        sit.append([o, NOMES[o], "", "", "fora do painel",
                    f"Abaixo de 80% na amostra 1 ({res[(4, 'a1')]:.0f}%) e na amostra 2 ({res[(4, 'a2')]:.0f}%); após o segundo ajuste a classe ficou com "
                    f"{len(v3_4)} itens, todos já julgados nas amostras usadas para o ajuste, sem amostra independente possível."])
        continue
    p = res[(o, FINAL[o])]
    sit.append([o, NOMES[o], round(p, 1), FINAL[o], "aprovada" if p >= 80 else "fora do painel", ""])
with open("fase2/tabelas/f2_06_precisao_modelo.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ordem", "classe", "rodada", "dicionario", "julgados", "pertinentes", "precisao_pct"])
    w.writerows(linhas)
with open("fase2/tabelas/f2_06_situacao_classes.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ordem", "classe", "precisao_final_pct", "rodada_final", "situacao", "motivo"])
    w.writerows(sit)
for l in linhas:
    print(l)
for s in sit:
    print(s)
