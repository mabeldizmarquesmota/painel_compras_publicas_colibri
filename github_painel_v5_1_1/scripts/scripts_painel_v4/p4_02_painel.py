"""Painel v4, etapa 2: painel HTML, metodologia e pacote de downloads da versao 4 (Ajuste 4: texto, ordem e layout).

Executar a partir de Processado/, depois de p4_01:  python scripts_painel_v4/p4_02_painel.py
Entradas (somente leitura): painel_soberania_digital_v3.html (copia de partida), METODOLOGIA_v3.md, pacote_downloads_v3.zip,
  tabelas_painel_v4/ia_achados_v4.csv (p4_01) e os scripts de scripts_painel_v4/.
Regras: nenhum numero e digitado nem recalculado; os numeros continuam saindo dos dados ja embutidos no HTML da v3 (as
  mesmas tabelas agregadas). Cada mudanca e uma substituicao de texto com contagem conferida: se o trecho de origem nao
  aparecer exatamente o numero de vezes esperado, o script para. A unica conta nova (achado 4 da IA) vem de p4_01.
Saidas: painel_soberania_digital_v4.html, METODOLOGIA_v4.md, pacote_downloads_v4.zip.
"""
import base64
import csv
import datetime
import html
import io
import json
import os
import re
import sys
import zipfile

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
HOJE = datetime.date.today()


def troca(txt, old, new, n=1, rot=None):
    c = txt.count(old)
    assert c == n, f"{rot or old[:100]!r}: {c} ocorrências, esperado {n}"
    return txt.replace(old, new)


def corta(txt, ini, fim, novo="", incluir_fim=False):
    """Substitui o trecho de 'ini' (inclusive) ate 'fim' (exclusive, ou inclusive com incluir_fim); cada marcador uma vez."""
    assert txt.count(ini) == 1, f"marcador inicial {ini[:80]!r}: {txt.count(ini)}"
    a = txt.find(ini)
    b = txt.find(fim, a)
    assert b > a and txt.count(fim, a) >= 1, f"marcador final {fim[:80]!r}"
    if incluir_fim:
        b += len(fim)
    return txt[:a] + novo + txt[b:]


def balanceado(txt, a, tag):
    """Fim do elemento <tag ...> que comeca em a, contando aberturas e fechamentos do mesmo tag."""
    prof = 0
    for m in re.finditer(rf"<{tag}\b|</{tag}>", txt[a:]):
        prof += -1 if m.group(0).startswith("</") else 1
        if prof == 0:
            return a + m.end()
    raise AssertionError(f"elemento {tag} sem fechamento")


def bloco(txt, marcador, inicio='<div class="graf-card"'):
    assert txt.count(marcador) == 1, f"marcador {marcador!r}: {txt.count(marcador)}"
    p = txt.find(marcador)
    a = txt.rfind(inicio, 0, p)
    assert a >= 0, inicio
    return txt[a:balanceado(txt, a, "div")]


def icone_de(txt, chave):
    a = txt.find(f"data-i='{chave}'")
    a = txt.rfind("<span class='info'", 0, a)
    return txt[a:balanceado(txt, a, "span")]


def info(chave, conteudo, rotulo, larg=None):
    lg = f" data-larg='{larg}'" if larg else ""
    return (f"<span class='info' tabindex='0' role='button' aria-label='{rotulo}' data-i='{chave}'{lg}>i"
            f"<span class='tt'>{conteudo}</span></span>")


h = open("painel_soberania_digital_v3.html", encoding="utf-8").read()
NOTA_HOM = ("Todos os valores são homologados: soma dos itens adjudicados aos vencedores, conforme registrado no PNCP. "
            "Não equivalem ao valor contratado nem ao valor pago.")

# ================================================================== CSS
CSS_NOVO = """
/* versao 4 (Ajuste 4): titulos, caixas de abertura com i, cartoes compactos das categorias e divisores */
h2.sec.tit-laranja{color:#E3972B;font-weight:400;font-size:28px;margin:4px 0 16px}
.caixa-i{position:relative;padding-right:62px}
.caixa-i>.info{position:absolute;top:18px;right:20px}
.texto-abertura p:last-of-type{margin-bottom:0}
.intro-sob{border-left:0}
.intro-sob .sel-tit{font-weight:700;margin:12px 0 0}
.cats{grid-template-columns:repeat(6,minmax(0,1fr));gap:12px;margin:10px 0 2px}
.cat-card{padding:10px 12px;border-radius:10px}
.cat-topo{gap:7px}
.cat-nome{font-size:14px;line-height:1.25}
@media (max-width:1100px){.cats{grid-template-columns:repeat(3,minmax(0,1fr))}}
@media (max-width:600px){.cats{grid-template-columns:repeat(2,minmax(0,1fr))}}
.divisor{height:8px;margin:34px 0 6px;background:radial-gradient(ellipse at center,rgba(148,163,184,.6) 0%,rgba(148,163,184,0) 72%)}
.ia-cad{margin-top:22px;padding-top:16px;border-top:1px solid var(--linha)}
.ia-cad .t1-acoes{align-items:center;gap:12px}
"""
h = troca(h, "footer{max-width:1280px;", CSS_NOVO.strip() + "\nfooter{max-width:1280px;")
h = troca(h, "@media (max-width:900px){.kpis,.kpis.dois,.kpis.tres,.cats{grid-template-columns:1fr}",
          "@media (max-width:900px){.kpis,.kpis.dois,.kpis.tres{grid-template-columns:1fr}")
# graficos de barras e de linha cerca de 35% mais baixos (altura fixa e altura calculada pelo numero de barras)
h = troca(h, ".area{position:relative;width:100%;height:380px}", ".area{position:relative;width:100%;height:247px}")
for de, para in (('style="height:280px"><canvas id="g2">', 'style="height:182px"><canvas id="g2">'),
                 ('style="height:240px"><canvas id="g3">', 'style="height:156px"><canvas id="g3">'),
                 ('style="height:380px" id="g4-area">', 'style="height:247px" id="g4-area">'),
                 ('style="height:400px"><canvas id="g5">', 'style="height:260px"><canvas id="g5">'),
                 ('style="height:320px"><canvas id="g6">', 'style="height:208px"><canvas id="g6">'),
                 ('style="height:440px" id="g7-area">', 'style="height:286px" id="g7-area">')):
    h = troca(h, de, para)
