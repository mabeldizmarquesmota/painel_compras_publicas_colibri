"""Painel v5.1, etapa 2: painel HTML, metodologia e pacote de downloads da versao 5.1.

Executar a partir de Processado/, depois de p51_01:  python scripts_painel_v5_1/p51_02_painel.py
Entradas (somente leitura): painel_soberania_digital_v5.html (copia de partida), METODOLOGIA_v5.md, pacote_downloads_v5.zip,
  tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv (p51_01) e os scripts de scripts_painel_v5_1/.
Mudancas: (1) "revisao humana independente" e variacoes -> "revisao manual realizada pela pesquisadora responsavel (Mabel Mota)",
  com a lista de cada ocorrencia alterada; (2) rodape "Versao 5.1" com a data de geracao; (3) grafico 9 com o mesmo componente e
  comportamento do grafico 8 (botoes em pilula iguais, cliques em no, fluxo e legenda filtrando grafico e tabela, novo clique desfaz,
  nos dois graficos); (4) nota no "i" do grafico 9 e reconciliacao com a categoria IA na metodologia.
Regras: nenhum numero e digitado; cada mudanca e uma substituicao com contagem conferida (o script para se o trecho nao casar).
Saidas: painel_soberania_digital_v5_1.html, METODOLOGIA_v5_1.md, pacote_downloads_v5_1.zip,
  tabelas_painel_v5_1/revisao_manual_ocorrencias.csv (arquivo; local; trecho_anterior; trecho_novo; ocorrencias).
"""
import base64
import csv
import datetime
import html
import io
import os
import re
import sys
import zipfile

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, "scripts_painel_v5_1")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v5_1.formatacao import inteiro, mi  # noqa: E402

HOJE = datetime.date.today()
T = "tabelas_painel_v5_1/"


def troca(txt, old, new, n=1, rot=None):
    c = txt.count(old)
    assert c == n, f"{rot or old[:100]!r}: {c} ocorrências, esperado {n}"
    return txt.replace(old, new)


h = open("painel_soberania_digital_v5.html", encoding="utf-8").read()
MD = open("METODOLOGIA_v5.md", encoding="utf-8").read()
z5 = zipfile.ZipFile("pacote_downloads_v5.zip")
LEIAME = z5.read("LEIAME.txt").decode("utf-8")

# ================================================================== 1. revisao humana -> revisao manual da pesquisadora responsavel
P = "revisão manual realizada pela pesquisadora responsável (Mabel Mota)"
P_V = "revisão manual realizada pela pesquisadora responsável, Mabel Mota"  # antes de parentese, para nao aninhar
REV = [  # (trecho anterior, trecho novo), dos mais longos para os mais curtos
    ("Revisão humana independente: 50 compras", "Revisão manual realizada pela pesquisadora responsável (Mabel Mota): 50 compras"),
    ("a revisão humana independente cobriu 120 casos", f"a {P} cobriu 120 casos"),
    ("Planilha da revisão humana independente (120 casos)", f"Planilha da {P_V} (120 casos)"),
    ("Revisão humana independente", "Revisão manual realizada pela pesquisadora responsável (Mabel Mota)"),
    ("uma revisora independente julgou uma subamostra", "a pesquisadora responsável (Mabel Mota) julgou, em revisão manual, uma subamostra"),
    ("Resultado da revisão humana por classe", f"Resultado da {P}, por classe"),
    ("Concordância entre a revisão humana e a verificação", f"Concordância entre a {P} e a verificação"),
    ("a correção de um caso da revisão humana (", f"a correção de um caso da {P_V} ("),
    ("na planilha da revisão humana, que já tinham", f"na planilha da {P}, que já tinham"),
    ("o dicionário não mudou depois da revisão humana.", f"o dicionário não mudou depois da {P}."),
    ("Revisão humana da classificação da aba Inteligência artificial", "Revisão manual realizada pela pesquisadora responsável (Mabel Mota): classificação da aba Inteligência artificial"),
    ("Revisão humana da lista: a equipe de pesquisa revisou à mão", "Revisão manual da lista, realizada pela pesquisadora responsável (Mabel Mota), que revisou à mão"),
    ("a verificação por amostragem e a revisão humana medem", f"a verificação por amostragem e a {P} medem"),
    ("apontada na revisão humana)", f"apontada na {P_V})"),
    ("Resultado da revisão humana, concordância entre revisões", f"Resultado da {P}, concordância entre revisões"),
    ("planilha de revisão humana (gerada uma vez;", f"planilha da {P_V} (gerada uma vez;"),
    ("planilha de revisão humana (lista congelada", f"planilha da {P_V} (lista congelada"),
    ("Resultado da revisão humana da aba de IA e divergências", f"Resultado da {P} na aba de IA e divergências"),
    ("não atingiu 80% de acerto na revisão humana.", f"não atingiu 80% de acerto na {P}."),
    ("na verificação por amostragem e na revisão humana: acréscimo", f"na verificação por amostragem e na {P}: acréscimo"),
]
MANTIDO = ['coluna "revisão humana" de validacao_ia/exclusao_fundacoes_apoio.csv', 'coluna &quot;revisão humana&quot; de validacao_ia/exclusao_fundacoes_apoio.csv']
i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
i_d = h.find("const D = ")
f_d = h.find(";\nconst ZIP", i_d)
partes = {"painel: metodologia (aba)": h[i_met:f_met], "painel: dados embutidos (textos dos i)": h[i_d:f_d]}
ocorr = []
for de, para in REV:
    tot = 0
    for loc in partes:
        n = partes[loc].count(de)
        if n:
            partes[loc] = partes[loc].replace(de, para)
            ocorr.append(["painel_soberania_digital_v5_1.html", loc, de, para, n])
            tot += n
    for nome in ("MD", "LEIAME"):
        txt = MD if nome == "MD" else LEIAME
        n = txt.count(de)
        if n:
            ocorr.append(["METODOLOGIA_v5_1.md" if nome == "MD" else "pacote_downloads_v5_1.zip: LEIAME.txt", "texto", de, para, n])
            tot += n
            if nome == "MD":
                MD = MD.replace(de, para)
            else:
                LEIAME = LEIAME.replace(de, para)
    assert tot > 0, de
