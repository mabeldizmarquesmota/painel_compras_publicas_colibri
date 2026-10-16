"""Painel, etapa 3: verificacao obrigatoria do HTML em Chromium headless, sem internet.

Executar a partir de Processado/, depois de p1_02:  python scripts_painel_v3/p1_03_verificar_html.py
Entrada: painel_soberania_digital_v3.html. Regras verificadas:
  - pagina aberta por arquivo local, com a rede desligada (contexto offline e toda requisicao nao local abortada);
  - console sem erros e sem excecoes de pagina;
  - cada KPI com numero (nunca vazio, 0, NaN, undefined ou "--");
  - graficos 1 a 8 com dados desenhados (Chart.js com elementos e valores positivos) e sem linha de grade nem
    borda de eixo; grafico 9 com fluxos e nos desenhados no SVG; cartoes de indicadores preenchidos;
  - tabelas 1 a 4 com linhas preenchidas;
  - filtros, alternador nominal/deflacionado, downloads CSV e .zip e barra fixa (abas e filtros) ao rolar.
Saidas: verificacao_html_v3/aba_*.png (capturas), verificacao_html_v3/resultado_verificacao.json,
  verificacao_html_v3/conf_painel.json (numeros exibidos no recorte padrao, para p1_04) e
  verificacao_html_v3/textos_i.json (textos dos icones "i").
"""
import csv
import json
import re
import os
import sys

import re as _re

from playwright.sync_api import sync_playwright

sys.stdout.reconfigure(encoding="utf-8")
OUT = "verificacao_html_v3"
os.makedirs(OUT, exist_ok=True)
URL = "file:///" + os.path.abspath("painel_soberania_digital_v3.html").replace("\\", "/")
R = {"falhas": [], "ok": [], "console": [], "requisicoes_bloqueadas": []}


def ok(cond, msg):
    (R["ok"] if cond else R["falhas"]).append(msg)
    return cond


RUIM = {"", "0", "NaN", "undefined", "--", "R$ 0 bi", "R$ 0 mi", "0%"}