h = troca(h, "(altura || Math.max(160, 46 * nomes.length + 30))", "(altura || Math.max(104, 30 * nomes.length + 20))")
h = troca(h, 'Math.max(220, 62 * mods.length + 60) + "px"', 'Math.max(143, 40 * mods.length + 40) + "px"')
# Sankeys cerca de 20% mais baixos (560 -> 448)
h = troca(h, "const W = estreito ? 900 : Math.max(700, box.clientWidth || 1100), H = 560;",
          "const W = estreito ? 900 : Math.max(700, box.clientWidth || 1100), H = 448;", 2)
# espacamento entre nos de 9 para 14 px: com a altura menor, rotulos de nos pequenos nao se sobrepoem (conferido por p4_03)
h = troca(h, ".nodePadding(9)", ".nodePadding(14)", 2)

# ================================================================== tooltip: i com largura propria (texto longo da abertura)
h = troca(h, "  TT.innerHTML = src.innerHTML; TT.style.display = \"block\";\n",
          "  TT.innerHTML = src.innerHTML; TT.style.maxWidth = el.dataset.larg || \"\"; TT.style.display = \"block\";\n")
h = troca(h, "function ttHTML(html, ev){ TT.innerHTML = html; TT.style.display = \"block\";",
          "function ttHTML(html, ev){ TT.innerHTML = html; TT.style.maxWidth = \"\"; TT.style.display = \"block\";")

# ================================================================== aba Compras publicas
TXT_CP = ("A análise mostra quanto o poder público contratou via PNCP, em que ritmo e por quais modalidades. O valor corresponde ao total "
          "homologado de cada compra, registrado uma única vez no ano de publicação. Os indicadores anuais somam as compras publicadas em "
          "cada ano, enquanto os indicadores do período refletem os anos selecionados no filtro.")
ini_cp = '<section class="aba-conteudo" id="aba-compras">'
a = h.find(ini_cp)
b = h.find('  <div class="kpis dois">', a)
h = h[:a] + ini_cp + f"""
  <div class="cab-sec"><div><h2 class="sec tit-laranja">Compras públicas</h2></div>
    <button class="btn-csv" id="cp-csv">⤓ Baixar dados (CSV)</button></div>
  <div class="card texto-abertura caixa-i">
    <p>{html.escape(TXT_CP, quote=False)}</p>{info("cp_abertura", f"<div class='tt-txt'>{html.escape(NOTA_HOM, quote=False)}</div>", "Valor homologado")}
  </div>
""" + h[b:]
assert h[a:b + 2000].count('id="cp-csv"') == 1
h = corta(h, '  $("cp-frase-valores").textContent = E.defl ?', '  const nPub = soma(rows.map(r => r[4]))')

# ================================================================== aba Tecnologias criticas para a soberania digital
ini_sd = '<section class="aba-conteudo" id="aba-soberania">'
a = h.find(ini_sd)
b = h.find("</section>", a) + len("</section>")
sec = h[a:b]
intro = bloco(sec, '<div class="cats">', '<div class="card intro-sob"')
m_txt = re.search(r"<p>Esta seção apresenta as compras públicas de tecnologias críticas para a soberania digital\. (Soberania digital é a capacidade .*? e o local de hospedagem dos dados\.)</p>", intro)
assert m_txt
TEXTO_LONGO = m_txt.group(1)
cartoes = []
for m in re.finditer(r"<div class='cat-card' style='--cor:(#[0-9A-Fa-f]{6})'><div class='cat-topo'><span class='cat-dot'></span><span class='cat-nome'>([^<]+)</span>"
                     r"<span class='info' tabindex='0' role='button' aria-label='Palavras-chave' data-i='(cat_\w+)'>i<span class='tt'>"
                     r"<div class='tt-rot'>Palavras-chave</div><div class='tt-txt'>(Termos buscados no objeto da compra e na descrição dos itens:)</div>(<ul class='tt-lista'>.*?</ul>)"
                     r"<div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Verificação:</b> ([^<]+)</div></span></span></div>"
                     r"<div class='cat-camada'>[^<]*</div><div class='cat-desc'>([^<]+)</div></div>", intro):
    cor, nome, chave, intro_termos, lista, verif, desc = m.groups()
    tt = (f"<div class='tt-txt'><b class='tt-ex'>Conceito:</b> {desc}</div><div class='tt-sep'></div>"
          f"<div class='tt-txt'><b class='tt-ex'>Palavras-chave:</b> {intro_termos}</div>{lista}<div class='tt-sep'></div>"
          f"<div class='tt-txt'><b class='tt-ex'>Verificação:</b> {verif}</div>")
    cartoes.append(f"<div class='cat-card' style='--cor:{cor}'><div class='cat-topo'><span class='cat-dot'></span><span class='cat-nome'>{nome}</span>"
                   f"{info(chave, tt, 'Conceito, palavras-chave e verificação')}</div></div>")
assert len(cartoes) == 6, len(cartoes)
TXT_SD = ("Esta seção apresenta as compras públicas de tecnologias críticas para a soberania digital, entendida como a capacidade do Estado "
          "de controlar dados, infraestrutura e tecnologias essenciais ao seu funcionamento.")
tt_intro = "<div class='tt-txt'>" + TEXTO_LONGO + "</div>"
novo_intro = (f'<div class="card intro-sob caixa-i">\n    <p>{TXT_SD}</p>'
              f'{info("sd_intro", tt_intro, "Soberania digital", "560px")}\n'
              f'    <p class="sel-tit">Tecnologias selecionadas:</p>\n    <div class="cats">{"".join(cartoes)}</div>\n  </div>')
