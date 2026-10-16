"""Painel v5, etapa 3: verificacao do HTML em Chromium headless, sem internet, em 1440 px e 390 px.

Executar a partir de Processado/, depois de p5_02:  python scripts_painel_v5/p5_03_verificar_html.py
Entradas: painel_soberania_digital_v5.html; painel_soberania_digital_v4.html (somente leitura, para medir a reducao das alturas);
  tabelas_painel_v3/pn_fluxo.csv, pn_fluxo_compras.csv, ia_resultados.csv (conferencia dos Sankeys).
Regras verificadas, nas duas larguras: console sem erros; sem rolagem horizontal; abas, filtros, alternador, sub-abas, cliques e icones "i"
  funcionando; ordem e titulos dos blocos; nenhum trecho excluido no Ajuste 5 visivel na tela; rotulos dos Sankeys sem sobreposicao.
  Grafico 9: os 5 botoes nos dois modos e um clique em cada tipo de no e num fluxo, com o total do grafico igual ao total da tabela de
  cadeias; Capacitacao so com a classe Capacitacao. Em 1440 px: alturas comparadas com as da v4; numeros exibidos (para p5_04);
  comparacao texto x grafico.
Saidas (verificacao_html_v5/): aba_sobre.png, aba_compras.png, aba_tecnologias.png, aba_ia_todas.png, aba_ia_capacitacao.png,
  aba_metodologia_topo.png; exclusoes.csv; grafico9_interacao.csv; resultado_verificacao.json; conf_painel.json; textos_i.json;
  alternador_exemplos.csv; sankey_conferencia.csv; ia_sankey_conferencia.csv; texto_grafico.csv; alturas_graficos.csv.
"""
import csv
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
OUT = "verificacao_html_v5"
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
EXCLUIDOS = [  # (item do Ajuste 5, trecho excluido ou substituido)
    ("1.1", "Use as abas acima para explorar os dados"),
    ("2.2", "A análise mostra quanto o poder público contratou via PNCP"),
    ("2.2", "Os indicadores anuais somam as compras publicadas em cada ano, enquanto os indicadores do período refletem os anos selecionados no filtro."),
    ("2.3", "Em 2024 e 2025, o setor público registrou cerca de 307 mil compras por ano."),
    ("2.3", "Das 875.682 compras publicadas, 710.197 têm valor homologado válido"),
    ("2.4", "De cada R$ 100 homologados no período"),
    ("2.5", "o maior valor anual foi o de"), ("2.5", "o ano com mais compras homologadas foi"), ("2.5", "De 2023 para 2025"),
    ("2.6", "não tem a esfera identificada na base"), ("2.7", "não tem o poder identificado na base"),
    ("3.1", "Esta seção apresenta as compras públicas de tecnologias críticas para a soberania digital"),
    ("3.1", "O que o Estado compra?"), ("3.1", "De quem o Estado compra?"), ("3.1", "O Estado usa o poder de compra a favor da oferta nacional?"),
    ("3.2", "Tecnologias selecionadas:"),
    ("3.3", "Escolha a categoria nos botões, no nó central ou num fluxo; clique num fornecedor ou órgão para ver só os fluxos desse nó."),
    ("3.3", "Maiores cadeias: fornecedor → objeto → órgão"), ("3.3", "cadeias por categoria, em ordem de valor"), ("3.3", "A tabela acompanha a seleção feita no gráfico 8."),
    ("3.3", "marcas citadas no recorte aparecem na tabela (pelo menos 20 compras com menção)"),
    ("3.4", "Os três campos estão preenchidos em 100% dos registros"), ("3.4", "campo preenchido em 100% dos registros"),
    ("3.4", "Nas seis categorias, foram identificadas 1 compra por encomenda tecnológica"),
    ("4.1", "Esta seção detalha as compras públicas de Inteligência Artificial"),
    ("4.2", "Nuvem/cloud broker"), ("4.3", "Outros objetos"),
    ("4.4", "Soluções de IA concentram o maior valor"), ("4.4", "Capacitação tem maior número de compras"), ("4.4", "Microsoft Copilot lidera o acréscimo de licenças"),
    ("4.4", "Valor das compras está concentrado em poucos fornecedores"),
    ("5.1", "Procedimentos e critérios"),
]
# texto visivel das abas (sem o conteudo dos icones i); a metodologia entra so pelo cabecalho da aba
JS_VISIVEL = """() => { const c = document.querySelector('main').cloneNode(true); c.querySelectorAll('.tt, #aba-metodologia > .card').forEach(e => e.remove());
  return [...c.querySelectorAll('section')].map(s => s.textContent).join(' '); }"""
