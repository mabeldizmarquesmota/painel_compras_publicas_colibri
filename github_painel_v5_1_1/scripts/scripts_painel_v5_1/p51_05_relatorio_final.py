"""Painel v5.1, etapa 5: relatorio final, conferencia final dos hashes da v1 a v5, congelamento da v5.1 e zip de envio.

Executar a partir de Processado/, depois de p51_04 e de p51_00 fim:  python scripts_painel_v5_1/p51_05_relatorio_final.py
Entradas: verificacao_html_v5_1/resultado_verificacao.json, grafico9_igual_grafico8.csv, grafico9_interacao.csv (p51_03);
  conferencia_numeros_v5_1.csv (p51_04); tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv (p51_01) e
  revisao_manual_ocorrencias.csv (p51_02); versao_congelada_v1 a v5/hashes_*.csv; scripts_painel_v5_1/_hashes_inicio.csv.
Regra: nenhum numero digitado; os hashes sao recalculados aqui e comparados com os registrados.
Saidas: relatorio_final_painel_v5_1.md; painel_v5_1_envio.zip (so o HTML e o pacote); versao_congelada_v5_1/ com hashes_sha256_v5_1.csv.
"""
import csv
import hashlib
import json
import os
import shutil
import sys
import zipfile

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "scripts_painel_v5_1")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v5_1.formatacao import inteiro, mi  # noqa: E402


