"""Julgamentos da amostra 3 (semente f2_modelo_a3, dicionario v3) do modelo de aquisicao, feitos um a um.
Executar a partir de Processado/:  python fase2/validacao/julgamentos_modelo_f2_modelo_a3.py
Entrada: fase2/validacao/fichas_modelo_f2_modelo_a3.csv (classes 3 e 7; a classe 4 da versao 3 nao teve itens fora das
  amostras anteriores, ver METODOLOGIA_fase2.md).
Criterio: o mesmo das amostras 1 e 2.
Saida: fase2/validacao/julgamentos_modelo_f2_modelo_a3.csv
"""
import csv

NAO = {
    3: "ponto de acesso (equipamento)", 8: "treinamento", 11: "licenciamento de uso (locacao)", 25: "treinamento",
    29: "manutencao mensal de licenca (suporte)", 47: "antivirus por prazo", 54: "Power BI (subscricao)", 60: "implantacao e treinamento",
    63: "creditos de nuvem", 66: "apenas software assurance", 68: "antivirus por 36 meses", 79: "licenca por prazo", 86: "Canva (subscricao)",
    93: "objeto incompativel (plataformas metalicas)",
    100: "licenca definitiva (classe 3)", 111: "equipamento de videoconferencia (classe 6)", 125: "gestao e operacao de servico (classe 5)",
    127: "impressora (classe 6)", 128: "licenca por periodo (classe 2)", 140: "lousa interativa (classe 6)", 144: "aquisicao de licenca (classe 3)",
    146: "atualizacao e suporte (classe 4)", 156: "impressora (classe 6)", 167: "plataforma como servico (classe 2)", 173: "impressora (classe 6)",
    176: "automacao de controle de acesso (classe 5)", 177: "ar condicionado de data center (classe 6)", 179: "appliance de backup (classe 6)",
    183: "garantia e suporte de storage (classe 5)", 187: "sistema como servico (classe 2)", 196: "auditoria (classe 5)", 198: "auditoria (classe 5)",
}
fichas = list(csv.DictReader(open("fase2/validacao/fichas_modelo_f2_modelo_a3.csv", encoding="utf-8"), delimiter=";"))
assert len(fichas) == 200 and max(NAO) < 200
with open("fase2/validacao/julgamentos_modelo_f2_modelo_a3.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ficha", "id_compra_item", "ordem", "classe", "pertinente", "motivo"])
    for k, r in enumerate(fichas):
        w.writerow([k, r["id_compra_item"], r["ordem"], r["classe"], "não" if k in NAO else "sim", NAO.get(k, "")])
print(len(fichas), "julgamentos;", len(NAO), "nao pertinentes")
