"""Fase 2, etapa 3b: dicionario do modelo de aquisicao, versao 2 (primeiro ajuste, apos a amostra f2_modelo_a1).
Executar a partir de Processado/:  python fase2/scripts/f2_03b_dicionario_modelo_v2.py
Entrada: nenhuma (o dicionario e o proprio conteudo deste script; motivos do ajuste em fase2/METODOLOGIA_fase2.md).
Mudancas em relacao a versao 1 (classes reprovadas na amostra 1: 3 = 64%, 4 = 26%, 7 = 63%):
  - regras com subregras (coluna 'sub'): a classe se aplica se alguma subregra se aplicar;
  - novo tipo 'exclusao_objeto': expressao aplicada ao objeto da compra (normalizado da mesma forma);
  - exclusao comum (classes 2, 3 e 5): texto livre no formato de material do catalogo (', nome: '), incompativel com servico;
  - classe 2: so servicos (S); exclusoes de assinatura digital restritas ao sentido de assinar documentos; nuvem generica
    ('cloud', 'em nuvem') como subregra propria, sem servicos de instalacao, migracao, consultoria ou treinamento;
  - classe 3: licenciamento de direitos permanentes explicito (subregra a) ou codigo de catalogo 'direitos permanentes' (subregra b) sem
    indicio de prazo, subscricao, suporte, renovacao ou nuvem no item ou no objeto;
  - classe 4: expressoes especificas de suporte, atualizacao ou manutencao de licenca/software, sem equipamentos,
    locacao, rastreamento, instalacao, operacao ou monitoramento;
  - classe 5: inclui garantia, assistencia tecnica, manutencao e gerenciamento como servicos tecnicos; treinamento fora;
  - classe 6: 'computador' sem fronteira de palavra (microcomputador), fitas de backup, telefones, controle de acesso,
    mesa digitalizadora; exclui microfone, etiqueta, cartucho, toner, suporte metalico e assistente virtual domestico;
    ar condicionado so de precisao.
Saidas: fase2/dicionario_modelo_aquisicao_v2.csv e fase2/dicionario_modelo_aquisicao.csv (versao em uso)
"""
import csv

V = "2"
L = []


def add(ordem, classe, tipo, expr, obs="", sub="a"):
    L.append([V, ordem, sub, classe, tipo, expr, obs])


C1, C2, C3, C4, C5, C6 = ("Acréscimo a licença existente", "Subscrição ou serviço", "Licenciamento de direitos permanentes de uso",
                          "Suporte e manutenção de licença", "Desenvolvimento e serviços técnicos",
                          "Equipamentos e infraestrutura física")
NOME_MATERIAL = r", nome: "
# 1. acrescimo a licenca existente (sem mudanca)
for e in [r"\badd[- ]?ons?\b", r"\bcopilot\b", r"\bgemini\b", r"\bmodulos? adiciona", r"\blicen[cs]\w* adiciona",
          r"\bexpansao d[aeo]s? (quantitativo d[aeo]s? )?licen", r"\bampliacao d[aeo]s? (quantitativo d[aeo]s? )?licen",
          r"\bacrescimo d[aeo]s? (quantitativo d[aeo]s? )?licen", r"\bcomplemento d[aeo]s? licen", r"\blicen[cs]\w* complementar",
          r"\btrue[- ]?up\b"]:
    add(1, C1, "inclusao", e)
# 2. subscricao ou servico (servicos digitais por periodo)
for sub in ("a", "b"):
    add(2, C2, "material", "S", "servico", sub)
    add(2, C2, "exclusao", NOME_MATERIAL, "texto livre de material incompativel", sub)
for e in [r"\bsubscri", r"\bsubscription", r"\bassinatura", r"\bsaas\b", r"\biaas\b", r"\bpaas\b", r"\bcomo servico\b",
          r"\bcloud broker", r"\bbroker de nuvem", r"\bbrokerage", r"\bsob demanda\b", r"\bcreditos? (de )?(nuvem|cloud|consumo)",
          r"\bpor usuario", r"\busuarios?\s*/\s*mes", r"\busuarios? mes\b", r"\bmensalidade", r"\blocacao de (software|licen|sistema|programa)",
          r"\bcessao temporaria de direitos", r"\bcomputacao em nuvem", r"\bservicos? (de|em) nuvem", r"\bnuvem publica",
          r"\bhospedagem", r"\b(microsoft|office|windows|w) ?365\b", r"\bm365\b", r"\bgoogle workspace", r"\blicen[cs]\w* (de uso )?(anual|mensal)",
          r"\bemissao de (outros tipos de )?certificad", r"\bcertificados? digita", r"\bmensageria"]:
    add(2, C2, "inclusao", e)
for e in [r"\b(com|para|de) assinatura (digital|eletronica)", r"\bassinatura (digital|eletronica) de documentos", r"\bassinador",
          r"\bsob demanda\b.*\b(recarga|gas|extintor)", r"\brecarga\b"]:
    add(2, C2, "exclusao", e, "assinatura no sentido de assinar documentos; recarga de gas")
