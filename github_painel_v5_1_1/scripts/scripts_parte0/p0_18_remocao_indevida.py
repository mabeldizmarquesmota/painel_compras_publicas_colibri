"""Julgamentos das compras removidas pelo ajuste do dicionario e taxa de remocao indevida.

Entrada: validacao/remocao_fichas_<amostra>.csv (p0_17). Julgamentos: revisao manual de cada ficha, com o mesmo
criterio de pertinencia da secao 6 do relatorio. A remocao e indevida quando a compra removida era pertinente a
categoria. Abaixo, para cada categoria, a lista das remocoes indevidas (ordem da ficha) com justificativa, e as
justificativas especificas de remocoes corretas que nao se explicam pelo trecho de exclusao; as demais remocoes
corretas recebem a justificativa correspondente ao trecho que hoje as exclui (dicionario MOTIVO_POR_TRECHO),
conferida na revisao.
Saidas: validacao/remocao_indevida_<categoria>.csv e validacao/remocao_indevida_por_categoria.csv
Uso (a partir de Processado/):  python scripts_parte0/p0_18_remocao_indevida.py remocao1
"""
import csv
import sys

AMOSTRA = sys.argv[1] if len(sys.argv) > 1 else "remocao1"

INDEVIDAS = {
    "remocao1": {
        "ia": {43: "plataforma de criação e edição de vídeos desenvolvida por IA (licença de software de IA); excluída pela palavra 'celular'"},
        "nuvem": {22: "Adobe Creative Cloud contratado expressamente na modalidade SaaS",
                  55: "inclui Canva Equipes (software como serviço em nuvem)",
                  66: "inclui licenças Google Workspace (software como serviço em nuvem)"},
        "plataformas": {24: "inclui licenciamento de software por subscrição; excluída pela palavra 'roteador'",
                        45: "licença de uso de plataforma web de comunicação; excluída pela palavra 'smartphones'",
                        66: "licença de ferramenta de software de monitoramento; excluída pela palavra 'celulares'"},
        "data_center": {7: "baterias do sistema de nobreak/UPS do data center",
                        8: "manutenção e monitoramento de sala-cofre/sala segura (rótulo CATSER de sala-cofre)",
                        12: "manutenção de rack seguro (infraestrutura física de data center)",
                        36: "disco compatível com servidor PowerEdge R740 (objeto indica uso em servidor)",
                        46: "manutenção de sala segura (rótulo CATSER de sala-cofre)",
                        50: "garantia e suporte de hardware e licenças que compõem o data center",
                        56: "suporte de hardware dos equipamentos que compõem a solução de data center",
                        77: "discos para RAID, servidor e NAS (objeto indica uso em servidor)",
                        85: "manutenção da sala de servidores (sala segura modular)",
                        96: "módulos de expansão de storage all-flash do data center",
                        99: "discos para servidor de alto desempenho de virtualização",
                        100: "discos para storage NAS"},
        "seguranca": {8: "storage para ambientes de backup/restore",
                      20: "link com implementação e gestão de firewalls",
                      40: "plataforma de conscientização em segurança da informação",
                      60: "licenças de antivírus EDR; excluída pela palavra 'notebooks'",
                      75: "fitas LTO Ultrium 8 para backup (grafia 'LTO Ultrium 8' não coberta)",
                      83: "destruição segura de discos para evitar vazamento de dados",
                      91: "discos para servidor de backup do data center",
                      92: "licenciamento Veeam de backup/restore",
                      93: "discos para expansão de storage de servidor de backup"},
    },
}
CORRETAS_ESPECIFICAS = {
    "remocao1": {
        "ia": {11: "aparelho (smartphone) sem IA como objeto", 13: "curadoria de exposição de artes, sem relação",
               14: "insumo de projeto de pesquisa", 19: "gestão administrativo-financeira de projeto",
               24: "termo é nome de órgão (Secretaria de Inovação e IA)", 25: "termo é nome de órgão",
               26: "projeto de fundação de apoio", 28: "termo é nome de órgão", 57: "termo é nome de órgão",
               63: "TV com assistente virtual integrado (atributo)", 75: "plataforma de cursos",
               80: "projeto de pesquisa de fundação de apoio", 85: "celular com reconhecimento facial (atributo)",
               89: "publicação de artigo", 94: "publicação de artigo", 97: "projeto de pesquisa de fundação de apoio",
               99: "projeto de extensão (apoio administrativo)"},
        "nuvem": {11: "serviço fotográfico de evento", 39: "antivírus (nome de produto com 'Cloud')",
                  48: "plataforma de cursos AWS"},
        "plataformas": {50: "roteador (sistema operacional é atributo)", 53: "locação de notebooks",
                        73: "SAP = Secretaria de Administração Penitenciária", 92: "equipamento médico (atributo)",
                        96: "SAP = Secretaria de Administração Penitenciária"},
        "data_center": {24: "disco externo avulso", 42: "disco avulso em compra genérica", 44: "discos avulsos",
                        61: "virtualização (software de outra categoria)", 68: "licenças Windows Server (software)",
                        97: "licenças Microsoft e Veeam (software)", 98: "serviços gerenciados de rede",
                        23: "appliance de backup (categoria segurança)", 51: "nuvem privada IaaS"},
        "seguranca": {3: "locação de equipamentos para data center, backup só mencionado",
                      7: "apoio técnico em contratações de TIC", 13: "gestão de frequência",
                      36: "hospedagem em nuvem", 37: "plataforma de gestão de pessoas", 49: "Power BI",
                      65: "hospedagem de sites", 70: "hospedagem de site", 72: "notebooks",
                      73: "conectividade via satélite", 89: "link de internet", 90: "manutenção de site",
                      94: "renovação de parque de computadores"},
    },
}
MOTIVO_POR_TRECHO = [  # (fragmento do trecho de exclusao, justificativa)
    (("curso", "capacit", "treinamento", "inscric", "participac", "palestr", "congresso", "seminario", "simposio",
      "evento", "pos-graduacao", "posgraduacao", "masterclass", "oficina", "docente", "instrutor", "lanches",
      "etp", "workshop", "turma"), "curso, evento ou capacitação sobre o tema, não contratação da tecnologia"),
    (("funape", "finatec", "fundac", "administrativo-financeira", "gestao administrativ", "apoio administrativo",
      "projeto de pesquisa"), "projeto de pesquisa ou extensão gerido por fundação de apoio"),
    (("eletrodo", "solda", "vareta"), "AWS é norma de solda (American Welding Society)"),
    (("creative cloud",), "licença Adobe Creative Cloud (software de uso geral, não serviço de nuvem)"),
    (("endpoint security cloud",), "antivírus com 'Cloud' no nome do produto"),
    (("notebook", "microcomputador", "tablet", "all in one", "all-in-one", "workstation", "smartphone", "celular",
      "servidor, tipo", "servidor tipo", "caracteristicas adicionais sistema operacional", "teclado"),
     "equipamento em que o termo é atributo do cadastro"),
    (("resolucao sap", "kit preso"), "SAP = Secretaria de Administração Penitenciária"),
    (("aplicacao", "storage nas", "gabinete"), "peça ou disco avulso em lista genérica de suprimentos"),
    (("sala cofre / sala tele",), "rótulo CATSER de videowall ou telepresença, sem sala-cofre"),
    (("roteador", "modem", "criptografia", "wpa", "edr", "memoria ram", "firewall integrado", "leitor", "leitora"),
     "atributo de equipamento de rede ou acessório"),
    (("datacenter core", "cis suite", "for virtual datacenters", "windows server", "red hat", "veeam", "licenc"),
     "software (edição 'Datacenter' ou licença de outra categoria)"),
    (("firewall", "antivirus", "backup", "endpoint", "waf"), "segurança ou backup (outra categoria)"),
    (("link", "sd-wan", "dvr", "navio", "self storage", "hpc"), "sem relação com infraestrutura de data center"),
    (("certificad",), "certificado digital (categoria identidade)"),
    (("hemodialise", "reagente"), "equipamento ou insumo fora de TI"),
    (("secretaria",), "termo é nome de órgão"),
]


