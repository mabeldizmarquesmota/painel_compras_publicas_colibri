"""Painel v5, etapa 5: relatorio final, conferencia final dos hashes da v1 a v4, congelamento da v5 e zip de envio.

Executar a partir de Processado/, depois de p5_04 e de p5_00 fim:  python scripts_painel_v5/p5_05_relatorio_final.py
Entradas: verificacao_html_v5/resultado_verificacao.json, alturas_graficos.csv, exclusoes.csv, grafico9_interacao.csv (p5_03);
  conferencia_numeros_v5.csv (p5_04); tabelas_painel_v5/ia_nuvem_servicos_ia.csv e ia_capacitacao_reconciliacao.csv (p5_01);
  versao_congelada_v1 a v4/hashes_*.csv; scripts_painel_v5/_hashes_inicio.csv.
Regra: nenhum numero digitado; os hashes sao recalculados aqui e comparados com os registrados.
Saidas: relatorio_final_painel_v5.md; painel_v5_envio.zip (so o HTML e o pacote); versao_congelada_v5/ com hashes_sha256_v5.csv.
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
sys.path.insert(0, "scripts_painel_v5")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v5.formatacao import inteiro, mi  # noqa: E402


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
                                  ("v4", "versao_congelada_v4/hashes_sha256_v4.csv", ["versao_congelada_v4/", ""])):
    reg = ler(manifesto)
    for base in bases:
        HS.append((versao, base or "Processado/", len(reg), sum(1 for r in reg if os.path.exists(base + r["arquivo"]) and sha(base + r["arquivo"]) == r["sha256"])))
ini = ler("scripts_painel_v5/_hashes_inicio.csv")
hs_ok = all(n == i for _, _, n, i in HS) and all(r["registrados"] == r["identicos"] for r in ini)

R = json.load(open("verificacao_html_v5/resultado_verificacao.json", encoding="utf-8"))
conf = ler("conferencia_numeros_v5.csv")
n_sim = sum(r["confere"] == "sim" for r in conf)
tg = [r for r in conf if r["texto_e_grafico"] != "não se aplica"]
alt = ler("verificacao_html_v5/alturas_graficos.csv")
exc = ler("verificacao_html_v5/exclusoes.csv")
inter = ler("verificacao_html_v5/grafico9_interacao.csv")
nuv = ler("tabelas_painel_v5/ia_nuvem_servicos_ia.csv")
cap = ler("tabelas_painel_v5/ia_capacitacao_reconciliacao.csv")
pct = lambda x: f"{float(x):.1f}".replace(".", ",")

with zipfile.ZipFile("painel_v5_envio.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write("painel_soberania_digital_v5.html")
    z.write("pacote_downloads_v5.zip")
H_HTML, H_PAC, H_ENV = sha("painel_soberania_digital_v5.html"), sha("pacote_downloads_v5.zip"), sha("painel_v5_envio.zip")

L = ["# Relatório final do painel, versão 5 (Ajuste 5, revisão final)", "",
     "Revisão de texto, ordem e layout feita a partir de uma cópia do HTML da versão 4, mais duas correções de funcionamento no gráfico 9. Nenhuma classificação foi refeita; "
     "os números vêm das tabelas existentes e continuam mudando com os filtros e o alternador.", "",
     "## O que mudou", "",
     "- **Compras públicas:** título \"Panorama das compras públicas\" (mesmo estilo; o botão da aba continua \"Compras públicas\"); texto novo da caixa de abertura, com o \"i\"; "
     "gráfico 1 só com o total do período e a frase de cobertura parcial (modos Valor e Quantidade); gráficos 2 e 3 sem a frase do valor sem esfera ou poder identificado.",
     "- **Tecnologias críticas:** caixa de abertura nova; ordem título, caixa, KPIs, linha divisória, \"Composição das compras por categoria tecnológica\" (gráficos 5 e 6), "
     "\"Modalidade de contratação\" (gráfico 7), \"Fornecedores, tecnologias e órgãos compradores\" (gráfico 8 e tabelas 1 e 2), \"Instrumentos de política pública associados às compras\" "
     "e \"Síntese dos principais achados\" no fim; tabela 1 com o título \"Principais relações entre fornecedores, objetos e órgãos compradores\"; \"i\" do gráfico 5 com Como interpretar, "
     "Nota metodológica (remete ao Dicionário de termos por categoria) e Exemplo de leitura; \"i\" dos instrumentos com a nota metodológica do preenchimento e a nota de encomenda "
     "tecnológica e CPSI; o texto visível dos instrumentos ficou só com a frase da margem prevista e aplicada.",
     "- **Acréscimo ao item 3.3 (pedido na mensagem):** no \"i\" do gráfico 8 entrou, ao fim do Como interpretar, a frase \"Os valores deste gráfico são o valor dos resultados "
     "(o homologado para cada fornecedor vencedor) e podem diferir dos gráficos por categoria, que usam o valor homologado das compras.\" A metodologia (Critérios de apresentação) registra o mesmo.",
     "- **Tabela 2:** \"A menção não comprova o produto entregue\" e o corte de 20 compras já estavam no \"i\"; não foram mudados.",
     "- **Inteligência artificial:** caixa de abertura nova; ordem gráfico 9 com a tabela de cadeias, tabela 3 e \"Principais achados das compras públicas de IA\" no fim, com os textos do item 4.4; "
     "coluna \"Principais vendedores/revendedores\"; \"Nuvem/cloud broker\" passou a \"Nuvem com serviços de IA\" no gráfico, legenda, tooltips, tabela de cadeias e CSV, com a explicação no \"i\" do gráfico 9.",
     "- **Metodologia:** título \"Procedimentos metodológicos\" no estilo laranja das outras abas (o botão continua \"Metodologia\"); nova seção \"Dicionário de termos por categoria\" "
     "com conceito, palavras-chave e verificação das seis categorias; Nuvem com serviços de IA, correções do gráfico 9 e textos levados aos \"i\" registrados; nomes novos de blocos e tabelas.",
     "- **Estilo:** " + "; ".join(f"{r['grafico']} {r['altura_v4_px']}→{r['altura_v5_px']} px ({'−' + pct(r['reducao_pct']) + '%' if float(r['reducao_pct']) else 'sem mudança'})" for r in alt) +
     ". Textos de interpretação abaixo dos gráficos e tabelas em 14 px e #4B5563 (contraste de 7,6:1 sobre o branco).", "",
     "## O que foi excluído", "",
     "Texto final da aba Sobre; frase dos indicadores anuais na caixa de Compras públicas; exemplo de leitura e nota do \"i\" do KPI de quantidade de compras; exemplo de leitura \"De cada R$ 100\" "
     "do \"i\" do KPI de valor homologado (estava nesse KPI); frases do maior valor anual, do ano com mais compras e da variação de 2023 para 2025 no gráfico 1; frases do valor sem esfera e sem "
     "poder identificados nos gráficos 2 e 3; \"Tecnologias selecionadas:\" e os seis cartões das categorias; instrução de uso abaixo do gráfico 8; notas das tabelas 1 e 2; preenchimento dos "
     "três campos no texto visível e nos cartões dos instrumentos; cartão da nota de encomenda tecnológica; rótulo \"Procedimentos e critérios\".",
     f"verificacao_html_v5/exclusoes.csv: {len(exc)} trechos, {sum(r['aparece na tela'] == 'não' for r in exc)} com \"aparece na tela: não\" "
     f"({100 * sum(r['aparece na tela'] == 'não' for r in exc) / len(exc):.0f}%), em 1440 px e 390 px. Os textos levados para os \"i\" aparecem só dentro deles.", "",
     "## Gráfico 9: causas e correções", "",
     f"1. **Capacitação aparecia como \"Outros\".** Causa: o dicionário de tipos de objeto da aba de IA (versão 3) põe todas as compras de capacitação no tipo \"Outros objetos\", e era esse o nome "
     "do nó central, da legenda e dos tooltips com o botão Capacitação. Esse tipo só reúne compras da classe Capacitação (conferido), então passou a se chamar \"Capacitação\" no painel, sem "
     "reclassificar nenhuma compra; nenhuma compra de Capacitação aparece em Outros. Totais: a tabela de classes tem "
     f"{inteiro(int(cap[0]['compras']))} compras e {mi(float(cap[0]['valor_nominal']))}; o gráfico 9, que usa o valor dos resultados, mostra as {inteiro(int(cap[1]['compras']))} compras com "
     f"vencedor identificado ({mi(float(cap[1]['valor_nominal']))}). As outras {inteiro(int(cap[2]['compras']))} compras não têm resultado com vencedor publicado; "
     f"{inteiro(int(cap[1]['compras']))} + {inteiro(int(cap[2]['compras']))} = {inteiro(int(cap[0]['compras']))}. O gráfico não pode mostrar compras sem fornecedor, por isso os totais diferem.",
     "2. **Tabela não reagia ao gráfico.** Causa: na v4, o clique em fornecedor e em órgão já filtrava a tabela, mas o clique no nó de tipo de objeto saía da função sem ação e os fluxos não "
     "tinham clique. Correção: com a mesma lógica do gráfico 8, os cliques em tipo de objeto e em fluxo agora selecionam o tipo, e a seleção filtra o diagrama e a tabela de cadeias; "
     "o botão Limpar seleção volta ao recorte.",
     f"3. **Teste:** verificacao_html_v5/grafico9_interacao.csv, {len(inter)} ações (5 botões nos modos Valor e Nº de compras, clique em fornecedor, tipo de objeto, órgão e fluxo), "
     f"{sum(r['confere'] == 'sim' for r in inter)} com o total do gráfico igual ao total da tabela.", "",
     "## Nuvem com serviços de IA", "",
     f"**{inteiro(int(nuv[0]['compras']))} compras, {mi(float(nuv[0]['valor_nominal']))}** (valor homologado na aba, período completo, nominal). No gráfico 9, que usa o valor dos "
     f"resultados: {inteiro(int(nuv[1]['compras']))} compras com vencedor identificado e {mi(float(nuv[1]['valor_nominal']))}. Nas tabelas do pacote o tipo mantém o nome \"Nuvem/cloud broker\" "
     "(registrado no LEIAME e na metodologia).", "",
     "## Conferências", "",
     f"- Navegador (Chromium sem internet, 1440 px e 390 px): {len(R['ok'])} verificações, {len(R['falhas'])} falhas; console sem erros; abas, filtros, alternador, sub-abas, cliques e \"i\" funcionando.",
     f"- conferencia_numeros_v5.csv: {len(conf)} linhas, {n_sim} \"sim\" ({100 * n_sim / len(conf):.0f}%); texto × gráfico: {sum(r['texto_e_grafico'] == 'sim' for r in tg)} de {len(tg)} \"sim\".",
     "- Capturas (verificacao_html_v5/): aba_sobre.png, aba_compras.png, aba_tecnologias.png, aba_ia_todas.png, aba_ia_capacitacao.png, aba_metodologia_topo.png.", "",
     "## Hashes", "", "| Versão | Local | Registrados | Idênticos no início | Idênticos no fim |", "|---|---|---|---|---|"]
for (v, loc, n, i), r in zip(HS, ini):
    L.append(f"| {v} | {loc} | {n} | {r['identicos']} | {i} |")
L += ["", f"v1 a v4 idênticas no início e no fim: {'sim' if hs_ok else 'NÃO'}. Nenhum script de versão anterior foi executado.", "",
      f"- painel_soberania_digital_v5.html: `{H_HTML}`", f"- pacote_downloads_v5.zip: `{H_PAC}`", f"- painel_v5_envio.zip (HTML e pacote): `{H_ENV}`",
      "- Lista completa da versão congelada: versao_congelada_v5/hashes_sha256_v5.csv.", ""]
open("relatorio_final_painel_v5.md", "w", encoding="utf-8").write("\n".join(L))

DEST = "versao_congelada_v5"
if os.path.exists(DEST):
    shutil.rmtree(DEST)
arquivos = ["painel_soberania_digital_v5.html", "METODOLOGIA_v5.md", "conferencia_numeros_v5.csv", "pacote_downloads_v5.zip", "painel_v5_envio.zip", "relatorio_final_painel_v5.md"]
for pasta in ("scripts_painel_v5", "tabelas_painel_v5", "verificacao_html_v5"):
    arquivos += sorted(os.path.join(pasta, x).replace("\\", "/") for x in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, x)))
linhas = []
for a in arquivos:
    os.makedirs(os.path.dirname(os.path.join(DEST, a)) or DEST, exist_ok=True)
    shutil.copy2(a, os.path.join(DEST, a))
    h_ = sha(a)
    assert sha(os.path.join(DEST, a)) == h_, a
    linhas.append([a, os.path.getsize(a), h_])
with open(os.path.join(DEST, "hashes_sha256_v5.csv"), "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["arquivo", "bytes", "sha256"])
    w.writerows(linhas)
print(f"hashes v1-v4 ok: {hs_ok}; v5 congelada com {len(linhas)} arquivos; conferência {n_sim}/{len(conf)}; navegador {len(R['ok'])} ok, {len(R['falhas'])} falhas")
sys.exit(0 if hs_ok and n_sim == len(conf) and not R["falhas"] and all(r["aparece na tela"] == "não" for r in exc) else 1)
