"""Painel v5.1, etapa 1: reconciliacao entre a categoria Inteligencia artificial do grafico 8 e a tecnologia de IA do grafico 9.

Executar a partir de Processado/:  python scripts_painel_v5_1/p51_01_reconciliacao_ia.py
Entradas (somente leitura): tabelas_painel_v3/pn_cadeias_compras.csv (base do grafico 8 por compra, controlada contra pn_fluxo.csv),
  ia_resultados.csv (base do grafico 9) e ia_base.csv (componente e classe de cada compra da aba de IA).
Regras: periodo completo, valores nominais arredondados a centavos como no painel; compras com vencedor identificado; fornecedor =
  CNPJ do vencedor; orgao = nome do orgao comprador. Grafico 8 com a categoria Inteligencia artificial; grafico 9 com o botao Todas
  (tecnologia: Acrescimo a licenca, Solucao de IA e Outros, sem Capacitacao).
Saida: tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv (linha; compras; fornecedores; orgaos; valor_nominal).
"""
import csv
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "scripts_painel_v5_1")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v5_1.formatacao import inteiro, mi  # noqa: E402

TP, T = "tabelas_painel_v3/", "tabelas_painel_v5_1/"
os.makedirs(T, exist_ok=True)
ler = lambda n: list(csv.DictReader(open(TP + n, encoding="utf-8"), delimiter=";"))
r2 = lambda x: round(float(x), 2)
g8 = [r for r in ler("pn_cadeias_compras.csv") if r["categoria"] == "ia"]
g9 = [r for r in ler("ia_resultados.csv") if r["classe"] != "Capacitação"]
base = {r["id_compra"]: r for r in ler("ia_base.csv")}
fl = sum(r2(r["valor_nominal"]) for r in ler("pn_fluxo.csv") if r["categoria"] == "ia")
assert abs(sum(r2(r["valor_nominal"]) for r in g8) - fl) < 0.01  # mesma base do grafico 8

S8, S9 = {r["id_compra"] for r in g8}, {r["id_compra"] for r in g9}
so8, so9, comum = S8 - S9, S9 - S8, S8 & S9
assert all(base[i]["componente"] == "A" and base[i]["classe"] == "Capacitação" for i in so8)  # capacitacao dentro da categoria IA
assert all(base[i]["componente"] == "C" for i in so9)  # acrescimo de IA a licenca classificado em outras categorias
v8 = lambda s: sum(r2(r["valor_nominal"]) for r in g8 if r["id_compra"] in s)
v9 = lambda s: sum(r2(r["valor_nominal"]) for r in g9 if r["id_compra"] in s)
assert abs(v8(comum) - v9(comum)) < 0.01  # nas compras comuns o valor e o mesmo nos dois graficos
conj = lambda rows, k, s=None: {r[k] for r in rows if s is None or r["id_compra"] in s}
F8, F9, O8, O9 = conj(g8, "cnpj_fornecedor"), conj(g9, "cnpj_fornecedor"), conj(g8, "orgao"), conj(g9, "orgao")
L = [
    ["gráfico 8, categoria Inteligência artificial", len(S8), len(F8), len(O8), round(v8(S8), 2)],
    ["(-) compras de capacitação classificadas na categoria IA (fora da tecnologia de IA)", -len(so8), -len(F8 - F9), -len(O8 - O9), -round(v8(so8), 2)],
    ["(+) compras de acréscimo de IA a licenças (Copilot, Gemini) classificadas em outras categorias", len(so9), len(F9 - F8), len(O9 - O8), round(v9(so9), 2)],
    ["gráfico 9, Todas (tecnologia)", len(S9), len(F9), len(O9), round(v9(S9), 2)],
    ["comuns aos dois gráficos (mesmo valor)", len(comum), len(F8 & F9), len(O8 & O9), round(v8(comum), 2)],
]
for k in range(1, 5):
    assert L[0][k] + L[1][k] + L[2][k] == L[3][k] or abs(L[0][k] + L[1][k] + L[2][k] - L[3][k]) < 0.02, k
# composicao das compras somadas por classe da aba (classe de maior valor de cada compra)
cls = {}
for i in so9:
    cls[base[i]["classe"]] = cls.get(base[i]["classe"], 0) + 1
L += [[f"   das {len(so9)} somadas, classe {c} na aba de IA", n, "", "", ""] for c, n in sorted(cls.items(), key=lambda x: -x[1])]
with open(T + "ia_reconciliacao_grafico8_grafico9.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["linha", "compras", "fornecedores", "orgaos", "valor_nominal"])
    w.writerows(L)
sys.stdout.reconfigure(encoding="utf-8")
for l in L:
    print(l[0], "|", *[inteiro(x) if isinstance(x, int) else (mi(x) if isinstance(x, float) else x) for x in l[1:]])
