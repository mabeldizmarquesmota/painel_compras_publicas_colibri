"""Painel v5, etapa 2: painel HTML, metodologia e pacote de downloads da versao 5 (Ajuste 5: revisao final de texto, ordem e layout,
mais as correcoes do grafico 9).

Executar a partir de Processado/, depois de p5_01:  python scripts_painel_v5/p5_02_painel.py
Entradas (somente leitura): painel_soberania_digital_v4.html (copia de partida), METODOLOGIA_v4.md, pacote_downloads_v4.zip,
  tabelas_painel_v5/*.csv (p5_01) e os scripts de scripts_painel_v5/.
Regras: nenhum numero e digitado nem recalculado; os numeros continuam saindo dos dados ja embutidos no HTML. Cada mudanca e uma
  substituicao de texto com contagem conferida: se o trecho de origem nao aparecer o numero de vezes esperado, o script para.
Saidas: painel_soberania_digital_v5.html, METODOLOGIA_v5.md, pacote_downloads_v5.zip.
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
sys.path.insert(0, "scripts_painel_v5")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v5.formatacao import inteiro, mi  # noqa: E402

HOJE = datetime.date.today()
T5 = "tabelas_painel_v5/"


def troca(txt, old, new, n=1, rot=None):
    c = txt.count(old)
    assert c == n, f"{rot or old[:100]!r}: {c} ocorrências, esperado {n}"
    return txt.replace(old, new)


def corta(txt, ini, fim, novo="", incluir_fim=False):
    assert txt.count(ini) == 1, f"marcador inicial {ini[:80]!r}: {txt.count(ini)}"
    a = txt.find(ini)
    b = txt.find(fim, a)
    assert b > a, f"marcador final {fim[:80]!r}"
    if incluir_fim:
        b += len(fim)
    return txt[:a] + novo + txt[b:]


def balanceado(txt, a, tag):
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


def icone(txt, chave):
    """(inicio, fim) do icone i com data-i=chave (uma ocorrencia na marcacao)."""
    assert txt.count(f"data-i='{chave}'") == 1, chave
    a = txt.rfind("<span class='info'", 0, txt.find(f"data-i='{chave}'"))
    return a, balanceado(txt, a, "span")


def no_icone(txt, chave, de, para, n=1):
    a, b = icone(txt, chave)
    return txt[:a] + troca(txt[a:b], de, para, n, f"i {chave}: {de[:60]}") + txt[b:]


ler5 = lambda n: list(csv.DictReader(open(T5 + n, encoding="utf-8"), delimiter=";"))
h = open("painel_soberania_digital_v4.html", encoding="utf-8").read()

# ================================================================== estilo
h = troca(h, ".texto-exec{font-size:16px;margin:22px 0 12px;color:#1F2937}", ".texto-exec{font-size:14px;margin:22px 0 12px;color:#4B5563}")
h = troca(h, ".nota-tab{font-size:14px;color:#374151;margin:14px 0 4px}", ".nota-tab{font-size:14px;color:#4B5563;margin:14px 0 4px}")
h = troca(h, "h2.sec.tit-laranja{color:#E3972B;font-weight:400;font-size:28px;margin:4px 0 16px}",
          "h2.sec.tit-laranja,#aba-metodologia h2.sec.tit-laranja{color:#E3972B;font-weight:400;font-size:28px;margin:4px 0 16px}")
# graficos de barras e de linha cerca de 25% mais baixos que na v4; Sankeys sem mudanca
h = troca(h, ".area{position:relative;width:100%;height:247px}", ".area{position:relative;width:100%;height:185px}")
for de, para in (('style="height:182px"><canvas id="g2">', 'style="height:137px"><canvas id="g2">'),
                 ('style="height:156px"><canvas id="g3">', 'style="height:117px"><canvas id="g3">'),
                 ('style="height:247px" id="g4-area">', 'style="height:185px" id="g4-area">'),
                 ('style="height:260px"><canvas id="g5">', 'style="height:195px"><canvas id="g5">'),
                 ('style="height:208px"><canvas id="g6">', 'style="height:156px"><canvas id="g6">'),
                 ('style="height:286px" id="g7-area">', 'style="height:215px" id="g7-area">')):
    h = troca(h, de, para)
h = troca(h, "(altura || Math.max(104, 30 * nomes.length + 20))", "(altura || Math.max(78, 22 * nomes.length + 16))")
h = troca(h, 'Math.max(143, 40 * mods.length + 40) + "px"', 'Math.max(107, 30 * mods.length + 30) + "px"')

# ================================================================== aba Sobre
h = troca(h, '\n  <p class="nota-kpi">Use as abas acima para explorar os dados. A aba Compras públicas mostra o conjunto das compras; a aba Tecnologias críticas para a '
          'soberania digital detalha as seis categorias, seus fornecedores e compradores. A aba Metodologia descreve os procedimentos e os critérios utilizados no painel.</p>', "")

# ================================================================== aba Compras publicas
h = troca(h, '<h2 class="sec tit-laranja">Compras públicas</h2>', '<h2 class="sec tit-laranja">Panorama das compras públicas</h2>')
h = troca(h, "<p>A análise mostra quanto o poder público contratou via PNCP, em que ritmo e por quais modalidades. O valor corresponde ao total homologado de cada compra, "
          "registrado uma única vez no ano de publicação. Os indicadores anuais somam as compras publicadas em cada ano, enquanto os indicadores do período refletem os anos "
          "selecionados no filtro.</p>",
          "<p>Mostra quanto o poder público contratou via PNCP, em que ritmo e por quais modalidades. O valor corresponde ao total homologado de cada compra, "
          "contabilizada uma vez no ano de publicação.</p>")
a, b = icone(h, "cp_compras")
i_cp = re.sub(r"<div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Nota metodológica:</b> Das 875\.682 compras publicadas.*?</div>", "", h[a:b], count=1)
i_cp = re.sub(r"<div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Exemplo de leitura:</b> Em 2024 e 2025, o setor público registrou cerca de 307 mil compras por ano\.</div>", "", i_cp, count=1)
assert "Das 875.682" not in i_cp and "307 mil" not in i_cp and "Como interpretar" in i_cp
h = h[:a] + i_cp + h[b:]
a, b = icone(h, "cp_valor")
i_cv = re.sub(r"<div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Exemplo de leitura:</b> <span class='ex-din' data-ex='cp_valor'>De cada R\$ 100.*?</span></div>", "", h[a:b], count=1)
assert "De cada R$ 100" not in i_cv and "Como interpretar" in i_cv
h = h[:a] + i_cv + h[b:]
# grafico 1: so o total do periodo e a frase de cobertura parcial
h = corta(h, '  let t1 = "";\n  if (!porAno.length || (qtd ? nHom : total) === 0) t1 = "Não há compras homologadas no recorte selecionado.";',
          '  $("g1-txt").textContent = t1;',
          '  const parc = notaParciais(anos);\n'
          '  const t1 = !porAno.length || (qtd ? nHom : total) === 0 ? "Não há compras homologadas no recorte selecionado."\n'
          '    : (qtd ? `Foram homologadas ${inteiro(nHom)} compras em ${per}` : `O valor global homologado somou ${bi(total)} em ${per}`) + (parc ? ";" + parc : ".");\n')
h = troca(h, "  const cmp = anosComp(s), g = a => porAno.find(p => p.a === a);\n", "")
# graficos 2 e 3: sem a frase do valor sem esfera ou poder identificado
h = corta(h, "    const niItem = itens.find(x => x.n === ni);\n", '    $(id + "-txt").textContent = !inf.length ?')
h = troca(h, '$(id + "-txt").textContent = !inf.length ? txtNi + "Não há valor homologado com "', '$(id + "-txt").textContent = !inf.length ? "Não há valor homologado com "')
h = troca(h, "      txtNi + `${art[0].toUpperCase() + art.slice(1)} ${nomeMin(inf[0].n)} respondeu por", "      `${art[0].toUpperCase() + art.slice(1)} ${nomeMin(inf[0].n)} respondeu por")

# ================================================================== aba Tecnologias criticas para a soberania digital
ini_sd = '<section class="aba-conteudo" id="aba-soberania">'
a = h.find(ini_sd)
b = h.find("</section>", a) + len("</section>")
sec = h[a:b]
cab = bloco(sec, 'id="sd-csv"', '<div class="cab-sec"')
intro = bloco(sec, '<div class="cats">', '<div class="card intro-sob')
cats = intro[intro.find('<div class="cats">'):balanceado(intro, intro.find('<div class="cats">'), "div")]
CATS_I = re.findall(r"<span class='cat-nome'>([^<]+)</span><span class='info'[^>]*>i<span class='tt'><div class='tt-txt'><b class='tt-ex'>Conceito:</b> ([^<]+)</div>"
                    r"<div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Palavras-chave:</b> [^<]+</div><ul class='tt-lista'>(.*?)</ul><div class='tt-sep'></div>"
                    r"<div class='tt-txt'><b class='tt-ex'>Verificação:</b> ([^<]+)</div>", cats)
assert len(CATS_I) == 6
DIC = [(n, c, [html.unescape(x) for x in re.findall(r"<li>(.*?)</li>", l)], v) for n, c, l, v in CATS_I]
intro = troca(intro, "<p>Esta seção apresenta as compras públicas de tecnologias críticas para a soberania digital, entendida como a capacidade do Estado de controlar dados, "
              "infraestrutura e tecnologias essenciais ao seu funcionamento.</p>",
              "<p>Reúne as compras públicas de tecnologias críticas para a soberania digital, considerando dados, infraestrutura e tecnologias essenciais ao Estado.</p>")
intro = troca(intro, '\n    <p class="sel-tit">Tecnologias selecionadas:</p>\n    ' + cats, "")
kpis = bloco(sec, 'id="sd-kpis"', '<div class="kpis"')
g5, g6, g7 = bloco(sec, 'id="g5"'), bloco(sec, 'id="g6"'), bloco(sec, 'id="g7"')
g5 = troca(g5, "</div><div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Exemplo de leitura:</b>",
           "</div><div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Nota metodológica:</b> Conceito, palavras-chave e verificação de cada categoria: "
           "ver Dicionário de termos por categoria, na aba Metodologia.</div><div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Exemplo de leitura:</b>")
sk = bloco(sec, 'id="sankey"')
sk = troca(sk, '    <p class="sk-dica">Escolha a categoria nos botões, no nó central ou num fluxo; clique num fornecedor ou órgão para ver só os fluxos desse nó. '
           'Passe o mouse para ver quem vendeu, o que vendeu, quem comprou, o valor e o número de compras.</p>\n', "")
FRASE_G8 = ("Os valores deste gráfico são o valor dos resultados (o homologado para cada fornecedor vencedor) e podem diferir dos gráficos por categoria, "
            "que usam o valor homologado das compras.")
sk = troca(sk, "por isso os lados somam mais que o total de compras distintas mostrado no resumo.</div>",
           f"por isso os lados somam mais que o total de compras distintas mostrado no resumo. {FRASE_G8}</div>")
t1 = troca(bloco(sec, 'id="t1"'), '\n    <p class="nota-tab" id="t1-nota"></p>', "")
tm = troca(bloco(sec, 'id="tm"'), '\n    <p class="nota-tab" id="tm-nota"></p>', "")
g10 = bloco(sec, 'id="ind-cartoes"')
g10 = troca(g10, '\n    <p class="texto-exec" id="g10-nota"></p>', "")
for k in ("prev", "apl", "ppb"):
    g10 = troca(g10, f'<div class="rot" id="ind-{k}-p"></div>', "")
g10 = troca(g10, "aria-label='Como interpretar' data-i='g10'>", "aria-label='Como interpretar' data-i='g10' data-larg='480px'>")
g10 = troca(g10, "(itens), margem aplicada no resultado (resultados) e exigência de PPB (itens).</div>",
            "(itens), margem aplicada no resultado (resultados) e exigência de PPB (itens).</div><div class='tt-sep'></div>"
            "<div class='tt-txt'><b class='tt-ex'>Nota metodológica:</b> <span id='g10-nota'></span></div><div class='tt-sep'></div>"
            "<div class='tt-txt'><b class='tt-ex'>Encomenda tecnológica e CPSI:</b> <span id='nota-encomenda'></span></div>")
assert sec.count('<div class="card"><b>Nota:</b> <span id="nota-encomenda"></span></div>') == 1
nova = f"""{ini_sd}
  {cab}
  {intro}
  {kpis}

  <div class="divisor"></div>
  <div class="bloco-tit">Composição das compras por categoria tecnológica</div>
  {g5}
  {g6}

  <div class="divisor"></div>
  <div class="bloco-tit">Modalidade de contratação</div>
  {g7}

  <div class="bloco-tit">Fornecedores, tecnologias e órgãos compradores</div>
  {sk}
  {t1}
  {tm}

  <div class="bloco-tit">Instrumentos de política pública associados às compras</div>
  {g10}

  <div class="divisor"></div>
  <div class="bloco-tit">Síntese dos principais achados</div>
  <div class="achados" id="achados"></div>
