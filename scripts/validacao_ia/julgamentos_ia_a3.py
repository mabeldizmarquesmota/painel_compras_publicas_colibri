"""Julgamentos da amostra 3 (semente ia_a3, dicionario versao 3, segundo e ultimo ajuste) das classes da aba Inteligencia
artificial, um a um. A classe Acrescimo a licenca nao mudou na versao 3 e nao entra nesta amostra.
Executar a partir de Processado/:  python validacao_ia/julgamentos_ia_a3.py
Entrada: validacao_ia/fichas_ia_a3.csv (20 compras por classe, sem compras das amostras 1 e 2). Criterio: o mesmo de julgamentos_ia_a1.py.
Saida: validacao_ia/julgamentos_ia_a3.csv (ficha; id_compra; classe; pertinente; motivo)
"""
import csv

NAO = {
    14: "sistema de controle de ponto com treinamento de usuarios, nao capacitacao em IA",
    20: "assinatura de pesquisa juridica com modulo de IA (varios componentes)",
    22: "servicos integrados de conectividade via satelite, IA e mensageria (varios componentes)",
    25: "cluster de alto desempenho (equipamento)",
    26: "suporte tecnico de TI integrado a plataforma (servico mais amplo)",
    27: "plataforma Bitrix24 com modulos de WhatsApp e chatbot (varios componentes)",
    30: "projeto de pesquisa em nanocompositos otimizado por IA, nao compra de solucao de IA",
    38: "assinatura de plataforma de conhecimento e informacoes sobre IA, nao solucao de IA",
    42: "gravadores de voz com IA (equipamento)",
    43: "solucao de IA para auditoria (IA exclusiva), nao pacote",
    46: "licenciamento de assistente virtual (chatbot): IA exclusiva, nao pacote",
    48: "um unico software (Canva Pro), sem pacote de varios softwares",
    51: "atendimento por WhatsApp com chatbot: IA exclusiva, nao pacote",
    64: "atendimento por WhatsApp com chatbot: IA exclusiva, nao outros",
}
fichas = list(csv.DictReader(open("validacao_ia/fichas_ia_a3.csv", encoding="utf-8"), delimiter=";"))
assert len(fichas) == 80 and all(int(k) < len(fichas) for k in NAO)
with open("validacao_ia/julgamentos_ia_a3.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ficha", "id_compra", "classe", "pertinente", "motivo"])
    for r in fichas:
        k = int(r["ficha"])
        w.writerow([k, r["id_compra"], r["classe"], "não" if k in NAO else "sim", NAO.get(k, "")])
res = {}
for r in fichas:
    x = res.setdefault(r["classe"], [0, 0])
    x[0] += 1
    x[1] += int(r["ficha"]) not in NAO
for c, (n, p) in res.items():
    print(c, n, p, f"{100 * p / n:.0f}%")