kpis = bloco(sec, 'id="sd-kpis"', '<div class="kpis"')
g5, g6, g7 = bloco(sec, 'id="g5"'), bloco(sec, 'id="g6"'), bloco(sec, 'id="g7"')
sk = bloco(sec, 'id="sankey"')
sk = troca(sk, '<div class="tg1">Gráfico 11</div>', '<div class="tg1">Gráfico 8</div>')
sk = troca(sk, '<p class="texto-exec" id="g9-txt"></p><div class="fonte" data-fonte></div>', '<div class="fonte" data-fonte></div>')
t1 = troca(bloco(sec, 'id="t1"'), '<div class="tg1">Tabela 2</div>', '<div class="tg1">Tabela 1</div>')
tm = troca(bloco(sec, 'id="tm"'), '<div class="tg1">Tabela 1</div>', '<div class="tg1">Tabela 2</div>')
g10 = bloco(sec, 'id="ind-cartoes"')
cab_sd = bloco(sec, 'id="sd-csv"', '<div class="cab-sec"')
assert cab_sd.count("Tecnologias digitais") == 1
nova_sec = f"""{ini_sd}
  <div class="cab-sec"><div><h2 class="sec tit-laranja">Compras públicas de tecnologias críticas para a soberania digital</h2></div>
    <button class="btn-csv" id="sd-csv">⤓ Baixar dados (CSV)</button></div>
  {novo_intro}

  <div class="divisor"></div>
  <div class="bloco-tit">Principais achados</div>
  <div class="achados" id="achados"></div>
  {kpis}

  <div class="divisor"></div>
  <div class="bloco-tit">O que o Estado compra?</div>
  {g5}
  {g6}

  <div class="divisor"></div>
  <div class="bloco-tit">Modalidade de contratação</div>
  {g7}

  <div class="bloco-tit">De quem o Estado compra?</div>
  {sk}
  {t1}
  {tm}

  <div class="bloco-tit">O Estado usa o poder de compra a favor da oferta nacional?</div>
  {g10}
  <div class="card"><b>Nota:</b> <span id="nota-encomenda"></span></div>
</section>"""
h = h[:a] + nova_sec + h[b:]

# JavaScript da aba: frase de abertura, grafico 5, grafico 8 (forma), modelo, vendedor, porte, tabelas 3 e 4, Sankey, NCM
h = corta(h, "  const nCv = new Set(rFx.flatMap(r => r.c)).size;", "\n  // grafico 5\n")
h = troca(h, "  const foco = s.cat < 0 ? tots[0].i : s.cat;\n  const vA = a => ds5[foco].data[anos.indexOf(a)];\n", "")
h = troca(h, "ª posição entre as seis categorias.`) +\n    (cmp ? ` Em ${D.nome[CAT(foco)]}, o valor passou de ${mi(vA(cmp[0]))} em ${cmp[0]} para ${mi(vA(cmp[1]))} em ${cmp[1]}.` : \"\");",
          "ª posição entre as seis categorias.`);")
h = corta(h, "  // grafico 8: forma de contratacao\n", "  renderContrata(s, per);\n", "  renderMarcas(s, per);\n", incluir_fim=True)
h = troca(h, '$("g9-txt").textContent = ""; ', "")
h = corta(h, "  const fMax = F.ord[0], rF = rows.filter(r => r[2] === fMax[0]);\n", "como principal comprador.`;\n}\n", "}\n", incluir_fim=True)
h = corta(h, "function renderT2(s, per){", "function renderTabelas(s, per){")
h = troca(h, "function renderTabelas(s, per){ renderT1(s, per); renderT2(s, per); renderT3(s, per); }", "function renderTabelas(s, per){ renderT1(s, per); }")
G10 = r'''function renderG10(s, per){
  const rec = s.cat, dv = V(), nomeR = rec < 0 ? "de tecnologias críticas para a soberania digital" : "de " + D.nome[CAT(rec)], nomeC = rec < 0 ? "das tecnologias críticas" : "de " + D.nome[CAT(rec)];
  $("g10-t2").textContent = `Uso de instrumentos de política nas compras ${nomeR}, ${per}`;
  const ri = D.instr.filter(r => r[0] === rec && r[1] >= s.ini && r[1] <= s.fim);
  const sm = k => soma(ri.map(r => r[k + dv]));
  const base = sm(2), prev = sm(4), apl = sm(6), ppb = sm(8);
  const pc = x => base ? 100 * x / base : 0;
  const pr = nome => D.preench.find(p => p[0] === nome);
  const p1 = pr("margem de preferência prevista no edital"), p2 = pr("margem de preferência aplicada no resultado"), p3 = pr("exigência de Processo Produtivo Básico (PPB)");
  const vals = [prev, apl, ppb], pcts = vals.map(pc), vtxt = v => v === 0 ? "R$ 0" : mi(v);
  const campo = p => `campo preenchido em ${fmtPct(100 * p[2] / p[1])} dos registros`;
  [["prev", 0, p1, "do valor"], ["apl", 1, p2, ""], ["ppb", 2, p3, ""]].forEach(([id, k, pp, suf]) => {
    $("ind-" + id).textContent = fmtPct(pcts[k]);
    $("ind-" + id + "-v").textContent = (suf ? suf + " | " : "") + vtxt(vals[k]);
    $("ind-" + id + "-p").textContent = campo(pp); });
  const rot = vals.map((v, k) => `${fmtPct(pcts[k])} | ${vtxt(v)}`);
  reg("g10_prevista", rot[0]); reg("g10_aplicada", rot[1]); reg("g10_ppb", rot[2]);
  reg("ind_preenchimento", [p1, p2, p3].map(campo).join("|"));
  // texto do Ajuste 4: contagens de pn_instrumentos_preenchimento (periodo completo) e valores do recorte filtrado
  const cheio = [p1, p2, p3].every(p => p[2] === p[1]) ? "100%" : fmtPct(Math.min(...[p1, p2, p3].map(p => 100 * p[2] / p[1])));
  const ext = v => v === 0 ? "R$ 0" : vauto(v).replace(/ mi$/, " milhões").replace(/ bi$/, " bilhões");
  $("g10-nota").textContent = reg("g10_texto1", `Os três campos estão preenchidos em ${cheio} dos registros, predominantemente com "falso". Há ${inteiro(p1[3])} registros com margem de preferência prevista no edital, ` +
    `${inteiro(p2[3])} com margem aplicada e ${p3[3] ? inteiro(p3[3]) : "nenhum"} com exigência de PPB. A base não permite distinguir "não se aplica" de "não informado".`);
  const quando = s.ini === s.fim ? `Em ${s.ini}` : `De ${s.ini} a ${s.fim}`;
  $("g10-txt").textContent = `${quando}, compras com margem prevista representaram ${fmtPct(pcts[0])} do valor homologado ${nomeC} (${ext(prev)}).` +
    (apl === 0 && ppb === 0 ? " Não foram identificados valores associados à margem aplicada ou ao PPB."
      : apl > 0 && ppb > 0 ? ` As compras com margem aplicada representaram ${fmtPct(pcts[1])} (${ext(apl)}), e as compras com exigência de PPB, ${fmtPct(pcts[2])} (${ext(ppb)}).`
      : apl > 0 ? ` As compras com margem aplicada representaram ${fmtPct(pcts[1])} (${ext(apl)}); não foram identificados valores associados ao PPB.`
      : ` As compras com exigência de PPB representaram ${fmtPct(pcts[2])} (${ext(ppb)}); não foram identificados valores associados à margem aplicada.`);
}
'''
h = corta(h, "function renderG10(s, per){", "\n\n/* ---------------------------------------------------------------- principais achados", G10)
h = corta(h, "/* ---------------------------------------------------------------- bloco: como o Estado contrata e de quem depende */", "function marcasRecorte(s){",
          "/* ---------------------------------------------------------------- tabela 2: compras com mencao a marca */\n")