def motivo(ficha):
    trecho = ((ficha.get("exclusao_objeto") or "") + " " + (ficha.get("exclusao_itens") or "")).lower()
    for frags, texto in MOTIVO_POR_TRECHO:
        if any(f in trecho for f in frags):
            return texto
    return "menção incidental ou atributo acessório (sem contratação da tecnologia)"


with open(f"validacao/remocao_fichas_{AMOSTRA}.csv", encoding="utf-8") as f:
    fichas = list(csv.DictReader(f, delimiter=";"))

resumo = []
for seg in sorted({r["segmento"] for r in fichas}):
    rs = sorted((r for r in fichas if r["segmento"] == seg), key=lambda r: int(r["ordem"]))
    ind = INDEVIDAS[AMOSTRA].get(seg, {})
    esp = CORRETAS_ESPECIFICAS[AMOSTRA].get(seg, {})
    assert set(ind) <= {int(r["ordem"]) for r in rs} and set(esp) <= {int(r["ordem"]) for r in rs}
    linhas = []
    for r in rs:
        k = int(r["ordem"])
        linhas.append({
            "amostra": AMOSTRA, "ordem": k, "id_compra": r["id_compra"], "objeto": r["objeto"],
            "termo_que_classificava": " | ".join(t for t in (r["termo_objeto"], r["termo_itens"]) if t),
            "trecho_que_exclui": " | ".join(t for t in (r["exclusao_objeto"], r["exclusao_itens"]) if t),
            "julgamento": "remocao_indevida" if k in ind else "remocao_correta",
            "justificativa": ind.get(k) or esp.get(k) or motivo(r),
        })
    arq = f"validacao/remocao_indevida_{seg}.csv"
    modo = "w" if AMOSTRA == "remocao1" else "a"
    with open(arq, modo, encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(linhas[0]), delimiter=";")
        if modo == "w":
            w.writeheader()
        w.writerows(linhas)
    n, k = len(linhas), sum(l["julgamento"] == "remocao_indevida" for l in linhas)
    resumo.append({"amostra": AMOSTRA, "categoria": seg, "n_julgadas": n, "n_remocao_indevida": k,
                   "taxa_remocao_indevida_pct": round(100.0 * k / n, 1)})

with open("validacao/remocao_indevida_por_categoria.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(resumo[0]), delimiter=";")
    w.writeheader()
    w.writerows(resumo)
for r in resumo:
    print(r)
