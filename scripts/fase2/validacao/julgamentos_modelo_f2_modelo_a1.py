"""Julgamentos da amostra 1 (semente f2_modelo_a1) do modelo de aquisicao, feitos um a um.
Executar a partir de Processado/:  python fase2/validacao/julgamentos_modelo_f2_modelo_a1.py
Entrada: fase2/validacao/fichas_modelo_f2_modelo_a1.csv (ordem das linhas = numero da ficha, a partir de 0).
Criterio: a ficha e pertinente quando o texto do item (e, como contexto, o objeto da compra) sustenta a classe
  atribuida e nenhuma classe de precedencia mais alta se aplica. Classe 2 inclui servicos digitais por periodo
  (assinaturas, licencas temporarias, nuvem, certificados digitais). Classe 5 inclui servicos tecnicos de instalacao,
  manutencao e assistencia tecnica de equipamentos; treinamento nao e servico tecnico. Classe 6: material com funcao de
  hardware ou de infraestrutura fisica de TI e seguranca. Classe 7 e pertinente quando nenhuma classe de 1 a 6 se aplica.
  Texto livre incompativel com o codigo do catalogo (ex.: 'herbicida' em item de software) = nao pertinente.
Saida: fase2/validacao/julgamentos_modelo_f2_modelo_a1.csv (ficha; id_compra_item; ordem; pertinente; motivo)
"""
import csv

