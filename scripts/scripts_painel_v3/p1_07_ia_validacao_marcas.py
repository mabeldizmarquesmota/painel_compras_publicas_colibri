"""Painel v3, etapa 7: verificacao das classes, marcas de IA citadas e planilha de revisao humana da aba Inteligencia artificial.
Executar a partir de Processado/, depois de p1_06 e dos julgamentos (validacao_ia/julgamentos_ia_a1.py a _a4.py):
  python scripts_painel_v3/p1_07_ia_validacao_marcas.py
Entradas: tabelas_painel_v3/ia_base.csv; validacao_ia/fichas_ia_a*.csv e julgamentos_ia_a*.csv; tabelas_painel_v3/dicionario_ia_marcas.csv;
  scripts_parte0/p0.duckdb (somente leitura: bl, pb, res, forn_nome); itens_dedup.parquet.
Regras:
  - precisao da classe = fichas pertinentes / fichas julgadas na ultima rodada em que a regra da classe mudou (a1: dicionario
    versao 1; a2: versao 2; a3: versao 3, segundo e ultimo ajuste; a classe Acrescimo a licenca nao mudou na versao 3 e fica
    com a rodada a2); classe com menos de 80% e somada a Outros (classe_final);
  - marcas: termo da marca (dicionario_ia_marcas.csv) no texto do item, no objeto ou na informacao complementar, em todas as
    compras da base do painel (2021 a 2026), sem corte minimo; termo de exclusao no mesmo texto descarta a mencao. Valor =
    valor homologado da compra quando a marca esta no objeto ou na informacao complementar; senao, resultados dos itens que
    citam a marca (limitado ao homologado da compra). Vendedores = os mesmos resultados, pelo CNPJ do vencedor;
  - revisao humana: 10 compras por classe (20 em Solucao de IA), sorteadas por hash com a semente ia_revisao_humana
    entre as fichas da ultima rodada de cada classe; os julgamentos anteriores ficam em arquivo separado. A planilha ja
    revisada fica congelada: se validacao_ia/revisao_humana_ia.xlsx existe, ela nao e regravada; as compras sao lidas da
    copia validacao_ia/revisao_humana_ia_marcada_v1.xlsx e so o arquivo de julgamentos anteriores e refeito com elas.
Saidas: tabelas_painel_v3/ia_precisao_classes.csv, ia_classes_final.csv, ia_marcas.csv, ia_marcas_mencoes.csv;
  validacao_ia/revisao_humana_ia.xlsx; validacao_ia/revisao_humana_ia_julgamentos_anteriores.csv
"""
import csv
import hashlib
import os
import re

import duckdb
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font

TP, V = "tabelas_painel_v3/", "validacao_ia/"
SOL = "Solução de IA (exclusiva ou em pacote)"
ler = lambda n: list(csv.DictReader(open(n, encoding="utf-8"), delimiter=";"))


def grava(nome, cab, rows):
    with open(nome, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)


# classes finais: IA exclusiva e Pacote multi-software somadas numa classe (a fronteira entre elas e ambigua), medida
# numa amostra nova (ia_a4), sem mudar o dicionario
CLASSES = ["Capacitação", "Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)", "Outros"]
RODADAS = [("ia_a1", "versão 1"), ("ia_a2", "versão 2"), ("ia_a3", "versão 3"), ("ia_a4", "versão 3, classes somadas")]
FINAL = {"Capacitação": "ia_a3", "Acréscimo à licença": "ia_a2", "Solução de IA (exclusiva ou em pacote)": "ia_a4", "Outros": "ia_a3"}
TODAS_CLASSES = ["Capacitação", "Acréscimo à licença", "IA exclusiva", "Pacote multi-software", "Solução de IA (exclusiva ou em pacote)", "Outros"]
fichas = {s: ler(V + f"fichas_{s}.csv") for s, _ in RODADAS}
julg = {s: {r["ficha"]: r for r in ler(V + f"julgamentos_{s}.csv")} for s, _ in RODADAS}
prec, linhas = {}, []
for s, dic in RODADAS:
    for c in TODAS_CLASSES:
        js = [julg[s][f["ficha"]] for f in fichas[s] if f["classe"] == c]
        if not js:
            continue
        p = sum(j["pertinente"] == "sim" for j in js)
        pct = 100 * p / len(js)
        if FINAL.get(c) == s:
            prec[c] = pct
        linhas.append([c, s, dic, len(js), p, pct, "sim" if FINAL.get(c) == s else "não"])