JS_SOBREP = """sel => { const t = [...document.querySelectorAll(sel + ' svg text')].map(e => { const r = e.getBoundingClientRect(); return [r.left, r.right, r.top, r.bottom, e.textContent]; });
  const o = []; for (let i = 0; i < t.length; i++) for (let j = i + 1; j < t.length; j++) { const a = t[i], b = t[j];
    if (a[0] < b[1] && b[0] < a[1] && a[2] < b[3] - 0.5 && b[2] < a[3] - 0.5) o.push(a[4] + ' / ' + b[4]); } return o; }"""
ALT_ABA = {"compras": ["g1", "g2", "g3", "g4"], "soberania": ["g5", "g6", "g7", "sankey"], "ia": ["ia-sankey"]}
JS_ALT = """ids => Object.fromEntries(ids.map(id => [id, (id.endsWith('sankey') ? document.querySelector('#' + id + ' svg') : document.getElementById(id).parentElement).getBoundingClientRect().height]))"""
ORDEM_SD = ["h2.tit-laranja", ".intro-sob", "#sd-kpis", "#g5", "#g6", "#g7", "#sankey", "#t1", "#tm", "#ind-cartoes", "#achados"]
ORDEM_IA = ["h2.tit-laranja", ".texto-abertura", "#ia-sankey", "#ia-t", "#ia-marcas", "#ia-achados"]
BLOCOS_SD = ["Composição das compras por categoria tecnológica", "Modalidade de contratação", "Fornecedores, tecnologias e órgãos compradores",
             "Instrumentos de política pública associados às compras", "Síntese dos principais achados"]
TITULOS = {"compras": "Panorama das compras públicas", "soberania": "Compras públicas de tecnologias críticas para a soberania digital",
           "ia": "Compras públicas de inteligência artificial", "metodologia": "Procedimentos metodológicos"}


def mede_alturas(p):
    r = {}
    for a, ids in ALT_ABA.items():
        p.click(f".aba[data-aba='{a}']")
        p.wait_for_timeout(700)
        r.update(p.evaluate(JS_ALT, ids))
    return r


def captura(pg, nome):  # viewport com a altura da pagina (a captura full_page apaga os canvas)
    hh = pg.evaluate("document.documentElement.scrollHeight")
    pg.set_viewport_size({"width": 1440, "height": hh})
    pg.wait_for_timeout(1500)
    pg.screenshot(path=f"{OUT}/{nome}")
    pg.set_viewport_size({"width": 1440, "height": 900})
    pg.wait_for_timeout(600)


