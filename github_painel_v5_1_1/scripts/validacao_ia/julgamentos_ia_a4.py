"""Julgamentos da amostra 4 (semente ia_a4) da classe somada 'Solucao de IA (exclusiva ou em pacote)', um a um.
A classe soma IA exclusiva e Pacote multi-software (dicionario versao 3, sem nova mudanca); a amostra nao repete compras das amostras 1 a 3.
Executar a partir de Processado/:  python validacao_ia/julgamentos_ia_a4.py
Criterio: pertinente quando a compra e de solucao de IA, so a IA ou a IA como componente de pacote de softwares ou servicos
  digitais (nuvem, suite, atendimento omnichannel, seguranca, sistema de gestao); nao pertinente quando e capacitacao,
  equipamento, servico mais amplo (desenvolvimento sob encomenda, suporte) ou quando nao ha IA na compra.
Saida: validacao_ia/julgamentos_ia_a4.csv (ficha; id_compra; classe; pertinente; motivo)
"""
import csv

NAO = {
    1: "palestra sobre ChatGPT e Direito (capacitacao)",
    9: "sistema de registro de ponto com reconhecimento facial e plataforma de RH (equipamento e sistema de gestao de pessoal)",
    13: "desenvolvimento de aplicativo sob encomenda com analise por IA (servico mais amplo)",
}
fichas = list(csv.DictReader(open("validacao_ia/fichas_ia_a4.csv", encoding="utf-8"), delimiter=";"))
assert len(fichas) == 20 and all(int(k) < len(fichas) for k in NAO)
with open("validacao_ia/julgamentos_ia_a4.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ficha", "id_compra", "classe", "pertinente", "motivo"])
    for r in fichas:
        k = int(r["ficha"])
        w.writerow([k, r["id_compra"], r["classe"], "não" if k in NAO else "sim", NAO.get(k, "")])
p = sum(int(r["ficha"]) not in NAO for r in fichas)
print(fichas[0]["classe"], len(fichas), p, f"{100 * p / len(fichas):.0f}%")
