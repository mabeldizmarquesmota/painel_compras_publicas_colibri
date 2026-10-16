"""Painel v5.1, etapa 4: conferencia de cada numero exibido no painel v5 com as tabelas agregadas e com a metodologia.

Executar a partir de Processado/, depois de p51_03:  python scripts_painel_v5_1/p51_04_conferencia.py
Adaptado de scripts_painel_v5/p5_04_conferencia.py (mesmas regras), mais a reconciliacao do grafico 9 com a categoria IA do grafico 8
  e o grafico 9 comparado com o grafico 8. A v5 por sua vez adaptou scripts_painel_v4/p4_04_conferencia.py: sairam as linhas dos textos excluidos no Ajuste 5 (exemplo de leitura
  do KPI de valor, preenchimento nos cartoes dos instrumentos); entraram os textos novos (caixas de abertura, graficos 1 a 3, achados
  da IA), a reconciliacao da Capacitacao e de Nuvem com servicos de IA, a interacao do grafico 9 e a comparacao texto x grafico.
  No painel, os tipos de objeto 'Nuvem/cloud broker' e 'Outros objetos' (so Capacitacao) das tabelas aparecem como
  'Nuvem com servicos de IA' e 'Capacitacao'; o mesmo nome e usado aqui.
Entradas: verificacao_html_v5_1/conf_painel.json, textos_i.json, alternador_exemplos.csv, sankey_conferencia.csv, ia_sankey_conferencia.csv,
  texto_grafico.csv, grafico9_interacao.csv, grafico9_igual_grafico8.csv (p51_03); tabelas_painel_v3/, v4/, v5/ e v5_1/ (somente leitura);
  METODOLOGIA_v5_1.md; PROMPT_PAINEL_V5.md.
Regra: o valor esperado e recalculado aqui, de forma independente do JavaScript do painel, a partir das tabelas agregadas,
  e formatado com as mesmas funcoes (scripts_painel_v5_1/formatacao.py). confere = sim quando o texto exibido e identico ao esperado.
Saida: conferencia_numeros_v5_1.csv (texto_exibido; valor_exibido; arquivo_de_origem; coluna; valor_calculado; confere; texto_e_grafico)
"""
import csv
import json
import statistics
import re as _re
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.dont_write_bytecode = True
sys.path.insert(0, "scripts_painel_v5_1")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v5_1.formatacao import bi, fmt_escala, fmt_num, fmt_pct, inteiro, mi, mi1, reais, vauto  # noqa: E402

TP = "tabelas_painel_v3/"
conf = json.load(open("verificacao_html_v5_1/conf_painel.json", encoding="utf-8"))
textos_i = json.load(open("verificacao_html_v5_1/textos_i.json", encoding="utf-8"))
met = open("METODOLOGIA_v5_1.md", encoding="utf-8").read()