for e in [r"\bcloud\b", r"\bem nuvem\b", r"\bna nuvem\b"]:
    add(2, C2, "inclusao", e, "nuvem generica", "b")
for e in [r"\binstalacao", r"\bconfiguracao", r"\bmigracao", r"\bconsultoria", r"\btreinamento", r"\bimplantacao", r"\bbackup em fita"]:
    add(2, C2, "exclusao", e, "servicos tecnicos sobre nuvem (classe 5)", "b")
# 3. licenciamento de direitos permanentes
for e in [r"\bperpetu", r"\bvitalici", r"\bdefinitiv", r"\buso permanente", r"\blicen[cs]\w* permanente", r"\bprazo indeterminado",
          r"\btempo indeterminado"]:
    add(3, C3, "inclusao", e, "licenciamento de direitos permanentes explicito", "a")
for e in [r"\bsuporte", r"\batualizac", r"\bsoftware assurance", r"\brenovacao", r"\bmanutencao"]:
    add(3, C3, "exclusao", e, "suporte de licenciamento de direitos permanentes (classe 4)", "a")
add(3, C3, "inclusao", r"\bdireitos permanentes", "codigo do catalogo", "b")
for e in [r"\bsub\b", r"\bsubscri", r"\bper user\b", r"\bpor usuario", r"\banual", r"\bannual", r"\byears?\b", r"\b\d+ ?anos?\b", r"\bmeses\b",
          r"\bmensal", r"\brenovacao", r"\bsuporte", r"\bgarantia", r"\bsoftware assurance", r"\bnuvem", r"\bcloud", r"\bservico",
          r"\bimplementacao", r"\batualizac", r"\bexpansao", r"\badiciona", r"\bmonthly", r"\bmonth\b"]:
    add(3, C3, "exclusao", e, "indicio de prazo, subscricao, suporte, servico ou expansao", "b")
add(3, C3, "exclusao", NOME_MATERIAL, "texto livre de material incompativel", "b")
for e in [r"\bsubscri", r"\bassinatura", r"\b365\b", r"\bnuvem", r"\bcloud", r"\bcontinuad", r"\bsuporte", r"\brenovacao", r"\batualizac",
          r"\bprestacao de servic", r"\bcontratacao de servic", r"\bservico de licenc", r"\bservicos de licenc", r"\bexpansao"]:
    add(3, C3, "exclusao_objeto", e, "objeto da compra indica subscricao, servico, suporte ou expansao", "b")
# 4. suporte e manutencao de licenca (software ja licenciado)
add(4, C4, "material", "S", "servico")
for e in [r"\bsuporte (tecnico )?(e|,) ?(a |de )?atualizac", r"\batualizac\w* (e|de) (suporte|versao|versoes)", r"\bsuporte e manutencao d[aeo]s? (licen|software)",
          r"\bmanutencao d[aeo]s? licen", r"\bplanos? (anual |anuais )?de (suporte|manutencao)", r"\bsoftware assurance", r"\brenovacao d[aeo]s? (suporte|garantia)",
          r"\bextensao d[aeo]s? (suporte|garantia)", r"\bsuporte (tecnico )?(d[oa]|ao|para o) licenciamento", r"\bupgrade d[ae] versao", r"\bvalidade tecnica",
          r"\b(garantia|suporte) premium", r"\bsuporte (oficial )?do fabricante", r"\bupgrade support", r"\bsuporte (tecnico )?(e|,) ?(manutencao|garantia)",
          r"\bmanutencao (e|,) ?(suporte|atualizac)", r"\bsuporte tecnico especializado", r"\bum ano de suporte"]:
    add(4, C4, "inclusao", e)
for e in [r"\blicen[cs]", r"\bsoftware", r"\bprogramas? de computador", r"\bsubscri", r"\bversao", r"\bversoes", r"\bsistema operacional",
          r"\bbanco de dados", r"\bantivirus", r"\baplicativo", r"\bfirewall", r"\boracle", r"\bmicrosoft", r"\bfortigate", r"\bpalo alto",
          r"\bcheck point", r"\bvmware", r"\bred hat", r"\bsql", r"\bwindows"]:
    add(4, C4, "exige", e, "contexto de software licenciado")
for e in [r"\bcorretiva", r"\badaptativa", r"\bevolutiva", r"\bperfectiva", r"\bdesenvolvimento", r"\bfabrica de software", r"\brastreamento",
          r"\blocacao", r"\bcomodato", r"\bcftv", r"\bcircuito fechado", r"\bcamera", r"\bcatraca", r"\brelogio", r"\bponto eletronico", r"\bnobreak",
          r"\bimpressao", r"\boutsourcing", r"\binstalacao", r"\bimplantacao", r"\bimplementacao", r"\bmigracao", r"\boperacao", r"\bmonitoramento",
          r"\bhardware", r"\bequipamentos?\b", r"\bfornecimento de (solucao|equipamento)", r"\baquisicao de (solucao|equipamento)", r"\bgerenciad",
          r"\bespecificacoes minimas", r"\bstorage", r"\bservidor", r"\bswitch", r"\bhiperconverg", r"\bappliances?\b.*\bhardware", r"\bcertificad",
          r"\bnovas? licen", r"\bcom suporte\b.*\bmeses\b.*\blicen"]:
    add(4, C4, "exclusao", e, "equipamentos, servicos tecnicos e outros servicos")
