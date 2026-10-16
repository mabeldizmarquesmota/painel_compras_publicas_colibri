"""Ajuste do dicionario de termos apos a verificacao por amostragem (amostra 1).

Motivo: cinco categorias ficaram abaixo de 80% de precisao na amostra 1 (validacao/amostra1_precisao.csv).
Identidade (87,3%) nao e alterada. As alteracoes atacam os padroes de erro observados na revisao manual
(validacao/julgamentos/*.txt) e estao descritas em METODOLOGIA.md.

Uso (a partir de Processado/):  python scripts_parte0/p0_05_dicionario_v2.py
Entrada: dicionario_termos_v1_original.csv (copia do dicionario usado nas etapas 4 a 7).
Saida:   dicionario_termos.csv (versao 2, lida por p0_02_classificacao.sql).
Os termos sao regex RE2 aplicadas ao texto em minusculas e sem acentos.
"""
import csv
import os
import shutil

V1 = "dicionario_termos_v1_original.csv"
if not os.path.exists(V1):
    shutil.copyfile("dicionario_termos.csv", V1)

with open(V1, encoding="utf-8") as f:
    v1 = list(csv.DictReader(f))

# Termos de inclusao substituidos por versoes com contexto (categoria seguranca)
SUBSTITUIR = {
    ("seguranca", r"seguranca da informacao"):
        r"(solucao|solucoes|servicos?|software|equipamentos?|itens|auditoria|pericia|consultoria|gestao|analise"
        r"|monitoramento|licenc\w*|produtos?|plataformas?|ferramentas?|sistemas?|appliances?|suporte)( \w+){0,3}"
        r" (de|em|para|a) seguranca da informacao",
    ("seguranca", r"\bbackup\b"):
        r"(solucao|solucoes|software|sistemas?|subsistemas?|servicos?|appliances?|licenc\w*|subscric\w*"
        r"|suporte|fitas?|cartuch\w*|midias?|robos?|bibliotecas?|repositorios?"
        r"|armazenamento|plano|politica|rotinas?|processos?|gerenciamento|gestao|infraestrutura|infra"
        r"|plataformas?|agentes?|gravador(es)?)( \w+)? (de |para |do |da )?backup",
}
INCLUSAO_EXTRA = {
    "seguranca": [
        r"backup (em nuvem|as a service|como servico|de dados|corporativo)",
        r"backup ?(&|e) ?(recovery|restore|recuperacao)",
        r"\blto[- ]?\d",
        r"seguranca da informacao e cibernetica",
    ],
}

# Contexto de curso, evento, capacitacao ou publicacao (nao e contratacao da tecnologia)
# "capacitacao" so conta quando dirigida a servidores ou equipes: capacitacao de usuarios e parte de contratos legitimos
EDU = (r"(\b(cursos?|capacitac(ao|oes) (de|dos|das|para) (servidor|militar|magistrad|membro|agente|vereador"
       r"|funcionari|colaborador|gestor|equipe|profissiona)\w*|capacitac(ao|oes) (em|sobre|profissional)|seminarios?|congressos?|simposios?|palestras?|workshops?|masterclass"
       r"|webinars?|conferencias?|summit|pos[- ]graduacao|mba|inscric(ao|oes)|instrutor(es)?"
       r"|lanches?|patrocinio|horas?[- ]aula|atividades didaticas)\b"
       r"|\b(no|na|ao|do|da) (treinamento|evento)\b)")
PUB = r"\b(publicacao|artigos?)\b"
# texto (objeto da compra ou descricao do item) que comeca por curso, capacitacao, treinamento ou inscricao
# (inclui os rotulos CATSER "Treinamento Qualificacao Profissional" e "Pagamento Inscricao Eventos")
INICIO_CURSO = (r"^\W*((contratacao|aquisicao|prestacao) (de|da|do|dos|das) |pagamento (de |da )?(taxa (de )?)?)?"
                r"(empresa( especializada)?( em| para| para ministrar)? |servicos? (de )?|vagas? (no |em |para )?"
                r"|uma? |os? |as? )?(capacitac\w*|treinamentos?|cursos?|inscric\w*|participac\w*)\b")

