"""Painel v4, etapa 3: verificacao do HTML em Chromium headless, sem internet, em 1440 px e 390 px.

Executar a partir de Processado/, depois de p4_02:  python scripts_painel_v4/p4_03_verificar_html.py
Entradas: painel_soberania_digital_v4.html; painel_soberania_digital_v3.html (somente leitura, para medir a reducao das alturas);
  tabelas_painel_v3/pn_fluxo.csv, pn_fluxo_compras.csv, ia_resultados.csv (conferencia dos Sankeys).
Regras verificadas, nas duas larguras: console sem erros; sem rolagem horizontal da pagina; abas, filtros, alternador, sub-abas
  dos Sankeys e icones "i" funcionando; ordem dos blocos das abas de tecnologias criticas e de IA; nenhum texto excluido visivel
  (itens 2.1, 3.2, 3.3 e 4.1 do Ajuste 4); rotulos dos Sankeys sem sobreposicao em todos os filtros e modos. Em 1440 px: alturas dos
  graficos comparadas com as da v3; numeros exibidos no recorte padrao e nos recortes filtrados (para p4_04); comparacao texto x grafico.
Saidas (verificacao_html_v4/): aba_compras_topo.png, aba_tecnologias_topo.png, aba_tecnologias_i_cartao_nuvem.png,
  aba_tecnologias_completa.png, aba_ia_completa.png; resultado_verificacao.json; conf_painel.json; textos_i.json;
  alternador_exemplos.csv; sankey_conferencia.csv; ia_sankey_conferencia.csv; texto_grafico.csv; textos_excluidos.csv; alturas_graficos.csv.
"""
import csv
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
OUT = "verificacao_html_v4"
os.makedirs(OUT, exist_ok=True)
url = lambda arq: "file:///" + os.path.abspath(arq).replace("\\", "/")
R = {"falhas": [], "ok": [], "console": [], "requisicoes_bloqueadas": []}


def ok(cond, msg):
    (R["ok"] if cond else R["falhas"]).append(msg)
    return cond