sit = {c: "validada" if prec[c] >= 80 else "não validada" for c in CLASSES}
assert all(v == "validada" for v in sit.values()), sit
grava(TP + "ia_precisao_classes.csv", ["classe", "rodada", "dicionario", "compras_julgadas", "pertinentes", "precisao_pct", "rodada_final"], linhas)
base = ler(TP + "ia_base.csv")
final = {r["id_compra"]: (r["classe"] if sit[r["classe"]] == "validada" else "Outros") for r in base}
grava(TP + "ia_classes_final.csv", ["id_compra", "classe_dicionario", "classe_final"], [[r["id_compra"], r["classe_dicionario"], final[r["id_compra"]]] for r in base])

# ---------------------------------------------------------------- marcas de IA citadas
dm = ler(TP + "dicionario_ia_marcas.csv")
MARCAS = list(dict.fromkeys(r["marca"] for r in dm))
inc = {m: "|".join(r["termo"] for r in dm if r["marca"] == m and r["tipo"] == "inclusao") for m in MARCAS}
exc = {m: "|".join(r["termo"] for r in dm if r["marca"] == m and r["tipo"] == "exclusao") for m in MARCAS}
TODAS = "|".join(f"({p})" for p in inc.values())
con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
oc = con.sql(f"""
SELECT 'objeto ou informação complementar' AS onde, id_compra, NULL AS item, strip_accents(lower(coalesce(objeto_compra, '') || ' ' || coalesce(informacao_complementar, ''))) AS t
FROM bl WHERE regexp_matches(strip_accents(lower(coalesce(objeto_compra, '') || ' ' || coalesce(informacao_complementar, ''))), '{TODAS}')
UNION ALL
SELECT 'texto do item', i.id_compra, i.id_compra_item, strip_accents(lower(coalesce(descricao, '') || ' ' || coalesce(descricao_detalhada, '') || ' ' || coalesce(descricao_resumida, '')))
FROM read_parquet('itens_dedup.parquet') i WHERE i.id_compra IN (SELECT id_compra FROM bl)
  AND regexp_matches(strip_accents(lower(coalesce(descricao, '') || ' ' || coalesce(descricao_detalhada, '') || ' ' || coalesce(descricao_resumida, ''))), '{TODAS}')""").fetchall()
men = []
for onde, c, i, t in oc:
    for m in MARCAS:
        x = re.search(inc[m], t)
        if x and not (exc[m] and re.search(exc[m], t)):
            men.append([m, c, i or "", onde, t[max(0, x.start() - 80):x.end() + 60].replace("\n", " ")])
grava(TP + "ia_marcas_mencoes.csv", ["marca", "id_compra", "id_compra_item", "onde", "trecho"], men)
pbh = dict(con.sql("SELECT id_compra, hom FROM pb").fetchall())
fat = dict(con.sql("SELECT id_compra, fator FROM pb").fetchall())
ids_c = sorted({x[1] for x in men})
res = con.sql("""SELECT r.id_compra, r.id_compra_item, coalesce(nullif(trim(r.ni_fornecedor), ''), 'ND'), r.v, coalesce(f.nome, r.ni_fornecedor)
  FROM res r LEFT JOIN forn_nome f ON f.ni = coalesce(nullif(trim(r.ni_fornecedor), ''), 'ND') WHERE r.id_compra IN (SELECT unnest($l)) AND r.v > 0""",
              params={"l": ids_c or ["-"]}).fetchall()
con.close()
res_c = {}
for c, i, ni, v, nome in res:
    res_c.setdefault(c, []).append((i, ni, v, nome))
base_ia = {r["id_compra"] for r in base}
cls_base = {r["id_compra"]: r["classe"] for r in base}
CAP_OBJ = "|".join(r["termo"] for r in ler(TP + "dicionario_ia_classes.csv") if r["classe"] == "Capacitação" and r["tipo"] in ("inclusao_inicio_objeto", "inclusao_objeto"))
con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
obj_men = dict(con.sql("SELECT id_compra, strip_accents(lower(coalesce(objeto_compra, '') || ' ' || coalesce(informacao_complementar, ''))) FROM bl WHERE id_compra IN (SELECT unnest($l))",
                       params={"l": ids_c or ["-"]}).fetchall())
