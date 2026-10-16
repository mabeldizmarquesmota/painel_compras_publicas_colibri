"""Painel, etapa 0: versao em linguagem comum de cada expressao de dicionario_termos.csv (dicionario final).

Entrada: dicionario_termos.csv. Regra: cada expressao regular recebe uma descricao em linguagem comum; o script
falha se alguma expressao do dicionario ficar sem descricao ou se houver descricao para expressao inexistente, para
que as palavras-chave exibidas no painel sejam exatamente as usadas na classificacao.
Saida: tabelas_painel_v3/dicionario_termos_legivel.csv (segmento; camada; tipo; termo_regex; texto_legivel)
Uso (a partir de Processado/):  python scripts_painel_v3/p1_00_dicionario_legivel.py
"""
import csv
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
os.makedirs("tabelas_painel", exist_ok=True)

# (segmento, tipo, regra de identificacao da expressao, texto legivel). A regra e a expressao exata (str) ou, para
# as familias de exclusao repetidas em varias categorias, uma tupla ("prefixo", inicio da expressao).
CURSOS = ("prefixo", r"(\b(cursos?|capacitac(ao|oes) (de|dos|das|para) (servidor")
PUBLIC = ("prefixo", r"\b(publicacao|artigos?)\b[^;]{0,250}")
INICIO = r"^\W*((contratacao|aquisicao|prestacao) (de|da|do|dos|das) |pagamento (de |da )?(taxa (de )?)?)?(empresa( especializada)?( em| para| para ministrar)? |servicos? (de )?|vagas? (no |em |para )?|uma? |os? |as? )?(capacitac\w*|treinamentos?|cursos?|inscric\w*|participac\w*)\b"
T_CURSOS = "cursos, capacitações, seminários, congressos, palestras, workshops, pós-graduação, inscrições e eventos sobre o tema"
T_PUBLIC = "publicação de artigos sobre o tema"
T_INICIO = "objeto que começa por contratação de capacitação, treinamento, curso, inscrição ou participação"