def ler(n):
    with open(n, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def f(x):
    return float(x) if x not in ("", None) else 0.0


NOME = {"ia": "Inteligência artificial", "nuvem": "Nuvem", "plataformas": "Plataformas e licenciamento",
        "identidade": "Identidade e infraestrutura pública digital", "data_center": "Data center",
        "seguranca": "Segurança cibernética"}
CATS = list(NOME)
ANOS = range(2021, 2027)
cubo, sob, cat = ler(TP + "pn_cubo_compras.csv"), ler(TP + "pn_soberania_ano.csv"), ler(TP + "pn_categoria_ano.csv")
tres = ler(TP + "pn_soberania_tres_regras.csv")[0]
L = []


# coluna usada de cada arquivo (quando a linha nao informa outra)
COLUNA = {
    "pn_cubo_compras.csv": "hom_nominal", "pn_soberania_tres_regras.csv": "regra_2a", "pn_soberania_ano.csv": "soberania_2a_nominal; homologado_total_nominal",
    "pn_categoria_ano.csv": "valor_nominal", "pn_modalidade_soberania.csv": "valor_nominal", "pn_forma_contratacao.csv": "valor_nominal",
    "pn_fluxo.csv": "valor_nominal", "pn_concentracao.csv": "n_fornecedores; cr4_nominal; hhi_nominal; valor_nominal",
    "pn_perfil_valores_por_compra.csv": "valor_nominal; srp", "pn_perfil_bens.csv": "valor_bens_nominal; valor_resultados_nominal",
    "pn_instrumentos.csv": "valor_nominal; margem_prevista_nominal; margem_aplicada_nominal; ppb_nominal", "pn_instrumentos_preenchimento.csv": "n_preenchidos; n_registros",
    "pn_margem_ncm.csv": "ncm_item_nominal; ncm_item_tradutor_nominal; margem_aplicada_material_nominal", "p0_preenchimento_pais_origem.csv": "pct_preenchido",
    "pn_precisao_final.csv": "n_revisadas_na_base; precisao_pct", "pn_fluxo_compras.csv": "id_compra; cnpj_fornecedor; orgao",
    "pn_modelo_categoria_ano.csv": "valor_nominal por classe", "pn_vendedor_categoria_ano.csv": "valor_nominal por tipo_vendedor",
    "pn_marca_resultados.csv": "chave_resultado; raiz_cnpj_vendedor; tipo_vendedor; id_compra; valor_nominal", "pn_porte_compras.csv": "id_compra; porte",
    "pn_porte_valor.csv": "valor_nominal por porte", "pn_achados.csv": "titulo; texto", "pn_textos_i.csv": "exemplo_de_leitura",
    "f2_11_numeros_achados.csv": "valor_exibido", "METODOLOGIA_v5_1.md": "texto", "pn_direitos_permanentes_codigo.csv": "valor_classe_total; valor_so_codigo_catalogo; pct_so_codigo_catalogo",
    "resultado_revisao_humana.csv": "linhas_revisadas; certo; concordancia_pct", "concordancia_entre_revisoes.csv": "concordam",
    "pn_modelo_grupo_componentes.csv": "valor_nominal; valor_deflacionado por ordem (0 e 4)", "pn_exemplos_modos.csv": "texto",
}


def coluna(ind, origem):
    cols = []
    for arq in _re.split(r"[,;] ?", origem):
        c = COLUNA.get(arq.strip().split("/")[-1], "")
        if arq.strip().endswith("pn_cubo_compras.csv") and "compras" in ind.lower() and "valor" not in ind.lower():
            c = "n_homologadas" if "homologadas" in ind else "n_publicadas"
        if c and c not in cols:
            cols.append(c)
    return "; ".join(cols)


def _soma(rows, key):
    d = {}
    for r in rows:
        k = key(r)
        d[k] = d.get(k, 0) + round(float(r["valor_nominal"]), 2)
    return d


def add(ind, painel, esperado, origem, col=None, tg="não se aplica"):
    # tg: o mesmo numero no texto e no grafico (sim/nao), quando o texto cita um numero do grafico
    L.append([ind, painel, origem, col or coluna(ind, origem), esperado, "sim" if painel == esperado else "não", tg])


def s(rows, campo, **flt):
    return sum(f(r[campo]) for r in rows if all(str(r[k]) == str(v) for k, v in flt.items()))


HOM = s(cubo, "hom_nominal")
N = s(cubo, "n_publicadas")
V2A = f(tres["regra_2a"])
# aba Sobre
add("Sobre: KPI compras publicadas", conf.get("sobre_kpi_compras"), inteiro(N), TP + "pn_cubo_compras.csv")
add("Sobre: KPI valor homologado total", conf.get("sobre_kpi_valor"), bi(HOM), TP + "pn_cubo_compras.csv")
add("Sobre: KPI homologado em tecnologias críticas para a soberania digital", conf.get("sobre_kpi_soberania"), bi(V2A), TP + "pn_soberania_tres_regras.csv")
add("Sobre: KPI participação", conf.get("sobre_kpi_participacao"), fmt_pct(100 * V2A / HOM), TP + "pn_soberania_tres_regras.csv")
# aba compras
add("Compras: KPI compras", conf.get("cp_kpi_compras"), inteiro(N), TP + "pn_cubo_compras.csv")
add("Compras: KPI valor homologado", conf.get("cp_kpi_valor"), bi(HOM), TP + "pn_cubo_compras.csv")
for a in ANOS:
    add(f"Gráfico 1: valor homologado {a}", conf.get(f"g1_valor_{a}"), bi(s(cubo, "hom_nominal", ano=a)), TP + "pn_cubo_compras.csv")
    add(f"Gráfico 1: compras homologadas {a}", conf.get(f"g1_qtd_{a}"), inteiro(s(cubo, "n_homologadas", ano=a)), TP + "pn_cubo_compras.csv")
for gid, dim in (("g2", "esfera"), ("g3", "poder"), ("g4", "modalidade")):
    for v in sorted({r[dim] for r in cubo}):
        x = s(cubo, "hom_nominal", **{dim: v})
        if x > 0:
            add(f"Gráfico {gid[1]}: {v}", conf.get(f"{gid}_{v}"), f"{vauto(x)} | {fmt_pct(100 * x / HOM)}", TP + "pn_cubo_compras.csv")
# aba soberania
add("Soberania: KPI valor (total das seis categorias)", conf.get("sd_kpi_valor"), bi(V2A), TP + "pn_soberania_ano.csv")
add("Soberania: KPI participação", conf.get("sd_kpi_part"), fmt_pct(100 * V2A / HOM), TP + "pn_soberania_ano.csv")
for c in CATS:
    for a in ANOS:
        add(f"Gráfico 5: {NOME[c]} {a}", conf.get(f"g5_{c}_{a}"), mi(s(cat, "valor_nominal", categoria=c, ano=a)), TP + "pn_categoria_ano.csv")
for r in sob:
    add(f"Gráfico 6: participação {r['ano']}", conf.get(f"g6_{r['ano']}"),
        fmt_pct(100 * f(r["soberania_2a_nominal"]) / f(r["homologado_total_nominal"])), TP + "pn_soberania_ano.csv")
mod = ler(TP + "pn_modalidade_soberania.csv")
t_sob = s(mod, "valor_nominal", recorte="todas")
for m in sorted({r["modalidade"] for r in cubo}):
    add(f"Gráfico 7: {m}, tecnologias críticas", conf.get(f"g7_sob_{m}"), fmt_pct(100 * s(mod, "valor_nominal", recorte="todas", modalidade=m) / t_sob), TP + "pn_modalidade_soberania.csv")
    add(f"Gráfico 7: {m}, total das compras", conf.get(f"g7_tot_{m}"), fmt_pct(100 * s(cubo, "hom_nominal", modalidade=m) / HOM), TP + "pn_cubo_compras.csv")
add("Gráfico 8: valor total dos fluxos", conf.get("g9_total"), mi(s(ler(TP + "pn_fluxo.csv"), "valor_nominal")), TP + "pn_fluxo.csv")
# tabelas 1 a 3 e Sankey (valores em centavos, como embutidos no painel; mesma ordem de desempate do painel)
conc = ler(TP + "pn_concentracao.csv")
flux = ler(TP + "pn_fluxo.csv")
orgs_pn = ler(TP + "pn_orgaos.csv")
ESF = ["Federal", "Estadual", "Municipal", "Distrital", "Esfera não informada"]
FORN = sorted({(r["cnpj_fornecedor"], r["fornecedor"]) for r in flux})
iF = {k: i for i, k in enumerate(FORN)}
ORG = sorted({r["orgao"] for r in flux} | {r["orgao"] for r in orgs_pn})
iO = {k: i for i, k in enumerate(ORG)}
FX = [(r["categoria"], iF[(r["cnpj_fornecedor"], r["fornecedor"])], iO[r["orgao"]], ESF.index(r["esfera"]), round(f(r["valor_nominal"]), 2)) for r in flux]


def soma_por(rows, k):
    m = {}
    for r in rows:
        m[r[k]] = m.get(r[k], 0) + r[4]
    return m


def ordena(m):
    return sorted(m.items(), key=lambda kv: (-kv[1], kv[0]))


# tabela 2: maiores cadeias fornecedor (raiz do CNPJ) -> objeto -> orgao, 5 primeiras de cada categoria no recorte padrao
CAD = ler(TP + "pn_cadeias_compras.csv")
OBJ = {r["id_compra"]: r["objeto"] for r in ler(TP + "pn_cadeias_objetos.csv")}
RZ = {r["raiz_cnpj"]: r for r in ler(TP + "pn_fornecedor_raiz.csv")}
ICOMP = {c: i for i, c in enumerate(sorted(OBJ))}
abrev70 = lambda t: t[:69].rstrip() + "…" if len(t) > 70 else t
for c in CATS:
    rc = [r for r in CAD if r["categoria"] == c]
    t = sum(round(f(r["valor_nominal"]), 2) for r in rc)
    m = {}
    for r in rc:
        x = m.setdefault((r["raiz_cnpj"], r["orgao"]), [0, {}])
        v = round(f(r["valor_nominal"]), 2)
        x[0] += v
        x[1][r["id_compra"]] = x[1].get(r["id_compra"], 0) + v
    top = sorted(m.items(), key=lambda kv: (-kv[1][0], RZ[kv[0][0]]["nome"], kv[0][1]))[:5]
    for k, ((z, o), (v, comp)) in enumerate(top):
        cm = sorted(comp.items(), key=lambda kv: (-kv[1], ICOMP[kv[0]]))[0][0]
        ob = abrev70(OBJ[cm]) + (f" e mais {inteiro(len(comp) - 1)}" if len(comp) > 1 else "")
        add(f"Tabela 1: {NOME[c]}, {k + 1}ª cadeia (fornecedor|porte|objeto|órgão|valor|nº de compras|%)", conf.get(f"t1_{NOME[c]}_{k}"),
            f"{RZ[z]['nome']}|{RZ[z]['porte']}|{ob}|{o}|{fmt_escala(v / 1e6)}|{inteiro(len(comp))}|{fmt_pct(100 * v / t)}",
            TP + "pn_cadeias_compras.csv, " + TP + "pn_cadeias_objetos.csv, " + TP + "pn_fornecedor_raiz.csv",
            "valor_nominal; id_compra; objeto; nome; porte")
# grafico 9: valor e 3 principais nomes do tooltip de cada fluxo, no recorte padrao
F = ordena(soma_por(FX, 1))
O = ordena(soma_por(FX, 2))
topF, topO = {k for k, _ in F[:10]}, {k for k, _ in O[:10]}
nomeF = lambda i: FORN[i][1] if i in topF else f"Demais fornecedores ({inteiro(len(F) - len(topF))})"
nomeO = lambda i: ORG[i] if i in topO else f"Demais órgãos ({inteiro(len(O) - len(topO))})"
gF = lambda r: r[1] if r[1] in topF else "D"
gO = lambda r: r[2] if r[2] in topO else "D"
links = {}
for r in FX:
    links.setdefault(("f", gF(r), r[0]), []).append(r)
    links.setdefault(("o", r[0], gO(r)), []).append(r)
for (tipo, a, b), rs in links.items():
    v = sum(r[4] for r in rs)
    if v <= 0:
        continue
    if tipo == "f":
        chave = f"{nomeF(a) if a != 'D' else nomeF(-1)} > {NOME[b]}"
        top3 = ordena(soma_por(rs, 2))[:3]
        lst = "; ".join(f"{ORG[i]}: {mi(x)}" for i, x in top3)
    else:
        chave = f"{NOME[a]} > {nomeO(b) if b != 'D' else nomeO(-1)}"
        top3 = ordena(soma_por(rs, 1))[:3]
        lst = "; ".join(f"{FORN[i][1]}: {mi(x)}" for i, x in top3)
    add(f"Gráfico 8: tooltip do fluxo {chave} (valor|3 principais)", conf.get(f"g9_tt_{chave}"), f"{mi(v)}|{lst}", TP + "pn_fluxo.csv")
ins = ler(TP + "pn_instrumentos.csv")
base = s(ins, "valor_nominal", recorte="todas")
for chave, campo in (("g10_prevista", "margem_prevista_nominal"), ("g10_aplicada", "margem_aplicada_nominal"), ("g10_ppb", "ppb_nominal")):
    x = s(ins, campo, recorte="todas")
    add(f"Indicadores: {campo.replace('_nominal', '')}", conf.get(chave), f"{fmt_pct(100 * x / base)} | {'R$ 0' if x == 0 else mi(x)}", TP + "pn_instrumentos.csv")
pre = ler(TP + "pn_instrumentos_preenchimento.csv")
ncm = ler(TP + "pn_margem_ncm.csv")
# cartoes das categorias excluidos na v5: a verificacao de cada categoria e conferida no Dicionario de termos da metodologia (fim do script)
# total das seis categorias e soma por categoria (1.2); a compra inteira em cada categoria (regra 2c) so na metodologia
v2b, v2c = bi(f(tres["regra_2b"])), bi(f(tres["regra_2c"]))
add("Sobre: nota do KPI soberania, soma por categoria", v2b if v2b in textos_i.get("sobre_soberania", "") else textos_i.get("sobre_soberania", ""), v2b, TP + "pn_soberania_tres_regras.csv", "regra_2b")
add("Ícones i sem a compra inteira em cada categoria (R$ 55,6 bi): ícones que citam o valor", str(sum(v2c in t for t in textos_i.values())), "0", TP + "pn_soberania_tres_regras.csv", "regra_2c")
for rot, v, col in (("total das seis categorias", bi(V2A), "regra_2a"), ("soma por categoria", v2b, "regra_2b"), ("compra inteira em cada categoria identificada", v2c, "regra_2c")):
    add(f"METODOLOGIA_v5_1.md, tabela das três regras: {rot}", v if f"| {v} |" in met else "ausente", v, TP + "pn_soberania_tres_regras.csv", col)
add("Gráfico 5: i com o total das seis categorias", bi(V2A) if f"supera o total das seis categorias ({bi(V2A)}), em que cada compra entra uma vez." in textos_i.get("g5", "") else textos_i.get("g5", ""),
    bi(V2A), TP + "pn_soberania_tres_regras.csv", "regra_2a")
for rot, chave in (("compras publicadas", "sobre_kpi_compras"), ("valor homologado total", "sobre_kpi_valor"),
                   ("homologado em tecnologias críticas para a soberania digital", "sobre_kpi_soberania"), ("participação", "sobre_kpi_participacao"),
                   ):
    v = conf.get(chave)
    add(f"METODOLOGIA_v5_1.md contém o número do painel: {rot}", v, v if v and v in met else "ausente", "METODOLOGIA_v5_1.md")
for r in ler(TP + "pn_precisao_final.csv"):
    v = fmt_pct(f(r["precisao_pct"]))
    add(f"METODOLOGIA_v5_1.md contém a precisão de {NOME[r['categoria']]}", v, v if f"| {v} |" in met else "ausente", "METODOLOGIA_v5_1.md")

# ---------------- versao 2: KPIs de fornecedores e orgaos, frase de abertura e linha-resumo do Sankey
fc = ler(TP + "pn_fluxo_compras.csv")
pl = lambda n, um, varios: f"{inteiro(n)} {um if n == 1 else varios}"


def frase(quando, n, sujeito, valor, rows_c):
    m, nf, no = len({r["id_compra"] for r in rows_c}), len({r["cnpj_fornecedor"] for r in rows_c}), len({r["orgao"] for r in rows_c})
    vend = (" Não há compras com fornecedor vencedor identificado no recorte." if not m else
            f" {'Na única compra' if m == 1 else f'Nas {inteiro(m)} compras'} com fornecedor vencedor identificado, "
            f"{pl(nf, 'fornecedor', 'fornecedores')} {'vendeu' if nf == 1 else 'venderam'} para {pl(no, 'órgão', 'órgãos')}.")
    return f"{quando}, {pl(n, 'compra', 'compras')} de {sujeito} {'somou' if n == 1 else 'somaram'} {bi(valor)} em valor homologado." + vend


def resumo(rows_c, rows_v):
    return (f"{pl(len({r['id_compra'] for r in rows_c}), 'compra com vencedor identificado', 'compras com vencedor identificado')} · {pl(len({r['cnpj_fornecedor'] for r in rows_c}), 'fornecedor', 'fornecedores')} · "
            f"{pl(len({r['orgao'] for r in rows_c}), 'órgão', 'órgãos')} · {mi(sum(round(f(r['valor_nominal']), 2) for r in rows_v))} (valor dos resultados, soma por categoria)")


ORIG2 = TP + "pn_fluxo_compras.csv"
add("Soberania: KPI fornecedores vencedores", conf.get("sd_kpi_forn"), inteiro(len({r["cnpj_fornecedor"] for r in fc})), ORIG2)
add("Soberania: KPI órgãos compradores", conf.get("sd_kpi_org"), inteiro(len({r["orgao"] for r in fc})), ORIG2)
add("Gráfico 8: linha-resumo (recorte padrão)", conf.get("g9_resumo"), resumo(fc, flux), ORIG2 + ", " + TP + "pn_fluxo.csv")
for c in CATS:
    fcc = [r for r in fc if r["categoria"] == c]
    nf, no = len({r["cnpj_fornecedor"] for r in fcc}), len({r["orgao"] for r in fcc})
    add(f"Gráfico 8: linha-resumo com {NOME[c]} selecionada", conf.get(f"g9_resumo_{c}"), resumo(fcc, [r for r in flux if r["categoria"] == c]), ORIG2 + ", " + TP + "pn_fluxo.csv")
    add(f"Soberania: KPI fornecedores vencedores, filtro {NOME[c]}", conf.get(f"sd_kpi_forn_{c}"), inteiro(nf), ORIG2)
    add(f"Soberania: KPI órgãos compradores, filtro {NOME[c]}", conf.get(f"sd_kpi_org_{c}"), inteiro(no), ORIG2)
fc5, fl5 = [r for r in fc if r["ano"] == "2025"], [r for r in flux if r["ano"] == "2025"]
nf5, no5 = len({r["cnpj_fornecedor"] for r in fc5}), len({r["orgao"] for r in fc5})
add("Gráfico 8: linha-resumo com filtro de ano 2025", conf.get("g9_resumo_2025"), resumo(fc5, fl5), ORIG2 + ", " + TP + "pn_fluxo.csv")
add("Soberania: KPI fornecedores vencedores, filtro 2025", conf.get("sd_kpi_forn_2025"), inteiro(nf5), ORIG2)
add("Soberania: KPI órgãos compradores, filtro 2025", conf.get("sd_kpi_org_2025"), inteiro(no5), ORIG2)
ex = f"de 2021 a 2026, {inteiro(len({r['cnpj_fornecedor'] for r in fc}))} fornecedores venceram resultados nas seis categorias"
add("Soberania: exemplo do i do KPI de fornecedores", ex if ex in textos_i.get("sd_forn", "") else textos_i.get("sd_forn", ""), ex, ORIG2)
V_SK = mi(s(flux, "valor_nominal"))
ex = (f"O valor do diagrama é a soma do valor homologado nos resultados de cada categoria. Uma compra classificada em mais de uma categoria aparece em cada uma delas; "
      f"por isso o total do diagrama ({V_SK}) é maior que o total das seis categorias ({bi(V2A)}), em que cada compra entra uma vez.")
add("Gráfico 8: nota do i (total do diagrama e total das seis categorias)", f"{V_SK}|{bi(V2A)}" if ex in textos_i.get("g9", "") else textos_i.get("g9", ""), f"{V_SK}|{bi(V2A)}",
    TP + "pn_fluxo.csv, " + TP + "pn_soberania_tres_regras.csv")
ex = f"de 2021 a 2026, {inteiro(len({r['orgao'] for r in fc}))} órgãos compraram nas seis categorias"
add("Soberania: exemplo do i do KPI de órgãos", ex if ex in textos_i.get("sd_org", "") else textos_i.get("sd_org", ""), ex, ORIG2)


# ---------------- bloco 'Como o Estado contrata essas tecnologias e de quem depende' e principais achados
mod_r, vend_r, marca_r = ler(TP + "pn_modelo_categoria_ano.csv"), ler(TP + "pn_vendedor_categoria_ano.csv"), ler(TP + "pn_marca_resultados.csv")
porte_c, porte_v, ach_r = ler(TP + "pn_porte_compras.csv"), ler(TP + "pn_porte_valor.csv"), ler(TP + "pn_achados.csv")
r2 = lambda x: round(f(x), 2)


def marca_linha(rows):
    res = {}
    for r in rows:
        res.setdefault(r["chave_resultado"], r)
    tot = sum(r2(r["valor_nominal"]) for r in res.values())
    por = {}
    for r in res.values():
        por[r["raiz_cnpj_vendedor"]] = por.get(r["raiz_cnpj_vendedor"], 0) + r2(r["valor_nominal"])
    vs = sorted(por.values(), reverse=True)
    tp = lambda t: sum(r2(r["valor_nominal"]) for r in res.values() if r["tipo_vendedor"] == t)
    n = len({r["id_compra"] for r in rows})
    return n, f"{inteiro(n)}|{fmt_escala(tot / 1e6)}|{fmt_pct(100 * tp('Revendedor ou integrador') / tot)}|{fmt_pct(100 * tp('Fabricante direto') / tot)}|" \
              f"{inteiro(len(por))}|{fmt_pct(100 * sum(vs[:4]) / tot)}|{fmt_num(sum((v / tot) ** 2 for v in vs), 3)}"


for rec, filtro, rot in [("", lambda r: True, "2021 a 2026")] + [("_" + c, (lambda c: lambda r: r["categoria"] == c)(c), NOME[c] + ", 2021 a 2026") for c in CATS] + \
        [("_2025", lambda r: r["ano"] == "2025", "2025")]:
    for m in sorted({r["marca"] for r in marca_r}):
        n, lin = marca_linha([r for r in marca_r if r["marca"] == m and filtro(r)] or [{"chave_resultado": "-", "valor_nominal": 1, "raiz_cnpj_vendedor": "-", "tipo_vendedor": "-", "id_compra": "-"}])
        if n >= 20:
            add(f"Tabela 2: {m}, {rot} (compras|valor|% revendedores|% fabricante|vendedores|CR4|HHI)", conf.get(f"tm_{m}{rec}"), lin, TP + "pn_marca_resultados.csv")
ach_painel = conf.get("achados_painel", [])
# numeros de cada achado: valor exibido no painel x valor gerado por fase2/scripts/f2_11_achados.py, com a base de cada numero
f2n = {(x["achado"], x["indicador"].replace("no valor sem dupla contagem", "no total das seis categorias")): x["valor_exibido"] for x in ler("fase2/tabelas/f2_11_numeros_achados.csv")}
nums = ler(TP + "pn_achados_numeros.csv")
# achado 4: definicao da aba de IA, recalculada de ia_base.csv e ia_base_classes.csv
_iab = {x["id_compra"]: x for x in ler(TP + "ia_base.csv")}
_iac = sorted({x["id_compra"] for x in ler(TP + "ia_base_classes.csv") if x["classe"] == "Acréscimo à licença"})  # compras com parte de acrescimo
ACH_IA = {"valor do acréscimo à licença (aba de IA)": mi(sum(round(f(x["valor_nominal"]), 2) for x in ler(TP + "ia_base_classes.csv") if x["classe"] == "Acréscimo à licença")),
          "compras do acréscimo à licença (aba de IA)": inteiro(len(_iac)),
          "compras do acréscimo na categoria Inteligência artificial": inteiro(sum(1 for c in _iac if _iab[c]["componente"] == "A"))}
for k, r in enumerate(ach_r):
    painel = ach_painel[k] if k < len(ach_painel) else None
    add(f"Principais achados: {r['achado']}. {r['titulo']} (título e texto)", painel, f"{r['achado']}. {r['titulo']}||{r['texto']}", TP + "pn_achados.csv")
    for nr in [x for x in nums if x["achado"] == r["achado"]]:
        v = nr["valor_exibido"]
        esp_ach = f2n[(nr["achado_f2_11"], nr["indicador"])] if nr["achado_f2_11"] else ACH_IA[nr["indicador"]]
        add(f"Principais achados: {r['achado']}, {nr['indicador']} ({nr['base']})", v if painel and v in painel.split("||")[1] else "ausente", esp_ach,
            nr["arquivo_de_origem"], f"valor do indicador '{nr['indicador']}' em fase2/tabelas/f2_11_numeros_achados.csv; base: {nr['base']}")
_nm = len({x["marca"] for x in ler("fase2/dicionario_marcas.csv")})
add("Principais achados: 2, número de marcas analisadas", str(_nm) if ach_painel and f"as {_nm} marcas analisadas" in ach_painel[1] else "ausente", str(_nm),
    "fase2/dicionario_marcas.csv", "marca (marcas distintas)")
for chave in ("tm",):
    add(f"Ícone i ({chave}): exemplo de leitura com número", "sim" if "Exemplo de leitura" in textos_i.get(chave, "") and _re.search(r"\d", textos_i.get(chave, "")) else "não", "sim",
        TP + "pn_textos_i.csv")


# ---------------- v3, parte 1: exemplos de leitura e texto do grafico 9 nos dois modos, selo, limitacao e revisao manual
alt = ler("verificacao_html_v5_1/alternador_exemplos.csv")
MODOS = ["valores nominais", "valores deflacionados"]
FRASE = ["Valores nominais.", "Valores deflacionados, a preços de " + _re.search(r"Mês-base: (\w+ de \d{4})", met).group(1) + "."]  # frase final dos textos que citam reais
comp_ = ler(TP + "pn_modelo_grupo_componentes.csv")
fx = ler(TP + "pn_fluxo.csv")
inst, ncm_, modal_ = ler(TP + "pn_instrumentos.csv"), ler(TP + "pn_margem_ncm.csv"), ler(TP + "pn_modalidade_soberania.csv")
forma_, perfil_ = ler(TP + "pn_forma_contratacao.csv"), ler(TP + "pn_perfil.csv")
NUM = _re.compile(r"R\$ [\d.]+(?:,\d+)?(?: bi| mi| mil)?|[\d.]+(?:,\d+)?%|\d+,\d+|\d{1,3}(?:\.\d{3})+|\b\d+\b")


def esperados(dv):
    """Exemplos de leitura recalculados aqui, sobre as tabelas agregadas arredondadas a centavos (como no painel)."""
    sx = ["nominal", "deflacionado"][dv]
    sm = lambda rows, col, **k: sum(r2(r[col]) for r in rows if all(str(r[a]) == str(b) for a, b in k.items()))
    ta = {a: sm(cubo, "hom_" + sx, ano=a) for a in ANOS}
    T = sum(ta.values())
    ordem = sorted(CATS, key=lambda c: -s(cat, "valor_nominal", categoria=c))
    pc = lambda dim, v: fmt_pct(100 * sm(cubo, "hom_" + sx, ano=2025, **{dim: v}) / ta[2025])
    v6 = sum(r2(r["soberania_2a_" + sx]) for r in sob)
    c25 = max(CATS, key=lambda c: sm(cat, "valor_" + sx, categoria=c, ano=2025))
    cm = max(CATS, key=lambda c: sm(cat, "valor_" + sx, categoria=c))
    g = {}
    for r in fx:
        g[(r["fornecedor"], r["categoria"], r["cnpj_fornecedor"])] = g.get((r["fornecedor"], r["categoria"], r["cnpj_fornecedor"]), 0) + r2(r["valor_" + sx])
    k9 = max(g, key=g.get)
    o9 = {}
    for r in fx:
        if (r["fornecedor"], r["categoria"], r["cnpj_fornecedor"]) == k9:
            o9[r["orgao"]] = o9.get(r["orgao"], 0) + r2(r["valor_" + sx])
    cc = [r for r in conc if r["ano"] == "2025"]
    hx, hn = max(cc, key=lambda r: f(r["hhi_" + sx])), min(cc, key=lambda r: f(r["hhi_" + sx]))
    srp = {c: sum(f(p["pct_srp_" + sx]) / 100 * sm(cat, "valor_" + sx, categoria=c, ano=p["ano"]) for p in perfil_ if p["categoria"] == c) / sm(cat, "valor_" + sx, categoria=c) for c in CATS}
    cs = max(CATS, key=srp.get)
    cag = {}
    for r in CAD:
        if r["categoria"] == ordem[0]:
            x = cag.setdefault((r["raiz_cnpj"], r["orgao"]), [0, set()])
            x[0] += r2(r["valor_" + sx])
            x[1].add(r["id_compra"])
    cam = max(cag, key=lambda k: cag[k][0])
    tca = sum(r2(r["valor_" + sx]) for r in CAD if r["categoria"] == ordem[0])
    mp = lambda c, cl: 100 * sm(mod_r, "valor_" + sx, categoria=c, classe=cl) / sm(mod_r, "valor_" + sx, categoria=c)
    vp = lambda c, tp: 100 * sm(vend_r, "valor_" + sx, categoria=c, tipo_vendedor=tp) / sm(vend_r, "valor_" + sx, categoria=c)
    ms = [r for r in marca_r if r["marca"] == "Microsoft"]
    res = {}
    for r in ms:
        res.setdefault(r["chave_resultado"], r)
    mt = sum(r2(r["valor_" + sx]) for r in res.values())
    por = {}
    for r in res.values():
        por[r["raiz_cnpj_vendedor"]] = por.get(r["raiz_cnpj_vendedor"], 0) + r2(r["valor_" + sx])
    rev = 100 * sum(r2(r["valor_" + sx]) for r in res.values() if r["tipo_vendedor"] == "Revendedor ou integrador") / mt
    pt = sm(porte_v, "valor_" + sx, recorte="todas")
    ca, cme = {r["id_compra"] for r in porte_c}, {r["id_compra"] for r in porte_c if r["porte"] == "ME ou EPP"}
    suf = ". " + FRASE[dv]
    perm = "Licenciamento de direitos permanentes de uso"
    nvg = "Serviços técnicos, equipamentos e não identificados"
    q = [mp(c, nvg) for c in ("data_center", "seguranca", "ia", "identidade")]
    vc = lambda o: sum(r2(r["valor_" + sx]) for r in comp_ if r["ordem"] == o)
    return {
        "g1_valor": (f"em 2025, o valor global homologado foi de {bi(ta[2025])}" + suf, "pn_cubo_compras.csv", "hom_" + sx),
        "g2": (f"em 2025, a esfera federal respondeu por {pc('esfera', 'Federal')} do valor global homologado.", "pn_cubo_compras.csv", "hom_" + sx + "; esfera"),
        "g3": (f"em 2025, o Poder Executivo respondeu por {pc('poder', 'Executivo')} do valor global homologado.", "pn_cubo_compras.csv", "hom_" + sx + "; poder"),
        "g4": (f"em 2025, o pregão eletrônico respondeu por {pc('modalidade', 'Pregão eletrônico')} do valor global homologado.", "pn_cubo_compras.csv", "hom_" + sx + "; modalidade"),
        "sd_valor": (f"dos {bi(T)} homologados no período, {bi(v6)} referem-se às seis categorias" + suf, "pn_cubo_compras.csv; pn_soberania_ano.csv", f"hom_{sx}; soberania_2a_{sx}"),
        "sd_part": (f"a cada R$ 100 homologados, cerca de {reais(100 * v6 / T)} foram destinados às tecnologias críticas para a soberania digital" + suf, "pn_cubo_compras.csv; pn_soberania_ano.csv", f"hom_{sx}; soberania_2a_{sx}"),
        "g5": (f"em 2025, {NOME[c25]} somou {mi(sm(cat, 'valor_' + sx, categoria=c25, ano=2025))}" + suf, "pn_categoria_ano.csv", "valor_" + sx),
        "g6": (f"em 2025, {fmt_pct(100 * r2(next(r for r in sob if r['ano'] == '2025')['soberania_2a_' + sx]) / ta[2025])} do valor global homologado correspondeu às seis categorias.", "pn_soberania_ano.csv; pn_cubo_compras.csv", f"soberania_2a_{sx}; hom_{sx}"),
        "g7": (f"nas tecnologias críticas, a inexigibilidade respondeu por {fmt_pct(100 * sm(modal_, 'valor_' + sx, recorte='todas', modalidade='Inexigibilidade') / sm(modal_, 'valor_' + sx, recorte='todas'))} do valor, "
               f"ante {fmt_pct(100 * sm(cubo, 'hom_' + sx, modalidade='Inexigibilidade') / T)} no total das compras.", "pn_modalidade_soberania.csv; pn_cubo_compras.csv", f"valor_{sx}; hom_{sx}"),
        "g9": (f"{k9[0]} recebeu {mi(g[k9])} em {NOME[k9[1]]}, principalmente de {max(o9, key=o9.get)}" + suf, "pn_fluxo.csv", "valor_" + sx),
        "t1": (f"em {NOME[ordem[0]]}, a maior cadeia de 2021 a 2026 vai de {RZ[cam[0]]['nome']} a {cam[1]}, com {mi(cag[cam][0])} em {inteiro(len(cag[cam][1]))} "
               f"compra{'s' if len(cag[cam][1]) > 1 else ''}, {fmt_pct(100 * cag[cam][0] / tca)} da categoria" + suf, "pn_cadeias_compras.csv; pn_fornecedor_raiz.csv", "valor_" + sx + "; raiz_cnpj; orgao; id_compra"),
        "g10": (f"{fmt_pct(100 * sm(inst, 'margem_aplicada_' + sx, recorte='todas') / sm(inst, 'valor_' + sx, recorte='todas'))} do total das seis categorias teve margem de preferência aplicada.", "pn_instrumentos.csv", f"margem_aplicada_{sx}; valor_{sx}"),
        "tm": (f"de 2021 a 2026, a Microsoft foi citada em {inteiro(len({r['id_compra'] for r in ms}))} compras, com {mi(mt)} em resultados; revendedores ficaram com {fmt_pct(rev)} desse valor, "
               f"entre {inteiro(len(por))} vendedores, com HHI de {fmt_num(sum((v / mt) ** 2 for v in por.values()), 3)}" + suf, "pn_marca_resultados.csv", f"chave_resultado; raiz_cnpj_vendedor; tipo_vendedor; valor_{sx}"),
    }


for dv, modo in enumerate(MODOS):
    esp = esperados(dv)
    exib = {}
    for r in alt:
        if r["modo"] == modo:
            k = r["elemento"].split(": ")[1]
            exib[k] = r["texto_exibido"]
    for k, (texto, arq, col) in esp.items():
        t = exib.get(k)
        rot = f"Exemplo de leitura do i ({k}), {modo}: {t}"
        add(rot, "; ".join(NUM.findall(t)) if t is not None else "ausente", "; ".join(NUM.findall(texto)) if t == texto else f"texto diferente: {texto}",
            "; ".join(TP + a for a in arq.split("; ")), col)
ex_s = [r for r in alt if r["elemento"].endswith("sobre_participacao")][0]["texto_exibido"]
add(f"Exemplo de leitura do i (sobre_participacao), aba Sobre: {ex_s}", "; ".join(NUM.findall(ex_s)),
    "; ".join(NUM.findall(f"a cada R$ 100 homologados em compras públicas, aproximadamente {reais(100 * V2A / HOM)} correspondem às seis categorias. Valores nominais.")),
    TP + "pn_soberania_tres_regras.csv; " + TP + "pn_cubo_compras.csv", "regra_2a; hom_nominal")
# limitacao do licenciamento de direitos permanentes de uso
lpc = ler(TP + "pn_direitos_permanentes_codigo.csv")[0]
m_ = _re.search(r"No licenciamento de direitos permanentes de uso, ([\d,]+%) do valor \((R\$ [\d.,]+ mi) de (R\$ [\d.,]+ mi)\) foi identificado só pelo nome do código do catálogo", met)
add("METODOLOGIA_v5_1.md, limitações: licenciamento de direitos permanentes de uso identificado só pelo código do catálogo", "; ".join(m_.groups()) if m_ else "ausente",
    f"{fmt_pct(f(lpc['pct_so_codigo_catalogo']))}; {mi(f(lpc['valor_so_codigo_catalogo']))}; {mi(f(lpc['valor_classe_total']))}", TP + "pn_direitos_permanentes_codigo.csv")
# revisao manual da pesquisadora responsavel: classe 3 (licenciamento de direitos permanentes de uso), 14 de 15 (93%)
rh = next(r for r in ler("fase2/validacao/resultado_revisao_humana.csv") if r["classe"] == "Licenciamento de direitos permanentes de uso")
m_ = _re.search(r"\| Modelo de aquisição \| Licenciamento de direitos permanentes de uso \| (\d+) \| (\d+) \| (\d+) \| ([\d,]+%) \| (\w+) \|", met)
add("METODOLOGIA_v5_1.md, revisão manual realizada pela pesquisadora responsável (Mabel Mota): licenciamento de direitos permanentes de uso (revisados; certo; errado; concordância; validada)", "; ".join(m_.groups()) if m_ else "ausente",
    f"{rh['linhas_revisadas']}; {rh['certo']}; {rh['errado']}; {fmt_pct(f(rh['concordancia_pct']))}; {rh['validada']}", "fase2/validacao/resultado_revisao_humana.csv")
# concordancia entre revisoes (revisao manual x verificacao por amostragem)
cr = ler("fase2/validacao/concordancia_entre_revisoes.csv")
nc = sum(r["concordam"] == "sim" for r in cr)
m_ = _re.search(r"Concordância entre a revisão manual realizada pela pesquisadora responsável \(Mabel Mota\) e a verificação por amostragem, nos mesmos casos: ([\d.]+) de ([\d.]+) \(([\d,]+%)\)", met)
add("METODOLOGIA_v5_1.md, revisão manual realizada pela pesquisadora responsável (Mabel Mota): concordância entre revisões (casos; total; %)", "; ".join(m_.groups()) if m_ else "ausente",
    f"{inteiro(nc)}; {inteiro(len(cr))}; {fmt_pct(100 * nc / len(cr))}", "fase2/validacao/concordancia_entre_revisoes.csv")

# grafico 11: conferencias do Sankey nos dois modos (verificacao_html_v5_1/sankey_conferencia.csv, lidas no Chromium por p1_03)
for r in ler("verificacao_html_v5_1/sankey_conferencia.csv"):
    add(f"Gráfico 8, {r['filtro']}, modo {r['modo']}: {r['medida']}", r["valor_no_grafico"], r["valor_calculado"], r["arquivo_de_origem"],
        "valor_nominal" if r["modo"] == "Valor" else "id_compra; cnpj_fornecedor; orgao; categoria")



# ---------------- aba Inteligencia artificial (recalculo independente a partir de ia_*.csv, recorte padrao, valores nominais)

IA_CLS = ["Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)", "Outros", "Capacitação"]

FIL = {"tec": [0, 1, 2], "acr": [0], "sol": [1], "out": [2], "cap": [3]}

DESC = {"tec": "Todas (tecnologia)", "acr": "Acréscimo à licença", "sol": "Solução de IA (exclusiva ou em pacote)", "out": "Outros", "cap": "Capacitação"}

ib, ipa, ir = ler(TP + "ia_base.csv"), ler(TP + "ia_base_classes.csv"), ler(TP + "ia_resultados.csv")
NOME_TIPO = {"Nuvem/cloud broker": "Nuvem com serviços de IA", "Outros objetos": "Capacitação"}  # nomes exibidos no painel v5
for _r in ib + ir:
    _r["tipo_objeto"] = NOME_TIPO.get(_r["tipo_objeto"], _r["tipo_objeto"])

ifc = {r["cnpj_fornecedor"]: r["nome"] for r in ler(TP + "ia_fornecedores_cnpj.csv")}

ifr = {r["raiz_cnpj"]: r for r in ler(TP + "ia_fornecedores.csv")}

iobj = {r["id_compra"]: r["objeto"] for r in ler(TP + "ia_objetos.csv")}

TIPOS = [r["objeto"] for r in ler(TP + "dicionario_ia_tipos.csv")]

CNPJS = sorted({r["cnpj_fornecedor"] for r in ir})

ORGS = sorted({r["orgao"] for r in ir})

ICOMP = {c: i for i, c in enumerate(sorted(r["id_compra"] for r in ib))}

FIA = "tabelas_painel_v3/ia_base.csv, tabelas_painel_v3/ia_base_classes.csv, tabelas_painel_v3/ia_resultados.csv"





def mercado(cls):

    nomes = {IA_CLS[i] for i in cls}

    rs = [r for r in ir if r["classe"] in nomes]

    return (sum(1 for r in ib if r["classe"] in nomes), sum(r2(r["valor_nominal"]) for r in ipa if r["classe"] in nomes),

            len({r["cnpj_fornecedor"] for r in rs}), len({r["orgao"] for r in rs}))





txt_m = lambda rot, m: f"{rot}: {pl(m[0], 'compra', 'compras')} · {pl(m[2], 'fornecedor', 'fornecedores')} · {pl(m[3], 'órgão', 'órgãos')} · {mi(m[1])}"





def ordena_k(d):  # mesma ordem do painel: valor decrescente, depois o indice

    return sorted(d.items(), key=lambda kv: (-kv[1], kv[0]))





for fk, cls in FIL.items():

    tec = cls if fk in ("acr", "sol", "out") else [0, 1, 2]

    rot = f"Tecnologia de IA, {IA_CLS[tec[0]]}" if fk in ("acr", "sol", "out") else "Tecnologia de IA"

    nomes = {IA_CLS[i] for i in cls}

    rs = [r for r in ir if r["classe"] in nomes]

    tot = sum(r2(r["valor_nominal"]) for r in rs)

    add(f"Aba IA, filtro {DESC[fk]}: linha-resumo do gráfico 9", conf.get(f"ia_skresumo_{fk}"),

        f"{pl(len({r['id_compra'] for r in rs}), 'compra com vencedor identificado', 'compras com vencedor identificado')} · {pl(len({r['cnpj_fornecedor'] for r in rs}), 'fornecedor', 'fornecedores')} · "

        f"{pl(len({r['orgao'] for r in rs}), 'órgão', 'órgãos')} · {mi(tot)} (valor dos resultados)", TP + "ia_resultados.csv", "valor_nominal; id_compra; cnpj_fornecedor; orgao")

    # tabela 5: cadeias (5 primeiras de cada classe)

    abrev = lambda t: t[:69].rstrip() + "…" if len(t) > 70 else t

    tc = {}

    for r in rs:

        tc[r["classe"]] = tc.get(r["classe"], 0) + r2(r["valor_nominal"])

    for c in [IA_CLS[i] for i in cls]:

        m = {}

        for r in rs:

            if r["classe"] != c:

                continue

            x = m.setdefault((r["raiz_cnpj"], r["orgao"]), [0, {}])

            x[0] += r2(r["valor_nominal"])

            x[1][r["id_compra"]] = x[1].get(r["id_compra"], 0) + r2(r["valor_nominal"])

        top = sorted(m.items(), key=lambda kv: (-kv[1][0], ifr[kv[0][0]]["nome"], kv[0][1]))[:5]

        for k, ((z, o), (v, comp)) in enumerate(top):

            cm = sorted(comp.items(), key=lambda kv: (-kv[1], ICOMP[kv[0]]))[0][0]

            ob = abrev(iobj[cm]) + (f" e mais {inteiro(len(comp) - 1)}" if len(comp) > 1 else "")

            add(f"Aba IA, filtro {DESC[fk]}: tabela de cadeias, {c}, {k + 1}ª cadeia", conf.get(f"ia_cad_{fk}_{c}_{k}"),

                f"{ifr[z]['nome']}|{ifr[z]['porte']}|{ob}|{o}|{fmt_escala(v / 1e6)}|{inteiro(len(comp))}|{fmt_pct(100 * v / tc[c])}",

                TP + "ia_resultados.csv, " + TP + "ia_objetos.csv, " + TP + "ia_fornecedores.csv", "valor_nominal; id_compra; objeto; nome; porte")

# grafico 12 (todas as classes de tecnologia): valor e numero de compras de cada fluxo

rs = [r for r in ir if r["classe"] != "Capacitação"]

vf_ = _soma(rs, lambda r: CNPJS.index(r["cnpj_fornecedor"]))

vo_ = _soma(rs, lambda r: ORGS.index(r["orgao"]))

topF = {k for k, _ in ordena_k(vf_)[:10]}

topO = {k for k, _ in ordena_k(vo_)[:10]}

nF = lambda i: ifc[CNPJS[i]] if i in topF else f"Demais fornecedores ({inteiro(len(vf_) - len(topF))})"

nO = lambda i: ORGS[i] if i in topO else f"Demais órgãos ({inteiro(len(vo_) - len(topO))})"

lk = {}

for r in rs:

    fi, oi, t = CNPJS.index(r["cnpj_fornecedor"]), ORGS.index(r["orgao"]), r["tipo_objeto"]

    for chave, par in (((nF(fi) if fi in topF else nF(-1)) + " > " + t, r["id_compra"] + "|" + r["cnpj_fornecedor"]),

                       (t + " > " + (nO(oi) if oi in topO else nO(-1)), r["id_compra"] + "|" + r["orgao"])):

        x = lk.setdefault(chave, [0.0, set()])

        x[0] += r2(r["valor_nominal"])

        x[1].add(par)

for chave, (v, ps) in lk.items():

    if v > 0:

        add(f"Aba IA, gráfico 9: fluxo {chave} (valor|nº de compras)", conf.get(f"ia_tt_{chave}"), f"{mi(v)}|{inteiro(len(ps))}", TP + "ia_resultados.csv", "valor_nominal; id_compra; cnpj_fornecedor; orgao")

# tabela 6: marcas

for r in ler(TP + "ia_marcas.csv"):

    add(f"Aba IA, tabela 3: {r['marca']} (compras de produto|valor|compras de capacitação|vendedores)", conf.get(f"ia_marca_{r['marca']}"),

        f"{inteiro(int(r['compras_de_produto']))}|{fmt_escala(r2(r['valor_nominal']) / 1e6)}|{inteiro(int(r['compras_de_capacitacao']))}|{r['principais_vendedores_compras_de_produto'] or '-'}",

        TP + "ia_marcas.csv", "compras_de_produto; valor_nominal; compras_de_capacitacao; principais_vendedores_compras_de_produto")

# achados da IA (texto do Ajuste 4 e numeros gerados por p4_01)
iach = ler("tabelas_painel_v5/ia_achados_v5.csv")
iach_p = conf.get("ia_achados_painel", [])
for k, r in enumerate(iach):
    painel = iach_p[k] if k < len(iach_p) else None
    add(f"Aba IA, principais achados: {r['achado']}. {r['titulo']} (título e texto)", painel, f"{r['achado']}. {r['titulo']}||{r['texto']}",
        "tabelas_painel_v5/ia_achados_v5.csv", "titulo; texto")
for r in ler("tabelas_painel_v5/ia_achados_numeros_v5.csv"):
    painel = iach_p[int(r["achado"]) - 1] if len(iach_p) >= int(r["achado"]) else ""
    add(f"Aba IA, principais achados: {r['achado']}, {r['indicador']} ({r['base']})", r["valor_exibido"] if r["valor_exibido"] in painel else "ausente", r["valor_exibido"],
        TP + r["arquivo_de_origem"], f"base: {r['base']}")
# achado 4 recalculado aqui de ia_resultados.csv (CNPJ do vencedor), independente de p4_01
_vf = _soma([r for r in ir if r["classe"] != "Capacitação"], lambda r: r["cnpj_fornecedor"])
_a4 = iach_p[3] if len(iach_p) > 3 else ""
add("Aba IA, achado 4: participação dos 10 maiores fornecedores (recalculada de ia_resultados.csv)",
    _a4.split("responderam por ")[1].split(" do valor")[0] if "responderam por " in _a4 else "ausente",
    fmt_pct(100 * sum(sorted(_vf.values(), reverse=True)[:10]) / sum(_vf.values())), TP + "ia_resultados.csv", "cnpj_fornecedor; valor_nominal (sem Capacitação)")
add("Aba IA, achado 4: fornecedores, CNPJ do vencedor (recalculado de ia_resultados.csv)",
    _a4.split("universo de ")[1].split(" fornecedores")[0] if "universo de " in _a4 else "ausente",
    inteiro(len(_vf)), TP + "ia_resultados.csv", "cnpj_fornecedor (sem Capacitação)")
# achados da IA identicos ao texto do Ajuste 5 (PROMPT_PAINEL_V5.md, item 4.4)
_prompt = open("PROMPT_PAINEL_V5.md", encoding="utf-8").read()
_p44 = _prompt[_prompt.index("### 4.4"):_prompt.index("## 5.")]
for k, r in enumerate(iach):
    m_ = _re.search(rf"^\s*{k + 1}\. \*\*(.+?)\*\* (.+)$", _p44, _re.M)
    esp_ = f"{k + 1}. {m_.group(1).rstrip('.')}||{m_.group(2)}" if m_ else "ausente"
    add(f"Aba IA, achado {k + 1}: texto igual ao do Ajuste 5 (item 4.4; título sem o ponto final)", iach_p[k] if k < len(iach_p) else None, esp_, "PROMPT_PAINEL_V5.md", "item 4.4")
# conferencias do grafico 12 e comparacao texto x grafico (lidas no Chromium por p1_03)

for r in ler("verificacao_html_v5_1/ia_sankey_conferencia.csv"):

    add(f"Aba IA, gráfico 9, filtro {DESC[r['filtro']]}, modo {r['modo']}: {r['medida']}", r["valor_no_grafico"], r["valor_calculado"], r["arquivo_de_origem"],

        "valor_nominal" if r["modo"] == "Valor" else "id_compra; cnpj_fornecedor; orgao")

# ---------------- versao 4: textos novos e comparacao texto x grafico
for r in ler("verificacao_html_v5_1/texto_grafico.csv"):
    add(f"Texto e gráfico, {r['elemento']}: {r['trecho_calculado_do_grafico']}", r["trecho_calculado_do_grafico"] if r["confere"] == "sim" else "ausente",
        r["trecho_calculado_do_grafico"], "verificacao_html_v5_1/texto_grafico.csv", "texto exibido x dados desenhados no gráfico", tg=r["confere"])
# margem de preferencia (item 3.4): texto recalculado de pn_instrumentos.csv e pn_instrumentos_preenchimento.csv
_pre = {r["indicador"]: r for r in ler(TP + "pn_instrumentos_preenchimento.csv")}
_p1, _p2, _p3 = (_pre[k] for k in ("margem de preferência prevista no edital", "margem de preferência aplicada no resultado", "exigência de Processo Produtivo Básico (PPB)"))
_cheio = "100%" if all(r["n_preenchidos"] == r["n_registros"] for r in (_p1, _p2, _p3)) else "ausente"
_t1 = (f'Os três campos estão preenchidos em {_cheio} dos registros, predominantemente com "falso". Há {inteiro(int(_p1["n_verdadeiro"]))} registros com margem de '
       f'preferência prevista no edital, {inteiro(int(_p2["n_verdadeiro"]))} com margem aplicada e {inteiro(int(_p3["n_verdadeiro"])) if int(_p3["n_verdadeiro"]) else "nenhum"} '
       'com exigência de PPB. A base não permite distinguir "não se aplica" de "não informado".')
_ext = lambda v: "R$ 0" if v == 0 else vauto(v).replace(" mi", " milhões").replace(" bi", " bilhões")


def _t2(ano=None):
    flt = {"recorte": "todas"} if ano is None else {"recorte": "todas", "ano": ano}
    b_, pv, ap, pp = (s(ins, c, **flt) for c in ("valor_nominal", "margem_prevista_nominal", "margem_aplicada_nominal", "ppb_nominal"))
    pc = lambda x: fmt_pct(100 * x / b_)
    t = f"{'De 2021 a 2026' if ano is None else f'Em {ano}'}, compras com margem prevista representaram {pc(pv)} do valor homologado das tecnologias críticas ({_ext(pv)})."
    if ap == 0 and pp == 0:
        t += " Não foram identificados valores associados à margem aplicada ou ao PPB."
    elif ap > 0 and pp > 0:
        t += f" As compras com margem aplicada representaram {pc(ap)} ({_ext(ap)}), e as compras com exigência de PPB, {pc(pp)} ({_ext(pp)})."
    elif ap > 0:
        t += f" As compras com margem aplicada representaram {pc(ap)} ({_ext(ap)}); não foram identificados valores associados ao PPB."
    else:
        t += f" As compras com exigência de PPB representaram {pc(pp)} ({_ext(pp)}); não foram identificados valores associados à margem aplicada."
    return t + " Valores nominais."


_O = TP + "pn_instrumentos.csv; " + TP + "pn_instrumentos_preenchimento.csv"
add("Instrumentos de política: nota metodológica do i (recorte padrão)", conf.get("g10_texto1"), _t1, TP + "pn_instrumentos_preenchimento.csv", "n_registros; n_preenchidos; n_verdadeiro")
add("Instrumentos de política: nota metodológica do i (filtro 2025)", conf.get("g10_texto1_2025"), _t1, TP + "pn_instrumentos_preenchimento.csv", "n_registros; n_preenchidos; n_verdadeiro")
add("Instrumentos de política: texto visível (recorte padrão, 2021 a 2026)", conf.get("g10_texto2"), _t2(), _O, "valor_nominal; margem_prevista_nominal; margem_aplicada_nominal; ppb_nominal")
add("Instrumentos de política: texto visível (filtro 2025)", conf.get("g10_texto2_2025"), _t2(2025), _O, "valor_nominal; margem_prevista_nominal; margem_aplicada_nominal; ppb_nominal")
_lit = ("Em 2025, compras com margem prevista representaram 0,6% do valor homologado das tecnologias críticas (R$ 80,3 milhões). "
        "Não foram identificados valores associados à margem aplicada ou ao PPB. Valores nominais.")
add("Margem de preferência, 2º parágrafo com filtro 2025 igual ao texto do Ajuste 4 (item 3.4)", conf.get("g10_texto2_2025"), _lit, "PROMPT_PAINEL_V5.md", "item 3.4")
add("Instrumentos de política: nota metodológica do i igual ao texto do Ajuste 5 (item 3.4.1)", conf.get("g10_texto1"),
    'Os três campos estão preenchidos em 100% dos registros, predominantemente com "falso". Há 253 registros com margem de preferência prevista no edital, 2 com margem '
    'aplicada e nenhum com exigência de PPB. A base não permite distinguir "não se aplica" de "não informado".', "PROMPT_PAINEL_V5.md", "item 3.4")
add("Margem de preferência, filtro 2025: percentual do texto igual ao do cartão", conf.get("g10_prevista_pct_2025"),
    fmt_pct(100 * s(ins, "margem_prevista_nominal", recorte="todas", ano=2025) / s(ins, "valor_nominal", recorte="todas", ano=2025)), TP + "pn_instrumentos.csv",
    "margem_prevista_nominal; valor_nominal", tg="sim" if conf.get("g10_prevista_pct_2025", "x") in (conf.get("g10_texto2_2025") or "") else "não")
# nota de encomenda tecnologica (item 3.5)
_enc = ler(TP + "pn_encomenda_cpsi.csv")
_n = [int(r["n_compras"]) for r in _enc]
_v = [vauto(f(r["valor_nominal"])) for r in _enc]
add("Encomenda tecnológica e CPSI (no i dos instrumentos)", conf.get("nota_encomenda"),
    f"Nas seis categorias, foram identificadas {inteiro(_n[0])} {'compra' if _n[0] == 1 else 'compras'} por encomenda tecnológica ({_v[0]}) e {inteiro(_n[1])} por solução "
    f"inovadora/CPSI ({_v[1]}). Pelo art. 75, V, da Lei 14.133/2021, há {inteiro(_n[2])} compras enquadradas ({_v[2]}), nem todas com menção explícita ao instrumento.",
    TP + "pn_encomenda_cpsi.csv", "n_compras; valor_nominal")
add("Encomenda tecnológica e CPSI igual ao texto do Ajuste 5 (item 3.4.4)", conf.get("nota_encomenda"),
    "Nas seis categorias, foram identificadas 1 compra por encomenda tecnológica (R$ 7,6 mi) e 2 por solução inovadora/CPSI (R$ 3,1 mil). Pelo art. 75, V, da Lei "
    "14.133/2021, há 4 compras enquadradas (R$ 10,3 mi), nem todas com menção explícita ao instrumento.", "PROMPT_PAINEL_V5.md", "item 3.4")
# grafico 5: so a primeira frase (item 3.3)
_tc = sorted(((sum(r2(r["valor_nominal"]) for r in cat if r["categoria"] == c), c) for c in CATS), reverse=True)
_g5 = f"{NOME[_tc[0][1]]} teve o maior valor homologado em 2021 a 2026 ({mi(_tc[0][0])}), seguida de {NOME[_tc[1][1]]} ({mi(_tc[1][0])})."
add("Gráfico 5: texto (só a primeira frase, sem a frase do modo dos valores)", conf.get("g5_txt"), _g5, TP + "pn_categoria_ano.csv", "valor_nominal")
add("Gráfico 5: texto igual ao do Ajuste 4 (item 3.3)", conf.get("g5_txt"),
    "Nuvem teve o maior valor homologado em 2021 a 2026 (R$ 18.622 mi), seguida de Plataformas e licenciamento (R$ 11.830 mi).", "PROMPT_PAINEL_V4.md", "item 3.3")
# alternador: textos abaixo dos graficos com a frase final do modo (e o do grafico 5 sem ela)
for r in alt:
    if r["elemento"].startswith("texto abaixo do gráfico"):
        add(f"Alternador, {r['aba']}, {r['elemento']}, {r['modo']}: frase final do modo dos valores", r["confere"], "sim", "verificacao_html_v5_1/alternador_exemplos.csv",
            "texto_exibido; termina_com_o_modo")
# metodologia: limitacao do pais de origem e achado 4 da IA
pais = next(r for r in ler("tabelas_parte0/p0_preenchimento_pais_origem.csv") if r["recorte"].startswith("seis"))
_lp = f"País de origem do produto ou serviço preenchido em {fmt_pct(f(pais['pct_preenchido']))} dos resultados das seis categorias"
add("METODOLOGIA_v5_1.md, limitações: país de origem preenchido e dependência de tecnologia estrangeira",
    fmt_pct(f(pais["pct_preenchido"])) if _lp in met and "não é possível medir diretamente a dependência de tecnologia estrangeira" in met else "ausente",
    fmt_pct(f(pais["pct_preenchido"])), "tabelas_parte0/p0_preenchimento_pais_origem.csv", "pct_preenchido")
_raiz = len({r["raiz_cnpj"] for r in ir if r["classe"] != "Capacitação"})
add("METODOLOGIA_v5_1.md, achado 4 da IA: fornecedores pelo CNPJ e pela raiz do CNPJ",
    f"{inteiro(len(_vf))}; {inteiro(_raiz)}" if f"{inteiro(len(_vf))} fornecedores, e os 10 maiores" in met and f"a base tem {inteiro(_raiz)} fornecedores" in met else "ausente",
    f"{inteiro(len(_vf))}; {inteiro(_raiz)}", TP + "ia_resultados.csv", "cnpj_fornecedor; raiz_cnpj (sem Capacitação)")
# ---------------- versao 5: textos novos, graficos 1 a 3, Capacitacao, Nuvem com servicos de IA e interacao do grafico 9
_P5 = "PROMPT_PAINEL_V5.md"
for rot, chave, esp_, item in (
        ("Compras públicas: texto da caixa de abertura", "cp_abertura", "Mostra quanto o poder público contratou via PNCP, em que ritmo e por quais modalidades. "
         "O valor corresponde ao total homologado de cada compra, contabilizada uma vez no ano de publicação.", "item 2.2"),
        ("Tecnologias críticas: texto da caixa de abertura", "sd_abertura", "Reúne as compras públicas de tecnologias críticas para a soberania digital, "
         "considerando dados, infraestrutura e tecnologias essenciais ao Estado.", "item 3.1"),
        ("Inteligência artificial: texto da caixa de abertura", "ia_abertura", "Apresenta uma análise específica das compras públicas de Inteligência Artificial, "
         "com classificação dos tipos de solução, fornecedores, marcas mencionadas e modelos de aquisição.", "item 4.1"),
        ("Gráfico 1, modo Valor: texto igual ao do Ajuste 5", "g1_txt", "O valor global homologado somou R$ 952 bi em 2021 a 2026; 2021 e 2022 têm cobertura parcial do PNCP, "
         "e 2026 vai até 24/05 (tom mais claro). Valores nominais.", "item 2.5"),
        ("Gráfico 2: texto igual ao do Ajuste 5", "g2_txt", "A esfera federal respondeu por 50% do valor global homologado em 2021 a 2026 (R$ 472 bi), seguida da estadual (29%). "
         "Valores nominais.", "item 2.6"),
        ("Gráfico 3: texto igual ao do Ajuste 5", "g3_txt", "O Poder Executivo respondeu por 75% do valor global homologado em 2021 a 2026 (R$ 715 bi), seguido do Judiciário (3,6%). "
         "Valores nominais.", "item 2.7")):
    add(rot, conf.get(chave), esp_, _P5, item)
# graficos 1 a 3 recalculados de pn_cubo_compras.csv
_parc = " 2021 e 2022 têm cobertura parcial do PNCP, e 2026 vai até 24/05 (tom mais claro)."
add("Gráfico 1, modo Valor: total do período", conf.get("g1_txt"), f"O valor global homologado somou {bi(HOM)} em 2021 a 2026;{_parc} Valores nominais.", TP + "pn_cubo_compras.csv", "hom_nominal")
add("Gráfico 1, modo Quantidade: total do período", conf.get("g1_txt_qtd"), f"Foram homologadas {inteiro(s(cubo, 'n_homologadas'))} compras em 2021 a 2026;{_parc}",
    TP + "pn_cubo_compras.csv", "n_homologadas")
for chave, dim, v1, v2, art, seg in (("g2_txt", "esfera", "Federal", "Estadual", "A esfera federal", "seguida da estadual"),
                                     ("g3_txt", "poder", "Executivo", "Judiciário", "O Poder Executivo", "seguido do Judiciário")):
    x1, x2 = s(cubo, "hom_nominal", **{dim: v1}), s(cubo, "hom_nominal", **{dim: v2})
    add(f"Gráfico {chave[1]}: texto (recalculado)", conf.get(chave), f"{art} respondeu por {fmt_pct(100 * x1 / HOM)} do valor global homologado em 2021 a 2026 ({bi(x1)}), "
        f"{seg} ({fmt_pct(100 * x2 / HOM)}). Valores nominais.", TP + "pn_cubo_compras.csv", f"hom_nominal; {dim}")
# Capacitacao: tabela de classes x grafico 9
_cr = ler("tabelas_painel_v5/ia_capacitacao_reconciliacao.csv")
_cap_ids = {r["id_compra"] for r in ib if r["classe"] == "Capacitação"}
add("Capacitação: compras e valor na tabela de classes (achado 2)", f"{inteiro(int(_cr[0]['compras']))}; {mi(f(_cr[0]['valor_nominal']))}",
    f"{inteiro(len(_cap_ids))}; {mi(sum(r2(r['valor_nominal']) for r in ipa if r['classe'] == 'Capacitação'))}", TP + "ia_base.csv; " + TP + "ia_base_classes.csv", "classe; valor_nominal")
_rc = [r for r in ir if r["classe"] == "Capacitação"]
_sk = conf.get("ia_skresumo_cap", "")
add("Capacitação: linha-resumo do gráfico 9 (compras com vencedor e valor dos resultados)", _sk,
    f"{inteiro(len({r['id_compra'] for r in _rc}))} compras com vencedor identificado · {inteiro(len({r['cnpj_fornecedor'] for r in _rc}))} fornecedores · "
    f"{inteiro(len({r['orgao'] for r in _rc}))} órgãos · {mi(sum(r2(r['valor_nominal']) for r in _rc))} (valor dos resultados)", TP + "ia_resultados.csv", "classe; valor_nominal")
add("Capacitação: compras do gráfico 9 + compras sem resultado = compras da tabela de classes",
    inteiro(len({r["id_compra"] for r in _rc}) + len(_cap_ids - {r["id_compra"] for r in _rc})), inteiro(len(_cap_ids)), TP + "ia_base.csv; " + TP + "ia_resultados.csv", "id_compra")
add("Capacitação: nenhuma compra de Capacitação fora do tipo Capacitação nem em Outros", str(sum(1 for r in ib if (r["classe"] == "Capacitação") != (r["tipo_objeto"] == "Capacitação"))),
    "0", TP + "ia_base.csv", "classe; tipo_objeto")
# Nuvem com servicos de IA
_nv = ler("tabelas_painel_v5/ia_nuvem_servicos_ia.csv")
_nids = {r["id_compra"] for r in ib if r["tipo_objeto"] == "Nuvem com serviços de IA"}
_nval = mi(sum(r2(r["valor_nominal"]) for r in ipa if r["id_compra"] in _nids))
add("Nuvem com serviços de IA: compras e valor na aba (metodologia e relatório)",
    f"{inteiro(int(_nv[0]['compras']))}; {mi(f(_nv[0]['valor_nominal']))}" if f"São {inteiro(int(_nv[0]['compras']))} compras, com {mi(f(_nv[0]['valor_nominal']))}" in met else "ausente",
    f"{inteiro(len(_nids))}; {_nval}", TP + "ia_base.csv; " + TP + "ia_base_classes.csv", "tipo_objeto; valor_nominal")
_nr = [r for r in ir if r["tipo_objeto"] == "Nuvem com serviços de IA" and r["classe"] != "Capacitação"]
add("Nuvem com serviços de IA: gráfico 9, valor dos resultados (metodologia)",
    (mi(sum(r2(r["valor_nominal"]) for r in _nr)) if f"{inteiro(int(_nv[1]['compras']))} compras com vencedor identificado e {mi(f(_nv[1]['valor_nominal']))}" in met else "ausente"),
    mi(sum(r2(r["valor_nominal"]) for r in _nr)), TP + "ia_resultados.csv", "tipo_objeto; valor_nominal")
add("Nuvem com serviços de IA: nome antigo ausente do gráfico e dos tooltips", str(sum("Nuvem/cloud broker" in k for k in conf)), "0", "verificacao_html_v5_1/conf_painel.json", "chaves")
# grafico 9: interacao com a tabela de cadeias
for r in ler("verificacao_html_v5_1/grafico9_interacao.csv"):
    add(f"Gráfico 9 e tabela de cadeias: {r['acao']}", r["total_na_tabela"], r["total_no_grafico"], "verificacao_html_v5_1/grafico9_interacao.csv",
        "total no gráfico x total da tabela", tg=r["confere"])
# metodologia: dicionario de termos e textos que passaram para o i
add("METODOLOGIA_v5_1.md: seção 'Dicionário de termos por categoria' com conceito, palavras-chave e verificação das seis categorias",
    str(sum(f"{NOME[c]}. Conceito: " in met for c in CATS)) if "### Dicionário de termos por categoria" in met else "ausente", "6", "METODOLOGIA_v5_1.md", "texto")
for r in ler(TP + "pn_precisao_final.csv"):
    esp = f"Verificada por amostragem de {inteiro(r['n_revisadas_na_base'])} compras, com precisão de {fmt_pct(f(r['precisao_pct']))}."
    add(f"METODOLOGIA_v5_1.md, Dicionário de termos: verificação de {NOME[r['categoria']]}", esp if f"Verificação: {esp}" in met else "ausente", esp, TP + "pn_precisao_final.csv",
        "n_revisadas_na_base; precisao_pct")
# ---------------- versao 5.1: reconciliacao da aba de IA com a categoria Inteligencia artificial e grafico 9 igual ao grafico 8
# grafico 8 com a categoria IA, recalculado de pn_fluxo_compras.csv (compras, fornecedores, orgaos) e pn_fluxo.csv (valor); grafico 9 de ia_resultados.csv
_fc8 = [r for r in fc if r["categoria"] == "ia"]
_v8 = sum(r2(r["valor_nominal"]) for r in flux if r["categoria"] == "ia")
_g9 = [r for r in ir if r["classe"] != "Capacitação"]
_n = lambda rows, k: len({r[k] for r in rows})
_rec = ler("tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv")
_t8 = (_n(_fc8, "id_compra"), _n(_fc8, "cnpj_fornecedor"), _n(_fc8, "orgao"), mi(_v8))
_t9 = (_n(_g9, "id_compra"), _n(_g9, "cnpj_fornecedor"), _n(_g9, "orgao"), mi(sum(r2(r["valor_nominal"]) for r in _g9)))
_fmt = lambda t: f"{inteiro(t[0])} / {inteiro(t[1])} / {inteiro(t[2])} / {t[3]}"
_lin = lambda r: f"{inteiro(abs(int(r['compras'])))} / {inteiro(abs(int(r['fornecedores'])))} / {inteiro(abs(int(r['orgaos'])))} / {mi(abs(float(r['valor_nominal'])))}"
add("Reconciliação: gráfico 8 com a categoria Inteligência artificial (compras / fornecedores / órgãos / valor)", _lin(_rec[0]), _fmt(_t8),
    TP + "pn_fluxo_compras.csv; " + TP + "pn_fluxo.csv", "categoria ia: id_compra; cnpj_fornecedor; orgao; valor_nominal")
add("Reconciliação: gráfico 9, Todas (tecnologia) (compras / fornecedores / órgãos / valor)", _lin(_rec[3]), _fmt(_t9), TP + "ia_resultados.csv",
    "classe sem Capacitação: id_compra; cnpj_fornecedor; orgao; valor_nominal")
_r8 = conf.get("g9_resumo_ia", "")
add("Reconciliação: linha-resumo do gráfico 8 com a categoria IA igual à tabela de reconciliação", _r8,
    f"{inteiro(_t8[0])} compras com vencedor identificado · {inteiro(_t8[1])} fornecedores · {inteiro(_t8[2])} órgãos · {_t8[3]} (valor dos resultados, soma por categoria)",
    "tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv", "linha 1", tg="sim" if _r8.startswith(f"{inteiro(_t8[0])} compras") and _t8[3] in _r8 else "não")
_r9 = conf.get("ia_skresumo_tec", "")
add("Reconciliação: linha-resumo do gráfico 9 (Todas) igual à tabela de reconciliação", _r9,
    f"{inteiro(_t9[0])} compras com vencedor identificado · {inteiro(_t9[1])} fornecedores · {inteiro(_t9[2])} órgãos · {_t9[3]} (valor dos resultados)",
    "tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv", "linha 4", tg="sim" if _r9.startswith(f"{inteiro(_t9[0])} compras") and _t9[3] in _r9 else "não")
_s8, _s9 = {r["id_compra"] for r in _fc8}, {r["id_compra"] for r in _g9}
_ibd = {r["id_compra"]: r for r in ib}
_sai, _ent = _s8 - _s9, _s9 - _s8
add("Reconciliação: compras que saem (capacitação na categoria IA)", inteiro(abs(int(_rec[1]["compras"]))),
    inteiro(sum(1 for i in _sai if _ibd[i]["classe"] == "Capacitação")), TP + "ia_base.csv", "classe")
add("Reconciliação: compras que entram (acréscimo de IA a licenças de outras categorias, componente C)", inteiro(int(_rec[2]["compras"])),
    inteiro(sum(1 for i in _ent if _ibd[i]["componente"] == "C")), TP + "ia_base.csv", "componente")
add("Reconciliação: 738 − 16 + 54 = 776 (compras), 537 − 10 + 14 = 541 (fornecedores), 411 − 6 + 24 = 429 (órgãos)",
    " | ".join(inteiro(int(_rec[0][k]) + int(_rec[1][k]) + int(_rec[2][k])) for k in ("compras", "fornecedores", "orgaos")),
    " | ".join(inteiro(x) for x in _t9[:3]), "tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv", "linhas 1 a 4")
add("Reconciliação: valor R$ 1.112 mi − R$ 2 mi + R$ 171 mi = R$ 1.281 mi", mi(sum(float(_rec[k]["valor_nominal"]) for k in range(3))), _t9[3],
    "tabelas_painel_v5_1/ia_reconciliacao_grafico8_grafico9.csv", "valor_nominal")
_p = (f"o gráfico 8, com a categoria Inteligência artificial, tem {inteiro(_t8[0])} compras, {inteiro(_t8[1])} fornecedores, {inteiro(_t8[2])} órgãos e {_t8[3]}",
      f"O resultado é o gráfico 9, com o botão Todas (tecnologia): {inteiro(_t9[0])} compras, {inteiro(_t9[1])} fornecedores, {inteiro(_t9[2])} órgãos e {_t9[3]}")
add("METODOLOGIA_v5_1.md: reconciliação com os totais dos dois gráficos", "sim" if all(x in met for x in _p) else "ausente", "sim", "METODOLOGIA_v5_1.md", "texto")
for r in ler("verificacao_html_v5_1/grafico9_igual_grafico8.csv"):
    add(f"Gráfico 9 igual ao gráfico 8: {r['aspecto']}", r["grafico_9"], r["grafico_8"], "verificacao_html_v5_1/grafico9_igual_grafico8.csv", "comparação lado a lado", tg=r["igual"])
with open("conferencia_numeros_v5_1.csv", "w", encoding="utf-8-sig", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["texto_exibido", "valor_exibido", "arquivo_de_origem", "coluna", "valor_calculado", "confere", "texto_e_grafico"])
    w.writerows(L)
nao = [l for l in L if l[5] != "sim" or l[6] == "não"]
for l in nao:
    print("DIFERENTE", l)
print(f"{len(L)} linhas; {len(L) - len(nao)} iguais; {len(nao)} diferentes")
sys.exit(1 if nao else 0)