h = corta(h, "function renderPorte(s, per){", "\n/* ---------------------------------------------------------------- nota: encomenda tecnologica e CPSI */")
NOTA = r'''  $("nota-encomenda").textContent = `Nas seis categorias, foram identificadas ${pl(e[0][1], "compra", "compras")} por encomenda tecnológica (${v(e[0][2])}) e ` +
    `${inteiro(e[1][1])} por solução inovadora/CPSI (${v(e[1][2])}). Pelo art. 75, V, da Lei 14.133/2021, há ${inteiro(e[2][1])} compras enquadradas (${v(e[2][2])}), ` +
    `nem todas com menção explícita ao instrumento.`;
  reg("nota_encomenda", $("nota-encomenda").textContent);
'''
h = corta(h, '  $("nota-encomenda").textContent = `Busca por encomenda tecnológica', "})();\n", NOTA)
h = troca(h, '["tabela 3: concentração por ano", nm(r[0])', '["concentração por ano", nm(r[0])')
h = troca(h, '["tabela 4: perfil por ano", nm(r[0])', '["perfil por ano", nm(r[0])')
# grafico 5: so a primeira frase, sem a frase final do modo dos valores
h = troca(h, 'document.querySelectorAll("#aba-compras .texto-exec, #aba-soberania .texto-exec, #aba-ia .texto-exec, #aba-ia .com-modo")',
          'document.querySelectorAll("#aba-compras .texto-exec, #aba-soberania .texto-exec:not(#g5-txt), #aba-ia .texto-exec")')

# ================================================================== aba Inteligencia artificial
ini_ia = '<section class="aba-conteudo" id="aba-ia">'
a = h.find(ini_ia)
b = h.find("</section>", a) + len("</section>")
sec = h[a:b]
sk_ia = bloco(sec, 'id="ia-sankey"')
cad = bloco(sec, 'id="ia-t"')
marcas_ia = troca(bloco(sec, 'id="ia-marcas"'), '<div class="tg1">Tabela 6</div>', '<div class="tg1">Tabela 3</div>')
sk_ia = troca(sk_ia, '<div class="tg1">Gráfico 12</div>', '<div class="tg1">Gráfico 9</div>')
sk_ia = troca(sk_ia, '    <div class="ia-destaques" id="ia-destaques"></div>\n', "")
sk_ia = troca(sk_ia, '    <p class="texto-exec" id="ia-txt"></p><div class="fonte" data-fonte></div>\n',
              f'''    <div class="ia-cad">
      <div class="t1-acoes"><button class="btn-csv" id="ia-t-csv">⤓ Baixar tabela (CSV)</button>{icone_de(cad, "ia_cadeias")}</div>
      <div class="tabela-rolagem"><table class="tabela" id="ia-t"></table></div>
      <p class="nota-tab" id="ia-t-nota"></p>
    </div>
    <div class="fonte" data-fonte></div>
''')
TXT_IA = ("Esta seção detalha as compras públicas de Inteligência Artificial, ampliando a análise para categorias como aquisição e acréscimo "
          "de licenças, compra exclusiva e capacitação. O objetivo é caracterizar como o setor público adquire e utiliza essa tecnologia "
          "crítica para a soberania digital.")
assert sec.count('<button class="btn-csv" id="ia-csv">⤓ Baixar dados (CSV)</button>') == 1
nova_ia = f"""{ini_ia}
  <div class="cab-sec"><div><h2 class="sec tit-laranja">Compras públicas de inteligência artificial</h2></div>
    <button class="btn-csv" id="ia-csv">⤓ Baixar dados (CSV)</button></div>
  <div class="card texto-abertura">
    <p>{TXT_IA}</p>
  </div>
  <div class="bloco-tit">Principais achados das compras públicas de IA</div>
  <div class="achados" id="ia-achados"></div>

  {sk_ia}

  {marcas_ia}
</section>"""
h = h[:a] + nova_ia + h[b:]
h = corta(h, "  // linha-resumo: os dois mercados separados\n", "  // botoes de filtro, titulo e frase descritiva\n")
h = troca(h, "  renderDestaquesIA(s, per, rowsF);\n", "")
h = corta(h, "function renderDestaquesIA(s, per, rows){", "let IAT = [];")
h = troca(h, '$("ia-txt").textContent = ""; ', "")
h = corta(h, "  const top10 = soma(F.ord.slice(0, 10).map(x => x[1])), fMax = F.ord[0], rF = rows.filter(r => r[3] === fMax[0]);\n",
          "como principal comprador.`;\n}\n", "}\n", incluir_fim=True)
