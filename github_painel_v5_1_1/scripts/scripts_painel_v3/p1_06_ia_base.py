"""Painel v3, etapa 6: base, classes e tipos de objeto da aba Inteligencia artificial (Parte 5).
Executar a partir de Processado/, depois de p1_01 e da fase 2:  python scripts_painel_v3/p1_06_ia_base.py
Entradas (somente leitura): scripts_parte0/p0.duckdb (bl, pb, sv, dict, res); itens_dedup.parquet; fase2/f2.duckdb
  (modelo_item_v3, modelo_valor_2a, itens_escopo); tabelas_painel_v3/dicionario_ia_classes.csv e dicionario_ia_tipos.csv.
Base (cada compra uma vez):
  A. compras da categoria Inteligencia artificial do painel (cat_compra/sv, mesmo dicionario e recorte de 2021 a 2026);
     valor = valor da compra na categoria (regra de soma por categoria do painel);
  B. compras de capacitacao em IA que o dicionario da categoria exclui: termo de inclusao da categoria IA e termo de
     capacitacao no mesmo texto (objeto e informacao complementar da compra, ou texto do item); valor pela mesma regra
     do painel: compra inteira quando o texto da compra casa; so os resultados dos itens que casam, quando so os itens casam;
  C. compras com assistente de IA acoplado a licenca existente (fase 2: item da classe 'acrescimo a licenca existente'
     cujo texto cita copilot, gemini ou duet ai), fora de A e B; valor = valor desses itens (fase 2, total das seis categorias).
  Deflacionado = nominal x fator da compra (IPCA, mesmo mes-base do painel).
Classes (precedencia): Capacitacao; Acrescimo a licenca; IA exclusiva; Pacote multi-software; Outros
  (dicionario_ia_classes.csv). Tipos de objeto de 'O que vendeu' (dicionario_ia_tipos.csv), na ordem do dicionario;
  tipo com menos de 3 compras vai para 'Outras soluções de IA'.
Saidas: tabelas_painel_v3/ia_base.csv (uma linha por compra), ia_itens.csv (itens que casam), ia_reconciliacao.csv,
  validacao_ia/fichas_ia_a1.csv (20 compras por classe, semente ia_a1, para a verificacao).
"""
import csv
import glob
import hashlib
import sys
import re
import unicodedata

import duckdb

TP = "tabelas_painel_v3/"
norm = lambda t: re.sub(r"\s+", " ", unicodedata.normalize("NFKD", (t or "").replace("\xa0", " ")).encode("ascii", "ignore").decode().lower()).strip()
dic_cls = list(csv.DictReader(open(TP + "dicionario_ia_classes.csv", encoding="utf-8"), delimiter=";"))
dic_tip = list(csv.DictReader(open(TP + "dicionario_ia_tipos.csv", encoding="utf-8"), delimiter=";"))
pad = lambda classe, tipo: "|".join(r["termo"] for r in dic_cls if r["classe"] == classe and r["tipo"] == tipo)

con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
INC = "|".join(t for (t,) in con.sql("SELECT termo_regex FROM dict WHERE segmento = 'ia' AND tipo = 'inclusao'").fetchall())
CAP = pad("Capacitação", "inclusao")
con.sql(f"""CREATE TEMP TABLE tc AS SELECT id_compra, strip_accents(lower(coalesce(objeto_compra, '') || ' ' || coalesce(informacao_complementar, ''))) AS t FROM bl""")
con.sql(f"""CREATE TEMP TABLE ti AS SELECT id_compra_item, id_compra,
  strip_accents(lower(coalesce(descricao, '') || ' ' || coalesce(descricao_detalhada, '') || ' ' || coalesce(descricao_resumida, ''))) AS t
  FROM read_parquet('itens_dedup.parquet') WHERE id_compra IN (SELECT id_compra FROM bl)""")
