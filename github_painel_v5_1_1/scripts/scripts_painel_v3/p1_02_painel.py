"""Painel, etapa 2: gera o painel HTML autocontido, a metodologia e o pacote de downloads.

Executar a partir de Processado/, depois de p1_00 e p1_01:  python scripts_painel_v3/p1_02_painel.py
Entradas: tabelas_painel_v3/*.csv (p1_00, p1_01), tabelas_parte0/*.csv e validacao/*.csv (verificacao e limpeza da base),
  dicionario_termos.csv, bibliotecas locais chart.umd.min.js, d3.min.js e d3-sankey.min.js, modelo
  scripts_painel_v3/painel_modelo.html; contagens lidas dos Parquet (sem copia-los).
Regras: todo numero exibido sai destas tabelas; formatacao numerica unica (funcoes fmt_*), identica a do JavaScript
  do painel (ver METODOLOGIA_v3.md, secao Formatacao). Os textos do icone "i" usam o recorte padrao (2021 a 2026, sem filtros).
Saidas: painel_soberania_digital_v3.html, METODOLOGIA_v3.md, pacote_downloads_v3.zip,
  tabelas_painel_v3/pn_precisao_final.csv, tabelas_painel_v3/pn_textos_i.csv, tabelas_painel_v3/pn_trilha_numeros.csv
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
from decimal import Decimal, ROUND_HALF_UP

import duckdb

sys.stdout.reconfigure(encoding="utf-8")
TP, T0, V = "tabelas_painel_v3/", "tabelas_parte0/", "validacao/"
HOJE = datetime.date.today()
ANOS = [2021, 2022, 2023, 2024, 2025, 2026]
CATS = ["ia", "nuvem", "plataformas", "identidade", "data_center", "seguranca"]
NOME = {"ia": "Inteligência artificial", "nuvem": "Nuvem", "plataformas": "Plataformas e licenciamento",
        "identidade": "Identidade e infraestrutura pública digital", "data_center": "Data center",
        "seguranca": "Segurança cibernética"}
COR = {"ia": "#2864AE", "nuvem": "#46AD44", "plataformas": "#FABD10", "identidade": "#1B4A82",
       "data_center": "#7FA7D6", "seguranca": "#E08A00"}
CAMADA = {"ia": "Inteligência artificial", "nuvem": "Nuvem", "plataformas": "Software de plataforma",
          "identidade": "Aplicações de governo", "data_center": "Infraestrutura física", "seguranca": "Transversal"}
# referencia de cada categoria (Recomendacao (UE) 2023/2113, anexo; EuroStack, camadas)
REFERENCIA = {
    "nuvem": "Recomendação (UE) 2023/2113, domínio 2 (computação em nuvem e periférica); EuroStack, camada de infraestrutura de nuvem.",
    "plataformas": "EuroStack, camada de plataformas de software (sistemas operacionais e aplicações).",
    "data_center": "Recomendação (UE) 2023/2113, domínio 2 (computação de alto desempenho); EuroStack, camada de infraestrutura de nuvem (armazenamento e processamento).",
    "seguranca": "Recomendação (UE) 2023/2113, domínio 5 (tecnologias de cibersegurança); EuroStack, camada de plataformas de software.",
    "ia": "Recomendação (UE) 2023/2113, domínio 2 (tecnologias de inteligência artificial); EuroStack, camada de dados e inteligência artificial.",
    "identidade": "Recomendação (UE) 2023/2113, domínio 5 (tecnologias de identidade digital); EuroStack, componente de identidade digital.",
}
DESCR = {"ia": "Sistemas que automatizam análise, decisão ou atendimento",
         "nuvem": "Capacidade de processamento e armazenamento contratada como serviço",
         "plataformas": "Software básico de que os sistemas do governo dependem",
         "identidade": "Meios de identificar cidadãos e validar documentos",
         "data_center": "Infraestrutura física de processamento e armazenamento",
         "seguranca": "Proteção de redes, dados e sistemas"}
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro"]
DATA_COLETA = "28/09/2026"


# ------------------------------------------------------------------ formatacao (identica ao JavaScript do painel)
sys.path.insert(0, "scripts_painel_v3")
from painel_compras_publicas_colibri.github_painel_v5_1_1.scripts.scripts_painel_v3.formatacao import _dec, fmt_num, fmt_escala, fmt_pct, bi, mi, mi1, reais, inteiro, vauto  # noqa: E402


# ------------------------------------------------------------------ leitura
def ler(caminho):
    with open(caminho, encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter=";"))


def f(x):
    return float(x) if x not in (None, "") else 0.0


cubo = ler(TP + "pn_cubo_compras.csv")
sob_ano = {int(r["ano"]): r for r in ler(TP + "pn_soberania_ano.csv")}
cat_ano = ler(TP + "pn_categoria_ano.csv")
tres = ler(TP + "pn_soberania_tres_regras.csv")[0]
modal = ler(TP + "pn_modalidade_soberania.csv")
forma = ler(TP + "pn_forma_contratacao.csv")
fluxo = ler(TP + "pn_fluxo.csv")
fluxo_c = ler(TP + "pn_fluxo_compras.csv")  # p1_01b: compras de cada fluxo
cad = ler(TP + "pn_cadeias_compras.csv")  # p1_01d: tabela 2 (cadeias fornecedor -> objeto -> orgao)
cad_obj = {r["id_compra"]: r["objeto"] for r in ler(TP + "pn_cadeias_objetos.csv")}
cad_raiz = {r["raiz_cnpj"]: r for r in ler(TP + "pn_fornecedor_raiz.csv")}
# modelo de aquisicao, tipo de vendedor, marcas, porte e achados (p1_01c, a partir da classificacao em fase2/)
f2_modelo, f2_vend, f2_marca = ler(TP + "pn_modelo_categoria_ano.csv"), ler(TP + "pn_vendedor_categoria_ano.csv"), ler(TP + "pn_marca_resultados.csv")
f2_porte_c, f2_porte_v, f2_achados = ler(TP + "pn_porte_compras.csv"), ler(TP + "pn_porte_valor.csv"), ler(TP + "pn_achados.csv")
f2_estatais = ler(TP + "pn_estatais_vencedoras.csv")
F2 = "fase2/"
f2_sit = ler(F2 + "tabelas/f2_06_situacao_classes.csv")
f2_prec = ler(F2 + "tabelas/f2_06_precisao_modelo.csv")
f2_dic = ler(F2 + "dicionario_modelo_aquisicao.csv")
f2_dicm = ler(F2 + "dicionario_marcas.csv")
f2_fab = ler(F2 + "fabricantes_cnpj.csv")
f2_jm = ler(F2 + "validacao/julgamentos_marcas_f2_marca_a1.csv")
_pfreq = ler(F2 + "tabelas/f2_10_porte_frequencia_base.csv")
_lpc = ler(TP + "pn_direitos_permanentes_codigo.csv")[0]
_an = {(r["achado"], r["indicador"]): r["valor_exibido"] for r in ler(TP + "pn_achados_numeros.csv")}
f2_comp = ler(TP + "pn_modelo_grupo_componentes.csv")  # suporte e manutencao de licenca e compras sem itens com valor (grupo do grafico 9)
f2_conc = ler(F2 + "validacao/concordancia_entre_revisoes.csv")
_pf = {r["porte_fornecedor_nome"]: f(r["pct_dos_resultados"]) for r in _pfreq}
f2_m4 = sum(f(r["valor_homologado_nominal"]) for r in ler(F2 + "tabelas/f2_07_modelo_categoria.csv") if r["ordem"] == "4")
conc = ler(TP + "pn_concentracao.csv")
perfil = ler(TP + "pn_perfil.csv")
perfil_vals = ler(TP + "pn_perfil_valores_por_compra.csv")
perfil_bens = ler(TP + "pn_perfil_bens.csv")
orgaos = ler(TP + "pn_orgaos.csv")
instr = ler(TP + "pn_instrumentos.csv")
preench = ler(TP + "pn_instrumentos_preenchimento.csv")
ncm = ler(TP + "pn_margem_ncm.csv")
encom = ler(TP + "pn_encomenda_cpsi.csv")
ipca_base = ler(TP + "pn_ipca_base.csv")[0]
controles_pn = ler(TP + "pn_controles.csv")
dic_leg = ler(TP + "dicionario_termos_legivel.csv")
pais = ler(T0 + "p0_preenchimento_pais_origem.csv")
robustez = ler(T0 + "p0_robustez_categorias.csv")
exclusoes = ler(T0 + "p0_exclusoes_por_motivo_ano.csv")
tot_completa = ler(T0 + "p0_totais_homologados_ano_base_completa.csv")
tot_ano = {int(r["ano"]): r for r in ler(T0 + "p0_totais_homologados_ano.csv")}
controles_p0 = ler(T0 + "p0_controles_base_limpa.csv")
dup_rem = ler(T0 + "duplicidades_removidas.csv")
dup_lit = ler(T0 + "duplicidades_regra_literal_cinco_campos.csv")
dup_proc = ler(T0 + "possiveis_duplicidades_processo_diferente.csv")
mg_decomp = ler(T0 + "margem_aplicada_decomposicao.csv")
mg_causa = ler(T0 + "margem_aplicada_fora_elegibilidade_causa.csv")
rem_taxa = ler(V + "remocao_indevida_por_categoria.csv")
prec_p0 = {r["categoria"]: r for r in ler(V + "precisao_por_categoria.csv")}
dup_ids = {r["id_compra"] for r in ler(T0 + "duplicidades_ids_removidos.csv")}

con = duckdb.connect()
n_extr, n_itens_extr, n_res_extr, n_base_limpa, n_itens_dedup, n_res_dedup = con.execute("""SELECT
    (SELECT count(*) FROM '../parquet/compras.parquet'), (SELECT count(*) FROM '../parquet/itens.parquet'),
    (SELECT count(*) FROM '../parquet/resultados.parquet'), (SELECT count(*) FROM 'base_limpa.parquet'),
    (SELECT count(*) FROM 'itens_dedup.parquet'), (SELECT count(*) FROM 'resultados_dedup.parquet')""").fetchone()
con.close()
con = duckdb.connect("scripts_parte0/p0.duckdb", read_only=True)
dmin, dmax = con.execute("SELECT min(data_pub), max(data_pub) FROM bl").fetchone()
n_rem_pares = dict(con.execute("SELECT segmento, count(*) FROM rem_pares GROUP BY 1").fetchall())
n_audit = con.execute("""SELECT count(*) FILTER (WHERE validacao_csv = 'erro_provavel'), count(*) FILTER (WHERE validacao_csv IS NOT NULL)
    FROM bs_dedup""").fetchone()
con.close()

# ------------------------------------------------------------------ precisao final (sem as compras removidas como republicacao)
precisao = {}
for c in CATS:
    am = prec_p0[c]["amostra_final"]
    js = [r for r in ler(V + f"{am}_julgamentos.csv") if r["segmento"] == c and r["id_compra"] not in dup_ids]
    n, p = len(js), sum(r["classificacao_manual"] == "pertinente" for r in js)
    precisao[c] = {"amostra": am, "n": n, "pertinentes": p, "pct": 100.0 * p / n,
                   "historico": prec_p0[c]["historico"], "ajustado": prec_p0[c]["dicionario_ajustado"]}
with open(TP + "pn_precisao_final.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["categoria", "amostra_final", "n_revisadas_na_base", "n_pertinentes", "precisao_pct", "dicionario_ajustado"])
    for c in CATS:
        w.writerow([c, precisao[c]["amostra"], precisao[c]["n"], precisao[c]["pertinentes"],
                    precisao[c]["pct"], precisao[c]["ajustado"]])

# ------------------------------------------------------------------ agregados do recorte padrao
def soma(rows, campo, **filtros):
    return sum(f(r[campo]) for r in rows if all(str(r[k]) == str(v) for k, v in filtros.items()))


N_PUB = sum(int(r["n_publicadas"]) for r in cubo)
N_HOM = sum(int(r["n_homologadas"]) for r in cubo)
N_SEM = sum(int(r["n_sem_homologacao"]) for r in cubo)
N_EXC = sum(int(r["n_valor_excluido"]) for r in cubo)
HOM = soma(cubo, "hom_nominal")
HOM_D = soma(cubo, "hom_deflacionado")
BRUTO = soma(cubo, "hom_bruto")
V2A, V2B, V2C = f(tres["regra_2a"]), f(tres["regra_2b"]), f(tres["regra_2c"])
V2A_D = sum(f(r["soberania_2a_deflacionado"]) for r in sob_ano.values())
N_SOB = int(tres["n_compras_seis_categorias"])
PART = 100 * V2A / HOM
ano_pub = {a: soma(cubo, "n_publicadas", ano=a) for a in ANOS}
ano_hom = {a: soma(cubo, "hom_nominal", ano=a) for a in ANOS}
ano_nhom = {a: soma(cubo, "n_homologadas", ano=a) for a in ANOS}
mes_base = int(ipca_base["mes_base"])
MES_BASE_TXT = f"{MESES[mes_base % 100 - 1]} de {mes_base // 100}"
MES_BASE_CURTO = f"{MESES[mes_base % 100 - 1]}/{mes_base // 100}"
pais6 = next(r for r in pais if r["recorte"].startswith("seis categorias"))
PAIS_PCT = f(pais6["pct_preenchido"])
cat_tot = {c: soma(cat_ano, "valor_nominal", categoria=c) for c in CATS}
# ordem das categorias em todo o painel: valor homologado de 2021 a 2026 pela regra de soma por categoria
CATS = sorted(CATS, key=lambda c: -cat_tot[c])
cat_2c = {c: soma(cat_ano, "valor_compra_inteira_nominal", categoria=c) for c in CATS}


def share_dim(dim, valor, ano):
    return 100 * soma(cubo, "hom_nominal", ano=ano, **{dim: valor}) / soma(cubo, "hom_nominal", ano=ano)


ncm_tot = {k: soma(ncm, k, recorte="todas") for k in ("ncm_item_nominal", "ncm_item_tradutor_nominal",
                                                       "margem_aplicada_material_nominal", "valor_itens_material_nominal")}
instr_tot = {k: soma(instr, k, recorte="todas") for k in ("valor_nominal", "margem_prevista_nominal",
                                                           "margem_aplicada_nominal", "ppb_nominal")}
# maior fluxo fornecedor x categoria no periodo e principal orgao
agg = {}
for r in fluxo:
    k = (r["cnpj_fornecedor"], r["fornecedor"], r["categoria"])
    agg[k] = agg.get(k, 0) + f(r["valor_nominal"])
kmax = max(agg, key=agg.get)
org_k = {}
for r in fluxo:
    if (r["cnpj_fornecedor"], r["fornecedor"], r["categoria"]) == kmax:
        org_k[r["orgao"]] = org_k.get(r["orgao"], 0) + f(r["valor_nominal"])
org_max = max(org_k, key=org_k.get)
forma_obj = {c: 100 * soma(forma, "valor_nominal", categoria=c, forma="Objeto próprio") / soma(forma, "valor_nominal", categoria=c)
             for c in CATS}
cat_maior = max(CATS, key=lambda c: cat_tot[c])
cat_2025 = max(CATS, key=lambda c: soma(cat_ano, "valor_nominal", categoria=c, ano=2025))
inex_sob = 100 * soma(modal, "valor_nominal", recorte="todas", modalidade="Inexigibilidade") / soma(modal, "valor_nominal", recorte="todas")
inex_tot = 100 * soma(cubo, "hom_nominal", modalidade="Inexigibilidade") / HOM
srp_cat = {}
for c in CATS:
    num = sum(f(p["pct_srp_nominal"]) / 100 * soma(cat_ano, "valor_nominal", categoria=c, ano=p["ano"])
              for p in perfil if p["categoria"] == c)
    srp_cat[c] = 100 * num / cat_tot[c]
cat_srp = max(CATS, key=lambda c: srp_cat[c])

# exemplo do "i" da tabela 2: categoria mais e menos concentrada em 2025 (maior e menor HHI)
c25 = [r for r in conc if r["ano"] == "2025"]
cmax, cmin = max(c25, key=lambda r: f(r["hhi_nominal"])), min(c25, key=lambda r: f(r["hhi_nominal"]))
EX_T2 = (f"em 2025, em {NOME[cmax['categoria']]}, os quatro maiores fornecedores concentraram {fmt_pct(f(cmax['cr4_nominal']))} do valor homologado (CR4) "
         f"e o HHI foi {fmt_num(f(cmax['hhi_nominal']), 3)}; em {NOME[cmin['categoria']]}, CR4 de {fmt_pct(f(cmin['cr4_nominal']))} e HHI de "
         f"{fmt_num(f(cmin['hhi_nominal']), 3)}, o que indica compras menos concentradas.")
# exemplo do "i" da tabela 1: maior orgao da categoria de maior valor, na base dos resultados
_org = {}
for r in fluxo:
    if r["categoria"] == CATS[0]:
        _org[r["orgao"]] = _org.get(r["orgao"], 0) + round(f(r["valor_nominal"]), 2)
_om = max(_org, key=_org.get)
EX_T1 = f"em {NOME[CATS[0]]}, o maior comprador de 2021 a 2026 foi {_om}, com {mi(_org[_om])} ({fmt_pct(100 * _org[_om] / sum(_org.values()))} da categoria)."

# fornecedores vencedores e orgaos compradores: mesma base e mesma regra do grafico 9 (pn_fluxo; CNPJ do vencedor e orgao)
N_FORN = len({r["cnpj_fornecedor"] for r in fluxo})
N_ORG = len({r["orgao"] for r in fluxo})
assert N_FORN == len({(r["cnpj_fornecedor"], r["fornecedor"]) for r in fluxo})  # um nome por CNPJ, como no Sankey
assert (N_FORN, N_ORG) == (len({r["cnpj_fornecedor"] for r in fluxo_c}), len({r["orgao"] for r in fluxo_c}))
NF_CAT0 = len({r["cnpj_fornecedor"] for r in fluxo if r["categoria"] == CATS[0]})
NO_CAT0 = len({r["orgao"] for r in fluxo if r["categoria"] == CATS[0]})
V_SANKEY = sum(round(f(r["valor_nominal"]), 2) for r in fluxo)  # total do diagrama no recorte padrao (soma por categoria)
assert V_SANKEY > V2A

# ------------------------------------------------------------------ textos do "i" (recorte padrao)
DEF_HOM = ("soma dos valores dos itens adjudicados aos fornecedores vencedores ao final da licitação ou da contratação direta, "
           "conforme registrado no PNCP. Não equivale ao valor contratado nem ao valor efetivamente pago.")
# KPIs de valor: a definicao do valor global homologado e a primeira linha do "i"
USA_HOM = ["sobre_valor", "cp_valor", "sd_valor"]  # a definicao fica so nos KPIs de valor e na metodologia
I = {
    "sobre_compras": {"como": "Número de compras vigentes publicadas no PNCP no período, conforme a base ComprasGov do Colibri, cada uma contada uma única vez.",
                      "nota": f"Foram identificadas {inteiro(N_PUB)} compras, correspondentes a {fmt_pct(100 * N_PUB / n_extr)} das {inteiro(n_extr)} compras extraídas do Colibri. Dessas, {inteiro(N_HOM)} têm valor homologado válido; a diferença corresponde a {inteiro(N_SEM)} compras sem homologação registrada e {inteiro(N_EXC)} com o valor excluído pela auditoria de erros de preenchimento, que continuam contadas como compras publicadas."},
    "sobre_valor": {"como": "Soma dos valores homologados das compras, em valores nominais, após a exclusão de registros com erros de preenchimento.",
                    "nota": f"O valor bruto extraído foi de {bi(BRUTO)}. Após a revisão e limpeza dos dados, foram considerados {bi(HOM)}. A diferença decorre, principalmente, da identificação e exclusão de valores com inconsistências de preenchimento."},
    "sobre_soberania": {"como": "Total das seis categorias: valor das compras de tecnologias críticas para a soberania digital, em que cada compra entra uma única vez.",
                        "nota": f"A classificação considera a correspondência dos termos definidos para as categorias no objeto da contratação e nos respectivos itens. Nos gráficos por categoria vale a soma por categoria ({bi(V2B)}): uma compra classificada em duas categorias aparece nas duas, por isso a soma supera o total das seis categorias."},
    "sobre_participacao": {"como": "Participação do valor homologado das compras de tecnologias críticas para a soberania digital no valor homologado de todas as compras analisadas entre 2021 e 2026.",
                           "exemplo": f"a cada R$ 100 homologados em compras públicas, aproximadamente {reais(PART)} correspondem às seis categorias."},
    "cp_compras": {"como": "Total de compras publicadas no PNCP entre 2021 e 2026, conforme a base ComprasGov do Colibri, cada uma contada uma única vez.",
                   "nota": f"Das {inteiro(N_PUB)} compras publicadas, {inteiro(N_HOM)} têm valor homologado válido; as outras {inteiro(N_SEM)} não têm homologação registrada e {inteiro(N_EXC)} tiveram o valor excluído pela auditoria. Por isso o gráfico de quantidade, que conta só compras com valor homologado válido, soma menos que este indicador.",
                   "exemplo": f"Em 2024 e 2025, o setor público registrou cerca de {inteiro(round((ano_pub[2024] + ano_pub[2025]) / 2 / 1000))} mil compras por ano."},
    "cp_valor": {"como": "Soma do valor global homologado de todas as compras do período, após a exclusão de registros com erro de preenchimento.",
                 "exemplo": f"De cada R$ 100 homologados no período, {reais(100 * (ano_hom[2024] + ano_hom[2025]) / HOM, 0)} concentram-se em 2024 e 2025."},
    "g1_valor": {"como": "Soma do valor global homologado das compras publicadas em cada ano, após a exclusão de registros com erro de preenchimento.",
                 "exemplo": f"em 2025, o valor global homologado foi de {bi(ano_hom[2025])}."},
    "g1_qtd": {"como": f"Número de compras com valor homologado válido, por ano de publicação; {inteiro(N_SEM)} compras publicadas no período não têm homologação registrada e não entram nesta contagem, nem as {inteiro(N_EXC)} cujo valor foi excluído pela auditoria.",
               "exemplo": f"em 2025, foram homologadas {inteiro(ano_nhom[2025])} compras."},
    "g2": {"como": "Soma do valor global homologado segundo a esfera do órgão comprador registrada no PNCP; o percentual é a participação no total do período.",
           "exemplo": f"em 2025, a esfera federal respondeu por {fmt_pct(share_dim('esfera', 'Federal', 2025))} do valor global homologado."},
    "g3": {"como": "Soma do valor global homologado segundo o poder do órgão comprador registrado no PNCP; o percentual é a participação no total do período.",
           "exemplo": f"em 2025, o Poder Executivo respondeu por {fmt_pct(share_dim('poder', 'Executivo', 2025))} do valor global homologado."},
    "g4": {"como": "Soma do valor global homologado segundo a modalidade registrada no PNCP. Dispensa e inexigibilidade são contratações diretas, sem disputa entre fornecedores (Lei 14.133/2021, arts. 72 a 75).",
           "exemplo": f"em 2025, o pregão eletrônico respondeu por {fmt_pct(share_dim('modalidade', 'Pregão eletrônico', 2025))} do valor global homologado."},
    "sd_valor": {"como": "Total das seis categorias: soma do valor das compras classificadas em ao menos uma das seis categorias de tecnologias críticas para a soberania digital, em que cada compra entra uma única vez: valor integral quando o termo está no objeto; apenas os itens correspondentes quando o termo aparece só nos itens.",
                 "exemplo": f"dos {bi(HOM)} homologados no período, {bi(V2A)} referem-se às seis categorias."},
    "sd_part": {"como": "Valor do indicador anterior dividido pelo valor global homologado de todas as compras do período.",
                "exemplo": f"a cada R$ 100 homologados, cerca de {reais(PART)} foram destinados às tecnologias críticas para a soberania digital."},
    "g5": {"como": f"Cada barra soma o valor das compras da categoria no ano. Uma compra classificada em duas categorias aparece nas duas; por isso a soma das barras supera o total das seis categorias ({bi(V2A)}), em que cada compra entra uma vez.",
           "exemplo": f"em 2025, {NOME[cat_2025]} somou {mi(soma(cat_ano, 'valor_nominal', categoria=cat_2025, ano=2025))}."},
    "g6": {"como": "Total das seis categorias (cada compra entra uma vez) dividido pelo valor global homologado de todas as compras do ano.",
           "exemplo": f"em 2025, {fmt_pct(100 * f(sob_ano[2025]['soberania_2a_nominal']) / f(sob_ano[2025]['homologado_total_nominal']))} do valor global homologado correspondeu às seis categorias."},
    "g7": {"como": "Participação de cada modalidade no valor homologado, calculada separadamente para as tecnologias críticas para a soberania digital e para o conjunto das compras; inexigibilidade indica inviabilidade de competição, como fornecedor exclusivo (Lei 14.133/2021, art. 74).",
           "exemplo": f"nas tecnologias críticas, a inexigibilidade respondeu por {fmt_pct(inex_sob)} do valor, ante {fmt_pct(inex_tot)} no total das compras."},
    "g8": {"como": "Objeto próprio quando o termo aparece no objeto da compra ou quando os itens da categoria representam mais da metade do valor da compra; nos demais casos, a tecnologia é item de uma contratação mais ampla. Cada barra usa a soma por categoria. Uma compra classificada em duas categorias aparece nas duas; por isso a soma das barras supera o total das seis categorias (" + bi(V2A) + "), em que cada compra entra uma vez.",
           "exemplo": f"em {NOME[cat_maior]}, {fmt_pct(forma_obj[cat_maior])} do valor foi contratado como objeto próprio."},
    "ia_resumo": {"como": "Tecnologia de IA: compras das classes Acréscimo à licença, Solução de IA (exclusiva ou em pacote) e Outros. Capacitação em IA: cursos, treinamentos, inscrições, pós-graduação e eventos sobre IA; a capacitação não faz parte do total das tecnologias críticas para a soberania digital. Compras: cada compra uma vez, na classe de maior valor. Fornecedores e órgãos: compras com vencedor identificado. Valor: valor homologado de cada compra, repartido entre as classes pelos itens (a mesma regra do gráfico 9).",
                  "nota": ""},
    "ia_sankey": {"como": "A espessura de cada fluxo é o valor homologado nos resultados (sub-aba Valor) ou o número de compras (sub-aba Nº de compras). Quem vendeu: CNPJ do vencedor, que pode ser revendedor. O que vendeu: tipo de objeto da compra, por palavras-chave (marcas de IA sempre com nome próprio; tipo com menos de 3 compras vai para 'Outras soluções de IA'). Quem comprou: órgão comprador. Os 10 maiores de cada lado são definidos pelo valor, nos dois modos; no modo Nº de compras, a compra é contada uma vez para cada fornecedor e uma vez para cada órgão.",
                  "nota": "O valor dos resultados é a soma dos itens adjudicados aos vencedores das compras com vencedor identificado; por isso o total do diagrama difere do valor homologado da linha-resumo, que inclui compras sem resultado publicado."},
    "ia_cadeias": {"como": "Cada linha é uma cadeia: fornecedor (raiz do CNPJ do vencedor), objeto e órgão comprador, numa classe, na base dos resultados do gráfico 12. O objeto é o da compra de maior valor da cadeia, como registrado no PNCP; 'e mais N' indica as demais compras. O porte é o registrado no PNCP para o fornecedor. % da classe = valor da linha ÷ valor dos resultados da classe no recorte. A tabela acompanha o filtro e a seleção feita no gráfico 12; até 50 linhas por classe."},
    "ia_marcas": {"como": "Compras que citam a marca no texto do item, no objeto ou na informação complementar, de 2021 a 2026, sem corte mínimo. Compras de produto e de capacitação aparecem separadas. Valor: valor homologado da compra quando a marca está no objeto ou na informação complementar; senão, valor dos resultados dos itens que citam a marca. Principais vendedores: CNPJ dos vencedores das compras de produto.",
                  "nota": "A busca cobre toda a base do painel, e não só a base da aba de IA; por isso o número de compras de uma marca pode ser maior que o do tipo de objeto no gráfico 12. A menção à marca não comprova o produto entregue."},
    "g9": {"como": "A espessura de cada fluxo é o valor homologado nos resultados (sub-aba Valor) ou o número de compras (sub-aba Nº de compras); o fornecedor é o CNPJ vencedor da contratação, que pode ser revendedor, e não o fabricante da tecnologia. Os 10 maiores de cada lado são definidos pelo valor, nos dois modos. No modo Nº de compras, a compra é contada uma vez para cada fornecedor e uma vez para cada órgão; por isso os lados somam mais que o total de compras distintas mostrado no resumo.",
           "nota": f"O valor do diagrama é a soma do valor homologado nos resultados de cada categoria. Uma compra classificada em mais de uma categoria aparece em cada uma delas; por isso o total do diagrama ({mi(V_SANKEY)}) é maior que o total das seis categorias ({bi(V2A)}), em que cada compra entra uma vez.",
           "exemplo": f"{kmax[1]} recebeu {mi(agg[kmax])} em {NOME[kmax[2]]}, principalmente de {org_max}."},
    "t2": {"como": "Os indicadores medem a concentração do valor homologado entre os fornecedores contratados pelo setor público, não a concentração do mercado como um todo. CR4 é a participação dos quatro maiores fornecedores no valor da categoria. O HHI (índice de Herfindahl-Hirschman) soma os quadrados das participações de todos os fornecedores e varia de 0 a 1: quanto mais próximo de 1, mais concentradas as compras. Os fornecedores são identificados pelo CNPJ do vencedor, que pode ser revendedor da tecnologia, e não o fabricante.",
           "nota": "sᵢ = valor homologado do fornecedor i ÷ valor homologado total da categoria no ano; CR4 = (s₁ + s₂ + s₃ + s₄) × 100, com os quatro maiores sᵢ; HHI = Σ sᵢ².",
           "exemplo": EX_T2},
    "t3": {"como": "A mediana indica o porte típico de uma compra; a participação do registro de preços indica quanto do valor é teto de ata, e não gasto; a participação de bens indica quanto do valor é de materiais, alcançáveis por instrumentos ligados à NCM, como PPB e margem de preferência.",
           "exemplo": f"em {NOME[cat_srp]}, {fmt_pct(srp_cat[cat_srp])} do valor homologado veio de atas de registro de preços."},
    "t1": {"como": "Cada linha é uma cadeia: fornecedor (raiz do CNPJ do vencedor, que pode ser revendedor), objeto e órgão comprador, numa categoria, na base dos resultados do gráfico 11. "
                   "O objeto é o da compra de maior valor da cadeia, como registrado no PNCP; 'e mais N' indica as demais compras. O porte é o registrado no PNCP para o fornecedor. "
                   "% da categoria = valor da linha ÷ valor dos resultados da categoria no recorte. A tabela acompanha a seleção feita no gráfico 11 (categoria, fornecedor ou órgão); até 50 linhas por categoria.",
           "exemplo": EX_T1},
    "g10ncm": {"como": "Soma do valor homologado dos itens de material cujo NCM está coberto por resolução CICS de margem de preferência vigente na data da compra. O indicador cobre apenas itens de material, porque a margem é definida por NCM. O valor principal usa só o NCM informado no item; o limite superior completa os itens sem NCM com o tradutor CATMAT→NCM do Colibri, parte dele gerado por IA.",
               "exemplo": f"nas tecnologias críticas para a soberania digital, {mi1(ncm_tot['ncm_item_nominal'])} em itens de material estavam cobertos por margem de preferência, mas só {mi1(ncm_tot['margem_aplicada_material_nominal'])} tiveram a margem efetivamente aplicada."},
    "sd_forn": {"como": "Número de fornecedores distintos que venceram ao menos um resultado com valor homologado positivo nas compras de tecnologias críticas para a soberania digital do recorte. O fornecedor é identificado pelo CNPJ do vencedor, a mesma regra do gráfico 11 e das tabelas 2 e 3, e é contado uma única vez, ainda que tenha vencido em mais de uma categoria, ano ou órgão. O CNPJ pode ser de revendedor, e não do fabricante da tecnologia. A contagem considera apenas as compras com resultado vencedor publicado (compras com vencedor identificado); compras classificadas sem resultado vencedor publicado não entram.",
                "exemplo": f"de 2021 a 2026, {inteiro(N_FORN)} fornecedores venceram resultados nas seis categorias; em {NOME[CATS[0]]}, {inteiro(NF_CAT0)}."},
    "sd_org": {"como": "Número de órgãos compradores distintos com ao menos um resultado com valor homologado positivo nas compras de tecnologias críticas para a soberania digital do recorte. O órgão é identificado pelo nome do órgão ou entidade compradora registrado na compra no PNCP, a mesma regra do gráfico 11 e da tabela 2, e é contado uma única vez, ainda que tenha comprado em mais de uma categoria ou ano. A contagem considera apenas as compras com resultado vencedor publicado (compras com vencedor identificado); compras classificadas sem resultado vencedor publicado não entram.",
               "exemplo": f"de 2021 a 2026, {inteiro(N_ORG)} órgãos compraram nas seis categorias; em {NOME[CATS[0]]}, {inteiro(NO_CAT0)}."},
    "g10": {"como": "Percentual do total das seis categorias (cada compra entra uma vez) em compras com cada instrumento registrado: margem de preferência prevista no edital (itens), margem aplicada no resultado (resultados) e exigência de PPB (itens).",
            "exemplo": f"{fmt_pct(100 * instr_tot['margem_aplicada_nominal'] / instr_tot['valor_nominal'])} do valor homologado das seis categorias teve margem de preferência aplicada."},
}
for c in CATS:
    termos = [r["texto_legivel"] for r in dic_leg if r["segmento"] == c and r["tipo"] == "inclusao"]
    I["cat_" + c] = {"como": "Termos buscados no objeto da compra e na descrição dos itens: " + "; ".join(termos) + ".", "termos": termos,
                     "exemplo": f"Verificada por amostragem de {inteiro(precisao[c]['n'])} compras, com precisão de {fmt_pct(precisao[c]['pct'])}."}

# ---- modelo de aquisicao, tipo de vendedor, marcas e porte (mesmas regras do JavaScript do painel)
minus = lambda t: t[0].lower() + t[1:]
MOD_CLS = [n for _, n in sorted({(int(r["ordem"]), r["classe"]) for r in f2_modelo})]
TIPOS_V = ["Fabricante direto", "Revendedor ou integrador", "Empresa pública de TI", "Outra empresa estatal", "Demais fornecedores privados"]
PORTES = ["ME ou EPP", "Demais", "Porte não informado"]
assert MOD_CLS[-1] == "Serviços técnicos, equipamentos e não identificados" and {r["tipo_vendedor"] for r in f2_vend} <= set(TIPOS_V)
prec_ap = [f(r["precisao_final_pct"]) for r in f2_sit if r["situacao"] == "aprovada" and r["ordem"] != "7"]
cls_fora = next(r for r in f2_sit if r["situacao"] != "aprovada")


def mod_pct(cat, classe):
    t = sum(round(f(r["valor_nominal"]), 2) for r in f2_modelo if r["categoria"] == cat)
    return 100 * sum(round(f(r["valor_nominal"]), 2) for r in f2_modelo if r["categoria"] == cat and r["classe"] == classe) / t


def vend_pct(cat, tipo):
    t = sum(round(f(r["valor_nominal"]), 2) for r in f2_vend if r["categoria"] == cat)
    return 100 * sum(round(f(r["valor_nominal"]), 2) for r in f2_vend if r["categoria"] == cat and r["tipo_vendedor"] == tipo) / t


def marca_stats(rows, col="valor_nominal"):  # rows de pn_marca_resultados de uma marca: compras, valor, % revendedores, % fabricante, vendedores, CR4, HHI
    res = {}
    for r in rows:
        res.setdefault(r["chave_resultado"], r)
    tot = sum(round(f(r[col]), 2) for r in res.values())
    por = {}
    for r in res.values():
        por[r["raiz_cnpj_vendedor"]] = por.get(r["raiz_cnpj_vendedor"], 0) + round(f(r[col]), 2)
    vs = sorted(por.values(), reverse=True)
    tp = lambda t: sum(round(f(r[col]), 2) for r in res.values() if r["tipo_vendedor"] == t)
    return {"compras": len({r["id_compra"] for r in rows}), "valor": tot, "rev": 100 * tp("Revendedor ou integrador") / tot,
            "fab": 100 * tp("Fabricante direto") / tot, "vend": len(por), "cr4": 100 * sum(vs[:4]) / tot, "hhi": sum((v / tot) ** 2 for v in vs)}


MS = marca_stats([r for r in f2_marca if r["marca"] == "Microsoft"])
pc_all = {r["id_compra"] for r in f2_porte_c}
pc_me = {r["id_compra"] for r in f2_porte_c if r["porte"] == "ME ou EPP"}
pv_tot = sum(round(f(r["valor_nominal"]), 2) for r in f2_porte_v if r["recorte"] == "todas")
pv_me = sum(round(f(r["valor_nominal"]), 2) for r in f2_porte_v if r["recorte"] == "todas" and r["porte"] == "ME ou EPP")
pv_ni = sum(round(f(r["valor_nominal"]), 2) for r in f2_porte_v if r["recorte"] == "todas" and r["porte"] == "Porte não informado")
f2_rh = ler(F2 + "validacao/resultado_revisao_humana.csv")
_rhm = {r["classe"]: r for r in f2_rh if r["grupo"] == "Modelo de aquisição"}
_nv_rh = [c for c, r in _rhm.items() if r["validada"] == "não"]
I["gm"] = {"como": "Cada barra reparte o valor da categoria entre os modelos de aquisição dos itens, na proporção do valor nos resultados de cada item (sem resultado, do valor estimado do item). "
                   f"Cada barra usa a soma por categoria. Uma compra classificada em duas categorias aparece nas duas; por isso a soma das barras supera o total das seis categorias ({bi(V2A)}), em que cada compra entra uma vez. "
                   "O modelo de cada item é atribuído por palavras-chave no texto do item. Aparecem separadamente as classes com pelo menos 80% de acerto na verificação por amostragem e na revisão humana: acréscimo a licença existente, subscrição ou serviço (assinaturas, licenças por prazo, nuvem e certificados digitais) e licenciamento de direitos permanentes de uso.",
           "nota": ""}  # nota com valores: EXEMPLOS (gm_nota), nos dois modos
I["gv"] = {"como": f"Valor nos resultados (vencedores), na soma por categoria. Uma compra classificada em duas categorias aparece nas duas; por isso a soma das barras supera o total das seis categorias ({bi(V2A)}), em que cada compra entra uma vez. Tipo do vencedor, nesta ordem: fabricante direto (subsidiária brasileira de uma das 15 marcas analisadas, citada na compra), empresa pública de TI, outra empresa estatal, revendedor ou integrador (marca citada e vencedor que não é o fabricante) e demais fornecedores privados (sem marca citada). Empresas públicas de TI: natureza jurídica de empresa pública ou sociedade de economia mista e atividade de tecnologia da informação.",
           "exemplo": f"em Nuvem, empresas públicas de TI ficaram com {fmt_pct(vend_pct('nuvem', 'Empresa pública de TI'))} do valor dos resultados de 2021 a 2026, e revendedores ou integradores, com {fmt_pct(vend_pct('nuvem', 'Revendedor ou integrador'))}."}
I["tm"] = {"como": "Compras com menção à marca no texto do item (ou, quando o item não cita marca, no objeto da compra). A menção não comprova o produto entregue. Valor = valor homologado dos resultados dessas compras, cada resultado uma vez por marca. Vendedor identificado pela raiz do CNPJ (matriz e filiais juntas). CR4 = participação dos quatro maiores vendedores no valor da marca; HHI = soma dos quadrados das participações, de 0 a 1. Só aparecem marcas citadas em pelo menos 20 compras no recorte.",
           "exemplo": f"de 2021 a 2026, a Microsoft foi citada em {inteiro(MS['compras'])} compras, com {mi(MS['valor'])} em resultados; revendedores ficaram com {fmt_pct(MS['rev'])} desse valor, entre {inteiro(MS['vend'])} vendedores, com HHI de {fmt_num(MS['hhi'], 3)}."}
I["porte"] = {"como": "Porte do fornecedor vencedor como registrado no resultado no PNCP, com microempresa e empresa de pequeno porte numa classe única (a fonte quase não registra empresa de pequeno porte; ver Metodologia, Limitações). % das compras com vencedor = compras com ao menos um resultado vencido por empresa do porte ÷ compras com vencedor identificado (uma compra com vencedores de portes diferentes conta em cada porte). % do valor = valor homologado nos resultados vencidos por empresas do porte ÷ valor total dos resultados (cada resultado uma vez). Resultados sem porte informado não aparecem nos cartões; a linha abaixo deles informa a parcela do valor sem porte.",
              "exemplo": f"de 2021 a 2026, micro ou pequenas empresas (ME ou EPP) venceram em {fmt_pct(100 * len(pc_me) / len(pc_all))} das {inteiro(len(pc_all))} compras com vencedor identificado e ficaram com {fmt_pct(100 * pv_me / pv_tot)} do valor; o porte não foi informado em {fmt_pct(100 * pv_ni / pv_tot)} do valor."}
# ---- exemplos de leitura nos dois modos do alternador (1.1). Recorte padrao (2021 a 2026, todas as categorias), sobre os dados
# arredondados a centavos que o painel embute (D); o JavaScript troca o texto conforme o modo (funcao atualizaExemplos).
def EXEMPLOS(dv):
    sx = "deflacionado" if dv else "nominal"
    rs = lambda rows, col, **flt: sum(round(f(r[col]), 2) for r in rows if all(str(r[k]) == str(v) for k, v in flt.items()))
    hc = "hom_" + sx
    totA = {a: rs(cubo, hc, ano=a) for a in ANOS}
    T = sum(totA.values())
    sh = lambda dim, val: 100 * rs(cubo, hc, ano=2025, **{dim: val}) / totA[2025]
    vsob = sum(round(f(r["soberania_2a_" + sx]), 2) for r in sob_ano.values())
    cv = {c: rs(cat_ano, "valor_" + sx, categoria=c) for c in CATS}
    c25 = max(CATS, key=lambda c: rs(cat_ano, "valor_" + sx, categoria=c, ano=2025))
    i_s = 100 * rs(modal, "valor_" + sx, recorte="todas", modalidade="Inexigibilidade") / rs(modal, "valor_" + sx, recorte="todas")
    i_t = 100 * rs(cubo, hc, modalidade="Inexigibilidade") / T
    cm = max(CATS, key=lambda c: cv[c])
    fo_ = 100 * rs(forma, "valor_" + sx, categoria=cm, forma="Objeto próprio") / rs(forma, "valor_" + sx, categoria=cm)
    ag = {}
    for r in fluxo:
        k = (r["cnpj_fornecedor"], r["fornecedor"], r["categoria"])
        ag[k] = ag.get(k, 0) + round(f(r["valor_" + sx]), 2)
    km = max(ag, key=ag.get)
    og = {}
    for r in fluxo:
        if (r["cnpj_fornecedor"], r["fornecedor"], r["categoria"]) == km:
            og[r["orgao"]] = og.get(r["orgao"], 0) + round(f(r["valor_" + sx]), 2)
    c25r = [r for r in conc if r["ano"] == "2025"]
    cx, cn = max(c25r, key=lambda r: f(r["hhi_" + sx])), min(c25r, key=lambda r: f(r["hhi_" + sx]))
    srp = {c: 100 * sum(f(p["pct_srp_" + sx]) / 100 * rs(cat_ano, "valor_" + sx, categoria=c, ano=p["ano"]) for p in perfil if p["categoria"] == c) / cv[c] for c in CATS}
    cs = max(CATS, key=lambda c: srp[c])
    ca = {}  # tabela 2: cadeia raiz do CNPJ x orgao na categoria de maior valor
    for r in cad:
        if r["categoria"] == CATS[0]:
            x = ca.setdefault((r["raiz_cnpj"], r["orgao"]), [0, set()])
            x[0] += round(f(r["valor_" + sx]), 2)
            x[1].add(r["id_compra"])
    cam = max(ca, key=lambda k: ca[k][0])
    tca = sum(round(f(r["valor_" + sx]), 2) for r in cad if r["categoria"] == CATS[0])
    mp = lambda cat, cl: 100 * rs(f2_modelo, "valor_" + sx, categoria=cat, classe=cl) / rs(f2_modelo, "valor_" + sx, categoria=cat)
    vp = lambda cat, tp: 100 * rs(f2_vend, "valor_" + sx, categoria=cat, tipo_vendedor=tp) / rs(f2_vend, "valor_" + sx, categoria=cat)
    ms = marca_stats([r for r in f2_marca if r["marca"] == "Microsoft"], "valor_" + sx)
    pvt = rs(f2_porte_v, "valor_" + sx, recorte="todas")
    pvp = lambda pt: 100 * rs(f2_porte_v, "valor_" + sx, recorte="todas", porte=pt) / pvt
    sa25 = sob_ano[2025]
    return {
        "cp_valor": f"De cada R$ 100 homologados no período, {reais(100 * (totA[2024] + totA[2025]) / T, 0)} concentram-se em 2024 e 2025.",
        "g1_valor": f"em 2025, o valor global homologado foi de {bi(totA[2025])}.",
        "g2": f"em 2025, a esfera federal respondeu por {fmt_pct(sh('esfera', 'Federal'))} do valor global homologado.",
        "g3": f"em 2025, o Poder Executivo respondeu por {fmt_pct(sh('poder', 'Executivo'))} do valor global homologado.",
        "g4": f"em 2025, o pregão eletrônico respondeu por {fmt_pct(sh('modalidade', 'Pregão eletrônico'))} do valor global homologado.",
        "sd_valor": f"dos {bi(T)} homologados no período, {bi(vsob)} referem-se às seis categorias.",
        "sd_part": f"a cada R$ 100 homologados, cerca de {reais(100 * vsob / T)} foram destinados às tecnologias críticas para a soberania digital.",
        "g5": f"em 2025, {NOME[c25]} somou {mi(rs(cat_ano, 'valor_' + sx, categoria=c25, ano=2025))}.",
        "g6": f"em 2025, {fmt_pct(100 * round(f(sa25['soberania_2a_' + sx]), 2) / totA[2025])} do valor global homologado correspondeu às seis categorias.",
        "g7": f"nas tecnologias críticas, a inexigibilidade respondeu por {fmt_pct(i_s)} do valor, ante {fmt_pct(i_t)} no total das compras.",
        "g8": f"em {NOME[cm]}, {fmt_pct(fo_)} do valor foi contratado como objeto próprio.",
        "g9": f"{km[1]} recebeu {mi(ag[km])} em {NOME[km[2]]}, principalmente de {max(og, key=og.get)}.",
        "t2": (f"em 2025, em {NOME[cx['categoria']]}, os quatro maiores fornecedores concentraram {fmt_pct(f(cx['cr4_' + sx]))} do valor (CR4) "
               f"e o HHI foi {fmt_num(f(cx['hhi_' + sx]), 3)}; em {NOME[cn['categoria']]}, CR4 de {fmt_pct(f(cn['cr4_' + sx]))} e HHI de "
               f"{fmt_num(f(cn['hhi_' + sx]), 3)}, o que indica compras menos concentradas."),
        "t3": f"em {NOME[cs]}, {fmt_pct(srp[cs])} do valor veio de atas de registro de preços.",
        "t1": (f"em {NOME[CATS[0]]}, a maior cadeia de 2021 a 2026 vai de {cad_raiz[cam[0]]['nome']} a {cam[1]}, com {mi(ca[cam][0])} em "
               f"{inteiro(len(ca[cam][1]))} compra{'s' if len(ca[cam][1]) > 1 else ''}, {fmt_pct(100 * ca[cam][0] / tca)} da categoria."),
        "g10ncm": (f"nas tecnologias críticas para a soberania digital, {mi1(rs(ncm, 'ncm_item_' + sx, recorte='todas'))} em itens de material estavam cobertos por margem de preferência, "
                   f"mas só {mi1(rs(ncm, 'margem_aplicada_material_' + sx, recorte='todas'))} tiveram a margem efetivamente aplicada."),
        "g10": f"{fmt_pct(100 * rs(instr, 'margem_aplicada_' + sx, recorte='todas') / rs(instr, 'valor_' + sx, recorte='todas'))} do total das seis categorias teve margem de preferência aplicada.",
        "gm": f"Em Nuvem, subscrição ou serviço respondeu por {fmt_pct(mp('nuvem', 'Subscrição ou serviço'))} do valor de 2021 a 2026.",
        "gv": (f"em Nuvem, empresas públicas de TI ficaram com {fmt_pct(vp('nuvem', 'Empresa pública de TI'))} do valor dos resultados de 2021 a 2026, "
               f"e revendedores ou integradores, com {fmt_pct(vp('nuvem', 'Revendedor ou integrador'))}."),
        "tm": (f"de 2021 a 2026, a Microsoft foi citada em {inteiro(ms['compras'])} compras, com {mi(ms['valor'])} em resultados; revendedores ficaram com "
               f"{fmt_pct(ms['rev'])} desse valor, entre {inteiro(ms['vend'])} vendedores, com HHI de {fmt_num(ms['hhi'], 3)}."),
        "porte": (f"de 2021 a 2026, micro ou pequenas empresas (ME ou EPP) venceram em {fmt_pct(100 * len(pc_me) / len(pc_all))} das {inteiro(len(pc_all))} compras "
                  f"com vencedor identificado e ficaram com {fmt_pct(pvp('ME ou EPP'))} do valor; o porte não foi informado em {fmt_pct(pvp('Porte não informado'))} do valor."),
    }


GRUPO_NV = "Serviços técnicos, equipamentos e não identificados"
CATS_NV = ["data_center", "seguranca", "ia", "identidade"]  # categorias em que o grupo e a maior parte do valor


def GM_TXT(dv):  # texto abaixo do grafico 9 no recorte padrao; o JavaScript monta o mesmo texto (funcao gmTexto)
    sx = "deflacionado" if dv else "nominal"
    mp = lambda cat, cl: 100 * sum(round(f(r["valor_" + sx]), 2) for r in f2_modelo if r["categoria"] == cat and r["classe"] == cl) / sum(round(f(r["valor_" + sx]), 2) for r in f2_modelo if r["categoria"] == cat)
    nv = [mp(c, GRUPO_NV) for c in CATS_NV]
    assert min(nv) > 50 and all(mp(c, GRUPO_NV) < 50 for c in CATS if c not in CATS_NV)
    return (f"Quando o modelo de aquisição é identificável, o Estado contrata por subscrição ou serviço: {fmt_pct(mp('nuvem', 'Subscrição ou serviço'))} do valor em Nuvem "
            f"e {fmt_pct(mp('plataformas', 'Subscrição ou serviço'))} em Plataformas e licenciamento. O licenciamento de direitos permanentes de uso não passa de "
            f"{fmt_pct(max(mp(c, 'Licenciamento de direitos permanentes de uso') for c in CATS))} do valor em nenhuma categoria. Em Data center, Segurança cibernética, Inteligência artificial e Identidade, "
            f"a maior parte do valor (entre {fmt_pct(min(nv))} e {fmt_pct(max(nv))}) está em serviços técnicos, equipamentos e itens não identificados, que a classificação não separa com segurança.")


def GM_NOTA(dv):  # nota do i do grafico 9: componentes do grupo no recorte padrao (soma por categoria)
    sx = "deflacionado" if dv else "nominal"
    v = lambda o: sum(round(f(r["valor_" + sx]), 2) for r in f2_comp if r["ordem"] == o)
    return ("Grupo de itens de desenvolvimento e serviços técnicos, equipamentos e itens sem indicação do modelo, cuja classificação automática não atingiu 80% de acerto "
            f"na revisão humana. Inclui também suporte e manutenção de licença ({mi(v('4'))}) e compras sem itens com valor ({mi(v('0'))}).")


ia_nota = {(r["componente"], r["mercado"]): r for r in ler(TP + "ia_nota_resumo.csv")}


def IA_NOTA(dv):  # nota do i da linha-resumo da aba IA: por que a tecnologia de IA difere da categoria IA do painel
    sx = "deflacionado" if dv else "nominal"
    g = lambda c, m: ia_nota.get((c, m), {"compras": "0", "valor_" + sx: "0"})
    v = lambda c, m: f(g(c, m)["valor_" + sx])
    k = lambda c, m: int(g(c, m)["compras"])
    tec, cap = v("A", "tecnologia") + v("C", "tecnologia"), v("A", "capacitação") + v("B", "capacitação") + v("C", "capacitação")
    return (f"A tecnologia de IA soma {mi(tec)}: {mi(v('A', 'tecnologia'))} de {inteiro(k('A', 'tecnologia'))} compras da categoria Inteligência artificial do painel e "
            f"{mi(v('C', 'tecnologia'))} de {inteiro(k('C', 'tecnologia'))} compras de acréscimo de IA a licença classificadas em outras categorias. "
            f"A categoria IA do painel soma {mi(v('A', 'tecnologia') + v('A', 'capacitação'))} em {inteiro(k('A', 'tecnologia') + k('A', 'capacitação'))} compras; "
            f"{inteiro(k('A', 'capacitação'))} delas, com {mi(v('A', 'capacitação'))}, são de capacitação. O valor de cada compra é repartido entre as classes pelos itens, "
            "como no gráfico 9, e a compra é contada uma vez, na classe de maior valor. "
            f"A capacitação em IA soma {mi(cap)}: {inteiro(k('B', 'capacitação'))} compras excluídas pelo dicionário da categoria, {inteiro(k('A', 'capacitação'))} da categoria "
            f"e {inteiro(k('C', 'capacitação'))} do acréscimo a licença.")


COM_REAIS = {"cp_valor", "g1_valor", "sd_valor", "sd_part", "g5", "g9", "t1", "g10ncm", "tm", "gm_nota", "ia_resumo_nota"}  # textos que citam reais
MODO_TXT = ["Valores nominais.", f"Valores deflacionados, a preços de {MES_BASE_TXT}."]  # frase final dos textos que citam reais
MODO_ROT = ["valores nominais", "valores deflacionados"]
com_modo = lambda t, dv: (t if t.endswith(".") else t + ".") + " " + MODO_TXT[dv]
EXS = [{k: (com_modo(t, dv) if k in COM_REAIS else t) for k, t in dict(EXEMPLOS(dv), gm_nota=GM_NOTA(dv), ia_resumo_nota=IA_NOTA(dv)).items()} for dv in (0, 1)]
for k, t in EXS[0].items():
    if k.endswith("_nota"):
        I[k[:-5]]["nota"] = t
    else:
        I[k]["exemplo"] = t
EXDIN = list(EXS[0])  # textos do "i" que mudam com o alternador Valores nominais / Valores deflacionados
I["sobre_participacao"]["exemplo"] = com_modo(I["sobre_participacao"]["exemplo"], 0)  # aba Sobre: sem alternador, valores nominais
with open(TP + "pn_exemplos_modos.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["elemento", "modo", "texto"])
    for dv in (0, 1):
        for k, t in EXS[dv].items():
            w.writerow([k, MODO_ROT[dv], t])
        w.writerow(["gm_txt", MODO_ROT[dv], GM_TXT(dv)])
with open(TP + "pn_textos_i.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["elemento", "definicao_valor_homologado", "como_interpretar", "exemplo_de_leitura", "nota_metodologica"])
    for k, v in I.items():
        w.writerow([k, "Valor global homologado: " + DEF_HOM if k in USA_HOM else "", v.get("como", ""), v.get("exemplo", ""), v.get("nota", "")])


# ------------------------------------------------------------------ dados embutidos (JavaScript)
def idx(lista):
    return {v: i for i, v in enumerate(lista)}


ESF = ["Federal", "Estadual", "Municipal", "Distrital", "Esfera não informada"]
POD = ["Executivo", "Legislativo", "Judiciário", "Poder não informado"]
MOD = sorted({r["modalidade"] for r in cubo}, key=lambda m: -soma(cubo, "hom_nominal", modalidade=m))
FORMAS = ["Objeto próprio", "Item de contratação mais ampla"]
iE, iP, iM, iC, iF = idx(ESF), idx(POD), idx(MOD), idx(CATS), idx(FORMAS)
forn_lista = sorted({(r["cnpj_fornecedor"], r["fornecedor"]) for r in fluxo})
iForn = idx(forn_lista)
org_lista = sorted({r["orgao"] for r in fluxo} | {r["orgao"] for r in orgaos})
iOrg = idx(org_lista)
r2 = lambda x: round(f(x), 2)
MARCAS_L = sorted({r["marca"] for r in f2_marca})
_ich = {c: i for i, c in enumerate(sorted({r["chave_resultado"] for r in f2_marca}))}
_irz = {c: i for i, c in enumerate(sorted({r["raiz_cnpj_vendedor"] for r in f2_marca}))}
_icp = {c: i for i, c in enumerate(sorted({r["id_compra"] for r in f2_marca} | {r["id_compra"] for r in f2_porte_c}))}
# compras de cada linha de D.fluxo (mesma ordem), em indices: contagem de compras distintas da linha-resumo do Sankey
_ic = {c: i for i, c in enumerate(sorted({r["id_compra"] for r in fluxo_c}))}
_fc = {}
for r in fluxo_c:
    _fc.setdefault((r["categoria"], r["ano"], r["cnpj_fornecedor"], r["orgao"], r["esfera"]), []).append(_ic[r["id_compra"]])
_iFc = {c: i for i, (c, _) in enumerate(forn_lista)}
_rz_de = {r["cnpj_fornecedor"]: r["raiz_cnpj"] for r in cad}
_raizes = sorted(set(_rz_de.values()))
_iRz = {z: i for i, z in enumerate(_raizes)}
FLUXO_C = [_fc[(r["categoria"], r["ano"], r["cnpj_fornecedor"], r["orgao"], r["esfera"])] for r in fluxo]
assert all(len(x) == int(r["n_compras"]) for x, r in zip(FLUXO_C, fluxo))
D = {
    "anos": ANOS, "cats": CATS, "nome": NOME, "cor": COR, "camada": CAMADA, "esferas": ESF, "poderes": POD,
    "modalidades": MOD, "formas": FORMAS, "mesBase": MES_BASE_CURTO, "mesBaseTxt": MES_BASE_TXT,
    "cubo": [[int(r["ano"]), iE[r["esfera"]], iP[r["poder"]], iM[r["modalidade"]], int(r["n_publicadas"]),
              int(r["n_homologadas"]), int(r["n_sem_homologacao"]), int(r["n_valor_excluido"]), r2(r["hom_nominal"]),
              r2(r["hom_deflacionado"])] for r in cubo],
    "sobAno": [[int(r["ano"]), r2(r["soberania_2a_nominal"]), r2(r["soberania_2a_deflacionado"]), int(r["n_compras_seis_categorias"])]
               for r in sob_ano.values()],
    "catAno": [[iC[r["categoria"]], int(r["ano"]), int(r["n_compras"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in cat_ano],
    "modal": [[-1 if r["recorte"] == "todas" else iC[r["recorte"]], int(r["ano"]), iM[r["modalidade"]], r2(r["valor_nominal"]),
               r2(r["valor_deflacionado"]), int(r["n_compras"])] for r in modal],
    "forma": [[iC[r["categoria"]], int(r["ano"]), iF[r["forma"]], int(r["n_compras"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"])]
              for r in forma],
    "forn": [n for _, n in forn_lista], "fornCnpj": [c for c, _ in forn_lista], "org": org_lista,
    "fluxo": [[iC[r["categoria"]], int(r["ano"]), iForn[(r["cnpj_fornecedor"], r["fornecedor"])], iOrg[r["orgao"]],
               r2(r["valor_nominal"]), r2(r["valor_deflacionado"]), iE[r["esfera"]]] for r in fluxo],
    "conc": [[iC[r["categoria"]], int(r["ano"]), int(r["n_fornecedores"]), f(r["cr4_nominal"]), f(r["hhi_nominal"]), r2(r["valor_nominal"]),
              f(r["cr4_deflacionado"]), f(r["hhi_deflacionado"]), r2(r["valor_deflacionado"])] for r in conc],
    "perfil": [[iC[r["categoria"]], int(r["ano"]), int(r["n_compras_valor_positivo"]), f(r["mediana_nominal"]), f(r["mediana_deflacionado"]),
                f(r["pct_srp_nominal"]), f(r["pct_srp_deflacionado"]),
                None if r["pct_bens_nominal"] == "" else f(r["pct_bens_nominal"]),
                None if r["pct_bens_deflacionado"] == "" else f(r["pct_bens_deflacionado"])] for r in perfil],
    "perfilVals": [[iC[r["categoria"]], int(r["ano"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"]), 1 if r["srp"] == "true" else 0] for r in perfil_vals],
    "bens": [[iC[r["categoria"]], int(r["ano"]), r2(r["valor_bens_nominal"]), r2(r["valor_resultados_nominal"]), r2(r["valor_bens_deflacionado"]), r2(r["valor_resultados_deflacionado"])] for r in perfil_bens],
    "orgaos": [[iC[r["categoria"]], int(r["ano"]), iOrg[r["orgao"]], iE[r["esfera"]], r2(r["valor_nominal"]), r2(r["valor_deflacionado"])]
               for r in orgaos],
    "instr": [[-1 if r["recorte"] == "todas" else iC[r["recorte"]], int(r["ano"])] + [r2(r[k]) for k in (
        "valor_nominal", "valor_deflacionado", "margem_prevista_nominal", "margem_prevista_deflacionado",
        "margem_aplicada_nominal", "margem_aplicada_deflacionado", "ppb_nominal", "ppb_deflacionado")] for r in instr],
    "ncm": [[-1 if r["recorte"] == "todas" else iC[r["recorte"]], int(r["ano"])] + [r2(r[k]) for k in (
        "ncm_item_nominal", "ncm_item_deflacionado", "ncm_item_tradutor_nominal", "ncm_item_tradutor_deflacionado",
        "margem_aplicada_material_nominal", "margem_aplicada_material_deflacionado")] for r in ncm],
    "preench": [[r["indicador"], int(r["n_registros"]), int(r["n_preenchidos"]), int(r["n_verdadeiro"])] for r in preench],
    "encomenda": [[r["instrumento"], int(r["n_compras"]), f(r["valor_nominal"])] for r in encom],
    "pais": [int(pais6["n_resultados"]), int(pais6["n_preenchido"]), PAIS_PCT],
    "fluxoC": FLUXO_C,
    # tabela 2: [categoria, ano, fornecedor (indice de D.forn), orgao, compra (indice de D.fluxoC), valor nominal, valor deflacionado]
    "cad": [[iC[r["categoria"]], int(r["ano"]), _iFc[r["cnpj_fornecedor"]], iOrg[r["orgao"]], _ic[r["id_compra"]], r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in cad],
    "cadObj": [cad_obj[c] for c in sorted(_ic, key=_ic.get)],
    "raiz": [[cad_raiz[z]["nome"], ["ME ou EPP", "Demais", "Não informado"].index(cad_raiz[z]["porte"])] for z in _raizes],
    "fornRaiz": [_iRz[_rz_de[c]] for c, _ in forn_lista],
    "portesRaiz": ["ME ou EPP", "Demais", "Não informado"],
    "modCls": MOD_CLS, "tiposV": TIPOS_V, "portes": PORTES, "marcas": MARCAS_L,
    "modelo": [[iC[r["categoria"]], int(r["ano"]), MOD_CLS.index(r["classe"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in f2_modelo],
    "vend": [[iC[r["categoria"]], int(r["ano"]), TIPOS_V.index(r["tipo_vendedor"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in f2_vend],
    "marcaR": [[MARCAS_L.index(r["marca"]), iC[r["categoria"]], int(r["ano"]), _ich[r["chave_resultado"]], _irz[r["raiz_cnpj_vendedor"]],
                TIPOS_V.index(r["tipo_vendedor"]), _icp[r["id_compra"]], r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in f2_marca],
    "porteC": [[iC[r["categoria"]], int(r["ano"]), PORTES.index(r["porte"]), _icp[r["id_compra"]]] for r in f2_porte_c],
    "porteV": [[-1 if r["recorte"] == "todas" else iC[r["recorte"]], int(r["ano"]), PORTES.index(r["porte"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in f2_porte_v],
    "achados": [[r["achado"], r["titulo"], r["texto"]] for r in f2_achados],
    "ex": {k: [EXS[0][k], EXS[1][k]] for k in EXDIN}, "modoTxt": MODO_TXT,
    "I": I,
}
# aba Inteligencia artificial (p1_06 a p1_08): compras, partes de valor por classe, resultados, fornecedores, objetos, marcas e achados
ia_base = sorted(ler(TP + "ia_base.csv"), key=lambda r: r["id_compra"])
ia_partes, ia_res = ler(TP + "ia_base_classes.csv"), ler(TP + "ia_resultados.csv")
ia_fr = {r["raiz_cnpj"]: r for r in ler(TP + "ia_fornecedores.csv")}
ia_fc = {r["cnpj_fornecedor"]: r["nome"] for r in ler(TP + "ia_fornecedores_cnpj.csv")}
ia_obj = {r["id_compra"]: r["objeto"] for r in ler(TP + "ia_objetos.csv")}
IA_CLS = ["Acréscimo à licença", "Solução de IA (exclusiva ou em pacote)", "Outros", "Capacitação"]
IA_TIPOS = [r["objeto"] for r in ler(TP + "dicionario_ia_tipos.csv")]
IA_PORTES = ["ME ou EPP", "Demais", "Não informado"]
_iIc = {r["id_compra"]: i for i, r in enumerate(ia_base)}
_ia_cnpj = sorted({r["cnpj_fornecedor"] for r in ia_res})
_iIf = {c: i for i, c in enumerate(_ia_cnpj)}
_ia_raiz = sorted(ia_fr)
_iIr = {z: i for i, z in enumerate(_ia_raiz)}
_ia_org = sorted({r["orgao"] for r in ia_res})
_iIo = {o: i for i, o in enumerate(_ia_org)}
_raiz_de = {r["cnpj_fornecedor"]: r["raiz_cnpj"] for r in ia_res}
ia_marcas = ler(TP + "ia_marcas.csv")
D["ia"] = {
    "classes": IA_CLS, "tipos": IA_TIPOS, "portes": IA_PORTES,
    # cores dos tipos de objeto: sem as cores das categorias
    "corTipo": ["#0B3D91", "#1351B4", "#7A5195", "#1F7A6F", "#0C7B8E", "#9C4F96", "#3F6E9C", "#B5651D", "#5E7C16", "#5C6B7A", "#8B6F47", "#A7B4C2", "#C9D3DF"],
    "compras": [[int(r["ano"]), IA_CLS.index(r["classe"]), IA_TIPOS.index(r["tipo_objeto"])] for r in ia_base],
    "partes": [[_iIc[r["id_compra"]], IA_CLS.index(r["classe"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in ia_partes],
    # resultados: [compra, classe, tipo, fornecedor (CNPJ), orgao, ano, valor nominal, valor deflacionado]
    "res": [[_iIc[r["id_compra"]], IA_CLS.index(r["classe"]), IA_TIPOS.index(r["tipo_objeto"]), _iIf[r["cnpj_fornecedor"]], _iIo[r["orgao"]], int(r["ano"]),
             r2(r["valor_nominal"]), r2(r["valor_deflacionado"])] for r in ia_res],
    "forn": [[ia_fc[c], _iIr[_raiz_de[c]]] for c in _ia_cnpj],
    "raiz": [[ia_fr[z]["nome"], IA_PORTES.index(ia_fr[z]["porte"])] for z in _ia_raiz],
    "org": _ia_org,
    "obj": [ia_obj[r["id_compra"]] for r in ia_base],
    "ids": [r["id_compra"] for r in ia_base],
    "marcas": [[r["marca"], int(r["compras_de_produto"]), r2(r["valor_nominal"]), r2(r["valor_deflacionado"]), int(r["compras_de_capacitacao"]),
                r["principais_vendedores_compras_de_produto"]] for r in ia_marcas],
    "achados": [[r["achado"], r["titulo"], r["texto"]] for r in ler(TP + "ia_achados.csv")],
    "filtros": [["tec", "Todas (tecnologia)", [0, 1, 2]], ["acr", "Acréscimo à licença", [0]], ["sol", "Solução de IA (exclusiva ou em pacote)", [1]],
                ["out", "Outros", [2]], ["cap", "Capacitação", [3]]],
    "desc": {"tec": ["Todas (tecnologia).", "Compras de tecnologia de IA: acréscimo à licença, solução de IA e outros. A capacitação tem botão próprio, à direita."],
             "acr": ["Acréscimo à licença.", "Assistente de IA acoplado a licença de software já usada, como Copilot para Microsoft 365 e Gemini para Google Workspace."],
             "sol": ["Solução de IA (exclusiva ou em pacote).", "A IA é o objeto da compra ou vem como componente entre vários: nuvem, suítes de produtividade, atendimento omnichannel, segurança."],
             "out": ["Outros.", "Compras com IA que não se enquadram nas classes anteriores, como equipamentos com IA embarcada e contratações mais amplas que citam IA nos itens."],
             "cap": ["Capacitação.", "Cursos, treinamentos, inscrições, pós-graduação e eventos sobre IA. Capacitação não faz parte do total das tecnologias críticas para a soberania digital."]},
}

# ------------------------------------------------------------------ metodologia (mesmo conteudo no painel e no .md)
B = []  # blocos: (tipo, conteudo)


def h(t, nivel=2): B.append(("h%d" % nivel, t))
def p(t): B.append(("p", t))
def ul(itens): B.append(("ul", itens))
def tab(cab, linhas, titulo=None): B.append(("table", (titulo, cab, linhas)))


n_dup = sum(int(r["compras_removidas"]) for r in dup_rem if r["recorte"] == "todas as compras")
bruto_dup = sum(f(r["valor_homologado_bruto_removido"]) for r in dup_rem if r["recorte"] == "todas as compras")
limpo_dup = sum(f(r["valor_homologado_limpo_removido"]) for r in dup_rem if r["recorte"] == "todas as compras")
n_dup6 = sum(int(r["compras_removidas"]) for r in dup_rem if r["recorte"] == "seis categorias")
limpo_dup6 = sum(f(r["valor_homologado_limpo_removido"]) for r in dup_rem if r["recorte"] == "seis categorias")
n_lit = sum(int(r["compras_removidas_regra_literal"]) for r in dup_lit)
bruto_lit = sum(f(r["valor_bruto_removido_regra_literal"]) for r in dup_lit)
n_completa = sum(int(r["n_compras_publicadas"]) for r in tot_completa)
bruto_completa = sum(f(r["homologado_bruto"]) for r in tot_completa)
limpo_completa = sum(f(r["homologado_limpo"]) for r in tot_completa)
assert n_completa == n_base_limpa
motivos = {}
for r in exclusoes:
    m = r["motivo_principal"]
    motivos.setdefault(m, [0, 0.0])
    motivos[m][0] += int(r["n_compras"])
    motivos[m][1] += f(r["valor_homologado_bruto_excluido"])
ROT_MOT = {"regra_1_valor_preenchimento": "Regra 1: valor de preenchimento (sequência de 9 ou acima de R$ 1 trilhão)",
           "regra_2_divergencia (sem regra 1)": "Regra 2: estimado e homologado divergem mais de 100 vezes (sem regra 1)",
           "regra_3_inconsistencia_itens (sem regras 1 e 2)": "Regra 3: inconsistência nos itens (sem regras 1 e 2)",
           "revisao_manual_erro_provavel": "Revisão manual: erro provável (compras acima de R$ 1 bi sem regra automática)"}
exc_total = sum(v[1] for v in motivos.values())
n_exc_total = sum(v[0] for v in motivos.values())
margem_tot = next(r for r in mg_decomp if r["dimensao"] == "total")
mg = lambda d, c: next((r for r in mg_decomp if r["dimensao"] == d and r["categoria"] == c), None)
pre = {r["indicador"]: r for r in preench}

B.append(("downloads", None))
h("1. Fonte e cobertura")
p(f"Os dados partem da camada tratada (main_intermediate) do Colibri (gestaogovbr.github.io/colibri), base ComprasGov, que organiza dados oficiais do Portal Nacional de Contratações Públicas (pncp.gov.br). A extração, em {DATA_COLETA}, reuniu {inteiro(n_extr)} compras, {inteiro(n_itens_extr)} itens e {inteiro(n_res_extr)} resultados publicados entre {dmin:%d/%m/%Y} e {dmax:%d/%m/%Y}. Após manter apenas os registros vigentes e remover duplicidades, restaram {inteiro(N_PUB)} compras únicas, aproveitamento de {fmt_pct(100 * N_PUB / n_extr)} do total extraído. O Colibri não informa se a base ComprasGov abrange a totalidade das contratações publicadas no PNCP. Os resultados referem-se às compras presentes nessa base.")
p("Valor global homologado: " + DEF_HOM)
p("Comparação com o PNCP em Números: não foi possível. O painel oficial (https://www.gov.br/pncp/pt-br/acesso-a-informacao/painel-pncp-em-numeros-2026) é um painel Qlik embutido que não carregou em navegador sem interface (Playwright com Chromium, com aceite de cookies) nas abas Visão Geral, Contratações Publicadas e Contratações Homologadas, e a página não traz números em texto nem arquivo para baixar. Não há, portanto, medida da cobertura da base ComprasGov em relação ao total publicado no PNCP.")
p("Extração: as tabelas foram exportadas integralmente para Parquet com COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__compras) TO 'compras.parquet' (FORMAT parquet), e o mesmo para __itens e __resultados. A exportação em CSV pela interface do DuckDB foi abandonada porque trunca o resultado em 50.000 linhas.")

h("2. Tratamento da base de dados e auditoria de valores")
ul([f"Vigência: somente registros com is_current = true. Compras deduplicadas por id_compra, mantendo a maior data_atualizacao (desempate por data_inclusao e valido_de): {inteiro(n_base_limpa)} compras (base_limpa.parquet).",
    f"Itens deduplicados por id_compra_item, mantendo a maior data_atualizacao (desempate por valido_de): {inteiro(n_itens_dedup)} itens vigentes, de {inteiro(n_itens_extr)} extraídos.",
    f"Resultados deduplicados pela chave (id_compra_item, sequencial_resultado, ni_fornecedor), mantendo a maior data efetiva entre as colunas de atualização, inclusão e resultado, e excluídos os cancelados (data_cancelamento preenchida): {inteiro(n_res_dedup)} resultados.",
    "Chaves de junção: id_compra (compra, itens e resultados) e id_compra_item (itens e resultados). O número de controle do PNCP ficou apenas como atributo de auditoria, por ter nulos nos itens.",
    f"Republicações: foram removidas {inteiro(n_dup)} compras que repetem outra compra em CNPJ do órgão, unidade, número do processo, objeto normalizado (minúsculas, sem acentos, espaços colapsados), valor homologado e conjunto de fornecedores vencedores, mantida a versão com data_atualizacao mais recente. Resultado: {inteiro(N_PUB)} compras.",
    "Regras automáticas de valor suspeito (a flag é a união das três e não apaga a compra): (1) valor de preenchimento, formado por sequência de 9 ou acima de R$ 1 trilhão; (2) valor estimado e homologado divergentes em mais de 100 vezes, em qualquer direção; (3) inconsistência nos itens, quando o valor total difere de quantidade × valor unitário em mais de 1% ou quando a quantidade é igual ao valor unitário.",
    f"Revisão manual: compras acima de R$ 1 bilhão não alcançadas pelas regras automáticas foram revisadas uma a uma (auditoria_revisao_manual_proposta.csv); as classificadas como erro provável ({inteiro(n_audit[0])} na base) têm o valor excluído das somas.",
    "Em todos os casos a compra continua na contagem de compras; apenas o valor sai das somas. O valor limpo é o homologado das compras sem exclusão."])
linhas = [[ROT_MOT[m], inteiro(v[0]), vauto(v[1])] for m, v in sorted(motivos.items(), key=lambda kv: -kv[1][1])]
linhas.append(["Total excluído", inteiro(n_exc_total), bi(exc_total)])
tab(["Motivo principal da exclusão", "Compras", "Valor homologado bruto excluído"], linhas, "Valores excluídos por motivo (2021 a 2026)")
linhas = []
for a in ANOS:
    t = tot_ano[a]
    linhas.append([str(a), inteiro(t["n_compras_publicadas"]), inteiro(t["n_compras_homologado_valido"]),
                   inteiro(t["n_compras_sem_homologacao"]), inteiro(t["n_compras_homologado_excluido"]),
                   vauto(t["homologado_bruto"]), vauto(t["homologado_excluido"]), vauto(t["homologado_limpo"])])
linhas.append(["Total", inteiro(N_PUB), inteiro(N_HOM), inteiro(N_SEM), inteiro(N_EXC), bi(BRUTO), bi(exc_total), bi(HOM)])
tab(["Ano", "Compras publicadas", "Com homologado válido", "Sem homologação", "Valor excluído", "Homologado bruto",
     "Excluído", "Homologado limpo"], linhas, "Valor bruto e valor limpo por ano")

h("3. Classificação das tecnologias críticas para a soberania digital")
p("Soberania digital é a capacidade de o Estado controlar os dados, a infraestrutura e as tecnologias de que depende para funcionar (Madiega, 2020; Floridi, 2020). Critério de criticidade: são críticas as tecnologias de que o Estado depende para operar sistemas, guardar dados e identificar cidadãos, e cujo controle define onde os dados ficam, em que condições o serviço é prestado e se pode ser interrompido. As seis categorias seguem documentos de referência da política tecnológica europeia (Comissão Europeia, 2023; Bria, Timmers e Gernone, 2025), indicados na coluna Referência da tabela abaixo.")
B.append(("h3", "Referências"))
ul(["MADIEGA, T. Digital sovereignty for Europe. EPRS Ideas Paper. Bruxelas: European Parliamentary Research Service, 2020.",
    "FLORIDI, L. The fight for digital sovereignty: what it is, and why it matters, especially for the EU. Philosophy & Technology, v. 33, 2020.",
    "COMISSÃO EUROPEIA. Recomendação (UE) 2023/2113 da Comissão, de 3 de outubro de 2023, relativa a domínios tecnológicos críticos para a segurança económica da UE, visando a realização de uma nova avaliação dos riscos com os Estados-Membros. Jornal Oficial da União Europeia, 2023. Disponível em: https://eur-lex.europa.eu/eli/reco/2023/2113",
    "BRIA, F.; TIMMERS, P.; GERNONE, F. EuroStack: a European alternative for digital sovereignty. Gütersloh: Bertelsmann Stiftung, 2025. DOI: 10.11586/2025006."])
p("Campos pesquisados: no nível da compra, objeto_compra e informacao_complementar; no nível do item, descricao, descricao_detalhada e descricao_resumida. O texto é convertido para minúsculas e sem acentos. Uma compra (ou item) entra na categoria quando contém algum termo de inclusão e nenhum termo de exclusão da mesma categoria no mesmo texto. As expressões exatas estão em dicionario_termos.csv, no pacote de downloads.")
p(f"Total das seis categorias e soma por categoria. O painel usa só estes dois termos. Total das seis categorias ({bi(V2A)}, nos KPIs): cada compra entra uma única vez. "
  f"Soma por categoria ({bi(V2B)}, nos gráficos e tabelas por categoria): uma compra classificada em duas categorias aparece nas duas, com o valor de cada uma; por isso a soma das categorias supera o total. "
  f"Uma terceira medida aparece só nesta metodologia: a compra inteira em cada categoria identificada, inclusive quando o termo está só nos itens ({bi(V2C)}).")
p("Regra do total das seis categorias: cada compra é contada uma única vez. Quando o termo está no objeto de qualquer categoria, entra o homologado limpo integral da compra. Quando o termo aparece só nos itens, entra a soma do valor homologado nos resultados desses itens (cada item uma vez), limitada ao homologado limpo da compra. Por categoria, a mesma regra vale dentro de cada categoria, e uma compra pode aparecer em mais de uma.")
linhas = []
for c in CATS:
    inc = "; ".join(r["texto_legivel"] for r in dic_leg if r["segmento"] == c and r["tipo"] == "inclusao")
    exc = "; ".join(dict.fromkeys(r["texto_legivel"] for r in dic_leg if r["segmento"] == c and r["tipo"] == "exclusao")) or "nenhum"
    linhas.append([NOME[c], CAMADA[c], REFERENCIA[c], inc, exc])
tab(["Categoria", "Camada tecnológica", "Referência", "Termos de inclusão", "Termos de exclusão"], linhas, "Dicionário de termos por categoria")
p("Verificação por amostragem: em cada categoria, uma amostra de 150 compras, sorteada por hash determinístico, foi revisada uma a uma. A compra é pertinente quando a tecnologia da categoria faz parte do que é contratado; não é pertinente quando o termo aparece como tema de curso, evento ou publicação, como nome de órgão, como atributo acessório de equipamento ou em menção incidental. As categorias abaixo de 80% tiveram o dicionário ajustado e foram medidas em nova amostra independente, sem repetir compras, até todas superarem 80%. A precisão final é a da última amostra, excluídas as compras que saíram da base como republicação.")
linhas = [[NOME[c], precisao[c]["amostra"], inteiro(precisao[c]["n"]), inteiro(precisao[c]["pertinentes"]),
           fmt_pct(precisao[c]["pct"]), "sim" if precisao[c]["ajustado"] == "sim" else "não"] for c in CATS]
tab(["Categoria", "Amostra final", "Compras revisadas", "Pertinentes", "Precisão", "Dicionário ajustado"], linhas, "Precisão por categoria")
p("Remoção indevida pelo ajuste do dicionário: entre as compras que o dicionário original classificava e o dicionário final deixou de classificar, 100 por categoria foram sorteadas (hash com o rótulo remocao1) e julgadas com o mesmo critério. A regra previa novo ajuste se alguma categoria passasse de 20%; nenhuma passou.")
linhas = [[NOME[r["categoria"]], inteiro(n_rem_pares.get(r["categoria"], 0)), inteiro(r["n_julgadas"]),
           inteiro(r["n_remocao_indevida"]), fmt_pct(r["taxa_remocao_indevida_pct"])] for r in sorted(rem_taxa, key=lambda r: CATS.index(r["categoria"]))]
tab(["Categoria", "Pares compra × categoria removidos", "Julgadas", "Remoções indevidas", "Taxa"], linhas, "Remoção indevida por categoria")

h("4. Teste de robustez")
linhas = [[NOME[r["categoria"]], mi(r["valor_a_so_objeto"]), r["posicao_a"], mi(r["valor_b_objeto_e_itens"]), r["posicao_b"]] for r in robustez]
tab(["Categoria", "(a) Só termo no objeto", "Posição (a)", "(b) Objeto e itens", "Posição (b)"], linhas,
    "TABELA 7. Valor global homologado e posição de cada categoria em duas versões da classificação (2021 a 2026) (Em R$ milhões)")
mesma = all(r["posicao_a"] == r["posicao_b"] for r in robustez)
p("A ordem entre as categorias " + ("se mantém nas duas versões" if mesma else "muda entre as duas versões") +
  ". A versão (b), objeto e itens, é o critério adotado no painel.")

h("5. Indicadores de concentração")
p("sᵢ = valor homologado do fornecedor i ÷ valor homologado total da categoria no ano; CR4 = (s₁ + s₂ + s₃ + s₄) × 100, com os quatro maiores sᵢ; HHI = Σ sᵢ², de 0 a 1. Base: resultados vigentes e não cancelados das compras da categoria (compra com termo no objeto: todos os resultados; termo só nos itens: resultados desses itens), com valor positivo, em compras sem valor excluído. O fornecedor é o CNPJ do vencedor (ni_fornecedor), que pode ser revendedor, e não o fabricante.")

h("6. Valores deflacionados")
p(f"IPCA, número-índice mensal, IBGE, SIDRA tabela 1737 (https://sidra.ibge.gov.br/tabela/1737), arquivo ipca_1737.csv. Mês-base: {MES_BASE_TXT} (último mês disponível, índice {fmt_num(ipca_base['indice_base'], 2)}). Regra: valor deflacionado = valor nominal × índice do mês-base ÷ índice do mês de publicação da compra, a mesma data usada para definir o ano. No período, o homologado limpo soma {bi(HOM)} em valores nominais e {bi(HOM_D)} em valores de {MES_BASE_CURTO}; nas seis categorias, {bi(V2A)} e {bi(V2A_D)}.")

h("7. Modelo de aquisição e tipo de vendedor")
p("O bloco 'Como o Estado contrata essas tecnologias e de quem depende' e os principais achados da aba de tecnologias críticas usam duas classificações adicionais, feitas sobre a mesma base do painel e a mesma classificação das seis categorias; nenhum valor já publicado foi recalculado. Os dados estão em pn_modelo_categoria_ano.csv, pn_vendedor_categoria_ano.csv, pn_marca_resultados.csv, pn_porte_compras.csv, pn_porte_valor.csv e pn_achados.csv.")
B.append(("h3", "Modelo de aquisição"))
p("Classificação de cada item do escopo das seis categorias pelo texto do item (descrição, descrição resumida, descrição detalhada e unidade de medida), em minúsculas e sem acentos. Classes mutuamente exclusivas, nesta precedência: 1 acréscimo a licença existente; 2 subscrição ou serviço (assinaturas, licenças por prazo, nuvem e certificados digitais); 3 licenciamento de direitos permanentes de uso (inclusive licença com software assurance); 4 suporte e manutenção de licença; 5 desenvolvimento e serviços técnicos (inclusive instalação, manutenção e garantia de equipamentos; treinamento não entra); 6 equipamentos e infraestrutura física (itens de material com função de hardware); 7 não identificado. O item recebe a primeira classe em que alguma expressão de inclusão aparece, nenhuma de exclusão aparece (no item ou, quando indicado, no objeto da compra) e o tipo de item exigido (material ou serviço) coincide.")
p("Licenciamento de direitos permanentes de uso: licença de software por prazo indeterminado, comprada uma vez. O nome segue o catálogo de compras do governo federal ('Licenciamento de Direitos Permanentes de Uso de Software').")
p("Valor por classe: o valor de cada compra × categoria pela regra de soma por categoria é repartido entre os itens do escopo na proporção do valor homologado nos resultados de cada item; sem resultado, na proporção do valor estimado do item; sem nenhum dos dois, o valor fica sem classe. As somas por categoria e ano reproduzem o gráfico 5.")
_grp = {}
for r in f2_dic:
    _grp.setdefault((int(r["ordem"]), r["classe"], r.get("sub") or "a", r["tipo"]), []).append(r["expressao"])
tab(["Classe", "Subregra", "Tipo", "Expressões (expressões regulares)"],
    [[f"{o}. {c}", sb, t, "; ".join(es)] for (o, c, sb, t), es in sorted(_grp.items())], "Dicionário do modelo de aquisição (versão final)")
B.append(("h3", "Revisão humana independente"))
p("Depois da verificação por amostragem, uma revisora independente julgou uma subamostra aleatória dos casos já verificados (semente f2_revisao_humana): 15 itens por classe aprovada do modelo de aquisição, 20 compras com menção a marca e 10 compras com vencedor classificado como empresa pública de TI, 120 casos ao todo, sem acesso aos julgamentos anteriores. "
  "Cada caso foi marcado como certo ou errado com o mesmo critério da verificação. Concordância = casos certos ÷ casos revisados; a classe é validada com pelo menos 80%.")
tab(["Grupo", "Classe", "Casos revisados", "Certo", "Errado", "Concordância", "Validada"],
    [[r["grupo"], r["classe"], r["linhas_revisadas"], r["certo"], r["errado"], fmt_pct(f(r["concordancia_pct"])), r["validada"]] for r in f2_rh],
    "Resultado da revisão humana por classe")
_nc = sum(r["concordam"] == "sim" for r in f2_conc)
p(f"Concordância entre a revisão humana e a verificação por amostragem, nos mesmos casos: {inteiro(_nc)} de {inteiro(len(f2_conc))} ({fmt_pct(100 * _nc / len(f2_conc))}). "
  "O número considera a correção de um caso da revisão humana (licença de software para cálculo do lucro real pelo prazo de um ano, marcada como errada na classe 3, porque licença por prazo é subscrição), registrada em fase2/validacao/ajustes_revisao_humana_v3.csv.")
p("O nome da classe 3 segue o catálogo de compras do governo federal em todas as tabelas. Nas fichas das amostras e na planilha da revisão humana, que já tinham julgamentos, "
  "o nome foi trocado uma única vez por fase2/scripts/f2_16_nome_classe_3.py, só na célula da classe, sem mudar julgamento, texto do PNCP ou número. "
  "Esse script não entra no pacote: numa execução nova, as fichas e a planilha já saem com o nome atual.")
p(f"Classes validadas: {', '.join(minus(r['classe']) for r in f2_rh if r['validada'] == 'sim')}. Não validadas: {', '.join(minus(r['classe']) for r in f2_rh if r['validada'] == 'não')}. "
  "Consequências: no gráfico 9 só aparecem separadamente acréscimo a licença existente, subscrição ou serviço e licenciamento de direitos permanentes de uso. As demais classes (desenvolvimento e serviços técnicos, equipamentos e infraestrutura física, suporte e manutenção de licença), os itens não identificados e as compras sem itens com valor formam o grupo 'Serviços técnicos, equipamentos e não identificados'. "
  "Os principais achados usam só classes validadas. "
  "Itens da amostra que estão fora da tecnologia da categoria em que a compra foi classificada estão listados, com o termo provável, em pendencias_dicionario_categorias.md; o dicionário das categorias não foi alterado.")
tab(["Classe", "Rodada", "Itens julgados", "Pertinentes", "Precisão"],
    [[r["classe"], r["rodada"], r["julgados"], r["pertinentes"], fmt_pct(f(r["precisao_pct"]))] for r in f2_prec], "Precisão do modelo de aquisição por rodada de verificação")
_sit_txt = "; ".join(r["classe"] + ": " + (fmt_pct(f(r["precisao_final_pct"])) if r["precisao_final_pct"] else r["situacao"]) for r in f2_sit)
p("Verificação por amostragem: 100 itens por classe (ou todos), sorteados por hash com semente fixa e julgados um a um; classe abaixo de 80% teve o dicionário ajustado e foi medida em nova amostra independente; classe que não atingisse 80% após dois ajustes ficaria fora do painel. "
  f"Situação final: {_sit_txt}. "
  f"A classe '{cls_fora['classe']}' ficou fora: {cls_fora['motivo']} No gráfico, seu valor entra em 'Serviços técnicos, equipamentos e não identificados'.")
B.append(("h3", "Tipo de vendedor e marcas"))
p("Base: valor homologado nos resultados das seis categorias (a mesma do gráfico 11). Marca citada: termos de 15 marcas no texto do item; quando o item não cita marca, valem as marcas citadas no objeto da compra. Tipo do vencedor, nesta precedência: fabricante direto (subsidiária brasileira da marca citada, identificada pelo nome empresarial nos resultados da base); empresa pública de TI (natureza jurídica de empresa pública ou sociedade de economia mista e atividade de tecnologia da informação); outra empresa estatal; revendedor ou integrador (marca citada e vencedor que não é o fabricante); demais fornecedores privados. No gráfico, o valor é somado por categoria; na tabela de marcas, cada resultado conta uma vez por marca, e o vendedor é a raiz do CNPJ.")
_gm = {}
for r in f2_dicm:
    _gm.setdefault(r["marca"], {"inclusao": [], "exclusao": []})[r["tipo"]].append(r["expressao"])
tab(["Marca", "Termos (expressões regulares)", "Exclusões"], [[m, "; ".join(d["inclusao"]), "; ".join(d["exclusao"]) or "nenhuma"] for m, d in _gm.items()], "Dicionário de marcas")
tab(["Marca", "Raiz do CNPJ", "Nome empresarial na base"], [[r["marca"], r["raiz_cnpj"], r["nomes_empresariais_na_base"]] for r in f2_fab], "CNPJs de fabricante direto")
tab(["Raiz do CNPJ", "Nome empresarial", "Tipo", "Compras", "Valor dos resultados"],
    [[r["raiz_cnpj"], r["nome_empresarial"], r["tipo_vendedor"], inteiro(int(r["compras"])), vauto(f(r["valor_resultados_soma_por_categoria"]))] for r in f2_estatais],
    "Empresas públicas de TI e outras estatais vencedoras nas seis categorias (valor somado por categoria)")
_pm = sum(r["pertinente"] == "sim" for r in f2_jm if r["grupo"] == "marca")
_nm = sum(r["grupo"] == "marca" for r in f2_jm)
_pp = sum(r["pertinente"] == "sim" for r in f2_jm if r["grupo"] != "marca")
_np = sum(r["grupo"] != "marca" for r in f2_jm)
p(f"Verificação por amostragem: {inteiro(_pm)} de {inteiro(_nm)} compras com menção a marca julgadas pertinentes ({fmt_pct(100 * _pm / _nm)}) e {inteiro(_pp)} de {inteiro(_np)} compras com vencedor classificado como empresa pública de TI ({fmt_pct(100 * _pp / _np)}).")
p("Porte: campo de porte do resultado no PNCP, com microempresa e empresa de pequeno porte numa classe única (micro ou pequena empresa) e demais empresas. Os cartões mostram a parcela das compras com vencedor identificado em que alguma empresa do porte venceu e a parcela do valor dos resultados (cada resultado uma vez).")
B.append(("h3", "Limitações destas classificações"))
ul(["Muitos itens trazem só o nome do código do catálogo; quando o texto livre contradiz o código, o item fica como não identificado.",
    "Marcas, tipos de vendedor e porte usam a base de resultados (valor homologado nos resultados), que não coincide com o total das seis categorias dos KPIs.",
    "A menção à marca na compra não prova o produto entregue: a marca pode aparecer como referência, compatibilidade ou exemplo.",
    "A identificação do fabricante direto depende do nome empresarial nos resultados; vencedores estrangeiros sem CNPJ não são identificados.",
    "A verificação por amostragem foi feita por um único revisor; a revisão humana independente cobriu 120 casos, e só as classes com concordância de pelo menos 80% aparecem separadamente.",
    "Os principais achados se referem ao período completo e às seis categorias e não mudam com os filtros. Cada número traz a sua base: total das seis categorias (cada compra uma vez), soma por categoria ou valor dos resultados; a lista está em pn_achados_numeros.csv. "
    + f"No achado 3, o valor vendido pelas empresas públicas de TI ({_an[('3', 'valor vendido por empresas públicas de TI (soma por categoria)')]}) e a participação no valor vendido nas seis categorias "
    + f"({_an[('3', 'participação no valor dos resultados (soma por categoria)')]}) usam a soma por categoria do valor dos resultados: uma venda em compra classificada em duas categorias conta nas duas. "
    + f"No achado 4, a base é a da aba de inteligência artificial: valor do acréscimo à licença repartido pelos itens ({_an[('4', 'valor do acréscimo à licença (aba de IA)')]}) "
    + f"e as {_an[('4', 'compras do acréscimo à licença (aba de IA)')]} compras em que ele está, o mesmo número nas duas abas. Na linha-resumo da aba de IA, o filtro Acréscimo à licença conta cada compra uma vez, na classe de maior valor; por isso mostra menos compras."])

h("8. Limitações")
ul(["Cobertura: o Colibri não informa se a base ComprasGov abrange todas as contratações publicadas no PNCP, e a comparação com o PNCP em Números não foi possível.",
    "Cobertura parcial antes de 2024: a publicação no PNCP só se tornou obrigatória para todas as contratações após 30/12/2023, fim da transição da Lei 14.133/2021. 2021 começa em " + f"{dmin:%d/%m} e 2026 termina em {dmax:%d/%m}.",
    "Valor homologado não equivale a gasto executado: em registro de preços, é o teto da ata; contratos de mais de um ano entram pelo valor integral no ano da compra.",
    "Fornecedor identificado pelo CNPJ do vencedor, que pode ser revendedor e não o fabricante da tecnologia.",
    f"País de origem do produto ou serviço preenchido em {fmt_pct(PAIS_PCT)} dos resultados das seis categorias ({inteiro(pais6['n_preenchido'])} de {inteiro(pais6['n_resultados'])}).",
    "Classificação por palavras-chave: sujeita a falsos positivos e negativos, medidos pela verificação por amostragem.",
    "Recorte tecnológico: as seis categorias cobrem as camadas de nuvem, plataformas de software, dados e inteligência artificial, segurança cibernética e identidade digital. Não incluem camadas de base que os documentos de referência também tratam como críticas, como semicondutores, redes e conectividade e dispositivos (Comissão Europeia, 2023; Bria, Timmers e Gernone, 2025). As referências utilizadas para delimitar as categorias são europeias.",
    "O painel mede a compra de tecnologias críticas para a soberania digital, não o grau de soberania do Estado; a base não informa a origem da tecnologia nem o local de hospedagem dos dados.",
    "Instrumentos de política: os campos de margem de preferência e de PPB estão sempre preenchidos com verdadeiro ou falso; não é possível distinguir 'não se aplica' de 'não informado'.",
    f"No licenciamento de direitos permanentes de uso, {fmt_pct(f(_lpc['pct_so_codigo_catalogo']))} do valor ({mi(f(_lpc['valor_so_codigo_catalogo']))} de {mi(f(_lpc['valor_classe_total']))}) foi identificado só pelo nome do código do catálogo ('Direitos Permanentes de Uso'). Há compras com esse código que descrevem licenças por prazo; o valor da classe é indicativo.",
    "Margem de preferência por NCM: o NCM vem do item quando informado; a faixa superior usa o tradutor CATMAT→NCM do Colibri, que combina classificação humana e sugestão por IA.",
    f"O campo de porte da fonte registra EPP em apenas {fmt_pct(_pf['EPP'])} dos resultados da base, contra {fmt_pct(_pf['ME'])} para ME, o que indica que a distinção entre microempresa e empresa de pequeno porte não é confiável; o painel apresenta as duas em uma classe única."])
tab(["Porte registrado no resultado", "Resultados", "% dos resultados"],
    [[r["porte_fornecedor_nome"], inteiro(int(r["resultados"])), fmt_pct(f(r["pct_dos_resultados"]))] for r in _pfreq],
    "Frequência do campo de porte do fornecedor na base inteira (todos os resultados)")

h("9. Aba Inteligência artificial")
_irec = ler(TP + "ia_reconciliacao.csv")
B.append(("h3", "Base da aba"))
p("A aba reúne três conjuntos de compras de 2021 a 2026, na mesma base limpa do painel; cada compra entra uma vez. "
  "A: compras da categoria Inteligência artificial do painel (mesmo dicionário e mesma regra de soma por categoria). "
  "B: compras de capacitação em IA que o dicionário da categoria exclui: termo de inclusão da categoria IA e termo de capacitação no mesmo texto (objeto e informação complementar, ou texto do item); "
  "valor pela regra do painel (compra inteira quando o texto da compra casa; só os resultados dos itens que casam, quando só os itens casam). "
  "C: compras com assistente de IA acoplado a licença existente (itens da classe 'acréscimo a licença existente' da fase 2 cujo texto cita copilot, gemini ou duet ai) que não estão em A nem em B; "
  "valor desses itens, cada item uma vez. Valores deflacionados pelo fator de cada compra (IPCA, mesmo mês-base do painel).")
tab(["Conjunto", "Compras", "Valor"], [[r["linha"], inteiro(int(r["compras"])), mi(f(r["valor_nominal"]))] for r in _irec], "Reconciliação da base da aba com a categoria IA do painel (ia_reconciliacao.csv)")
B.append(("h3", "Valor por classe e contagem de compras"))
p("O valor de cada compra é repartido entre as classes pelos itens, a mesma regra do gráfico 9: nas compras da categoria IA, o valor da compra na categoria é repartido entre os itens na proporção "
  "do valor nos resultados (sem resultado, do valor estimado do item); a classe Acréscimo à licença recebe só os itens com assistente acoplado e os demais itens ficam com a classe que o dicionário indica "
  "para a compra. Para contar compras, cada compra entra uma vez, na classe em que tem mais valor. Tecnologia de IA = Acréscimo à licença, Solução de IA (exclusiva ou em pacote) e Outros; "
  "Capacitação em IA = classe Capacitação, que não faz parte do total das tecnologias críticas para a soberania digital. Fornecedores, órgãos, o gráfico 12 e a tabela 5 usam o valor homologado "
  "nos resultados (compras com vencedor identificado), a mesma base do gráfico 11.")
B.append(("h3", "Classes e dicionário"))
p("Classes, na ordem de precedência: Capacitação; Acréscimo à licença; Solução de IA (exclusiva ou em pacote), soma das classes IA exclusiva e Pacote multi-software do dicionário; Outros. "
  "O texto é convertido para minúsculas e sem acentos; as expressões são expressões regulares. Versões do dicionário: 1 (inicial), 2 e 3 (ajustes depois das amostras 1 e 2), "
  "4 (regra das fundações de apoio, depois da verificação por valor). Arquivo: tabelas_painel_v3/dicionario_ia_classes.csv (versões anteriores em dicionario_ia_classes_v1.csv a _v3.csv).")
tab(["Classe", "Tipo", "Expressão", "Justificativa"], [[r["classe"], r["tipo"], r["termo"], r["justificativa"]] for r in ler(TP + "dicionario_ia_classes.csv")],
    "Dicionário das classes da aba Inteligência artificial (versão final)")
B.append(("h3", "Verificação das classes"))
_ipc = ler(TP + "ia_precisao_classes.csv")
_fin = {r["classe"]: r for r in _ipc if r["rodada_final"] == "sim"}
p("A classificação da aba de Inteligência artificial foi verificada por amostragem, com 20 compras por classe em cada rodada, sorteadas por hash com semente fixa e sem repetir compras entre rodadas; "
  "a classe é validada com pelo menos 80% de compras pertinentes. O dicionário teve dois ajustes (versões 2 e 3). As classes IA exclusiva e Pacote multi-software não chegaram a 80% em nenhuma rodada "
  f"depois dos ajustes ({fmt_pct(f(next(r for r in _ipc if r['classe'] == 'IA exclusiva' and r['rodada'] == 'ia_a3')['precisao_pct']))} e "
  f"{fmt_pct(f(next(r for r in _ipc if r['classe'] == 'Pacote multi-software' and r['rodada'] == 'ia_a3')['precisao_pct']))} na amostra 3). "
  "A maior parte dos erros estava na fronteira entre as duas, que é ambígua: um chatbot de atendimento por WhatsApp, por exemplo, pode ser a própria solução de IA ou um componente de uma plataforma de atendimento. "
  "Por isso as duas classes foram somadas em 'Solução de IA (exclusiva ou em pacote)', sem nova mudança no dicionário, e a classe somada foi medida numa amostra nova (amostra 4): "
  f"{_fin['Solução de IA (exclusiva ou em pacote)']['pertinentes']} de {_fin['Solução de IA (exclusiva ou em pacote)']['compras_julgadas']} compras pertinentes "
  f"({fmt_pct(f(_fin['Solução de IA (exclusiva ou em pacote)']['precisao_pct']))}). Classes finais: Capacitação, Acréscimo à licença, Solução de IA (exclusiva ou em pacote) e Outros.")
_irh_all = ler("validacao_ia/resultado_revisao_humana_ia.csv")
_irh, _irh_tot = [r for r in _irh_all if r["classe"] in IA_CLS], next(r for r in _irh_all if r["classe"] == "Total")
_irh_val = next(r for r in _irh_all if r["classe"].startswith("Capacitação: verificação por valor"))
tab(["Classe", "Amostra", "Dicionário", "Compras julgadas", "Pertinentes", "Precisão", "Rodada final"],
    [[r["classe"], r["rodada"].replace("ia_a", "amostra "), r["dicionario"], r["compras_julgadas"], r["pertinentes"], fmt_pct(f(r["precisao_pct"])), r["rodada_final"]] for r in _ipc],
    "Verificação das classes da aba Inteligência artificial, por amostra")
p(f"Revisão humana independente: {inteiro(int(_irh_tot['casos_revisados']))} compras já verificadas, sorteadas por hash (semente ia_revisao_humana): 10 de Capacitação, 10 de Acréscimo à licença, "
  "20 de Solução de IA (exclusiva ou em pacote) e 10 de Outros, julgadas sem acesso aos julgamentos anteriores, com o mesmo critério. "
  f"Concordância com a verificação por amostragem: {inteiro(int(_irh_tot['concordancia_entre_revisoes']))} de {inteiro(int(_irh_tot['casos_revisados']))} "
  f"({fmt_pct(f(_irh_tot['concordancia_entre_revisoes_pct']))}). Todas as classes passaram de 80% nas duas verificações; o dicionário não mudou depois da revisão humana. "
  "As divergências, com o motivo de cada uma, estão em validacao_ia/divergencias_revisao_humana_ia.csv.")
tab(["Classe", "Casos revisados", "Certo", "Errado", "Concordância", "Validada", "Concordância entre revisões"],
    [[r["classe"], r["casos_revisados"], r["certo"], r["errado"], fmt_pct(f(r["concordancia_pct"])), r["validada"], f"{r['concordancia_entre_revisoes']} de {r['casos_revisados']}"] for r in _irh],
    "Revisão humana da classificação da aba Inteligência artificial")
_fund = ler("validacao_ia/exclusao_fundacoes_apoio.csv")
_rep = ler("validacao_ia/capacitacao_itens_repartidos.csv")
p(f"Verificação por valor da classe Capacitação: as 10 compras de maior valor da classe foram revisadas à mão (validacao_ia/capacitacao_maiores_valores_revisadas.csv). "
  f"{inteiro(int(_irh_val['certo']))} de {inteiro(int(_irh_val['casos_revisados']))} estavam certas; {mi(f(_irh_val['valor_em_compras_erradas']))} dos {mi(f(_irh_val['valor_revisado']))} dessas compras "
  f"({fmt_pct(f(_irh_val['pct_do_valor_em_compras_erradas']))}) estavam em compras erradas, todas contratos de gestão administrativa e financeira com fundações de apoio. Daí as duas regras abaixo.")
p(f"Regra das fundações de apoio (versão 4 do dicionário das classes): sai da classe Capacitação e da base da aba a compra cujo objeto contrata fundação de apoio para gestão administrativa, financeira "
  f"ou operacional de curso ou projeto da instituição, porque não é compra de capacitação nem de tecnologia de IA. A regra vale para toda a base: {inteiro(len(_fund))} compras, "
  f"{mi(sum(f(r['valor_nominal']) for r in _fund))}, listadas em validacao_ia/exclusao_fundacoes_apoio.csv. Inscrição ou participação de servidores em curso ou evento continua como capacitação, "
  "mesmo com fundação de apoio no texto.")
p(f"Revisão humana da lista: a equipe de pesquisa revisou à mão as {inteiro(len(_fund))} compras excluídas pela regra das fundações de apoio, à procura de curso para os servidores do órgão. "
  f"Nenhuma é curso; a exclusão foi confirmada nas {inteiro(sum(r['revisão humana'] == 'confirmada' for r in _fund))} compras (coluna \"revisão humana\" de validacao_ia/exclusao_fundacoes_apoio.csv).")
p(f"Regra dos itens na capacitação: quando a compra classificada pelo objeto tem itens identificáveis (algum item com termo de IA e algum sem), conta só a parte dos itens com termo de IA, "
  f"repartida pelo valor dos resultados de cada item (sem resultado, pelo valor estimado), a mesma regra do gráfico 9. {inteiro(len(_rep))} compras mudaram de valor; o efeito é de "
  f"{mi(sum(f(r['valor_depois']) - f(r['valor_antes']) for r in _rep))} (validacao_ia/capacitacao_itens_repartidos.csv).")

B.append(("h3", "Tipos de objeto (O que vendeu)"))
p("Cada compra recebe um tipo de objeto pelo texto do objeto, da informação complementar e dos itens com IA, na ordem da tabela; compras de capacitação ficam em 'Outros objetos'. "
  "Tipo com menos de 3 compras vai para 'Outras soluções de IA', salvo as marcas de IA (Microsoft Copilot, Google Gemini, ChatGPT/OpenAI, Claude/Anthropic, Perplexity e Manus), que aparecem sempre com nome próprio.")
tab(["Ordem", "Tipo de objeto", "Expressão", "Justificativa"], [[r["ordem"], r["objeto"], r["termo"], r["justificativa"]] for r in ler(TP + "dicionario_ia_tipos.csv")],
    "Dicionário dos tipos de objeto (dicionario_ia_tipos.csv)")
B.append(("h3", "Marcas de IA citadas"))
p("A tabela 6 busca a marca no texto do item, no objeto e na informação complementar de todas as compras do painel (não só da base da aba), sem corte mínimo de compras; termo de exclusão "
  "no mesmo texto descarta a menção. Compras de capacitação (na base da aba, classe Capacitação; fora dela, objeto de capacitação) aparecem separadas. Valor das compras de produto: "
  "valor homologado da compra quando a marca está no objeto ou na informação complementar; senão, resultados dos itens que a citam. As menções estão listadas em ia_marcas_mencoes.csv.")
tab(["Marca", "Tipo", "Expressão", "Justificativa"], [[r["marca"], r["tipo"], r["termo"], r["justificativa"]] for r in ler(TP + "dicionario_ia_marcas.csv")],
    "Dicionário das marcas de IA (dicionario_ia_marcas.csv)")
B.append(("h3", "Reconciliação do Copilot e do acréscimo à licença"))
tab(["Conjunto", "Compras", "Valor", "Base de valor", "Motivo da diferença"],
    [[r["conjunto"], inteiro(int(r["compras"])), mi(f(r["valor_nominal"])), r["base_de_valor"], r["motivo"]] for r in ler(TP + "ia_reconciliacao_copilot.csv")],
    "Achado 4 da aba de tecnologias críticas, classe Acréscimo, tipos e marca Copilot (ia_reconciliacao_copilot.csv)")
B.append(("h3", "Limitações da aba"))
ul(["Classificação por palavras-chave: a verificação por amostragem e a revisão humana medem a precisão das classes, não a cobertura; compras de IA sem termo de IA no texto ficam de fora.",
    "A fronteira entre IA exclusiva e pacote multi-software é ambígua; por isso as duas classes foram somadas.",
    "Outros reúne sobretudo equipamentos com IA embarcada e contratações mais amplas que citam IA nos itens; parte delas não é compra de tecnologia de IA (por exemplo, manutenção de CFTV apontada na revisão humana).",
    "A menção a uma marca não comprova o produto entregue; a tabela de marcas cobre toda a base do painel.",
    "O valor da capacitação em IA depende da separação dos itens; quando a compra não tem itens identificáveis, entra o valor homologado inteiro."])

h("Trilha dos números")
p("Do total extraído até o valor exibido em cada KPI, linha por linha.")
trilha = [
    ["1", "parquet/compras.parquet", "extração (Colibri)", "todas as versões das compras", "-", inteiro(n_extr), "-", "-"],
    ["2", "parquet/compras.parquet", "etapa3_base_limpa.sql", "vigentes (is_current) e únicas por id_compra", inteiro(n_extr), inteiro(n_base_limpa), "-", bi(bruto_completa)],
    ["3", "base_limpa.parquet", "p0_14_duplicidades.sql, p0_15_base_sem_duplicidades.sql", "remoção de republicações (cinco campos e mesmos vencedores)", inteiro(n_base_limpa), inteiro(N_PUB), bi(bruto_completa), bi(BRUTO)],
    ["4", "tabela bl (p0.duckdb)", "p1_01_dados_painel.sql", "KPI compras publicadas", inteiro(N_PUB), inteiro(N_PUB), "-", "-"],
]
k = 5
acum = BRUTO
for m, v in sorted(motivos.items(), key=lambda kv: -kv[1][1]):
    trilha.append([str(k), "base_limpa.parquet, auditoria_revisao_manual_proposta.csv", "p0_01_totais_homologados.sql",
                   ROT_MOT[m] + ": valor excluído", "-", f"{inteiro(v[0])} compras", bi(acum), bi(acum - v[1])])
    acum -= v[1]
    k += 1
trilha.append([str(k), "tabela bl", "p1_01_dados_painel.sql", "KPI valor homologado total (limpo)", "-", "-", bi(acum), bi(HOM)])
trilha.append([str(k + 1), "tabelas cat_compra, item_match (p0_02)", "p0_07_soberania.sql", "compras em ao menos uma categoria", inteiro(N_PUB), inteiro(N_SOB), bi(HOM), bi(V2A)])
trilha.append([str(k + 2), "compra_unica (p0_07)", "p1_01_dados_painel.sql", "KPI tecnologias críticas para a soberania digital (total das seis categorias)", "-", "-", "-", bi(V2A)])
trilha.append([str(k + 3), "pn_soberania_tres_regras.csv", "p1_02_painel.py", "KPI participação = soberania ÷ homologado total", "-", "-", "-", fmt_pct(PART)])
tab(["Passo", "Arquivo de entrada", "Script", "Regra", "Registros antes", "Registros depois", "Valor antes", "Valor depois"], trilha)
assert abs(acum - HOM) < 1e3, (acum, HOM)
with open(TP + "pn_trilha_numeros.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["passo", "arquivo_entrada", "script", "regra", "registros_antes", "registros_depois", "valor_antes", "valor_depois"])
    w.writerows(trilha)

h("Três regras de soma das tecnologias críticas para a soberania digital")
tab(["Regra", "Valor", "Uso no painel"], [
    ["Total das seis categorias (cada compra uma vez)", bi(V2A), "KPIs, participação e gráfico 6"],
    ["Soma por categoria", bi(V2B), "gráficos e tabelas por categoria"],
    ["Compra inteira em cada categoria identificada", bi(V2C), "só nesta metodologia"]])

h("Verificações de qualidade da base")
p(f"Duplicidades. O critério inicial considerava duplicidade a coincidência de cinco campos: CNPJ do órgão, unidade, número do processo, objeto normalizado e valor homologado. Aplicado literalmente, ele removeria {inteiro(n_lit)} compras (R$ {fmt_escala(bruto_lit / 1e9)} bi de homologado bruto). A regra adotada pela equipe de pesquisa exige também o mesmo conjunto de fornecedores vencedores, porque credenciamentos geram contratações com mesmo processo, objeto e valor e fornecedores distintos (por exemplo, o credenciamento de pipeiros da Operação Carro-Pipa, em que cada compra tem um fornecedor diferente). Com a condição adicional foram removidas {inteiro(n_dup)} compras ({bi(bruto_dup)} de homologado bruto e {bi(limpo_dup)} de homologado limpo), das quais {inteiro(n_dup6)} nas seis categorias ({mi(limpo_dup6)} de homologado limpo). Casos com os mesmos campos exceto o número do processo ({inteiro(len({r['grupo'] for r in dup_proc}))} grupos, {inteiro(len(dup_proc))} compras) foram mantidos e listados em possiveis_duplicidades_processo_diferente.csv.")
p("Remoção indevida pelo ajuste do dicionário: ver seção 3 (taxas por categoria, todas abaixo de 20%).")
fora = mg("elegibilidade", "fora da elegibilidade")
dentro = mg("elegibilidade", "dentro da elegibilidade")
antes = mg("periodo", "antes de 01/09/2024")
p(f"Margem de preferência. O valor homologado com margem aplicada em toda a base soma {mi(margem_tot['valor_margem_aplicada'])} ({inteiro(margem_tot['itens'])} itens), todo em compras publicadas a partir de 01/09/2024" + ("" if antes is None else f" (antes: {mi(antes['valor_margem_aplicada'])})") + f". Desse valor, {mi(dentro['valor_margem_aplicada'])} estão em itens com NCM coberto por resolução CICS vigente na data da compra e {mi(fora['valor_margem_aplicada'])} fora dessa cobertura. Causas identificadas nos dados: " +
  "; ".join(f"{r['causa'].replace('resolucao', 'resolução').replace('vigencia', 'vigência')} ({r['origem_ncm']}), {mi(r['valor_margem_aplicada'])}" for r in mg_causa) +
  ". Como a diferença tem causa identificada, o painel usa como número principal o valor em itens com NCM informado no item e, como limite superior, o valor com NCM do item mais o tradutor CATMAT→NCM.")
tab(["Indicador (seis categorias, 2021 a 2026)", "Valor"], [
    ["Valor homologado em itens de material com NCM coberto por margem de preferência (resoluções CICS vigentes na data da compra), NCM informado no item", mi1(ncm_tot["ncm_item_nominal"])],
    ["Mesmo indicador com NCM do item e, na falta, do tradutor CATMAT→NCM (limite superior)", mi1(ncm_tot["ncm_item_tradutor_nominal"])],
    ["Valor dos itens de material com margem de preferência efetivamente aplicada", mi1(ncm_tot["margem_aplicada_material_nominal"])],
    ["Valor das compras com ao menos um resultado com margem aplicada (total das seis categorias)", mi(instr_tot["margem_aplicada_nominal"])]])
p(f"Os dois últimos valores medem coisas diferentes: {mi(instr_tot['margem_aplicada_nominal'])} é o valor homologado das compras em que ao menos um resultado teve a margem aplicada (a compra inteira ou os itens da categoria, pela regra de soma); {mi1(ncm_tot['margem_aplicada_material_nominal'])} é o valor dos próprios itens com a margem aplicada.")

h("Critérios de apresentação")
ul(["O gráfico 4 mostra todas as modalidades presentes na base, sem agrupar; esfera e poder não informados aparecem em azul-claro, por último.",
    "Anos de cobertura parcial: 2021 e 2022 em tom mais claro, com a marcação 'cobertura parcial do PNCP'; 2026 em tom mais claro, com a marcação 'parcial, até 24/05'.",
    "Esfera: códigos fora de F, E, M e D (N e o valor 'false') aparecem como Esfera não informada; poder fora de E, L e J, como Poder não informado.",
    "Tabela 2 (órgãos compradores): logo abaixo do gráfico 11, com o mesmo valor dos resultados e reativa à seleção no gráfico; mostra até 50 órgãos por categoria, em ordem de valor. Tabela 3 (concentração): uma linha por categoria e ano, porque os índices de concentração não se somam entre anos. Tabela 4 (perfil): uma linha por categoria para o período filtrado; a mediana usa todas as compras do período e os percentuais são ponderados pelo valor. Os dados por ano estão no CSV de download da aba.",
    "Categorias em ordem de valor homologado de 2021 a 2026 pela regra de soma por categoria, em gráficos, legendas, cartões, filtros e tabelas.",
    "Gráfico 11 (Sankey) e tabelas 2 e 3 usam o valor dos resultados (vencedores), a única fonte que identifica o fornecedor; os demais gráficos por categoria usam a regra de soma por categoria. No Sankey, os 10 maiores fornecedores e os 10 maiores órgãos do recorte aparecem nominalmente; os demais são agrupados em Demais. O clique numa categoria equivale ao filtro de categoria; o clique num fornecedor ou órgão refaz o diagrama só com os fluxos desse nó. Os valores dos tooltips saem da tabela fornecedor × categoria × órgão (pn_fluxo.csv).",
    "Indicadores de instrumentos de política (cartões numéricos no bloco 'O Estado usa o poder de compra a favor da oferta nacional?'): margem prevista e PPB são marcados na compra quando algum item do escopo da categoria tem o campo verdadeiro; margem aplicada, quando algum resultado desse escopo tem aplicacao_margem_preferencia verdadeiro. O percentual é o valor dessas compras sobre o total das seis categorias ou o valor da categoria filtrada. O indicador por NCM aparece em cartão separado, em reais. Gráficos e tabelas são numerados em sequência, pela ordem de aparição: gráficos 1 a 11 e tabelas 1 a 4 no painel, tabela 5 nesta metodologia; os instrumentos de política e o porte são apresentados como indicadores, não como gráfico.",
    "Aba Tecnologias críticas para a soberania digital: a frase de abertura e os quatro KPIs respondem aos filtros de ano e de categoria. Compras e valor seguem o total das seis categorias (ou o valor da categoria, com uma categoria filtrada); fornecedores vencedores e órgãos compradores são contados uma única vez no recorte, na mesma base do gráfico 11 (resultados com valor positivo; fornecedor pelo CNPJ do vencedor; órgão pelo nome do órgão comprador). A segunda frase da abertura e os KPIs de fornecedores e órgãos consideram apenas as compras com vencedor identificado (resultado vencedor publicado). Acima do gráfico 11, a linha-resumo mostra as compras com vencedor identificado, os fornecedores, os órgãos e o valor dos fluxos exibidos, na base dos resultados e somado por categoria (uma compra em mais de uma categoria entra em cada uma), e acompanha o filtro e os cliques em categoria, fornecedor ou órgão (pn_fluxo.csv e pn_fluxo_compras.csv).",
    "Bloco 'Como o Estado contrata essas tecnologias e de quem depende' (gráficos 9 e 10, tabela 1 e indicadores de porte): responde aos filtros de ano e de categoria; o gráfico 9 usa a regra de soma por categoria, e o gráfico 10, a tabela 1 e os indicadores de porte usam o valor dos resultados (ver seção 7). Os principais achados, logo abaixo dos KPIs, refletem o período completo e não mudam com os filtros.",
    "Encomenda tecnológica e CPSI: busca por menção explícita no amparo legal (nome e descrição), na modalidade e no objeto.",
    "Precisão exibida nos cartões: amostra final de cada categoria, sem as compras removidas como republicação.",
    "Formatação: valores em bilhões somente a partir de R$ 1 bi (abaixo disso, em milhões); valores em escala (bi, mi, mil) com uma casa decimal abaixo de 100 e nenhuma a partir de 100, na unidade adequada ao valor; percentuais com uma casa abaixo de 10, nenhuma a partir de 10, três abaixo de 0,1 e '< 0,001%' abaixo disso; contagens inteiras; ',0' é omitido. O indicador de margem de preferência por NCM é exibido em R$ milhões com uma casa decimal. Exemplos em reais por R$ 100, com centavos.",
    "Arredondamento: meio para cima, sobre a representação decimal mais curta do valor calculado (a mesma regra do navegador); nenhum número é digitado."])


def md_inline(t):
    return t


NUMERICO = re.compile(r"^(R\$ )?(< )?-?[\d.]+(,\d+)?(%| bi| mi| mil| compras)?$")


def numerico(x):
    return bool(NUMERICO.match(str(x).strip()))


def quebra(x):  # texto: permite quebra de linha apos "_", "/" e "." (nomes de arquivo), nunca no meio de numeros
    return re.sub(r"([_/.])(?=[A-Za-z])", r"\g<1><wbr>", html.escape(str(x)))


def render_html(blocos):
    out = []
    for tipo, c in blocos:
        if tipo == "downloads":
            out.append("<!--__DOWNLOADS__-->")
        elif tipo in ("h2", "h3"):
            out.append(f"<{tipo}>{html.escape(c)}</{tipo}>")
        elif tipo == "p":
            out.append(f"<p>{html.escape(c)}</p>")
        elif tipo == "ul":
            out.append("<ul>" + "".join(f"<li>{html.escape(i)}</li>" for i in c) + "</ul>")
        elif tipo == "table":
            titulo, cab, linhas = c
            t = ""
            if titulo:
                partes = titulo.split(". ", 1) if titulo.startswith("TABELA") else [None, titulo]
                if partes[0]:
                    t = f"<div class='tit-graf'><div class='tg1'>{html.escape(partes[0])}</div><div class='tg2'>{html.escape(partes[1])}</div></div>"
                else:
                    t = f"<h3>{html.escape(titulo)}</h3>"
            # coluna numerica: todas as celulas preenchidas (diferentes de "-") sao numeros
            ncol = [all(numerico(l[k]) for l in linhas if str(l[k]).strip() != "-") and any(numerico(l[k]) for l in linhas) for k in range(len(cab))]
            cl = lambda k, x: " class='n'" if ncol[k] or numerico(x) else ""
            out.append(t + "<div class='tabela-wrap'><table class='tabela' data-tabela='" + html.escape(titulo or "") + "'><thead><tr>" +
                       "".join(f"<th{' class=n' if ncol[k] else ''}>{html.escape(x)}</th>" for k, x in enumerate(cab)) + "</tr></thead><tbody>" +
                       "".join("<tr>" + "".join(f"<td{cl(k, x)}>{quebra(x) if not cl(k, x) else html.escape(str(x))}</td>" for k, x in enumerate(l)) + "</tr>" for l in linhas) +
                       "</tbody></table></div>")
    return "\n".join(out)


def render_md(blocos):
    out = ["# Metodologia do painel de compras públicas de tecnologias críticas para a soberania digital", "",
           f"Gerado por `scripts_painel_v3/p1_02_painel.py` em {HOJE:%d/%m/%Y}, a partir das tabelas agregadas. "
           "Os números coincidem com os do painel `painel_soberania_digital_v3.html` (conferência em `conferencia_numeros_v3.csv`).", ""]
    for tipo, c in blocos:
        if tipo == "downloads":
            out += ["## Downloads", "",
                    "- Scripts executados, em ordem, com LEIAME.txt: `pacote_downloads_v3.zip`, pasta `scripts/`.",
                    "- Tabelas agregadas que alimentam cada gráfico e tabela: `pacote_downloads_v3.zip`, pasta `tabelas_agregadas/`.",
                    "- Dados brutos: https://gestaogovbr.github.io/colibri/ . Extração: `COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__compras) TO 'compras.parquet' (FORMAT parquet)`; o mesmo para `__itens` e `__resultados`. Os Parquet não fazem parte do pacote.", ""]
        elif tipo == "h2":
            out += [f"## {c}", ""]
        elif tipo == "h3":
            out += [f"### {c}", ""]
        elif tipo == "p":
            out += [c, ""]
        elif tipo == "ul":
            out += [f"- {i}" for i in c] + [""]
        elif tipo == "table":
            titulo, cab, linhas = c
            if titulo:
                out += [f"**{titulo}**", ""]
            out += ["| " + " | ".join(cab) + " |", "|" + "---|" * len(cab)]
            out += ["| " + " | ".join(str(x).replace("|", "/") for x in l) + " |" for l in linhas] + [""]
    return "\n".join(out)


# ordem de execucao dos scripts (LEIAME e metodologia)
SCRIPTS = [
    ("etapa2_agregacao.py", "Deduplicação de compras e regras automáticas de valor suspeito (etapa2_compras_auditadas.parquet)."),
    ("etapa3_dedup_compras_extra.sql", "Deduplicação complementar de compras (colunas extras)."),
    ("etapa3_dedup_itens.sql", "Deduplicação de itens (itens_dedup.parquet)."),
    ("etapa3_dedup_resultados.sql", "Deduplicação de resultados (resultados_dedup.parquet)."),
    ("etapa3_base_limpa.sql", "Base limpa de compras com regras de valor suspeito (base_limpa.parquet)."),
    ("scripts_parte0/p0_01_totais_homologados.sql", "Recálculo do valor limpo a partir das flags e da revisão manual, e controles."),
    ("scripts_parte0/p0_14_duplicidades.sql", "Identificação de republicações."),
    ("scripts_parte0/p0_15_base_sem_duplicidades.sql", "Base de análise sem republicações (tabela bl)."),
    ("scripts_parte0/p0_05_dicionario_v2.py", "Geração do dicionário final a partir do original."),
    ("scripts_parte0/p0_02_classificacao.sql", "Classificação de compras e itens nas seis categorias."),
    ("scripts_parte0/p0_16_duplicidades_resumo.sql", "Resumo das republicações por ano e nas seis categorias."),
    ("scripts_parte0/p0_03_fichas_validacao.sql", "Fichas da amostra 1 de validação."),
    ("scripts_parte0/p0_04_precisao.py", "Precisão da amostra 1."),
    ("scripts_parte0/p0_06_margem_colibri_listar.py", "Lista das tabelas de margem no Colibri (somente leitura)."),
    ("scripts_parte0/p0_06b_margem_colibri_exportar.py", "Cópia das tabelas de margem e do tradutor CATMAT→NCM."),
    ("scripts_parte0/p0_07_soberania.sql", "Valores de soberania (três regras), robustez e país de origem."),
    ("scripts_parte0/p0_07b_controle_dicionario_original.py", "Controle com o dicionário original."),
    ("scripts_parte0/p0_08_margem_preferencia.sql", "Margem de preferência por NCM."),
    ("scripts_parte0/p0_09_amostra2.sql", "Amostra 2 de validação."),
    ("scripts_parte0/p0_10_amostra3.sql", "Amostra 3 de validação."),
    ("scripts_parte0/p0_11_amostra4.sql", "Amostra 4 de validação."),
    ("scripts_parte0/p0_12_consolidar_validacao.py", "Consolidação da precisão por categoria."),
    ("scripts_parte0/p0_17_fichas_remocao.sql", "Sorteio das compras removidas pelo ajuste do dicionário."),
    ("scripts_parte0/p0_18_remocao_indevida.py", "Julgamentos e taxa de remoção indevida."),
    ("scripts_parte0/p0_19_margem_decomposicao.sql", "Decomposição do valor com margem aplicada."),
    ("scripts_painel_v3/p1_00_dicionario_legivel.py", "Palavras-chave em linguagem comum, idênticas ao dicionário."),
    ("scripts_painel_v3/p1_01_dados_painel.sql", "Tabelas agregadas do painel."),
    ("fase2/scripts/f2_01_base_escopo.py", "Base das classificações de modelo de aquisição e tipo de vendedor (banco do painel aberto somente para leitura)."),
    ("fase2/scripts/f2_02_diagnostico_campos.py", "Existência e preenchimento dos campos usados nas classificações."),
    ("fase2/scripts/f2_03_dicionario_modelo_v1.py", "Dicionário do modelo de aquisição, versão 1."),
    ("fase2/scripts/f2_04_classifica_modelo.py", "Classificação dos itens (argumentos: dicionário e rótulo; executado com v1, v2 e v3)."),
    ("fase2/scripts/f2_05_amostra_modelo.py", "Amostras de verificação do modelo de aquisição (sementes f2_modelo_a1, a2 e a3)."),
    ("fase2/validacao/julgamentos_modelo_f2_modelo_a1.py", "Julgamentos da amostra 1."),
    ("fase2/scripts/f2_03b_dicionario_modelo_v2.py", "Dicionário do modelo de aquisição, versão 2."),
    ("fase2/validacao/julgamentos_modelo_f2_modelo_a2.py", "Julgamentos da amostra 2."),
    ("fase2/scripts/f2_03c_dicionario_modelo_v3.py", "Dicionário do modelo de aquisição, versão 3 (final)."),
    ("fase2/validacao/julgamentos_modelo_f2_modelo_a3.py", "Julgamentos da amostra 3."),
    ("fase2/scripts/f2_06_precisao_modelo.py", "Precisão por classe e situação final."),
    ("fase2/scripts/f2_07_modelo_valores.py", "Valor por modelo de aquisição e categoria."),
    ("fase2/scripts/f2_08_marcas_vendedores.py", "Marcas citadas, fabricantes, empresas públicas de TI e tipo de vendedor."),
    ("fase2/scripts/f2_09_amostra_marcas.py", "Amostra de verificação de marca e tipo de vendedor (semente f2_marca_a1)."),
    ("fase2/validacao/julgamentos_marcas_f2_marca_a1.py", "Julgamentos da amostra de marcas."),
    ("fase2/scripts/f2_10_porte.py", "Compras e valor por porte do vencedor."),
    ("fase2/scripts/f2_11_achados.py", "Principais achados e números de origem."),
    ("fase2/scripts/f2_14_revisao_humana.py", "Planilha da revisão humana independente (120 casos)."),
    ("fase2/scripts/f2_15_revisao_humana_resultado.py", "Resultado da revisão humana, concordância entre revisões e pendências do dicionário das categorias."),
    ("scripts_painel_v3/p1_06_ia_base.py", "Base, classes, tipos de objeto e resultados da aba de inteligência artificial (com a semente como argumento, gera as fichas de verificação: ia_a1 a ia_a4)."),
    ("validacao_ia/julgamentos_ia_a1.py", "Julgamentos da amostra 1 das classes de IA."),
    ("validacao_ia/julgamentos_ia_a2.py", "Julgamentos da amostra 2 das classes de IA."),
    ("validacao_ia/julgamentos_ia_a3.py", "Julgamentos da amostra 3 das classes de IA."),
    ("validacao_ia/julgamentos_ia_a4.py", "Julgamentos da amostra 4 (classe somada Solução de IA)."),
    ("scripts_painel_v3/p1_07_ia_validacao_marcas.py", "Precisão das classes de IA, marcas de IA citadas, planilha de revisão humana (gerada uma vez; depois da revisão, fica congelada e não é regravada) e reconciliação do Copilot."),
    ("validacao_ia/capacitacao_maiores_valores.py", "As 10 maiores compras da classe Capacitação, como linhas extras da planilha de revisão humana (lista congelada depois da revisão)."),
    ("validacao_ia/resultado_revisao_humana_ia.py", "Resultado da revisão humana da aba de IA e divergências com a verificação por amostragem."),
    ("scripts_painel_v3/p1_08_ia_achados.py", "Principais achados e nota da linha-resumo da aba de IA."),
    ("scripts_painel_v3/p1_01c_fase2_painel.py", "Tabelas agregadas do bloco de modelo de aquisição e tipo de vendedor e dos principais achados."),
    ("scripts_painel_v3/p1_01d_cadeias.py", "Base da tabela 2 (cadeias fornecedor, objeto e órgão comprador), com controle contra a base do gráfico 11."),
    ("scripts_painel_v3/p1_01b_fluxo_compras.py", "Compras de cada fluxo do gráfico 11, para a contagem de compras distintas da linha-resumo do Sankey (banco aberto somente para leitura)."),
    ("scripts_painel_v3/p1_02_painel.py", "Painel HTML, metodologia e pacote de downloads."),
    ("scripts_painel_v3/p1_03_verificar_html.py", "Verificação do HTML em Chromium sem internet e capturas de tela."),
    ("scripts_painel_v3/p1_04_conferencia.py", "Conferência dos números do painel com as tabelas agregadas."),
    ("scripts_painel_v3/p1_05_relatorio_final.py", "Relatório final da entrega, com a conferência dos hashes das versões 1 e 2."),
]
B.append(("h2", "Scripts, em ordem de execução"))
B.append(("ul", [f"{i + 1}. {s}: {d}" for i, (s, d) in enumerate(SCRIPTS)]))

MET_HTML = render_html(B)
MET_MD = render_md(B)

# ------------------------------------------------------------------ pacote de downloads
TABELAS_PACOTE = sorted(os.path.join(TP, x) for x in os.listdir(TP) if x.endswith(".csv"))
TABELAS_PACOTE += sorted("validacao_ia/" + x for x in os.listdir("validacao_ia") if x.endswith(".csv"))  # fichas, julgamentos e revisão humana da aba de IA
TABELAS_PACOTE += [T0 + x for x in ("p0_totais_homologados_ano.csv", "p0_exclusoes_por_motivo_ano.csv",
                                    "p0_soberania_tres_regras.csv", "p0_soberania_ano.csv", "p0_categoria_ano.csv",
                                    "p0_categoria_total.csv", "p0_robustez_categorias.csv", "p0_preenchimento_pais_origem.csv",
                                    "duplicidades_removidas.csv", "duplicidades_regra_literal_cinco_campos.csv",
                                    "possiveis_duplicidades_processo_diferente.csv", "margem_aplicada_decomposicao.csv",
                                    "margem_aplicada_fora_elegibilidade_causa.csv", "margem_aplicada_fora_elegibilidade_top20.csv",
                                    "margem_elegivel_camadas.csv")]
TABELAS_PACOTE += [V + "remocao_indevida_por_categoria.csv", "dicionario_termos.csv"]
TABELAS_PACOTE += sorted(F2 + x for x in os.listdir(F2) if x.endswith(".csv"))  # dicionarios e listas de CNPJ
TABELAS_PACOTE += sorted(F2 + "tabelas/" + x for x in os.listdir(F2 + "tabelas") if x.endswith(".csv"))
TABELAS_PACOTE += sorted(F2 + "validacao/" + x for x in os.listdir(F2 + "validacao") if x.startswith("julgamentos_") and x.endswith(".csv"))  # precisao final: pn_precisao_final.csv
LEIAME = ["Pacote de downloads do painel de compras públicas de tecnologias críticas para a soberania digital (Ipea).",
          f"Gerado em {HOJE:%d/%m/%Y} por scripts_painel_v3/p1_02_painel.py.", "",
          "Pré-requisitos: DuckDB (CLI) e Python 3 com o módulo duckdb. Pasta de trabalho: Processado/, com os Parquet",
          "extraídos do Colibri em ../parquet/ (compras, itens, resultados). Os Parquet não fazem parte do pacote.",
          "Scripts .sql: duckdb scripts_parte0/p0.duckdb < <script>  (os da etapa 3 leem e gravam Parquet em Processado/).",
          "Scripts .py: python <script>.", "", "Ordem de execução:"]
LEIAME += [f"{i + 1:2d}. {s}  ({d})" for i, (s, d) in enumerate(SCRIPTS)]
LEIAME += ["", "Os scripts que geram apenas relatórios internos de verificação não fazem parte do pacote; nenhum número do painel depende deles.",
           "p0_17 é executado com o rótulo do sorteio: sed 's/__ROTULO__/remocao1/g' scripts_parte0/p0_17_fichas_remocao.sql | duckdb scripts_parte0/p0.duckdb",
           "p0_18 recebe o mesmo rótulo: python scripts_parte0/p0_18_remocao_indevida.py remocao1", "",
           "Tabelas agregadas (pasta tabelas_agregadas/): separador ';', ponto decimal. Cada CSV é descrito no cabeçalho do script que o gera."]
arquivos_scripts = list(dict.fromkeys([s for s, _ in SCRIPTS] + ["scripts_painel_v3/painel_modelo.html", "scripts_painel_v3/formatacao.py"]))
for s in arquivos_scripts:
    assert os.path.exists(s), s


def zip_bytes(pares):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for nome, conteudo in pares:
            z.writestr(nome, conteudo)
    return buf.getvalue()


ler_b = lambda c: open(c, "rb").read()
scripts_zip = zip_bytes([("LEIAME.txt", "\n".join(LEIAME))] + [(s, ler_b(s)) for s in arquivos_scripts])
tabelas_zip = zip_bytes([("LEIAME.txt", "\n".join(LEIAME))] + [(os.path.basename(t), ler_b(t)) for t in TABELAS_PACOTE])
with zipfile.ZipFile("pacote_downloads_v3.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.writestr("LEIAME.txt", "\n".join(LEIAME))
    for s in arquivos_scripts:
        z.writestr("scripts/" + s, ler_b(s))
    for t in TABELAS_PACOTE:
        z.writestr("tabelas_agregadas/" + os.path.basename(t), ler_b(t))
    z.writestr("scripts.zip", scripts_zip)
    z.writestr("tabelas_agregadas.zip", tabelas_zip)
    z.writestr("METODOLOGIA_v3.md", MET_MD)

# ------------------------------------------------------------------ montagem do HTML
downloads = ("<div class='downloads'>"
             "<button class='btn-dl' data-zip='scripts'>Baixar scripts (.zip)</button>"
             "<button class='btn-dl' data-zip='tabelas'>Baixar tabelas agregadas (.zip)</button>"
             "<a class='btn-dl' href='https://gestaogovbr.github.io/colibri/' target='_blank' rel='noopener'>Dados brutos (Colibri)</a>"
             "</div><p class='nota-dl'>Os dois pacotes são os mesmos arquivos de <code>pacote_downloads_v3.zip</code> (pastas scripts e tabelas_agregadas). "
             "Extração dos dados brutos: <code>COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__compras) TO 'compras.parquet' (FORMAT parquet)</code>; "
             "o mesmo para <code>__itens</code> e <code>__resultados</code>. Os Parquet não fazem parte do pacote.</p>")
MET_HTML = MET_HTML.replace("<!--__DOWNLOADS__-->", downloads)

cards = []
for c in CATS:
    ic = I["cat_" + c]
    cards.append(f"<div class='cat-card' style='--cor:{COR[c]}'><div class='cat-topo'><span class='cat-dot'></span>"
                 f"<span class='cat-nome'>{html.escape(NOME[c])}</span>{{{{I:cat_{c}}}}}</div>"
                 f"<div class='cat-camada'>Camada tecnológica: {html.escape(CAMADA[c])}</div>"
                 f"<div class='cat-desc'>{html.escape(DESCR[c])}</div></div>")

modelo = open("scripts_painel_v3/painel_modelo.html", encoding="utf-8").read()
sub = {
    "__LIB_CHART__": open("chart.umd.min.js", encoding="utf-8").read(),
    "__LIB_D3__": open("d3.min.js", encoding="utf-8").read(),
    "__LIB_SANKEY__": open("d3-sankey.min.js", encoding="utf-8").read(),
    "__DADOS__": json.dumps(D, ensure_ascii=False, separators=(",", ":")).replace("</", r"<\/"),
    "__ZIP_SCRIPTS__": base64.b64encode(scripts_zip).decode(),
    "__ZIP_TABELAS__": base64.b64encode(tabelas_zip).decode(),
    "__METODOLOGIA__": MET_HTML,
    "__CARTOES__": "".join(cards),
    "__DATA_GERACAO__": HOJE.strftime("%d/%m/%Y"),
    "__KPI_SOBRE_COMPRAS__": inteiro(N_PUB),
    "__KPI_SOBRE_VALOR__": bi(HOM),
    "__KPI_SOBRE_SOBERANIA__": bi(V2A),
    "__KPI_SOBRE_PART__": fmt_pct(PART),
    "__PAIS_PCT__": fmt_pct(PAIS_PCT),
    "__IA_N_REV__": inteiro(int(_irh_tot["casos_revisados"])),
    "__IA_MIN_REV__": fmt_pct(min(f(r["concordancia_pct"]) for r in _irh)),
    "__SELO_PRECISAO__": f"precisão entre {fmt_pct(min(precisao[c]['pct'] for c in CATS))} e {fmt_pct(max(precisao[c]['pct'] for c in CATS))} por categoria",
}
for k, v in sub.items():
    assert k in modelo, k
    modelo = modelo.replace(k, v)


def icone(chave):
    t = I[chave]
    if chave.startswith("cat_"):
        rotulo = "Palavras-chave"
        partes = [f"<div class='tt-rot'>{rotulo}</div><div class='tt-txt'>Termos buscados no objeto da compra e na descrição dos itens:</div>"
                  "<ul class='tt-lista'>" + "".join(f"<li>{html.escape(x)}</li>" for x in t["termos"]) + "</ul>"]
    else:
        rotulo = "Como interpretar"
        partes = [f"<div class='tt-rot'>{rotulo}</div><div class='tt-txt'>{html.escape(t['como'])}</div>"]
    if chave in USA_HOM:
        partes = [f"<div class='tt-txt tt-def'><b class='tt-ex'>Valor global homologado:</b> {html.escape(DEF_HOM)}</div><div class='tt-sep'></div>"] + partes
    if t.get("nota"):
        nt = html.escape(t["nota"])
        if chave + "_nota" in EXDIN:  # muda com o alternador
            nt = f"<span class='ex-din' data-ex='{chave}_nota'>{nt}</span>"
        partes.append(f"<div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>Nota metodológica:</b> {nt}</div>")
    if t.get("exemplo"):
        rot = "Verificação:" if chave.startswith("cat_") else "Exemplo de leitura:"
        ex = html.escape(t["exemplo"])
        if chave in EXDIN:  # muda com o alternador (atualizaExemplos, no JavaScript)
            ex = f"<span class='ex-din' data-ex='{chave}'>{ex}</span>"
        partes.append(f"<div class='tt-sep'></div><div class='tt-txt'><b class='tt-ex'>{rot}</b> {ex}</div>")
    return (f"<span class='info' tabindex='0' role='button' aria-label='{rotulo}' data-i='{chave}'>i"
            f"<span class='tt'>{''.join(partes)}</span></span>")


modelo = re.sub(r"\{\{I:(\w+)\}\}", lambda m: icone(m.group(1)), modelo)
assert "{{I:" not in modelo
assert all(k in I for k in USA_HOM)
open("painel_soberania_digital_v3.html", "w", encoding="utf-8").write(modelo)
open("METODOLOGIA_v3.md", "w", encoding="utf-8").write(MET_MD)
print("ok", f"{os.path.getsize('painel_soberania_digital_v3.html') / 1e6:.1f} MB",
      f"pacote {os.path.getsize('pacote_downloads_v3.zip') / 1e6:.1f} MB")
