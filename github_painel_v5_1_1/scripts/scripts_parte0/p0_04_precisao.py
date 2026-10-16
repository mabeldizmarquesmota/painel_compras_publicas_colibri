"""Consolida os julgamentos manuais e calcula a precisao por categoria.

Uso (a partir de Processado/):
    python scripts_parte0/p0_04_precisao.py <fichas.csv> <pasta_julgamentos> <rotulo_amostra> <saida_prefixo>

- <fichas.csv>: fichas de revisao (separador ';'), ordenadas por segmento e id_compra.
- <pasta_julgamentos>: um arquivo <segmento>.txt por categoria. Linha "P: n1,n2,..." lista as compras
  pertinentes; as demais linhas "<motivo>: n1,n2,..." listam as nao pertinentes e o motivo. A numeracao
  segue a ordem das fichas da categoria (1 = primeira ficha da categoria).
- Cada numero de 1 a N (N = fichas da categoria) deve aparecer exatamente uma vez; caso contrario, erro.
Saidas: <saida_prefixo>_julgamentos.csv (uma linha por compra) e <saida_prefixo>_precisao.csv.
"""
import csv
import os
import sys

fichas_path, julg_dir, rotulo, saida = sys.argv[1:5]

fichas = {}
with open(fichas_path, encoding="utf-8") as f:
    for r in csv.DictReader(f, delimiter=";"):
        fichas.setdefault(r["segmento"], []).append(r)

linhas, resumo = [], []
for seg in sorted(fichas):
    arq = os.path.join(julg_dir, f"{seg}.txt")
    if not os.path.exists(arq):
        continue
    n = len(fichas[seg])
    marcado = {}
    with open(arq, encoding="utf-8") as f:
        for ln in f:
            ln = ln.strip()
            if not ln or ln.startswith("#"):
                continue
            chave, nums = ln.split(":", 1)
            for x in nums.split(","):
                x = x.strip()
                if not x:
                    continue
                k = int(x)
                if k in marcado:
                    sys.exit(f"{seg}: numero {k} repetido")
                if not 1 <= k <= n:
                    sys.exit(f"{seg}: numero {k} fora de 1..{n}")
                marcado[k] = chave.strip()
    faltam = sorted(set(range(1, n + 1)) - set(marcado))
    if faltam:
        sys.exit(f"{seg}: faltam julgamentos para {faltam}")
    n_p = 0
    for k in range(1, n + 1):
        r = fichas[seg][k - 1]
        pert = marcado[k] == "P"
        n_p += pert
        linhas.append({
            "amostra": rotulo, "segmento": seg, "ordem": k, "id_compra": r["id_compra"],
            "local_match": r["local_match"],
            "classificacao_manual": "pertinente" if pert else "nao_pertinente",
            "motivo": "" if pert else marcado[k],
        })
    resumo.append({"amostra": rotulo, "segmento": seg, "n_revisadas": n, "n_pertinentes": n_p,
                   "precisao_pct": round(100.0 * n_p / n, 1)})

campos = ["amostra", "segmento", "ordem", "id_compra", "local_match", "classificacao_manual", "motivo"]
with open(f"{saida}_julgamentos.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=campos, delimiter=";")
    w.writeheader()
    w.writerows(linhas)
with open(f"{saida}_precisao.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(resumo[0]), delimiter=";")
    w.writeheader()
    w.writerows(resumo)
for r in resumo:
    print(r)