# A: categoria IA do painel
A = {r[0]: r for r in con.sql("SELECT id_compra, local_match, v_2b, v_2b_defl FROM sv WHERE segmento = 'ia'").fetchall()}
# B: capacitacao em IA (termo da categoria e termo de capacitacao no mesmo texto)
b_obj = {r[0] for r in con.sql(f"SELECT id_compra FROM tc WHERE regexp_matches(t, '{INC}') AND regexp_matches(t, '{CAP}')").fetchall()}
b_itm = con.sql(f"SELECT id_compra_item, id_compra FROM ti WHERE regexp_matches(t, '{INC}') AND regexp_matches(t, '{CAP}')").fetchall()
B_ids = (b_obj | {c for _, c in b_itm}) - set(A)
itens_b = [i for i, c in b_itm if c in B_ids and c not in b_obj]
con.sql("CREATE TEMP TABLE ib AS SELECT unnest($l) AS id_compra_item", params={"l": itens_b or ["-"]})
vb = dict(con.sql("""
SELECT p.id_compra, CASE WHEN p.id_compra IN (SELECT unnest($o)) THEN p.hom ELSE least(p.hom, coalesce(sum(r.v), 0)) END
FROM pb p LEFT JOIN res r ON r.id_compra = p.id_compra AND r.id_compra_item IN (SELECT id_compra_item FROM ib)
WHERE p.id_compra IN (SELECT unnest($b)) GROUP BY p.id_compra, p.hom""", params={"o": list(b_obj) or ["-"], "b": list(B_ids) or ["-"]}).fetchall())
pbx = {r[0]: r[1:] for r in con.sql("SELECT id_compra, ano, orgao, esfera, modalidade, fator, hom, objeto_compra, informacao_complementar FROM pb").fetchall()}
# regra das fundacoes de apoio (versao 4): sai da classe Capacitacao e da base B a compra cujo objeto contrata fundacao de
# apoio para gestao administrativa, financeira ou operacional de curso ou projeto (nao e compra de capacitacao nem de tecnologia de IA)
FUND_F, FUND_G, FUND_X = pad("Capacitação", "exclusao_fundacao"), pad("Capacitação", "exclusao_fundacao_gestao"), pad("Capacitação", "excecao_fundacao")
_tf = lambda c: norm((pbx[c][6] or "") + " " + (pbx[c][7] or ""))
eh_fund = lambda c: re.search(FUND_F, _tf(c)) is not None and re.search(FUND_G, _tf(c)) is not None and re.search(FUND_X, _tf(c)) is None
fund_ids = {c for c in B_ids if eh_fund(c)}
venc_f = dict(con.sql("""SELECT r.id_compra, arg_max(coalesce(f.nome, r.ni_fornecedor), r.v) FROM res r LEFT JOIN forn_nome f ON f.ni = r.ni_fornecedor
  WHERE r.id_compra IN (SELECT unnest($l)) AND r.v > 0 GROUP BY 1""", params={"l": list(fund_ids) or ["-"]}).fetchall())
excl_fund = sorted(([c, pbx[c][1], venc_f.get(c, "sem resultado com valor"), re.sub(r"\s+", " ", pbx[c][6] or "").strip(), round(vb.get(c, 0), 2)] for c in fund_ids), key=lambda x: -x[4])
B_ids = B_ids - fund_ids
# regra dos itens (capacitacao com cursos misturados): na compra classificada pelo objeto, com itens identificaveis (algum item
# com termo de IA e algum sem), conta so a parte dos itens com termo de IA, repartida pelo valor dos resultados de cada item
# (sem resultado, pelo valor estimado do item), a mesma regra do grafico 9
pes = con.execute("""SELECT i.id_compra, i.id_compra_item,
  regexp_matches(strip_accents(lower(coalesce(descricao, '') || ' ' || coalesce(descricao_detalhada, '') || ' ' || coalesce(descricao_resumida, ''))), $p) AS ia,
  coalesce(nullif((SELECT sum(r.v) FROM res r WHERE r.id_compra_item = i.id_compra_item AND r.v > 0), 0), try_cast(i.valor_total AS DOUBLE), 0) AS w
  FROM read_parquet('itens_dedup.parquet') i WHERE i.id_compra IN (SELECT unnest($l))""", {"p": INC, "l": list(b_obj & B_ids) or ["-"]}).fetchall()