con.close()
# capacitacao: compra da classe Capacitacao na base da aba; fora da base, objeto ou informacao complementar de capacitacao
# (as mesmas expressoes que a classe usa para o objeto)
eh_cap = lambda c: cls_base.get(c) == "Capacitação" if c in base_ia else re.search(CAP_OBJ, obj_men.get(c, "")) is not None
tab, tab_ext = [], []
for m in MARCAS:
    mm = [x for x in men if x[0] == m]
    todas_c = sorted({x[1] for x in mm})
    cap_c = [c for c in todas_c if eh_cap(c)]
    comp = [c for c in todas_c if not eh_cap(c)]
    vn = vd = 0.0
    vend = {}
    for c in comp:
        no_obj = any(x[1] == c and x[3] != "texto do item" for x in mm)
        itens = {x[2] for x in mm if x[1] == c and x[3] == "texto do item"}
        rs = res_c.get(c, []) if no_obj else [r for r in res_c.get(c, []) if r[0] in itens]
        h = pbh.get(c) or 0
        v = h if no_obj else min(h, sum(r[2] for r in rs))
        vn += v
        vd += v * (fat.get(c) or 1)
        for _, ni, vr, nome in rs:
            vend[(ni, nome)] = vend.get((ni, nome), 0) + vr
    top = sorted(vend.items(), key=lambda kv: -kv[1])[:3]
    tab.append([m, len(comp), vn, vd, len(cap_c), "; ".join(nome for (_, nome), _ in top), len(set(comp) & base_ia), len(todas_c)])
    tab_ext.append([m, top])
grava(TP + "ia_marcas.csv", ["marca", "compras_de_produto", "valor_nominal", "valor_deflacionado", "compras_de_capacitacao", "principais_vendedores_compras_de_produto",
                             "compras_de_produto_na_base_da_aba", "compras_com_mencao_total"], tab)

# ---------------------------------------------------------------- planilha de revisao humana (10 compras por classe)
COMP = {"A": "Inteligência artificial (categoria do painel)", "B": "Capacitação em IA (fora das seis categorias)", "C": "Acréscimo de IA a licença (outra categoria)"}
con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
venc = {c: n for c, n in con.sql("""SELECT r.id_compra, arg_max(coalesce(f.nome, r.ni_fornecedor), r.v) FROM res r
  LEFT JOIN forn_nome f ON f.ni = r.ni_fornecedor WHERE r.id_compra IN (SELECT unnest($l)) AND r.v > 0 GROUP BY 1""",
                                         params={"l": [r["id_compra"] for r in base]}).fetchall()}
con.close()
rev, ant = [], []
CONGELADA = os.path.exists(V + "revisao_humana_ia.xlsx")
if CONGELADA:  # revisao ja feita: as 50 compras vem da copia marcada; a planilha nao e regravada
    _ws = load_workbook(V + "revisao_humana_ia_marcada_v1.xlsx", read_only=True)["revisao"]
    _sel = [(r[3], r[1]) for r in _ws.iter_rows(min_row=2, values_only=True) if r[0] == "Classes da aba IA"]
    assert len(_sel) == 50
for c in CLASSES:
    s = FINAL[c]
    if CONGELADA:
        _por_id = {f["id_compra"]: f for f in fichas[s] if f["classe"] == c}
        fs = [_por_id[i] for k, i in _sel if k == c]
    else:
        fs = sorted((f for f in fichas[s] if f["classe"] == c), key=lambda f: hashlib.md5((f["id_compra"] + "ia_revisao_humana").encode()).hexdigest())[:20 if c == SOL else 10]
    for f in fs:
        rev.append(["Classes da aba IA", f["id_compra"], COMP[f["componente"]], c, (f["objeto"] + (" | " + f["informacao_complementar"] if f["informacao_complementar"].strip() else ""))[:1500],
                    f["itens_ia"][:1500], venc.get(f["id_compra"], "sem resultado com valor"), None])
        j = julg[s][f["ficha"]]
        ant.append([f["id_compra"], c, s, j["pertinente"], j["motivo"]])
wb = Workbook()
ws = wb.active
ws.title = "revisao"
ws.append(["grupo", "id", "categoria", "classe atribuída", "texto do objeto", "texto do item (ou marcas e trechos)", "fornecedor", "revisão (certo/errado)"])
for r in rev:
    ws.append(r)
