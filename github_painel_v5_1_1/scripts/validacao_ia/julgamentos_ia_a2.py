"""Julgamentos da amostra 2 (semente ia_a2, dicionario versao 2) das classes da aba Inteligencia artificial, um a um.
Executar a partir de Processado/:  python validacao_ia/julgamentos_ia_a2.py
Entrada: validacao_ia/fichas_ia_a2.csv (20 compras por classe, sem compras da amostra 1). Criterio: o mesmo de julgamentos_ia_a1.py.
Saida: validacao_ia/julgamentos_ia_a2.csv (ficha; id_compra; classe; pertinente; motivo)
"""
import csv

NAO = {
    6: "curso com varios temas de gabinete; IA e um modulo entre muitos",
    22: "o item com Copilot e treinamento em Copilot e Power Platform, nao acrescimo a licenca",
    43: "relogio eletronico de ponto com reconhecimento facial (equipamento)",
    44: "software de gerenciamento de atendimentos com chatbot (varios componentes)",
    48: "plataforma WhatsApp Business com automacao, integracao e assistente virtual (varios componentes)",
    51: "software Articulate 360 e solucao Articulate AI (varios produtos)",
    53: "evento sobre IA (capacitacao)",
    55: "sustentacao e projetos de sistemas da area de IA (servico mais amplo)",
    56: "dispositivos de reconhecimento facial (equipamento)",
    57: "acao de capacitacao sobre redacao com auxilio de IA (capacitacao)",
    65: "servico de videomonitoramento (equipamento e servico de seguranca)",
    67: "plataforma para criacao de chatbot: IA exclusiva, nao pacote",
    72: "IA generativa com integracao ao WhatsApp: IA exclusiva, nao pacote",
    85: "sistema de informacao juridica com orientacoes e acesso a IA (varios componentes): pacote, nao outros",
    99: "solucao integrada em nuvem com e-mail, suite de escritorio e IA generativa: pacote, nao outros",
}
fichas = list(csv.DictReader(open("validacao_ia/fichas_ia_a2.csv", encoding="utf-8"), delimiter=";"))
assert len(fichas) == 100 and all(int(k) < len(fichas) for k in NAO)
with open("validacao_ia/julgamentos_ia_a2.csv", "w", encoding="utf-8", newline="") as fo:
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
