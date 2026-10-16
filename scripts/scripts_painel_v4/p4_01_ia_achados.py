"""Painel v4, etapa 1: principais achados da aba Inteligencia artificial (texto do Ajuste 4) e a conta nova do achado 4.

Executar a partir de Processado/:  python scripts_painel_v4/p4_01_ia_achados.py
Entradas (somente leitura, tabelas da v3): tabelas_painel_v3/ia_base.csv, ia_base_classes.csv, ia_resultados.csv,
  ia_fornecedores_cnpj.csv.
Regras: periodo completo (2021 a 2026), valores nominais, valores arredondados a centavos como no painel. Os achados 1 a 3
  usam os mesmos numeros da v3 (p1_08), so com o texto novo. Achado 4 (unica conta nova): resultados da tecnologia de IA
  (classes Acrescimo a licenca, Solucao de IA e Outros, sem Capacitacao), fornecedor = CNPJ completo do vencedor, a mesma
  definicao da linha-resumo do grafico 9 (Sankey da IA) e dos KPIs de fornecedores da aba de tecnologias criticas.
  A versao anterior contava a raiz do CNPJ (8 digitos); a diferenca entre as duas contagens fica registrada.
Saidas: tabelas_painel_v4/ia_achados_v4.csv (achado; titulo; texto); tabelas_painel_v4/ia_achados_numeros_v4.csv
  (achado; indicador; valor_exibido; arquivo_de_origem; base); tabelas_painel_v4/ia_achado4_fornecedores.csv
  (definicao; fornecedores; valor_10_maiores; valor_total; pct_10_maiores) e ia_achado4_raizes_com_mais_de_um_cnpj.csv.
"""
import csv
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "scripts_painel_v4")
from painel_compras_publicas_colibri.scripts.scripts_painel_v4.formatacao import fmt_num, fmt_pct, inteiro, mi  # noqa: E402

TP, T4 = "tabelas_painel_v3/", "tabelas_painel_v4/"
os.makedirs(T4, exist_ok=True)
ler = lambda n: list(csv.DictReader(open(TP + n, encoding="utf-8"), delimiter=";"))
r2 = lambda x: round(float(x), 2)
CAP, ACR, SOL = "Capacitação", "Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)"
base = {r["id_compra"]: r for r in ler("ia_base.csv")}
partes = ler("ia_base_classes.csv")
res = [r for r in ler("ia_resultados.csv") if r["classe"] != CAP]
nome = {r["cnpj_fornecedor"]: r["nome"] for r in ler("ia_fornecedores_cnpj.csv")}

v_cls, n_cls, v_acr_tipo = {}, {}, {}
for r in partes:
    v_cls[r["classe"]] = v_cls.get(r["classe"], 0) + r2(r["valor_nominal"])
    if r["classe"] == ACR:
        t = base[r["id_compra"]]["tipo_objeto"]
        v_acr_tipo[t] = v_acr_tipo.get(t, 0) + r2(r["valor_nominal"])
for r in base.values():
    n_cls[r["classe"]] = n_cls.get(r["classe"], 0) + 1
tec_v = sum(v for k, v in v_cls.items() if k != CAP)
tec_n = sum(n for k, n in n_cls.items() if k != CAP)
n_acr = len({r["id_compra"] for r in partes if r["classe"] == ACR})


def concentracao(chave):
    vf = {}
    for r in res:
        vf[r[chave]] = vf.get(r[chave], 0) + r2(r["valor_nominal"])
    tot = sum(vf.values())
    top = sum(sorted(vf.values(), reverse=True)[:10])
    return len(vf), top, tot


n_cnpj, top_cnpj, tot_cnpj = concentracao("cnpj_fornecedor")
n_raiz, top_raiz, tot_raiz = concentracao("raiz_cnpj")
NUM = []


def n(a, ind, val, arq, base_v):
    NUM.append([a, ind, val, arq, base_v])
    return val