# 5. desenvolvimento e servicos tecnicos
add(5, C5, "material", "S", "servico")
add(5, C5, "exclusao", NOME_MATERIAL, "texto livre de material incompativel")
for e in [r"\btreinamento", r"\bcapacitacao", r"\bcurso\b", r"\bvouchers?\b", r"\blocacao de equipamento", r"\barrendamento",
          r"\bassinatura", r"\bmensageria", r"\bbrokerage"]:
    add(5, C5, "exclusao", e, "treinamento, locacao de equipamento e servicos da classe 2")
for e in [r"\bdesenvolviment", r"\bfabrica de software", r"\bsustentacao", r"\bimplantacao", r"\bimplementacao", r"\bintegracao",
          r"\bconsultoria", r"\bassessoria", r"\boperacao\b", r"\boperacao (de|da|do|e)\b", r"\binstalacao", r"\bconfiguracao", r"\bparametrizacao",
          r"\bmigracao", r"\bcustomizacao", r"\bmanutencao", r"\bponto de funcao", r"\bunidade de servico tecnico", r"\bservico tecnico",
          r"\bservicos tecnicos", r"\bservice desk", r"\bcentral de servicos", r"\bsuporte", r"\bassistencia tecnica", r"\bmonitoramento",
          r"\bservicos auxiliares de tecnologia", r"\bservicos para a infraestrutura", r"\boutsourcing", r"\bgerenciamento",
          r"\bhoras? (de )?(servico|tecnic)", r"\bmao de obra", r"\bgarantia", r"\brecarga", r"\btestes? de (intrusao|invasao)", r"\bpentest",
          r"\bservicos? gerenciad", r"\bmontagem"]:
    add(5, C5, "inclusao", e)
# 6. equipamentos e infraestrutura fisica (material)
add(6, C6, "material", "M", "itens de material com funcao de hardware")
for e in [r"\bservidor", r"\bstorage", r"\brack\b", r"\bappliance", r"\bswitch", r"\broteador", r"\bfirewall", r"\bno-?break", r"\bnobreak",
          r"\bups\b", r"\baccess point", r"\bponto de acesso", r"\bequipamento (de rede|wireless|de seguranca)", r"\bdisco", r"\bssd\b", r"\bhd\b",
          r"\bmemoria", r"\bprocessador", r"computador", r"\bnotebook", r"\bdesktop", r"\bestacao de trabalho", r"\bmonitor\b",
          r"\btoken", r"\bleitor", r"\bcamera", r"\bunidade de fita", r"\bfita (de )?(gravacao|backup)", r"\blto\b", r"\btape", r"\bgpu\b", r"\bplaca",
          r"\btransceiver", r"\bgbic", r"\bsfp\b", r"\bpatch panel", r"\bcabo", r"\bgerador", r"\bar condicionado de precisao", r"\bprecisao\b.*\bclimatiza",
          r"\bbateria", r"\bfonte de alimentacao", r"\bfonte alimentacao", r"\bmodulo eletronico", r"\bchip", r"\bimpressora", r"\bscanner", r"\btablet",
          r"\bdispositivo", r"\bcontrolador", r"\bbiometric", r"\bcatraca", r"\bsensor", r"\bantena", r"\bhub\b", r"\bconector", r"\bpdu\b",
          r"\bsala cofre", r"\btelefon", r"\bmesa digitalizadora", r"\bcontrole (de )?acesso", r"\bfechadura", r"\bmouse", r"\bteclado",
          r"\bestabilizador", r"\bregua eletrica", r"\bextensao optica", r"\bfibra optica", r"\bcoletor"]:
    add(6, C6, "inclusao", e)
for e in [r"\bmicrofone", r"\betiqueta", r"\bcartucho", r"\btoner", r"\bsuporte\s*(,|/|de)\s*(nobreak|videocassete|televisao|tv|monitor|parede)",
          r"\bassistente virtual", r"\bsmart speaker", r"\bfita led"]:
    add(6, C6, "exclusao", e, "acessorios e consumiveis sem funcao de hardware")

for arq in ("fase2/dicionario_modelo_aquisicao_v2.csv", "fase2/dicionario_modelo_aquisicao.csv"):
    with open(arq, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["versao", "ordem", "sub", "classe", "tipo", "expressao", "observacao"])
        w.writerows(L)
print(len(L), "linhas")
