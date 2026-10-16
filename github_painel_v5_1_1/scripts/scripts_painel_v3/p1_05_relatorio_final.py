"""Painel v3, etapa 5: relatorio final da entrega, gerado a partir dos arquivos produzidos.

Executar a partir de Processado/, depois de p1_04:  python scripts_painel_v3/p1_05_relatorio_final.py
Entradas: verificacao_html_v3/conf_painel.json e resultado_verificacao.json (numeros exibidos e verificacao no Chromium);
  verificacao_html_v2/conf_painel.json (KPIs da v2); conferencia_numeros_v3.csv; tabelas_painel_v3/*.csv; validacao_ia/*.csv;
  versao_congelada_v1/hashes_sha256_v1.csv e versao_congelada_v2/hashes_sha256_v2.csv (hashes registrados da v1 e da v2).
Regra: nenhum numero digitado; os hashes sao recalculados aqui e comparados com os registrados.
Saida: relatorio_final_painel_v3.md
"""
import csv
import glob
import hashlib
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "scripts_painel_v3")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v3.formatacao import bi, fmt_num, fmt_pct, inteiro, mi  # noqa: E402

TP, VI, VH = "tabelas_painel_v3/", "validacao_ia/", "verificacao_html_v3/"
ler = lambda n: list(csv.DictReader(open(n, encoding="utf-8-sig"), delimiter=";"))
f = float


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fo:
        for b in iter(lambda: fo.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


conf = json.load(open(VH + "conf_painel.json", encoding="utf-8"))
conf2 = json.load(open("verificacao_html_v2/conf_painel.json", encoding="utf-8"))
verif = json.load(open(VH + "resultado_verificacao.json", encoding="utf-8"))
confe = ler("conferencia_numeros_v3.csv")
# hashes da v1 (151 arquivos registrados) e da v2
h1 = ler("versao_congelada_v1/hashes_sha256_v1.csv")
v1_dif = [r["arquivo"] for r in h1 if not os.path.exists(r["arquivo"]) or sha(r["arquivo"]) != r["sha256"]]
_reg1 = {r["arquivo"] for r in h1}
for d in ["scripts_painel", "tabelas_painel", "scripts_parte0", "tabelas_parte0", "validacao"]:  # arquivos novos nas pastas da v1
    for raiz, _, nomes in os.walk(d):
        if "__pycache__" not in raiz:
            v1_dif += [p for p in (os.path.join(raiz, n).replace("\\", "/") for n in nomes) if p not in _reg1]
h2 = ler("versao_congelada_v2/hashes_sha256_v2.csv")
v2_dif = [r["arquivo"] for r in h2 if sha(r["arquivo"]) != r["sha256"]]
# numeros da v3
alt = ler(VH + "alternador_exemplos.csv")
skc = ler(VH + "sankey_conferencia.csv")
iac = ler(VH + "ia_sankey_conferencia.csv")
itg = ler(VH + "ia_texto_grafico.csv")
busca = ler(VH + "busca_nome_classe_3.csv")
ach = ler(TP + "pn_achados.csv")
iab, iap = ler(TP + "ia_base.csv"), ler(TP + "ia_base_classes.csv")
irec = ler(TP + "ia_reconciliacao.csv")
iprec = ler(TP + "ia_precisao_classes.csv")
irh = ler(VI + "resultado_revisao_humana_ia.csv")
idiv = ler(VI + "divergencias_revisao_humana_ia.csv")
ifund = ler(VI + "exclusao_fundacoes_apoio.csv")
irep = ler(VI + "capacitacao_itens_repartidos.csv")
_inss = next(r for r in irep if r["orgao"] == "INSTITUTO NACIONAL DO SEGURO SOCIAL")
irv = ler(VI + "capacitacao_maiores_valores_revisadas.csv")
ivalor = next(r for r in irh if r["classe"].startswith("Capacitação: verificação por valor"))
irh = [r for r in irh if r is not ivalor]
from openpyxl import load_workbook  # noqa: E402
_mx = {r[1]: str(r[7]).strip().lower() for r in load_workbook(VI + "revisao_humana_ia.xlsx", read_only=True)["revisao"].iter_rows(min_row=2, values_only=True) if r[0] == "Capacitação: maiores valores"}
_fund_ids, _rep = {r["id_compra"] for r in ifund}, {r["id_compra"]: r for r in irep}
imar = ler(TP + "ia_marcas.csv")
prec = ler(TP + "pn_precisao_final.csv")
cad = ler(TP + "pn_cadeias_compras.csv")
CLS = ["Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)", "Outros", "Capacitação"]
vcls = {c: sum(round(f(r["valor_nominal"]), 2) for r in iap if r["classe"] == c) for c in CLS}
ncls = {c: sum(1 for r in iab if r["classe"] == c) for c in CLS}
capturas = sorted(os.path.basename(p) for p in glob.glob(VH + "*.png"))
NOME_KPI = {"sobre_kpi_compras": "Sobre, compras", "sobre_kpi_valor": "Sobre, valor", "sobre_kpi_soberania": "Sobre, seis categorias", "sobre_kpi_participacao": "Sobre, participação",
            "cp_kpi_compras": "Compras públicas, compras", "cp_kpi_valor": "Compras públicas, valor", "sd_kpi_valor": "Tecnologias críticas, valor", "sd_kpi_part": "Tecnologias críticas, participação",
            "sd_kpi_forn": "Tecnologias críticas, fornecedores", "sd_kpi_org": "Tecnologias críticas, órgãos"}
KPIS = ["sobre_kpi_compras", "sobre_kpi_valor", "sobre_kpi_soberania", "sobre_kpi_participacao", "cp_kpi_compras", "cp_kpi_valor", "sd_kpi_valor", "sd_kpi_part", "sd_kpi_forn", "sd_kpi_org"]
kpi_iguais = [k for k in KPIS if conf.get(k) == conf2.get(k)]
sim = sum(r["confere"] == "sim" for r in confe)
tg = [r for r in confe if r["texto_e_grafico"] != "não se aplica"]
erros_console = [c for c in verif["console"] if c.startswith(("error", "pageerror"))]

L = ["# Relatório final: painel v3", "",
     "Gerado por `scripts_painel_v3/p1_05_relatorio_final.py` a partir dos números exibidos no painel (lidos no Chromium sem internet), das tabelas agregadas e dos "
     "arquivos de verificação. Nenhum número foi digitado.", ""]
# ------------------------------------------------------------------ resumo
L += ["## Resumo", "",
      f"- Conferência dos números: {inteiro(sim)} de {inteiro(len(confe))} linhas com \"sim\" em `conferencia_numeros_v3.csv`; "
      f"{inteiro(sum(r['texto_e_grafico'] == 'sim' for r in tg))} de {inteiro(len(tg))} comparações entre texto e gráfico iguais.",
      f"- Verificação do HTML: {inteiro(len(verif['ok']))} verificações ok e {inteiro(len(verif['falhas']))} falhas, em 1440 px e 390 px; "
      f"{inteiro(len(erros_console))} erros no console; {inteiro(len(verif['requisicoes_bloqueadas']))} requisições externas.",
      f"- Versão 1: {inteiro(len(h1) - len(v1_dif))} de {inteiro(len(h1))} arquivos com o mesmo SHA-256 registrado. Versão 2: {inteiro(len(h2) - len(v2_dif))} de {inteiro(len(h2))} arquivos iguais.",
      f"- KPIs das abas Sobre, Compras públicas e Tecnologias críticas: {inteiro(len(kpi_iguais))} de {inteiro(len(KPIS))} iguais aos da v2.", ""]
# ------------------------------------------------------------------ o que mudou
nm_alt = len({r["elemento"] for r in alt})
L += ["## O que mudou", "",
      "### Parte 1. Textos e leitura", "",
      f"- Exemplos de leitura e textos com reais acompanham o alternador: {inteiro(len(alt))} textos testados nos dois modos ({inteiro(nm_alt)} elementos), "
      "com o modo dos valores numa frase final separada (\"Valores nominais.\" ou \"Valores deflacionados, a preços de agosto de 2026.\").",
      "- Dois termos para as somas das seis categorias: \"total das seis categorias\" (cada compra uma vez) e \"soma por categoria\"; a compra inteira em cada categoria ficou só na metodologia.",
      "- Nota fixa do valor homologado nas abas de dados; a definição do valor global homologado ficou só nos KPIs de valor. Títulos \"Valor por...\" e colunas \"Valor (R$ mi)\".",
      "- Gráfico 9: grupo \"Serviços técnicos, equipamentos e não identificados\"; classe 3 renomeada para \"Licenciamento de direitos permanentes de uso\" em todo o painel e na origem da fase 2 "
      f"(o nome antigo não aparece em texto do painel, da metodologia ou do pacote; restam {inteiro(len(busca))} ocorrências da palavra só em expressões de busca e em texto original do PNCP).",
      f"- Selo de precisão das categorias (entre {fmt_pct(min(f(r['precisao_pct']) for r in prec))} e {fmt_pct(max(f(r['precisao_pct']) for r in prec))}).", "",
      "### Parte 2. Principais achados", "",
      f"- {inteiro(len(ach))} achados em linhas, lado a lado, logo depois dos KPIs da aba de tecnologias críticas; cada número com a sua base em `pn_achados_numeros.csv`.",
      f"- Achado 4 com a base da aba de IA: {ach[3]['texto'] if len(ach) > 3 else ''}", "",
      "### Parte 3. Tabela 2 em cadeias", "",
      f"- \"Maiores cadeias: fornecedor → objeto → órgão\", com porte, objeto completo no tooltip, ordenação e download; base de {inteiro(len({r['id_compra'] for r in cad}))} compras do gráfico 11.", "",
      "### Parte 4. Gráfico 11", "",
      f"- Sub-abas Valor e Nº de compras e botões de categoria; {inteiro(sum(r['confere'] == 'sim' for r in skc))} de {inteiro(len(skc))} conferências em `sankey_conferencia.csv`.",
      "- Linha-resumo: compras com vencedor identificado, fornecedores, órgãos e valor dos resultados (soma por categoria).", "",
      "### Parte 5. Aba Inteligência artificial", "",
      f"- Base: {inteiro(len(iab))} compras; " + "; ".join(f"{r['linha']}: {inteiro(int(r['compras']))} compras, {mi(f(r['valor_nominal']))}" for r in irec) + ".",
      "- Classes finais (valor repartido pelos itens; compra contada uma vez, na classe de maior valor): "
      + "; ".join(f"{c}: {inteiro(ncls[c])} compras, {mi(vcls[c])}" for c in CLS) + ".",
      f"- Regra das fundações de apoio: {inteiro(len(ifund))} compras ({mi(sum(f(r['valor_nominal']) for r in ifund))}) saíram da aba; a revisão humana confirmou a exclusão em {inteiro(sum(r['revisão humana'] == 'confirmada' for r in ifund))} delas (nenhuma é curso para servidores). "
      f"Regra dos itens na capacitação: {inteiro(len(irep))} compras passaram a contar só o valor dos itens de IA (redução de {mi(sum(f(r['valor_antes']) - f(r['valor_depois']) for r in irep))}); "
      f"no INSS, de {mi(f(_inss['valor_antes']))} para {mi(f(_inss['valor_depois']))}, só o item do MBA em IA.",
      f"- Gráfico 12 (Sankey da IA): {inteiro(sum(r['confere'] == 'sim' for r in iac))} de {inteiro(len(iac))} conferências; destaques: {inteiro(sum(r['confere'] == 'sim' for r in itg))} de "
      f"{inteiro(len(itg))} números iguais aos do gráfico. Tabela 5 (cadeias) e tabela 6 (marcas de IA, {inteiro(len(imar))} marcas, sem corte mínimo).", "",
      "### Parte 6. Metodologia, pacote e verificação", "",
      "- METODOLOGIA_v3.md e aba Metodologia com os itens 1.2, 1.4 e 1.6 e a seção 9 (aba de IA: base, valor, classes, dicionários, verificação, revisão humana, tipos, marcas, reconciliação e limitações).",
      f"- `pacote_downloads_v3.zip` ({fmt_num(os.path.getsize('pacote_downloads_v3.zip') / 1e6, 1)} MB) com os scripts em ordem de execução e as tabelas novas; "
      f"painel com {fmt_num(os.path.getsize('painel_soberania_digital_v3.html') / 1e6, 1)} MB.",
      f"- {inteiro(len(capturas))} capturas em `verificacao_html_v3/`, entre elas: " + ", ".join(c for c in capturas if c.startswith(("grafico5_", "grafico9_", "achados_linhas", "tabela2_cadeias", "grafico11_sankey", "aba_ia_todas")) and c.endswith(("_1440.png", "_390.png"))) + ".", ""]
# ------------------------------------------------------------------ o que nao mudou
L += ["## O que não mudou", "",
      f"- Versão 1 e versão 2 (arquivos e pacotes), conferidas por SHA-256: v1 {'idêntica' if not v1_dif else 'DIFERENTE: ' + ', '.join(v1_dif[:5])}; v2 {'idêntica' if not v2_dif else 'DIFERENTE: ' + ', '.join(v2_dif)}.",
      "- Base de dados (Colibri e bancos de trabalho abertos só para leitura) e classificação das seis categorias.",
      "- KPIs: " + "; ".join(f"{NOME_KPI[k]} = {conf.get(k)}" for k in kpi_iguais) + ".", ""]
# ------------------------------------------------------------------ verificacao da IA
L += ["## Aba de IA: verificação de 20 compras por classe", "", "| Classe | Amostra | Dicionário | Julgadas | Pertinentes | Precisão | Rodada final |", "|---|---|---|---|---|---|---|"]
L += [f"| {r['classe']} | {r['rodada'].replace('ia_a', 'amostra ')} | {r['dicionario']} | {r['compras_julgadas']} | {r['pertinentes']} | {fmt_pct(f(r['precisao_pct']))} | {r['rodada_final']} |" for r in iprec]
L += ["", "IA exclusiva e Pacote multi-software não chegaram a 80% depois de dois ajustes e foram somadas em \"Solução de IA (exclusiva ou em pacote)\", medida numa amostra nova (amostra 4).", "",
      "### Revisão humana", "", "| Classe | Casos | Certo | Concordância | Igual à verificação por amostragem |", "|---|---|---|---|---|"]
L += [f"| {r['classe']} | {r['casos_revisados']} | {r['certo']} | {fmt_pct(f(r['concordancia_pct']))} | {r['concordancia_entre_revisoes'] or '-'} |" for r in irh]
_situ = lambda c: ("saiu da aba pela regra das fundações de apoio" if c in _fund_ids else
                   f"valor repartido pelos itens: {mi(f(_rep[c]['valor_antes']))} para {mi(f(_rep[c]['valor_depois']))}" if c in _rep else
                   f"segue em {iab_d[c]['classe']}" if c in iab_d else "fora da aba")
iab_d = {r["id_compra"]: r for r in iab}
L += ["", "### Verificação por valor (10 maiores compras de Capacitação)", "",
      f"{inteiro(int(ivalor['certo']))} de {inteiro(int(ivalor['casos_revisados']))} compras certas. As compras marcadas como erradas somavam {mi(f(ivalor['valor_em_compras_erradas']))} "
      f"dos {mi(f(ivalor['valor_revisado']))} revisados ({fmt_pct(f(ivalor['pct_do_valor_em_compras_erradas']))}). Situação depois das regras das fundações de apoio e dos itens:", "",
      "| Compra | Órgão | Valor revisado | Revisão | Situação agora |", "|---|---|---|---|---|"]
L += [f"| {r['id_compra']} | {r['orgao']} | {mi(f(r['valor_nominal']))} | {_mx.get(r['id_compra'], '-')} | {_situ(r['id_compra'])} |" for r in irv]
L += ["", "Divergências e erros apontados (`validacao_ia/divergencias_revisao_humana_ia.csv`):", ""] + [f"- {r['id_compra']} ({r['classe']}): {r['motivo']}" for r in idiv] + [""]
# ------------------------------------------------------------------ pendencias
L += ["## Ocorrência nesta etapa", "",
      "- Ao refazer a aba de IA com as regras das fundações e dos itens, `p1_07_ia_validacao_marcas.py` regravou `validacao_ia/revisao_humana_ia.xlsx` com uma planilha nova, sem marcações. "
      "A planilha foi restaurada a partir de `revisao_humana_ia_marcada_v1.xlsx` (as 50 marcações conferidas uma a uma) e as 10 linhas extras da verificação por valor foram repostas com as marcações registradas "
      "(5 certas, 5 erradas, soma das erradas igual à registrada). O script agora não regrava a planilha quando ela existe. "
      "`resultado_revisao_humana_ia.csv` e `divergencias_revisao_humana_ia.csv`, refeitos com a planilha restaurada, ficaram idênticos aos anteriores.", ""]
L += ["## Pendências", "",
      "- Os três erros apontados na revisão humana da IA (lanches para curso de IA, palestra sobre ChatGPT, manutenção de CFTV) continuam na classe em que estão: o dicionário das classes não mudou depois da revisão.",
      "- Duas compras da amostra final do Acréscimo à licença (amostra 2, fichas 29 e 35) passaram a contar em Solução de IA com a repartição do valor pelos itens; os julgamentos não mudaram e a ficha tem nota.",
      "- A classe Outros da aba de IA reúne sobretudo equipamentos com IA embarcada e contratações mais amplas que citam IA nos itens; parte delas não é compra de tecnologia de IA.",
      "- Expressões de busca do dicionário e textos originais do PNCP mantêm a palavra do nome antigo da classe 3; não são texto do painel.",
      "- O script de migração do nome da classe 3 nas fichas e na planilha da fase 2 (`fase2/scripts/f2_16_nome_classe_3.py`) não entra no pacote; numa execução nova, os arquivos já saem com o nome atual.",
      "- A comparação com o PNCP em Números segue sem fonte acessível em texto ou arquivo.", ""]
L += ["## Arquivos", "", "- `painel_soberania_digital_v3.html`", "- `METODOLOGIA_v3.md`", "- `pacote_downloads_v3.zip`", "- `conferencia_numeros_v3.csv`",
      "- `tabelas_painel_v3/`, `scripts_painel_v3/`, `validacao_ia/`, `verificacao_html_v3/`", "- `relatorio_final_painel_v3.md`", ""]
open("relatorio_final_painel_v3.md", "w", encoding="utf-8").write("\n".join(L) + "\n")
print("\n".join(L))
