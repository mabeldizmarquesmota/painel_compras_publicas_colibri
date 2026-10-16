"""Julgamentos da amostra 2 (semente f2_modelo_a2, dicionario v2) do modelo de aquisicao, feitos um a um.
Executar a partir de Processado/:  python fase2/validacao/julgamentos_modelo_f2_modelo_a2.py
Entrada: fase2/validacao/fichas_modelo_f2_modelo_a2.csv (ordem das linhas = numero da ficha, a partir de 0).
Criterio: o mesmo da amostra 1 (ver julgamentos_modelo_f2_modelo_a1.py). Na classe 4, compra de licenca (direitos permanentes,
  com ou sem software assurance) e renovacao de licenca por prazo nao sao suporte de licenca existente. Na classe 7, item
  com texto livre incompativel com o codigo do catalogo, ou com informacao contraditoria entre item e objeto, e
  pertinente (nao identificavel).
Saida: fase2/validacao/julgamentos_modelo_f2_modelo_a2.csv
"""
import csv

NAO = {
    7: "objeto e digitalizacao de documentos", 12: "versao de uso permanente do produto", 41: "licenciamento de direitos permanentes", 56: "suporte e atualizacao (classe 4)",
    62: "servico de recuperacao de dados", 85: "objeto de material de expediente", 88: "aquisicao de licenca Windows Server",
    100: "suporte e atualizacao de licenciamento de direitos permanentes", 101: "produto por subscricao", 115: "certificacao tecnica (treinamento)",
    127: "objeto de certificados digitais", 134: "apenas software assurance", 141: "suporte de licenciamento de direitos permanentes", 145: "antivirus por prazo",
    146: "software via web", 152: "locacao de licenca", 153: "upgrade por 12 meses", 158: "produto vendido por subscricao",
    159: "treinamento", 168: "subscricao por usuario", 169: "renovacao de suporte", 171: "upgrade por 12 meses", 177: "renovacao de suporte",
    178: "servico", 193: "produto vendido por subscricao", 199: "produtos vendidos por subscricao",
    200: "compra de licenca com software assurance", 201: "compra de licenca", 202: "compra de licenciamento de direitos permanentes com suporte",
    203: "compra de licenciamento de direitos permanentes", 204: "compra de licenca", 209: "compra de licenca vitalicia", 212: "compra de licenca",
    213: "compra de licenciamento de direitos permanentes", 216: "compra de licenca", 217: "compra de licenca", 218: "renovacao de licenciamento e suporte (subscricao)",
    219: "compra de licenciamento de direitos permanentes", 220: "reativacao de licenca por 12 meses (subscricao)", 222: "compra de licenciamento de direitos permanentes",
    223: "compra de licenca", 225: "plataforma por 12 meses", 228: "renovacao de solucao por 36 meses (subscricao)", 229: "compra de licenciamento de direitos permanentes",
    230: "compra de licenca com software assurance", 232: "compra de licenca", 235: "compra de solucao de seguranca", 236: "compra de licenciamento de direitos permanentes",
    237: "compra de licenca", 238: "compra de licenca", 239: "renovacao de licenca por prazo", 242: "compra de licenca",
    244: "licenca por 36 meses", 248: "renovacao de solucao com licenciamento (subscricao)", 249: "compra de antivirus",
    251: "licenca por 36 meses", 252: "compra de licenca", 253: "renovacao de licenca por prazo", 254: "compra de licenca com software assurance",
    255: "compra de licenca", 258: "compra de licenca", 259: "compra de licenca", 260: "compra de licenca com software assurance",
    261: "compra de licenca", 263: "renovacao de solucao com licenciamento (subscricao)", 266: "licenca por 12 meses",
    268: "renovacao de licenca por prazo", 272: "appliance com suporte", 276: "compra de licenca vitalicia",
    279: "renovacao de antivirus por 36 meses (subscricao)", 282: "compra de licenca", 285: "compra de licencas com software assurance",
    286: "compra de licencas com software assurance", 288: "compra de licenciamento de direitos permanentes", 289: "compra de licenciamento de direitos permanentes",
    290: "servico de manutencao (classe 5)", 291: "compra de licencas",
    298: "locacao de equipamento", 301: "concessao de software", 308: "plataforma de e-mail marketing (classe 2)", 309: "suporte de licenca (classe 4)",
    313: "suporte premium de appliance de seguranca (classe 4)", 321: "locacao de painel", 328: "licenciamento e suporte (classe 4 ou 2)",
    337: "locacao de desktops", 338: "suporte de licenca (classe 4)", 350: "suporte de licenca (classe 4)", 366: "objeto de assinatura",
    367: "compra de solucao", 380: "licenca anual (classe 2)", 388: "suporte de software (classe 4)", 390: "compra de software",
    392: "suporte de licenca (classe 4)",
    411: "disco de corte (ferramenta)", 429: "equipamento nao identificado", 433: "fita de limpeza (consumivel)", 476: "equipamento medico",
    482: "cateter",
    496: "SMS por consumo (classe 2)", 498: "assinatura eletronica por transacao (classe 2)", 499: "chatbot como servico (classe 2)",
    508: "instalacao de cabeamento (classe 5)", 516: "implantacao (classe 5)", 517: "camera (classe 6)", 531: "projeto de engenharia (classe 5)",
    534: "impressora termica (classe 6)", 535: "instalacao (classe 5)", 541: "conversao de arquivos (classe 5)", 545: "automacao de controle de acesso (classe 5)",
    557: "subscricao (classe 2)", 559: "creditos de nuvem (classe 2)", 567: "fita de backup (classe 6)", 574: "servico de takedown (classe 5)",
    587: "geoprocessamento (classe 5)", 588: "licenca por 12 meses (classe 2)", 589: "licenciamento de direitos permanentes (classe 3)",
}
fichas = list(csv.DictReader(open("fase2/validacao/fichas_modelo_f2_modelo_a2.csv", encoding="utf-8"), delimiter=";"))
assert len(fichas) == 593 and max(NAO) < 593
with open("fase2/validacao/julgamentos_modelo_f2_modelo_a2.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ficha", "id_compra_item", "ordem", "classe", "pertinente", "motivo"])
    for k, r in enumerate(fichas):
        w.writerow([k, r["id_compra_item"], r["ordem"], r["classe"], "não" if k in NAO else "sim", NAO.get(k, "")])
print(len(fichas), "julgamentos;", len(NAO), "nao pertinentes")