NAO = {  # ficha: motivo (demais fichas: pertinente)
    19: "licenca base com add-on (compra da licenca, nao acrescimo)", 26: "licenca base com recurso incluido", 31: "treinamento",
    42: "licenca base com add-ons", 45: "pacote de licencas base", 58: "licenca base com add-on", 61: "servicos tecnicos",
    63: "pacote de licencas base", 71: "renovacao de licencas com suporte", 75: "licenca base por subscricao", 86: "licenca base com add-on",
    88: "licenca base", 89: "licenca base", 92: "licenca base com licencas adicionais", 94: "suporte tecnico", 98: "servico de instalacao",
    105: "texto livre incompativel (herbicida)", 108: "inscricao em congresso", 119: "texto livre incompativel (herbicida)",
    128: "servico de migracao de dados", 132: "texto livre incompativel (toalha)", 137: "texto livre incompativel (regua)",
    147: "recarga de gas de combate a incendio", 160: "texto livre incompativel (livro ata)", 161: "texto livre incompativel (regua)",
    169: "servico de manutencao e operacao", 175: "texto livre incompativel (herbicida)", 176: "aquisicao de solucao de firewall",
    181: "equipamento (captura de assinatura)", 182: "texto livre incompativel (toalha)", 186: "texto livre incompativel (pilhas)",
    193: "software assurance (suporte de licenca)",
    201: "servico de licenciamento ja contratado (renovacao)", 203: "suporte de licenciamento de direitos permanentes", 204: "licenca por 12 meses",
    205: "garantia e suporte de storage", 207: "texto livre incompativel (desodorante)", 208: "suporte e atualizacao", 210: "licenca em nuvem",
    212: "material pedagogico", 214: "subscricao de 5 anos", 216: "renovacao de software assurance", 218: "servico continuo",
    219: "expansao de solucao existente", 220: "fornecimento continuado (subscricao)", 221: "licenca na modalidade cloud",
    223: "licenca de expansao (acrescimo)", 226: "licencas Microsoft 365 (subscricao)", 231: "servico de suporte por 60 meses",
    232: "subscricao por usuario", 233: "texto livre incompativel (desodorante)", 234: "licenca de antivirus por prazo",
    237: "renovacao de software assurance", 247: "suporte", 248: "subscricao de 2 anos", 251: "texto livre incompativel (desodorante)",
    256: "servico de uso de solucao", 257: "subscricao", 260: "licenca anual", 267: "servico de licenciamento e suporte",
    268: "servico de implementacao", 271: "renovacao de appliance com suporte", 281: "renovacao por 36 meses", 288: "renovacao de suporte",
    290: "texto livre incompativel (cortina)", 293: "renovacao de licenciamento", 294: "contratacao de servico", 296: "servico de atualizacao",
    303: "servico de instalacao de servidores", 304: "suporte de hardware de appliance", 305: "locacao de equipamentos de ponto",
    306: "monitoramento e operacao", 307: "fornecimento de solucao de firewall", 311: "rastreamento veicular", 312: "rastreamento veicular",
    313: "outsourcing de impressao", 314: "solucao de conectividade", 315: "catraca", 316: "locacao de relogio de ponto",
    318: "instalacao de CFTV", 319: "rastreamento veicular", 320: "renovacao de licenca de protecao (subscricao)", 321: "certificado digital",
    322: "apoio a gestao de servicos", 324: "atendimento a usuarios", 325: "suporte de hardware de appliance", 326: "equipamento (access point)",
    327: "equipamento (placa de rede)", 329: "CFTV", 330: "equipamento (gravador)", 331: "rastreamento veicular", 332: "rastreamento veicular",
    333: "manutencao de sala cofre", 334: "instalacao e operacao assistida", 335: "renovacao de licenca de protecao (subscricao)",
    338: "licenca por 2 anos", 339: "suporte de hardware de storage", 340: "CFTV", 341: "equipamento de video", 342: "solucao de controle de acesso",
    343: "locacao de relogio de ponto", 344: "certificado digital", 347: "sistema online com suporte (servico)", 349: "CFTV",
    350: "instalacao e migracao", 351: "rastreamento veicular", 353: "rastreamento veicular", 355: "licenca de uso mensal com suporte",
    356: "rastreamento veicular", 357: "locacao de ponto de TV", 358: "aquisicao de software", 362: "implementacao e migracao",
    365: "equipamento (gravador)", 366: "locacao de relogio de ponto", 367: "implantacao de software", 368: "servico de seguranca gerenciado",
    369: "servicos de instalacao e operacao", 370: "licenca com suporte", 371: "locacao de catracas", 372: "manutencao de nobreak",
    374: "solucao de hiperconvergencia", 375: "locacao de controle de acesso", 376: "rastreamento veicular", 378: "suporte de hardware",
    379: "CFTV", 380: "servicos de gestao de TI", 381: "locacao de tablet", 382: "licenca mensal com manutencao", 384: "rastreamento veicular",
    385: "CFTV", 386: "rastreamento veicular", 388: "locacao de relogio de ponto", 390: "produtos e servicos de SAN", 391: "rastreamento veicular",
    392: "equipamento (access point)", 393: "manutencao de nobreak", 394: "rastreamento veicular", 395: "licencas de ramal",
    396: "garantia de hardware", 397: "rastreamento veicular", 398: "servico gerenciado", 399: "aquisicao de solucao de firewall",
    404: "texto livre incompativel (filme)", 409: "corretagem de nuvem (classe 2)", 418: "locacao de equipamento", 425: "texto livre incompativel (negativo)",
    427: "assinatura de televisao", 430: "treinamento", 434: "servico de mensageria (classe 2)", 435: "treinamento", 439: "equipamento",
    441: "equipamento", 445: "texto livre incompativel (composto quimico)", 454: "suporte do fabricante a licenca (classe 4)", 456: "equipamento",
    467: "equipamento", 469: "texto livre incompativel (adrica)", 471: "solucao de software", 474: "texto livre incompativel (lencol)",
    480: "texto livre incompativel (filme)", 486: "servico de protecao por 36 meses (classe 2)", 495: "suporte premium do fabricante (classe 4)",
    503: "microfone", 509: "ar condicionado de escritorio", 520: "etiqueta adesiva", 523: "assistente virtual domestico", 531: "suporte metalico",
    557: "microfone", 572: "cartucho de tinta",
    600: "garantia de equipamento (classe 5)", 601: "manutencao de data center (classe 5)", 602: "licenca em nuvem (classe 2)",
    607: "microcomputador (classe 6)", 608: "recarga de gas (manutencao, classe 5)", 611: "gerenciamento de infraestrutura (classe 5)",
    617: "fita de backup (classe 6)", 618: "controle de acesso (classe 6)", 619: "gerenciamento de infraestrutura (classe 5)",
    622: "assessoria (classe 5)", 623: "certificado digital (classe 2)", 629: "certificado digital (classe 2)", 631: "controle de acesso (classe 6)",
    632: "certificado digital (classe 2)", 635: "certificado digital (classe 2)", 636: "servicos gerenciados (classe 5)",
    641: "assinatura de plataforma (classe 2)", 642: "aparelho telefonico (classe 6)", 648: "certificado digital (classe 2)",
    649: "suporte e garantia (classe 5)", 651: "certificado digital (classe 2)", 652: "suporte de servidor (classe 5)",
    653: "mesa digitalizadora (classe 6)", 654: "manutencao (classe 5)", 656: "fita de backup (classe 6)",
    657: "gerenciamento de infraestrutura (classe 5)", 669: "fita de backup (classe 6)", 670: "manutencao (classe 5)",
    673: "fita de backup (classe 6)", 676: "aparelho telefonico (classe 6)", 681: "gerenciamento de infraestrutura (classe 5)",
    682: "manutencao (classe 5)", 685: "manutencao (classe 5)", 690: "certificado digital (classe 2)", 691: "certificado digital (classe 2)",
    698: "suporte e garantia de switch (classe 5)", 699: "assinatura de jornal (classe 2)",
}
fichas = list(csv.DictReader(open("fase2/validacao/fichas_modelo_f2_modelo_a1.csv", encoding="utf-8"), delimiter=";"))
assert len(fichas) == 700 and max(NAO) < 700
with open("fase2/validacao/julgamentos_modelo_f2_modelo_a1.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ficha", "id_compra_item", "ordem", "classe", "pertinente", "motivo"])
    for k, r in enumerate(fichas):
        w.writerow([k, r["id_compra_item"], r["ordem"], r["classe"], "não" if k in NAO else "sim", NAO.get(k, "")])
print(len(fichas), "julgamentos;", len(NAO), "nao pertinentes")
