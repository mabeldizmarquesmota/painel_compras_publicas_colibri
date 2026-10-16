"""Julgamentos da amostra 1 (semente ia_a1) das classes da aba Inteligencia artificial, feitos um a um.
Executar a partir de Processado/:  python validacao_ia/julgamentos_ia_a1.py
Entrada: validacao_ia/fichas_ia_a1.csv (20 compras por classe; numero da ficha = ordem da linha).
Criterio (o mesmo da instrucao da revisao humana):
  Capacitacao: curso, treinamento, inscricao, pos-graduacao ou evento cujo tema e IA.
  Acrescimo a licenca: assistente de IA acoplado a licenca de software ja usada (Copilot para Microsoft 365, Gemini
    para Workspace); produto de IA vendido a parte (Copilot Studio sozinho, assinatura de ChatGPT, Gemini e Claude) nao e.
  IA exclusiva: o objeto e so a solucao de IA (plataforma, modelo, API, assistente ou chatbot de IA, licencas de IA).
  Pacote multi-software: a IA e um componente entre varios softwares ou servicos digitais (nuvem, suite, atendimento
    omnichannel, seguranca, sistema de gestao).
  Outros: nenhuma das classes anteriores se aplica (equipamento com IA embarcada, compra mais ampla, outros objetos).
Saida: validacao_ia/julgamentos_ia_a1.csv (ficha; id_compra; classe; pertinente; motivo)
"""
import csv

NAO = {  # ficha -> motivo (as demais fichas sao pertinentes)
    11: "evento de gestao de pessoas; o motivo principal foi um painel sobre felicidade corporativa, nao IA",
    25: "so Copilot Studio, produto vendido a parte, sem acrescimo a licenca existente",
    31: "assinaturas de ChatGPT, Gemini e Claude: IA exclusiva, nao acrescimo a licenca",
    36: "so Copilot Studio (educacao), produto vendido a parte",
    40: "sistema de controle de acesso (equipamento) com reconhecimento facial",
    41: "servicos tecnicos de apoio a supervisao de modelos, nao so a solucao de IA",
    42: "formacao de professores em IA (capacitacao)",
    44: "seguranca eletronica com IA (servico mais amplo)",
    45: "projeto com solucoes digitais, IA, ciencia de dados e geoprocessamento (varios componentes)",
    47: "controladores de acesso com reconhecimento facial (equipamento)",
    48: "aplicativo multiplataforma e chatbot (varios componentes)",
    49: "API de dados juridicos publicos, nao solucao de IA",
    50: "solucao de videoconferencia (equipamento) com recursos de IA",
    53: "terminal com reconhecimento facial (equipamento)",
    55: "formacao de profissionais da educacao em IA (capacitacao)",
    58: "assinatura de ecossistema de ensino de IA (capacitacao)",
    59: "workshop sobre IA (capacitacao)",
    62: "solucao de reconhecimento facial e analise de imagens: IA exclusiva, nao pacote",
    66: "sistema de frequencia com registrador fisico (equipamento), sem varios softwares",
    76: "um unico software (Canva Pro), sem pacote de varios softwares",
}
fichas = list(csv.DictReader(open("validacao_ia/fichas_ia_a1.csv", encoding="utf-8"), delimiter=";"))
assert len(fichas) == 100 and all(int(k) < len(fichas) for k in NAO)
with open("validacao_ia/julgamentos_ia_a1.csv", "w", encoding="utf-8", newline="") as fo:
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