for col, w in zip("ABCDEFGH", (22, 26, 34, 24, 70, 60, 34, 22)):
    ws.column_dimensions[col].width = w
for row in ws.iter_rows(min_row=2):
    for cel in row:
        cel.alignment = Alignment(wrap_text=True, vertical="top")
for cel in ws[1]:
    cel.font = Font(bold=True)
wi = wb.create_sheet("instrucoes")
for t in ["Revisão humana da classificação da aba Inteligência artificial: 10 compras de Capacitação, 10 de Acréscimo à licença, 20 de Solução de IA (exclusiva ou em pacote) e 10 de Outros (50 linhas), sorteadas por hash com a semente ia_revisao_humana entre as compras já verificadas.",
          "Para cada linha, escreva 'certo' ou 'errado' na coluna H. Julgue pela classe atribuída (coluna D), lendo o objeto (coluna E) e, quando houver, os itens com IA (coluna F).",
          "Capacitação: certo quando a compra é curso, treinamento, inscrição, pós-graduação, palestra ou evento cujo tema principal é IA. Errado quando a IA é um tema entre muitos ou quando a compra é de solução, sistema ou equipamento.",
          "Acréscimo à licença: certo quando a compra inclui assistente de IA acoplado a licença de software já usada (Copilot para Microsoft 365, Gemini para Google Workspace e similares). Errado quando o produto de IA é vendido à parte (Copilot Studio sozinho, assinatura de ChatGPT ou Claude) ou quando o item é treinamento.",
          "Solução de IA (exclusiva ou em pacote): certo quando a compra é de solução de IA, seja só a IA (plataforma, modelo, API, assistente ou chatbot de IA, licenças de ChatGPT, Claude e similares), seja a IA como componente de pacote de softwares ou serviços digitais (nuvem, suíte de produtividade, atendimento omnichannel, segurança, sistema de gestão). Errado quando a compra é capacitação, equipamento com IA embarcada, serviço mais amplo (desenvolvimento sob encomenda, suporte, pesquisa) ou não tem IA.",
          "Outros: certo quando nenhuma das classes anteriores se aplica (por exemplo, equipamento com IA embarcada, como controle de acesso com reconhecimento facial, ou compra em que a IA aparece só num item de contratação mais ampla). Errado quando a compra se encaixa numa das classes anteriores.",
          "Os julgamentos anteriores (verificação por amostragem) ficam em arquivo separado e não devem ser consultados antes da revisão."]:
    wi.append([t])
wi.column_dimensions["A"].width = 160
for row in wi.iter_rows():
    for cel in row:
        cel.alignment = Alignment(wrap_text=True, vertical="top")
if not CONGELADA:
    wb.save(V + "revisao_humana_ia.xlsx")
grava(V + "revisao_humana_ia_julgamentos_anteriores.csv", ["id", "classe", "rodada", "pertinente_julgamento_anterior", "motivo"], ant)

# ---------------------------------------------------------------- reconciliacao: achado 4, classe Acrescimo, tipos e marca Copilot
dcl = ler(TP + "dicionario_ia_classes.csv")
pat = lambda c, t: "|".join(r["termo"] for r in dcl if r["classe"] == c and r["tipo"] == t)
ACR, ACR2, ACR_EXC = pat("Acréscimo à licença", "inclusao"), pat("Acréscimo à licença", "inclusao_acoplado"), pat("Acréscimo à licença", "exclusao_objeto")
f2 = duckdb.connect("fase2/f2.duckdb", read_only=True)
QI = """FROM {t} v JOIN modelo_item_v3 m USING (id_compra_item)
JOIN (SELECT DISTINCT id_compra_item, strip_accents(lower(concat_ws(' ', descricao, descricao_resumida, descricao_detalhada))) AS t FROM itens_escopo) i USING (id_compra_item)
WHERE m.ordem = 1 AND regexp_matches(i.t, $p)"""
s0 = f2.execute("SELECT DISTINCT v.id_compra, v.id_compra_item, v.valor, i.t " + QI.format(t="modelo_valor_2a"), {"p": ACR}).fetchall()
s0c = f2.execute("SELECT DISTINCT v.segmento, v.id_compra, v.id_compra_item, v.valor " + QI.format(t="modelo_valor_cat"), {"p": ACR}).fetchall()
f2.close()
bi = {r["id_compra"]: r for r in base}
S0 = {}
for c, i, v, t in s0:
    S0.setdefault(c, [0.0, []])
    S0[c][0] += v
    S0[c][1].append(t)
