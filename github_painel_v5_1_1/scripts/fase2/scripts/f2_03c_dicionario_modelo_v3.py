"""Fase 2, etapa 3c: dicionario do modelo de aquisicao, versao 3 (segundo e ultimo ajuste, apos a amostra f2_modelo_a2).
Executar a partir de Processado/:  python fase2/scripts/f2_03c_dicionario_modelo_v3.py
Entrada: fase2/dicionario_modelo_aquisicao_v2.csv.
Motivo: na amostra 2 a classe 4 ficou em 45%, porque a versao 2 retirou da classe 3 as compras de licenciamento de direitos permanentes com
  suporte ou software assurance (que passaram para a classe 4) e porque renovacoes de licenca por prazo eram tratadas
  como suporte. Mudancas (classes 1, 2, 6 e 7 sem mudanca de regra):
  - classe 3, subregra a: exclui so suporte DE licenciamento de direitos permanentes (update & support, renewal, reativacao, CSI, servico de
    suporte/atualizacao, renovacao) e nao mais a compra de licenciamento de direitos permanentes que inclui suporte;
  - classe 3, nova subregra c: compra de licenca com software assurance (licenca + SA, 'sem software assurance', LSA);
  - classe 4: exclui compra de licenca (aquisicao/fornecimento de licenca, uso permanente, vitalicia, licenca + SA, sem SA, LSA),
    renovacao ou reativacao de licenca/solucao por prazo e vigencia;
  - classe 5: exclui licenciamento e renovacao de licenca/solucao (nao sao servicos tecnicos).
Saidas: fase2/dicionario_modelo_aquisicao_v3.csv e fase2/dicionario_modelo_aquisicao.csv (versao em uso)
"""
import csv

v2 = list(csv.reader(open("fase2/dicionario_modelo_aquisicao_v2.csv", encoding="utf-8"), delimiter=";"))
cab, linhas = v2[0], v2[1:]
C3, C4, C5 = "Licenciamento de direitos permanentes de uso", "Suporte e manutenção de licença", "Desenvolvimento e serviços técnicos"
SAI_3A = {r"\bsuporte", r"\batualizac", r"\bsoftware assurance", r"\brenovacao", r"\bmanutencao"}
L = [["3"] + l[1:] for l in linhas if not (l[1] == "3" and l[2] == "a" and l[4] == "exclusao" and l[5] in SAI_3A)]


def add(ordem, sub, classe, tipo, expr, obs=""):
    L.append(["3", str(ordem), sub, classe, tipo, expr, obs])


for e in [r"\bupdate (&|and) support", r"\brenewal", r"\breativacao", r"\brenovacao", r"\bcsi\b", r"^\W*(suporte|atualizac|servico)",
          r"\bservicos? de (suporte|atualizac)", r"\b(suporte|atualizac\w*)( tecnico)? (e|,) ?(suporte|atualizac\w*)? ?(para|d[aeo]s?) (as )?licen\w* (perpetu|existente)",
          r"\b(suporte|atualizac\w*|manutencao)\b[^|]{0,60}\bprocessor perpetual"]:
    add(3, "a", C3, "exclusao", e, "suporte de licenciamento de direitos permanentes ja existente (classe 4)")
for e in [r"\blicen\w*[^|]{0,40}\+ ?software assurance", r"\bsem (o )?software assurance", r"\b(alng|slng) lsa\b", r"\blsa (2l|ucal|dcal)\b",
          r"\blicen\w* e software assurance"]:
    add(3, "c", C3, "inclusao", e, "compra de licenca com software assurance")
add(3, "c", C3, "material", "S", "servico")
for e in [r"\brenovacao d[aeo]s? software assurance", r"\b^\W*renovacao", r"\bsomente software assurance"]:
    add(3, "c", C3, "exclusao", e, "renovacao de software assurance (classe 4)")
for e in [r"\b(aquisicao|fornecimento|compra) d[ae]s? (\d+ )?licen", r"\bperpetu", r"\bvitalici", r"\blicen\w*[^|]{0,40}\+ ?software assurance",
          r"\bsem (o )?software assurance", r"\b(alng|slng) lsa\b", r"\blsa (2l|ucal|dcal)\b", r"\brenovacao d[aeo]s? (licen\w*|solucao|software|subscri)",
          r"\breativacao", r"\bvigencia", r"\bincluindo licenciamento", r"\blicenciamento e suporte"]:
    add(4, "a", C4, "exclusao", e, "compra de licenca ou renovacao de licenca por prazo")
for e in [r"\blicenciamento", r"\brenovacao d[aeo]s? (licen\w*|solucao|software|subscri)"]:
    add(5, "a", C5, "exclusao", e, "licenciamento nao e servico tecnico")

with open("fase2/dicionario_modelo_aquisicao_v3.csv", "w", encoding="utf-8", newline="") as fo, \
        open("fase2/dicionario_modelo_aquisicao.csv", "w", encoding="utf-8", newline="") as fo2:
    for f in (fo, fo2):
        w = csv.writer(f, delimiter=";")
        w.writerow(cab)
        w.writerows(L)
print(len(L), "linhas")
