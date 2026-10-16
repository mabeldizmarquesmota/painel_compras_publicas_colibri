"""Fase 2, etapa 3: dicionario do modelo de aquisicao, versao 1 (regras escritas pela equipe de pesquisa).
Executar a partir de Processado/:  python fase2/scripts/f2_03_dicionario_modelo_v1.py
Entrada: nenhuma (o dicionario e o proprio conteudo deste script).
Regra de aplicacao (f2_04): texto do item = descricao + descricao resumida + descricao detalhada + unidade de medida,
  em minusculas, sem acentos e com espacos colapsados. Classes em ordem de precedencia (1 a 6; 7 = nao identificado).
  O item recebe a primeira classe em que (a) alguma expressao de 'inclusao' ocorre, (b) nenhuma de 'exclusao' ocorre,
  (c) se houver linhas 'exige', ao menos uma ocorre, e (d) se houver linha 'material', o tipo do item coincide (M ou S).
  Expressoes regulares (sintaxe Python).
Saidas: fase2/dicionario_modelo_aquisicao_v1.csv (registro da versao 1) e fase2/dicionario_modelo_aquisicao.csv
  (versao em uso; substituida pelas versoes seguintes, se houver ajuste)
"""
import csv

V = "1"
L = []


def add(ordem, classe, tipo, expr, obs=""):
    L.append([V, ordem, classe, tipo, expr, obs])


C1, C2, C3, C4, C5, C6 = ("Acréscimo a licença existente", "Subscrição ou serviço", "Licenciamento de direitos permanentes de uso",
                          "Suporte e manutenção de licença", "Desenvolvimento e serviços técnicos",
                          "Equipamentos e infraestrutura física")
# 1. acrescimo a licenca existente
for e in [r"\badd[- ]?ons?\b", r"\bcopilot\b", r"\bgemini\b", r"\bmodulos? adiciona", r"\blicen[cs]\w* adiciona",
          r"\bexpansao d[aeo]s? (quantitativo d[aeo]s? )?licen", r"\bampliacao d[aeo]s? (quantitativo d[aeo]s? )?licen",
          r"\bacrescimo d[aeo]s? (quantitativo d[aeo]s? )?licen", r"\bcomplemento d[aeo]s? licen", r"\blicen[cs]\w* complementar",
          r"\btrue[- ]?up\b"]:
    add(1, C1, "inclusao", e)
# 2. subscricao ou servico
for e in [r"\bsubscri", r"\bsubscription", r"\bassinatura", r"\bsaas\b", r"\biaas\b", r"\bpaas\b", r"\bcomo servico\b",
          r"\bcloud broker", r"\bbroker de nuvem", r"\bsob demanda\b", r"\bcreditos? (de )?(nuvem|cloud|consumo)",
          r"\bpor usuario", r"\busuarios?\s*/\s*mes", r"\busuarios? mes\b", r"\bmensalidade", r"\blocacao de (software|licen|sistema|programa)",
          r"\bcessao temporaria de direitos", r"\bcomputacao em nuvem", r"\bservicos? (de|em) nuvem", r"\bnuvem publica",
          r"\bhospedagem", r"\b(microsoft|office|windows|w) ?365\b", r"\bm365\b", r"\bgoogle workspace", r"\blicen[cs]\w* (de uso )?(anual|mensal)",
          r"\bemissao de (outros tipos de )?certificad", r"\bcertificados? digita"]:
    add(2, C2, "inclusao", e)
for e in [r"\bassinatura (digital|eletronica|qualificada|avancada|de documentos)", r"\bassinaturas (digitais|eletronicas)", r"\bassinador",
          r"\btoken\b.*\b(usb|criptografic)", r"\bleitor(a)? de (cartao|certificado)"]:
    add(2, C2, "exclusao", e, "assinatura no sentido de assinatura digital; token e leitora sao equipamentos")
# 3. licenciamento de direitos permanentes
for e in [r"\bperpetu", r"\bdefinitiv", r"\buso permanente", r"\bdireitos permanentes", r"\blicen[cs]\w* permanente",
          r"\bprazo indeterminado", r"\btempo indeterminado"]:
    add(3, C3, "inclusao", e)