v0, v0c = sum(x[0] for x in S0.values()), sum(x[3] for x in s0c)
S1 = {c for c, r in bi.items() if r["classe"] == "Acréscimo à licença"}  # compras contadas na classe (classe de maior valor)
partes = ler(TP + "ia_base_classes.csv")
acr_parte = {r["id_compra"]: float(r["valor_nominal"]) for r in partes if r["classe"] == "Acréscimo à licença"}
Sp = set(acr_parte)  # compras com parte de acrescimo (inclusive de valor zero)
vp = sum(acr_parte[c] for c in Sp)
assert S1 <= Sp <= set(S0)
dA = sum(acr_parte[c] - S0[c][0] for c in Sp if bi[c]["componente"] == "A")
dC = sum(acr_parte[c] - S0[c][0] for c in Sp if bi[c]["componente"] != "A")


con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
OBJ = dict(con.sql("SELECT id_compra, strip_accents(lower(coalesce(objeto_compra, '') || ' ' || coalesce(informacao_complementar, ''))) FROM bl WHERE id_compra IN (SELECT unnest($l))",
                   params={"l": list(S0)}).fetchall())
con.close()


def motivo_fora(c):
    r = bi[c]
    if r["componente"] == "A" and any(re.search(ACR2, t) for t in S0[c][1]) and r["classe"] != "Capacitação":
        return "itens de acréscimo fora do escopo da categoria IA (sem valor na categoria pela regra do gráfico 9)"
    if r["classe"] == "Capacitação":
        return "compra de capacitação (a classe Capacitação tem precedência)"
    if ACR_EXC and re.search(ACR_EXC, OBJ.get(c, "")) and not any(re.search(ACR2, t) for t in S0[c][1]):
        return "assinatura de ChatGPT, OpenAI ou Claude no objeto (solução de IA, não acréscimo)"
    if all("copilot studio" in t or not re.search(ACR2, t) for t in S0[c][1]):
        return "itens só de Copilot Studio ou de treinamento em Copilot, sem assistente acoplado à licença"
    return "objeto com ChatGPT, OpenAI ou Claude (solução de IA, não acréscimo)"


fora = {}
for c in sorted(set(S0) - Sp):
    fora.setdefault(motivo_fora(c), []).append(c)
