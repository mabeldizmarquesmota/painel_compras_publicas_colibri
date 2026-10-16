"""Julgamentos da amostra de marca e tipo de vendedor (semente f2_marca_a1), feitos um a um.
Executar a partir de Processado/:  python fase2/validacao/julgamentos_marcas_f2_marca_a1.py
Entrada: fase2/validacao/fichas_marcas_f2_marca_a1.csv (grupo 'marca': 100 compras; grupo 'empresa publica de TI': 50).
Criterio: grupo 'marca' - a compra e pertinente quando cada marca detectada se refere a produto ou servico da marca que e
  objeto da compra (vendido, licenciado, suportado ou integrado) e o tipo de vendedor atribuido esta correto; mencao
  incidental (compatibilidade, link, comparacao, sistema alvo de outra solucao) nao e pertinente. Grupo 'empresa
  publica de TI' - pertinente quando o vencedor e empresa estatal cuja atividade e tecnologia da informacao.
Saida: fase2/validacao/julgamentos_marcas_f2_marca_a1.csv
"""
import csv

NAO_MARCA = {7: "link do Google Drive", 9: "compatibilidade com servidor IBM", 22: "mencao incidental ao Windows Server",
             24: "comparacao com Google Sheets", 27: "sistema SAP citado como local do cadastro", 28: "compatibilidade com Red Hat",
             29: "compatibilidade com navegador e Java", 30: "produtos Microsoft como alvo de outra solucao", 34: "compatibilidade com Windows",
             52: "software de terceiro com banco SQL Server", 55: "compatibilidade com G Suite", 65: "solucao de terceiro para Office 365 e Google Workspace",
             86: "compatibilidade com Red Hat"}
NAO_PUB = {}
f = list(csv.DictReader(open("fase2/validacao/fichas_marcas_f2_marca_a1.csv", encoding="utf-8"), delimiter=";"))
assert sum(r["grupo"] == "marca" for r in f) == 100 and sum(r["grupo"] != "marca" for r in f) == 50
with open("fase2/validacao/julgamentos_marcas_f2_marca_a1.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["grupo", "ficha", "id_compra", "pertinente", "motivo"])
    for r in f:
        k = int(r["ficha"])
        nao = NAO_MARCA if r["grupo"] == "marca" else NAO_PUB
        w.writerow([r["grupo"], k, r["id_compra"], "não" if k in nao else "sim", nao.get(k, "")])
print("marca:", 100 - len(NAO_MARCA), "de 100; empresa publica de TI:", 50 - len(NAO_PUB), "de 50")
