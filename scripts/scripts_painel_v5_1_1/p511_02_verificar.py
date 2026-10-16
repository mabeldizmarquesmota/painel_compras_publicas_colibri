"""Painel v5.1.1, etapa 2: verificacoes obrigatorias (buscas no HTML e Chromium sem internet, 1440 px e 390 px).

Executar a partir de Processado/, depois de p511_01:  python scripts_painel_v5_1_1/p511_02_verificar.py
Entradas: painel_soberania_digital_v5_1_1.html; versao_congelada_v5_1/painel_soberania_digital_v5_1.html (somente leitura, referencia).
Verifica: buscas de texto (itens 2 a 4 do prompt, com o local de cada ocorrencia restante); abas carregam; cartoes de KPI identicos aos da
  v5.1 (texto, estilo calculado e posicao do i); graficos 8 e 9 clicaveis (clique num no filtra o diagrama e a tabela); console sem erros.
Saidas (verificacao_html_v5_1_1/): verificacoes.csv; buscas.csv; resultado.json.
"""
import csv
import json
import os
import re
import sys

from playwright.sync_api import sync_playwright

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
OUT = "verificacao_html_v5_1_1"
NOVO, V51 = "painel_soberania_digital_v5_1_1.html", "versao_congelada_v5_1/painel_soberania_digital_v5_1.html"
url = lambda a: "file:///" + os.path.abspath(a).replace("\\", "/")
RODAPE = ("Versão 5.1.1, gerada em 06/10/2026. Base extraída em 28/09/2026. Fonte: PNCP, via Colibri (gestaogovbr). Elaboração: Mabel Mota para discussão "
          "interna no Ipea. Ferramentas: Python 3.14.")
V = []


def ok(item, cond, detalhe):
    V.append([item, "sim" if cond else "não", detalhe])


# ---------------- buscas no HTML, com o local de cada ocorrencia
h = open(NOVO, encoding="utf-8").read()
i_met = h.find('<section class="aba-conteudo" id="aba-metodologia">')
f_met = h.find("</section>", i_met)
i_d = h.find("const D = ")
f_d = h.find(";\nconst ZIP", i_d)


def local(p):
    if i_met < p < f_met:
        return "aba Metodologia"
    if i_d < p < f_d:
        return "dados embutidos (objeto da compra, texto original do PNCP)"
    return "outro"


B = []
for termo in ("pacote_downloads_v5_1", "COPY (SELECT", "Os Parquet não fazem parte", "—", "Proibida a reprodução", RODAPE):
    oc = [(local(m.start()), h[max(0, m.start() - 70):m.start() + 50].replace("\n", " ")) for m in re.finditer(re.escape(termo), h)]
    for lo, ctx in oc or [("", "")]:
        B.append([termo[:60], len(oc), lo, ctx])
cont = lambda t: h.count(t)
ok("2. sem 'pacote_downloads_v5_1'", cont("pacote_downloads_v5_1") == 0, f"{cont('pacote_downloads_v5_1')} ocorrências")
ok("2. sem 'COPY (SELECT'", cont("COPY (SELECT") == 0, f"{cont('COPY (SELECT')} ocorrência(s), em: {sorted({local(m.start()) for m in re.finditer(re.escape('COPY (SELECT'), h)})}")
ok("2. sem 'Os Parquet não fazem parte'", cont("Os Parquet não fazem parte") == 0, f"{cont('Os Parquet não fazem parte')} ocorrências")
ok("3. rodapé novo exatamente uma vez", cont(RODAPE) == 1 and re.search(r"<footer>(.*?)</footer>", h).group(1) == RODAPE, f"{cont(RODAPE)} ocorrência(s), no <footer>")
ok("4. sem travessão (—)", cont("—") == 0, f"{cont('—')} ocorrência(s), em: {sorted({local(m.start()) for m in re.finditer('—', h)})}")
ok("4. sem 'Proibida a reprodução'", cont("Proibida a reprodução") == 0, f"{cont('Proibida a reprodução')} ocorrências")

# ---------------- navegador
JS_KPI = """() => [...document.querySelectorAll('.kpi')].map(k => { const s = getComputedStyle(k), n = k.querySelector('.num'), i = k.querySelector('.info'), r = k.getBoundingClientRect();
  const ri = i ? i.getBoundingClientRect() : null;
  return [k.closest('section').id, k.innerText.replace(/\\s+/g, ' '), s.borderTop, s.borderLeft, s.borderRadius, s.boxShadow, n ? getComputedStyle(n).color : '',
          Math.round(r.width), Math.round(r.height), ri ? [Math.round(r.right - ri.right), Math.round(ri.top - r.top)].join(',') : ''].join(' | '); })"""