_pi = {}
for c, i, ia, w in pes:
    _pi.setdefault(c, []).append((i, ia, w or 0.0))
itens_ia_b, rep_itens = {}, []
for c, its in _pi.items():
    wt, wia = sum(w for _, _, w in its), sum(w for _, ia, w in its if ia)
    if wt > 0 and any(ia for _, ia, _ in its) and not all(ia for _, ia, _ in its):
        antes = vb[c]
        vb[c] = antes * wia / wt
        itens_ia_b[c] = {i for i, ia, _ in its if ia}
        rep_itens.append([c, pbx[c][1], round(antes, 2), round(vb[c], 2), len(its), len(itens_ia_b[c])])
# C: acrescimo de IA a licenca (fase 2)
f2 = duckdb.connect("fase2/f2.duckdb", read_only=True)
ACR = pad("Acréscimo à licença", "inclusao")
C_itens = f2.sql(f"""
SELECT DISTINCT v.id_compra, v.id_compra_item, v.valor FROM modelo_valor_2a v JOIN modelo_item_v3 m USING (id_compra_item)
JOIN (SELECT DISTINCT id_compra_item, strip_accents(lower(concat_ws(' ', descricao, descricao_resumida, descricao_detalhada))) AS t FROM itens_escopo) i USING (id_compra_item)
WHERE m.ordem = 1 AND regexp_matches(i.t, '{ACR}')""").fetchall()
# valor da compra na categoria IA repartido pelos itens (fase 2, a mesma regra do grafico 9)
mvc_ia = dict(f2.sql("SELECT id_compra_item, sum(valor) FROM modelo_valor_cat WHERE segmento = 'ia' AND id_compra_item IS NOT NULL GROUP BY 1").fetchall())
f2.close()
vc = {}
for c, _, v in C_itens:
    vc[c] = vc.get(c, 0) + v
acr_ids = set(vc)
C_ids = acr_ids - set(A) - B_ids - fund_ids

# textos dos itens das compras da base (para classes, tipos e marcas)
base_ids = set(A) | B_ids | C_ids
con.sql("CREATE TEMP TABLE bs AS SELECT unnest($l) AS id_compra", params={"l": list(base_ids)})
itens = con.sql(f"""SELECT ti.id_compra, ti.id_compra_item, ti.t, regexp_matches(ti.t, '{INC}') AS ia FROM ti JOIN bs USING (id_compra)""").fetchall()
con.close()
it_por = {}
for c, i, t, ia in itens:
    it_por.setdefault(c, []).append((i, t, ia))

# ---- classes e tipos
def casa(p, t):
    return bool(p) and re.search(p, t) is not None


MULTI, HW, CAP_INI = pad("Pacote multi-software", "inclusao"), pad("IA exclusiva", "exclusao"), pad("Capacitação", "inclusao_inicio_objeto")
CAP_OBJ, COMPOSTO = pad("Capacitação", "inclusao_objeto"), pad("IA exclusiva", "exclusao_composta")
ACR2, ACR_EXC = pad("Acréscimo à licença", "inclusao_acoplado"), pad("Acréscimo à licença", "exclusao_objeto")
txt_item = {i: t for c, i, t, ia in itens}
acr_txt, acr_val2a = {}, {}
for c, i, v in C_itens:
    acr_txt.setdefault(c, []).append(norm(txt_item.get(i, "")))
    acr_val2a[i] = acr_val2a.get(i, 0) + v