EXCLUSAO_EXTRA = {
    "ia": [
        r"secretaria[^.;]{0,60}inteligencia artificial",
        r"\b(cursos?|seminarios?|congressos?|simposios?|palestra(s|nte)?|workshops?|masterclass|webinars?"
        r"|conferencias?|summit|pos[- ]graduacao|mba|instrutor(es)?|lanches?"
        r"|patrocinio|horas?[- ]aula|atividades didaticas|turma|oficinas?|encontro"
        r"|evento (externo|presencial|online|on-line)|(no|do|ao) evento|eventos? de capacitacao"
        r"|projeto de (pesquisa|extensao)|experiencias artisticas|(treinamento|capacitacao) e aperfeicoamento)\b",
        # ajuste da amostra 2: projetos geridos por fundacao de apoio, aparelhos e softwares de uso geral com IA
        r"fundac(ao|oes) de apoio|gestao administrativ[ao] e financeira|apoio administrativo|termo de fomento"
        r"|\b(funape|fundep|finatec|funtef|fapunifesp)\b",
        r"\b(smartphones?|celular(es)?|notebooks?|ultrabooks?|smart ?tvs?|televisor(es)?|tv \d\d)\b",
        r"creative cloud|banco de imagens|\bmatlab\b|\blivros?\b",
        INICIO_CURSO,
        # ajuste da amostra 3: outras formas de curso e evento, fundacoes e softwares de uso geral
        r"^\W*eventos?\b|vagas? (em|para) (o |a )?(evento|realizacao)|\beventos? (tele)?presencia\w*"
        r"|realizacao presencial|acao educacional|\bpa?lestras?\b|estrutura para realizacao",
        r"(contratacao|aquisicao) (de|da|do) (capacitac\w*|cursos?)\b|\b(na|a|da) capacitac\w* [\"“]"
        r"|participac\w*[^;]{0,120}\b(capacitac\w*|cursos?|eventos?|treinamentos?|seminarios?|congressos?)\b"
        r"|capacitac\w* (aos|as) |treinamento (presencial|de inteligencia)|treinamento ?[:\"“]",
        r"\b(dfd|etp)\b|planilhas orcamentarias|\bsinapi\b",
        r"fundac(ao|oes)( \w+){0,4} para apoiar|administrativo-financeira",
        r"banco de precos|\bcapcut\b",
    ],
    "nuvem": [
        r"\bsolda|eletrodo|soldagem|\bvareta",           # AWS = norma da American Welding Society
        r"creative cloud",                               # nome de produto Adobe (licenca de software)
        r"endpoint security cloud",                      # nome de produto antivirus
    ],
    "plataformas": [
        r"\b(micro ?computador(es)?|notebooks?|tablets?|smartphones?|celular(es)?|all[- ]in[- ]one"
        r"|workstations?|roteador(es)?|teclados?|servidor,? tipo|identificador biometrico|sonorizacao)\b",
        r"caracteristicas adicionais:? ?sistema operacional",
        r"resolucao sap|\bsap[- ]?\d{1,4}/|kit pres[oa]s?|uniformes? para sap",
    ],
    "data_center": [
        r"aplicacao:? ?(servidor (de rede|storage)|storage|conectar fonte ao equipamento storage)",
        r"caracteristicas ?adicionais:? ?storage nas",
        r"compatibilidade:? ?storage",
        r"(windows server|jira( software)?|cis suite|suite) data ?centers?",
        r"for virtual datacenters",
        r"self[- ]storage",
        r"sala cofre / sala tele",
        r"\bansys\b",
        # hospedagem acessoria de sistema contratado e software de outra categoria instalado no data center
        r"(licenc\w*|locacao de software|sistemas? (integrad\w* )?(de )?gestao|solucao integrada|aplicacao web"
        r"|modulo)[^;]{0,300}hospedagem",
        r"(virtualizacao|vmware|veeam|red hat|sistemas? operaciona\w*|netbackup|backup|firewall|antivirus)"
        r"[^;]{0,200}(data ?centers?|servidor(es)? de rede)",
        r"\bdvr\b",
        # ajuste da amostra 2
        r"(windows server|server)( \d{4})?( edicao)? data ?center|data ?center \d-core|datacenter core",
        r"(sistemas? (de gestao|integrad\w*)|softwares? de gestao|licenc\w* de (uso|direito|software)|licenciamento"
        r" (de|temporario de) softwares?|solucao integrada|solucoes integradas|aplicac(ao|oes) web|modulos?)"
        r"[^;]{0,250}(hospedad\w*|provimento de data ?center|data ?centers?)",
        r"\blinks? (de )?(internet|comunicac\w*|dedicad\w*|de acesso)|sd-wan|\bpostes\b|central telefonica"
        r"|rede privada|energia eletrica - fornecimento|fornecimento de energia eletrica para",
        r"armazenamento (de arquivos )?em nuvem|servidor(es)? em nuvem|cloud storage|google cloud",
        r"\bwaf\b|aplicacoes web/api|endpoints?",
        r"helice de passo|passo controlado|\bnavio|embarcac",
        r"\btoken\b|midia criptografica|\bfrasco|storage tube|energy storage",
        INICIO_CURSO,
    ],
    "seguranca": [
        r"criptografia wep|wep, wp|bluetooth[^.;]{0,20}edr|\+ ?edr\b",
        r"firewall integrado|recurso seguranca:? ?f",
        r"client server suite",                          # CATMAT generico usado para outros softwares
        r"pre-?amplificador|mixer",
        r"certificad\w* digita|\be-?cpf\b|\be-?cnpj\b",  # certificados digitais: categoria identidade
        r"oxigenio|ar comprimido|hemodialise|hemocultura|criogenic",
        r"\b(notebooks?|micro ?computador(es)?|all[- ]in[- ]one)\b",
        # ajuste da amostra 2: atributos de equipamento, backup fora de TI, conectividade e hospedagem
        r"criptografias? (wpa|wep|por aes|aes|de \d|\d)|protocolo enlace:? ?criptografia|criptografia \d{3}",
        r"retina xdr|\b(smartphones?|celular(es)?|roteador(es)?|modem|mikrotik|receptor|helicoptero)\b",
        r"radio ?comunicac|cameras? instaladas|leitor(a)? (biometrico|cartao)|cartao proximidade",
        r"aplicacao:? ?firewall, capacidade ?memoria|memoria ram",
        r"\blinks? (de )?(backup|internet|dedicad\w*|de acesso)|backup (de|do) (acesso|link)|backup e redundancia",
        r"equipamentos? de backup|cilindros? backup|unidade completa de backup",
        r"hospedagem (vps|de e-?mails?)|servidor(es)? em nuvem|certificado ssl|\bssl dv\b",
        r"\bciosp\b|seguranca publica|reagentes?",
        INICIO_CURSO,
    ],
}
AJUSTADAS = ["ia", "nuvem", "plataformas", "data_center", "seguranca"]