with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    ctx = nav.new_context(viewport={"width": 1440, "height": 900}, offline=True, accept_downloads=True)
    pg = ctx.new_page()

    def rota(route):
        if route.request.url.startswith(("file:", "data:", "blob:")):
            route.continue_()
        else:
            R["requisicoes_bloqueadas"].append(route.request.url)
            route.abort()

    pg.route("**/*", rota)
    pg.on("console", lambda m: R["console"].append(f"{m.type}: {m.text}") if m.type in ("error", "warning") else None)
    pg.on("pageerror", lambda e: R["console"].append(f"pageerror: {e}"))
    pg.goto(URL)
    pg.wait_for_function("window.__pronto === true", timeout=60000)
    car = pg.evaluate("""() => { const c = document.getElementById('carrossel'), sl = [...c.querySelectorAll('.slide')];
        return {indice: window.__carrossel.indice(), classe: c.className, cartoes: sl.length, pontos: document.querySelectorAll('#pontos button').length,
                titulo: c.querySelector('.slide.ativo h3').innerText, rotulo: c.querySelector('.slide.ativo .eb').innerText,
                alturas: [...new Set(sl.map(x => Math.round(x.getBoundingClientRect().height)))].length, transborda: sl.some(x => x.scrollHeight > x.clientHeight + 1),
                cabe: sl.every(x => x.getBoundingClientRect().bottom <= c.getBoundingClientRect().bottom)}; }""")
    ok(car["indice"] == 0 and car["classe"].endswith("c0") and car["cartoes"] == 5 and car["pontos"] == 5 and car["titulo"] == "Sobre o projeto"
       and car["rotulo"].upper() == "CONTEXTO E ESCOPO" and car["alturas"] == 1 and not car["transborda"] and car["cabe"],
       f"Carrossel: cinco cartões e cinco pontos, abre em 'Sobre o projeto', mesma altura e sem texto cortado {car}")
    rem = pg.evaluate("""() => ({linha: document.querySelector('.topo').innerText.includes('Painel de apoio à análise das compras públicas'), p_topo: document.querySelectorAll('.topo p').length,
        bloco: document.querySelectorAll('#aba-sobre > .eyebrow2, #aba-sobre > h2.sec, #aba-sobre > .texto-abertura').length,
        primeiro: document.getElementById('aba-sobre').firstElementChild.id,
        folga: Math.round(document.querySelector('.topo').getBoundingClientRect().bottom - document.querySelector('.topo h1').getBoundingClientRect().bottom)})""")
    ok(not rem["linha"] and rem["p_topo"] == 0 and rem["bloco"] == 0 and rem["primeiro"] == "carrossel" and rem["folga"] <= 24,
       f"Cabeçalho sem a linha de descrição e aba Sobre começando pelo carrossel {rem}")

    def captura(nome):  # viewport com a altura da pagina (a captura full_page redimensiona e apaga os canvas)
        h = pg.evaluate("document.documentElement.scrollHeight")
        pg.set_viewport_size({"width": 1440, "height": h})
        pg.wait_for_timeout(1500)
        pg.screenshot(path=f"{OUT}/{nome}")
        pg.set_viewport_size({"width": 1440, "height": 900})
        pg.wait_for_timeout(700)

    def aba(nome):
        pg.click(f".aba[data-aba='{nome}']")
        pg.wait_for_timeout(900)

    # ---------------- Sobre
    aba("sobre")
    pg.mouse.move(5, 5)
    captura("aba_sobre.png")
    for k in ("sobre_kpi_compras", "sobre_kpi_valor", "sobre_kpi_soberania", "sobre_kpi_participacao"):
        t = pg.inner_text(f"[data-conf='{k}']").strip()
        ok(t not in RUIM and "NaN" not in t and "undefined" not in t, f"KPI {k} = {t!r}")

    # ---------------- Compras
    aba("compras")
    captura("aba_compras.png")
    for sel in ("#cp-kpi-n", "#cp-kpi-v"):
        t = pg.inner_text(sel).strip()
        ok(t not in RUIM and "NaN" not in t and "undefined" not in t, f"KPI {sel} = {t!r}")

    # ---------------- Soberania
    aba("soberania")
    captura("aba_soberania.png")
    for sel in ("#sd-kpi-v", "#sd-kpi-p", "#sd-kpi-f", "#sd-kpi-o"):
        t = pg.inner_text(sel).strip()
        ok(t not in RUIM and "NaN" not in t and "undefined" not in t, f"KPI {sel} = {t!r}")
    conf = pg.evaluate("Object.assign({}, window.__conf)")  # recorte padrao, abas de dados ja renderizadas
    estat = pg.evaluate("Object.fromEntries([...document.querySelectorAll('[data-conf]')].map(e => [e.dataset.conf, e.textContent.trim()]))")
    conf = {**estat, **conf}

    # aba de tecnologias criticas: frase de abertura, quatro KPIs (ordem, cores, posicao) e linha-resumo do Sankey
    kp = pg.evaluate("""() => { const ks = [...document.querySelectorAll('#sd-kpis > .kpi')], fr = document.getElementById('sd-frase');
        return {ids: ks.map(k => k.querySelector('.num').id), rots: ks.map(k => k.querySelector('.rot').innerText), cores: ks.map(k => getComputedStyle(k).borderTopColor),
                topo: ks.map(k => Math.round(k.getBoundingClientRect().top)), frase: fr.innerText,
                frase_acima: fr.getBoundingClientRect().bottom <= ks[0].getBoundingClientRect().top,
                intro_acima: document.querySelector('.intro-sob').getBoundingClientRect().bottom <= fr.getBoundingClientRect().top,
                i: ks.map(k => !!k.querySelector('.info'))}; }""")
    ok(kp["ids"] == ["sd-kpi-v", "sd-kpi-p", "sd-kpi-f", "sd-kpi-o"] and len(set(kp["topo"])) == 1 and all(kp["i"])
       and kp["cores"] == ["rgb(19, 81, 180)", "rgb(22, 136, 33)", "rgb(184, 84, 0)", "rgb(12, 123, 142)"]
       and kp["rots"][2] == "fornecedores vencedores (compras com vencedor identificado, 2021 a 2026)" and kp["rots"][3] == "órgãos compradores (compras com vencedor identificado, 2021 a 2026)",
       f"Aba de tecnologias críticas: quatro KPIs na ordem valor, participação, fornecedores e órgãos, na mesma linha, com i e bordas #1351B4, #168821, #B85400, #0C7B8E {kp['rots']}")
    ok(conf["sd_kpi_forn"] == "5.369" and conf["sd_kpi_org"] == "1.693", f"KPIs novos no período completo: {conf['sd_kpi_forn']} fornecedores e {conf['sd_kpi_org']} órgãos (iguais aos do Sankey da versão 1)")
    ok(kp["frase_acima"] and kp["intro_acima"] and kp["frase"] == conf["sd_frase"] and kp["frase"].startswith("No período, ")
       and kp["frase"].endswith(f"somaram {conf['sd_kpi_valor']} em valor homologado. Nas {conf['g9_resumo'].split(' compras')[0]} compras com fornecedor vencedor identificado, {conf['sd_kpi_forn']} fornecedores venderam para {conf['sd_kpi_org']} órgãos."),
       f"Frase de abertura logo acima dos KPIs: {kp['frase']}")
    ok(conf["g9_resumo"] == pg.inner_text("#g9-resumo") and conf["g9_resumo"].endswith(f" · {conf['g9_total']} (valor dos resultados, soma por categoria)") and _re.fullmatch(r"^[\d.]+ compras? com vencedor identificado · [\d.]+ fornecedor(es)? · [\d.]+ órgãos? · R\$ [\d.,]+ mi \(valor dos resultados, soma por categoria\)$", conf["g9_resumo"]) is not None
       and f" compras com vencedor identificado · {conf['sd_kpi_forn']} fornecedores · {conf['sd_kpi_org']} órgãos · " in conf["g9_resumo"],
       f"Linha-resumo do Sankey no recorte padrão: {conf['g9_resumo']}")
    t9 = pg.inner_text("#g9-t2")
    ok(t9 == "Fluxo do valor homologado nos resultados entre fornecedores, categorias de tecnologias críticas para a soberania digital e órgãos compradores, 2021 a 2026", f"Gráfico 9: título {t9}")
    tt9 = pg.evaluate("document.querySelector('[data-i=g9] .tt').textContent")
    ok("O valor do diagrama é a soma do valor homologado nos resultados de cada categoria. Uma compra classificada em mais de uma categoria aparece em cada uma delas; "
       f"por isso o total do diagrama ({conf['g9_total']}) é maior que o total das seis categorias ({conf['sd_kpi_valor']}), em que cada compra entra uma vez." in tt9, "Gráfico 9: i explica a soma por categoria, com os totais do diagrama e do KPI")
    ok("Os 10 maiores de cada lado são definidos pelo valor, nos dois modos. No modo Nº de compras, a compra é contada uma vez para cada fornecedor e uma vez para cada órgão; por isso os lados somam mais que o total de compras distintas mostrado no resumo." in tt9,
       "Gráfico 11: i explica os 10 maiores pelo valor e a contagem de compras por fornecedor e por órgão")
    tti = pg.evaluate("['sd_forn', 'sd_org'].map(k => document.querySelector(`[data-i=${k}] .tt`).textContent)")
    ok(all("A contagem considera apenas as compras com resultado vencedor publicado" in t for t in tti), "KPIs de fornecedores e órgãos: i explica que só entram compras com resultado vencedor publicado")
    pg.evaluate("document.getElementById('sd-frase').scrollIntoView()")
    pg.evaluate("window.scrollBy(0, -260)")
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/soberania_topo_frase_kpis.png")
    pg.evaluate("document.getElementById('sankey').closest('.graf-card').scrollIntoView()")
    pg.evaluate("window.scrollBy(0, -150)")
    pg.wait_for_timeout(400)
    pg.screenshot(path=f"{OUT}/sankey_sem_selecao.png")
    pg.evaluate("window.scrollTo(0, 0)")

    # graficos Chart.js: dados desenhados e sem grade
    chk = pg.evaluate("""() => ['g1','g2','g3','g4','g5','g6','g7','g8','gm','gv'].map(id => {
        const c = Chart.getChart(document.getElementById(id));
        if (!c) return {id, existe: false};
        let elementos = 0, positivos = 0;
        c.data.datasets.forEach((d, i) => { elementos += c.getDatasetMeta(i).data.length;
          d.data.forEach(v => { if (typeof v === 'number' && v > 0) positivos++; }); });
        const grade = Object.values(c.scales).map(s => ({id: s.id, grid: s.options.grid.display, borda: s.options.border.display}));
        return {id, existe: true, elementos, positivos, grade, largura: c.width, altura: c.height};
    })""")
    for g in chk:
        n = {"gm": "Gráfico 9 (modelo de aquisição)", "gv": "Gráfico 10 (tipo de vendedor)"}.get(g["id"], g["id"].replace("g", "Gráfico "))
        ok(g["existe"] and g["elementos"] > 0 and g["positivos"] > 0, f"{n}: {g.get('elementos')} elementos, {g.get('positivos')} valores positivos")
        if g["existe"]:
            ok(all(s["grid"] is False and s["borda"] is False for s in g["grade"]), f"{n}: sem grade e sem borda de eixo {g['grade']}")
    sk = pg.evaluate("() => ({paths: document.querySelectorAll('#sankey svg path').length, rects: document.querySelectorAll('#sankey svg rect').length})")
    ok(sk["paths"] > 0 and sk["rects"] > 0, f"Gráfico 11 (Sankey): {sk['paths']} fluxos, {sk['rects']} nós")
    ind = pg.evaluate("[...document.querySelectorAll('#ind-cartoes .kpi')].map(k => [...k.children].map(c => c.innerText))")
    ok(len(ind) == 3 and all(k[1].endswith("%") and "R$" in k[2] and k[3].startswith("campo preenchido em") for k in ind),
       f"Indicadores (antigo gráfico 10): três cartões numéricos {ind}")
    ok(pg.evaluate("document.getElementById('g10') === null"), "Indicadores: sem gráfico de barras")
    tam = pg.evaluate("[getComputedStyle(document.getElementById('g10-nota')).fontSize, getComputedStyle(document.getElementById('g10-txt')).fontSize, getComputedStyle(document.getElementById('ncm-txt')).fontSize, getComputedStyle(document.getElementById('ncm-nota')).fontSize]")
    ok(len(set(tam)) == 1, f"Indicadores e cartão de NCM: parágrafos com o mesmo tamanho de fonte {tam}")
    ordem = pg.evaluate("window.__ordemCategoriasSankey")
    lat = pg.evaluate("""() => { const r = [...document.querySelectorAll('#sankey rect[data-no]')].map(e => [e.dataset.no, +e.getAttribute('y')]);
        const topo = p => r.filter(x => x[0][0] === p).sort((a, b) => a[1] - b[1])[0][0]; return [topo('f'), topo('o')]; }""")
    ok(ordem == list(range(6)) and lat == ["fD", "oD"], f"Sankey: categorias na ordem do painel {ordem}; Demais no topo das colunas laterais {lat}")
    ncm = pg.inner_text("#ncm-txt")
    ok("R$" in ncm and "NaN" not in ncm and "undefined" not in ncm, f"Cartão de margem por NCM: {ncm}")
    for t, rot in (("tm", "Tabela 1 (marcas)"), ("t1", "Tabela 2 (órgãos)"), ("t2", "Tabela 3 (concentração)"), ("t3", "Tabela 4 (perfil)")):
        n = pg.evaluate(f"() => [...document.querySelectorAll('#{t} tbody tr')].filter(r => r.querySelectorAll('td').length > 1).length")
        ok(n > 0, f"{rot}: {n} linhas")

    # ---------------- blocos novos: principais achados, modelo de aquisicao, tipo de vendedor, marcas e porte
    import csv as _csv2
    ach_ref = [(f"{r['achado']}. {r['titulo']}", r["texto"]) for r in _csv2.DictReader(open("tabelas_painel_v3/pn_achados.csv", encoding="utf-8"), delimiter=";")]
    # Parte 2: achados em linhas, ultimo bloco da aba, sem cartao
    def ach_info():
        return pg.evaluate("""() => { const c = [...document.querySelectorAll('#achados .achado')], g = document.getElementById('achados'), sec = document.getElementById('aba-soberania');
            const st = x => getComputedStyle(x), gb = g.getBoundingClientRect();
            return {cards: c.map(x => [x.querySelector('h4').innerText, x.querySelector('p').innerText]), colunas: st(g).gridTemplateColumns.split(' ').length,
                    por_linha: [...new Set(c.map(x => Math.round(x.getBoundingClientRect().top)))].map(t => c.filter(x => Math.round(x.getBoundingClientRect().top) === t).length),
                    posicao: document.getElementById('sd-kpis').getBoundingClientRect().bottom <= gb.top
                      && gb.bottom <= [...sec.querySelectorAll('.bloco-tit')].find(e => e.innerText === 'O que o Estado compra?').getBoundingClientRect().top,
                    tit: g.previousElementSibling.previousElementSibling.innerText, nota: document.querySelector('.nota-achados').innerText, nota_fs: st(document.querySelector('.nota-achados')).fontSize,
                    estilo: c.map(x => [st(x).backgroundColor, st(x).boxShadow, st(x).borderTopWidth + ' ' + st(x).borderTopStyle + ' ' + st(x).borderTopColor,
                                        st(x).borderLeftWidth, st(x).borderBottomWidth, st(x).borderRightWidth]),
                    h4: c.map(x => [st(x.querySelector('h4')).fontSize, st(x.querySelector('h4')).fontWeight]), p: c.map(x => [st(x.querySelector('p')).fontSize, st(x.querySelector('p')).color])}; }""")
    ach = ach_info()
    _est = {tuple(e) for e in ach["estilo"]}
    ok([tuple(c) for c in ach["cards"]] == ach_ref and len(ach_ref) == 4 and ach["colunas"] == 4 and ach["por_linha"] == [4] and ach["posicao"]
       and ach["tit"] == "Principais achados" and ach["nota"] == "Os achados se referem ao período completo (2021 a 2026) e às seis categorias; não mudam com os filtros." and ach["nota_fs"] == "13px",
       f"Principais achados: na posição da v2 (logo após os KPIs, antes de 'O que o Estado compra?'), título, nota em 13 px e 4 achados lado a lado em uma linha, iguais a pn_achados.csv {ach['por_linha']}")
    ok(_est == {("rgba(0, 0, 0, 0)", "none", "1px solid rgb(31, 41, 55)", "0px", "0px", "0px")} and {tuple(x) for x in ach["h4"]} == {("15px", "700")}
       and {tuple(x) for x in ach["p"]} == {("14px", "rgb(55, 65, 81)")},
       f"Principais achados sem cartão, sombra, fundo ou cor de borda por item; linha de 1 px #1F2937 no topo; título 15 px em negrito; texto 14 px #374151 {_est}")
    _pal = [len(x.split()) for _, x in ach_ref]
    ok(max(_pal) <= 30 and not any("dupla contagem" in t + x for t, x in ach_ref) and all(t.split(". ", 1)[0] == str(i + 1) for i, (t, _) in enumerate(ach_ref)),
       f"Principais achados: numerados, no máximo 30 palavras {_pal} e sem 'dupla contagem'")
    _cols = {}
    for _w in (1000, 600):
        pg.set_viewport_size({"width": _w, "height": 900})
        pg.wait_for_timeout(300)
        _cols[_w] = ach_info()["colunas"]
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.wait_for_timeout(300)
    ok(_cols == {1000: 2, 600: 1}, f"Principais achados: 2 colunas abaixo de 1100 px e 1 abaixo de 700 px {_cols}")
    conf["achados_painel"] = [c[0] + "||" + c[1] for c in ach["cards"]]
    PRIV = ["Microsoft", "Google", "Amazon", "Oracle", "SAP", "IBM", "Red Hat", "VMware", "Broadcom", "Salesforce", "Adobe", "Huawei", "Cisco", "Fortinet", "Palo Alto", "Check Point"]
    ok(not [t for t, _ in ach_ref if any(p.lower() in t.lower() for p in PRIV)], f"Principais achados: nenhum nome de empresa privada nos títulos {[t for t, _ in ach_ref]}")
    st = pg.evaluate("""[...document.querySelectorAll('#aba-soberania .status-f2')].map(e => { const c = getComputedStyle(e);
        return [e.innerText, e.nextElementSibling.innerText, c.backgroundColor, c.color, c.borderLeftWidth + ' ' + c.borderLeftStyle + ' ' + c.borderLeftColor, c.fontSize]; })""")
    ok(len(st) == 1 and st[0][0] == "Classificação por palavras-chave verificada por amostragem e por revisão humana independente de 120 casos; são exibidas separadamente apenas as classes com concordância de pelo menos 80%."
       and st[0][1] == "Como o Estado contrata essas tecnologias e de quem depende" and st[0][2:] == ["rgb(238, 243, 250)", "rgb(27, 74, 130)", "4px solid rgb(19, 81, 180)", "13px"],
       f"Nota de classificação só antes de 'Como o Estado contrata...', no estilo do selo (fundo #EEF3FA, texto #1B4A82, borda 4px #1351B4, 13 px) {st}")
    bl = pg.evaluate("""() => [...document.querySelectorAll('#aba-soberania .bloco-tit')].map(e => e.innerText)""")
    ok(bl.index("Como o Estado contrata essas tecnologias e de quem depende") == bl.index("Como o Estado compra?") + 1, f"Bloco novo logo após 'Como o Estado compra?' {bl}")
    nv = pg.evaluate("""() => { const c = Chart.getChart(document.getElementById('gm')), d = c.data.datasets;
        return {n: d.length, rotulos: d.map(x => x.label), ult: d[d.length - 1].label, cor: d[d.length - 1].backgroundColor, leg: c.options.plugins.legend.position, eixo: c.options.indexAxis,
                soma: c.data.labels.map((_, i) => Math.round(d.reduce((a, x) => a + x.data[i], 0))), barras: c.data.labels.length}; }""")
    ok(nv["ult"] == "Serviços técnicos, equipamentos e não identificados" and nv["rotulos"][2] == "Licenciamento de direitos permanentes de uso" and nv["cor"] == "#C9D3DF" and nv["n"] == 4 and nv["leg"] == "bottom" and nv["eixo"] == "y" and set(nv["soma"]) == {100} and nv["barras"] == 6,
       f"Gráfico 9: barras horizontais 100% por categoria, só classes validadas e 'Serviços técnicos, equipamentos e não identificados' em #C9D3DF por último, legenda embaixo {nv}")
    nv2 = pg.evaluate("""() => { const c = Chart.getChart(document.getElementById('gv')), d = c.data.datasets;
        return {rot: d.map(x => x.label), leg: c.options.plugins.legend.position, soma: c.data.labels.map((_, i) => Math.round(d.reduce((a, x) => a + x.data[i], 0)))}; }""")
    ok(nv2["rot"] == ["Fabricante direto", "Revendedor ou integrador", "Empresa pública de TI", "Outra empresa estatal", "Demais fornecedores privados"] and nv2["leg"] == "bottom" and set(nv2["soma"]) == {100},
       f"Gráfico 10: cinco tipos de vendedor, barras 100%, legenda embaixo {nv2['rot']}")
    t3s = pg.evaluate("[...document.querySelectorAll('#aba-soberania .graf-card')].filter(c => c.querySelector('#gm, #gv, #tm, #porte-cartoes')).map(c => [...c.querySelectorAll('.tit-graf > div')].map(d => d.innerText))")
    ok(len(t3s) == 4 and all(len(x) == 3 and all(x) for x in t3s) and "soma por categoria" in t3s[1][2], f"Blocos novos com título Ipea em três linhas {t3s}")
    tti = pg.evaluate("['gm', 'gv', 'tm', 'porte'].map(k => document.querySelector(`[data-i=${k}] .tt`).textContent)")
    ok("Grupo de itens de desenvolvimento e serviços técnicos, equipamentos e itens sem indicação do modelo, cuja classificação automática não atingiu 80% de acerto na revisão humana. Inclui também suporte e manutenção de licença (R$ " in tti[0] and all("Exemplo de leitura" in t and "Como interpretar" in t for t in tti)
       and "não comprova o produto entregue" in tti[2] and "na soma por categoria" in tti[1], "Blocos novos: i com como interpretar e exemplo; nota da classe não validada; base dos resultados; menção à marca não prova o produto")
    fontes = pg.evaluate("[...document.querySelectorAll('#aba-soberania .graf-card')].filter(c => c.querySelector('#gm, #gv, #tm, #porte-cartoes')).map(c => c.querySelector('[data-fonte]').innerText)")
    ok(len(fontes) == 4 and all(f.startswith("Fonte:") for f in fontes), "Blocos novos com fonte")
    tm = pg.evaluate("""() => ({linhas: [...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(c => c.innerText)),
        tit: document.getElementById('tm-t2').innerText, alt: document.querySelector('#tm').closest('.tabela-rolagem').clientHeight,
        sticky: getComputedStyle(document.querySelector('#tm thead th')).position, setas: document.querySelectorAll('#tm .ord').length})""")
    num = lambda t: float(t.replace("%", "").replace(".", "").replace(",", "."))
    ok(tm["linhas"] and all(num(l[1]) >= 20 for l in tm["linhas"]) and "menção à marca" in tm["tit"] and tm["alt"] <= 500 and tm["sticky"] == "sticky" and tm["setas"] == 14,
       f"Tabela 1 (marcas): {len(tm['linhas'])} marcas com pelo menos 20 compras, rolagem de 12 linhas, cabeçalho fixo, setas de ordenação; título: {tm['tit']}")
    for col, k in (("compras", 1), ("v", 2), ("hhi", 7)):
        pg.click(f"#tm .ord[data-col='{col}'][data-dir='-1']")
        pg.wait_for_timeout(200)
        d = [num(r) for r in pg.evaluate(f"[...document.querySelectorAll('#tm tbody tr')].map(r => r.cells[{k}].innerText)")]
        pg.click(f"#tm .ord[data-col='{col}'][data-dir='1']")
        pg.wait_for_timeout(200)
        a = [num(r) for r in pg.evaluate(f"[...document.querySelectorAll('#tm tbody tr')].map(r => r.cells[{k}].innerText)")]
        ok(d == sorted(d, reverse=True) and a == sorted(a), f"Tabela 1 (marcas): ordenação por {col}")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(500)
    po = pg.evaluate("[...document.querySelectorAll('#porte-cartoes .kpi')].map(k => [k.querySelector('.rot-top').innerText, k.querySelector('.num').innerText, k.querySelector('.rot').innerText, getComputedStyle(k).borderTopColor])")
    pni = pg.inner_text("#porte-ni")
    ok(len(po) == 2 and [x[0] for x in po] == ["micro ou pequena empresa (ME ou EPP)", "demais empresas"] and all(" | " in x[1] and x[1].count("%") == 2 and x[2] == "das compras com vencedor | do valor" for x in po)
       and [x[3] for x in po] == ["rgb(19, 81, 180)", "rgb(22, 136, 33)"] and pni.startswith("Porte não informado em ") and pni.endswith("% do valor."),
       f"Indicadores de porte: dois cartões (ME ou EPP; demais) no estilo dos KPIs e linha de porte não informado {po} | {pni}")
    # contraste dos rotulos dentro das barras dos graficos 9 e 10 (branco se contraste >= 4,5:1; senao #1B2A41)
    def _lum(h):
        c = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
        c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
        return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
    _ctr = lambda a, b: (max(_lum(a), _lum(b)) + 0.05) / (min(_lum(a), _lum(b)) + 0.05)
    PAL_ESP = {"gm": ["#0B3D91", "#1351B4", "#7A5195", "#C9D3DF"], "gv": ["#0B3D91", "#1351B4", "#1F7A6F", "#7A5195", "#C9D3DF"]}
    contr = {}
    for gid, pal in PAL_ESP.items():
        cfg = pg.evaluate(f"""() => {{ const c = Chart.getChart(document.getElementById('{gid}')); const o = c.config.options.plugins.rotulos;
            return c.data.datasets.map((d, i) => [d.label, d.backgroundColor, o.corDentro(i)]); }}""")
        lin = []
        for (rot, fundo, cor), esp in zip(cfg, pal):
            cb = _ctr("#FFFFFF", fundo)
            certo = "#FFFFFF" if cb >= 4.5 else "#1B2A41"
            lin.append({"classe": rot, "fundo": fundo, "rotulo": cor, "contraste_branco": round(cb, 2), "contraste_rotulo": round(_ctr(cor, fundo), 2), "esperado": certo})
            ok(fundo.upper() == esp and cor.upper() == certo and _ctr(cor, fundo) >= 4.5 and (fundo.upper() != "#1F7A6F" or cor.upper() == "#FFFFFF"),
               f"Contraste {gid}, {rot}: fundo {fundo}, rótulo {cor} (contraste do branco {cb:.2f}:1; do rótulo {_ctr(cor, fundo):.2f}:1)")
        contr[gid] = lin
    json.dump(contr, open(f"{OUT}/contraste_rotulos_graficos_9_10.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    # conferencia de cores no painel inteiro: so os graficos que mostram categorias usam as cores das categorias
    CORES_CAT = [c.upper() for c in pg.evaluate("Object.values(D.cor)")]
    def cores_graficos():
        return pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('canvas')].filter(c => Chart.getChart(c)).map(c => {
            const ch = Chart.getChart(c), cs = new Set();
            ch.data.datasets.forEach(d => [d.backgroundColor, d.borderColor].forEach(x => (Array.isArray(x) ? x : [x]).forEach(v => { if (typeof v === 'string') cs.add(v); })));
            return [c.id, [...cs]]; }))""")
    def hexa(v):
        v = v.strip()
        if v.startswith("rgba(") or v.startswith("rgb("):
            n = [int(float(x)) for x in v[v.index("(") + 1:-1].split(",")[:3]]
            return "#%02X%02X%02X" % tuple(n)
        return v.upper()
    MOSTRA_CAT = {"g5"}  # grafico 5: uma serie por categoria; o Sankey (D3) colore os fluxos pela categoria
    rel = {}
    for estado in ("padrão", "Nuvem"):
        if estado == "Nuvem":
            pg.select_option("#sd-cat", "0")
            pg.wait_for_timeout(700)
            MOSTRA_CAT = {"g5", "g6", "g7"}  # com categoria filtrada, os graficos 6 e 7 mostram a propria categoria
        for aba_ in ("compras", "soberania"):
            aba(aba_)
            for gid, cs in cores_graficos().items():
                usa = sorted({hexa(c) for c in cs} & set(CORES_CAT))
                rel[f"{gid} ({estado})"] = {"cores": sorted({hexa(c) for c in cs}), "cores_de_categoria": usa, "mostra_categorias": gid in MOSTRA_CAT}
                if gid not in MOSTRA_CAT:
                    ok(not usa, f"Cores: {gid} ({estado}) não usa cores de categoria {sorted({hexa(c) for c in cs})}")
    sk_cores = pg.evaluate("[...new Set([...document.querySelectorAll('#sankey rect')].filter(r => !(r.dataset.no || '').startsWith('c')).map(r => r.getAttribute('fill').toUpperCase()))]")
    rel["sankey: nós de fornecedor e órgão"] = {"cores": sk_cores, "cores_de_categoria": sorted(set(sk_cores) & set(CORES_CAT)), "mostra_categorias": False}
    ok(not set(sk_cores) & set(CORES_CAT), f"Cores: nós de fornecedor e órgão do Sankey sem cores de categoria {sk_cores}")
    json.dump(rel, open(f"{OUT}/conferencia_cores_graficos.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    pg.click("#sd-limpar")
    pg.wait_for_timeout(600)
    aba("soberania")
    gtx = pg.inner_text("#gm-txt")
    _exm = {(r["elemento"], r["modo"]): r["texto"] for r in csv.DictReader(open("tabelas_painel_v3/pn_exemplos_modos.csv", encoding="utf-8"), delimiter=";")}
    ok(gtx == _exm[("gm_txt", "valores nominais")], f"Gráfico 9: texto abaixo do gráfico no recorte padrão igual ao gerado a partir dos dados (pn_exemplos_modos.csv): {gtx}")
    pg.select_option("#sd-cat", str(pg.evaluate("D.cats.indexOf('identidade')")))
    pg.wait_for_timeout(700)
    gtx2 = pg.inner_text("#gm-txt")
    _r9 = pg.evaluate("""() => { const c = Chart.getChart(document.getElementById('gm')), d = c.data.datasets;
        return [d.find(x => x.label === 'Subscrição ou serviço').data[0], d[d.length - 1].data[0]].map(fmtPct); }""")
    ok(gtx2 == f"Em Identidade e infraestrutura pública digital, subscrição ou serviço responde por {_r9[0]} do valor; serviços técnicos, equipamentos e não identificados, por {_r9[1]}.",
       f"Gráfico 9 com uma categoria filtrada: uma frase sobre a categoria, com os números do gráfico {gtx2}")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(600)
    pg.select_option("#sd-ini", "2025")
    pg.select_option("#sd-fim", "2025")
    pg.wait_for_timeout(700)
    gtx3 = pg.inner_text("#gm-txt")
    _cj = pg.evaluate("""() => { const dv = V(), cats = D.cats.map((_, i) => i), k = D.modCls.indexOf('Subscrição ou serviço'), nv = D.modCls.length - 1;
        const r = D.modelo.filter(x => x[1] === 2025), t = soma(r.map(x => x[3 + dv]));
        return [fmtPct(100 * soma(r.filter(x => x[2] === k).map(x => x[3 + dv])) / t), fmtPct(100 * soma(r.filter(x => x[2] === nv).map(x => x[3 + dv])) / t)]; }""")
    ok(gtx3 == f"No conjunto das categorias, subscrição ou serviço responde por {_cj[0]} do valor; serviços técnicos, equipamentos e não identificados, por {_cj[1]}.",
       f"Gráfico 9 com filtro de ano e todas as categorias: a mesma frase para o conjunto das categorias {gtx3}")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(600)
    st0 = pg.locator(".status-f2").first
    st0.scroll_into_view_if_needed()
    pg.evaluate("window.scrollBy(0, -200)")
    pg.wait_for_timeout(400)
    bb = st0.bounding_box()
    pg.screenshot(path=f"{OUT}/rotulo_revisao_humana.png", clip={"x": 0, "y": max(0, bb["y"] - 60), "width": 1440, "height": bb["height"] + 160})
    for e in ("gm-txt", "gv-txt", "tm-txt", "porte-txt", "porte-ni"):
        t = pg.inner_text("#" + e)
        ok(len(t) > 25 and "NaN" not in t and "undefined" not in t, f"Texto executivo {e}: {t[:140]}")
    tg = pg.evaluate("[...document.querySelectorAll('main .tg1')].map(e => e.innerText.trim().toUpperCase())")
    gs = [int(x.split()[1]) for x in tg if x.startswith("GRÁFICO ")]
    ts = [int(x.split()[1]) for x in tg if x.startswith("TABELA ")]
    ok(gs == list(range(1, 13)) and ts == list(range(1, 8)), f"Numeração em sequência pela ordem de aparição: gráficos {gs}, tabelas {ts} (tabelas 1 a 4 na aba de tecnologias críticas, 5 e 6 na aba de IA e 7 na metodologia)")
    # capturas dos blocos novos
    pg.set_viewport_size({"width": 1440, "height": 1600})
    pg.wait_for_timeout(800)
    for sel, nome in (("#achados", "achados_principais.png"), ("#gm", "grafico9_modelo_aquisicao.png"), ("#gv", "grafico10_tipo_vendedor.png"),
                      ("#tm", "tabela1_marcas.png"), ("#porte-cartoes", "indicadores_porte.png")):
        alvo = pg.locator(sel).locator("xpath=ancestor-or-self::*[contains(@class,'graf-card')][1]") if sel != "#achados" else pg.locator(sel)
        alvo.scroll_into_view_if_needed()
        pg.evaluate("window.scrollBy(0, -170)")
        pg.wait_for_timeout(500)
        if sel == "#achados":
            _y = pg.evaluate("""() => { const a = document.querySelector('.nota-achados').getBoundingClientRect(), b = document.getElementById('achados').getBoundingClientRect();
                return [a.top + window.scrollY, b.bottom + window.scrollY]; }""")
            pg.screenshot(path=f"{OUT}/{nome}", full_page=True, clip={"x": 0, "y": max(0, _y[0] - 120), "width": 1440, "height": _y[1] - _y[0] + 150})
        else:
            alvo.screenshot(path=f"{OUT}/{nome}")
    aba("compras")
    g4c = pg.locator("#g4").locator("xpath=ancestor::*[contains(@class,'graf-card')][1]")
    g4c.scroll_into_view_if_needed()
    pg.evaluate("window.scrollBy(0, -170)")
    pg.wait_for_timeout(600)
    g4c.screenshot(path=f"{OUT}/grafico4_modalidade.png")
    aba("soberania")
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.wait_for_timeout(600)
    pg.evaluate("window.scrollTo(0, 0)")

    # barra fixa ao rolar
    pg.evaluate("window.scrollTo(0, 2200)")
    pg.wait_for_timeout(400)
    pos = pg.evaluate("() => ({barra: document.getElementById('barra').getBoundingClientRect().top, topo: document.querySelector('.topo').getBoundingClientRect().bottom, filtros: getComputedStyle(document.getElementById('f-soberania')).display})")
    ok(abs(pos["barra"]) < 1 and pos["topo"] < 0 and pos["filtros"] != "none", f"Barra de abas e filtros fixa ao rolar {pos}")
    pg.screenshot(path=f"{OUT}/aba_soberania_rolagem.png")
    pg.evaluate("window.scrollTo(0, 0)")

    # ---------------- Metodologia
    aba("metodologia")
    captura("aba_metodologia.png")
    n4 = pg.evaluate("() => { const t = [...document.querySelectorAll('table.tabela')].find(x => (x.dataset.tabela || '').startsWith('TABELA 7')); return t ? t.querySelectorAll('tbody tr').length : 0; }")
    ok(n4 > 0, f"Tabela 7 (metodologia, robustez): {n4} linhas")
    for ini, fim, nome in (("3. Classificação das tecnologias críticas para a soberania digital", "4. Teste de robustez", "metodologia_secao3.png"),
                           ("7. Modelo de aquisição e tipo de vendedor", "8. Limitações", "metodologia_secao7_modelo_vendedor.png"),
                           ("8. Limitações", "Trilha dos números", "metodologia_limitacoes.png")):
        r = pg.evaluate("""([a, b]) => { const hs = [...document.querySelectorAll('#aba-metodologia h2')];
            const h1 = hs.find(h => h.innerText.trim() === a), h2 = hs.find(h => h.innerText.trim() === b);
            const y0 = h1.getBoundingClientRect().top + window.scrollY - 12, y1 = h2.getBoundingClientRect().top + window.scrollY - 8;
            return [y0, y1 - y0]; }""", [ini, fim])
        ok(r[1] > 50, f"Metodologia: seção '{ini}' encontrada ({round(r[1])} px)")
        pg.screenshot(path=f"{OUT}/{nome}", full_page=True, clip={"x": 0, "y": r[0], "width": 1440, "height": r[1]})
    sec3 = pg.inner_text("#aba-metodologia")
    ok("Critério de criticidade:" in sec3 and "Recomendação (UE) 2023/2113 da Comissão, de 3 de outubro de 2023" in sec3 and "Gütersloh: Bertelsmann Stiftung, 2025" in sec3
       and "Recorte tecnológico:" in sec3, "Metodologia: critério de criticidade, referências e recorte tecnológico presentes")
    refs = pg.evaluate("() => { const t = [...document.querySelectorAll('#aba-metodologia table.tabela')].find(x => x.dataset.tabela === 'Dicionário de termos por categoria'); const i = [...t.querySelectorAll('th')].findIndex(h => h.innerText === 'Referência'); return [...t.querySelectorAll('tbody tr')].map(r => r.cells[i].innerText); }")
    ok(len(refs) == 6 and all(r for r in refs), f"Metodologia: coluna Referência preenchida nas seis categorias")
    vis = pg.evaluate("() => [getComputedStyle(document.getElementById('f-compras')).display, getComputedStyle(document.getElementById('f-soberania')).display]")
    ok(vis == ["none", "none"], f"Metodologia sem barra de filtros: {vis}")
    for z in ("scripts", "tabelas"):
        with pg.expect_download() as d:
            pg.click(f"[data-zip='{z}']")
        dl = d.value
        caminho = f"{OUT}/download_{dl.suggested_filename}"
        dl.save_as(caminho)
        ok(os.path.getsize(caminho) > 1000, f"Download {dl.suggested_filename}: {os.path.getsize(caminho)} bytes")

    # textos dos icones i
    textos_i = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('.info[data-i]')].map(e => [e.dataset.i, e.querySelector('.tt').innerText]))")

    # ---------------- filtros, alternador e CSV (aba compras)
    aba("compras")
    antes = pg.inner_text("#cp-kpi-v")
    pg.click("#f-compras [data-alt] button[data-v='defl']")
    pg.wait_for_timeout(500)
    depois = pg.inner_text("#cp-kpi-v")
    ok(antes != depois, f"Alternador deflacionado altera o KPI de valor: {antes} -> {depois}")
    frase = pg.inner_text("#cp-frase-valores")
    ok("valores constantes" in frase, "Texto de abertura muda para valores constantes")
    captura("aba_compras_deflacionado.png")
    pg.select_option("#cp-ini", "2024")
    pg.select_option("#cp-fim", "2025")
    pg.select_option("#cp-esf", "0")
    pg.wait_for_timeout(500)
    ok(pg.inner_text("#cp-exib") == "2024 a 2025", "Filtro de anos (compras) aplicado")
    t = pg.inner_text("#cp-kpi-n")
    ok(t not in RUIM, f"KPI compras com filtro esfera federal 2024 a 2025 = {t}")
    with pg.expect_download() as d:
        pg.click("#cp-csv")
    caminho = f"{OUT}/download_{d.value.suggested_filename}"
    d.value.save_as(caminho)
    import csv as _csv
    linhas = list(_csv.reader(open(caminho, encoding="utf-8-sig"), delimiter=";"))
    ok(len(linhas) > 1 and all(l[1] == "Federal" and l[0] in ("2024", "2025") for l in linhas[1:]),
       f"CSV compras filtrado: {len(linhas) - 1} linhas, todas da esfera federal, 2024 e 2025")
    pg.click("#cp-limpar")
    pg.wait_for_timeout(400)
    ok(pg.inner_text("#cp-kpi-v") == conf["cp_kpi_valor"], "Limpar filtros restaura o recorte padrão (compras)")
    pg.click("#g1-sel button[data-m='qtd']")
    pg.wait_for_timeout(400)
    ok(pg.evaluate("Chart.getChart(document.getElementById('g1')).data.datasets[0].label") == "Compras homologadas", "Seletor Valor | Quantidade do gráfico 1")
    pg.click("#g1-sel button[data-m='valor']")

    # ---------------- filtros da aba soberania
    aba("soberania")
    pg.select_option("#sd-cat", "1")
    pg.wait_for_timeout(700)
    t = pg.inner_text("#sd-kpi-v")
    ok(t not in RUIM and t != conf["sd_kpi_valor"], f"Filtro de categoria (Nuvem) altera o KPI: {t}")
    cores = pg.evaluate("Chart.getChart(document.getElementById('g5')).data.datasets.map(d => d.backgroundColor[3])")
    ok(sum(c == "#D5DBE3" for c in cores) == 5, f"Gráfico 5: categorias não filtradas em cinza-claro {cores}")
    captura("aba_soberania_filtro_nuvem.png")
    with pg.expect_download() as d:
        pg.click("#sd-csv")
    caminho = f"{OUT}/download_{d.value.suggested_filename}"
    d.value.save_as(caminho)
    txt = open(caminho, encoding="utf-8-sig").read()
    ok(len(txt.splitlines()) > 1 and "tabela 3: concentração por ano" in txt and "tabela 4: perfil por ano" in txt,
       "CSV soberania filtrado, com os dados por ano das tabelas 3 e 4")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(500)
    ok(pg.inner_text("#sd-kpi-v") == conf["sd_kpi_valor"], "Limpar filtros restaura o recorte padrão (soberania)")

    # ---------------- Sankey interativo: clique em cada categoria, botao Voltar e reacao da tabela 1
    aba("soberania")
    ncat = pg.evaluate("D.cats.length")
    for c in range(ncat):
        nome = pg.evaluate(f"D.nome[D.cats[{c}]]")
        pg.locator(f"#sankey rect[data-no='c{c}']").first.click()
        pg.wait_for_timeout(700)
        est = pg.evaluate("""() => ({sel: document.getElementById('sd-cat').value, botao: [...document.querySelectorAll('#sk-cats button.ativo')].map(b => b.innerText),
            grupos: document.querySelectorAll('#t1 tbody tr.grupo').length, tit: document.getElementById('t1-t2').innerText,
            linhas: document.querySelectorAll('#t1 tbody tr').length, fluxos: document.querySelectorAll('#sankey svg path').length,
            kpi: document.getElementById('sd-kpi-v').innerText})""")
        ok(est["sel"] == str(c) and est["botao"] == [nome] and est["grupos"] == 0 and est["tit"].endswith(f"({nome})") and 0 < est["linhas"] <= 50 and est["fluxos"] > 0,
           f"Sankey: clique em {nome} sincroniza o filtro e o botão da categoria e filtra a tabela 2 ({est['linhas']} linhas, KPI {est['kpi']})")
        cc = pg.evaluate("D.cats[%d]" % c)
        rs = pg.evaluate("""() => ({resumo: document.getElementById('g9-resumo').innerText, forn: document.getElementById('sd-kpi-f').innerText,
            org: document.getElementById('sd-kpi-o').innerText, frase: document.getElementById('sd-frase').innerText, valor: document.getElementById('sd-kpi-v').innerText})""")
        conf[f"g9_resumo_{cc}"], conf[f"sd_kpi_forn_{cc}"], conf[f"sd_kpi_org_{cc}"], conf[f"sd_frase_{cc}"] = rs["resumo"], rs["forn"], rs["org"], rs["frase"]
        nb = pg.evaluate("""() => ({gm: Chart.getChart(document.getElementById('gm')).data.labels, gv: Chart.getChart(document.getElementById('gv')).data.labels,
            porte: ['mpe', 'demais'].map(k => document.getElementById('porte-' + k).innerText), pni: document.getElementById('porte-ni').innerText,
            tm: [...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(c => c.innerText)), ach: [...document.querySelectorAll('#achados .achado')].map(a => a.innerText)})""")
        for k, n in zip(("ME ou EPP", "Demais"), nb["porte"]):
            conf[f"porte_{k}_{cc}"] = n
        conf[f"porte_nao_informado_{cc}"] = nb["pni"].replace("Porte não informado em ", "").replace(" do valor.", "")
        for l in nb["tm"]:
            if len(l) == 8:
                conf[f"tm_{l[0]}_{cc}"] = "|".join(l[1:])
        ok(nb["gm"] == [nome] and nb["gv"] == [nome] and all(" | " in x for x in nb["porte"]) and nb["ach"] == [a + "\n\n" + b for a, b in ach_ref],
           f"Blocos novos com {nome}: gráficos 9 e 10 com uma barra, porte {nb['porte']}, {len(nb['tm'])} linhas na tabela de marcas, achados inalterados")
        txt_aba = pg.inner_text("#aba-soberania")
        ruins = sorted(set(_re.findall(r"(?<!acima de )(?<!a partir de )R\$ (?:0(?:,\d+)? bi|1 bi(?![,0-9]))", txt_aba)))
        ok(not ruins, f"Formatação em {nome}: nenhum valor abaixo de R$ 1 bi exibido em bilhões ({ruins}); frase: {rs['frase']}")
        ok(rs["resumo"] != conf["g9_resumo"] and f" · {rs['forn']} fornecedor" in rs["resumo"] and f" · {rs['org']} órgão" in rs["resumo"]
           and f"de {nome} somaram {rs['valor']}" in rs["frase"] and f"{rs['forn']} fornecedores venderam para {rs['org']} órgãos." in rs["frase"]
           and _re.fullmatch(r"^[\d.]+ compras? com vencedor identificado · [\d.]+ fornecedor(es)? · [\d.]+ órgãos? · R\$ [\d.,]+ mi \(valor dos resultados, soma por categoria\)$", rs["resumo"]) is not None and "NaN" not in rs["resumo"] + rs["frase"],
           f"Linha-resumo do Sankey em {nome}: {rs['resumo']} (KPIs {rs['forn']} fornecedores, {rs['org']} órgãos)")
        if c == 0:
            captura("aba_soberania_sankey_categoria_selecionada.png")
            pg.evaluate("document.getElementById('sankey').closest('.graf-card').scrollIntoView()")
            pg.wait_for_timeout(500)
            pg.screenshot(path=f"{OUT}/sankey_categoria_selecionada.png")
        pg.click("#sk-cats button[data-cat='-1']")
        pg.wait_for_timeout(700)
        vv = pg.evaluate("[document.getElementById('sd-cat').value, [...document.querySelectorAll('#sk-cats button.ativo')].map(b => b.innerText).join(), document.getElementById('sd-kpi-v').innerText]")
        ok(vv[0] == "-1" and vv[1] == "Todas" and vv[2] == conf["sd_kpi_valor"], f"Sankey: botão Todas após {nome} restaura o recorte {vv}")
        vr = pg.evaluate("[document.getElementById('g9-resumo').innerText, document.getElementById('sd-kpi-f').innerText, document.getElementById('sd-kpi-o').innerText, document.getElementById('sd-frase').innerText]")
        ok(vr == [conf["g9_resumo"], conf["sd_kpi_forn"], conf["sd_kpi_org"], conf["sd_frase"]], f"Voltar após {nome}: linha-resumo, KPIs novos e frase voltam ao recorte padrão ({vr[0]})")
    # legenda do Sankey e filtro superior sincronizados
    pg.locator("#g9-leg span[data-cat='2']").click()
    pg.wait_for_timeout(600)
    ok(pg.evaluate("document.getElementById('sd-cat').value") == "2", "Sankey: clique na legenda seleciona a categoria no filtro superior")
    pg.select_option("#sd-cat", "1")
    pg.wait_for_timeout(600)
    ok(pg.evaluate("[...document.querySelectorAll('#sankey rect[data-no^=\"c\"]')].map(r => r.dataset.no)") == ["c1"], "Sankey: filtro superior de categoria reflete no diagrama")
    pg.click("#sk-cats button[data-cat='-1']")
    pg.wait_for_timeout(600)
    # clique em fornecedor e tooltip de fluxo
    forn = pg.evaluate("[...document.querySelectorAll('#sankey rect[data-no^=\"f\"]')].map(r => r.dataset.no).find(x => x !== 'fD')")
    pg.locator(f"#sankey rect[data-no='{forn}']").click()
    pg.wait_for_timeout(700)
    st = pg.evaluate("[document.getElementById('sk-sel').innerText, document.getElementById('t1-t2').innerText, document.querySelectorAll('#sankey rect[data-no^=\"f\"]').length, document.querySelectorAll('#t1 tbody tr').length]")
    ok("fornecedor" in st[0] and "fornecedor" in st[1] and st[2] == 1 and st[3] > 0, f"Sankey: clique em fornecedor destaca só os fluxos dele e filtra a tabela 1 {st}")
    rf = pg.evaluate("[document.getElementById('g9-resumo').innerText, document.getElementById('sd-kpi-f').innerText]")
    ok(" · 1 fornecedor · " in rf[0] and rf[1] == conf["sd_kpi_forn"], f"Linha-resumo após clique em fornecedor: {rf[0]} (KPI do recorte inalterado: {rf[1]})")
    pg.screenshot(path=f"{OUT}/sankey_fornecedor_selecionado.png")
    pg.click("#sk-voltar")
    pg.wait_for_timeout(600)
    org = pg.evaluate("[...document.querySelectorAll('#sankey rect[data-no^=\"o\"]')].map(r => r.dataset.no).find(x => x !== 'oD')")
    pg.locator(f"#sankey rect[data-no='{org}']").click()
    pg.wait_for_timeout(700)
    ro = pg.inner_text("#g9-resumo")
    ok(" · 1 órgão · " in ro and ro != conf["g9_resumo"], f"Linha-resumo após clique em órgão: {ro}")
    pg.click("#sk-voltar")
    pg.wait_for_timeout(600)
    ok(pg.inner_text("#g9-resumo") == conf["g9_resumo"], "Voltar após clique em órgão restaura a linha-resumo")
    pg.select_option("#sd-ini", "2025")
    pg.select_option("#sd-fim", "2025")
    pg.wait_for_timeout(700)
    ra = pg.evaluate("[document.getElementById('g9-resumo').innerText, document.getElementById('sd-kpi-f').innerText, document.getElementById('sd-kpi-o').innerText, document.getElementById('sd-frase').innerText]")
    conf["g9_resumo_2025"], conf["sd_kpi_forn_2025"], conf["sd_kpi_org_2025"], conf["sd_frase_2025"] = ra
    n25 = pg.evaluate("""() => ({porte: ['mpe', 'demais'].map(k => document.getElementById('porte-' + k).innerText), pni: document.getElementById('porte-ni').innerText,
        tm: [...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(c => c.innerText)), gm: Chart.getChart(document.getElementById('gm')).data.labels.length,
        ach: [...document.querySelectorAll('#achados .achado')].map(a => a.innerText)})""")
    for k, n in zip(("ME ou EPP", "Demais"), n25["porte"]):
        conf[f"porte_{k}_2025"] = n
    conf["porte_nao_informado_2025"] = n25["pni"].replace("Porte não informado em ", "").replace(" do valor.", "")
    for l in n25["tm"]:
        if len(l) == 8:
            conf[f"tm_{l[0]}_2025"] = "|".join(l[1:])
    ok(n25["gm"] == 6 and n25["ach"] == [a + "\n\n" + b for a, b in ach_ref], f"Filtro de ano 2025: blocos novos atualizados (porte {n25['porte']}, {len(n25['tm'])} marcas) e achados inalterados")
    ruins = sorted(set(_re.findall(r"(?<!acima de )(?<!a partir de )R\$ (?:0(?:,\d+)? bi|1 bi(?![,0-9]))", pg.inner_text("#aba-soberania"))))
    ok(not ruins, f"Formatação com filtro 2025: nenhum valor abaixo de R$ 1 bi exibido em bilhões ({ruins})")
    todo = pg.evaluate("document.querySelector('main').textContent") + json.dumps(conf, ensure_ascii=False)
    ruins = sorted(set(_re.findall(r"(?<!acima de )(?<!a partir de )R\$ (?:0(?:,\d+)? bi|1 bi(?![,0-9]))", todo)))
    ok(not ruins, f"Formatação no painel inteiro (todas as abas, metodologia e números registrados): nenhum valor abaixo de R$ 1 bi em bilhões ({ruins})")
    ok(ra[0] != conf["g9_resumo"] and ra[3].startswith("Em 2025, ") and f"{ra[1]} fornecedores venderam para {ra[2]} órgãos." in ra[3],
       f"Filtro de ano (2025): linha-resumo {ra[0]}; frase {ra[3]}")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(700)
    pg.evaluate("document.getElementById('sankey').closest('.graf-card').scrollIntoView()")
    pg.evaluate("window.scrollBy(0, 250)")
    pg.wait_for_timeout(400)
    pt = pg.evaluate("""() => { const ps = [...document.querySelectorAll('#sankey svg path')];
        for (const p of ps) { const w = parseFloat(p.getAttribute('stroke-width')); if (w < 6) continue;
          const q = p.getPointAtLength(p.getTotalLength() / 2), m = p.getScreenCTM();
          const x = q.x * m.a + m.e, y = q.y * m.d + m.f; if (y > 220 && y < 820) return [x, y]; } return null; }""")
    pg.mouse.move(pt[0], pt[1])
    pg.wait_for_timeout(400)
    tt = pg.inner_text("#tooltip")
    vis = pg.evaluate("getComputedStyle(document.getElementById('tooltip')).display")
    hl = pg.evaluate("[...new Set([...document.querySelectorAll('#sankey svg path')].map(p => p.getAttribute('stroke-opacity')))].sort()")
    ok(vis == "block" and "Quem vendeu" in tt and "Quem comprou" in tt and "O que vendeu" in tt and "R$" in tt and "Nº de compras:" in tt and hl == ["0.35", "0.65"],
       f"Sankey: passar o mouse destaca o fluxo e mostra quem vendeu, o que vendeu, quem comprou, valor e nº de compras (opacidades {hl})")
    pg.screenshot(path=f"{OUT}/sankey_tooltip.png")
    pg.mouse.move(5, 5)
    # ordenacao da tabela 2
    def col_t2(i):
        return pg.evaluate(f"[...document.querySelectorAll('#t2 tbody tr')].map(r => r.cells[{i}].innerText)")
    num = lambda t: float(t.replace("%", "").replace(".", "").replace(",", "."))
    for col, idx, rot in (("cr4", 2, "CR4"), ("hhi", 3, "HHI"), ("n", 1, "Número de fornecedores"), ("v", 4, "Valor homologado")):
        pg.click(f"#t2 .ord[data-col='{col}'][data-dir='-1']")
        pg.wait_for_timeout(300)
        d = [num(x) for x in col_t2(idx)]
        pg.click(f"#t2 .ord[data-col='{col}'][data-dir='1']")
        pg.wait_for_timeout(300)
        a = [num(x) for x in col_t2(idx)]
        ok(d == sorted(d, reverse=True) and a == sorted(a) and len(a) > 12, f"Tabela 2: ordenação decrescente e crescente por {rot} ({len(a)} linhas)")
    alt = pg.evaluate("[document.querySelector('#t2').closest('.tabela-rolagem').clientHeight, getComputedStyle(document.querySelector('#t2 thead th')).position]")
    ok(alt[0] <= 500 and alt[1] == "sticky", f"Tabela 2: rolagem com limite de 12 linhas e cabeçalho fixo {alt}")
    alt = pg.evaluate("[document.querySelector('#t1').closest('.tabela-rolagem').clientHeight, getComputedStyle(document.querySelector('#t1 thead th')).position]")
    ok(alt[0] <= 500 and alt[1] == "sticky", f"Tabela 1: rolagem com limite de 12 linhas e cabeçalho fixo {alt}")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(500)
    # ---------------- Parte 3: Tabela 2, maiores cadeias fornecedor -> objeto -> orgao
    pg.click("#sd-limpar")
    pg.wait_for_timeout(700)
    aba("soberania")
    t1 = pg.evaluate("""() => ({cab: [...document.querySelectorAll('#t1 thead th')].map(t => t.innerText.replace(/[▲▼]/g, '').trim()),
        ords: [...document.querySelectorAll('#t1 thead th')].map(t => t.querySelectorAll('.ord').length), tit: document.getElementById('t1-t2').innerText,
        grupos: [...document.querySelectorAll('#t1 tbody tr.grupo')].map(r => r.innerText),
        por_grupo: (() => { const o = {}; let g = null; document.querySelectorAll('#t1 tbody tr').forEach(r => { if (r.classList.contains('grupo')) { g = r.innerText; o[g] = 0; } else o[g]++; }); return o; })(),
        portes: [...new Set([...document.querySelectorAll('#t1 .porte-forn')].map(e => e.innerText))],
        porte_css: (e => [getComputedStyle(e).fontSize, getComputedStyle(e).color])(document.querySelector('#t1 .porte-forn')),
        objs: [...document.querySelectorAll('#t1 tbody tr:not(.grupo)')].map(r => [r.querySelector('.obj').innerText, r.cells[1].innerText, +r.cells[4].innerText.replace(/[.]/g, '')]),
        nota: document.getElementById('t1-nota').innerText})""")
    ok(t1["cab"] == ["Fornecedor", "Objeto", "Órgão comprador", "Valor (R$ mi)", "Nº de compras", "% da categoria"] and t1["ords"] == [2] * 6
       and t1["tit"].startswith("Maiores cadeias: fornecedor → objeto → órgão, 2021 a 2026"),
       f"Tabela 2: título e colunas na ordem pedida, todas com ordenação {t1['cab']}")
    ok(t1["grupos"] == pg.evaluate("D.cats.map(c => D.nome[c])") and all(0 < n <= 50 for n in t1["por_grupo"].values()) and set(t1["portes"]) <= {"ME ou EPP", "Demais", "Não informado"}
       and t1["porte_css"] == ["12px", "rgb(107, 114, 128)"],
       f"Tabela 2: até 50 linhas por categoria {t1['por_grupo']}; porte em cinza 12 px abaixo do fornecedor {t1['portes']}")
    _mais = all((n == 1 and c == o) or c == f"{o} e mais {pg.evaluate(f'inteiro({n - 1})')}" for o, c, n in t1["objs"])
    ok(all(len(o) <= 70 for o, _, _ in t1["objs"]) and _mais, f"Tabela 2: objeto com até 70 caracteres e ' e mais N' quando a cadeia tem mais de uma compra ({len(t1['objs'])} linhas)")
    # objeto = objeto da compra (texto livre do PNCP), nunca so o nome do codigo do catalogo
    _objs = {r["objeto"] for r in csv.DictReader(open("tabelas_painel_v3/pn_cadeias_objetos.csv", encoding="utf-8"), delimiter=";")}
    _full = pg.evaluate("T1.map(x => x.obj)")
    ok(all(o in _objs for o in _full), f"Tabela 2: objeto é o texto do objeto da compra no PNCP (pn_cadeias_objetos.csv) em todas as {len(_full)} linhas")
    pg.locator("#t1 .obj").first.scroll_into_view_if_needed()
    pg.locator("#t1 .obj").first.hover()
    pg.wait_for_timeout(300)
    ok(pg.inner_text("#tooltip").replace("Objeto da compra de maior valor: ", "") == _full[0], "Tabela 2: tooltip do objeto com o texto completo")
    pg.mouse.move(5, 5)
    # ordenacao em todas as colunas (dentro da categoria), com Nuvem selecionada
    pg.click("#sk-cats button[data-cat='0']")
    pg.wait_for_timeout(700)
    num = lambda t: float(t.replace("%", "").replace(".", "").replace(",", "."))
    for col, idx, txt in (("forn", 0, True), ("obj", 1, True), ("org", 2, True), ("v", 3, False), ("n", 4, False), ("p", 5, False)):
        res = []
        for d in (1, -1):
            pg.click(f"#t1 .ord[data-col='{col}'][data-dir='{d}']")
            pg.wait_for_timeout(300)
            if txt:
                res.append(pg.evaluate(f"""(() => {{ const v = T1.map(x => x['{col}']); return v.every((x, i) => i === 0 || {d} * v[i - 1].localeCompare(x, 'pt-BR') <= 0); }})()"""))
            else:
                v = [num(x) for x in pg.evaluate(f"[...document.querySelectorAll('#t1 tbody tr:not(.grupo)')].map(r => r.cells[{idx}].innerText)")]
                res.append(v == sorted(v, reverse=(d == -1)))
        ok(all(res), f"Tabela 2: ordenação crescente e decrescente por {col}")
    # download CSV do recorte
    with pg.expect_download() as dl:
        pg.click("#t1-csv")
    _c = list(csv.reader(open(dl.value.path(), encoding="utf-8-sig"), delimiter=";"))
    _ncad = int(_re.search(r"; ([\d.]+) cadeias no recorte", pg.inner_text("#t1-nota")).group(1).replace(".", ""))
    ok(_c[0][:5] == ["categoria", "fornecedor", "porte", "objeto_da_compra_de_maior_valor", "orgao_comprador"] and len(_c) - 1 == _ncad and {x[0] for x in _c[1:]} == {"Nuvem"},
       f"Tabela 2: CSV do recorte (Nuvem) com {len(_c) - 1} cadeias, igual à nota da tabela")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(700)

    # ---------------- Parte 4: Sankey com sub-abas Valor | Nº de compras e botoes de categoria
    aba("soberania")
    sk = pg.evaluate("""() => ({modos: [...document.querySelectorAll('#sk-modo button')].map(b => b.innerText), cats: [...document.querySelectorAll('#sk-cats button')].map(b => b.innerText),
        cab: [...document.querySelectorAll('#sk-rolagem .sankey-cab span')].map(e => [e.innerText, getComputedStyle(e).textTransform, getComputedStyle(e.parentElement).color]),
        resumo_dir: document.getElementById('g9-resumo').getBoundingClientRect().right >= document.getElementById('sk-modo').parentElement.getBoundingClientRect().right - 2,
        f: [...document.querySelectorAll('#sankey rect[data-no^="f"]')].length, o: [...document.querySelectorAll('#sankey rect[data-no^="o"]')].length,
        fD: !!document.querySelector('#sankey rect[data-no="fD"]'), oD: !!document.querySelector('#sankey rect[data-no="oD"]')})""")
    ok(sk["modos"] == ["Valor", "Nº de compras"] and sk["cats"] == ["Todas"] + pg.evaluate("D.cats.map(c => D.nome[c])")
       and [x[0] for x in sk["cab"]] == ["QUEM VENDEU", "O QUE VENDEU", "QUEM COMPROU"] and all(x[1] == "uppercase" for x in sk["cab"]) and sk["resumo_dir"]
       and sk["f"] == 11 and sk["o"] == 11 and sk["fD"] and sk["oD"],
       f"Gráfico 11: sub-abas {sk['modos']}, botões {sk['cats']}, cabeçalhos em caixa alta, resumo à direita, 10 maiores e 'Demais' em cada ponta")
    # conferencia: Valor = total dos resultados da categoria; Nº de compras = cada compra uma vez por fornecedor e por orgao
    _fl = list(csv.DictReader(open("tabelas_painel_v3/pn_fluxo.csv", encoding="utf-8"), delimiter=";"))
    _fc = list(csv.DictReader(open("tabelas_painel_v3/pn_fluxo_compras.csv", encoding="utf-8"), delimiter=";"))
    CATS_ = pg.evaluate("D.cats")
    conf_sk = []
    for ci in [-1] + list(range(len(CATS_))):
        rot = "Todas" if ci < 0 else pg.evaluate(f"D.nome[D.cats[{ci}]]")
        pg.click(f"#sk-cats button[data-cat='{ci}']")
        pg.wait_for_timeout(600)
        selc = (lambda r: True) if ci < 0 else (lambda r, c=CATS_[ci]: r["categoria"] == c)
        tot = sum(round(float(r["valor_nominal"]), 2) for r in _fl if selc(r))
        pares_f = {(r["categoria"], r["id_compra"], r["cnpj_fornecedor"]) for r in _fc if selc(r)}
        pares_o = {(r["categoria"], r["id_compra"], r["orgao"]) for r in _fc if selc(r)}
        compras = {r["id_compra"] for r in _fc if selc(r)}
        for m in ("v", "n"):
            pg.click(f"#sk-modo button[data-m='{m}']")
            pg.wait_for_timeout(600)
            g = pg.evaluate("window.__sk")
            esq = sum(l[2] for l in g["links"] if l[0][0] == "f")
            dirr = sum(l[2] for l in g["links"] if l[1][0] == "o")
            if m == "v":
                fmt = lambda x: pg.evaluate(f"mi({x})")
                for med, a, b in (("soma dos fluxos fornecedor → categoria", esq, tot), ("soma dos fluxos categoria → órgão", dirr, tot)):
                    conf_sk.append([rot, "Valor", med, fmt(a), fmt(b), "tabelas_painel_v3/pn_fluxo.csv (valor_nominal)", "sim" if abs(a - b) < 0.5 and fmt(a) == fmt(b) else "não"])
            else:
                for med, a, b in (("soma dos fluxos fornecedor → categoria (cada compra uma vez por fornecedor)", esq, len(pares_f)),
                                  ("soma dos fluxos categoria → órgão (cada compra uma vez por órgão)", dirr, len(pares_o)),
                                  ("compras distintas na linha-resumo", g["compras"], len(compras))):
                    conf_sk.append([rot, "Nº de compras", med, str(int(a)), str(b), "tabelas_painel_v3/pn_fluxo_compras.csv", "sim" if int(a) == b else "não"])
        pg.click("#sk-modo button[data-m='v']")
        pg.wait_for_timeout(400)
    with open(f"{OUT}/sankey_conferencia.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["filtro", "modo", "medida", "valor_no_grafico", "valor_calculado", "arquivo_de_origem", "confere"])
        w.writerows(conf_sk)
    ok(len(conf_sk) == 35 and all(x[6] == "sim" for x in conf_sk),
       f"Gráfico 11: {len(conf_sk)} conferências em sankey_conferencia.csv (Valor = total dos resultados; Nº de compras = cada compra uma vez por fornecedor e por órgão) {[x for x in conf_sk if x[6] != 'sim'][:3]}")
    pg.click("#sk-cats button[data-cat='-1']")
    pg.wait_for_timeout(500)
    # sub-aba muda a espessura dos fluxos e a unidade
    larg_v = pg.evaluate("[...document.querySelectorAll('#sankey svg path')].map(p => p.getAttribute('stroke-width')).join()")
    pg.click("#sk-modo button[data-m='n']")
    pg.wait_for_timeout(600)
    larg_n = pg.evaluate("[...document.querySelectorAll('#sankey svg path')].map(p => p.getAttribute('stroke-width')).join()")
    ok(larg_v != larg_n and pg.inner_text("#g9-t3") == "(Número de compras)" and pg.inner_text("#g9-resumo") == conf["g9_resumo"],
       "Gráfico 11: a sub-aba Nº de compras muda a espessura dos fluxos e a unidade; a linha-resumo não muda")
    pg.click("#sk-modo button[data-m='v']")
    pg.wait_for_timeout(500)

    # ---------------- capturas em 1440 px e 390 px
    def captura_bloco(nome, alvo):
        pg.wait_for_timeout(300)
        # barras fixas (abas e filtros) escondidas so durante a captura, para nao cobrirem o cartao
        pg.evaluate("""() => document.querySelectorAll('body *').forEach(e => { const p = getComputedStyle(e).position;
            if ((p === 'sticky' || p === 'fixed') && !e.closest('table')) { e.dataset.capOculto = '1'; e.style.visibility = 'hidden'; } })""")
        if alvo == "achados":
            y = pg.evaluate("""() => { const a = [...document.querySelectorAll('#aba-soberania .bloco-tit')].find(e => e.innerText === 'Principais achados').getBoundingClientRect(),
                b = document.getElementById('achados').getBoundingClientRect(); return [a.top + window.scrollY, b.bottom + window.scrollY]; }""")
            w = pg.evaluate("document.documentElement.clientWidth")
            pg.screenshot(path=f"{OUT}/{nome}", full_page=True, clip={"x": 0, "y": max(0, y[0] - 20), "width": w, "height": y[1] - y[0] + 40})
        else:
            card = pg.locator(alvo).locator("xpath=ancestor::*[contains(@class,'graf-card')][1]")
            card.scroll_into_view_if_needed()
            pg.wait_for_timeout(500)
            card.screenshot(path=f"{OUT}/{nome}")
        pg.evaluate("() => document.querySelectorAll('[data-cap-oculto]').forEach(e => { e.style.visibility = ''; delete e.dataset.capOculto; })")
    larg = {}
    for w in (1440, 390):
        pg.set_viewport_size({"width": w, "height": 1400})
        pg.wait_for_timeout(900)
        aba("soberania")
        pg.wait_for_timeout(600)
        captura_bloco(f"achados_principais_{w}.png", "achados")
        captura_bloco(f"tabela2_cadeias_{w}.png", "#t1")
        pg.click("#sk-modo button[data-m='v']")
        captura_bloco(f"grafico11_sankey_valor_{w}.png", "#sankey")
        pg.click("#sk-modo button[data-m='n']")
        captura_bloco(f"grafico11_sankey_compras_{w}.png", "#sankey")
        pg.click("#sk-modo button[data-m='v']")
        pg.wait_for_timeout(400)
        larg[w] = pg.evaluate("""() => { const r = document.getElementById('sk-rolagem');
            return {pagina: document.documentElement.scrollWidth, janela: window.innerWidth, rola: r.scrollWidth > r.clientWidth, estreito: r.classList.contains('estreito'),
                    rot: Math.max(...[...document.querySelectorAll('#sankey text')].map(t => t.textContent.split('  ')[0].length)),
                    colunas: getComputedStyle(document.getElementById('achados')).gridTemplateColumns.split(' ').length}; }""")
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.wait_for_timeout(900)
    ok(not larg[1440]["estreito"] and not larg[1440]["rola"] and larg[1440]["rot"] <= 42 and larg[390]["estreito"] and larg[390]["rola"] and larg[390]["rot"] <= 24
       and larg[390]["pagina"] <= 390 and larg[390]["colunas"] == 1,
       f"Gráfico 11 responsivo: abaixo de 900 px, rótulos curtos e rolagem horizontal dentro do cartão, sem rolar a página {larg}")
    import shutil as _sh
    _sh.copyfile(f"{OUT}/achados_principais_1440.png", f"{OUT}/achados_principais.png")
    aba("soberania")
    # ---------------- Parte 5: aba Inteligencia artificial
    pg.set_viewport_size({"width": 1440, "height": 900})
    aba("ia")
    pg.wait_for_timeout(800)
    NOTA_V = ("Todos os valores são homologados: soma dos itens adjudicados aos vencedores, conforme registrado no PNCP. "
              "Não equivalem ao valor contratado nem ao valor pago.")
    ia0 = pg.evaluate("""() => { const s = document.getElementById('aba-ia'), b = [...document.querySelectorAll('#ia-filtros button')];
        const r = document.getElementById('ia-resumo-box').getBoundingClientRect(), a = document.getElementById('ia-achados').getBoundingClientRect(),
              g = document.querySelector('#aba-ia .graf-card').getBoundingClientRect();
        return {nota: s.querySelector('.nota-valores').innerText, nota1: s.firstElementChild.className, selo: document.getElementById('ia-selo').innerText, selo_classe: document.getElementById('ia-selo').className,
                selo_cor: getComputedStyle(document.getElementById('ia-selo')).backgroundColor, botoes: b.map(x => x.innerText),
                cap_esp: parseFloat(getComputedStyle(b[b.length - 1]).marginLeft), resumo: document.getElementById('ia-resumo').innerText,
                ordem: r.bottom <= a.top && a.bottom <= g.top, ach: [...document.querySelectorAll('#ia-achados .achado')].map(x => [x.querySelector('h4').innerText, x.querySelector('p').innerText]),
                ach_linhas: new Set([...document.querySelectorAll('#ia-achados .achado')].map(x => Math.round(x.getBoundingClientRect().top))).size,
                modos: [...document.querySelectorAll('#ia-modo button')].map(x => x.innerText), abas: [...document.querySelectorAll('.aba')].map(x => x.innerText)}; }""")
    ach_ia = [(f"{r['achado']}. {r['titulo']}", r["texto"]) for r in csv.DictReader(open("tabelas_painel_v3/ia_achados.csv", encoding="utf-8"), delimiter=";")]
    ok(ia0["abas"] == ["Sobre", "Compras públicas", "Tecnologias críticas para a soberania digital", "Inteligência artificial", "Metodologia"],
       f"Abas: Inteligência artificial entre Tecnologias críticas e Metodologia {ia0['abas']}")
    _rh = {r["classe"]: r for r in csv.DictReader(open("validacao_ia/resultado_revisao_humana_ia.csv", encoding="utf-8"), delimiter=";")}
    _st = pg.evaluate(f"`Classificação por palavras-chave verificada por amostragem e por revisão humana independente de ${{inteiro({_rh['Total']['casos_revisados']})}} casos; "
                      f"todas as classes exibidas tiveram concordância de pelo menos ${{fmtPct({min(float(r['concordancia_pct']) for k, r in _rh.items() if k in ('Capacitação', 'Acréscimo à licença', 'Solução de IA (exclusiva ou em pacote)', 'Outros'))})}}.`")
    ok(ia0["nota"] == NOTA_V and ia0["nota1"] == "nota-valores" and ia0["selo"] == _st and ia0["selo_classe"] == "status-f2" and ia0["selo_cor"] == "rgb(238, 243, 250)",
       f"Aba IA: nota fixa do valor homologado no topo e nota da classificação no estilo da aba de tecnologias críticas: {ia0['selo']}")
    ok(ia0["botoes"] == ["Todas (tecnologia)", "Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)", "Outros", "Capacitação"] and ia0["cap_esp"] >= 16
       and ia0["modos"] == ["Valor", "Nº de compras"],
       f"Aba IA: sub-abas {ia0['modos']} e botões {ia0['botoes']}, com espaço antes de Capacitação ({ia0['cap_esp']} px)")
    ok(_re.fullmatch(r"Tecnologia de IA: [\d.]+ compras · [\d.]+ fornecedores · [\d.]+ órgãos · R\$ [\d.,]+ (bi|mi) \| Capacitação em IA: [\d.]+ compras · [\d.]+ fornecedores · [\d.]+ órgãos · R\$ [\d.,]+ (bi|mi)", ia0["resumo"]) is not None,
       f"Aba IA: linha-resumo com os dois mercados separados: {ia0['resumo']}")
    ok([tuple(x) for x in ia0["ach"]] == ach_ia and len(ach_ia) <= 4 and ia0["ach_linhas"] == 1 and ia0["ordem"] and all(len(t.split()) <= 30 for _, t in ach_ia),
       f"Aba IA: {len(ach_ia)} achados lado a lado, logo depois da linha-resumo e antes do gráfico, iguais a ia_achados.csv")
    conf["ia_achados_painel"] = [h + "||" + t for h, t in ia0["ach"]]
    tti_ia = pg.evaluate("document.querySelector('[data-i=ia_resumo] .tt').textContent")
    ok("A tecnologia de IA soma" in tti_ia and "compras de acréscimo de IA a licença classificadas em outras categorias" in tti_ia and "repartido entre as classes pelos itens" in tti_ia,
       "Aba IA: i da linha-resumo explica a diferença entre a tecnologia de IA e a categoria IA do painel (componente C e repartição por itens), com números")
    ok("toda a base do painel, e não só a base da aba de IA" in pg.inner_text("#ia-marcas-nota"), "Tabela de marcas: nota sobre a busca em toda a base do painel")
    # dados para a conferencia (Python), nos dois modos e em cada filtro
    _ib = list(csv.DictReader(open("tabelas_painel_v3/ia_base.csv", encoding="utf-8"), delimiter=";"))
    _ip = list(csv.DictReader(open("tabelas_painel_v3/ia_base_classes.csv", encoding="utf-8"), delimiter=";"))
    _ir = list(csv.DictReader(open("tabelas_painel_v3/ia_resultados.csv", encoding="utf-8"), delimiter=";"))
    CLS_IA = pg.evaluate("D.ia.classes")
    FILT_IA = {k: [CLS_IA[i] for i in c] for k, _, c in pg.evaluate("D.ia.filtros")}
    NOME_F = {"tec": "tecnologia", "acr": "acrescimo", "sol": "solucao", "out": "outros", "cap": "capacitacao"}
    conf_ia, txt_graf, palavras = [], [], []
    for fk in ("tec", "acr", "sol", "out", "cap"):
        pg.click(f"#ia-filtros button[data-f='{fk}']")
        pg.wait_for_timeout(600)
        rs = [r for r in _ir if r["classe"] in FILT_IA[fk]]
        tot = sum(round(float(r["valor_nominal"]), 2) for r in rs)
        pf = {(r["id_compra"], r["cnpj_fornecedor"]) for r in rs}
        po = {(r["id_compra"], r["orgao"]) for r in rs}
        cpr = {r["id_compra"] for r in rs}
        for m in ("v", "n"):
            pg.click(f"#ia-modo button[data-m='{m}']")
            pg.wait_for_timeout(600)
            g = pg.evaluate("window.__skIA")
            esq = sum(l[2] for l in g["links"] if l[0][0] == "f")
            dirr = sum(l[2] for l in g["links"] if l[1][0] == "o")
            if m == "v":
                fmt = lambda x: pg.evaluate(f"mi({x})")
                for med, a, b in (("soma dos fluxos fornecedor → tipo de objeto", esq, tot), ("soma dos fluxos tipo de objeto → órgão", dirr, tot)):
                    conf_ia.append([fk, "Valor", med, fmt(a), fmt(b), "tabelas_painel_v3/ia_resultados.csv (valor_nominal)", "sim" if abs(a - b) < 0.5 and fmt(a) == fmt(b) else "não"])
            else:
                for med, a, b in (("soma dos fluxos fornecedor → tipo de objeto (cada compra uma vez por fornecedor)", esq, len(pf)),
                                  ("soma dos fluxos tipo de objeto → órgão (cada compra uma vez por órgão)", dirr, len(po)),
                                  ("compras distintas na linha-resumo do gráfico", g["compras"], len(cpr))):
                    conf_ia.append([fk, "Nº de compras", med, str(int(a)), str(b), "tabelas_painel_v3/ia_resultados.csv", "sim" if int(a) == b else "não"])
            if m == "v":
                # texto x grafico: numeros dos destaques e o no do grafico correspondente
                nos = {x[0]: x for x in g["nos"]}
                dest = pg.evaluate("[...document.querySelectorAll('#ia-destaques .ia-destaque')].map(d => [d.querySelector('b').innerText, d.querySelector('span').innerText])")
                for t, x in dest:
                    palavras.append([fk, t, len(x.replace(" Valores nominais.", "").split())])
                tot_g = g["total"]
                for t, x in dest:
                    if t == "O que mais se compra":
                        nome = x.split(" respondeu por ")[0]
                        no = next(v for k, v in nos.items() if k[0] == "t" and v[1] == nome)
                    elif t == "Quem mais vende":
                        nome = x.split(" recebeu ")[0]
                        no = next(v for k, v in nos.items() if k[0] == "f" and v[1] == nome)
                    elif t == "Quem mais compra":
                        nome = x.split(" respondeu por ")[0]
                        no = next(v for k, v in nos.items() if k[0] == "o" and v[1] == nome)
                    else:
                        continue
                    pct_txt = _re.search(r"([\d,]+%)", x).group(1)
                    pct_g = pg.evaluate(f"fmtPct({100 * no[2] / tot_g})")
                    txt_graf.append([fk, t, x, pct_txt, pct_g, "sim" if pct_txt == pct_g else "não"])
        pg.click("#ia-modo button[data-m='v']")
        pg.wait_for_timeout(400)
    conf.update({k: v for k, v in pg.evaluate("Object.assign({}, window.__conf)").items() if k.startswith("ia_")})
    with open(f"{OUT}/ia_sankey_conferencia.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["filtro", "modo", "medida", "valor_no_grafico", "valor_calculado", "arquivo_de_origem", "confere"])
        w.writerows(conf_ia)
    with open(f"{OUT}/ia_texto_grafico.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["filtro", "destaque", "texto", "numero_no_texto", "numero_no_grafico", "confere"])
        w.writerows(txt_graf)
    ok(len(conf_ia) == 25 and all(x[6] == "sim" for x in conf_ia),
       f"Gráfico 12: {len(conf_ia)} conferências em ia_sankey_conferencia.csv (Valor = total dos resultados; Nº de compras = cada compra uma vez por fornecedor e por órgão) {[x for x in conf_ia if x[6] != 'sim'][:3]}")
    ok(len(txt_graf) == 14 and all(x[5] == "sim" for x in txt_graf), f"Aba IA: números dos destaques iguais aos do gráfico 12 em todos os filtros ({len(txt_graf)} comparações) {[x for x in txt_graf if x[5] != 'sim'][:2]}")
    ok(len(palavras) == 15 and all(x[2] <= 25 for x in palavras), f"Aba IA: três destaques por filtro, com até 25 palavras {[x for x in palavras if x[2] > 25]}")
    # alternador na aba IA
    r_nom = pg.inner_text("#ia-resumo")
    pg.click("#f-ia [data-alt] button[data-v='defl']")
    pg.wait_for_timeout(700)
    r_def, d_def = pg.inner_text("#ia-resumo"), pg.evaluate("[...document.querySelectorAll('#ia-destaques .com-modo')].map(x => x.innerText)")
    ok(r_def != r_nom and all((not "R$" in x) or x.endswith(" Valores deflacionados, a preços de " + pg.evaluate("D.mesBaseTxt") + ".") for x in d_def),
       f"Aba IA: o alternador muda a linha-resumo e os destaques com reais terminam com o modo ({r_def})")
    pg.click("#ia-limpar")
    pg.wait_for_timeout(700)
    # capturas em 1440 px e 390 px: a aba inteira e uma por filtro, nos modos Valor e Nº de compras
    def captura_ia(nome, w):
        pg.wait_for_timeout(400)
        pg.evaluate("""() => document.querySelectorAll('body *').forEach(e => { const p = getComputedStyle(e).position;
            if ((p === 'sticky' || p === 'fixed') && !e.closest('table')) { e.dataset.capOculto = '1'; e.style.visibility = 'hidden'; } })""")
        el = pg.locator("#aba-ia")
        el.screenshot(path=f"{OUT}/{nome}")
        pg.evaluate("() => document.querySelectorAll('[data-cap-oculto]').forEach(e => { e.style.visibility = ''; delete e.dataset.capOculto; })")
    larg_ia = {}
    for w in (1440, 390):
        pg.set_viewport_size({"width": w, "height": 1200})
        pg.wait_for_timeout(800)
        aba("ia")
        pg.wait_for_timeout(800)
        captura_ia(f"aba_ia_todas_{w}.png", w)
        for fk in ("tec", "acr", "sol", "out", "cap"):
            pg.click(f"#ia-filtros button[data-f='{fk}']")
            for m, rot in (("v", "valor"), ("n", "compras")):
                pg.click(f"#ia-modo button[data-m='{m}']")
                pg.wait_for_timeout(500)
                captura_ia(f"aba_ia_{NOME_F[fk]}_{rot}_{w}.png", w)
        pg.click("#ia-limpar")
        pg.wait_for_timeout(500)
        larg_ia[w] = pg.evaluate("""() => { const r = document.getElementById('ia-rolagem');
            return {pagina: document.documentElement.scrollWidth, rola: r.scrollWidth > r.clientWidth, estreito: r.classList.contains('estreito')}; }""")
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.wait_for_timeout(800)
    ok(not larg_ia[1440]["estreito"] and larg_ia[390]["estreito"] and larg_ia[390]["rola"] and larg_ia[390]["pagina"] <= 390,
       f"Gráfico 12 responsivo: abaixo de 900 px, rolagem horizontal dentro do cartão, sem rolar a página {larg_ia}")
    aba("soberania")
    # ---------------- Parte 6: verificacao final em 1440 px e 390 px (todas as abas trocam, sem rolagem horizontal da pagina) e capturas
    ABAS6 = ["sobre", "compras", "soberania", "ia", "metodologia"]
    final = {}
    for w in (1440, 390):
        pg.set_viewport_size({"width": w, "height": 1200})
        pg.wait_for_timeout(800)
        for a6 in ABAS6:
            aba(a6)
            pg.wait_for_timeout(500)
            final[(w, a6)] = pg.evaluate("""a => ({ativa: document.querySelector('.aba-conteudo.ativa').id === 'aba-' + a, botao: document.querySelector('.aba.ativa').dataset.aba === a,
                largura: document.documentElement.scrollWidth, janela: window.innerWidth})""", a6)
        aba("soberania")
        pg.click("#f-soberania [data-alt] button[data-v='nom']")
        pg.wait_for_timeout(600)
        captura_bloco(f"grafico5_nominal_{w}.png", "#g5")
        ex_n = pg.evaluate("document.querySelector('[data-ex=g5]').textContent")
        pg.click("#f-soberania [data-alt] button[data-v='defl']")
        pg.wait_for_timeout(700)
        captura_bloco(f"grafico5_deflacionado_{w}.png", "#g5")
        ex_d = pg.evaluate("document.querySelector('[data-ex=g5]').textContent")
        final[(w, "exemplo_g5")] = {"muda": ex_n != ex_d and ex_d.endswith(pg.evaluate("D.modoTxt[1]"))}
        pg.click("#sd-limpar")
        pg.wait_for_timeout(600)
        captura_bloco(f"grafico9_{w}.png", "#gm")
        captura_bloco(f"achados_linhas_{w}.png", "achados")
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.wait_for_timeout(800)
    import shutil as _sh6
    for nome in ("grafico5_nominal", "grafico5_deflacionado", "grafico9", "achados_linhas", "tabela2_cadeias", "grafico11_sankey_valor", "grafico11_sankey_compras", "aba_ia_todas"):
        _sh6.copyfile(f"{OUT}/{nome}_1440.png", f"{OUT}/{nome}.png")
    ok(all(v["ativa"] and v["botao"] for k, v in final.items() if k[1] in ABAS6), f"Todas as abas trocam, em 1440 px e 390 px {[k for k, v in final.items() if k[1] in ABAS6 and not (v['ativa'] and v['botao'])]}")
    ok(all(v["largura"] <= v["janela"] for k, v in final.items() if k[1] in ABAS6),
       f"Nenhuma aba rola na horizontal, em 1440 px e 390 px {[(k, v['largura']) for k, v in final.items() if k[1] in ABAS6 and v['largura'] > v['janela']]}")
    ok(final[(1440, "exemplo_g5")]["muda"] and final[(390, "exemplo_g5")]["muda"], "Gráfico 5: o exemplo de leitura muda junto com o alternador, em 1440 px e 390 px")
    aba("soberania")
    # ordem das categorias no filtro
    ordem = pg.evaluate("[...document.querySelectorAll('#sd-cat option')].slice(1).map(o => o.textContent)")
    ok(ordem == ["Nuvem", "Plataformas e licenciamento", "Data center", "Segurança cibernética", "Inteligência artificial",
                 "Identidade e infraestrutura pública digital"], f"Ordem das categorias no filtro: {ordem}")
    # carrossel: pausa com o mouse e com clique em seta; retoma ao sair
    aba("sobre")
    pg.hover("#carrossel")
    pg.wait_for_timeout(400)
    w1 = pg.evaluate("parseFloat(document.querySelector('#carrossel .progresso span').style.width)")
    pg.wait_for_timeout(1500)
    w2 = pg.evaluate("parseFloat(document.querySelector('#carrossel .progresso span').style.width)")
    ok(pg.evaluate("window.__carrossel.pausado()") and w1 == w2, f"Carrossel pausa com o mouse sobre ele ({w1} = {w2})")
    antes = pg.evaluate("window.__carrossel.indice()")
    pg.click("#carrossel .dir")
    pg.wait_for_timeout(1500)
    esp = (antes + 1) % 5
    est = pg.evaluate("[window.__carrossel.pausado(), window.__carrossel.indice(), document.getElementById('carrossel').className, parseFloat(document.querySelector('#carrossel .progresso span').style.width)]")
    ok(est[0] and est[1] == esp and est[2].endswith(f"c{esp}") and est[3] == 0, f"Carrossel: clique na seta avança do cartão {antes} para o {esp} e mantém a pausa {est}")
    pg.click("#pontos button:nth-child(2)")
    pg.wait_for_timeout(300)
    pg.screenshot(path=f"{OUT}/carrossel_seta_pausa.png", clip={"x": 0, "y": 0, "width": 1440, "height": 900})
    pg.mouse.move(5, 5)
    pg.wait_for_timeout(1500)
    w3 = pg.evaluate("parseFloat(document.querySelector('#carrossel .progresso span').style.width)")
    ok(not pg.evaluate("window.__carrossel.pausado()") and w3 > 0, f"Carrossel retoma ao retirar o mouse (progresso {w3:.1f}%)")
    # carrossel: cores Blues_d, texto branco com contraste >= 4,5:1; amarelo so na barra e no ponto ativo
    def lum(rgb):
        v = [int(x) / 255 for x in re.findall(r"\d+", rgb)[:3]]
        v = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in v]
        return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
    esperado = ["rgb(19, 81, 180)", "rgb(22, 136, 33)", "rgb(184, 84, 0)", "rgb(12, 123, 142)", "rgb(27, 74, 130)"]
    for k in range(5):
        pg.click(f"#pontos button:nth-child({k + 1})")
        pg.wait_for_timeout(250)
        est = pg.evaluate("""() => { const c = document.getElementById('carrossel');
            return [getComputedStyle(c).backgroundColor, getComputedStyle(c.querySelector('.slide.ativo h3')).color, getComputedStyle(c.querySelector('.slide.ativo p, .slide.ativo li')).color,
                    getComputedStyle(c.querySelector('.progresso span')).backgroundColor, getComputedStyle(document.querySelector('#pontos button.ativo')).backgroundColor]; }""")
        l1, l2 = lum(est[1]), lum(est[0])
        cr = (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)
        ok(est[0] == esperado[k] and est[1] == est[2] == "rgb(255, 255, 255)" and cr >= 4.5 and est[3] == est[4] == "rgb(250, 189, 16)",
           f"Carrossel, cartão {k + 1}: fundo {est[0]}, texto branco, contraste {cr:.2f}:1; barra e ponto ativo amarelos")
        caixa = pg.locator("#carrossel").bounding_box()
        pg.screenshot(path=f"{OUT}/sobre_carrossel_cartao_{k + 1}.png", clip={"x": 0, "y": max(0, caixa["y"] - 20), "width": 1440, "height": caixa["height"] + 70})
    pg.mouse.move(5, 5)
    # bordas dos KPIs na escala Blues_d, por posicao
    esc = {4: ["rgb(19, 81, 180)", "rgb(22, 136, 33)", "rgb(184, 84, 0)", "rgb(12, 123, 142)"],
           2: ["rgb(19, 81, 180)", "rgb(22, 136, 33)"], 3: ["rgb(19, 81, 180)", "rgb(22, 136, 33)", "rgb(184, 84, 0)"]}
    for nome_aba, sel in (("sobre", "#aba-sobre .kpis"), ("compras", "#aba-compras .kpis"), ("soberania", "#sd-kpis"), ("soberania", "#ind-cartoes")):
        aba(nome_aba)
        cores = pg.evaluate(f"[...document.querySelectorAll('{sel} > .kpi')].map(k => getComputedStyle(k).borderTopColor)")
        ok(cores == esc[len(cores)], f"Bordas dos KPIs ({sel}): {cores}")
        rots = pg.evaluate(f"[...document.querySelectorAll('{sel} > .kpi .rot, {sel} > .kpi .rot-top')].map(r => r.innerText.trim()).filter(Boolean)")
        rots = [r for r in rots if not r.startswith("R$")]  # linhas de valor, nao rotulos
        ok(rots and all(r[0] == r[0].lower() for r in rots), f"Rótulos dos KPIs ({sel}) com inicial minúscula: {rots}")
        pg.locator(sel).scroll_into_view_if_needed()
        pg.evaluate("window.scrollBy(0, -220)")
        pg.wait_for_timeout(300)
        pg.locator(sel).screenshot(path=f"{OUT}/kpis_{sel.replace('#', '').replace(' .', '_').replace('.', '_').replace(' ', '_')}.png")
    # cabecalho: sem logo e sem imagem embutida; titulo em uma linha a partir de 1280 px; alinhado ao conteudo
    fonte_html = open("painel_soberania_digital_v3.html", encoding="utf-8").read()
    ok("data:image/png;base64" not in fonte_html and pg.evaluate("document.querySelectorAll('.topo img').length") == 0,
       "Cabeçalho sem logo e sem imagem em base64 no HTML")
    aba("sobre")
    for largura in (1280, 1440):
        pg.set_viewport_size({"width": largura, "height": 900})
        pg.wait_for_timeout(300)
        h = pg.evaluate("""() => { const h1 = document.querySelector('.topo h1');
            return {linhas: Math.round(h1.getBoundingClientRect().height / parseFloat(getComputedStyle(h1).lineHeight)), cabe: h1.scrollWidth <= h1.clientWidth,
                    esq_topo: [...document.querySelectorAll('.topo .eyebrow, .topo h1, .topo p')].map(e => Math.round(e.getBoundingClientRect().left)),
                    esq_sobre: Math.round(document.querySelector('.aba[data-aba="sobre"]').getBoundingClientRect().left)}; }""")
        ok(h["linhas"] == 1 and h["cabe"] and all(x == h["esq_sobre"] == 44 for x in h["esq_topo"]),
           f"Cabeçalho em {largura} px: título em uma linha; texto na margem do botão Sobre (44 px) {h}")
        pg.evaluate("window.scrollTo(0, 0)")
        pg.mouse.move(5, 5)
        pg.wait_for_timeout(200)
        pg.screenshot(path=f"{OUT}/sobre_cabecalho_{largura}.png", clip={"x": 0, "y": 0, "width": largura, "height": 260})
    # numeros das tabelas nunca quebram de linha (todas as abas, 1280 e 1440 px)
    RX = r"^(R\$ )?(< )?-?[\d.]+(,\d+)?(%| bi| mi| mil| compras)?$"
    for largura in (1280, 1440):
        pg.set_viewport_size({"width": largura, "height": 900})
        for nome_aba in ("soberania", "metodologia"):
            aba(nome_aba)
            r = pg.evaluate("""(rx) => { const re = new RegExp(rx); let n = 0; const ruins = [];
                document.querySelectorAll('#aba-%s table td, #aba-%s table th').forEach(c => {
                  const t = c.innerText.trim(); if (!re.test(t)) return; n++;
                  const rg = document.createRange(); rg.selectNodeContents(c);
                  const tops = new Set([...rg.getClientRects()].filter(x => x.width > 0).map(x => Math.round(x.top)));
                  const numClasse = c.classList.contains('n'), nowrap = getComputedStyle(c).whiteSpace === 'nowrap';
                  if (tops.size > 1 || !numClasse || !nowrap) ruins.push([t, tops.size, numClasse, nowrap]); });
                return {n, ruins: ruins.slice(0, 10), nruins: ruins.length}; }""".replace("%s", nome_aba), RX)
            ok(r["n"] > 0 and r["nruins"] == 0, f"Tabelas da aba {nome_aba} em {largura} px: {r['n']} células numéricas, todas em uma linha, à direita e sem quebra {r['ruins']}")
        # trilha dos numeros
        aba("metodologia")
        trilha = pg.locator("table.tabela").filter(has_text="Registros depois").first
        trilha.scroll_into_view_if_needed()
        pg.evaluate("window.scrollBy(0, -160)")
        pg.wait_for_timeout(300)
        larg = pg.evaluate("() => { const t = [...document.querySelectorAll('table.tabela')].find(x => x.innerText.includes('Registros depois')); const w = t.closest('.tabela-wrap'); return [t.scrollWidth, w.clientWidth]; }")
        ok(True, f"Trilha dos números em {largura} px: largura da tabela {larg[0]} px no cartão de {larg[1]} px" + (" (rolagem horizontal)" if larg[0] > larg[1] else ""))
        trilha.screenshot(path=f"{OUT}/trilha_dos_numeros_{largura}.png")
    pg.set_viewport_size({"width": 1440, "height": 900})
    aba("sobre")
    rod = pg.inner_text("footer")
    ok("Elaboração Mabel Mota para discussão interna no Ipea" in rod, f"Rodapé: {rod}")

    aba("soberania")
    # ---------------- terminologia: tecnologias criticas para a soberania digital
    aba("soberania")
    pg.evaluate("window.scrollTo(0, 0)")
    rots = pg.evaluate("[document.getElementById('sd-kpi-v-rot').innerText, document.getElementById('sd-kpi-p-rot').innerText, document.querySelector('[data-conf=\"sobre_kpi_soberania\"]').nextElementSibling.innerText]")
    ok(rots == ["homologado em tecnologias críticas para a soberania digital (2021 a 2026)", "do valor homologado total (2021 a 2026)",
                "homologado em tecnologias críticas para a soberania digital (2021 a 2026)"], f"Rótulos dos KPIs de tecnologias críticas: {rots}")
    intro = pg.inner_text(".intro-sob")
    ok(intro.startswith("Esta seção apresenta as compras públicas de tecnologias críticas para a soberania digital.") and "(Comissão Europeia, 2023; Bria, Timmers e Gernone, 2025)" in intro
       and "não constituem medida direta de soberania digital" in intro and pg.inner_text("#aba-soberania h2.sec") == "Compras públicas de tecnologias críticas para a soberania digital",
       "Abertura da aba Tecnologias críticas para a soberania digital: título da seção e texto novo")
    # barra de abas em uma linha (1280 e 1440 px), com a aba ativa e fixa ao rolar
    for largura in (1280, 1440):
        pg.set_viewport_size({"width": largura, "height": 900})
        for rolagem in (0, 1500):
            pg.evaluate(f"window.scrollTo(0, {rolagem})")
            pg.wait_for_timeout(250)
            b = pg.evaluate("""() => { const bs = [...document.querySelectorAll('.abas .aba')];
                return {textos: bs.map(x => x.innerText), linhas_barra: new Set(bs.map(x => Math.round(x.getBoundingClientRect().top))).size,
                        botao_uma_linha: bs.every(x => x.getBoundingClientRect().height < 45), fonte: getComputedStyle(bs[0]).fontSize,
                        topo_barra: Math.round(document.getElementById('barra').getBoundingClientRect().top), ativa: document.querySelector('.aba.ativa').innerText}; }""")
            ok(b["textos"] == ["Sobre", "Compras públicas", "Tecnologias críticas para a soberania digital", "Inteligência artificial", "Metodologia"] and b["linhas_barra"] == 1
               and b["botao_uma_linha"] and b["fonte"] == "15px" and (rolagem == 0 or b["topo_barra"] == 0),
               f"Barra de abas em {largura} px, rolagem {rolagem}: uma linha, aba ativa '{b['ativa']}' {b}")
            if rolagem == 0:
                pg.screenshot(path=f"{OUT}/barra_abas_{largura}.png", clip={"x": 0, "y": 0, "width": largura, "height": 200})
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.evaluate("window.scrollTo(0, 0)")
    pg.wait_for_timeout(300)
    caixa = pg.locator(".intro-sob").bounding_box()
    pg.evaluate(f"window.scrollTo(0, {caixa['y'] - 230})")
    pg.wait_for_timeout(300)
    pg.locator(".intro-sob").screenshot(path=f"{OUT}/soberania_abertura.png")
    import io as _io
    import zipfile as _zip
    SD = "soberania" + " digital"  # montado por partes para que este script nao contenha as expressoes procuradas
    EXPR = [f"{p} de {SD}" for p in ("categorias", "categoria", "valor", "compras")] + [f"homologado em {SD}"]
    textos = {"painel_soberania_digital_v3.html": open("painel_soberania_digital_v3.html", encoding="utf-8").read(),
              "METODOLOGIA_v3.md": open("METODOLOGIA_v3.md", encoding="utf-8").read()}
    def ler_zip(nome, dados):
        z = _zip.ZipFile(_io.BytesIO(dados))
        for n in z.namelist():
            b = z.read(n)
            if n.endswith(".zip"):
                ler_zip(f"{nome}/{n}", b)
            else:
                textos[f"{nome}/{n}"] = b.decode("utf-8", "replace")
    ler_zip("pacote_downloads_v3.zip", open("pacote_downloads_v3.zip", "rb").read())
    achados = [(a, e, t.lower().count(e)) for a, t in textos.items() for e in EXPR if e in t.lower()]
    ok(not achados, f"Varredura de terminologia em {len(textos)} arquivos (HTML, METODOLOGIA_v3.md e pacote): {sum(x[2] for x in achados)} ocorrências {achados[:5]}")
    ABAS = ["aba " + "Soberania digital", "Painel das " + "compras públicas"]  # montado por partes (ver acima)
    achados_abas = [(a, e, t.count(e)) for a, t in textos.items() for e in ABAS if e in t]
    ok(not achados_abas, f"Varredura dos nomes antigos das abas em {len(textos)} arquivos: {sum(x[2] for x in achados_abas)} ocorrências {achados_abas[:5]}")
    json.dump({"arquivos": len(textos), "expressoes": EXPR + ABAS, "ocorrencias": achados + achados_abas}, open(f"{OUT}/varredura_terminologia.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)

    # textos do "i": definicao do valor homologado, palavras-chave dos cartoes e texto do grafico 5
    DEF = ("Valor global homologado: soma dos valores dos itens adjudicados aos fornecedores vencedores ao final da licitação ou da contratação direta, "
           "conforme registrado no PNCP. Não equivale ao valor contratado nem ao valor efetivamente pago.")
    USA_HOM = ["sobre_valor", "cp_valor", "sd_valor"]  # so os KPIs de valor
    tts = pg.evaluate("""() => Object.fromEntries([...document.querySelectorAll('.info[data-i]')].map(e => { const t = e.querySelector('.tt');
        return [e.dataset.i, {primeira: t.firstElementChild.textContent, rot: (t.querySelector('.tt-rot') || {}).textContent, txt: t.textContent,
                itens: t.querySelectorAll('.tt-lista li').length}]; }))""")
    com = sorted(k for k, v in tts.items() if v["primeira"] == DEF)
    ok(com == sorted(USA_HOM) and all(DEF not in v["txt"] for k, v in tts.items() if k not in USA_HOM),
       f"Definição do valor global homologado só nos {len(com)} KPIs de valor {com}; ausente nos demais {len([k for k in tts if k not in USA_HOM])} ícones i")
    cats_i = {k: v for k, v in tts.items() if k.startswith("cat_")}
    ok(len(cats_i) == 6 and all(v["rot"] == "Palavras-chave" and "Termos buscados no objeto da compra e na descrição dos itens:" in v["txt"]
                                and v["itens"] > 0 and "Verificação:" in v["txt"] and "Como interpretar" not in v["txt"] for v in cats_i.values()),
       f"Cartões das categorias: título PALAVRAS-CHAVE, frase de abertura, lista de termos e linha Verificação ({ {k: v['itens'] for k, v in cats_i.items()} } termos)")
    ok(pg.evaluate("getComputedStyle(document.querySelector('[data-i=cat_nuvem] .tt-rot')).textTransform") == "uppercase", "Título PALAVRAS-CHAVE em maiúsculas")
    g5 = pg.inner_text("#g5-txt")
    G5_PADRAO = ("Cada barra soma o valor das compras da categoria no ano. Uma compra classificada em duas categorias aparece nas duas; por isso a soma das barras supera "
                 f"o total das seis categorias ({conf['sd_kpi_valor']}), em que cada compra entra uma vez.")
    ok("aparece nas duas" not in g5 and G5_PADRAO in tts["g5"]["txt"],
       f"Gráfico 5: frase sobre dupla classificação só no i (texto executivo: {g5})")
    met = pg.evaluate("document.getElementById('aba-metodologia').textContent")
    i1, i2 = met.find("1. Fonte e cobertura"), met.find("2. Tratamento da base")
    ok(DEF in met[i1:i2] and DEF in open("METODOLOGIA_v3.md", encoding="utf-8").read().split("## 2.")[0], "Metodologia, seção Fonte e cobertura: definição do valor global homologado (painel e METODOLOGIA_v3.md)")
    # capturas: cartao de categoria e grafico com o "i" aberto
    for sel, nome in (("[data-i='cat_nuvem']", "i_cartao_categoria"), ("[data-i='g5']", "i_grafico5")):
        pg.locator(sel).scroll_into_view_if_needed()
        pg.evaluate(f"window.scrollBy(0, -250)")
        pg.wait_for_timeout(200)
        pg.hover(sel)
        pg.wait_for_timeout(300)
        ok(pg.evaluate("getComputedStyle(document.getElementById('tooltip')).display") == "block", f"Captura {nome}.png com o i aberto")
        pg.screenshot(path=f"{OUT}/{nome}.png")
        pg.mouse.move(5, 5)

    # ---------------- Parte 1 da v3: alternador nos exemplos e textos, termos, nota, selo, titulos, colunas, grafico 9
    NOTA = ("Todos os valores são homologados: soma dos itens adjudicados aos vencedores, conforme registrado no PNCP. "
            "Não equivalem ao valor contratado nem ao valor pago.")
    pg.mouse.move(5, 5)
    nt = pg.evaluate("""() => Object.fromEntries(['sobre', 'compras', 'soberania', 'metodologia'].map(a => { const s = document.getElementById('aba-' + a);
        return [a, [...s.querySelectorAll('.nota-valores')].map(e => [e.innerText, e === s.firstElementChild])]; }))""")
    ok(nt["compras"] == [[NOTA, True]] and nt["soberania"] == [[NOTA, True]] and not nt["sobre"] and not nt["metodologia"],
       f"Nota fixa logo abaixo das abas Compras públicas e Tecnologias críticas (e só nelas) {nt}")
    sl = pg.evaluate("""() => { const e = document.getElementById('selo-precisao'), c = getComputedStyle(e);
        return {t: e.innerText, ant: e.previousElementSibling.className, bg: c.backgroundColor, cor: c.color, fs: c.fontSize}; }""")
    _pf = [float(r["precisao_pct"]) for r in csv.DictReader(open("tabelas_painel_v3/pn_precisao_final.csv", encoding="utf-8"), delimiter=";")]
    _faixa = pg.evaluate(f"[fmtPct({min(_pf)}), fmtPct({max(_pf)})]")
    ok(sl["t"] == ("Classificação automatizada validada por amostragem. Exercício empírico, feito com palavras-chave sobre os textos do PNCP; "
                   f"precisão entre {_faixa[0]} e {_faixa[1]} por categoria.") and sl["ant"] == "nota-valores"
       and sl["bg"] == "rgb(238, 243, 250)" and sl["cor"] == "rgb(27, 74, 130)" and sl["fs"] == "13px",
       f"Selo da aba Tecnologias críticas abaixo da nota, fundo #EEF3FA, texto #1B4A82, 13 px; faixa de pn_precisao_final.csv {sl}")
    tit = pg.evaluate("[...document.querySelectorAll('main .tg2')].map(e => e.innerText)")
    ok(not [t for t in tit if t.startswith(("Valor homologado por", "Valor global homologado por"))]
       and all(pg.inner_text(f"#{i}-t2").startswith("Valor por ") for i in ("g2", "g3", "g4", "g5", "g7", "gm")) and pg.inner_text("#gv-t2").startswith("Valor nos resultados por "),
       f"Títulos 'Valor por...' {[pg.inner_text(f'#{i}-t2') for i in ('g2', 'g3', 'g4', 'g5', 'g7', 'gm', 'gv')]}")
    un = pg.evaluate("['g2', 'g3', 'g4', 'g5', 'g7', 'gm', 'gv'].map(i => document.getElementById(i + '-t2').nextElementSibling.innerText)")
    ok(all(u.startswith("(Em ") for u in un), f"Linha de unidade mantida abaixo dos títulos {un}")
    cab = pg.evaluate("['t1', 't2', 'tm'].map(i => [...document.querySelectorAll('#' + i + ' th')].map(t => t.innerText.replace(/[▲▼]/g, '').trim()))")
    ok(all("Valor (R$ mi)" in c for c in cab) and not any("Valor homologado" in x or "Valor nos resultados" in x for c in cab for x in c),
       f"Colunas de valor das tabelas: 'Valor (R$ mi)' {cab}")
    tt_all = pg.evaluate("[...document.querySelectorAll('.info .tt')].map(e => e.textContent)")
    ok(not [t for t in tt_all if "R$ 55,6" in t] and "R$ 55,6 bi" in pg.evaluate("document.getElementById('aba-metodologia').textContent"),
       "R$ 55,6 bi (compra inteira em cada categoria) fora dos ícones i e presente só na metodologia")
    ok(not [t for t in tt_all if "Valor global homologado:" in t and "soma dos valores dos itens adjudicados" in t][3:], "Bloco 'Valor global homologado' só nos três KPIs de valor")
    ttm = pg.evaluate("document.querySelector('[data-i=gm] .tt').textContent")
    _comp = list(csv.DictReader(open("tabelas_painel_v3/pn_modelo_grupo_componentes.csv", encoding="utf-8"), delimiter=";"))
    _vc = pg.evaluate(f"[mi({sum(round(float(r['valor_nominal']), 2) for r in _comp if r['ordem'] == '4')}), mi({sum(round(float(r['valor_nominal']), 2) for r in _comp if r['ordem'] == '0')})]")
    ok(f"Grupo de itens de desenvolvimento e serviços técnicos, equipamentos e itens sem indicação do modelo, cuja classificação automática não atingiu 80% de acerto na revisão humana. Inclui também suporte e manutenção de licença ({_vc[0]}) e compras sem itens com valor ({_vc[1]}). Valores nominais." in ttm,
       f"Gráfico 9: i com o texto do grupo, suporte e manutenção de licença ({_vc[0]}) e compras sem itens com valor ({_vc[1]}), de pn_modelo_grupo_componentes.csv")
    txt_tudo = pg.evaluate("document.body.innerText + ' ' + [...document.querySelectorAll('.tt')].map(e => e.textContent).join(' ') + ' ' + JSON.stringify(D.achados) + ' ' + JSON.stringify(D.ex)")
    met_md = open("METODOLOGIA_v3.md", encoding="utf-8").read()
    # A: nome da classe 3; busca no HTML, na metodologia e no pacote (busca_nome_classe_3.csv)
    import io, zipfile
    BUSCA = _re.compile(r"perp[eé]tu\w*|licen[çc]as? permanentes?", _re.I)

    def tipo_ocorrencia(arq, txt, m):
        if arq.endswith(("possiveis_duplicidades_processo_diferente.csv", "pn_cadeias_objetos.csv", "ia_objetos.csv")) or "fichas_ia_a" in arq or _no_objeto(txt, m.start(), m.end()):
            return "texto original do objeto da compra no PNCP"
        antes = txt[max(0, m.start() - 3):m.start()]
        if antes.endswith(("\\b", "(", "|")) or txt[max(0, m.start() - 10):m.end()].lower().endswith("processor perpetual"):
            return "expressão de busca do dicionário (texto do PNCP sem acento)"
        return "nome ou texto do painel"
    oc = []
    # objetos das compras (texto do PNCP, exibido na tabela 2): no HTML aparecem como texto e dentro dos dados (JSON)
    _objl = [r["objeto"] for a in ("pn_cadeias_objetos.csv", "ia_objetos.csv") for r in csv.DictReader(open("tabelas_painel_v3/" + a, encoding="utf-8"), delimiter=";")]
    _big = "\n".join(_objl) + "\n" + json.dumps(_objl, ensure_ascii=False, separators=(",", ":"))

    def _no_objeto(txt, a, b):
        return any(txt[max(0, a - k):b + k] in _big for k in (25, 12)) or txt[max(0, a - 25):b].split("…")[0] in _big

    def busca(arq, txt):
        for m in BUSCA.finditer(txt):
            oc.append([arq, m.group(0), tipo_ocorrencia(arq, txt, m), txt[max(0, m.start() - 60):m.end() + 30].replace("\n", " ").replace("\r", " ")])
    busca("painel_soberania_digital_v3.html", open("painel_soberania_digital_v3.html", encoding="utf-8").read())
    busca("painel_soberania_digital_v3.html (texto exibido nos dois modos)", txt_tudo)
    busca("METODOLOGIA_v3.md", met_md)
    _z = zipfile.ZipFile("pacote_downloads_v3.zip")
    for _n in _z.namelist():
        _d = _z.read(_n)
        for _m, _dd in ([(_n + "/" + x, zipfile.ZipFile(io.BytesIO(_d)).read(x)) for x in zipfile.ZipFile(io.BytesIO(_d)).namelist()] if _n.endswith(".zip") else [(_n, _d)]):
            try:
                busca("pacote_downloads_v3.zip/" + _m, _dd.decode("utf-8"))
            except UnicodeDecodeError:
                pass
    with open(f"{OUT}/busca_nome_classe_3.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["arquivo", "ocorrencia", "tipo", "trecho"])
        w.writerows(oc)
    _acento = [o for o in oc if "é" in o[1].lower() and o[2] != "texto original do objeto da compra no PNCP"]
    _painel = [o for o in oc if o[2] == "nome ou texto do painel"]
    ok(not _acento and not _painel and "licenciamento de direitos permanentes de uso" in txt_tudo.lower() and "Licenciamento de direitos permanentes de uso" in pg.evaluate("Chart.getChart(document.getElementById('gm')).data.datasets.map(d => d.label)")
       and "Licenciamento de direitos permanentes de uso: licença de software por prazo indeterminado, comprada uma vez. O nome segue o catálogo de compras do governo federal ('Licenciamento de Direitos Permanentes de Uso de Software')." in met_md,
       f"Nome 'Licenciamento de direitos permanentes de uso' em todo o painel, metodologia e pacote: {len(_acento)} ocorrências com acento e {len(_painel)} como nome ou texto; restam {len(oc)} ocorrências, todas em expressões de busca do dicionário ou em texto original do objeto da compra no PNCP {_painel[:3]}")
    _lpc = next(csv.DictReader(open("tabelas_painel_v3/pn_direitos_permanentes_codigo.csv", encoding="utf-8"), delimiter=";"))
    _lim = pg.evaluate(f"`No licenciamento de direitos permanentes de uso, ${{fmtPct({_lpc['pct_so_codigo_catalogo']})}} do valor (${{mi({_lpc['valor_so_codigo_catalogo']})}} de ${{mi({_lpc['valor_classe_total']})}}) foi identificado só pelo nome do código do catálogo ('Direitos Permanentes de Uso'). Há compras com esse código que descrevem licenças por prazo; o valor da classe é indicativo.`")
    ok(_lim in met_md and _lim in pg.evaluate("document.getElementById('aba-metodologia').textContent"), f"Limitação do licenciamento de direitos permanentes de uso na metodologia: {_lim}")
    # F: subtitulo da Tabela 1 (marcas) informa que o valor e o dos resultados
    _sub_tm = pg.evaluate("document.getElementById('tm-t2').nextElementSibling.innerText")
    ok("nos resultados" in _sub_tm and pg.inner_text("#gv-t2").startswith("Valor nos resultados por tipo de vendedor"), f"Tabela 1: subtítulo com o valor dos resultados {_sub_tm}")
    # G: concordancia entre revisoes na metodologia
    _cr = list(csv.DictReader(open("fase2/validacao/concordancia_entre_revisoes.csv", encoding="utf-8"), delimiter=";"))
    _cg = sum(r["concordam"] == "sim" for r in _cr)
    _tg = pg.evaluate(f"`${{inteiro({_cg})}} de ${{inteiro({len(_cr)})}} (${{fmtPct({100 * _cg / len(_cr)})}})`")
    ok(f"Concordância entre a revisão humana e a verificação por amostragem, nos mesmos casos: {_tg}." in met_md, f"Metodologia: concordância entre revisões {_tg}")
    # varredura de estilo: travessao, 'nao apenas' e 'estrategico' no texto visivel, nos i e na metodologia
    EST = ["—", "–", "não apenas", "Não apenas", "estratégic", "Estratégic"]
    _objs_est = "\n".join(r["objeto"] for a in ("pn_cadeias_objetos.csv", "ia_objetos.csv") for r in csv.DictReader(open("tabelas_painel_v3/" + a, encoding="utf-8"), delimiter=";"))
    _fora_obj = lambda t, e: [m.start() for m in _re.finditer(_re.escape(e), t) if not any(t[max(0, m.start() - k):m.end() + k] in _objs_est for k in (25, 12))
                              and t[max(0, m.start() - 25):m.end()].split("…")[0] not in _objs_est]
    # texto do painel e da metodologia (os objetos das compras, citados do PNCP na tabela 2, ficam fora da varredura de estilo)
    est = [(e, len(_fora_obj(txt_tudo, e)) + met_md.count(e)) for e in EST if _fora_obj(txt_tudo, e) or e in met_md]
    ok(not est, f"Sem travessão, 'não apenas' e 'estratégico' no painel e na metodologia {est}")

    # alternador: exemplos de leitura e textos com reais nos dois modos
    EXM = {(r["elemento"], r["modo"]): r["texto"] for r in csv.DictReader(open("tabelas_painel_v3/pn_exemplos_modos.csv", encoding="utf-8"), delimiter=";")}
    MODOS = {"nom": "valores nominais", "defl": "valores deflacionados"}
    FRASE = {"nom": pg.evaluate("D.modoTxt[0]"), "defl": pg.evaluate("D.modoTxt[1]")}
    SUF = lambda m: " " + FRASE[m]
    SEM_MODO = lambda t: not _re.search(r"\(valores |Valores nominais\.|Valores deflacionados", t)
    paren = []
    linhas_alt = []
    regra4 = []
    for m in ("nom", "defl"):
        for a in ("compras", "soberania"):
            aba(a)
            pg.click(f"#f-{a} [data-alt] button[data-v='{m}']")
            pg.wait_for_timeout(900)
            ex = pg.evaluate("""a => [...document.querySelectorAll('#aba-' + a + ' .ex-din')].map(e => [e.dataset.ex, e.textContent])""", a)
            for k, t in ex:
                esp = EXM[(k, MODOS[m])]
                reais_ = "R$" in t
                fim = t.endswith(SUF(m))
                okk = t == esp and (fim if reais_ else SEM_MODO(t)) and "(valores" not in t
                linhas_alt.append([a, ("nota do i: " if k.endswith("_nota") else "exemplo de leitura (i): ") + k, MODOS[m], t, "sim" if reais_ else "não", "sim" if fim else "não", esp, "sim" if okk else "não"])
            tx = pg.evaluate("""a => [...document.querySelectorAll('#aba-' + a + ' .texto-exec')].filter(e => e.innerText.trim()).map(e => [e.id, e.innerText])""", a)
            for k, t in tx:
                reais_ = "R$" in t
                fim = t.endswith(SUF(m))
                okk = (fim if reais_ else SEM_MODO(t)) and "(valores" not in t and ") (" not in t
                linhas_alt.append([a, "texto abaixo do gráfico: " + k, MODOS[m], t, "sim" if reais_ else "não", "sim" if fim else "não", "", "sim" if okk else "não"])
        # E: nenhum ") (" no texto exibido nem nos i, neste modo
        _tx = pg.evaluate("document.body.innerText + ' ' + [...document.querySelectorAll('.tt')].map(e => e.textContent).join(' ')")
        paren.append([MODOS[m], _tx.count(") ("), [_tx[max(0, i - 60):i + 40] for i in [x.start() for x in _re.finditer(r"\) \(", _tx)][:3]]])
        # regra 4: o mesmo numero com o mesmo arredondamento no grafico, no tooltip, no exemplo e no texto
        r4 = pg.evaluate("""() => { const c = Chart.getChart(document.getElementById('gm')), i = c.data.labels.indexOf('Nuvem'),
            ds = c.data.datasets.find(d => d.label === 'Subscrição ou serviço'), j = c.data.labels.indexOf('Plataformas e licenciamento');
            const g5 = soma(D.catAno.filter(r => D.cats[r[0]] === 'nuvem' && r[1] === 2025).map(r => r[3 + V()]));
            const nvd = c.data.datasets[c.data.datasets.length - 1], q = ['Data center', 'Segurança cibernética', 'Inteligência artificial', 'Identidade e infraestrutura pública digital'].map(n => nvd.data[c.data.labels.indexOf(n)]);
            return {nuvem: fmtPct(ds.data[i]), plat: fmtPct(ds.data[j]), g5: mi(g5), nvmin: fmtPct(Math.min(...q)), nvmax: fmtPct(Math.max(...q)),
                    ex_gm: document.querySelector('[data-ex=gm]').textContent, gm_txt: document.getElementById('gm-txt').innerText,
                    ex_g5: document.querySelector('[data-ex=g5]').textContent, kpi: document.getElementById('sd-kpi-v').innerText,
                    ex_sd: document.querySelector('[data-ex=sd_valor]').textContent}; }""")
        for nome, cond in ((f"Nuvem, subscrição ou serviço: tooltip e rótulo do gráfico 9 {r4['nuvem']}, exemplo e texto abaixo do gráfico",
                            f"respondeu por {r4['nuvem']} do valor" in r4["ex_gm"] and f"{r4['nuvem']} do valor em Nuvem" in r4["gm_txt"]),
                           (f"Plataformas, subscrição ou serviço: gráfico 9 {r4['plat']} e texto abaixo do gráfico", f"e {r4['plat']} em Plataformas" in r4["gm_txt"]),
                           (f"Grupo em Data center, Segurança, IA e Identidade: gráfico 9 entre {r4['nvmin']} e {r4['nvmax']} e texto abaixo do gráfico",
                            f"(entre {r4['nvmin']} e {r4['nvmax']})" in r4["gm_txt"]),
                           (f"Nuvem em 2025: gráfico 5 {r4['g5']} e exemplo", f"Nuvem somou {r4['g5']}" in r4["ex_g5"]),
                           (f"KPI de tecnologias críticas {r4['kpi']} e exemplo", f", {r4['kpi']} referem-se às seis categorias" in r4["ex_sd"])):
            regra4.append([MODOS[m], nome, "sim" if cond else "não"])
        if m == "nom":
            aba("soberania")
            pg.set_viewport_size({"width": 1440, "height": 1600})
            for sel, nome in (("#g5", "grafico5_nominal.png"), ("#gm", "grafico9.png")):
                card = pg.locator(sel).locator("xpath=ancestor::*[contains(@class,'graf-card')][1]")
                card.scroll_into_view_if_needed()
                pg.wait_for_timeout(600)
                card.screenshot(path=f"{OUT}/{nome}")
            pg.set_viewport_size({"width": 1440, "height": 900})
        else:
            aba("soberania")
            pg.set_viewport_size({"width": 1440, "height": 1600})
            card = pg.locator("#g5").locator("xpath=ancestor::*[contains(@class,'graf-card')][1]")
            card.scroll_into_view_if_needed()
            pg.wait_for_timeout(600)
            card.screenshot(path=f"{OUT}/grafico5_deflacionado.png")
            pg.set_viewport_size({"width": 1440, "height": 900})
    ex_sobre = pg.evaluate("document.querySelector('[data-i=sobre_participacao] .tt').textContent")
    linhas_alt.append(["sobre", "exemplo de leitura (i): sobre_participacao", "valores nominais", ex_sobre.split("Exemplo de leitura:")[1].strip(),
                       "sim", "sim" if ex_sobre.endswith(SUF("nom")) else "não", "", "sim" if ex_sobre.endswith(SUF("nom")) else "não"])
    with open(f"{OUT}/alternador_exemplos.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["aba", "elemento", "modo", "texto_exibido", "cita_reais", "termina_com_o_modo", "texto_gerado_pelos_dados", "confere"])
        w.writerows(linhas_alt)
    with open(f"{OUT}/regra4_mesmo_numero.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(["modo", "verificacao", "confere"])
        w.writerows(regra4)
    nm = sorted({x[1] for x in linhas_alt if x[2] == "valores nominais"} & {x[1] for x in linhas_alt if x[2] == MODOS["defl"]})
    ok(all(x[7] == "sim" for x in linhas_alt) and len(nm) >= 30,
       f"Alternador: {len(linhas_alt)} textos testados nos dois modos ({len(nm)} elementos), exemplos iguais aos gerados pelos dados e textos com reais terminando com o modo; falhas {[x[:4] for x in linhas_alt if x[7] != 'sim'][:4]}")
    ok(all(x[1] == 0 for x in paren), f"Nenhum ') (' no texto exibido e nos i, nos dois modos {paren}")
    ok(all(x[2] == "sim" for x in regra4), f"Regra 4: mesmo número e mesmo arredondamento no gráfico, no exemplo e no texto, nos dois modos {[x for x in regra4 if x[2] != 'sim']}")
    pg.click("#sd-limpar")
    pg.wait_for_timeout(600)
    pg.mouse.move(5, 5)

    # icone i
    pg.hover("[data-i='sd_valor']")
    pg.wait_for_timeout(300)
    ok(pg.evaluate("getComputedStyle(document.getElementById('tooltip')).display") == "block", "Ícone i mostra o texto ao passar o mouse")
    pg.screenshot(path=f"{OUT}/icone_i_soberania.png", clip={"x": 0, "y": 0, "width": 1440, "height": 900})
    nav.close()

erros = [c for c in R["console"] if c.startswith(("error", "pageerror"))]
ok(not erros, f"Console sem erros ({len(R['console'])} mensagens de erro ou aviso)")
ok(not R["requisicoes_bloqueadas"], f"Nenhuma requisição externa ({len(R['requisicoes_bloqueadas'])})")
json.dump(R, open(f"{OUT}/resultado_verificacao.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(conf, open(f"{OUT}/conf_painel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(textos_i, open(f"{OUT}/textos_i.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for m in R["ok"]:
    print("ok   ", m)
for m in R["falhas"]:
    print("FALHA", m)
for c in R["console"]:
    print("console", c)
print(f"{len(R['ok'])} verificações ok, {len(R['falhas'])} falhas")
sys.exit(1 if R["falhas"] else 0)