with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    alturas = {}
    ctx4 = nav.new_context(viewport={"width": 1440, "height": 900}, offline=True)
    p4 = ctx4.new_page()
    p4.goto(url("painel_soberania_digital_v4.html"))
    p4.wait_for_function("window.__pronto === true", timeout=60000)
    alturas["v4"] = mede_alturas(p4)
    ctx4.close()

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
        pg.goto(url("painel_soberania_digital_v5.html"))
        pg.wait_for_function("window.__pronto === true", timeout=60000)
        L = f"{largura} px"

        def aba(nome):
            pg.click(f".aba[data-aba='{nome}']")
            pg.wait_for_timeout(800)

        for a in ("sobre", "compras", "soberania", "ia", "metodologia"):
            aba(a)
            st = pg.evaluate("a => ({vis: getComputedStyle(document.getElementById('aba-' + a)).display !== 'none', ativa: document.querySelector('.aba.ativa').dataset.aba, "
                             "filtro: [...document.querySelectorAll('.filtros.visivel')].map(f => f.id), larg: document.documentElement.scrollWidth, "
                             "h2: (document.querySelector('#aba-' + a + ' h2.sec') || {}).innerText || ''})", a)
            ok(st["vis"] and st["ativa"] == a and st["filtro"] == ({"compras": ["f-compras"], "soberania": ["f-soberania"], "ia": ["f-ia"]}.get(a, []))
               and st["larg"] <= largura and st["h2"] == TITULOS.get(a, ""), f"{L}: aba {a} abre, com a barra de filtros certa, sem rolagem horizontal e título '{st['h2']}'")
        if largura == 1440:
            conf = {**pg.evaluate("Object.fromEntries([...document.querySelectorAll('[data-conf]')].map(e => [e.dataset.conf, e.textContent.trim()]))"),
                    **pg.evaluate("Object.assign({}, window.__conf)")}
            conf["achados_painel"] = pg.evaluate("[...document.querySelectorAll('#achados .achado')].map(a => a.querySelector('h4').innerText + '||' + a.querySelector('p').innerText)")
            conf["ia_achados_painel"] = pg.evaluate("[...document.querySelectorAll('#ia-achados .achado')].map(a => a.querySelector('h4').innerText + '||' + a.querySelector('p').innerText)")
            textos_i = pg.evaluate("() => Object.fromEntries([...document.querySelectorAll('.info[data-i]')].map(e => [e.dataset.i, e.querySelector('.tt').textContent]))")
            alturas["v5"] = mede_alturas(pg)
            est = pg.evaluate("""() => { const t = document.querySelector('#g1-txt'), d = document.createElement('div'); document.body.appendChild(d); d.style.color = '#4B5563';
              const r = [getComputedStyle(t).fontSize, getComputedStyle(t).color, getComputedStyle(d).color,
                         ...['compras', 'metodologia'].map(a => { const e = document.querySelector('#aba-' + a + ' h2.sec'); const s = getComputedStyle(e); return [s.fontSize, s.color, s.fontWeight].join(' '); })];
              d.remove(); return r; }""")
            ok(est[0] == "14px" and est[1] == est[2] and est[3] == est[4], f"Estilo: textos de interpretação em 14px e #4B5563; título da Metodologia igual ao das outras abas ({est})")

        # ordem e titulos dos blocos
        for a, ordem in (("soberania", ORDEM_SD), ("ia", ORDEM_IA)):
            aba(a)
            ys = pg.evaluate("([a, o]) => o.map(s => document.querySelector('#aba-' + a + ' ' + s).getBoundingClientRect().top)", [a, ordem])
            ok(all(ys[i] < ys[i + 1] for i in range(len(ys) - 1)), f"{L}: ordem dos blocos da aba {a}: {' > '.join(ordem)}")
        aba("soberania")
        bt = pg.evaluate("[...document.querySelectorAll('#aba-soberania .bloco-tit')].map(e => e.innerText)")
        ok(bt == BLOCOS_SD and pg.locator("#aba-soberania .cat-card").count() == 0, f"{L}: blocos da aba de tecnologias com os nomes novos e sem cartões das categorias ({bt})")
        aba("ia")
        ok(pg.evaluate("[...document.querySelectorAll('#aba-ia .bloco-tit')].map(e => e.innerText)") == ["Principais achados das compras públicas de IA"]
           and pg.evaluate("[...document.querySelectorAll('#ia-marcas th')].map(e => e.innerText)")[-1] == "Principais vendedores/revendedores",
           f"{L}: aba de IA com achados no fim e coluna 'Principais vendedores/revendedores'")

        # trechos excluidos: nenhum visivel
        vis = pg.evaluate(JS_VISIVEL)
        if largura == 1440:
            excl_vis = [vis.count(t) for _, t in EXCLUIDOS]
        ok(all(vis.count(t) == 0 for _, t in EXCLUIDOS), f"{L}: nenhum dos {len(EXCLUIDOS)} trechos excluídos aparece na tela ({[t for _, t in EXCLUIDOS if vis.count(t)]})")

        # icones i
        for a, chave, trechos in (("compras", "cp_abertura", ["Todos os valores são homologados"]),
                                  ("compras", "cp_compras", ["Como interpretar"]), ("compras", "cp_valor", ["Como interpretar"]),
                                  ("soberania", "sd_intro", ["Soberania digital é a capacidade de o Estado controlar os dados"]),
                                  ("soberania", "g5", ["Como interpretar", "Nota metodológica: Conceito, palavras-chave e verificação de cada categoria: ver Dicionário de termos por categoria, na aba Metodologia.", "Exemplo de leitura:"]),
                                  ("soberania", "g9", ["Os valores deste gráfico são o valor dos resultados (o homologado para cada fornecedor vencedor) e podem diferir dos gráficos por categoria, que usam o valor homologado das compras."]),
                                  ("soberania", "tm", ["A menção não comprova o produto entregue.", "pelo menos 20 compras"]),
                                  ("soberania", "g10", ["Como interpretar", "Nota metodológica: Os três campos estão preenchidos em 100% dos registros", "Encomenda tecnológica e CPSI: Nas seis categorias, foram identificadas 1 compra por encomenda tecnológica", "Exemplo de leitura:"]),
                                  ("ia", "ia_sankey", ["Nuvem com serviços de IA: contratos de nuvem cujo objeto cita serviços de inteligência artificial (por exemplo, créditos de nuvem com acesso a modelos de IA). O valor é o do contrato inteiro; o PNCP não permite separar a parte gasta com IA."]),
                                  ("ia", "ia_cadeias", ["Cada linha é uma cadeia"])):
            aba(a)
            el = pg.locator(f"#aba-{a} [data-i='{chave}']")
            el.scroll_into_view_if_needed()
            el.hover()
            pg.wait_for_timeout(300)
            tt = pg.evaluate("[getComputedStyle(document.getElementById('tooltip')).display, document.getElementById('tooltip').innerText.replace(/\\s+/g, ' '), document.getElementById('tooltip').getBoundingClientRect().right]")
            pos = [tt[1].lower().find(t.lower()) for t in trechos]  # o rotulo "Como interpretar" e exibido em caixa alta (CSS)
            ok(tt[0] == "block" and all(p >= 0 for p in pos) and pos == sorted(pos) and tt[2] <= largura, f"{L}: i {chave} abre e mostra, nesta ordem, {[t[:40] for t in trechos]}")
            if chave in ("cp_compras", "cp_valor"):
                ok("Exemplo de leitura" not in tt[1] and "Nota metodológica" not in tt[1], f"{L}: i {chave} sem exemplo de leitura nem nota")
            pg.mouse.move(2, 2)

        # filtros, alternador e sub-abas
        aba("compras")
        v0 = pg.inner_text("#cp-kpi-v")
        pg.select_option("#cp-esf", "0")
        pg.wait_for_timeout(500)
        ok(pg.inner_text("#cp-kpi-v") != v0, f"{L}: filtro de esfera altera o KPI de valor")
        pg.click("#cp-limpar")
        pg.wait_for_timeout(500)
        pg.click("#g1-sel button[data-m='qtd']")
        pg.wait_for_timeout(400)
        tq = pg.inner_text("#g1-txt")
        ok(tq.startswith("Foram homologadas ") and "; 2021 e 2022 têm cobertura parcial do PNCP, e 2026 vai até 24/05 (tom mais claro)." in tq and "ano com mais" not in tq,
           f"{L}: gráfico 1, modo Quantidade: só total e cobertura parcial ({tq})")
        pg.click("#g1-sel button[data-m='valor']")
        pg.wait_for_timeout(400)
        aba("soberania")
        k0, r0 = pg.inner_text("#sd-kpi-v"), pg.inner_text("#g9-resumo")
        pg.select_option("#sd-cat", "0")
        pg.wait_for_timeout(600)
        ok(pg.inner_text("#sd-kpi-v") != k0 and pg.inner_text("#g9-resumo") != r0, f"{L}: filtro de categoria altera KPI e linha-resumo do gráfico 8")
        pg.click("#sd-limpar")
        pg.wait_for_timeout(600)
        pg.click("#f-soberania [data-alt] button[data-v='defl']")
        pg.wait_for_timeout(700)
        ok(pg.inner_text("#sd-kpi-v") != k0 and pg.inner_text("#g10-txt").endswith("Valores deflacionados, a preços de agosto de 2026."), f"{L}: alternador muda os valores")
        pg.click("#f-soberania [data-alt] button[data-v='nom']")
        pg.wait_for_timeout(700)
        for m in ("n", "v"):
            pg.click(f"#sk-modo button[data-m='{m}']")
            pg.wait_for_timeout(500)
        ok(pg.evaluate("window.__sk.modo") == "v" and pg.inner_text("#sd-kpi-v") == k0, f"{L}: sub-abas do gráfico 8 e volta aos valores nominais")
        pg.locator("#sankey rect[data-no^='f']").nth(1).dispatch_event("click")  # em 390 px o no pode estar fora da area visivel da rolagem horizontal
        pg.wait_for_timeout(600)
        ok(pg.evaluate("!!E.sk") and pg.inner_text("#t1-t2").startswith("Principais relações entre fornecedores, objetos e órgãos compradores, 2021 a 2026 (fornecedor:"),
           f"{L}: clique num fornecedor do gráfico 8 filtra a tabela 1 ({pg.inner_text('#t1-t2')[:90]})")
        pg.click("#sd-limpar")
        pg.wait_for_timeout(500)

        # rotulos dos Sankeys
        sob = []
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
        ok(not sob, f"{L}: rótulos dos gráficos 8 e 9 sem sobreposição ({sob[:3]})")

        # grafico 9: botoes, modos e cliques; total do grafico x total da tabela de cadeias
        inter = []
        ESTADO = """() => { const s = window.__skIA, t = window.__iaTab;
          return {valor_g: s.total, valor_t: t.valor, compras_g: s.compras, compras_t: t.compras, classes: t.classes.map(c => D.ia.classes[c]),
                  tipos: t.tipos.map(c => D.ia.tipos[c]), nos: s.nos.filter(n => n[0][0] === 't').map(n => n[1]), sel: document.getElementById('ia-sel').innerText,
                  leg: [...document.querySelectorAll('#ia-leg span')].map(e => e.innerText), linhas: document.querySelectorAll('#ia-t tbody tr:not(.grupo)').length}; }"""

        def registra(acao):
            e = pg.evaluate(ESTADO)
            fmt = lambda x: pg.evaluate(f"mi({x})")
            iguais = abs(e["valor_g"] - e["valor_t"]) < 0.5 and e["compras_g"] == e["compras_t"] and e["linhas"] > 0
            inter.append([acao, f"{fmt(e['valor_g'])}; {e['compras_g']} compras", f"{fmt(e['valor_t'])}; {e['compras_t']} compras", "sim" if iguais else "não"])
            return e

        for f, nome in (("tec", "Todas"), ("acr", "Acréscimo à licença"), ("sol", "Solução de IA"), ("out", "Outros"), ("cap", "Capacitação")):
            for m, nm in (("v", "Valor"), ("n", "Nº de compras")):
                pg.click(f"#ia-filtros button[data-f='{f}']")
                pg.wait_for_timeout(400)
                pg.click(f"#ia-modo button[data-m='{m}']")
                pg.wait_for_timeout(400)
                e = registra(f"botão {nome}, modo {nm}")
                if f == "cap":
                    ok(e["classes"] == ["Capacitação"] and e["tipos"] == ["Capacitação"] and e["nos"] == ["Capacitação"] and e["leg"] == ["Capacitação"]
                       and pg.inner_text("#ia-desc-tit") == "Capacitação.", f"{L}: botão Capacitação, modo {nm}: só a classe Capacitação, com o nome certo no nó, na legenda e na frase do filtro")
                if f == "out":
                    ok("Capacitação" not in e["classes"] and "Capacitação" not in e["nos"], f"{L}: botão Outros sem compras de Capacitação")
            pg.click("#ia-modo button[data-m='v']")
            pg.wait_for_timeout(300)
        pg.click("#ia-filtros button[data-f='tec']")
        pg.wait_for_timeout(400)
        for tipo, rot in (("f", "fornecedor"), ("t", "tipo de objeto"), ("o", "órgão")):
            el = pg.locator(f"#ia-sankey rect[data-no^='{tipo}']").nth(1)
            el.scroll_into_view_if_needed()
            nome_no = pg.evaluate(f"window.__skIA.nos.find(n => n[0] === '{el.get_attribute('data-no')}')[1]")
            bb = el.bounding_box()
            pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
            pg.wait_for_timeout(500)
            e = registra(f"clique no nó de {rot}: {nome_no}")
            ok(e["sel"] == f"Seleção: {rot} {nome_no}" and e["valor_t"] < pg.evaluate("soma(iaLinhas(E.ia).map(ivf))"), f"{L}: clique no nó de {rot} filtra o gráfico e a tabela ({e['sel']})")
            pg.click("#ia-voltar")
            pg.wait_for_timeout(400)
        lk = pg.locator("#ia-sankey svg path").nth(4)
        lk.scroll_into_view_if_needed()
        bb = lk.bounding_box()
        alvo = pg.evaluate("""([x, y]) => { const el = document.elementFromPoint(x, y); return el && el.tagName === 'path' ? 1 : 0; }""", [bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2])
        pg.locator("#ia-sankey svg path").nth(4).dispatch_event("click") if not alvo else pg.mouse.click(bb["x"] + bb["width"] / 2, bb["y"] + bb["height"] / 2)
        pg.wait_for_timeout(500)
        e = registra("clique num fluxo: " + pg.inner_text("#ia-sel").replace("Seleção: ", ""))
        ok(e["sel"].startswith("Seleção: tipo de objeto ") and len(e["tipos"]) == 1, f"{L}: clique num fluxo filtra pelo tipo de objeto do fluxo ({e['sel']})")
        pg.click("#ia-voltar")
        pg.wait_for_timeout(400)
        ok(all(x[3] == "sim" for x in inter), f"{L}: gráfico 9, {len(inter)} ações com total do gráfico igual ao total da tabela de cadeias")
        if largura == 1440:
            grava("grafico9_interacao.csv", ["acao", "total_no_grafico", "total_na_tabela", "confere"], inter)

        if largura == 1440:
            # ---------------- capturas
            for a, nome in (("sobre", "aba_sobre.png"), ("compras", "aba_compras.png"), ("soberania", "aba_tecnologias.png"), ("ia", "aba_ia_todas.png")):
                aba(a)
                pg.evaluate("window.scrollTo(0, 0)")
                if a == "sobre":
                    pg.evaluate("document.querySelector('.carrossel .seta.esq').click()")  # pausa o carrossel no 1o cartao
                captura(pg, nome)
            pg.click("#ia-filtros button[data-f='cap']")
            pg.wait_for_timeout(500)
            captura(pg, "aba_ia_capacitacao.png")
            pg.click("#ia-limpar")
            aba("metodologia")
            pg.evaluate("window.scrollTo(0, 0)")
            pg.wait_for_timeout(400)
            pg.screenshot(path=f"{OUT}/aba_metodologia_topo.png")

            # ---------------- recortes filtrados (para p5_04)
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
                             "[...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(c => c.innerText)), document.getElementById('g10-nota').textContent, "
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
            aba("compras")
            conf["g1_txt"], conf["g2_txt"], conf["g3_txt"], conf["cp_abertura"] = [pg.inner_text(f"#{i}") for i in ("g1-txt", "g2-txt", "g3-txt", "aba-compras .texto-abertura p")]
            pg.click("#g1-sel button[data-m='qtd']")
            pg.wait_for_timeout(400)
            conf["g1_txt_qtd"] = pg.inner_text("#g1-txt")
            pg.click("#g1-sel button[data-m='valor']")
            pg.wait_for_timeout(400)
            conf["sd_abertura"] = pg.evaluate("document.querySelector('#aba-soberania .intro-sob p').innerText")
            conf["ia_abertura"] = pg.evaluate("document.querySelector('#aba-ia .texto-abertura p').innerText")
            aba("soberania")

            # ---------------- comparacao texto x grafico (recorte padrao, valores nominais)
            tg = pg.evaluate("""() => { const L = []; const c = id => Chart.getChart(document.getElementById(id)); const tx = id => document.getElementById(id).innerText;
              const g5 = c('g5'), tot5 = g5.data.datasets.map(d => [d.label, soma(d.data)]).sort((a, b) => b[1] - a[1]);
              L.push(['gráfico 5', tx('g5-txt'), `${tot5[0][0]} teve o maior valor homologado`, `(${mi(tot5[0][1])}), seguida de ${tot5[1][0]} (${mi(tot5[1][1])})`]);
              const g6 = c('g6'), lb6 = g6.data.labels.map(l => String(Array.isArray(l) ? l[0] : l)), p6 = a => fmtPct(g6.data.datasets[0].data[lb6.indexOf(a)]);
              L.push(['gráfico 6', tx('g6-txt'), `de ${p6('2023')} em 2023`, `para ${p6('2025')} em 2025`, `a média ponderada foi de ${document.getElementById('sd-kpi-p').innerText}`]);
              const g7 = c('g7'), i7 = n => g7.data.labels.indexOf(n), d7 = (k, n) => g7.data.datasets[k].data[i7(n)];
              L.push(['gráfico 7', tx('g7-txt'), `responderam por ${fmtPct(d7(0, 'Inexigibilidade') + d7(0, 'Dispensa'))} do valor`, `ante ${fmtPct(d7(1, 'Inexigibilidade') + d7(1, 'Dispensa'))} no total`,
                      `respondeu por ${fmtPct(d7(0, 'Inexigibilidade'))} do valor, ante ${fmtPct(d7(1, 'Inexigibilidade'))} no total`]);
              const ms = [...document.querySelectorAll('#tm tbody tr')].map(r => [...r.cells].map(x => x.innerText)), mic = ms.find(r => r[0] === 'Microsoft');
              L.push(['tabela 2', tx('tm-txt'), `Microsoft foi a marca citada em mais compras (${mic[1]})`, `ficaram com ${mic[3]} do valor`]);
              L.push(['indicadores de margem', tx('g10-txt'), `representaram ${document.getElementById('ind-prev').innerText} do valor`, `representaram ${document.getElementById('ind-apl').innerText} (`]);
              return L; }""")
            aba("compras")
            tg += pg.evaluate("""() => { const c = id => Chart.getChart(document.getElementById(id)), tx = id => document.getElementById(id).innerText, L = [];
              const g1 = c('g1'); L.push(['gráfico 1', tx('g1-txt'), `somou ${bi(soma(g1.data.datasets[0].data))} em`]);
              for (const [id, art] of [['g2', 'A esfera federal'], ['g3', 'O Poder Executivo']]) { const g = c(id), d = g.data.datasets[0].data, t = soma(d);
                L.push([id === 'g2' ? 'gráfico 2' : 'gráfico 3', tx(id + '-txt'), `${art} respondeu por ${fmtPct(100 * d[0] / soma(g.data.datasets[0].data.concat([])) * soma(d) / t)}`,
                        `(${bi(d[0])})`, `(${fmtPct(100 * d[1] / t)})`]); }
              return L; }""")
            aba("ia")
            ia_g = pg.evaluate("""() => { const s = window.__skIA, f = s.nos.filter(n => n[0][0] === 'f' && n[0] !== 'fD'), nf = +document.getElementById('ia-skresumo').innerText.match(/· ([\\d.]+) fornecedores/)[1].replace('.', '');
              return [document.querySelector('#ia-achados .achado:nth-child(4) p').innerText, `responderam por ${fmtPct(100 * soma(f.map(n => n[2])) / s.total)} do valor`, `um universo de ${inteiro(nf)} fornecedores`]; }""")
            tg.append(["achado 4 da IA x gráfico 9 (10 maiores fornecedores e linha-resumo)"] + ia_g)
            linhas_tg = []
            for r in tg:
                for trecho in r[2:]:
                    linhas_tg.append([r[0], r[1], trecho, "sim" if trecho in r[1] else "não"])
            grava("texto_grafico.csv", ["elemento", "texto_exibido", "trecho_calculado_do_grafico", "confere"], linhas_tg)
            ok(all(x[3] == "sim" for x in linhas_tg), f"Texto x gráfico: {sum(x[3] == 'sim' for x in linhas_tg)} de {len(linhas_tg)} números do texto iguais aos do gráfico")
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

