"""Confere os hashes registrados das versoes congeladas v1, v2 e v3.

v1 e v2: caminhos relativos a Processado/.
v3: confere a copia em versao_congelada_v3/ e, quando existe, a copia de trabalho em Processado/.
Uso: python scripts_painel_v4/p4_00_hashes.py  (a partir de Processado/). Grava scripts_painel_v4/_hashes_ok.csv.
"""
import csv
import hashlib
import os
import sys


def sha(c):
    h = hashlib.sha256()
    with open(c, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def ler(c):
    with open(c, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


saida = []
for versao, manifesto, bases in [
    ("v1", "versao_congelada_v1/hashes_sha256_v1.csv", [""]),
    ("v2", "versao_congelada_v2/hashes_sha256_v2.csv", [""]),
    ("v3", "versao_congelada_v3/hashes_sha256_v3.csv", ["versao_congelada_v3/", ""]),
]:
    linhas = ler(manifesto)
    for base in bases:
        ok = dif = aus = 0
        for r in linhas:
            c = base + r["arquivo"]
            if not os.path.exists(c):
                aus += 1
                if base == bases[0]:
                    print("AUSENTE", c)
                continue
            if sha(c) == r["sha256"]:
                ok += 1
            else:
                dif += 1
                print("DIFERENTE", c)
        local = base or "Processado/"
        print(f"{versao} {local}: {len(linhas)} registrados, {ok} idênticos, {dif} diferentes, {aus} ausentes")
        saida.append({"versao": versao, "local": local, "registrados": len(linhas), "identicos": ok, "diferentes": dif, "ausentes": aus})

with open("scripts_painel_v4/_hashes_" + (sys.argv[1] if len(sys.argv) > 1 else "inicio") + ".csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(saida[0]), delimiter=";")
    w.writeheader()
    w.writerows(saida)