EXCL = pad("IA exclusiva", "inclusao")
linhas, partes_lin, acr_itens_por, resto_por = [], [], {}, {}
for c in sorted(base_ids):
    ano, orgao, esfera, modalidade, fator, hom, obj, info = pbx[c]
    tc = norm((obj or "") + " " + (info or ""))
    ti_ia = " | ".join(t for _, t, ia in it_por.get(c, []) if ia or casa(ACR, t))
    if c in A:
        comp, vn = "A", A[c][2]
    elif c in B_ids:
        comp, vn = "B", vb.get(c, 0)
    else:
        comp, vn = "C", vc[c]
    ia_obj = casa(INC, tc) or casa(EXCL, tc)
    if comp == "B" or casa(CAP_INI, tc) or casa(CAP_OBJ, tc):
        cls = "Capacitação"
    elif c in acr_ids and any(casa(ACR2, t) for t in acr_txt[c]) and not casa(ACR_EXC, tc):
        cls = "Acréscimo à licença"
    elif ia_obj and not casa(MULTI, tc) and not casa(HW, tc) and not casa(COMPOSTO, tc):
        cls = "IA exclusiva"
    elif (casa(MULTI, tc) or casa(MULTI, ti_ia)) and not casa(HW, tc):
        cls = "Pacote multi-software"
    else:
        cls = "Outros"
    # classe dos itens que nao sao de acrescimo: a que o dicionario indica sem a regra do acrescimo
    if ia_obj and not casa(MULTI, tc) and not casa(HW, tc) and not casa(COMPOSTO, tc):
        resto = "IA exclusiva"
    elif (casa(MULTI, tc) or casa(MULTI, ti_ia)) and not casa(HW, tc):
        resto = "Pacote multi-software"
    else:
        resto = "Outros"
    # classes somadas (a fronteira entre IA exclusiva e pacote multi-software e ambigua); o dicionario nao muda
    soma_cls = lambda k: "Solução de IA (exclusiva ou em pacote)" if k in ("IA exclusiva", "Pacote multi-software") else k
    cls_dic, cls, resto = cls, soma_cls(cls), soma_cls(resto)
    base_v = {"A": "valor da compra na categoria IA (soma por categoria do painel)", "B": "regra do painel aplicada à capacitação",
              "C": "itens de acréscimo de IA a licença (fase 2), cada item uma vez"}[comp]
    # reparticao do valor da compra entre as classes pelos itens (a mesma regra do grafico 9): o acrescimo recebe so os itens
    # com assistente de IA acoplado; os demais itens ficam com a classe que o dicionario indica para a compra
    itens_acr = set()
    if cls == "Acréscimo à licença":
        itens_acr = {i for cc, i, _ in C_itens if cc == c and casa(ACR2, norm(txt_item.get(i, "")))}
        v_acr = sum(mvc_ia.get(i, 0) for i in itens_acr) if comp == "A" else sum(acr_val2a[i] for i in itens_acr)
        partes = {"Acréscimo à licença": v_acr, resto: vn - v_acr}
    else:
        partes = {cls: vn}
    partes = {k: v for k, v in partes.items() if abs(v) > 1e-9} or {cls: 0.0}
    cls = max(partes, key=lambda k: (partes[k], k == "Acréscimo à licença"))  # compra contada uma vez, na classe de maior valor
    for k, v in partes.items():
        partes_lin.append([c, k, round(v, 6), round(v * fator, 6)])
    acr_itens_por[c] = itens_acr
    resto_por[c] = resto if itens_acr else cls  # classe dos itens que nao sao de acrescimo
    texto_tipo = tc + " | " + ti_ia
    tipo = "Outros objetos"
    if cls != "Capacitação":
        for r in dic_tip:
            if r["tipo"] == "inclusao" and casa(r["termo"], texto_tipo):
                tipo = r["objeto"]
                break
        else:
            tipo = "Outras soluções de IA" if casa(INC, texto_tipo) or casa(EXCL, texto_tipo) else "Outros objetos"
    linhas.append([c, comp, cls, tipo, ano, orgao, esfera, modalidade, round(vn, 6), round(vn * fator, 6), hom, cls_dic, base_v])
# tipo com menos de 3 compras vai para 'Outras solucoes de IA', salvo as marcas de IA, que aparecem sempre com nome proprio
MARCAS_TIPO = {"Microsoft Copilot", "Google Gemini", "ChatGPT/OpenAI", "Claude/Anthropic", "Perplexity", "Manus"}
n_tipo = {}
for l in linhas:
    n_tipo[l[3]] = n_tipo.get(l[3], 0) + 1