milhoes = lambda x: mi(x).replace(" mi", " milhões")
bilhao = lambda x: "R$ " + fmt_num(x / 1e9, 2) + (" bilhão" if x < 2e9 else " bilhões")
HC, RS = "valor homologado repartido pelas classes", "valor dos resultados"
ACH = [
    ("1", "Soluções de IA concentram o maior valor",
     f"Entre 2021 e 2026, as compras de IA somaram {n('1', 'valor da tecnologia de IA', bilhao(tec_v), 'ia_base_classes.csv', HC)} "
     f"em {n('1', 'compras de tecnologia de IA', inteiro(tec_n), 'ia_base.csv', 'compras')} compras. As soluções de IA responderam por "
     f"{n('1', 'participação de solução de IA', fmt_pct(100 * v_cls[SOL] / tec_v), 'ia_base_classes.csv', HC)} do valor total."),
    ("2", "Capacitação tem maior número de compras",
     f"Foram {n('2', 'compras de capacitação em IA', inteiro(n_cls[CAP]), 'ia_base.csv', 'compras')} compras de capacitação em IA, superando as compras "
     f"de tecnologia em quantidade. O segmento movimentou {n('2', 'valor da capacitação em IA', milhoes(v_cls[CAP]), 'ia_base_classes.csv', HC)}."),
    ("3", "Microsoft Copilot lidera o acréscimo de licenças",
     f"O Microsoft Copilot concentrou {n('3', 'participação do Copilot no acréscimo', fmt_pct(100 * v_acr_tipo.get('Microsoft Copilot', 0) / v_cls[ACR]), 'ia_base_classes.csv', HC)} "
     f"do valor das compras de acréscimo de licença, equivalentes a {n('3', 'valor do acréscimo à licença', milhoes(v_cls[ACR]), 'ia_base_classes.csv', HC)} "
     f"em {n('3', 'compras com parte de acréscimo à licença', inteiro(n_acr), 'ia_base_classes.csv', 'compras com parte de acréscimo')} compras. "
     f"O Google Gemini respondeu pelos {n('3', 'participação do Gemini no acréscimo', fmt_pct(100 * v_acr_tipo.get('Google Gemini', 0) / v_cls[ACR]), 'ia_base_classes.csv', HC)} restantes."),
    ("4", "Valor das compras está concentrado em poucos fornecedores",
     f"Os 10 maiores fornecedores concentraram {n('4', 'participação dos 10 maiores fornecedores (CNPJ do vencedor)', fmt_pct(100 * top_cnpj / tot_cnpj), 'ia_resultados.csv', RS)} "
     f"do valor homologado nos resultados, em um universo de {n('4', 'fornecedores da tecnologia de IA (CNPJ do vencedor)', inteiro(n_cnpj), 'ia_resultados.csv', RS)} fornecedores."),
]
# texto do Ajuste 4 (PROMPT_PAINEL_V4.md, item 4.2), com N calculado aqui: o texto gerado tem de ser identico
ESPERADO = [
    "Entre 2021 e 2026, as compras de IA somaram R$ 1,28 bilhão em 983 compras. As soluções de IA responderam por 45% do valor total.",
    "Foram 1.471 compras de capacitação em IA, superando as compras de tecnologia em quantidade. O segmento movimentou R$ 34,9 milhões.",
    "O Microsoft Copilot concentrou 75% do valor das compras de acréscimo de licença, equivalentes a R$ 147 milhões em 56 compras. O Google Gemini respondeu pelos 25% restantes.",
    f"Os 10 maiores fornecedores concentraram 72% do valor homologado nos resultados, em um universo de {inteiro(n_cnpj)} fornecedores.",
]
for (a, _, t), e in zip(ACH, ESPERADO):
    assert t == e, (a, t, e)


def grava(nome_arq, cab, rows):
    with open(T4 + nome_arq, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)


grava("ia_achados_v4.csv", ["achado", "titulo", "texto"], ACH)
grava("ia_achados_numeros_v4.csv", ["achado", "indicador", "valor_exibido", "arquivo_de_origem", "base"], NUM)
grava("ia_achado4_fornecedores.csv", ["definicao", "fornecedores", "valor_10_maiores", "valor_total", "pct_10_maiores"],
      [["CNPJ completo do vencedor (painel v4: achado 4 e linha-resumo do gráfico 9)", n_cnpj, round(top_cnpj, 2), round(tot_cnpj, 2), round(100 * top_cnpj / tot_cnpj, 4)],
       ["raiz do CNPJ, 8 dígitos (achado 4 da v3)", n_raiz, round(top_raiz, 2), round(tot_raiz, 2), round(100 * top_raiz / tot_raiz, 4)]])
raizes = {}
for r in res:
    raizes.setdefault(r["raiz_cnpj"], set()).add(r["cnpj_fornecedor"])
grava("ia_achado4_raizes_com_mais_de_um_cnpj.csv", ["raiz_cnpj", "cnpj_fornecedor", "nome"],
      [[z, c, nome.get(c, "")] for z, cs in sorted(raizes.items()) if len(cs) > 1 for c in sorted(cs)])
sys.stdout.reconfigure(encoding="utf-8")
for a in ACH:
    print(a[0], a[1], "|", a[2])
print(f"achado 4: {n_cnpj} CNPJs ({fmt_pct(100 * top_cnpj / tot_cnpj)}); {n_raiz} raízes ({fmt_pct(100 * top_raiz / tot_raiz)}); "
      f"{sum(1 for cs in raizes.values() if len(cs) > 1)} raízes com mais de um CNPJ")