cons = []
with sync_playwright() as pw:
    nav = pw.chromium.launch(headless=True)
    for larg in (1440, 390):
        kp = {}
        for arq in (V51, NOVO):
            ctx = nav.new_context(viewport={"width": larg, "height": 900}, offline=True)
            pg = ctx.new_page()
            if arq == NOVO:
                pg.on("console", lambda m, L=larg: cons.append(f"{L}px {m.type}: {m.text}") if m.type in ("error", "warning") else None)
                pg.on("pageerror", lambda e, L=larg: cons.append(f"{L}px pageerror: {e}"))
            pg.goto(url(arq))
            pg.wait_for_function("window.__pronto === true", timeout=60000)
            vis = []
            for a in ("sobre", "compras", "soberania", "ia", "metodologia"):
                pg.click(f".aba[data-aba='{a}']")
                pg.wait_for_timeout(700)
                vis.append(pg.evaluate("a => getComputedStyle(document.getElementById('aba-' + a)).display !== 'none' && document.getElementById('aba-' + a).innerText.length > 100", a))
            kp[arq] = []
            for a in ("sobre", "compras", "soberania"):
                pg.click(f".aba[data-aba='{a}']")
                pg.wait_for_timeout(600)
                kp[arq] += [x for x in pg.evaluate(JS_KPI) if x.startswith("aba-" + a)]
            if arq == NOVO:
                ok(f"5. todas as abas carregam ({larg} px)", all(vis), str(vis))
                pg.click(".aba[data-aba='metodologia']")
                pg.wait_for_timeout(400)
                corpo = pg.evaluate("document.body.innerText")
                ok(f"1. parágrafo fora da tela, botões de download mantidos ({larg} px)", "Os dois pacotes são os mesmos arquivos" not in corpo and pg.locator("#aba-metodologia .btn-dl").count() == 3,
                   f"{pg.locator('#aba-metodologia .btn-dl').count()} botões")
                ok(f"3. rodapé exibido igual ao texto ({larg} px)", pg.inner_text("footer") == RODAPE, pg.inner_text("footer")[:60])
                # graficos clicaveis: grafico 1 (alternador), grafico 8 e grafico 9 (clique num no de fornecedor filtra o diagrama e a tabela)
                for aba, svg, sk, tab in (("soberania", "#sankey", "window.__sk", "#t1"), ("ia", "#ia-sankey", "window.__skIA", "#ia-t")):
                    pg.click(f".aba[data-aba='{aba}']")
                    pg.wait_for_timeout(600)
                    e0 = pg.evaluate(f"[{sk}.total, document.querySelector('{tab} tbody').innerText.length]")
                    pg.locator(f"{svg} rect[data-no^='f']").nth(1).dispatch_event("click")
                    pg.wait_for_timeout(600)
                    e1 = pg.evaluate(f"[{sk}.total, document.querySelector('{tab} tbody').innerText.length]")
                    ok(f"5. gráfico {'8' if aba == 'soberania' else '9'} clicável: clique num fornecedor filtra o diagrama e a tabela ({larg} px)", e1[0] < e0[0] and e1[1] != e0[1], f"{e0} -> {e1}")
                pg.click(".aba[data-aba='compras']")
                pg.wait_for_timeout(500)
                t0 = pg.inner_text("#g1-t2")
                pg.click("#g1-sel button[data-m='qtd']")
                pg.wait_for_timeout(500)
                ok(f"5. gráfico 1 responde ao alternador Valor/Quantidade ({larg} px)", pg.inner_text("#g1-t2") != t0, pg.inner_text("#g1-t2")[:50])
            ctx.close()
        ok(f"5. cartões de KPI idênticos aos da v5.1 ({larg} px: texto, borda, cantos, sombra, cor do número, tamanho e posição do i)",
           kp[V51] == kp[NOVO] and len(kp[NOVO]) == 13, f"{len(kp[NOVO])} cartões; diferentes: {[x for x, y in zip(kp[V51], kp[NOVO]) if x != y][:2]}")
    nav.close()
ok("5. console sem erros nem avisos (1440 e 390 px)", not cons, str(cons[:3]))
with open(f"{OUT}/verificacoes.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["verificacao", "confere", "detalhe"])
    w.writerows(V)
with open(f"{OUT}/buscas.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["termo", "ocorrencias", "local", "contexto"])
    w.writerows(B)
json.dump({"verificacoes": V, "console": cons}, open(f"{OUT}/resultado.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
for v in V:
    print(v[1].upper().ljust(4), v[0], "|", v[2][:150])
