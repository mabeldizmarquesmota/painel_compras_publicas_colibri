"""Painel v3, etapa 8: principais achados e nota da linha-resumo da aba Inteligencia artificial.
Executar a partir de Processado/, depois de p1_06 e p1_07:  python scripts_painel_v3/p1_08_ia_achados.py
Entradas: tabelas_painel_v3/ia_base.csv, ia_base_classes.csv, ia_resultados.csv, ia_fornecedores.csv, ia_reconciliacao.csv.
Regras: periodo completo (2021 a 2026), valores nominais; cada numero gravado com o arquivo de origem e a base de valor:
  valor homologado repartido pelas classes (ia_base_classes) ou valor dos resultados (ia_resultados). Cada achado tem no
  maximo 30 palavras. Tecnologia de IA = classes Acrescimo a licenca, Solucao de IA e Outros; Capacitacao em IA = classe Capacitacao.
Saidas: tabelas_painel_v3/ia_achados.csv (achado; titulo; texto); ia_achados_numeros.csv (achado; indicador; valor_exibido;
  arquivo_de_origem; base); ia_nota_resumo.csv (componente; compras; valor_nominal; valor_deflacionado), usada no "i" da linha-resumo.
"""
import csv
import sys

sys.path.insert(0, "scripts_painel_v3")
from painel_compras_publicas_colibri.scripts.scripts_painel_v3.formatacao import bi, fmt_pct, inteiro, mi  # noqa: E402

TP = "tabelas_painel_v3/"
ler = lambda n: list(csv.DictReader(open(TP + n, encoding="utf-8"), delimiter=";"))
f = float
CAP, ACR, SOL = "Capacitação", "Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)"
base = {r["id_compra"]: r for r in ler("ia_base.csv")}
partes = ler("ia_base_classes.csv")
res = ler("ia_resultados.csv")
r2 = lambda x: round(f(x), 2)  # valores embutidos no painel, arredondados a centavos
v_cls = {}
for r in partes:
    v_cls[r["classe"]] = v_cls.get(r["classe"], 0) + r2(r["valor_nominal"])
n_cls = {}
for r in base.values():
    n_cls[r["classe"]] = n_cls.get(r["classe"], 0) + 1
tec_v = sum(v for k, v in v_cls.items() if k != CAP)
tec_n = sum(n for k, n in n_cls.items() if k != CAP)
# acrescimo por tipo de objeto
v_acr_tipo = {}
for r in partes:
    if r["classe"] == ACR:
        t = base[r["id_compra"]]["tipo_objeto"]
        v_acr_tipo[t] = v_acr_tipo.get(t, 0) + r2(r["valor_nominal"])
# concentracao dos fornecedores (raiz do CNPJ) no valor dos resultados da tecnologia de IA
vf = {}
for r in res:
    if r["classe"] != CAP:
        vf[r["raiz_cnpj"]] = vf.get(r["raiz_cnpj"], 0) + r2(r["valor_nominal"])
tot_res = sum(vf.values())
top10 = sum(sorted(vf.values(), reverse=True)[:10])
NUM = []


def n(a, ind, val, arq, base_v):
    NUM.append([a, ind, val, arq, base_v])
    return val


HC, RS = "valor homologado repartido pelas classes", "valor dos resultados"
ACH = [
    ("1", "Solução de IA lidera a tecnologia de IA",
     f"De 2021 a 2026, a tecnologia de IA somou {n('1', 'valor da tecnologia de IA', mi(tec_v), 'ia_base_classes.csv', HC)} em {n('1', 'compras de tecnologia de IA', inteiro(tec_n), 'ia_base.csv', 'compras')} compras; "
     f"solução de IA respondeu por {n('1', 'participação de solução de IA', fmt_pct(100 * v_cls[SOL] / tec_v), 'ia_base_classes.csv', HC)}."),
    ("2", "Capacitação é o mercado mais frequente",
     f"Foram {n('2', 'compras de capacitação em IA', inteiro(n_cls[CAP]), 'ia_base.csv', 'compras')} compras de capacitação em IA, mais que as de tecnologia, "
     f"somando {n('2', 'valor da capacitação em IA', mi(v_cls[CAP]), 'ia_base_classes.csv', HC)}."),
    ("3", "Copilot domina o acréscimo à licença",
     f"Microsoft Copilot respondeu por {n('3', 'participação do Copilot no acréscimo', fmt_pct(100 * v_acr_tipo.get('Microsoft Copilot', 0) / v_cls[ACR]), 'ia_base_classes.csv', HC)} "
     f"do valor do acréscimo à licença ({n('3', 'valor do acréscimo à licença', mi(v_cls[ACR]), 'ia_base_classes.csv', HC)}, em "
     f"{n('3', 'compras com parte de acréscimo à licença', inteiro(len({r['id_compra'] for r in partes if r['classe'] == ACR})), 'ia_base_classes.csv', 'compras com parte de acréscimo')} compras); Google Gemini, por "
     f"{n('3', 'participação do Gemini no acréscimo', fmt_pct(100 * v_acr_tipo.get('Google Gemini', 0) / v_cls[ACR]), 'ia_base_classes.csv', HC)}."),
    ("4", "Venda concentrada em poucos fornecedores",
     f"Os 10 maiores fornecedores ficaram com {n('4', 'participação dos 10 maiores fornecedores', fmt_pct(100 * top10 / tot_res), 'ia_resultados.csv', RS)} "
     f"do valor dos resultados da tecnologia de IA, entre {n('4', 'fornecedores da tecnologia de IA', inteiro(len(vf)), 'ia_resultados.csv', RS)} fornecedores."),
]
assert all(len(t.split()) <= 30 for _, _, t in ACH), [len(t.split()) for _, _, t in ACH]


def grava(nome, cab, rows):
    with open(TP + nome, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)


grava("ia_achados.csv", ["achado", "titulo", "texto"], ACH)
grava("ia_achados_numeros.csv", ["achado", "indicador", "valor_exibido", "arquivo_de_origem", "base"], NUM)
# componentes da tecnologia de IA e da capacitacao, para o "i" da linha-resumo
comp = {}
for r in partes:
    k = (base[r["id_compra"]]["componente"], "capacitação" if r["classe"] == CAP else "tecnologia")
    x = comp.setdefault(k, [set(), 0.0, 0.0])
    x[0].add(r["id_compra"])
    x[1] += r2(r["valor_nominal"])
    x[2] += r2(r["valor_deflacionado"])
grava("ia_nota_resumo.csv", ["componente", "mercado", "compras", "valor_nominal", "valor_deflacionado"],
      [[k[0], k[1], len(v[0]), v[1], v[2]] for k, v in sorted(comp.items())])
for a in ACH:
    print(a[0], a[1], "|", a[2], f"({len(a[2].split())} palavras)")
print(sorted((k, len(v[0]), round(v[1] / 1e6, 1)) for k, v in comp.items()))