for l in linhas:
    if n_tipo[l[3]] < 3 and l[3] not in ("Outros objetos", "Outras soluções de IA") and l[3] not in MARCAS_TIPO:
        l[3] = "Outras soluções de IA"


def grava(nome, cab, rows):
    with open(nome, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)


grava(TP + "ia_base.csv", ["id_compra", "componente", "classe", "tipo_objeto", "ano", "orgao", "esfera", "modalidade", "valor_nominal", "valor_deflacionado",
                            "homologado_limpo_compra", "classe_dicionario", "base_do_valor"], linhas)
grava(TP + "ia_base_classes.csv", ["id_compra", "classe", "valor_nominal", "valor_deflacionado"], partes_lin)
# revisao humana da lista de fundacoes de apoio (concluida): nenhuma das compras e curso para servidores; exclusao confirmada.
# Compra nova que a regra venha a pegar sai como "não revisada".
FUND_REVISADAS = {
    "15404806001402025",
    "15305206005342024",
    "15307906003342025",
    "15307906006692025",
    "15435806003462025",
    "15435806001212026",
    "15435806001192026",
    "15307906003192026",
    "15307906004322025",
    "15317806001352025",
    "15317606001072024",
    "15317606000542023",
    "15317606000532023",
    "15317606001062024",
    "15317606000552023",
    "15317606000092023",
    "15317606000562023",
    "15404306010572026",
    "15307906008512025",
    "15404006002502025",
    "15667806000922026",
    "15435806003562025",
    "15317706000502026",
    "15305206002932026",
    "15317806000572024",
    "15317706000562024",
    "15317806001342025",
    "15303106003332026",
    "15307906005392024",
    "15317606000762026"
}
grava("validacao_ia/exclusao_fundacoes_apoio.csv", ["id_compra", "orgao", "fundacao", "objeto", "valor_nominal", "revisão humana"],
      [x + ["confirmada" if x[0] in FUND_REVISADAS else "não revisada"] for x in excl_fund])
grava("validacao_ia/capacitacao_itens_repartidos.csv", ["id_compra", "orgao", "valor_antes", "valor_depois", "itens", "itens_com_termo_de_ia"], sorted(rep_itens, key=lambda x: x[3] - x[2]))
assert not any(eh_fund(l[0]) for l in linhas if l[2] == "Capacitação"), "compra de fundação de apoio na classe Capacitação fora da base B"
print("fundações de apoio excluídas:", len(excl_fund), round(sum(x[4] for x in excl_fund) / 1e6, 2), "mi")
print("capacitação com itens repartidos:", len(rep_itens), "compras; efeito", round(sum(x[3] - x[2] for x in rep_itens) / 1e6, 2), "mi")
grava(TP + "ia_itens.csv", ["id_compra", "id_compra_item", "casa_termo_ia", "casa_capacitacao", "acrescimo_licenca"],
      sorted([c, i, "sim" if ia else "não", "sim" if casa(CAP, t) else "não", "sim" if i in {x[1] for x in C_itens} else "não"]
             for c, i, t, ia in itens if ia or casa(ACR, t)))  # ordem fixa: a consulta nao garante ordem
# reconciliacao com a categoria IA do painel
cat_ia = [r for r in csv.DictReader(open(TP + "pn_categoria_ano.csv", encoding="utf-8"), delimiter=";") if r["categoria"] == "ia"]
nA, vA = len(A), sum(r[2] for r in A.values())
rec = [["Categoria Inteligência artificial do painel (pn_categoria_ano.csv)", sum(int(r["n_compras"]) for r in cat_ia), sum(float(r["valor_nominal"]) for r in cat_ia)],
       ["A. Compras da categoria IA na base da aba", nA, vA],
       ["B. Capacitação em IA, excluída pelo dicionário da categoria", len(B_ids), sum(vb.get(c, 0) for c in B_ids)],
       ["C. Acréscimo de IA a licença em outras categorias (fase 2)", len(C_ids), sum(vc[c] for c in C_ids)],
       ["Compras com acréscimo de IA a licença já na categoria IA (contadas em A)", len(acr_ids & set(A)), sum(A[c][2] for c in acr_ids & set(A))],
       ["Total da aba Inteligência artificial (A + B + C, cada compra uma vez)", len(linhas), sum(l[8] for l in linhas)]]
