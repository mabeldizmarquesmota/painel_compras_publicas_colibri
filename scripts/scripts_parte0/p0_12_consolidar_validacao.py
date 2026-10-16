"""Consolida a verificacao por amostragem.

1. Preenche a coluna classificacao_manual (pertinente / nao_pertinente) e acrescenta motivo_manual nos arquivos
   originais validacao/validacao_<segmento>.csv (amostra 1, sorteada na etapa 4).
2. Grava validacao/precisao_por_categoria.csv com a precisao final de cada categoria, medida na ultima amostra
   independente sorteada da classificacao final, e o historico das amostras anteriores.

Regra: a precisao final de cada categoria vem de uma amostra que nao foi usada para ajustar o dicionario.
- identidade: dicionario nao alterado -> amostra 1.
- nuvem e plataformas: ajustadas apos a amostra 1 -> amostra 2 (sorteada da classificacao final dessas categorias).
- data_center e seguranca: ajustadas apos as amostras 1 e 2 -> amostra 3.
- ia: ajustada apos as amostras 1, 2 e 3 -> amostra 4.
Executar a partir de Processado/.
"""
import csv
import glob
import os

AMOSTRAS = {  # rotulo -> arquivo de julgamentos consolidado por p0_04_precisao.py
    "amostra1": "validacao/amostra1_julgamentos.csv",
    "amostra2": "validacao/amostra2_julgamentos.csv",
    "amostra3": "validacao/amostra3_julgamentos.csv",
    "amostra4": "validacao/amostra4_julgamentos.csv",
}
FINAL = {"identidade": "amostra1", "nuvem": "amostra2", "plataformas": "amostra2",
         "data_center": "amostra3", "seguranca": "amostra3", "ia": "amostra4"}
NOMES = {"ia": "Inteligencia artificial", "nuvem": "Nuvem", "plataformas": "Plataformas e licenciamento",
         "identidade": "Identidade e infraestrutura publica digital", "data_center": "Data center",
         "seguranca": "Seguranca cibernetica"}
DICIONARIO = {"amostra1": "original (etapa 4)", "amostra2": "ajuste 1", "amostra3": "ajuste 2",
              "amostra4": "ajuste 3 (final)"}

jul = {}
for rot, arq in AMOSTRAS.items():
    with open(arq, encoding="utf-8") as f:
        for r in csv.DictReader(f, delimiter=";"):
            jul.setdefault(rot, {}).setdefault(r["segmento"], []).append(r)

# 1. preencher classificacao_manual na amostra 1 original
j1 = {(r["segmento"], r["id_compra"]): r for seg in jul["amostra1"].values() for r in seg}
for arq in sorted(glob.glob("validacao/validacao_*.csv")):
    with open(arq, encoding="utf-8") as f:
        linhas = list(csv.DictReader(f))
    campos = list(linhas[0].keys())
    if "motivo_manual" not in campos:
        campos.append("motivo_manual")
    for r in linhas:
        j = j1.get((r["segmento"], r["id_compra"]))
        if j is None:  # compra sem registro em base_limpa (sem ano e sem valor): nao avaliada
            r["classificacao_manual"] = "nao_avaliada"
            r["motivo_manual"] = "compra ausente de base_limpa"
        else:
            r["classificacao_manual"] = j["classificacao_manual"]
            r["motivo_manual"] = j["motivo"]
    with open(arq, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(linhas)

# 2. precisao final e historico
saida = []
for seg in ["ia", "nuvem", "plataformas", "identidade", "data_center", "seguranca"]:
    hist = []
    for rot in AMOSTRAS:
        rs = jul.get(rot, {}).get(seg)
        if rs:
            p = sum(r["classificacao_manual"] == "pertinente" for r in rs)
            hist.append((rot, len(rs), p))
    rot_f = FINAL[seg]
    n, p = next((n, p) for r, n, p in hist if r == rot_f)
    saida.append({
        "categoria": seg, "nome": NOMES[seg],
        "amostra_final": rot_f, "dicionario_da_amostra_final": DICIONARIO[rot_f],
        "n_revisadas": n, "n_pertinentes": p, "precisao_pct": round(100.0 * p / n, 1),
        "historico": "; ".join(f"{r} ({DICIONARIO[r]}): {pp}/{nn} = {100.0*pp/nn:.1f}%".replace(".", ",") for r, nn, pp in hist),
        "dicionario_ajustado": "nao" if seg == "identidade" else "sim",
    })
with open("validacao/precisao_por_categoria.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(saida[0]), delimiter=";")
    w.writeheader()
    w.writerows(saida)
for s in saida:
    print(s["categoria"], s["precisao_pct"], "|", s["historico"])
