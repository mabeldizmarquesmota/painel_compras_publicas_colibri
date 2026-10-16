"""Painel v4, etapa 5: relatorio final, conferencia final dos hashes da v1, v2 e v3, congelamento da v4 e zip de envio.

Executar a partir de Processado/, depois de p4_04:  python scripts_painel_v4/p4_05_relatorio_final.py
Entradas: verificacao_html_v4/resultado_verificacao.json, alturas_graficos.csv, textos_excluidos.csv, texto_grafico.csv (p4_03);
  conferencia_numeros_v4.csv (p4_04); tabelas_painel_v4/ia_achado4_*.csv (p4_01); versao_congelada_v1/2/3/hashes_*.csv.
Regra: nenhum numero digitado; os hashes sao recalculados aqui e comparados com os registrados.
Saidas: relatorio_final_painel_v4.md; painel_v4_envio.zip (so o HTML e o pacote); versao_congelada_v4/ com hashes_sha256_v4.csv.
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


def sha(c):
    h = hashlib.sha256()
    with open(c, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


ler = lambda c: list(csv.DictReader(open(c, encoding="utf-8-sig"), delimiter=";"))

# hashes das versoes congeladas (fim da v4)
HS = []
for versao, manifesto, bases in (("v1", "versao_congelada_v1/hashes_sha256_v1.csv", [""]), ("v2", "versao_congelada_v2/hashes_sha256_v2.csv", [""]),
                                  ("v3", "versao_congelada_v3/hashes_sha256_v3.csv", ["versao_congelada_v3/", ""])):
    reg = ler(manifesto)
    for base in bases:
        iguais = sum(1 for r in reg if os.path.exists(base + r["arquivo"]) and sha(base + r["arquivo"]) == r["sha256"])
        HS.append((versao, base or "Processado/", len(reg), iguais))
ini = ler("scripts_painel_v4/_hashes_inicio.csv")
hs_ok = all(n == i for _, _, n, i in HS) and all(r["registrados"] == r["identicos"] for r in ini)

R = json.load(open("verificacao_html_v4/resultado_verificacao.json", encoding="utf-8"))
conf = ler("conferencia_numeros_v4.csv")
n_sim = sum(r["confere"] == "sim" for r in conf)
tg = [r for r in conf if r["texto_e_grafico"] != "não se aplica"]
alt = ler("verificacao_html_v4/alturas_graficos.csv")
exc = ler("verificacao_html_v4/textos_excluidos.csv")
a4 = {r["definicao"].split(" ")[0]: r for r in ler("tabelas_painel_v4/ia_achado4_fornecedores.csv")}
rz = ler("tabelas_painel_v4/ia_achado4_raizes_com_mais_de_um_cnpj.csv")
emp = sorted({r["nome"] for r in rz})

# zip de envio
with zipfile.ZipFile("painel_v4_envio.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write("painel_soberania_digital_v4.html")
    z.write("pacote_downloads_v4.zip")
H_HTML, H_PAC, H_ENV = sha("painel_soberania_digital_v4.html"), sha("pacote_downloads_v4.zip"), sha("painel_v4_envio.zip")
pct = lambda x: f"{float(x):.1f}".replace(".", ",")

L = ["# Relatório final do painel, versão 4 (Ajuste 4)", "",
     "Versão de texto, ordem e layout, feita a partir de uma cópia do HTML da versão 3. Nenhuma classificação, dicionário, amostra ou revisão humana foi refeita; "
     "os números vêm das tabelas já existentes. A única conta nova é a do achado 4 da aba de IA.", "",
     "## O que mudou", "",
     "- **Compras públicas:** título laranja \"Compras públicas\" (sem o cabeçalho \"Panorama geral\"), caixa de abertura com o texto novo e um \"i\" no canto superior direito com a nota do valor homologado.",
     "- **Tecnologias críticas:** título laranja; abertura de uma frase com \"i\" (texto longo de soberania digital, com as citações); \"Tecnologias selecionadas:\" e seis cartões compactos numa linha (3 por linha abaixo de 1100 px, 2 abaixo de 600 px), cada \"i\" com Conceito, Palavras-chave e Verificação; "
     "divisor e Principais achados antes dos KPIs; divisores antes de \"O que o Estado compra?\" e \"Modalidade de contratação\"; Sankey passou a gráfico 8, cadeias a tabela 1, marcas a tabela 2; texto novo da margem de preferência e da nota de encomenda tecnológica (números e período seguem os dados e o filtro); gráfico 5 só com a primeira frase.",
     "- **Inteligência artificial:** título laranja, caixa de abertura nova, \"Principais achados das compras públicas de IA\" com o texto do item 4.2, Sankey como gráfico 9 com a tabela de cadeias no mesmo cartão (sem rótulo, título ou subtítulo, com o \"i\"), marcas de IA como tabela 3.",
     "- **Alturas:** " + "; ".join(f"{r['grafico']} {r['altura_v3_px']}→{r['altura_v4_px']} px (−{pct(r['reducao_pct'])}%)" for r in alt) + ". "
     "Nos Sankeys, o espaço entre nós passou de 9 para 14 px: com 9 px e a altura menor, rótulos de nós pequenos se sobrepunham; com 14 px não há sobreposição em nenhum filtro, modo ou largura.",
     "- **Numeração:** gráficos 1 a 9; tabelas 1 (cadeias), 2 (marcas), 3 (marcas de IA) e 4 (robustez, na metodologia). Referências cruzadas atualizadas nos \"i\", nas notas, na metodologia, no LEIAME e nos rótulos da conferência.",
     "- **Metodologia (METODOLOGIA_v4.md):** métodos de modelo de aquisição, tipo de vendedor, porte, concentração e margem por NCM mantidos, com registro de que os resultados estão no pacote e não são exibidos em gráfico; limitação do país de origem com a frase da caixa retirada; nova seção sobre o achado 4 da IA.",
     "- **Pacote (pacote_downloads_v4.zip):** todo o conteúdo do pacote v3, inclusive as tabelas dos gráficos e tabelas retirados, mais os scripts de scripts_painel_v4/, as tabelas de tabelas_painel_v4/ e METODOLOGIA_v4.md no lugar da v3.", "",
     "## O que foi excluído", "",
     "Notas fixas do valor homologado (as três abas; a da aba Compras foi para o \"i\"), selo de classificação automatizada, nota de classificação (tecnologias e IA), frase de abertura com 18.574 compras, frase \"Os achados se referem ao período completo...\", "
     "descrição e camada tecnológica dos cartões, gráficos de forma de contratação, modelo de aquisição e tipo de vendedor, indicadores de porte, tabelas de concentração e de perfil, texto abaixo dos dois Sankeys, cartão de margem por NCM, "
     "caixa \"Limitação da informação\" (texto levado à metodologia), segunda frase e frase do modo no gráfico 5, linha-resumo dos dois mercados e destaques da aba de IA.",
     f"Busca dos trechos excluídos ({len(exc)} trechos dos itens 2.1, 3.2, 3.3 e 4.1 e da numeração antiga): nenhum aparece no texto visível das abas (1440 px e 390 px), na marcação visível nem no código. "
     "Restam no arquivo só onde é esperado: a nota do valor homologado dentro do \"i\" da aba Compras (pedido no item 2.4), descrições de método na metodologia "
     "(\"Camada tecnológica\", \"Valor por modelo de aquisição\", \"Margem de preferência por NCM\" e \"539 fornecedores\", este na explicação do achado 4) e o texto do \"i\" da linha-resumo retirada, que fica nos dados embutidos e não é exibido "
     "(verificacao_html_v4/textos_excluidos.csv).", "",
     "## Achado 4 da IA: N", "",
     f"**N = {int(a4['CNPJ']['fornecedores']):,} fornecedores**".replace(",", ".") + f"; os 10 maiores ficaram com {pct(a4['CNPJ']['pct_10_maiores'])}% do valor homologado nos resultados (exibido: 72%, o mesmo da versão anterior). "
     f"Base: resultados da tecnologia de IA, sem capacitação, 2021 a 2026, valores nominais. O texto anterior dizia {a4['raiz']['fornecedores']} porque contava a raiz do CNPJ (8 dígitos); "
     f"a linha-resumo do Sankey conta o CNPJ completo do vencedor, a mesma definição usada nos KPIs de fornecedores da aba de tecnologias críticas. A diferença de {int(a4['CNPJ']['fornecedores']) - int(a4['raiz']['fornecedores'])} "
     f"vem de duas empresas que venceram com dois estabelecimentos: {' e '.join(e.title() for e in emp)}. O número correto para o painel é {a4['CNPJ']['fornecedores']}, igual à linha-resumo. "
     "Na raiz do CNPJ, a participação dos 10 maiores é a mesma (os dois CNPJs de cada empresa estão fora dos 10 maiores).", "",
     "## Conferências", "",
     f"- Navegador (Chromium sem internet, 1440 px e 390 px): {len(R['ok'])} verificações, {len(R['falhas'])} falhas; console sem erros nem avisos; abas, filtros, alternador, sub-abas, botões dos Sankeys e ícones \"i\" funcionando; "
     "ordem dos blocos conferida; sem rolagem horizontal; rótulos dos Sankeys sem sobreposição.",
     f"- conferencia_numeros_v4.csv: {len(conf)} linhas, {n_sim} \"sim\" ({100 * n_sim / len(conf):.0f}%); comparação texto e gráfico: {sum(r['texto_e_grafico'] == 'sim' for r in tg)} de {len(tg)} \"sim\". "
     "Inclui os textos novos comparados com o Ajuste 4 (margem com filtro 2025, nota de encomenda, gráfico 5 e os 4 achados da IA) e os Sankeys nos dois modos.",
     "- Capturas (verificacao_html_v4/): aba_compras_topo.png, aba_tecnologias_topo.png, aba_tecnologias_i_cartao_nuvem.png, aba_tecnologias_completa.png, aba_ia_completa.png.",
     "- Margem de preferência: com o filtro 2025, o texto exibido é idêntico ao do item 3.4. No recorte padrão (2021 a 2026), a frase começa por \"De 2021 a 2026\" e, como há valor com margem aplicada no período (R$ 12,5 milhões), "
     "informa esse valor em vez de \"Não foram identificados valores associados à margem aplicada\".", "",
     "## Hashes", "",
     "| Versão | Local | Registrados | Idênticos no início | Idênticos no fim |", "|---|---|---|---|---|"]
for (v, loc, n, i), r in zip(HS, ini):
    L.append(f"| {v} | {loc} | {n} | {r['identicos']} | {i} |")
L += ["", f"v1, v2 e v3 idênticas no início e no fim: {'sim' if hs_ok else 'NÃO'}. Nenhum script de scripts_painel_v3/ foi executado.", "",
      f"- painel_soberania_digital_v4.html: `{H_HTML}`", f"- pacote_downloads_v4.zip: `{H_PAC}`", f"- painel_v4_envio.zip (HTML e pacote): `{H_ENV}`",
      "- Lista completa da versão congelada: versao_congelada_v4/hashes_sha256_v4.csv.", ""]
open("relatorio_final_painel_v4.md", "w", encoding="utf-8").write("\n".join(L))

# congelamento
DEST = "versao_congelada_v4"
if os.path.exists(DEST):
    shutil.rmtree(DEST)
arquivos = ["painel_soberania_digital_v4.html", "METODOLOGIA_v4.md", "conferencia_numeros_v4.csv", "pacote_downloads_v4.zip", "painel_v4_envio.zip", "relatorio_final_painel_v4.md"]
for pasta in ("scripts_painel_v4", "tabelas_painel_v4", "verificacao_html_v4"):
    arquivos += sorted(os.path.join(pasta, x).replace("\\", "/") for x in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, x)))
linhas = []
for a in arquivos:
    os.makedirs(os.path.dirname(os.path.join(DEST, a)) or DEST, exist_ok=True)
    shutil.copy2(a, os.path.join(DEST, a))
    h_ = sha(a)
    assert sha(os.path.join(DEST, a)) == h_, a
    linhas.append([a, os.path.getsize(a), h_])
with open(os.path.join(DEST, "hashes_sha256_v4.csv"), "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["arquivo", "bytes", "sha256"])
    w.writerows(linhas)
print(f"hashes v1-v3 ok: {hs_ok}; v4 congelada com {len(linhas)} arquivos; conferência {n_sim}/{len(conf)}; navegador {len(R['ok'])} ok, {len(R['falhas'])} falhas")
sys.exit(0 if hs_ok and n_sim == len(conf) and not R["falhas"] else 1)