grava(TP + "ia_reconciliacao.csv", ["linha", "compras", "valor_nominal"], rec)
assert rec[0][1] == rec[1][1] and abs(rec[0][2] - rec[1][2]) < 1, "componente A nao reproduz a categoria IA do painel"
assert rec[-1][1] == rec[1][1] + rec[2][1] + rec[3][1] and abs(rec[-1][2] - rec[1][2] - rec[2][2] - rec[3][2]) < 1

# ---- resultados da aba (base do grafico 'Quem vendeu, o que vendeu, quem comprou' e da tabela de cadeias): a mesma regra
# do painel (resultados vigentes, valor > 0, compras sem valor excluido); A: resultados do escopo da categoria IA;
# B: resultados da compra (texto da compra casa) ou dos itens que casam; C: resultados dos itens de acrescimo da fase 2.
# Classe do resultado: Acrescimo quando o item e de assistente acoplado; senao, a classe dos demais itens da compra.
con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
ids_l = list(base_ids)
rA = con.sql("""SELECT r.id_compra, r.id_compra_item, coalesce(nullif(trim(r.ni_fornecedor), ''), 'ND'), r.v FROM res_cat_valid r
  WHERE r.segmento = 'ia' AND r.v > 0""").fetchall()
rT = con.sql("""SELECT r.id_compra, r.id_compra_item, coalesce(nullif(trim(r.ni_fornecedor), ''), 'ND'), r.v FROM res r
  WHERE r.v > 0 AND r.id_compra IN (SELECT unnest($l))""", params={"l": ids_l}).fetchall()
nomes = dict(con.sql("SELECT ni, nome FROM forn_nome WHERE ni IN (SELECT DISTINCT coalesce(nullif(trim(ni_fornecedor), ''), 'ND') FROM res WHERE id_compra IN (SELECT unnest($l)))",
                     params={"l": ids_l}).fetchall())
porte_r = dict(((i, n), p) for i, n, p in con.sql("""SELECT DISTINCT id_compra_item, ni_fornecedor, porte_fornecedor_nome FROM read_parquet('resultados_dedup.parquet')
  WHERE id_compra IN (SELECT unnest($l))""", params={"l": ids_l}).fetchall())
con.close()
itens_c = {}
for c, i, _ in C_itens:
    itens_c.setdefault(c, set()).add(i)
ib_set = set(itens_b)
res_ia = []
for c, i, ni, v in rA:
    if c in A and (pbx[c][5] or 0) > 0:  # pbx: ano, orgao, esfera, modalidade, fator, hom, objeto, informacao
        res_ia.append((c, i, ni, v))
for c, i, ni, v in rT:
    if c in A or (pbx[c][5] or 0) <= 0:
        continue
    if c in B_ids and ((c in b_obj and (c not in itens_ia_b or i in itens_ia_b[c])) or i in ib_set):
        res_ia.append((c, i, ni, v))
    elif c in C_ids and i in itens_c.get(c, ()):
        res_ia.append((c, i, ni, v))
cls_comp = {l[0]: l for l in linhas}
RAIZ = lambda ni: ni[:8] if re.fullmatch(r"[0-9]{14}", ni) else ni
PORTE = lambda p: "ME ou EPP" if p in ("ME", "EPP") else "Demais" if p == "Demais" else "Não informado"
res_lin, porte_v = [], {}
for c, i, ni, v in res_ia:
    l = cls_comp[c]
    k = "Acréscimo à licença" if i in acr_itens_por[c] else resto_por[c]
    res_lin.append([c, i, ni, RAIZ(ni), k, l[3], l[4], l[5], l[6], round(v, 6), round(v * pbx[c][4], 6)])
    pp = porte_v.setdefault(RAIZ(ni), {})
    pp[PORTE(porte_r.get((i, ni)))] = pp.get(PORTE(porte_r.get((i, ni))), 0) + v