def sha(c):
    h = hashlib.sha256()
    with open(c, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


ler = lambda c: list(csv.DictReader(open(c, encoding="utf-8-sig"), delimiter=";"))
HS = []
for versao, manifesto, bases in (("v1", "versao_congelada_v1/hashes_sha256_v1.csv", [""]), ("v2", "versao_congelada_v2/hashes_sha256_v2.csv", [""]),
                                  ("v3", "versao_congelada_v3/hashes_sha256_v3.csv", ["versao_congelada_v3/", ""]),
                                  ("v4", "versao_congelada_v4/hashes_sha256_v4.csv", ["versao_congelada_v4/", ""]),
                                  ("v5", "versao_congelada_v5/hashes_sha256_v5.csv", ["versao_congelada_v5/", ""])):
    reg = ler(manifesto)
    for base in bases:
        HS.append((versao, base or "Processado/", len(reg), sum(1 for r in reg if os.path.exists(base + r["arquivo"]) and sha(base + r["arquivo"]) == r["sha256"])))
ini = ler("scripts_painel_v5_1/_hashes_inicio.csv")
hs_ok = all(n == i for _, _, n, i in HS) and all(r["registrados"] == r["identicos"] for r in ini)

R = json.load(open("verificacao_html_v5_1/resultado_verificacao.json", encoding="utf-8"))
conf = ler("conferencia_numeros_v5_1.csv")
n_sim = sum(r["confere"] == "sim" for r in conf)
tg = [r for r in conf if r["texto_e_grafico"] != "não se aplica"]
lado = ler("verificacao_html_v5_1/grafico9_igual_grafico8.csv")
inter = ler("verificacao_html_v5_1/grafico9_interacao.csv")
oc = ler("tabelas_painel_v5_1/revisao_manual_ocorrencias.csv")
rec = ler("tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv")

with zipfile.ZipFile("painel_v5_1_envio.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write("painel_soberania_digital_v5_1.html")
    z.write("pacote_downloads_v5_1.zip")
H_HTML, H_PAC, H_ENV = sha("painel_soberania_digital_v5_1.html"), sha("pacote_downloads_v5_1.zip"), sha("painel_v5_1_envio.zip")
rodape = open("painel_soberania_digital_v5_1.html", encoding="utf-8").read().split("<footer>")[1].split("</footer>")[0]
sinal = lambda x: ("" if not str(x).startswith("-") else "− ") if x != "" else ""
num = lambda x, f: "" if x == "" else sinal(x) + f(abs(float(x)))

L = ["# Relatório final do painel, versão 5.1", "",
     "Feita a partir de uma cópia do HTML da versão 5 congelada. Nenhuma classificação foi refeita e nenhum número do painel mudou; a única tabela nova é a da reconciliação "
     "da aba de IA com a categoria Inteligência artificial.", "",
     "## 1. Revisão manual realizada pela pesquisadora responsável (Mabel Mota)", "",
     f"\"Revisão humana independente\" e variações foram trocadas em {sum(int(r['ocorrencias']) for r in oc if r['local'] != 'mantido')} ocorrências "
     "(tabelas_painel_v5_1/revisao_manual_ocorrencias.csv). No painel, todas estão na aba Metodologia ou nos textos de ícones \"i\" guardados nos dados embutidos; nenhuma ficava "
     "em texto visível das abas de dados.", "",
     "| Arquivo | Local | Trecho anterior | Trecho novo | Ocorrências |", "|---|---|---|---|---|"]
L += [f"| {r['arquivo']} | {r['local']} | {r['trecho_anterior']} | {r['trecho_novo']} | {r['ocorrencias']} |" for r in oc]
L += ["", "Mantidos sem mudança, por serem identificadores e não texto: o nome literal da coluna \"revisão humana\" em validacao_ia/exclusao_fundacoes_apoio.csv (citado na metodologia), "
      "nomes de arquivos e sementes (revisao_humana_ia.xlsx, f2_revisao_humana, ia_revisao_humana) e o código dos scripts das versões anteriores dentro do pacote. "
      "Os relatórios das versões 3 a 5 estão congelados e não foram alterados; este relatório já usa a forma nova.", "",
     "## 2. Rodapé", "", f"Rodapé: \"{rodape}\"", "",
     "## 3. Gráfico 9 com o componente do gráfico 8", "",
     "Botões em pílula com o mesmo estilo e a mesma posição (saiu o recuo antes de Capacitação); cursor de mão em nós e fluxos; clique em nó de fornecedor, de tipo de objeto "
     "e de órgão, em fluxo e na legenda filtra o gráfico e a tabela de baixo; um novo clique no mesmo elemento, ou no botão já ativo, desfaz a seleção. Para os dois gráficos "
     "ficarem iguais, o novo clique para desfazer também entrou no gráfico 8. Os botões da IA continuam: Todas, Acréscimo à licença, Solução de IA, Outros e Capacitação.",
     f"Teste lado a lado (verificacao_html_v5_1/grafico9_igual_grafico8.csv): {sum(r['igual'] == 'sim' for r in lado)} de {len(lado)} aspectos iguais, em 1440 px e 390 px "
     "(estilo dos botões inativo e ativo, espaçamento, posição, cursor, dicas ao passar o mouse, cliques em cada tipo de nó, fluxo, legenda e botão, e Limpar seleção). "
     f"Interação do gráfico 9 com a tabela: {sum(r['confere'] == 'sim' for r in inter)} de {len(inter)} ações com o total do gráfico igual ao da tabela.", "",
     "## 4. Aba de IA e categoria Inteligência artificial", "",
     "Entrou no \"i\" do gráfico 9: \"A aba de inteligência artificial não coincide com a categoria Inteligência artificial da aba de tecnologias críticas: exclui as compras de "
     "capacitação e inclui as compras de acréscimo de IA a licenças (Copilot, Gemini) classificadas em outras categorias. Por isso os totais diferem.\" A reconciliação está na "
     "metodologia (seção 9, \"Aba de IA e categoria Inteligência artificial\").", "",
     "Período completo, valores nominais, compras com vencedor identificado:", "",
     "| | Compras | Fornecedores | Órgãos | Valor |", "|---|---|---|---|---|"]
L += [f"| {r['linha'].strip()} | {num(r['compras'], inteiro)} | {num(r['fornecedores'], inteiro)} | {num(r['orgaos'], inteiro)} | {num(r['valor_nominal'], mi)} |" for r in rec]
L += ["", "Fornecedores e órgãos que saem são os que só aparecem nas compras de capacitação da categoria; os que entram só aparecem nas compras de acréscimo de outras categorias. "
      "Nas compras comuns, o valor é o mesmo nos dois gráficos.", "",
      "## 5. Conferências", "",
      f"- Navegador (Chromium sem internet, 1440 px e 390 px): {len(R['ok'])} verificações, {len(R['falhas'])} falhas; console sem erros; abas, filtros, alternador, sub-abas, cliques e \"i\" funcionando.",
      f"- conferencia_numeros_v5_1.csv: {len(conf)} linhas, {n_sim} \"sim\" ({100 * n_sim / len(conf):.0f}%); texto × gráfico: {sum(r['texto_e_grafico'] == 'sim' for r in tg)} de {len(tg)} \"sim\".",
      "- Alturas dos gráficos iguais às da v5; trechos excluídos na v5 continuam fora da tela.", "",
      "## Hashes", "", "| Versão | Local | Registrados | Idênticos no início | Idênticos no fim |", "|---|---|---|---|---|"]
for (v, loc, n, i), r in zip(HS, ini):
    L.append(f"| {v} | {loc} | {n} | {r['identicos']} | {i} |")
L += ["", f"v1 a v5 idênticas no início e no fim: {'sim' if hs_ok else 'NÃO'}. Nenhum script de versão anterior foi executado.", "",
      f"- painel_soberania_digital_v5_1.html: `{H_HTML}`", f"- pacote_downloads_v5_1.zip: `{H_PAC}`", f"- painel_v5_1_envio.zip (HTML e pacote): `{H_ENV}`",
      "- Lista completa da versão congelada: versao_congelada_v5_1/hashes_sha256_v5_1.csv.", ""]
open("relatorio_final_painel_v5_1.md", "w", encoding="utf-8").write("\n".join(L))

DEST = "versao_congelada_v5_1"
if os.path.exists(DEST):
    shutil.rmtree(DEST)
arquivos = ["painel_soberania_digital_v5_1.html", "METODOLOGIA_v5_1.md", "conferencia_numeros_v5_1.csv", "pacote_downloads_v5_1.zip", "painel_v5_1_envio.zip", "relatorio_final_painel_v5_1.md"]
for pasta in ("scripts_painel_v5_1", "tabelas_painel_v5_1", "verificacao_html_v5_1"):
    arquivos += sorted(os.path.join(pasta, x).replace("\\", "/") for x in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, x)))
linhas = []
for a in arquivos:
    os.makedirs(os.path.dirname(os.path.join(DEST, a)) or DEST, exist_ok=True)
    shutil.copy2(a, os.path.join(DEST, a))
    h_ = sha(a)
    assert sha(os.path.join(DEST, a)) == h_, a
    linhas.append([a, os.path.getsize(a), h_])
with open(os.path.join(DEST, "hashes_sha256_v5_1.csv"), "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["arquivo", "bytes", "sha256"])
    w.writerows(linhas)
print(f"hashes v1-v5 ok: {hs_ok}; v5.1 congelada com {len(linhas)} arquivos; conferência {n_sim}/{len(conf)}; navegador {len(R['ok'])} ok, {len(R['falhas'])} falhas")
sys.exit(0 if hs_ok and n_sim == len(conf) and not R["falhas"] and all(r["igual"] == "sim" for r in lado) else 1)