</section>"""
h = h[:a] + nova + h[b:]
h = troca(h, "`Maiores cadeias: fornecedor → objeto → órgão, ${per}${sel}`", "`Principais relações entre fornecedores, objetos e órgãos compradores, ${per}${sel}`")
h = corta(h, '  $("t1-nota").textContent = `Até 50 cadeias por categoria', "\n}\n$(\"t1-csv\").onclick")
h = corta(h, '  $("tm-nota").textContent = `${inteiro(rr.length)} das ${inteiro(todas.length)} marcas citadas', "  const top = rr.slice().sort(")
h = troca(h, '    $("ind-" + id + "-p").textContent = campo(pp); });', "  });")
h = troca(h, '  reg("ind_preenchimento", [p1, p2, p3].map(campo).join("|"));\n', "")
h = troca(h, "  const campo = p => `campo preenchido em ${fmtPct(100 * p[2] / p[1])} dos registros`;\n", "")
h = troca(h, '  [["prev", 0, p1, "do valor"], ["apl", 1, p2, ""], ["ppb", 2, p3, ""]].forEach(([id, k, pp, suf]) => {',
          '  [["prev", 0, "do valor"], ["apl", 1, ""], ["ppb", 2, ""]].forEach(([id, k, suf]) => {')

# ================================================================== aba Inteligencia artificial
ini_ia = '<section class="aba-conteudo" id="aba-ia">'
a = h.find(ini_ia)
b = h.find("</section>", a) + len("</section>")
sec = h[a:b]
cab = bloco(sec, 'id="ia-csv"', '<div class="cab-sec"')
sk_ia = bloco(sec, 'id="ia-sankey"')
marcas = bloco(sec, 'id="ia-marcas"')
NUVEM_I = ("Nuvem com serviços de IA: contratos de nuvem cujo objeto cita serviços de inteligência artificial (por exemplo, créditos de nuvem com acesso a modelos de IA). "
           "O valor é o do contrato inteiro; o PNCP não permite separar a parte gasta com IA.")
sk_ia = troca(sk_ia, "que inclui compras sem resultado publicado.</div>",
              f"que inclui compras sem resultado publicado.</div><div class='tt-sep'></div><div class='tt-txt'>{NUVEM_I}</div>")
nova = f"""{ini_ia}
  {cab}
  <div class="card texto-abertura">
    <p>Apresenta uma análise específica das compras públicas de Inteligência Artificial, com classificação dos tipos de solução, fornecedores, marcas mencionadas e modelos de aquisição.</p>
  </div>

  {sk_ia}

  {marcas}

  <div class="bloco-tit">Principais achados das compras públicas de IA</div>
  <div class="achados" id="ia-achados"></div>