h = h[:i_met] + partes["painel: metodologia (aba)"] + h[f_met:i_d] + partes["painel: dados embutidos (textos dos i)"] + h[f_d:]
resto = lambda t: re.sub("|".join(re.escape(m) for m in MANTIDO), "", t)
for t, rot in ((h, "HTML"), (MD, "MD"), (LEIAME, "LEIAME")):
    assert not re.search(r"(?i)revis(ão|ões) humanas?|revisora independente", resto(t)), (rot, re.findall(r".{40}(?i:revis(?:ão|ões) humanas?).{40}", resto(t))[:3])
for m in MANTIDO[:1]:
    ocorr.append(["METODOLOGIA_v5_1.md e painel (metodologia)", "mantido", m, "sem mudança: nome literal de coluna do arquivo de dados", MD.count(m) + h.count(MANTIDO[1])])
with open(T + "revisao_manual_ocorrencias.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["arquivo", "local", "trecho_anterior", "trecho_novo", "ocorrencias"])
    w.writerows(ocorr)

# ================================================================== 2. rodape
h = troca(h, "<footer>Versão 1.0, gerada em 02/10/2026.", f"<footer>Versão 5.1, gerada em {HOJE:%d/%m/%Y}.")

# ================================================================== 3. grafico 9 com o componente e o comportamento do grafico 8
# botoes em pilula: mesmo estilo e espacamento do grafico 8 (sem o recuo antes de Capacitacao)
h = troca(h, ".ia-filtros button.ia-cap{margin-left:22px}\n", "")
h = troca(h, '${k === s.f ? "ativo" : ""}${k === "cap" ? " ia-cap" : ""}', '${k === s.f ? "ativo" : ""}')
h = troca(h, "#sankey path,#sankey rect,.legenda-html span{cursor:pointer}", "#sankey path,#sankey rect,#ia-sankey path,#ia-sankey rect,.legenda-html span{cursor:pointer}")
# grafico 8: novo clique no mesmo elemento desfaz a selecao (categoria, fornecedor, orgao, fluxo, legenda, botao ativo)
h = troca(h, "function selecionaCategoria(c){ E.sd.cat = c; E.sk = null; renderSoberania(); }",
          "function selecionaCategoria(c){ E.sd.cat = E.sd.cat === c && !E.sk ? -1 : c; E.sk = null; renderSoberania(); }  // novo clique desfaz")
h = troca(h, "    E.sk = {tipo, ids: sel, nome: d.nome}; const per2 = periodo(E.sd.ini, E.sd.fim);",
          "    E.sk = E.sk && E.sk.tipo === tipo && E.sk.nome === d.nome ? null : {tipo, ids: sel, nome: d.nome}; const per2 = periodo(E.sd.ini, E.sd.fim);")
# grafico 9: mesma logica
h = troca(h, 'b.onclick = () => { E.ia.f = b.dataset.f; E.ia.sk = null; E.ia.ord = null; renderIA(); });',
          'b.onclick = () => { E.ia.f = E.ia.f === b.dataset.f && !E.ia.sk ? "tec" : b.dataset.f; E.ia.sk = null; E.ia.ord = null; renderIA(); });  // novo clique desfaz')
h = troca(h, 'function clicaNo(d){ const tipo = d.id[0]; if (tipo === "t") { E.ia.sk = {tipo, ids: [+d.id.slice(1)], nome: d.nome}; renderIA(); return; }\n'
          '    const T = tipo === "f" ? F : O;\n    const sel = d.id.endsWith("D") ? [...T.m.keys()].filter(k => !T.top.has(k)) : [+d.id.slice(1)];\n'
          '    E.ia.sk = {tipo, ids: sel, nome: d.nome}; renderIA',
          'function clicaNo(d){ const tipo = d.id[0], T = tipo === "f" ? F : O;\n'
          '    const sel = tipo === "t" ? [+d.id.slice(1)] : d.id.endsWith("D") ? [...T.m.keys()].filter(k => !T.top.has(k)) : [+d.id.slice(1)];\n'
          '    selecionaIA(tipo, sel, d.nome); renderIA')
h = troca(h, 'E.ia.sk = {tipo: "t", ids: [d.tipo], nome: IA.tipos[d.tipo]}; renderIA(); });',
          'selecionaIA("t", [d.tipo], IA.tipos[d.tipo]); renderIA(); });')
h = troca(h, "function iaSelecao(s, rows){",
          "// selecao no grafico 9 (no, fluxo ou legenda), como no grafico 8: novo clique no mesmo elemento desfaz\n"
          "function selecionaIA(tipo, ids, nome){ E.ia.sk = E.ia.sk && E.ia.sk.tipo === tipo && E.ia.sk.nome === nome ? null : {tipo, ids, nome}; }\n"
          "function iaSelecao(s, rows){")
h = troca(h, '  $("ia-leg").innerHTML = tiposUsados.map(t => `<span><i style="background:${corT(t)}"></i>${IA.tipos[t]}</span>`).join("");',
          '  $("ia-leg").innerHTML = tiposUsados.map(t => `<span data-tipo="${t}" class="${s.sk && s.sk.tipo === "t" && !s.sk.ids.includes(t) ? "inativo" : ""}">'
          '<i style="background:${corT(t)}"></i>${IA.tipos[t]}</span>`).join("");\n'
          '  $("ia-leg").querySelectorAll("span").forEach(sp => sp.onclick = () => { selecionaIA("t", [+sp.dataset.tipo], IA.tipos[+sp.dataset.tipo]); renderIA(); });')

# ================================================================== 4. nota no i do grafico 9 e reconciliacao
NOTA_IA = ("A aba de inteligência artificial não coincide com a categoria Inteligência artificial da aba de tecnologias críticas: exclui as compras de capacitação "
           "e inclui as compras de acréscimo de IA a licenças (Copilot, Gemini) classificadas em outras categorias. Por isso os totais diferem.")
h = troca(h, "o PNCP não permite separar a parte gasta com IA.</div></span></span>",
          f"o PNCP não permite separar a parte gasta com IA.</div><div class='tt-sep'></div><div class='tt-txt'>{NOTA_IA}</div></span></span>")
REC = list(csv.DictReader(open(T + "ia_reconciliacao_grafico8_grafico9.csv", encoding="utf-8"), delimiter=";"))
n_ = lambda x: inteiro(abs(int(x)))
v_ = lambda x: mi(abs(float(x)))
g8, me, ma, g9, cm = REC[:5]
P_REC = (f"{NOTA_IA} Reconciliação, período completo, valores nominais, compras com vencedor identificado (ia_reconciliacao_grafico8_grafico9.csv): o gráfico 8, com a categoria "
         f"Inteligência artificial, tem {n_(g8['compras'])} compras, {n_(g8['fornecedores'])} fornecedores, {n_(g8['orgaos'])} órgãos e {v_(g8['valor_nominal'])}; saem "
         f"{n_(me['compras'])} compras de capacitação classificadas na categoria ({n_(me['fornecedores'])} fornecedores e {n_(me['orgaos'])} órgãos que só aparecem nelas; "
         f"{v_(me['valor_nominal'])}) e entram {n_(ma['compras'])} compras de acréscimo de IA a licenças classificadas em outras categorias ({n_(ma['fornecedores'])} fornecedores e "
         f"{n_(ma['orgaos'])} órgãos novos; {v_(ma['valor_nominal'])}). O resultado é o gráfico 9, com o botão Todas (tecnologia): {n_(g9['compras'])} compras, "
         f"{n_(g9['fornecedores'])} fornecedores, {n_(g9['orgaos'])} órgãos e {v_(g9['valor_nominal'])}. As {n_(cm['compras'])} compras comuns aos dois gráficos têm o mesmo "
         f"valor ({v_(cm['valor_nominal'])}).")
P_V51 = ("Versão 5.1: o gráfico 9 usa o mesmo componente e o mesmo comportamento do gráfico 8: botões em pílula no mesmo estilo e na mesma posição; o clique num nó de "
         "fornecedor, de tipo de objeto ou de órgão, num fluxo ou na legenda filtra o diagrama e a tabela logo abaixo; um novo clique no mesmo elemento, ou no botão já ativo, "
         "desfaz a seleção, nos dois gráficos; as dicas ao passar o mouse seguem o mesmo formato.")
MET = [
    ("o clique num fornecedor ou órgão refaz o diagrama só com os fluxos desse nó.",
     "o clique num fornecedor ou órgão refaz o diagrama só com os fluxos desse nó; um novo clique no mesmo elemento (ou no botão já ativo) desfaz a seleção."),
]
SCRIPTS = [
    ("scripts_painel_v5_1/p51_00_hashes.py", "Conferência dos hashes registrados das versões congeladas 1 a 5 (no início e no fim da versão 5.1)."),
    ("scripts_painel_v5_1/p51_01_reconciliacao_ia.py", "Reconciliação entre a categoria Inteligência artificial do gráfico 8 e a tecnologia de IA do gráfico 9."),
    ("scripts_painel_v5_1/p51_02_painel.py", "Painel HTML da versão 5.1 a partir do HTML da versão 5, metodologia, pacote e lista das ocorrências da revisão manual."),
    ("scripts_painel_v5_1/p51_03_verificar_html.py", "Verificação do HTML em Chromium sem internet, em 1440 px e 390 px, gráfico 9 comparado com o gráfico 8 e capturas."),
    ("scripts_painel_v5_1/p51_04_conferencia.py", "Conferência dos números do painel com as tabelas agregadas."),
    ("scripts_painel_v5_1/p51_05_relatorio_final.py", "Relatório final, congelamento da versão 5.1 e conferência dos hashes."),
]
for s_, _ in SCRIPTS:
    assert os.path.exists(s_), s_
N0 = 74
md = MD
for de, para in MET:
    md = troca(md, de, para)
md = troca(md, MD.split("\n")[2], f"Versão 5.1, gerada por `scripts_painel_v5_1/p51_02_painel.py` em {HOJE:%d/%m/%Y} a partir de METODOLOGIA_v5.md: revisão manual atribuída à "
           "pesquisadora responsável, gráfico 9 com o comportamento do gráfico 8 e reconciliação da aba de IA com a categoria Inteligência artificial; nenhuma classificação foi "
           "refeita. Os números coincidem com os do painel `painel_soberania_digital_v5_1.html` (conferência em `conferencia_numeros_v5_1.csv`).")
md = troca(md, "`pacote_downloads_v5.zip`", "`pacote_downloads_v5_1.zip`", 2)
md = troca(md, "\n### Marcas de IA citadas\n", "\n" + P_V51 + "\n\n### Aba de IA e categoria Inteligência artificial\n\n" + P_REC + "\n\n### Marcas de IA citadas\n")
ult = f"- {N0}. scripts_painel_v5/p5_05_relatorio_final.py: Relatório final, congelamento da versão 5 e conferência dos hashes."
md = troca(md, ult, ult + "".join(f"\n- {N0 + i + 1}. {s_}: {d_}" for i, (s_, d_) in enumerate(SCRIPTS)))
i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
met = h[i_met:f_met]
esc = html.escape
for de, para in MET:
    met = troca(met, esc(de), esc(para))
met = troca(met, "\n<h3>Marcas de IA citadas</h3>", f"\n<p>{esc(P_V51)}</p>\n<h3>Aba de IA e categoria Inteligência artificial</h3>\n<p>{esc(P_REC)}</p>\n<h3>Marcas de IA citadas</h3>")
ult_h = f"<li>{esc(ult[2:])}</li>"
met = troca(met, ult_h, ult_h + "".join(f"<li>{esc(f'{N0 + i + 1}. {s_}: {d_}')}</li>" for i, (s_, d_) in enumerate(SCRIPTS)))
met = troca(met, "<code>pacote_downloads_v5.zip</code>", "<code>pacote_downloads_v5_1.zip</code>")
h = h[:i_met] + met + h[f_met:]

# ================================================================== pacote de downloads
LEIAME = troca(LEIAME, "Os scripts da versão 5 (69 a 74) não regravam nenhuma saída das versões anteriores.",
               "Os scripts da versão 5 (69 a 74) não regravam nenhuma saída das versões anteriores.\n"
               f"Versão 5.1: gerada em {HOJE:%d/%m/%Y} por scripts_painel_v5_1/p51_02_painel.py a partir da versão 5; METODOLOGIA_v5_1.md substitui METODOLOGIA_v5.md. "
               "Os scripts da versão 5.1 (75 a 80) não regravam nenhuma saída das versões anteriores. Nos textos, a revisão humana passou a ser identificada como revisão manual "
               "realizada pela pesquisadora responsável (Mabel Mota); nomes de arquivos, colunas e sementes (por exemplo, revisao_humana_ia.xlsx) foram mantidos.")
l74 = f"{N0}. scripts_painel_v5/p5_05_relatorio_final.py  (Relatório final, congelamento da versão 5 e conferência dos hashes.)"
LEIAME = troca(LEIAME, l74, l74 + "".join(f"\n{N0 + i + 1}. {s_}  ({d_})" for i, (s_, d_) in enumerate(SCRIPTS)))
LEIAME = troca(LEIAME, "Tabelas agregadas (pasta tabelas_agregadas/):", "Tabelas novas da versão 5.1: ia_reconciliacao_grafico8_grafico9.csv (p51_01) e "
               "revisao_manual_ocorrencias.csv (p51_02).\nTabelas agregadas (pasta tabelas_agregadas/):")
SCR = sorted("scripts_painel_v5_1/" + x for x in os.listdir("scripts_painel_v5_1") if x.endswith(".py"))
TAB = sorted(T + x for x in os.listdir(T) if x.endswith(".csv"))
ler_b = lambda c: open(c, "rb").read()


def zip_bytes(pares):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in pares:
            z.writestr(nome, conteudo)
    return buf.getvalue()


def interno(nome_zip, extras):
    zz = zipfile.ZipFile(io.BytesIO(z5.read(nome_zip)))
    pares = [("LEIAME.txt", LEIAME)] + [(n, zz.read(n)) for n in zz.namelist() if n != "LEIAME.txt"]
    nomes = {n for n, _ in pares}
    for nome, c in extras:
        assert nome not in nomes, nome
        pares.append((nome, ler_b(c)))
    return zip_bytes(pares)


scripts_zip = interno("scripts.zip", [(s_, s_) for s_ in SCR])
tabelas_zip = interno("tabelas_agregadas.zip", [(os.path.basename(t), t) for t in TAB])
with zipfile.ZipFile("pacote_downloads_v5_1.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("LEIAME.txt", LEIAME)
    for n in z5.namelist():
        if n.startswith(("scripts/", "tabelas_agregadas/")):
            z.writestr(n, z5.read(n))
    for s_ in SCR:
        z.writestr("scripts/" + s_, ler_b(s_))
    for t in TAB:
        z.writestr("tabelas_agregadas/" + os.path.basename(t), ler_b(t))
    z.writestr("scripts.zip", scripts_zip)
    z.writestr("tabelas_agregadas.zip", tabelas_zip)
    z.writestr("METODOLOGIA_v5_1.md", md)
m_zip = re.search(r'const ZIP = \{scripts: "([A-Za-z0-9+/=]+)", tabelas: "([A-Za-z0-9+/=]+)"\};', h)
assert m_zip
h = h[:m_zip.start()] + f'const ZIP = {{scripts: "{base64.b64encode(scripts_zip).decode()}", tabelas: "{base64.b64encode(tabelas_zip).decode()}"}};' + h[m_zip.end():]
open("painel_soberania_digital_v5_1.html", "w", encoding="utf-8").write(h)
open("METODOLOGIA_v5_1.md", "w", encoding="utf-8").write(md)
print("ok", f"{os.path.getsize('painel_soberania_digital_v5_1.html') / 1e6:.1f} MB", f"pacote {os.path.getsize('pacote_downloads_v5_1.zip') / 1e6:.1f} MB",
      f"{sum(x[4] for x in ocorr if x[1] != 'mantido')} ocorrências de revisão humana alteradas")