MAPA = [
    # ---------------- data center
    ("data_center", "inclusao", "data ?center", "data center"),
    ("data_center", "inclusao", "centro de dados", "centro de dados"),
    ("data_center", "inclusao", "sala[- ]cofre", "sala-cofre"),
    ("data_center", "inclusao", "colocation", "colocation"),
    ("data_center", "inclusao", r"\bstorage\b", "storage"),
    ("data_center", "inclusao", "hiperconvergen", "hiperconvergência"),
    ("data_center", "inclusao", "supercomputad", "supercomputador"),
    ("data_center", "inclusao", r"\bhpc\b", "HPC (computação de alto desempenho)"),
    ("data_center", "inclusao", "servidor(es)? (de rede|rack|blade)", "servidores de rede, rack ou blade"),
    ("data_center", "exclusao", "servidor(es)? public", "servidor público"),
    ("data_center", "exclusao", "servidor(es)? efetiv", "servidor efetivo"),
    ("data_center", "exclusao", CURSOS, T_CURSOS),
    ("data_center", "exclusao", PUBLIC, T_PUBLIC),
    ("data_center", "exclusao", "aplicacao:? ?(servidor (de rede|storage)|storage|conectar fonte ao equipamento storage)",
     "peça cuja aplicação é servidor ou storage (atributo do cadastro de material)"),
    ("data_center", "exclusao", "caracteristicas ?adicionais:? ?storage nas", "storage NAS como característica adicional de equipamento"),
    ("data_center", "exclusao", "compatibilidade:? ?storage", "peça compatível com storage"),
    ("data_center", "exclusao", "(windows server|jira( software)?|cis suite|suite) data ?centers?", "edição Datacenter de software (Windows Server, Jira, suítes)"),
    ("data_center", "exclusao", "for virtual datacenters", "licença for virtual datacenters"),
    ("data_center", "exclusao", "self[- ]storage", "self storage (guarda-volumes)"),
    ("data_center", "exclusao", "sala cofre / sala tele", "rótulo de catálogo de videowall ou telepresença"),
    ("data_center", "exclusao", r"\bansys\b", "software Ansys"),
    ("data_center", "exclusao", r"(licenc\w*|locacao de software|sistemas? (integrad\w* )?(de )?gestao|solucao integrada|aplicacao web|modulo)[^;]{0,300}hospedagem",
     "licença ou sistema de gestão com hospedagem incluída"),
    ("data_center", "exclusao", "(virtualizacao|vmware|veeam|red hat|sistemas? operaciona\\w*|netbackup|backup|firewall|antivirus)[^;]{0,200}(data ?centers?|servidor(es)? de rede)",
     "software de virtualização, backup ou segurança para data center"),
    ("data_center", "exclusao", r"\bdvr\b", "DVR (gravador de vídeo)"),
    ("data_center", "exclusao", r"(windows server|server)( \d{4})?( edicao)? data ?center|data ?center \d-core|datacenter core",
     "licença Windows Server edição Datacenter"),
    ("data_center", "exclusao", r"(sistemas? (de gestao|integrad\w*)|softwares? de gestao|licenc\w* de (uso|direito|software)|licenciamento (de|temporario de) softwares?|solucao integrada|solucoes integradas|aplicac(ao|oes) web|modulos?)[^;]{0,250}(hospedad\w*|provimento de data ?center|data ?centers?)",
     "sistema de gestão ou aplicação web hospedada em data center do fornecedor"),
    ("data_center", "exclusao", r"\blinks? (de )?(internet|comunicac\w*|dedicad\w*|de acesso)|sd-wan|\bpostes\b|central telefonica|rede privada|energia eletrica - fornecimento|fornecimento de energia eletrica para",
     "links de internet, SD-WAN, telefonia, rede privada e energia elétrica"),
    ("data_center", "exclusao", "armazenamento (de arquivos )?em nuvem|servidor(es)? em nuvem|cloud storage|google cloud",
     "armazenamento ou servidor em nuvem (categoria nuvem)"),
    ("data_center", "exclusao", r"\bwaf\b|aplicacoes web/api|endpoints?", "WAF e proteção de endpoints (categoria segurança)"),
    ("data_center", "exclusao", r"helice de passo|passo controlado|\bnavio|embarcac", "hélice de passo controlado, navio e embarcação"),
    ("data_center", "exclusao", r"\btoken\b|midia criptografica|\bfrasco|storage tube|energy storage", "token, mídia criptográfica, frasco, storage tube e energy storage"),
    ("data_center", "exclusao", INICIO, T_INICIO),
    # ---------------- nuvem
    ("nuvem", "inclusao", "computacao em nuvem", "computação em nuvem"),
    ("nuvem", "inclusao", "servicos? de nuvem", "serviços de nuvem"),
    ("nuvem", "inclusao", "nuvem (publica|privada|hibrida|de governo)", "nuvem pública, privada, híbrida ou de governo"),
    ("nuvem", "inclusao", r"\bcloud\b", "cloud"),
    ("nuvem", "inclusao", r"\biaas\b", "IaaS"),
    ("nuvem", "inclusao", r"\bpaas\b", "PaaS"),
    ("nuvem", "inclusao", r"\bsaas\b", "SaaS"),
    ("nuvem", "inclusao", "multinuvem", "multinuvem"),
    ("nuvem", "inclusao", "multicloud", "multicloud"),
    ("nuvem", "inclusao", "broker de nuvem", "broker de nuvem"),
    ("nuvem", "inclusao", "amazon web services", "Amazon Web Services"),
    ("nuvem", "inclusao", r"\baws\b", "AWS"),
    ("nuvem", "inclusao", r"\bazure\b", "Azure"),
    ("nuvem", "inclusao", "google cloud", "Google Cloud"),
    ("nuvem", "inclusao", r"\bgcp\b", "GCP"),
    ("nuvem", "inclusao", "oracle cloud", "Oracle Cloud"),
    ("nuvem", "inclusao", "huawei cloud", "Huawei Cloud"),
    ("nuvem", "exclusao", CURSOS, T_CURSOS),
    ("nuvem", "exclusao", PUBLIC, T_PUBLIC),
    ("nuvem", "exclusao", r"\bsolda|eletrodo|soldagem|\bvareta", "solda, eletrodo e vareta (AWS como norma de soldagem)"),
    ("nuvem", "exclusao", "creative cloud", "Adobe Creative Cloud"),
    ("nuvem", "exclusao", "endpoint security cloud", "antivírus Endpoint Security Cloud"),
    # ---------------- plataformas
    ("plataformas", "inclusao", "microsoft 365", "Microsoft 365"),
    ("plataformas", "inclusao", "office 365", "Office 365"),
    ("plataformas", "inclusao", r"\bm365\b", "M365"),
    ("plataformas", "inclusao", "windows server", "Windows Server"),
    ("plataformas", "inclusao", "sistema operacional", "sistema operacional"),
    ("plataformas", "inclusao", r"\bvmware\b", "VMware"),
    ("plataformas", "inclusao", "virtualizacao", "virtualização"),
    ("plataformas", "inclusao", "red hat", "Red Hat"),
    ("plataformas", "inclusao", r"\bsap\b", "SAP"),
    ("plataformas", "inclusao", "oracle database", "Oracle Database"),
    ("plataformas", "inclusao", "sql server", "SQL Server"),
    ("plataformas", "inclusao", "subscricao", "subscrição"),
    ("plataformas", "inclusao", "licenc(a|as|iamento) de (uso de )?software", "licença ou licenciamento de (uso de) software"),
    ("plataformas", "exclusao", "licenca (ambiental|premio|maternidade|paternidade)", "licença ambiental, prêmio, maternidade ou paternidade"),
    ("plataformas", "exclusao", CURSOS, T_CURSOS),
    ("plataformas", "exclusao", PUBLIC, T_PUBLIC),
    ("plataformas", "exclusao", r"\b(micro ?computador(es)?|notebooks?|tablets?|smartphones?|celular(es)?|all[- ]in[- ]one|workstations?|roteador(es)?|teclados?|servidor,? tipo|identificador biometrico|sonorizacao)\b",
     "equipamentos em que o software é atributo (microcomputador, notebook, tablet, celular, roteador, teclado, sonorização)"),
    ("plataformas", "exclusao", "caracteristicas adicionais:? ?sistema operacional", "sistema operacional como característica adicional de equipamento"),
    ("plataformas", "exclusao", r"resolucao sap|\bsap[- ]?\d{1,4}/|kit pres[oa]s?|uniformes? para sap", "SAP como Secretaria de Administração Penitenciária"),
    # ---------------- inteligencia artificial
    ("ia", "inclusao", "inteligencia artificial", "inteligência artificial"),
    ("ia", "inclusao", "aprendizado de maquina", "aprendizado de máquina"),
    ("ia", "inclusao", "machine learning", "machine learning"),
    ("ia", "inclusao", "deep learning", "deep learning"),
    ("ia", "inclusao", "ia generativa", "IA generativa"),
    ("ia", "inclusao", r"\bllm\b", "LLM"),
    ("ia", "inclusao", "modelos? de linguagem", "modelos de linguagem"),
    ("ia", "inclusao", "chatbot", "chatbot"),
    ("ia", "inclusao", "assistente virtual", "assistente virtual"),
    ("ia", "inclusao", "visao computacional", "visão computacional"),
    ("ia", "inclusao", "reconhecimento facial", "reconhecimento facial"),
    ("ia", "inclusao", "processamento de linguagem natural", "processamento de linguagem natural"),
    ("ia", "inclusao", r"(solucao|plataforma|ferramenta|sistema|modelo) (de|com|baseada em) \bia\b",
     "solução, plataforma, ferramenta, sistema ou modelo de IA"),
    ("ia", "exclusao", CURSOS, T_CURSOS),
    ("ia", "exclusao", PUBLIC, T_PUBLIC),
    ("ia", "exclusao", "secretaria[^.;]{0,60}inteligencia artificial", "inteligência artificial no nome de secretaria"),
    ("ia", "exclusao", ("prefixo", r"\b(cursos?|seminarios?|congressos?|simposios?|palestra(s|nte)?"),
     "cursos, eventos, turmas, oficinas e projetos de pesquisa ou extensão"),
    ("ia", "exclusao", r"fundac(ao|oes) de apoio|gestao administrativ[ao] e financeira|apoio administrativo|termo de fomento|\b(funape|fundep|finatec|funtef|fapunifesp)\b",
     "fundação de apoio, gestão administrativa e financeira e termo de fomento"),
    ("ia", "exclusao", r"\b(smartphones?|celular(es)?|notebooks?|ultrabooks?|smart ?tvs?|televisor(es)?|tv \d\d)\b",
     "celular, notebook e televisor com recurso de IA"),
    ("ia", "exclusao", r"creative cloud|banco de imagens|\bmatlab\b|\blivros?\b", "Creative Cloud, banco de imagens, Matlab e livros"),
    ("ia", "exclusao", INICIO, T_INICIO),
    ("ia", "exclusao", r"^\W*eventos?\b|vagas? (em|para) (o |a )?(evento|realizacao)|\beventos? (tele)?presencia\w*|realizacao presencial|acao educacional|\bpa?lestras?\b|estrutura para realizacao",
     "eventos, ações educacionais e palestras"),
    ("ia", "exclusao", ("prefixo", r"(contratacao|aquisicao) (de|da|do) (capacitac\w*|cursos?)\b"),
     "contratação de capacitação, curso ou treinamento"),
    ("ia", "exclusao", r"\b(dfd|etp)\b|planilhas orcamentarias|\bsinapi\b", "elaboração de DFD, ETP e planilhas orçamentárias"),
    ("ia", "exclusao", r"fundac(ao|oes)( \w+){0,4} para apoiar|administrativo-financeira", "fundação para apoiar projeto e gestão administrativo-financeira"),
    ("ia", "exclusao", r"banco de precos|\bcapcut\b", "banco de preços e CapCut"),
    # ---------------- identidade
    ("identidade", "inclusao", "identidade digital", "identidade digital"),
    ("identidade", "inclusao", "biometri", "biometria"),
    ("identidade", "inclusao", "assinatura (eletronica|digital)", "assinatura eletrônica ou digital"),
    ("identidade", "inclusao", "certificados? digita", "certificado digital"),
    ("identidade", "inclusao", "identificacao civil", "identificação civil"),
    # ---------------- seguranca
    ("seguranca", "inclusao", ("prefixo", r"(solucao|solucoes|servicos?|software|equipamentos?|itens|auditoria|pericia"),
     "solução, serviço, software, equipamento, auditoria, consultoria, monitoramento ou licença de segurança da informação"),
    ("seguranca", "inclusao", "seguranca cibernetica", "segurança cibernética"),
    ("seguranca", "inclusao", "ciberseguranca", "cibersegurança"),
    ("seguranca", "inclusao", "firewall", "firewall"),
    ("seguranca", "inclusao", "centro de operacoes de seguranca", "centro de operações de segurança"),
    ("seguranca", "inclusao", r"\bedr\b", "EDR"),
    ("seguranca", "inclusao", r"\bxdr\b", "XDR"),
    ("seguranca", "inclusao", r"\bsiem\b", "SIEM"),
    ("seguranca", "inclusao", "antivirus", "antivírus"),
    ("seguranca", "inclusao", "criptografia", "criptografia"),
    ("seguranca", "inclusao", "protecao de endpoint", "proteção de endpoint"),
    ("seguranca", "inclusao", "teste de intrusao", "teste de intrusão"),
    ("seguranca", "inclusao", "pentest", "pentest"),
    ("seguranca", "inclusao", ("prefixo", r"(solucao|solucoes|software|sistemas?|subsistemas?|servicos?|appliances?|licenc\w*|subscric\w*|suporte|fitas?"),
     "solução, software, serviço, licença, fita, mídia, política ou infraestrutura de backup"),
    ("seguranca", "exclusao", "seguranca (patrimonial|privada|do trabalho)", "segurança patrimonial, privada ou do trabalho"),
    ("seguranca", "exclusao", "vigilancia (patrimonial|armada|desarmada)", "vigilância patrimonial, armada ou desarmada"),
    ("seguranca", "inclusao", "backup (em nuvem|as a service|como servico|de dados|corporativo)", "backup em nuvem, como serviço, de dados ou corporativo"),
    ("seguranca", "inclusao", "backup ?(&|e) ?(recovery|restore|recuperacao)", "backup e recuperação (recovery, restore)"),
    ("seguranca", "inclusao", r"\blto[- ]?\d", "fitas LTO"),
    ("seguranca", "inclusao", "seguranca da informacao e cibernetica", "segurança da informação e cibernética"),
    ("seguranca", "exclusao", CURSOS, T_CURSOS),
    ("seguranca", "exclusao", PUBLIC, T_PUBLIC),
    ("seguranca", "exclusao", r"criptografia wep|wep, wp|bluetooth[^.;]{0,20}edr|\+ ?edr\b", "criptografia WEP e Bluetooth EDR (atributos de equipamento)"),
    ("seguranca", "exclusao", "firewall integrado|recurso seguranca:? ?f", "firewall integrado a equipamento"),
    ("seguranca", "exclusao", "client server suite", "client server suite"),
    ("seguranca", "exclusao", "pre-?amplificador|mixer", "pré-amplificador e mixer"),
    ("seguranca", "exclusao", r"certificad\w* digita|\be-?cpf\b|\be-?cnpj\b", "certificado digital, e-CPF e e-CNPJ (categoria identidade)"),
    ("seguranca", "exclusao", "oxigenio|ar comprimido|hemodialise|hemocultura|criogenic", "oxigênio, ar comprimido, hemodiálise e criogenia (backup de gases e equipamentos)"),
    ("seguranca", "exclusao", r"\b(notebooks?|micro ?computador(es)?|all[- ]in[- ]one)\b", "notebook, microcomputador e all-in-one"),
    ("seguranca", "exclusao", r"criptografias? (wpa|wep|por aes|aes|de \d|\d)|protocolo enlace:? ?criptografia|criptografia \d{3}",
     "criptografia WPA, WEP ou AES como atributo de equipamento de rede"),
    ("seguranca", "exclusao", r"retina xdr|\b(smartphones?|celular(es)?|roteador(es)?|modem|mikrotik|receptor|helicoptero)\b",
     "celular, roteador, modem, receptor e tela Retina XDR"),
    ("seguranca", "exclusao", r"radio ?comunicac|cameras? instaladas|leitor(a)? (biometrico|cartao)|cartao proximidade",
     "radiocomunicação, câmeras e leitores de cartão ou biometria"),
    ("seguranca", "exclusao", "aplicacao:? ?firewall, capacidade ?memoria|memoria ram", "memória para firewall (atributo de peça)"),
    ("seguranca", "exclusao", r"\blinks? (de )?(backup|internet|dedicad\w*|de acesso)|backup (de|do) (acesso|link)|backup e redundancia",
     "link de internet ou link de backup"),
    ("seguranca", "exclusao", "equipamentos? de backup|cilindros? backup|unidade completa de backup", "equipamento, cilindro ou unidade de backup (não informático)"),
    ("seguranca", "exclusao", r"hospedagem (vps|de e-?mails?)|servidor(es)? em nuvem|certificado ssl|\bssl dv\b", "hospedagem, servidor em nuvem e certificado SSL"),
    ("seguranca", "exclusao", r"\bciosp\b|seguranca publica|reagentes?", "segurança pública, CIOSP e reagentes"),
    ("seguranca", "exclusao", INICIO, T_INICIO),
]