h = corta(h, '  const sel = s.sk ? ` (${s.sk.tipo === "f" ? "fornecedor" : "órgão"}: ${s.sk.nome})` : "";\n', "  const cls = iaCls(s.f)")
# principais achados da IA: texto do Ajuste 4 (p4_01), no lugar dos achados da v3 nos dados embutidos
i_d = h.find("const D = ") + len("const D = ")
D = json.loads(h[i_d:h.find(";\nconst ZIP", i_d)].replace("<\\/", "</"))
velho = json.dumps(D["ia"]["achados"], ensure_ascii=False, separators=(",", ":"))
novos = [[r["achado"], r["titulo"], r["texto"]] for r in csv.DictReader(open("tabelas_painel_v4/ia_achados_v4.csv", encoding="utf-8"), delimiter=";")]
h = troca(h, '"achados":' + velho, '"achados":' + json.dumps(novos, ensure_ascii=False, separators=(",", ":")))

# ================================================================== referencias cruzadas (nova numeracao)
REF = [  # (de, para, ocorrencias no HTML: i, copia dos textos do i em D.I, JavaScript)
    ("a mesma regra do gráfico 11 e das tabelas 2 e 3", "a mesma regra do gráfico 8 e da tabela 1", 2),
    ("a mesma regra do gráfico 11 e da tabela 2", "a mesma regra do gráfico 8 e da tabela 1", 2),
    ("na base dos resultados do gráfico 11.", "na base dos resultados do gráfico 8.", 2),
    ("A tabela acompanha a seleção feita no gráfico 11", "A tabela acompanha a seleção feita no gráfico 8", 3),
    ("(a mesma regra do gráfico 9)", "(a mesma regra do modelo de aquisição, descrita na metodologia)", 1),
    ("como no gráfico 9, e a compra", "como no modelo de aquisição, e a compra", 3),
    ("na base dos resultados do gráfico 12.", "na base dos resultados do gráfico 9.", 2),
    ("seleção feita no gráfico 12", "seleção feita no gráfico 9", 3),
    ("que o do tipo de objeto no gráfico 12.", "que o do tipo de objeto no gráfico 9.", 3),
]
h = troca(h, "(valor dos resultados, base do grafico 12 e da tabela 5).", "(valor dos resultados, base do grafico 9 e da tabela de cadeias logo abaixo dele).")
i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
fora = h[:i_met] + "\x00" + h[f_met:]
for de, para, n in REF:
    print(f"referência: {fora.count(de)}x {de!r} -> {para!r}")
    fora = troca(fora, de, para, n)
h = fora.split("\x00")[0] + h[i_met:f_met] + fora.split("\x00")[1]
for velho_ in ("gráfico 10", "gráfico 11", "gráfico 12", "Gráfico 10", "Gráfico 11", "Gráfico 12", "Tabela 4", "Tabela 5", "Tabela 6", "tabela 5", "tabela 6"):
    i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
    resto = h[:i_met] + h[h.find("</section>", i_met):]
    resto = re.sub(r'"(?:ia_resumo|ia_resumo_nota|porte|gm|gv|t2|t3|g8|g10ncm|gm_nota)":\{[^{}]*\}', "", resto)  # textos de elementos retirados (sem uso)
    assert velho_ not in resto.replace("tabela 1737", ""), velho_

# ================================================================== metodologia
MD = open("METODOLOGIA_v3.md", encoding="utf-8").read()
CRIT_T = ("Tabela 1 (cadeias fornecedor → objeto → órgão): logo abaixo do gráfico 8, com o mesmo valor dos resultados e reativa à seleção no gráfico; "
          "mostra até 50 cadeias por categoria, em ordem de valor. Tabela 2 (compras com menção à marca): responde aos filtros de ano e de categoria e usa o valor dos resultados (ver seção 7). "
          "Concentração (CR4 e HHI) e perfil das compras não são exibidos no painel; os dados por categoria e ano estão no pacote de downloads (pn_concentracao.csv, pn_perfil.csv, "
          "pn_perfil_valores_por_compra.csv e pn_perfil_bens.csv) e no CSV de download da aba.")