grava(TP + "ia_resultados.csv", ["id_compra", "id_compra_item", "cnpj_fornecedor", "raiz_cnpj", "classe", "tipo_objeto", "ano", "orgao", "esfera",
                                 "valor_nominal", "valor_deflacionado"], sorted(res_lin, key=lambda x: (x[0], x[1], x[2], x[4])))
nome_raiz = {}
for c, i, ni, v in res_ia:
    z = nome_raiz.setdefault(RAIZ(ni), {})
    nm = nomes.get(ni) or ("Fornecedor não identificado" if ni == "ND" else ni)
    z[nm] = z.get(nm, 0) + v
grava(TP + "ia_fornecedores.csv", ["raiz_cnpj", "nome", "porte"],
      [[z, max(n, key=n.get), max(porte_v[z], key=porte_v[z].get)] for z, n in sorted(nome_raiz.items())])
grava(TP + "ia_fornecedores_cnpj.csv", ["cnpj_fornecedor", "nome"],
      sorted({(ni, nomes.get(ni) or ("Fornecedor não identificado" if ni == "ND" else ni)) for _, _, ni, _ in res_ia}))
grava(TP + "ia_objetos.csv", ["id_compra", "objeto"], [[c, re.sub(r"\s+", " ", pbx[c][6] or "").strip()] for c in sorted(base_ids)])
# controle: os resultados de A reproduzem os do grafico 11 na categoria IA (pn_fluxo)
vA_res = sum(v for c, i, ni, v in res_ia if c in A)
vA_fluxo = sum(float(r["valor_nominal"]) for r in csv.DictReader(open(TP + "pn_fluxo.csv", encoding="utf-8"), delimiter=";") if r["categoria"] == "ia")
assert abs(vA_res - vA_fluxo) < 1, (vA_res, vA_fluxo)
print("resultados da aba:", len(res_lin), "linhas;", len({x[0] for x in res_lin}), "compras;", round(sum(x[9] for x in res_lin) / 1e6, 1), "mi")

# ---- fichas da verificacao (so quando a semente e informada): 20 compras por classe, ordem por hash com semente fixa,
# sem compras de amostras anteriores; ex.: python scripts_painel_v3/p1_06_ia_base.py ia_a2
SEMENTE = sys.argv[1] if len(sys.argv) > 1 else None
ja = {r["id_compra"] for a in glob.glob("validacao_ia/fichas_ia_*.csv") if SEMENTE and not a.endswith(f"{SEMENTE}.csv")
      for r in csv.DictReader(open(a, encoding="utf-8"), delimiter=";")}
fichas = []
CLASSES_AMOSTRA = sys.argv[2].split(",") if len(sys.argv) > 2 else ["Capacitação", "Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)", "Outros"]
for cls in CLASSES_AMOSTRA if SEMENTE else ():
    ids = sorted((l for l in linhas if l[2] == cls and l[0] not in ja), key=lambda l: hashlib.md5((l[0] + SEMENTE).encode()).hexdigest())[:20]
    for l in ids:
        obj, info = pbx[l[0]][6], pbx[l[0]][7]
        ti_ia = " | ".join(t[:300] for _, t, ia in it_por.get(l[0], []) if ia or casa(ACR, t))[:900]
        fichas.append([len(fichas), cls, l[0], l[1], l[3], l[4], l[5], round(l[8], 2), (obj or "")[:600], (info or "")[:300], ti_ia, SEMENTE])
if SEMENTE:
    grava(f"validacao_ia/fichas_{SEMENTE}.csv", ["ficha", "classe", "id_compra", "componente", "tipo_objeto", "ano", "orgao", "valor_nominal", "objeto", "informacao_complementar", "itens_ia", "semente"], fichas)
for r in rec:
    print(r)
cnt = {}
for l in linhas:
    x = cnt.setdefault(l[2], [0, 0])
    x[0] += 1
    x[1] += l[8]
print(cnt)
tp = {}
for l in linhas:
    tp[l[3]] = tp.get(l[3], 0) + 1
print(tp)
