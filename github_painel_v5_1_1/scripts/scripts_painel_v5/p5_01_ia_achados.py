"""Painel v5, etapa 1: achados da aba de IA (texto do Ajuste 5), numeros de 'Nuvem com servicos de IA' e reconciliacao da Capacitacao.

Executar a partir de Processado/:  python scripts_painel_v5/p5_01_ia_achados.py
Entradas (somente leitura): tabelas_painel_v3/ia_base.csv, ia_base_classes.csv, ia_resultados.csv.
Regras: periodo completo (2021 a 2026), valores nominais arredondados a centavos como no painel. Nenhuma classificacao e refeita:
  'Nuvem com servicos de IA' e so o nome novo do tipo de objeto 'Nuvem/cloud broker'; no painel, o tipo 'Outros objetos', que so
  reune compras da classe Capacitacao, aparece com o nome 'Capacitacao'. Achado 4: fornecedor = CNPJ completo do vencedor (como na v4).
Saidas (tabelas_painel_v5/): ia_achados_v5.csv (achado; titulo; texto); ia_achados_numeros_v5.csv; ia_nuvem_servicos_ia.csv
  (base; compras; valor_nominal); ia_capacitacao_reconciliacao.csv (medida; compras; valor_nominal).
"""
import csv
import os
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, "scripts_painel_v5")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v5.formatacao import fmt_pct, inteiro, mi  # noqa: E402

TP, T5 = "tabelas_painel_v3/", "tabelas_painel_v5/"
os.makedirs(T5, exist_ok=True)
ler = lambda n: list(csv.DictReader(open(TP + n, encoding="utf-8"), delimiter=";"))
r2 = lambda x: round(float(x), 2)
CAP, NUV = "Capacitação", "Nuvem/cloud broker"
base = {r["id_compra"]: r for r in ler("ia_base.csv")}
partes = ler("ia_base_classes.csv")
res = ler("ia_resultados.csv")

# achados 2 e 4
cap_ids = [k for k, r in base.items() if r["classe"] == CAP]
cap_v = sum(r2(r["valor_nominal"]) for r in partes if r["classe"] == CAP)
vf = {}
for r in res:
    if r["classe"] != CAP:
        vf[r["cnpj_fornecedor"]] = vf.get(r["cnpj_fornecedor"], 0) + r2(r["valor_nominal"])
top10 = 100 * sum(sorted(vf.values(), reverse=True)[:10]) / sum(vf.values())
NUM = [["2", "compras de capacitação em IA", inteiro(len(cap_ids)), "ia_base.csv", "compras (classe Capacitação)"],
       ["2", "valor da capacitação em IA", mi(cap_v).replace(" mi", " milhões"), "ia_base_classes.csv", "valor homologado repartido pelas classes"],
       ["4", "participação dos 10 maiores fornecedores (CNPJ do vencedor)", fmt_pct(top10), "ia_resultados.csv", "valor dos resultados, sem Capacitação"],
       ["4", "fornecedores da tecnologia de IA (CNPJ do vencedor)", inteiro(len(vf)), "ia_resultados.csv", "valor dos resultados, sem Capacitação"]]
ACH = [
    ("1", "As compras de IA ainda apresentam opacidade sobre as soluções contratadas",
     "Os dados permitem identificar fornecedores e objetos contratados, mas não informam, em todos os casos, as infraestruturas, plataformas, serviços "
     "utilizados ou a localização do processamento e armazenamento de dados."),
    ("2", "Capacitação concentra o maior número de contratações",
     f"Foram identificadas {NUM[0][2]} compras de capacitação em IA, no valor de R$ {NUM[1][2][3:]}."),
    ("3", "Parte das aquisições ocorre por acréscimo de licenças",
     "Os registros indicam que parte das compras de IA ocorre por meio da ampliação de licenças de softwares e plataformas já utilizados pelos órgãos públicos."),
    ("4", "O valor homologado está concentrado em poucos fornecedores",
     f"Os dez maiores fornecedores responderam por {NUM[2][2]} do valor homologado, em um universo de {NUM[3][2]} fornecedores."),
]
# texto do Ajuste 5 (PROMPT_PAINEL_V5.md, item 4.4): o texto gerado tem de ser identico
ESPERADO = ["Foram identificadas 1.471 compras de capacitação em IA, no valor de R$ 34,9 milhões.",
            "Os dez maiores fornecedores responderam por 72% do valor homologado, em um universo de 541 fornecedores."]
assert [ACH[1][2], ACH[3][2]] == ESPERADO, [ACH[1][2], ACH[3][2]]

# Nuvem com servicos de IA (tipo 'Nuvem/cloud broker'): cada compra uma vez; valor homologado da compra na aba (todas as classes)
nuv = {k for k, r in base.items() if r["tipo_objeto"] == NUV}
nuv_v = sum(r2(r["valor_nominal"]) for r in partes if r["id_compra"] in nuv)
nuv_r = [r for r in res if r["tipo_objeto"] == NUV]
NUVEM = [["valor homologado da compra na aba de IA (ia_base_classes.csv, todas as classes)", len(nuv), round(nuv_v, 2)],
         ["valor dos resultados, compras com vencedor identificado (ia_resultados.csv, base do gráfico 9)", len({r["id_compra"] for r in nuv_r}),
          round(sum(r2(r["valor_nominal"]) for r in nuv_r), 2)]]

# Capacitacao: tabela de classes x base do grafico 9 (resultados)
cap_r = [r for r in res if r["classe"] == CAP]
com_res = {r["id_compra"] for r in cap_r}
sem_res = [k for k in cap_ids if k not in com_res]
REC = [["classe Capacitação, tabela de classes (ia_base.csv e ia_base_classes.csv)", len(cap_ids), round(cap_v, 2)],
       ["compras da classe com vencedor identificado (gráfico 9: valor dos resultados)", len(com_res), round(sum(r2(r["valor_nominal"]) for r in cap_r), 2)],
       ["compras da classe sem resultado com vencedor publicado (não entram no gráfico 9)", len(sem_res),
        round(sum(r2(r["valor_nominal"]) for r in partes if r["classe"] == CAP and r["id_compra"] in set(sem_res)), 2)]]
assert REC[1][1] + REC[2][1] == REC[0][1]
assert all(r["tipo_objeto"] == "Outros objetos" for r in base.values() if r["classe"] == CAP)
assert all(r["classe"] == CAP for r in base.values() if r["tipo_objeto"] == "Outros objetos")


def grava(nome, cab, rows):
    with open(T5 + nome, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)


grava("ia_achados_v5.csv", ["achado", "titulo", "texto"], ACH)
grava("ia_achados_numeros_v5.csv", ["achado", "indicador", "valor_exibido", "arquivo_de_origem", "base"], NUM)
grava("ia_nuvem_servicos_ia.csv", ["base", "compras", "valor_nominal"], NUVEM)
grava("ia_capacitacao_reconciliacao.csv", ["medida", "compras", "valor_nominal"], REC)
sys.stdout.reconfigure(encoding="utf-8")
for a in ACH:
    print(a[0], a[1], "|", a[2])
print("Nuvem com serviços de IA:", [(x[1], mi(x[2])) for x in NUVEM])
print("Capacitação:", [(x[1], mi(x[2])) for x in REC])