MET = [  # (de, para): aplicados ao METODOLOGIA_v4.md e, com o mesmo texto escapado, a metodologia dentro do HTML
    ("**TABELA 7. ", "**TABELA 4. "),
    ("O fornecedor é o CNPJ do vencedor (ni_fornecedor), que pode ser revendedor, e não o fabricante.",
     "O fornecedor é o CNPJ do vencedor (ni_fornecedor), que pode ser revendedor, e não o fabricante. Os resultados (pn_concentracao.csv) estão no pacote de downloads e não são exibidos em gráfico no painel."),
    ("O bloco 'Como o Estado contrata essas tecnologias e de quem depende' e os principais achados da aba de tecnologias críticas usam duas classificações adicionais, "
     "feitas sobre a mesma base do painel e a mesma classificação das seis categorias; nenhum valor já publicado foi recalculado. Os dados estão em pn_modelo_categoria_ano.csv, "
     "pn_vendedor_categoria_ano.csv, pn_marca_resultados.csv, pn_porte_compras.csv, pn_porte_valor.csv e pn_achados.csv.",
     "Os principais achados da aba de tecnologias críticas e a tabela 2 (marcas) usam duas classificações adicionais, modelo de aquisição e tipo de vendedor, "
     "feitas sobre a mesma base do painel e a mesma classificação das seis categorias; nenhum valor já publicado foi recalculado. Os resultados do modelo de aquisição, "
     "do tipo de vendedor e do porte estão no pacote de downloads (pn_modelo_categoria_ano.csv, pn_vendedor_categoria_ano.csv, pn_porte_compras.csv e pn_porte_valor.csv) "
     "e não são exibidos em gráfico no painel; as marcas estão em pn_marca_resultados.csv e os achados, em pn_achados.csv."),
    ("Consequências: no gráfico 9 só aparecem separadamente", "Consequências: nos resultados do modelo de aquisição (pn_modelo_categoria_ano.csv) só aparecem separadamente"),
    ("No gráfico, seu valor entra em 'Serviços técnicos", "Nos resultados, seu valor entra em 'Serviços técnicos"),
    ("Base: valor homologado nos resultados das seis categorias (a mesma do gráfico 11).", "Base: valor homologado nos resultados das seis categorias (a mesma do gráfico 8)."),
    ("No gráfico, o valor é somado por categoria; na tabela de marcas, cada resultado conta uma vez por marca",
     "No tipo de vendedor (pn_vendedor_categoria_ano.csv), o valor é somado por categoria; na tabela de marcas (tabela 2), cada resultado conta uma vez por marca"),
    ("Os cartões mostram a parcela das compras com vencedor identificado em que alguma empresa do porte venceu e a parcela do valor dos resultados (cada resultado uma vez).",
     "As tabelas de porte (pn_porte_compras.csv e pn_porte_valor.csv) dão a parcela das compras com vencedor identificado em que alguma empresa do porte venceu e a parcela "
     "do valor dos resultados (cada resultado uma vez); estão no pacote de downloads e não são exibidas em gráfico no painel."),
    (" Na linha-resumo da aba de IA, o filtro Acréscimo à licença conta cada compra uma vez, na classe de maior valor; por isso mostra menos compras.", ""),
    ("País de origem do produto ou serviço preenchido em 0,006% dos resultados das seis categorias (2 de 33.422).",
     "País de origem do produto ou serviço preenchido em 0,006% dos resultados das seis categorias (2 de 33.422). Com os dados do PNCP, não é possível medir diretamente "
     "a dependência de tecnologia estrangeira."),
    ("O valor de cada compra é repartido entre as classes pelos itens, a mesma regra do gráfico 9:", "O valor de cada compra é repartido entre as classes pelos itens, a mesma regra do modelo de aquisição (seção 7):"),
    ("Fornecedores, órgãos, o gráfico 12 e a tabela 5 usam o valor homologado nos resultados (compras com vencedor identificado), a mesma base do gráfico 11.",
     "Fornecedores, órgãos, o gráfico 9 e a tabela de cadeias logo abaixo dele usam o valor homologado nos resultados (compras com vencedor identificado), a mesma base do gráfico 8."),
    ("(sem resultado, pelo valor estimado), a mesma regra do gráfico 9. 18 compras", "(sem resultado, pelo valor estimado), a mesma regra do modelo de aquisição. 18 compras"),
    ("A tabela 6 busca a marca", "A tabela 3 busca a marca"),
    ("(regra do gráfico 9)", "(regra do modelo de aquisição)"),
    ("(sem valor na categoria pela regra do gráfico 9)", "(sem valor na categoria pela regra do modelo de aquisição)"),
    ("Como a diferença tem causa identificada, o painel usa como número principal o valor em itens com NCM informado no item e, como limite superior, "
     "o valor com NCM do item mais o tradutor CATMAT→NCM.",
     "Como a diferença tem causa identificada, o indicador por NCM usa como número principal o valor em itens com NCM informado no item e, como limite superior, "
     "o valor com NCM do item mais o tradutor CATMAT→NCM. O indicador está no pacote de downloads (pn_margem_ncm.csv) e não é exibido no painel."),
    ("Tabela 2 (órgãos compradores): logo abaixo do gráfico 11, com o mesmo valor dos resultados e reativa à seleção no gráfico; mostra até 50 órgãos por categoria, em ordem de valor. "
     "Tabela 3 (concentração): uma linha por categoria e ano, porque os índices de concentração não se somam entre anos. Tabela 4 (perfil): uma linha por categoria para o período "
     "filtrado; a mediana usa todas as compras do período e os percentuais são ponderados pelo valor. Os dados por ano estão no CSV de download da aba.", CRIT_T),
    ("Gráfico 11 (Sankey) e tabelas 2 e 3 usam o valor dos resultados", "Gráfico 8 (Sankey) e tabelas 1 e 2 usam o valor dos resultados"),
    ("O indicador por NCM aparece em cartão separado, em reais. Gráficos e tabelas são numerados em sequência, pela ordem de aparição: gráficos 1 a 11 e tabelas 1 a 4 no painel, "
     "tabela 5 nesta metodologia; os instrumentos de política e o porte são apresentados como indicadores, não como gráfico.",
     "O indicador por NCM não é exibido no painel; está no pacote de downloads (pn_margem_ncm.csv). Gráficos e tabelas são numerados em sequência, pela ordem de aparição: "
     "gráficos 1 a 9 e tabelas 1 a 3 no painel, tabela 4 nesta metodologia; a tabela de cadeias da aba de inteligência artificial fica junto do gráfico 9, sem número; "
     "os instrumentos de política são apresentados como indicadores, não como gráfico."),
    ("Aba Tecnologias críticas para a soberania digital: a frase de abertura e os quatro KPIs respondem aos filtros de ano e de categoria.",
     "Aba Tecnologias críticas para a soberania digital: os quatro KPIs respondem aos filtros de ano e de categoria."),
    ("na mesma base do gráfico 11 (resultados com valor positivo;", "na mesma base do gráfico 8 (resultados com valor positivo;"),
    ("A segunda frase da abertura e os KPIs de fornecedores e órgãos consideram apenas", "Os KPIs de fornecedores e órgãos consideram apenas"),
    ("Acima do gráfico 11, a linha-resumo mostra", "Acima do gráfico 8, a linha-resumo mostra"),
    ("Bloco 'Como o Estado contrata essas tecnologias e de quem depende' (gráficos 9 e 10, tabela 1 e indicadores de porte): responde aos filtros de ano e de categoria; "
     "o gráfico 9 usa a regra de soma por categoria, e o gráfico 10, a tabela 1 e os indicadores de porte usam o valor dos resultados (ver seção 7). "
     "Os principais achados, logo abaixo dos KPIs, refletem o período completo e não mudam com os filtros.",
     "Modelo de aquisição, tipo de vendedor, porte e concentração: os resultados sustentam os principais achados e estão no pacote de downloads "
     "(pn_modelo_categoria_ano.csv, pn_vendedor_categoria_ano.csv, pn_porte_compras.csv, pn_porte_valor.csv e pn_concentracao.csv); não são exibidos em gráfico no painel. "
     "Os principais achados, logo abaixo da caixa de abertura, refletem o período completo e não mudam com os filtros."),
    ("Base da tabela 2 (cadeias fornecedor, objeto e órgão comprador), com controle contra a base do gráfico 11.",
     "Base da tabela 1 (cadeias fornecedor, objeto e órgão comprador), com controle contra a base do gráfico 8."),
    ("Compras de cada fluxo do gráfico 11, para a contagem", "Compras de cada fluxo do gráfico 8, para a contagem"),
]
ACH4 = {r["definicao"]: r for r in csv.DictReader(open("tabelas_painel_v4/ia_achado4_fornecedores.csv", encoding="utf-8"), delimiter=";")}
_cn = next(v for k, v in ACH4.items() if k.startswith("CNPJ"))
_rz = next(v for k, v in ACH4.items() if k.startswith("raiz"))
sys.path.insert(0, "scripts_painel_v4")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v4.formatacao import fmt_pct, inteiro  # noqa: E402
P_ACH4 = (f"Achado 4 (concentração dos fornecedores): base de valor dos resultados da tecnologia de IA (Acréscimo à licença, Solução de IA e Outros, sem Capacitação), "
          f"período completo, valores nominais. O fornecedor é o CNPJ completo do vencedor, a mesma definição da linha-resumo do gráfico 9 e dos fornecedores da aba de "
          f"tecnologias críticas: {inteiro(int(_cn['fornecedores']))} fornecedores, e os 10 maiores ficaram com {fmt_pct(float(_cn['pct_10_maiores']))} do valor. "
          f"Contada pela raiz do CNPJ (8 dígitos), critério da versão anterior do achado, a base tem {inteiro(int(_rz['fornecedores']))} fornecedores, porque duas empresas "
          f"venceram com dois estabelecimentos (dois CNPJs com a mesma raiz); a participação dos 10 maiores é a mesma ({fmt_pct(float(_rz['pct_10_maiores']))}). "
          "Dados em ia_achado4_fornecedores.csv e ia_achado4_raizes_com_mais_de_um_cnpj.csv; texto e números dos achados em ia_achados_v4.csv e ia_achados_numeros_v4.csv.")