# 4. suporte e manutencao de licenca (software ja licenciado)
for e in [r"\bsuporte", r"\bmanutencao", r"\bgarantia", r"\batualizac\w* de versao", r"\batualizac\w* de versoes", r"\bupgrade",
          r"\bsoftware assurance", r"\brenovacao d[aeo]s? (suporte|garantia|licen)"]:
    add(4, C4, "inclusao", e)
for e in [r"\blicen[cs]", r"\bsoftware", r"\bprogramas? de computador", r"\bsubscri", r"\bversao", r"\bversoes",
          r"\bsistema operacional", r"\bbanco de dados", r"\bantivirus", r"\baplicativo"]:
    add(4, C4, "exige", e, "contexto de software licenciado")
for e in [r"\bcorretiva", r"\badaptativa", r"\bevolutiva", r"\bperfectiva", r"\bdesenvolvimento", r"\bfabrica de software"]:
    add(4, C4, "exclusao", e, "manutencao de sistemas sob medida e desenvolvimento (classe 5)")
add(4, C4, "material", "S", "suporte de licenca e servico")
# 5. desenvolvimento e servicos tecnicos
for e in [r"\bdesenvolviment", r"\bfabrica de software", r"\bsustentacao", r"\bimplantacao", r"\bimplementacao", r"\bintegracao",
          r"\bconsultoria", r"\boperacao\b", r"\boperacao (de|da|do|e)\b", r"\binstalacao", r"\bconfiguracao", r"\bparametrizacao",
          r"\bmigracao", r"\bcustomizacao", r"\bmanutencao de (software|sistema)", r"\bmanutencao (preventiva|corretiva|evolutiva|adaptativa)",
          r"\bponto de funcao", r"\bunidade de servico tecnico", r"\bservico tecnico", r"\bservicos tecnicos", r"\bservice desk",
          r"\bcentral de servicos", r"\bsuporte (tecnico )?(ao|aos) usuarios?", r"\bassistencia tecnica", r"\bmonitoramento",
          r"\bservicos auxiliares de tecnologia", r"\bservicos para a infraestrutura", r"\boutsourcing", r"\bgestao de (infraestrutura|ambiente|rede)",
          r"\bhoras? (de )?(servico|tecnic)", r"\bmao de obra"]:
    add(5, C5, "inclusao", e)
# 6. equipamentos e infraestrutura fisica (material)
for e in [r"\bservidor", r"\bstorage", r"\brack\b", r"\bappliance", r"\bswitch", r"\broteador", r"\bfirewall", r"\bno-?break", r"\bnobreak",
          r"\bups\b", r"\baccess point", r"\bponto de acesso", r"\bequipamento (de rede|wireless|de seguranca)", r"\bdisco", r"\bssd\b", r"\bhd\b",
          r"\bmemoria", r"\bprocessador", r"\bcomputador", r"\bnotebook", r"\bdesktop", r"\bestacao de trabalho", r"\bmonitor\b",
          r"\btoken", r"\bleitor", r"\bcamera", r"\bunidade de fita", r"\btape", r"\bgpu\b", r"\bplaca", r"\btransceiver", r"\bgbic", r"\bsfp\b",
          r"\bpatch panel", r"\bcabo", r"\bgerador", r"\bar condicionado", r"\bcondicionador de ar", r"\bbateria", r"\bfonte de alimentacao",
          r"\bmodulo eletronico", r"\bchip", r"\bimpressora", r"\bscanner", r"\btablet", r"\bdispositivo", r"\bcontrolador", r"\bbiometric",
          r"\bcatraca", r"\bsensor", r"\bantena", r"\bhub\b", r"\bconector", r"\bpdu\b", r"\bsala cofre"]:
    add(6, C6, "inclusao", e)
add(6, C6, "material", "M", "itens de material com funcao de hardware")

for arq in ("fase2/dicionario_modelo_aquisicao_v1.csv", "fase2/dicionario_modelo_aquisicao.csv"):
    with open(arq, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["versao", "ordem", "classe", "tipo", "expressao", "observacao"])
        w.writerows(L)
print(len(L), "linhas")