def grava(nome, cab, linhas):
    with open(f"{OUT}/{nome}", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(linhas)


ler = lambda n: list(csv.DictReader(open(n, encoding="utf-8"), delimiter=";"))
EXCLUIDOS = [  # (item do Ajuste 4, trecho)
    ("2.1", "Todos os valores são homologados: soma dos itens adjudicados aos vencedores"),
    ("2.2", "Panorama geral"), ("2.3", "Quanto o poder público brasileiro contratou por meio do PNCP"),
    ("3.1", "Os achados se referem ao período completo"), ("3.1", "18.574 compras de tecnologias críticas para a soberania digital somaram"),
    ("3.1", "Camada tecnológica"), ("3.1", "Como o Estado contrata essas tecnologias e de quem depende"), ("3.1", "Como o Estado compra?"),
    ("3.2", "Classificação automatizada validada por amostragem"), ("3.2", "Classificação por palavras-chave verificada por amostragem e por revisão humana"),
    ("3.2", "segundo a forma de contratação da tecnologia"), ("3.2", "Valor por modelo de aquisição"), ("3.2", "Valor nos resultados por tipo de vendedor"),
    ("3.2", "Indicadores de porte"), ("3.2", "Concentração de fornecedores por categoria"), ("3.2", "Perfil das compras por categoria"),
    ("3.2", "maiores fornecedores receberam"), ("3.2", "Margem de preferência por NCM"), ("3.2", "Limitação da informação"),
    ("3.3", "o valor passou de"), ("3.4", "quase sempre com"), ("3.5", "Busca por encomenda tecnológica e contrato público"),
    ("4.1", "Tecnologia de IA:"), ("4.1", "Capacitação em IA:"), ("4.1", "O que mais se compra"), ("4.1", "Quem mais vende"), ("4.1", "Quem mais compra"),
    ("4.1", "Os 10 maiores fornecedores receberam 72%"), ("4.1", "Classificação por palavras-chave verificada por amostragem"),
    ("5.2", "Gráfico 10"), ("5.2", "Gráfico 11"), ("5.2", "Gráfico 12"), ("5.2", "Tabela 4"), ("5.2", "Tabela 5"), ("5.2", "Tabela 6"),
    ("4.2", "Solução de IA lidera a tecnologia de IA"), ("4.2", "539 fornecedores"),
]
JS_VISIVEL = """() => { const c = document.querySelector('main').cloneNode(true); c.querySelectorAll('.tt, #aba-metodologia').forEach(e => e.remove());
  return [...c.querySelectorAll('section')].map(s => s.textContent).join(' '); }"""
JS_SOBREP = """sel => { const t = [...document.querySelectorAll(sel + ' svg text')].map(e => { const r = e.getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom, e.textContent]; });
  const o = []; for (let i = 0; i < t.length; i++) for (let j = i + 1; j < t.length; j++) { const a = t[i], b = t[j];
    if (a[0] < b[1] && b[0] < a[1] && a[2] < b[3] - 0.5 && b[2] < a[3] - 0.5) o.push(a[4] + ' / ' + b[4]); } return o; }"""
ALT_ABA = {"compras": ["g1", "g2", "g3", "g4"], "soberania": ["g5", "g6", "g7", "sankey"], "ia": ["ia-sankey"]}
JS_ALT = """ids => Object.fromEntries(ids.map(id => [id, (id.endsWith('sankey') ? document.querySelector('#' + id + ' svg') : document.getElementById(id).parentElement).getBoundingClientRect().height]))"""


def mede_alturas(p):
    r = {}
    for a, ids in ALT_ABA.items():
        p.click(f".aba[data-aba='{a}']")
        p.wait_for_timeout(700)
        r.update(p.evaluate(JS_ALT, ids))
    return r


ORDEM_SD = ["h2.tit-laranja", ".intro-sob .sel-tit", ".intro-sob .cats", "#achados", "#sd-kpis", "#g5", "#g6", "#g7", "#sankey", "#t1", "#tm", "#ind-cartoes", "#nota-encomenda"]
ORDEM_IA = ["h2.tit-laranja", ".texto-abertura", "#ia-achados", "#ia-sankey", "#ia-t", "#ia-marcas"]

with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    alturas = {}
    # alturas da v3 (mesma largura), so para medir a reducao
    ctx3 = nav.new_context(viewport={"width": 1440, "height": 900}, offline=True)
    p3 = ctx3.new_page()
    p3.goto(url("painel_soberania_digital_v3.html"))
    p3.wait_for_function("window.__pronto === true", timeout=60000)
    alturas["v3"] = mede_alturas(p3)
    ctx3.close()

    for largura in (1440, 390):
        ctx = nav.new_context(viewport={"width": largura, "height": 900}, offline=True, accept_downloads=True)
        pg = ctx.new_page()

        def rota(route):
            if route.request.url.startswith(("file:", "data:", "blob:")):
                route.continue_()
            else:
                R["requisicoes_bloqueadas"].append(route.request.url)
                route.abort()

        pg.route("**/*", rota)
        pg.on("console", lambda m, L=largura: R["console"].append(f"{L}px {m.type}: {m.text}") if m.type in ("error", "warning") else None)
        pg.on("pageerror", lambda e, L=largura: R["console"].append(f"{L}px pageerror: {e}"))
        pg.goto(url("painel_soberania_digital_v4.html"))
        pg.wait_for_function("window.__pronto === true", timeout=60000)
        L = f"{largura} px"

        def aba(nome):
            pg.click(f".aba[data-aba='{nome}']")
            pg.wait_for_timeout(800)

        # abas
        for a in ("sobre", "compras", "soberania", "ia", "metodologia"):
            aba(a)
            st = pg.evaluate("a => ({vis: getComputedStyle(document.getElementById('aba-' + a)).display !== 'none', ativa: document.querySelector('.aba.ativa').dataset.aba, "
                             "filtro: [...document.querySelectorAll('.filtros.visivel')].map(f => f.id), larg: document.documentElement.scrollWidth})", a)
            ok(st["vis"] and st["ativa"] == a and st["filtro"] == ({"compras": ["f-compras"], "soberania": ["f-soberania"], "ia": ["f-ia"]}.get(a, []))
               and st["larg"] <= largura, f"{L}: aba {a} abre, com a barra de filtros certa e sem rolagem horizontal ({st})")
        if largura == 1440:
            conf = {**pg.evaluate("Object.fromEntries([...document.querySelectorAll('[data-conf]')].map(e => [e.dataset.conf, e.textContent.trim()]))"),
                    **pg.evaluate("Object.assign({}, window.__conf)")}
            conf["achados_painel"] = pg.evaluate("[...document.querySelectorAll('#achados .achado')].map(a => a.querySelector('h4').innerText + '||' + a.querySelector('p').innerText)")
            conf["ia_achados_painel"] = pg.evaluate("[...document.querySelectorAll('#ia-achados .achado')].map(a => a.querySelector('h4').innerText + '||' + a.querySelector('p').innerText)")
            textos_i = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('.info[data-i]')].map(e => [e.dataset.i, e.querySelector('.tt').textContent]))")
            alturas["v4"] = mede_alturas(pg)

        # ordem dos blocos
        for a, ordem in (("soberania", ORDEM_SD), ("ia", ORDEM_IA)):
            aba(a)
            ys = pg.evaluate("([a, o]) => o.map(s => document.querySelector('#aba-' + a + ' ' + s).getBoundingClientRect().top)", [a, ordem])
            ok(all(ys[i] < ys[i + 1] for i in range(len(ys) - 1)), f"{L}: ordem dos blocos da aba {a}: {' > '.join(ordem)}")
        aba("soberania")
        nc = pg.evaluate("[...document.querySelectorAll('.intro-sob .cat-card')].map(c => [Math.round(c.getBoundingClientRect().top), c.cloneNode(true).querySelector('.cat-topo') && (() => { const k = c.cloneNode(true); k.querySelectorAll('.info').forEach(e => e.remove()); return k.innerText.trim(); })()])")
        linhas_c = len({t for t, _ in nc})
        ok(len(nc) == 6 and linhas_c == (1 if largura == 1440 else 3) and all("\n" not in t for _, t in nc),
           f"{L}: seis cartões das categorias em {linhas_c} linha(s), só com o nome ({[t for _, t in nc]})")

        # textos excluidos: nenhum visivel
        aba("ia")
        vis = pg.evaluate(JS_VISIVEL)
        exc = [[it, t, vis.count(t)] for it, t in EXCLUIDOS]
        ok(all(x[2] == 0 for x in exc), f"{L}: nenhum dos {len(EXCLUIDOS)} trechos excluídos aparece no texto visível das abas")
        if largura == 1440:
            excl_vis = exc

        # icones i
        aba("compras")
        for a, chave, trecho in (("compras", "cp_abertura", "Todos os valores são homologados: soma dos itens adjudicados aos vencedores, conforme registrado no PNCP. Não equivalem ao valor contratado nem ao valor pago."),
                                 ("soberania", "sd_intro", "Soberania digital é a capacidade de o Estado controlar os dados"),
                                 ("soberania", "cat_nuvem", "Conceito: Capacidade de processamento e armazenamento contratada como serviço"),
                                 ("ia", "ia_cadeias", "Cada linha é uma cadeia"), ("ia", "ia_sankey", "A espessura de cada fluxo")):
            aba(a)
            el = pg.locator(f"#aba-{a} [data-i='{chave}']")
            el.scroll_into_view_if_needed()
            el.hover()
            pg.wait_for_timeout(300)
            tt = pg.evaluate("[getComputedStyle(document.getElementById('tooltip')).display, document.getElementById('tooltip').innerText, document.getElementById('tooltip').getBoundingClientRect().right]")
            ok(tt[0] == "block" and trecho in tt[1] and tt[2] <= largura, f"{L}: i {chave} abre ao passar o mouse e mostra '{trecho[:60]}'")
            if largura == 1440 and chave == "cat_nuvem":
                pg.screenshot(path=f"{OUT}/aba_tecnologias_i_cartao_nuvem.png")
            pg.mouse.move(2, 2)
        t_nuvem = pg.evaluate("document.querySelector('[data-i=cat_nuvem] .tt').innerText")
        ok(t_nuvem.index("Conceito:") < t_nuvem.index("Palavras-chave:") < t_nuvem.index("Verificação:"), f"{L}: i do cartão Nuvem na ordem Conceito, Palavras-chave, Verificação")

        # filtros, alternador e sub-abas
        aba("compras")
        v0 = pg.inner_text("#cp-kpi-v")
        pg.select_option("#cp-esf", "0")
        pg.wait_for_timeout(500)
        ok(pg.inner_text("#cp-kpi-v") != v0, f"{L}: filtro de esfera altera o KPI de valor ({v0} -> {pg.inner_text('#cp-kpi-v')})")
        pg.click("#cp-limpar")
        pg.wait_for_timeout(500)
        aba("soberania")
        k0, r0 = pg.inner_text("#sd-kpi-v"), pg.inner_text("#g9-resumo")
        pg.select_option("#sd-cat", "0")
        pg.wait_for_timeout(600)
        ok(pg.inner_text("#sd-kpi-v") != k0 and pg.inner_text("#g9-resumo") != r0 and pg.evaluate("document.querySelector('#sk-cats button.ativo').dataset.cat") == "0",
           f"{L}: filtro de categoria altera KPI, linha-resumo e botão do gráfico 8")
        pg.click("#sd-limpar")
        pg.wait_for_timeout(600)
        pg.click("#f-soberania [data-alt] button[data-v='defl']")
        pg.wait_for_timeout(700)
        kd = pg.inner_text("#sd-kpi-v")
        g5d = pg.inner_text("#g5-txt")
        ok(kd != k0 and pg.inner_text("#g10-txt").endswith("Valores deflacionados, a preços de agosto de 2026.") and not g5d.endswith(".  Valores deflacionados, a preços de agosto de 2026.")
           and "Valores" not in g5d, f"{L}: alternador muda os valores ({k0} -> {kd}); gráfico 5 sem a frase do modo ({g5d})")
        pg.click("#f-soberania [data-alt] button[data-v='nom']")
        pg.wait_for_timeout(700)
        ok(pg.inner_text("#sd-kpi-v") == k0, f"{L}: alternador volta aos valores nominais")
        for m in ("n", "v"):
            pg.click(f"#sk-modo button[data-m='{m}']")
            pg.wait_for_timeout(500)
        ok(pg.evaluate("window.__sk.modo") == "v", f"{L}: sub-abas Valor e Nº de compras do gráfico 8")
        aba("ia")
        s0 = pg.inner_text("#ia-skresumo")
        pg.select_option("#ia-ini", "2025")
        pg.wait_for_timeout(600)
        ok(pg.inner_text("#ia-skresumo") != s0, f"{L}: filtro de ano da aba de IA altera a linha-resumo do gráfico 9")
        pg.click("#ia-limpar")
        pg.wait_for_timeout(600)
        for f in ("acr", "sol", "out", "cap", "tec"):
            pg.click(f"#ia-filtros button[data-f='{f}']")
            pg.wait_for_timeout(400)
            ok(pg.evaluate("window.__skIA.f") == f and pg.locator("#ia-t tbody tr").count() > 0, f"{L}: botão {f} do gráfico 9 redesenha o diagrama e a tabela de cadeias")
        pg.click("#ia-modo button[data-m='n']")
        pg.wait_for_timeout(400)
        ok(pg.evaluate("window.__skIA.modo") == "n", f"{L}: sub-aba Nº de compras do gráfico 9")
        pg.click("#ia-modo button[data-m='v']")
        pg.wait_for_timeout(400)

        # rotulos dos Sankeys: nenhuma sobreposicao, em todos os filtros e modos
        sob = []
        aba("soberania")
        for c in range(-1, 6):
            for m in "vn":
                pg.evaluate(f"E.sd.cat = {c}; E.sk = null; E.skModo = '{m}'; renderSoberania()")
                pg.wait_for_timeout(120)
                sob += [f"gráfico 8, categoria {c}, modo {m}: {x}" for x in pg.evaluate(JS_SOBREP, "#sankey")]
        pg.click("#sd-limpar")
        aba("ia")
        for f in ("tec", "acr", "sol", "out", "cap"):
            for m in "vn":
                pg.evaluate(f"E.ia.f = '{f}'; E.ia.modo = '{m}'; E.ia.sk = null; renderIA()")
                pg.wait_for_timeout(120)
                sob += [f"gráfico 9, {f}, modo {m}: {x}" for x in pg.evaluate(JS_SOBREP, "#ia-sankey")]
        pg.click("#ia-limpar")
        pg.wait_for_timeout(500)
        ok(not sob, f"{L}: rótulos dos gráficos 8 e 9 sem sobreposição em 7 recortes de categoria e 5 filtros de IA, nos dois modos ({sob[:3]})")

        if largura == 1440:
            # ---------------- capturas
            pg.set_viewport_size({"width": 1440, "height": 900})
            aba("compras")
            pg.evaluate("window.scrollTo(0, 0)")
            pg.wait_for_timeout(500)
            pg.screenshot(path=f"{OUT}/aba_compras_topo.png")
            aba("soberania")
            pg.evaluate("window.scrollTo(0, 0)")
            pg.wait_for_timeout(500)
            pg.screenshot(path=f"{OUT}/aba_tecnologias_topo.png")
            for a, nome in (("soberania", "aba_tecnologias_completa.png"), ("ia", "aba_ia_completa.png")):
                aba(a)
                hh = pg.evaluate("document.documentElement.scrollHeight")
                pg.set_viewport_size({"width": 1440, "height": hh})
                pg.wait_for_timeout(1500)
                pg.screenshot(path=f"{OUT}/{nome}")
                pg.set_viewport_size({"width": 1440, "height": 900})
                pg.wait_for_timeout(600)

            # ---------------- recortes filtrados (para p4_04)
            aba("soberania")
            for c in range(6):
                cc = pg.evaluate(f"D.cats[{c}]")
                pg.select_option("#sd-cat", str(c))
                pg.wait_for_timeout(500)
                rs = pg.evaluate("() => [document.getElementById('g9-resumo').innerText, document.getElementById('sd-kpi-f').innerText, document.getElementById('sd-kpi-o').innerText, "
                                 "[...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(c => c.innerText))]")
                conf[f"g9_resumo_{cc}"], conf[f"sd_kpi_forn_{cc}"], conf[f"sd_kpi_org_{cc}"] = rs[:3]
                for l in rs[3]:
                    if len(l) == 8:
                        conf[f"tm_{l[0]}_{cc}"] = "|".join(l[1:])
            pg.click("#sd-limpar")
            pg.wait_for_timeout(500)
            pg.select_option("#sd-ini", "2025")
            pg.select_option("#sd-fim", "2025")
            pg.wait_for_timeout(600)
            rs = pg.evaluate("() => [document.getElementById('g9-resumo').innerText, document.getElementById('sd-kpi-f').innerText, document.getElementById('sd-kpi-o').innerText, "
                             "[...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(c => c.innerText)), document.getElementById('g10-nota').innerText, "
                             "document.getElementById('g10-txt').innerText, document.getElementById('ind-prev').innerText]")
            conf["g9_resumo_2025"], conf["sd_kpi_forn_2025"], conf["sd_kpi_org_2025"] = rs[:3]
            for l in rs[3]:
                if len(l) == 8:
                    conf[f"tm_{l[0]}_2025"] = "|".join(l[1:])
            conf["g10_texto1_2025"], conf["g10_texto2_2025"], conf["g10_prevista_pct_2025"] = rs[4:]
            pg.click("#sd-limpar")
            pg.wait_for_timeout(600)
            conf["g10_texto2"] = pg.inner_text("#g10-txt")
            conf["g5_txt"] = pg.inner_text("#g5-txt")

            # ---------------- comparacao texto x grafico (recorte padrao, valores nominais)
            tg = pg.evaluate("""() => { const L = []; const c = id => Chart.getChart(document.getElementById(id)); const tx = id => document.getElementById(id).innerText;
              const g5 = c('g5'), tot5 = g5.data.datasets.map(d => [d.label, soma(d.data)]).sort((a, b) => b[1] - a[1]);
              L.push(['gráfico 5', tx('g5-txt'), `${tot5[0][0]} teve o maior valor homologado`, `(${mi(tot5[0][1])}), seguida de ${tot5[1][0]} (${mi(tot5[1][1])})`]);
              const g6 = c('g6'), lb6 = g6.data.labels.map(l => String(Array.isArray(l) ? l[0] : l)), p6 = a => fmtPct(g6.data.datasets[0].data[lb6.indexOf(a)]);
              L.push(['gráfico 6', tx('g6-txt'), `de ${p6('2023')} em 2023`, `para ${p6('2025')} em 2025`, `a média ponderada foi de ${document.getElementById('sd-kpi-p').innerText}`]);
              const g7 = c('g7'), i7 = n => g7.data.labels.indexOf(n), d7 = (k, n) => g7.data.datasets[k].data[i7(n)];
              L.push(['gráfico 7', tx('g7-txt'), `responderam por ${fmtPct(d7(0, 'Inexigibilidade') + d7(0, 'Dispensa'))} do valor`, `ante ${fmtPct(d7(1, 'Inexigibilidade') + d7(1, 'Dispensa'))} no total`,
                      `respondeu por ${fmtPct(d7(0, 'Inexigibilidade'))} do valor, ante ${fmtPct(d7(1, 'Inexigibilidade'))} no total`]);
              const g1 = c('g1'); L.push(['gráfico 1', tx('g1-txt'), `somou ${bi(soma(g1.data.datasets[0].data))}`, `(${bi(Math.max(...g1.data.datasets[0].data))})`]);
              const ms = [...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(x => x.innerText)), mic = ms.find(r => r[0] === 'Microsoft');
              L.push(['tabela 2', tx('tm-txt'), `Microsoft foi a marca citada em mais compras (${mic[1]})`, `ficaram com ${mic[3]} do valor`]);
              L.push(['indicadores de margem', tx('g10-txt'), `representaram ${document.getElementById('ind-prev').innerText} do valor`, `representaram ${document.getElementById('ind-apl').innerText} (`]);
              return L; }""")
            aba("ia")
            ia_g = pg.evaluate("""() => { const s = window.__skIA, f = s.nos.filter(n => n[0][0] === 'f' && n[0] !== 'fD'), nf = +document.getElementById('ia-skresumo').innerText.match(/· ([\\d.]+) fornecedores/)[1].replace('.', '');
              return [document.querySelector('#ia-achados .achado:nth-child(4) p').innerText, `concentraram ${fmtPct(100 * soma(f.map(n => n[2])) / s.total)} do valor`, `um universo de ${inteiro(nf)} fornecedores`]; }""")
            tg.append(["achado 4 da IA x gráfico 9 (10 maiores fornecedores e linha-resumo)"] + ia_g)
            linhas_tg = []
            for r in tg:
                for trecho in r[2:]:
                    linhas_tg.append([r[0], r[1], trecho, "sim" if trecho in r[1] else "não"])
            grava("texto_grafico.csv", ["elemento", "texto_exibido", "trecho_calculado_do_grafico", "confere"], linhas_tg)
            ok(all(x[3] == "sim" for x in linhas_tg), f"Texto x gráfico: {sum(x[3] == 'sim' for x in linhas_tg)} de {len(linhas_tg)} números do texto iguais aos do gráfico")

            # ---------------- Sankey da IA: filtros, para p4_04
            for fk in ("tec", "acr", "sol", "out", "cap"):
                pg.click(f"#ia-filtros button[data-f='{fk}']")
                pg.wait_for_timeout(400)
            conf.update({k: v for k, v in pg.evaluate("Object.assign({}, window.__conf)").items() if k.startswith("ia_")})
            pg.click("#ia-limpar")
            pg.wait_for_timeout(400)

            # ---------------- conferencia dos Sankeys nos dois modos
            aba("soberania")
            _fl, _fc = ler("tabelas_painel_v3/pn_fluxo.csv"), ler("tabelas_painel_v3/pn_fluxo_compras.csv")
            CATS_ = pg.evaluate("D.cats")
            conf_sk = []
            for ci in [-1] + list(range(len(CATS_))):
                rot = "Todas" if ci < 0 else pg.evaluate(f"D.nome[D.cats[{ci}]]")
                pg.click(f"#sk-cats button[data-cat='{ci}']")
                pg.wait_for_timeout(500)
                selc = (lambda r: True) if ci < 0 else (lambda r, c=CATS_[ci]: r["categoria"] == c)
                tot = sum(round(float(r["valor_nominal"]), 2) for r in _fl if selc(r))
                pf = {(r["categoria"], r["id_compra"], r["cnpj_fornecedor"]) for r in _fc if selc(r)}
                po = {(r["categoria"], r["id_compra"], r["orgao"]) for r in _fc if selc(r)}
                cp = {r["id_compra"] for r in _fc if selc(r)}
                for m in ("v", "n"):
                    pg.click(f"#sk-modo button[data-m='{m}']")
                    pg.wait_for_timeout(500)
                    g = pg.evaluate("window.__sk")
                    esq = sum(x[2] for x in g["links"] if x[0][0] == "f")
                    dirr = sum(x[2] for x in g["links"] if x[1][0] == "o")
                    if m == "v":
                        fmt = lambda x: pg.evaluate(f"mi({x})")
                        for med, a_, b_ in (("soma dos fluxos fornecedor → categoria", esq, tot), ("soma dos fluxos categoria → órgão", dirr, tot)):
                            conf_sk.append([rot, "Valor", med, fmt(a_), fmt(b_), "tabelas_painel_v3/pn_fluxo.csv (valor_nominal)", "sim" if abs(a_ - b_) < 0.5 and fmt(a_) == fmt(b_) else "não"])
                    else:
                        for med, a_, b_ in (("soma dos fluxos fornecedor → categoria (cada compra uma vez por fornecedor)", esq, len(pf)),
                                            ("soma dos fluxos categoria → órgão (cada compra uma vez por órgão)", dirr, len(po)),
                                            ("compras distintas na linha-resumo", g["compras"], len(cp))):
                            conf_sk.append([rot, "Nº de compras", med, str(int(a_)), str(b_), "tabelas_painel_v3/pn_fluxo_compras.csv", "sim" if int(a_) == b_ else "não"])
                pg.click("#sk-modo button[data-m='v']")
                pg.wait_for_timeout(300)
            pg.click("#sd-limpar")
            grava("sankey_conferencia.csv", ["filtro", "modo", "medida", "valor_no_grafico", "valor_calculado", "arquivo_de_origem", "confere"], conf_sk)
            aba("ia")
            _ir = ler("tabelas_painel_v3/ia_resultados.csv")
            CLS_IA = pg.evaluate("D.ia.classes")
            FILT_IA = {k: [CLS_IA[i] for i in c] for k, _, c in pg.evaluate("D.ia.filtros")}
            conf_ia = []
            for fk in ("tec", "acr", "sol", "out", "cap"):
                pg.click(f"#ia-filtros button[data-f='{fk}']")
                pg.wait_for_timeout(400)
                rs_ = [r for r in _ir if r["classe"] in FILT_IA[fk]]
                tot = sum(round(float(r["valor_nominal"]), 2) for r in rs_)
                pf = {(r["id_compra"], r["cnpj_fornecedor"]) for r in rs_}
                po = {(r["id_compra"], r["orgao"]) for r in rs_}
                cp = {r["id_compra"] for r in rs_}
                for m in ("v", "n"):
                    pg.click(f"#ia-modo button[data-m='{m}']")
                    pg.wait_for_timeout(400)
                    g = pg.evaluate("window.__skIA")
                    esq = sum(x[2] for x in g["links"] if x[0][0] == "f")
                    dirr = sum(x[2] for x in g["links"] if x[1][0] == "o")
                    if m == "v":
                        fmt = lambda x: pg.evaluate(f"mi({x})")
                        for med, a_, b_ in (("soma dos fluxos fornecedor → tipo de objeto", esq, tot), ("soma dos fluxos tipo de objeto → órgão", dirr, tot)):
                            conf_ia.append([fk, "Valor", med, fmt(a_), fmt(b_), "tabelas_painel_v3/ia_resultados.csv (valor_nominal)", "sim" if abs(a_ - b_) < 0.5 and fmt(a_) == fmt(b_) else "não"])
                    else:
                        for med, a_, b_ in (("soma dos fluxos fornecedor → tipo de objeto (cada compra uma vez por fornecedor)", esq, len(pf)),
                                            ("soma dos fluxos tipo de objeto → órgão (cada compra uma vez por órgão)", dirr, len(po)),
                                            ("compras distintas na linha-resumo do gráfico", g["compras"], len(cp))):
                            conf_ia.append([fk, "Nº de compras", med, str(int(a_)), str(b_), "tabelas_painel_v3/ia_resultados.csv", "sim" if int(a_) == b_ else "não"])
                pg.click("#ia-modo button[data-m='v']")
                pg.wait_for_timeout(300)
            pg.click("#ia-limpar")
            grava("ia_sankey_conferencia.csv", ["filtro", "modo", "medida", "valor_no_grafico", "valor_calculado", "arquivo_de_origem", "confere"], conf_ia)

            # ---------------- alternador: exemplos de leitura e textos com reais nos dois modos
            FRASE = {"nom": pg.evaluate("D.modoTxt[0]"), "defl": pg.evaluate("D.modoTxt[1]")}
            MODOS = {"nom": "valores nominais", "defl": "valores deflacionados"}
            alt = []
            for m in ("nom", "defl"):
                for a in ("compras", "soberania", "ia"):
                    aba(a)
                    pg.click(f"#f-{a} [data-alt] button[data-v='{m}']")
                    pg.wait_for_timeout(700)
                    for k, t in pg.evaluate("a => [...document.querySelectorAll('#aba-' + a + ' .ex-din')].map(e => [e.dataset.ex, e.textContent])", a):
                        alt.append([a, "exemplo de leitura (i): " + k, MODOS[m], t, "sim" if "R$" in t else "não", "sim" if t.endswith(" " + FRASE[m]) else "não", "", "não se aplica"])
                    for k, t in pg.evaluate("a => [...document.querySelectorAll('#aba-' + a + ' .texto-exec')].filter(e => e.innerText.trim()).map(e => [e.id, e.innerText])", a):
                        fim = t.endswith(" " + FRASE[m])
                        okk = (not fim and "Valores" not in t) if k == "g5-txt" else (fim if "R$" in t else not re.search(r"Valores nominais\.|Valores deflacionados", t))
                        alt.append([a, "texto abaixo do gráfico: " + k, MODOS[m], t, "sim" if "R$" in t else "não", "sim" if fim else "não", "", "sim" if okk else "não"])
            pg.click("#f-ia [data-alt] button[data-v='nom']")
            ex_s = pg.evaluate("document.querySelector('[data-i=sobre_participacao] .tt').textContent")
            alt.append(["sobre", "exemplo de leitura (i): sobre_participacao", "valores nominais", ex_s.split("Exemplo de leitura:")[1].strip(), "sim",
                        "sim" if ex_s.endswith(" " + FRASE["nom"]) else "não", "", "não se aplica"])
            grava("alternador_exemplos.csv", ["aba", "elemento", "modo", "texto_exibido", "cita_reais", "termina_com_o_modo", "texto_gerado_pelos_dados", "confere"], alt)
            ok(all(x[7] != "não" for x in alt), "Alternador: textos abaixo dos gráficos terminam com o modo dos valores quando citam reais; o do gráfico 5 não tem a frase do modo")
        ctx.close()
    nav.close()