SCRIPTS_V4 = [
    ("scripts_painel_v4/p4_00_hashes.py", "Conferência dos hashes registrados das versões congeladas 1, 2 e 3 (no início e no fim da versão 4)."),
    ("scripts_painel_v4/p4_01_ia_achados.py", "Principais achados da aba de IA com o texto da versão 4 e a conta do achado 4 (fornecedores pelo CNPJ do vencedor)."),
    ("scripts_painel_v4/p4_02_painel.py", "Painel HTML da versão 4 a partir do HTML da versão 3, metodologia e pacote de downloads."),
    ("scripts_painel_v4/p4_03_verificar_html.py", "Verificação do HTML em Chromium sem internet, em 1440 px e 390 px, e capturas de tela."),
    ("scripts_painel_v4/p4_04_conferencia.py", "Conferência dos números do painel com as tabelas agregadas."),
    ("scripts_painel_v4/p4_05_relatorio_final.py", "Relatório final, congelamento da versão 4 e conferência dos hashes."),
]
for s_, _ in SCRIPTS_V4:
    assert os.path.exists(s_), s_
N0 = 62
md = MD
for de, para in MET:
    md = troca(md, de, para, md.count(de) if de in ("(regra do gráfico 9)",) else 1, "MD: " + de[:70])
md = troca(md, MD.split("\n")[2], "Versão 4, gerada por `scripts_painel_v4/p4_02_painel.py` em " + f"{HOJE:%d/%m/%Y}" +
           " a partir de METODOLOGIA_v3.md (gerada por `scripts_painel_v3/p1_02_painel.py`), com os ajustes de texto, ordem e numeração do painel da versão 4; "
           "nenhum número foi recalculado, exceto o do achado 4 da aba de IA. Os números coincidem com os do painel `painel_soberania_digital_v4.html` "
           "(conferência em `conferencia_numeros_v4.csv`).")
md = troca(md, "`pacote_downloads_v3.zip`", "`pacote_downloads_v4.zip`", 2)
md = troca(md, "### Limitações da aba\n", "### Principais achados da aba (versão 4)\n\n" + P_ACH4 + "\n\n### Limitações da aba\n")
ult = f"- {N0}. scripts_painel_v3/p1_05_relatorio_final.py: Relatório final da entrega, com a conferência dos hashes das versões 1 e 2."
md = troca(md, ult, ult + "".join(f"\n- {N0 + i + 1}. {s_}: {d_}" for i, (s_, d_) in enumerate(SCRIPTS_V4)))
assert "gráfico 1" not in re.sub(r"gráfico [1-9](?!\d)", "", md) and "gráfico 1" not in re.sub(r"gráfico [1-9](?!\d)", "", md.lower())
assert not re.search(r"(?i)gráficos? 1[0-2]|tabelas? [5-7](?!\d)", md), re.findall(r".{60}(?i:gráficos? 1[0-2]|tabelas? [5-7](?!\d)).{20}", md)