def casa(regra, termo):
    if isinstance(regra, tuple):
        return termo.startswith(regra[1])
    return termo == regra


with open("dicionario_termos.csv", encoding="utf-8") as f:
    dic = list(csv.DictReader(f))

usadas = [0] * len(MAPA)
saida = []
for d in dic:
    achou = [k for k, (seg, tipo, regra, _) in enumerate(MAPA)
             if seg == d["segmento"] and tipo == d["tipo"] and casa(regra, d["termo_regex"])]
    if len(achou) != 1:
        sys.exit(f"expressao sem descricao unica ({len(achou)}): {d['segmento']} {d['tipo']} {d['termo_regex'][:120]}")
    usadas[achou[0]] += 1
    saida.append({**d, "texto_legivel": MAPA[achou[0]][3]})
sobras = [MAPA[k][:2] + (str(MAPA[k][2])[:60],) for k, n in enumerate(usadas) if n == 0]
if sobras:
    sys.exit(f"descricoes sem expressao no dicionario: {sobras}")

with open("tabelas_painel_v3/dicionario_termos_legivel.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(saida[0]), delimiter=";")
    w.writeheader()
    w.writerows(saida)
print("ok", len(saida), "expressoes;", sum(1 for s in saida if s["tipo"] == "inclusao"), "de inclusao")