# alturas: barras e linhas cerca de 35% menores; Sankeys cerca de 20%
alt_l = []
for k in alturas["v3"]:
    a3, a4 = alturas["v3"][k], alturas["v4"][k]
    red = 100 * (1 - a4 / a3)
    alvo = (15, 25) if k.endswith("sankey") else (30, 40)
    alt_l.append([k, round(a3), round(a4), round(red, 1), f"{alvo[0]} a {alvo[1]}", "sim" if alvo[0] <= red <= alvo[1] else "não"])
grava("alturas_graficos.csv", ["grafico", "altura_v3_px", "altura_v4_px", "reducao_pct", "faixa_esperada_pct", "confere"], alt_l)
ok(all(x[5] == "sim" for x in alt_l), f"Alturas: {[(x[0], x[3]) for x in alt_l]}")

# textos excluidos: presenca no HTML (fora da metodologia), com o lugar de cada ocorrencia
h = open("painel_soberania_digital_v4.html", encoding="utf-8").read()
i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
i_d = h.find("const D = ")
f_d = h.find(";\nconst ZIP", i_d)
marc = h[h.find("<main>"):i_met] + h[f_met:h.find("<script>")]
marc_sem_tt = re.sub(r"<span class='tt'>.*?</span></span>", "", marc, flags=re.S)
codigo = h[h.rfind("<script>"):i_d] + h[f_d:]
dados = h[i_d:f_d]
linhas_exc = []
for (it, t), v in zip(EXCLUIDOS, excl_vis):
    n_tt = marc.count(t) - marc_sem_tt.count(t)
    linhas_exc.append([it, t, v[2], marc_sem_tt.count(t), n_tt, codigo.count(t), dados.count(t), h[i_met:f_met].count(t)])
grava("textos_excluidos.csv", ["item", "trecho", "texto_visivel_1440", "marcacao_visivel_html", "dentro_de_icone_i", "codigo_javascript", "dados_embutidos", "metodologia"], linhas_exc)
ok(all(x[2] == 0 and x[3] == 0 and x[5] == 0 for x in linhas_exc), "HTML: nenhum trecho excluído na marcação visível nem no código; ocorrências restantes só em ícone i pedido, dados ou metodologia (textos_excluidos.csv)")
ok(not R["console"], f"Console sem erros nem avisos nas duas larguras ({R['console'][:3]})")
ok(not R["requisicoes_bloqueadas"], "Nenhuma requisição externa")
json.dump(R, open(f"{OUT}/resultado_verificacao.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(conf, open(f"{OUT}/conf_painel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(textos_i, open(f"{OUT}/textos_i.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f_ in R["falhas"]:
    print("FALHA", f_)
print(f"{len(R['ok'])} verificações ok; {len(R['falhas'])} falhas; capturas: {sorted(x for x in os.listdir(OUT) if x.endswith('.png'))}")
sys.exit(1 if R["falhas"] else 0)