i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
met = h[i_met:f_met]
esc = lambda t: html.escape(t)
for de, para in MET:
    if de.startswith("**TABELA 7. "):
        met = troca(met, "TABELA 7", "TABELA 4", 2)
        continue
    met = troca(met, esc(de), esc(para), met.count(esc(de)) if de == "(regra do gráfico 9)" else 1, "HTML: " + de[:70])
met = troca(met, "<h3>Limitações da aba</h3>", f"<h3>Principais achados da aba (versão 4)</h3>\n<p>{esc(P_ACH4)}</p>\n<h3>Limitações da aba</h3>")
ult_h = f"<li>{esc(ult[2:])}</li>"
met = troca(met, ult_h, ult_h + "".join(f"<li>{esc(f'{N0 + i + 1}. {s_}: {d_}')}</li>" for i, (s_, d_) in enumerate(SCRIPTS_V4)))
met = troca(met, "<code>pacote_downloads_v3.zip</code>", "<code>pacote_downloads_v4.zip</code>")
assert not re.search(r"(?i)gráficos? 1[0-2]|tabelas? [5-7](?!\d)", re.sub(r"<[^>]+>", " ", met))
h = h[:i_met] + met + h[f_met:]

# ================================================================== pacote de downloads
z3 = zipfile.ZipFile("pacote_downloads_v3.zip")
LEIAME = z3.read("LEIAME.txt").decode("utf-8")
LEIAME = troca(LEIAME, "Gerado em 02/10/2026 por scripts_painel_v3/p1_02_painel.py.",
               f"Gerado em 02/10/2026 por scripts_painel_v3/p1_02_painel.py (versão 3).\nVersão 4 (Ajuste 4: texto, ordem e layout): gerada em {HOJE:%d/%m/%Y} por "
               "scripts_painel_v4/p4_02_painel.py a partir da versão 3; METODOLOGIA_v4.md substitui METODOLOGIA_v3.md. Os scripts da versão 4 (63 a 68) não regravam "
               "nenhuma saída da versão 3.")
LEIAME = troca(LEIAME, "(Base da tabela 2 (cadeias fornecedor, objeto e órgão comprador), com controle contra a base do gráfico 11.)",
               "(Base da tabela 1 (cadeias fornecedor, objeto e órgão comprador), com controle contra a base do gráfico 8.)")
LEIAME = troca(LEIAME, "(Compras de cada fluxo do gráfico 11, para", "(Compras de cada fluxo do gráfico 8, para")
l62 = "62. scripts_painel_v3/p1_05_relatorio_final.py  (Relatório final da entrega, com a conferência dos hashes das versões 1 e 2.)"
LEIAME = troca(LEIAME, l62, l62 + "".join(f"\n{N0 + i + 1}. {s_}  ({d_})" for i, (s_, d_) in enumerate(SCRIPTS_V4)))
LEIAME = troca(LEIAME, "Tabelas agregadas (pasta tabelas_agregadas/):", "Tabelas novas da versão 4: ia_achados_v4.csv, ia_achados_numeros_v4.csv, ia_achado4_fornecedores.csv e "
               "ia_achado4_raizes_com_mais_de_um_cnpj.csv (p4_01).\nTabelas agregadas (pasta tabelas_agregadas/):")
SCR4 = sorted(["scripts_painel_v4/" + x for x in os.listdir("scripts_painel_v4") if x.endswith(".py")])
TAB4 = sorted(["tabelas_painel_v4/" + x for x in os.listdir("tabelas_painel_v4") if x.endswith(".csv")])
ler_b = lambda c: open(c, "rb").read()


def zip_bytes(pares):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in pares:
            z.writestr(nome, conteudo)
    return buf.getvalue()


def interno(nome_zip, extras):
    zz = zipfile.ZipFile(io.BytesIO(z3.read(nome_zip)))
    pares = [("LEIAME.txt", LEIAME)] + [(n, zz.read(n)) for n in zz.namelist() if n != "LEIAME.txt"]
    nomes = {n for n, _ in pares}
    for nome, c in extras:
        assert nome not in nomes, nome
        pares.append((nome, ler_b(c)))
    return zip_bytes(pares)


scripts_zip = interno("scripts.zip", [(s_, s_) for s_ in SCR4])
tabelas_zip = interno("tabelas_agregadas.zip", [(os.path.basename(t), t) for t in TAB4])
with zipfile.ZipFile("pacote_downloads_v4.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("LEIAME.txt", LEIAME)
    for n in z3.namelist():
        if n.startswith(("scripts/", "tabelas_agregadas/")):
            z.writestr(n, z3.read(n))
    for s_ in SCR4:
        z.writestr("scripts/" + s_, ler_b(s_))
    for t in TAB4:
        z.writestr("tabelas_agregadas/" + os.path.basename(t), ler_b(t))
    z.writestr("scripts.zip", scripts_zip)
    z.writestr("tabelas_agregadas.zip", tabelas_zip)
    z.writestr("METODOLOGIA_v4.md", md)
# zips embutidos no HTML (botoes da aba Metodologia): os mesmos do pacote v4
m_zip = re.search(r'const ZIP = \{scripts: "([A-Za-z0-9+/=]+)", tabelas: "([A-Za-z0-9+/=]+)"\};', h)
assert m_zip
h = h[:m_zip.start()] + f'const ZIP = {{scripts: "{base64.b64encode(scripts_zip).decode()}", tabelas: "{base64.b64encode(tabelas_zip).decode()}"}};' + h[m_zip.end():]

open("painel_soberania_digital_v4.html", "w", encoding="utf-8").write(h)
open("METODOLOGIA_v4.md", "w", encoding="utf-8").write(md)
print("ok", f"{os.path.getsize('painel_soberania_digital_v4.html') / 1e6:.1f} MB", f"pacote {os.path.getsize('pacote_downloads_v4.zip') / 1e6:.1f} MB")