# alturas: barras e linhas cerca de 25% abaixo da v4; Sankeys com a altura da v4
alt_l = []
for k in alturas["v4"]:
    a4, a5 = alturas["v4"][k], alturas["v5"][k]
    red = 100 * (1 - a5 / a4)
    alvo = (-1, 1) if k.endswith("sankey") else (20, 30)
    alt_l.append([k, round(a4), round(a5), round(red, 1), f"{alvo[0]} a {alvo[1]}", "sim" if alvo[0] <= red <= alvo[1] else "não"])
grava("alturas_graficos.csv", ["grafico", "altura_v4_px", "altura_v5_px", "reducao_pct", "faixa_esperada_pct", "confere"], alt_l)
ok(all(x[5] == "sim" for x in alt_l), f"Alturas: {[(x[0], x[3]) for x in alt_l]}")

# exclusoes: aparece na tela (1440 px e 390 px) e onde o trecho ainda esta no arquivo
h = open("painel_soberania_digital_v5.html", encoding="utf-8").read()
i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
i_d = h.find("const D = ")
f_d = h.find(";\nconst ZIP", i_d)
marc = h[h.find("<main>"):h.find("<script>")]
marc_sem_tt = re.sub(r"<span class='tt'>.*?</span></span>", "", marc, flags=re.S)
linhas_exc = []
for (it, t), v in zip(EXCLUIDOS, excl_vis):
    linhas_exc.append([it, t, "sim" if v else "não", (marc.count(t) - marc_sem_tt.count(t)), h[f_d:].count(t), h[i_d:f_d].count(t), h[i_met:f_met].count(t)])
grava("exclusoes.csv", ["item", "trecho", "aparece na tela", "dentro_de_icone_i", "codigo_javascript", "dados_embutidos", "metodologia"], linhas_exc)
ok(all(x[2] == "não" for x in linhas_exc), f"Exclusões: {sum(x[2] == 'não' for x in linhas_exc)} de {len(linhas_exc)} com 'aparece na tela: não'")
ok(not R["console"], f"Console sem erros nem avisos nas duas larguras ({R['console'][:3]})")
ok(not R["requisicoes_bloqueadas"], "Nenhuma requisição externa")
json.dump(R, open(f"{OUT}/resultado_verificacao.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(conf, open(f"{OUT}/conf_painel.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(textos_i, open(f"{OUT}/textos_i.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for f_ in R["falhas"]:
    print("FALHA", f_)
print(f"{len(R['ok'])} verificações ok; {len(R['falhas'])} falhas; capturas: {sorted(x for x in os.listdir(OUT) if x.endswith('.png'))}")
sys.exit(1 if R["falhas"] else 0)