linhas = []
for r in v1:
    k = (r["segmento"], r["termo_regex"])
    if k in SUBSTITUIR:
        r = dict(r, termo_regex=SUBSTITUIR[k])
    linhas.append(r)
camada = {r["segmento"]: r["camada"] for r in v1}
for seg, termos in INCLUSAO_EXTRA.items():
    for t in termos:
        linhas.append({"segmento": seg, "camada": camada[seg], "tipo": "inclusao", "termo_regex": t})

# exclusao de contexto: curso/evento ou publicacao seguidos de um termo de inclusao da categoria
for seg in AJUSTADAS:
    inc = "|".join(r["termo_regex"] for r in linhas if r["segmento"] == seg and r["tipo"] == "inclusao")
    linhas.append({"segmento": seg, "camada": camada[seg], "tipo": "exclusao",
                   "termo_regex": EDU + r"[^;]{0,200}(" + inc + ")"})
    linhas.append({"segmento": seg, "camada": camada[seg], "tipo": "exclusao",
                   "termo_regex": PUB + r"[^;]{0,250}(" + inc + ")"})
    for t in EXCLUSAO_EXTRA.get(seg, []):
        linhas.append({"segmento": seg, "camada": camada[seg], "tipo": "exclusao", "termo_regex": t})

with open("dicionario_termos.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["segmento", "camada", "tipo", "termo_regex"])
    w.writeheader()
    w.writerows(linhas)
print(len(v1), "->", len(linhas), "linhas")