</section>"""
h = h[:a] + nova + h[b:]
h = troca(h, '<th>Principais vendedores</th>', "<th>Principais vendedores/revendedores</th>")
h = no_icone(h, "ia_marcas", "Principais vendedores: CNPJ dos vencedores", "Principais vendedores/revendedores: CNPJ dos vencedores")
# grafico 9: a tabela de cadeias reage aos botoes e aos cliques no diagrama (fornecedor, tipo de objeto, orgao e fluxo), como no grafico 8
h = troca(h, 'const set = new Set(s.sk.ids), k = s.sk.tipo === "f" ? 3 : 4; return rows.filter(r => set.has(r[k])); }',
          'const set = new Set(s.sk.ids), k = s.sk.tipo === "f" ? 3 : s.sk.tipo === "o" ? 4 : 2; return rows.filter(r => set.has(r[k])); }')
h = troca(h, 'function clicaNo(d){ if (d.id[0] === "t") return; const tipo = d.id[0], T = tipo === "f" ? F : O;',
          'function clicaNo(d){ const tipo = d.id[0]; if (tipo === "t") { E.ia.sk = {tipo, ids: [+d.id.slice(1)], nome: d.nome}; renderIA(); return; }\n'
          '    const T = tipo === "f" ? F : O;')
h = troca(h, '.on("mouseleave", () => { escondeTT(); lk.attr("stroke-opacity", 0.35); });\n  const nd = svg.append("g").selectAll("g").data(g.nodes).join("g");\n  nd.append("rect").attr("x", d => d.x0).attr("y", d => d.y0).attr("width", d => d.x1 - d.x0).attr("height", d => Math.max(1, d.y1 - d.y0))\n    .attr("fill", d => d.id[0] === "t" ? corT(',
          '.on("mouseleave", () => { escondeTT(); lk.attr("stroke-opacity", 0.35); })\n'
          '    .on("click", (ev, d) => { escondeTT(); E.ia.sk = {tipo: "t", ids: [d.tipo], nome: IA.tipos[d.tipo]}; renderIA(); });\n'
          '  const nd = svg.append("g").selectAll("g").data(g.nodes).join("g");\n  nd.append("rect").attr("x", d => d.x0).attr("y", d => d.y0).attr("width", d => d.x1 - d.x0).attr("height", d => Math.max(1, d.y1 - d.y0))\n    .attr("fill", d => d.id[0] === "t" ? corT(')
h = troca(h, '$("ia-sel").textContent = s.sk ? `Seleção: ${s.sk.tipo === "f" ? "fornecedor" : "órgão"} ${s.sk.nome}` : "";',
          '$("ia-sel").textContent = s.sk ? `Seleção: ${s.sk.tipo === "f" ? "fornecedor" : s.sk.tipo === "o" ? "órgão" : "tipo de objeto"} ${s.sk.nome}` : "";')

# conferencia (p5_03): total da base da tabela de cadeias (todas as cadeias do recorte e da selecao, nao so as 50 exibidas)
CLS_JS = "  const cls = iaCls(s.f).filter(c => todas.some(x => x.c === c));\n"
h = troca(h, CLS_JS, CLS_JS + "  window.__iaTab = {valor: soma(todas.map(x => x.v)), compras: new Set(rows.map(r => r[0])).size, cadeias: todas.length, "
          "classes: [...new Set(rows.map(r => r[1]))], tipos: [...new Set(rows.map(r => r[2]))]};\n")

# ================================================================== aba Metodologia
h = troca(h, '<div class="eyebrow2">Procedimentos e critérios</div>\n  <h2 class="sec">Metodologia</h2>', '<h2 class="sec tit-laranja">Procedimentos metodológicos</h2>')

# ================================================================== dados embutidos
i_d = h.find("const D = ") + len("const D = ")
f_d = h.find(";\nconst ZIP", i_d)
D = json.loads(h[i_d:f_d].replace("<\\/", "</"))
tp = D["ia"]["tipos"]
assert tp.count("Nuvem/cloud broker") == 1 and tp.count("Outros objetos") == 1
tp[tp.index("Nuvem/cloud broker")] = "Nuvem com serviços de IA"
tp[tp.index("Outros objetos")] = "Capacitação"  # o tipo so reune compras da classe Capacitacao (p5_01)
i_out = tp.index("Capacitação")
assert all(D["ia"]["classes"][c[1]] == "Capacitação" for c in D["ia"]["compras"] if c[2] == i_out)
assert all(c[2] == i_out for c in D["ia"]["compras"] if D["ia"]["classes"][c[1]] == "Capacitação")
D["ia"]["achados"] = [[r["achado"], r["titulo"], r["texto"]] for r in ler5("ia_achados_v5.csv")]
for k in ("nota", "exemplo"):
    D["I"]["cp_compras"].pop(k, None)
D["I"]["cp_valor"].pop("exemplo", None)
D["ex"].pop("cp_valor", None)
D["I"]["g9"]["como"] = D["I"]["g9"]["como"] + " " + FRASE_G8
D["I"]["g5"]["nota"] = "Conceito, palavras-chave e verificação de cada categoria: ver Dicionário de termos por categoria, na aba Metodologia."
D["I"]["ia_marcas"]["como"] = troca(D["I"]["ia_marcas"]["como"], "Principais vendedores:", "Principais vendedores/revendedores:")
h = h[:i_d] + json.dumps(D, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/") + h[f_d:]

# ================================================================== metodologia
NUV = ler5("ia_nuvem_servicos_ia.csv")
CAPR = ler5("ia_capacitacao_reconciliacao.csv")
fv = lambda x: mi(float(x))
P_DIC_INTRO = ("Conceito, palavras-chave e verificação de cada uma das seis categorias; o ícone i do gráfico 5 "
               "remete a esta seção. As palavras-chave estão em linguagem comum; as expressões exatas estão em dicionario_termos.csv, no pacote de downloads.")
P_DIC = [f"{n}. Conceito: {c}. Palavras-chave: {'; '.join(t)}. Verificação: {v}" for n, c, t, v in DIC]
P_NUV = (f"{NUVEM_I} No painel, o tipo de objeto antes chamado 'Nuvem/cloud broker' (nome mantido nas tabelas do pacote, como ia_base.csv e ia_resultados.csv) "
         f"aparece como 'Nuvem com serviços de IA'. São {inteiro(int(NUV[0]['compras']))} compras, com {fv(NUV[0]['valor_nominal'])} de valor homologado na aba "
         f"(período completo, valores nominais); no gráfico 9, que usa o valor dos resultados, são {inteiro(int(NUV[1]['compras']))} compras com vencedor identificado "
         f"e {fv(NUV[1]['valor_nominal'])} (ia_nuvem_servicos_ia.csv).")
P_G9 = ("Correções da versão 5. (1) Capacitação: o dicionário de tipos de objeto põe as compras de capacitação no tipo 'Outros objetos', e o nó central do gráfico 9 mostrava "
        "esse nome com o botão Capacitação. Como o tipo só reúne compras da classe Capacitação, no painel ele passou a se chamar 'Capacitação' (gráfico, legenda, tooltips, "
        "tabela de cadeias e CSV), sem reclassificar nenhuma compra; nenhuma compra de Capacitação aparece em Outros. "
        f"A classe tem {inteiro(int(CAPR[0]['compras']))} compras e {fv(CAPR[0]['valor_nominal'])} na tabela de classes; o gráfico 9 usa o valor dos resultados e mostra as "
        f"{inteiro(int(CAPR[1]['compras']))} compras com vencedor identificado ({fv(CAPR[1]['valor_nominal'])}); as outras {inteiro(int(CAPR[2]['compras']))} compras "
        "não têm resultado com vencedor publicado (ia_capacitacao_reconciliacao.csv). (2) Tabela de cadeias: o clique no nó de tipo de objeto e o clique num fluxo não "
        "tinham ação, e a tabela não acompanhava essas seleções. Agora, como no gráfico 8, os botões de classe e os cliques em fornecedor, tipo de objeto, órgão ou fluxo "
        "filtram o diagrama e a tabela de cadeias logo abaixo; o botão Limpar seleção volta ao recorte do filtro.")
MET = [  # (de, para): aplicados ao METODOLOGIA_v5.md e, escapados, a metodologia dentro do HTML
    ("compras de capacitação ficam em 'Outros objetos'.", "compras de capacitação ficam em 'Outros objetos', que no painel aparece com o nome 'Capacitação' (o tipo só reúne compras dessa classe)."),
    ("| Nuvem/cloud broker |", "| Nuvem com serviços de IA (nas tabelas do pacote: Nuvem/cloud broker) |"),
    ("| Outros objetos |", "| Outros objetos (no painel: Capacitação) |"),
    ("### Principais achados da aba (versão 4)", "### Principais achados da aba"),
    ("texto e números dos achados em ia_achados_v4.csv e ia_achados_numeros_v4.csv.",
     "texto e números dos achados em ia_achados_v4.csv e ia_achados_numeros_v4.csv. Na versão 5, os achados 1 e 3 são qualitativos e os números dos achados 2 e 4 estão em "
     "ia_achados_v5.csv e ia_achados_numeros_v5.csv; a síntese fica no fim da aba."),
    ("Tabela 1 (cadeias fornecedor → objeto → órgão): logo abaixo", "Tabela 1 (Principais relações entre fornecedores, objetos e órgãos compradores): logo abaixo"),
    ("em gráficos, legendas, cartões, filtros e tabelas.", "em gráficos, legendas, filtros e tabelas."),
    ("(cartões numéricos no bloco 'O Estado usa o poder de compra a favor da oferta nacional?'):", "(cartões numéricos no bloco 'Instrumentos de política pública associados às compras'):"),
    ("O indicador por NCM não é exibido no painel; está no pacote de downloads (pn_margem_ncm.csv).",
     "O preenchimento dos três campos (sempre verdadeiro ou falso) e a busca por encomenda tecnológica e CPSI estão no ícone i desses indicadores. "
     "O indicador por NCM não é exibido no painel; está no pacote de downloads (pn_margem_ncm.csv)."),
    ("Os principais achados, logo abaixo da caixa de abertura, refletem o período completo", "A síntese dos principais achados, no fim da aba, reflete o período completo"),
    ("Encomenda tecnológica e CPSI: busca por menção explícita no amparo legal (nome e descrição), na modalidade e no objeto.",
     "Encomenda tecnológica e CPSI: busca por menção explícita no amparo legal (nome e descrição), na modalidade e no objeto; o resultado aparece no ícone i dos indicadores "
     "de instrumentos de política."),
    ("Precisão exibida nos cartões: amostra final", "Precisão informada no Dicionário de termos por categoria: amostra final"),
    ("Os valores dos tooltips saem da tabela fornecedor × categoria × órgão (pn_fluxo.csv).",
     "Os valores dos tooltips saem da tabela fornecedor × categoria × órgão (pn_fluxo.csv). Como o diagrama usa o valor dos resultados, seus valores podem diferir dos gráficos "
     "por categoria, que usam o valor homologado das compras (nota no ícone i do gráfico 8). Aba Inteligência artificial: os botões de classe e os cliques no gráfico 9 "
     "(fornecedor, tipo de objeto, órgão ou fluxo) filtram o diagrama e a tabela de cadeias logo abaixo, como no gráfico 8."),
]
SCRIPTS_V5 = [
    ("scripts_painel_v5/p5_00_hashes.py", "Conferência dos hashes registrados das versões congeladas 1 a 4 (no início e no fim da versão 5)."),
    ("scripts_painel_v5/p5_01_ia_achados.py", "Achados da aba de IA com o texto da versão 5, números de Nuvem com serviços de IA e reconciliação da classe Capacitação."),
    ("scripts_painel_v5/p5_02_painel.py", "Painel HTML da versão 5 a partir do HTML da versão 4, metodologia e pacote de downloads."),
    ("scripts_painel_v5/p5_03_verificar_html.py", "Verificação do HTML em Chromium sem internet, em 1440 px e 390 px, interação do gráfico 9 e capturas de tela."),
    ("scripts_painel_v5/p5_04_conferencia.py", "Conferência dos números do painel com as tabelas agregadas."),
    ("scripts_painel_v5/p5_05_relatorio_final.py", "Relatório final, congelamento da versão 5 e conferência dos hashes."),
]
for s_, _ in SCRIPTS_V5:
    assert os.path.exists(s_), s_
MD = open("METODOLOGIA_v4.md", encoding="utf-8").read()
md = MD
for de, para in MET:
    md = troca(md, de, para, 1, "MD: " + de[:70])
md = troca(md, MD.split("\n")[2], f"Versão 5, gerada por `scripts_painel_v5/p5_02_painel.py` em {HOJE:%d/%m/%Y} a partir de METODOLOGIA_v4.md, com os ajustes de texto, ordem e "
           "layout do painel da versão 5 e as correções do gráfico 9; nenhuma classificação foi refeita. Os números coincidem com os do painel "
           "`painel_soberania_digital_v5.html` (conferência em `conferencia_numeros_v5.csv`).")
md = troca(md, "`pacote_downloads_v4.zip`", "`pacote_downloads_v5.zip`", 2)
md = troca(md, "\n## 4. Teste de robustez\n", "\n### Dicionário de termos por categoria\n\n" + P_DIC_INTRO + "\n\n" + "\n\n".join(P_DIC) + "\n\n## 4. Teste de robustez\n")
md = troca(md, "\n### Marcas de IA citadas\n", "\n" + P_NUV + "\n\n### Correções do gráfico 9\n\n" + P_G9 + "\n\n### Marcas de IA citadas\n")
N0 = 68
ult = f"- {N0}. scripts_painel_v4/p4_05_relatorio_final.py: Relatório final, congelamento da versão 4 e conferência dos hashes."
md = troca(md, ult, ult + "".join(f"\n- {N0 + i + 1}. {s_}: {d_}" for i, (s_, d_) in enumerate(SCRIPTS_V5)))

i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
met = h[i_met:f_met]
esc = html.escape
wbr = lambda t: re.sub(r"([_/.])(?=[A-Za-z])", r"\g<1><wbr>", esc(t))  # celulas de tabela da metodologia (p1_02: quebra)
for de, para in MET:
    if de.startswith("| "):
        de_c, para_c = de.strip("| "), para.strip("| ")
        met = troca(met, f"<td>{wbr(de_c)}</td>", f"<td>{wbr(para_c)}</td>", 1, "HTML: " + de_c)
    elif de.startswith("### "):
        met = troca(met, f"<h3>{esc(de[4:])}</h3>", f"<h3>{esc(para[4:])}</h3>", 1, "HTML: " + de)
    else:
        met = troca(met, esc(de), esc(para), 1, "HTML: " + de[:70])
met = troca(met, "\n<h2>4. Teste de robustez</h2>", f"\n<h3>Dicionário de termos por categoria</h3>\n<p>{esc(P_DIC_INTRO)}</p>\n" +
            "".join(f"<p><b>{esc(n)}.</b> {esc(x[len(n) + 2:])}</p>\n" for (n, _, _, _), x in zip(DIC, P_DIC)) + "<h2>4. Teste de robustez</h2>")
met = troca(met, "\n<h3>Marcas de IA citadas</h3>", f"\n<p>{esc(P_NUV)}</p>\n<h3>Correções do gráfico 9</h3>\n<p>{esc(P_G9)}</p>\n<h3>Marcas de IA citadas</h3>")
ult_h = f"<li>{esc(ult[2:])}</li>"
met = troca(met, ult_h, ult_h + "".join(f"<li>{esc(f'{N0 + i + 1}. {s_}: {d_}')}</li>" for i, (s_, d_) in enumerate(SCRIPTS_V5)))
met = troca(met, "<code>pacote_downloads_v4.zip</code>", "<code>pacote_downloads_v5.zip</code>")
h = h[:i_met] + met + h[f_met:]
for t in ("cartões da aba", "cartões das categorias", "exibida nos cartões", "Tecnologias selecionadas", "Maiores cadeias", "O que o Estado compra", "De quem o Estado compra", "oferta nacional", "Procedimentos e critérios"):
    assert t not in md and t not in re.sub(r"<[^>]+>", "", met), t

# ================================================================== pacote de downloads
z4 = zipfile.ZipFile("pacote_downloads_v4.zip")
LEIAME = z4.read("LEIAME.txt").decode("utf-8")
LEIAME = troca(LEIAME, "METODOLOGIA_v4.md substitui METODOLOGIA_v3.md. Os scripts da versão 4 (63 a 68) não regravam nenhuma saída da versão 3.",
               "METODOLOGIA_v4.md substitui METODOLOGIA_v3.md. Os scripts da versão 4 (63 a 68) não regravam nenhuma saída da versão 3.\n"
               f"Versão 5 (Ajuste 5: revisão final de texto, ordem e layout e correções do gráfico 9): gerada em {HOJE:%d/%m/%Y} por scripts_painel_v5/p5_02_painel.py a partir "
               "da versão 4; METODOLOGIA_v5.md substitui METODOLOGIA_v4.md. Os scripts da versão 5 (69 a 74) não regravam nenhuma saída das versões anteriores. "
               "No painel, o tipo de objeto 'Nuvem/cloud broker' das tabelas aparece como 'Nuvem com serviços de IA', e o tipo 'Outros objetos' (só compras de capacitação), como 'Capacitação'.")
l68 = f"{N0}. scripts_painel_v4/p4_05_relatorio_final.py  (Relatório final, congelamento da versão 4 e conferência dos hashes.)"
LEIAME = troca(LEIAME, l68, l68 + "".join(f"\n{N0 + i + 1}. {s_}  ({d_})" for i, (s_, d_) in enumerate(SCRIPTS_V5)))
LEIAME = troca(LEIAME, "Tabelas agregadas (pasta tabelas_agregadas/):", "Tabelas novas da versão 5: ia_achados_v5.csv, ia_achados_numeros_v5.csv, ia_nuvem_servicos_ia.csv e "
               "ia_capacitacao_reconciliacao.csv (p5_01).\nTabelas agregadas (pasta tabelas_agregadas/):")
SCR5 = sorted("scripts_painel_v5/" + x for x in os.listdir("scripts_painel_v5") if x.endswith(".py"))
TAB5 = sorted(T5 + x for x in os.listdir(T5) if x.endswith(".csv"))
ler_b = lambda c: open(c, "rb").read()


def zip_bytes(pares):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in pares:
            z.writestr(nome, conteudo)
    return buf.getvalue()


def interno(nome_zip, extras):
    zz = zipfile.ZipFile(io.BytesIO(z4.read(nome_zip)))
    pares = [("LEIAME.txt", LEIAME)] + [(n, zz.read(n)) for n in zz.namelist() if n != "LEIAME.txt"]
    nomes = {n for n, _ in pares}
    for nome, c in extras:
        assert nome not in nomes, nome
        pares.append((nome, ler_b(c)))
    return zip_bytes(pares)


scripts_zip = interno("scripts.zip", [(s_, s_) for s_ in SCR5])
tabelas_zip = interno("tabelas_agregadas.zip", [(os.path.basename(t), t) for t in TAB5])
with zipfile.ZipFile("pacote_downloads_v5.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("LEIAME.txt", LEIAME)
    for n in z4.namelist():
        if n.startswith(("scripts/", "tabelas_agregadas/")):
            z.writestr(n, z4.read(n))
    for s_ in SCR5:
        z.writestr("scripts/" + s_, ler_b(s_))
    for t in TAB5:
        z.writestr("tabelas_agregadas/" + os.path.basename(t), ler_b(t))
    z.writestr("scripts.zip", scripts_zip)
    z.writestr("tabelas_agregadas.zip", tabelas_zip)
    z.writestr("METODOLOGIA_v5.md", md)
m_zip = re.search(r'const ZIP = \{scripts: "([A-Za-z0-9+/=]+)", tabelas: "([A-Za-z0-9+/=]+)"\};', h)
assert m_zip
h = h[:m_zip.start()] + f'const ZIP = {{scripts: "{base64.b64encode(scripts_zip).decode()}", tabelas: "{base64.b64encode(tabelas_zip).decode()}"}};' + h[m_zip.end():]

open("painel_soberania_digital_v5.html", "w", encoding="utf-8").write(h)
open("METODOLOGIA_v5.md", "w", encoding="utf-8").write(md)
print("ok", f"{os.path.getsize('painel_soberania_digital_v5.html') / 1e6:.1f} MB", f"pacote {os.path.getsize('pacote_downloads_v5.zip') / 1e6:.1f} MB")