mot01 = "; ".join(f"{len(v)} {k}" for k, v in fora.items())
TC = {c for c, r in bi.items() if r["tipo_objeto"] == "Microsoft Copilot"}
TG = {c for c, r in bi.items() if r["tipo_objeto"] == "Google Gemini"}
vt = lambda S: sum(float(bi[c]["valor_nominal"]) for c in S)
mc = next(t for t in tab if t[0] == "Microsoft Copilot")
mg = next(t for t in tab if t[0] == "Google Gemini")
copilot_men = sorted({x[1] for x in men if x[0] == "Microsoft Copilot"})
cap_cop = [c for c in copilot_men if eh_cap(c)]
fora_base = [c for c in copilot_men if c not in base_ia and not eh_cap(c)]
na_base_prod = [c for c in copilot_men if c in base_ia and not eh_cap(c)]
rows = [
    ["Achado 4 da aba de tecnologias críticas (fase 2)", len(S0), v0, "valor dos itens, cada item uma vez (total das seis categorias)",
     "itens da classe 'acréscimo a licença existente' cujo texto cita copilot, gemini ou duet ai", 0, 0.0, "conjunto de referência"],
    ["Mesmo conjunto na soma por categoria", len(S0), v0c, "valor dos itens na soma por categoria (item em duas categorias conta nas duas)",
     "a mesma do achado 4", 0, v0c - v0, "um item classificado em duas categorias conta duas vezes; a aba de IA conta cada compra uma vez e usa a base do achado 4"],
    ["Parte de acréscimo à licença na aba IA (valor repartido pelos itens)", len(Sp), vp,
     "nas compras da categoria IA, a parte do valor da compra na categoria que cabe aos itens de acréscimo (regra do gráfico 9); nas demais, o valor desses itens, cada um uma vez",
     "a mesma do achado 4, só com itens de assistente acoplado à licença (versão 2 do dicionário: sem Copilot Studio sozinho, sem treinamento, sem ChatGPT ou Claude no objeto)",
     len(Sp) - len(S0), vp - v0,
     f"saem {len(S0) - len(Sp)} compras: {mot01}. Valor: {dA / 1e6:+.1f} mi nas compras da categoria IA (parte dos itens de acréscimo no valor da compra na categoria, "
     f"em vez do valor dos itens) e {dC / 1e6:+.1f} mi nas demais (só os itens com assistente acoplado)"],
    ["Classe Acréscimo à licença (compras contadas na classe de maior valor)", len(S1), vp, "o valor da classe soma a parte de acréscimo de todas as compras",
     "compra contada uma vez, na classe em que tem mais valor", len(S1) - len(S0), vp - v0,
     f"{len(Sp - S1)} compras com parte de acréscimo contam em outra classe, porque o restante da compra vale mais que os itens de Copilot ou Gemini"],
    ["Tipo 'Microsoft Copilot' em O que vendeu (aba IA)", len(TC), vt(TC), "valor total da compra na aba (todas as classes)",
     "termo copilot no objeto ou nos itens com IA, em compras da aba que não são de capacitação, na ordem dos tipos",
     len(TC) - len(S0), vt(TC) - v0,
     f"{len(TC & S1)} compras também estão na classe Acréscimo; {len(TC - set(S0))} citam Copilot fora do conjunto do achado 4 (Copilot Studio, Copilot em compra de solução de IA); "
     f"{len((set(S0) - TC) & TG)} compras do achado 4 são do tipo Google Gemini e {len(set(S0) - TC - TG)} de outro tipo ou de capacitação"],
    ["Tipo 'Google Gemini' em O que vendeu (aba IA)", len(TG), vt(TG), "valor da compra na aba", "termo gemini no objeto ou nos itens com IA, fora de capacitação, depois de Copilot na ordem dos tipos",
     len(TG) - len(S0), vt(TG) - v0, f"{len(TG & set(S0))} compras estão no conjunto do achado 4"],
    ["Marca Microsoft Copilot, compras de produto (tabela de marcas)", mc[1], mc[2], "valor homologado da compra quando a marca está no objeto; senão, resultados dos itens que a citam",
     "termo copilot no item, no objeto ou na informação complementar, em todas as compras do painel; exclui CoPilot da Extreme Networks",
     mc[1] - len(S0), mc[2] - v0, f"{len(na_base_prod)} compras de produto na base da aba e {len(fora_base)} fora dela (compras com Copilot em itens que a fase 2 não classificou como acréscimo, "
     f"como Copilot Studio, ou fora das seis categorias); a base de valor é outra"],
    ["Marca Microsoft Copilot, compras de capacitação", len(cap_cop), 0.0, "não se aplica", "a mesma da linha anterior, em cursos e eventos",
     len(cap_cop), 0.0, f"total da marca: {len(copilot_men)} compras = {mc[1]} de produto + {len(cap_cop)} de capacitação"],
]
grava(TP + "ia_reconciliacao_copilot.csv", ["conjunto", "compras", "valor_nominal", "base_de_valor", "regra_de_inclusao", "diferenca_compras_achado_4", "diferenca_valor_achado_4", "motivo"], rows)
grava(TP + "ia_reconciliacao_copilot_compras.csv", ["id_compra", "achado_4", "classe_acrescimo", "tipo_microsoft_copilot", "tipo_google_gemini", "marca_copilot", "classe_na_aba"],
      [[c, "sim" if c in S0 else "não", "sim" if c in S1 else "não", "sim" if c in TC else "não", "sim" if c in TG else "não", "sim" if c in copilot_men else "não", bi.get(c, {}).get("classe", "fora da base")]
       for c in sorted(set(S0) | S1 | TC | TG | set(copilot_men))])

for l in linhas:
    print(l[:5], f"{l[5]:.0f}%", l[6])
for r in rows:
    print(r[0], "|", r[1], f"{r[2] / 1e6:.1f} mi", "|", r[5], f"{r[6] / 1e6:+.1f} mi", "|", r[7])
print({c: sit[c] for c in CLASSES})
for t in tab:
    print(t[0], "| produto", t[1], f"{t[2] / 1e6:.1f} mi", "| capacitação", t[4], "|", t[5][:110], "| total", t[7])
print(len(rev), "linhas na planilha de revisão humana")
