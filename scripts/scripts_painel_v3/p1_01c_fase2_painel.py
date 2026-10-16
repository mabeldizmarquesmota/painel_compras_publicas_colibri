"""Painel v2, etapa 1c: tabelas agregadas da Fase 2 (modelo de aquisicao, tipo de vendedor, marcas, porte e achados).
Executar a partir de Processado/, depois de fase2/scripts/f2_01 a f2_11:  python scripts_painel_v3/p1_01c_fase2_painel.py
Entradas (somente leitura): fase2/f2.duckdb (modelo_valor_cat, modelo_item_v3, res_tipo, res_marca, res_v, res_venda,
  compras_escopo); scripts_parte0/p0.duckdb (pb.fator, deflator de cada compra, o mesmo do painel);
  fase2/tabelas/f2_06_situacao_classes.csv; fase2/tabelas/f2_11_achados.csv.
Regras:
  - modelo de aquisicao: valor por categoria pela regra do painel por categoria (2b), repartido entre as classes dos itens
    (f2_07); so aparecem com nome proprio as classes aprovadas na verificacao por amostragem e validadas na revisao
    humana (concordancia >= 80%); as demais (desenvolvimento e servicos tecnicos, equipamentos e infraestrutura fisica,
    nao identificado, suporte e manutencao de licenca e compras sem itens com valor) formam 'Servicos tecnicos, equipamentos e nao
    identificados'.
  - tipo de vendedor, marcas e porte: valor homologado dos resultados (base do grafico do Sankey); porte com ME e EPP
    numa classe unica, 'ME ou EPP'.
  - deflacionado = nominal x fator da compra (IPCA, mesmo mes-base do painel).
Controles: modelo por categoria e ano = pn_categoria_ano.csv; tipo de vendedor por categoria e ano = pn_fluxo.csv.
Saidas: tabelas_painel_v3/pn_modelo_categoria_ano.csv, pn_vendedor_categoria_ano.csv, pn_marca_resultados.csv,
  pn_porte_compras.csv, pn_porte_valor.csv, pn_achados.csv, pn_achados_numeros.csv, pn_direitos_permanentes_codigo.csv, pn_modelo_grupo_componentes.csv, pn_estatais_vencedoras.csv (empresas publicas de TI e outras
  estatais vencedoras nas seis categorias, por raiz de CNPJ)
"""
import csv
import sys
import shutil

import duckdb

sys.path.insert(0, "scripts_painel_v3")
from painel_compras_publicas_colibri.scripts.scripts_painel_v3.formatacao import inteiro, mi  # noqa: E402

TP = "tabelas_painel_v3/"
con = duckdb.connect("fase2/f2.duckdb", read_only=True)
con.sql("ATTACH 'scripts_parte0/p0.duckdb' AS p (READ_ONLY)")
# classes exibidas separadamente: aprovadas na verificacao por amostragem E validadas na revisao humana independente
# (concordancia >= 80%, fase2/validacao/resultado_revisao_humana.csv); as demais formam o grupo NV
_rh = {r["classe"]: r["validada"] for r in csv.DictReader(open("fase2/validacao/resultado_revisao_humana.csv", encoding="utf-8"), delimiter=";")
       if r["grupo"] == "Modelo de aquisição"}
aprov = {int(r["ordem"]): r["classe"] for r in csv.DictReader(open("fase2/tabelas/f2_06_situacao_classes.csv", encoding="utf-8"), delimiter=";")
         if r["situacao"] == "aprovada" and r["ordem"] != "7" and _rh.get(r["classe"]) == "sim"}
NV = "Serviços técnicos, equipamentos e não identificados"
caso = "CASE " + " ".join(f"WHEN m.ordem = {o} THEN '{n}'" for o, n in sorted(aprov.items())) + f" ELSE '{NV}' END"


def grava(nome, cab, rows):
    with open(TP + nome, "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)
    return rows


modelo = grava("pn_modelo_categoria_ano.csv", ["categoria", "ano", "ordem", "classe", "valor_nominal", "valor_deflacionado"], con.sql(f"""
SELECT m.segmento, c.ano, CASE WHEN m.ordem IN ({','.join(map(str, aprov))}) THEN m.ordem ELSE 9 END AS ordem, {caso} AS classe,
  sum(m.valor), sum(m.valor * pb.fator)
FROM modelo_valor_cat m JOIN (SELECT DISTINCT segmento, id_compra, ano FROM compras_escopo) c USING (segmento, id_compra)
JOIN p.pb pb ON pb.id_compra = m.id_compra GROUP BY ALL ORDER BY 1, 2, 3""").fetchall())
vend = grava("pn_vendedor_categoria_ano.csv", ["categoria", "ano", "tipo_vendedor", "valor_nominal", "valor_deflacionado"], con.sql("""
SELECT r.segmento, r.ano, r.tipo, sum(r.v), sum(r.v * pb.fator) FROM res_tipo r JOIN p.pb pb USING (id_compra) GROUP BY ALL ORDER BY 1, 2, 3""").fetchall())
grava("pn_marca_resultados.csv", ["marca", "categoria", "ano", "chave_resultado", "raiz_cnpj_vendedor", "tipo_vendedor", "id_compra", "valor_nominal", "valor_deflacionado"], con.sql("""
SELECT m.marca, m.segmento, r.ano, m.id_compra_item || '|' || m.ni_fornecedor || '|' || CAST(m.v AS VARCHAR), substr(m.ni_fornecedor, 1, 8), m.tipo, m.id_compra,
  m.v, m.v * pb.fator
FROM res_marca m JOIN res_v r USING (rid) JOIN p.pb pb ON pb.id_compra = m.id_compra ORDER BY 1, 2, 3, 4""").fetchall())
# ME e EPP em classe unica (a fonte quase nao registra EPP; ver fase2/tabelas/f2_10_porte_frequencia_base.csv)
P = "CASE WHEN porte_fornecedor_nome IN ('ME', 'EPP') THEN 'ME ou EPP' WHEN porte_fornecedor_nome = 'Demais' THEN 'Demais' ELSE 'Porte não informado' END"
grava("pn_porte_compras.csv", ["categoria", "ano", "porte", "id_compra"], con.sql(f"""
SELECT DISTINCT segmento, ano, {P}, id_compra FROM res_venda ORDER BY ALL""").fetchall())
grava("pn_porte_valor.csv", ["recorte", "ano", "porte", "valor_nominal", "valor_deflacionado"], con.sql(f"""
WITH r AS (SELECT segmento, id_compra, id_compra_item, ni_fornecedor, v, ano, {P} AS porte FROM res_venda)
SELECT r.segmento, r.ano, r.porte, sum(r.v), sum(r.v * pb.fator) FROM r JOIN p.pb pb USING (id_compra) GROUP BY ALL
UNION ALL  -- seis categorias: cada resultado uma vez
SELECT 'todas', u.ano, u.porte, sum(u.v), sum(u.v * pb.fator) FROM (SELECT DISTINCT id_compra, id_compra_item, ni_fornecedor, v, ano, porte FROM r) u
JOIN p.pb pb USING (id_compra) GROUP BY ALL ORDER BY 1, 2, 3""").fetchall())
# principais achados (texto da v3): numeros de fase2/tabelas/f2_11_numeros_achados.csv (gerados por f2_11) e numero de marcas do
# dicionario de marcas; cada numero usado fica em pn_achados_numeros.csv, com a base (total das seis categorias, soma por categoria
# ou valor dos resultados), para a conferencia
_num = {(r["achado"], r["indicador"]): r for r in csv.DictReader(open("fase2/tabelas/f2_11_numeros_achados.csv", encoding="utf-8"), delimiter=";")}
N_MARCAS = len({r["marca"] for r in csv.DictReader(open("fase2/dicionario_marcas.csv", encoding="utf-8"), delimiter=";")})
_usados = []


def n(a, ind, base, num):  # a: numero do achado em f2_11; num: numero exibido no painel
    r = _num[(a, ind)]
    _usados.append([num, a, ind.replace("no valor sem dupla contagem", "no total das seis categorias"), r["valor_exibido"], r["arquivo_de_origem"], base])
    return r["valor_exibido"]


T6, SC, VR = "total das seis categorias", "soma por categoria", "valor dos resultados"
# achado 4: a mesma base da aba de IA: valor do acrescimo a licenca repartido pelos itens e as compras em que ele esta
# (compras com parte de acrescimo), de tabelas_painel_v3/ia_base.csv e ia_base_classes.csv (p1_06)
_ia_b = {r["id_compra"]: r for r in csv.DictReader(open(TP + "ia_base.csv", encoding="utf-8"), delimiter=";")}
_ia_p = [r for r in csv.DictReader(open(TP + "ia_base_classes.csv", encoding="utf-8"), delimiter=";") if r["classe"] == "Acréscimo à licença"]
_ia_acr = sorted({r["id_compra"] for r in _ia_p})
_ia_v = sum(round(float(r["valor_nominal"]), 2) for r in _ia_p)
_ia_a = sum(1 for c in _ia_acr if _ia_b[c]["componente"] == "A")


def ia_n(ind, val):
    _usados.append(["4", "", ind, val, "tabelas_painel_v3/ia_base.csv; tabelas_painel_v3/ia_base_classes.csv",
                    "valor repartido pelos itens, como na aba de IA" if ind.startswith("valor") else "compras com parte de acréscimo à licença, como na aba de IA"])
    return val
# quatro achados, nesta ordem (os de licenciamento de direitos permanentes, porte e concentracao da venda saem do bloco;
# os numeros continuam nos graficos, tabelas e metodologia)
ACH = [
    ("1", "Contratação como serviço predomina",
     f"Subscrições e serviços somam {n('1', 'valor de subscrição ou serviço', T6, '1')}, {n('1', 'participação de subscrição ou serviço no valor sem dupla contagem', T6, '1')} do total das seis categorias. "
     f"Em Nuvem, chegam a {n('1', 'participação em Nuvem', SC, '1')}; em Plataformas e licenciamento, a {n('1', 'participação em Plataformas e licenciamento', SC, '1')}."),
    ("2", "Marcas globais chegam por revenda",
     f"Nas compras que citam as {N_MARCAS} marcas analisadas, revendedores e integradores ficaram com {n('3', 'participação de revendedores no valor com marca', VR, '2')} do valor; "
     f"subsidiárias brasileiras das marcas, com {n('3', 'participação de fabricantes diretos', VR, '2')}."),
    ("3", "Empresas públicas de TI têm peso relevante",
     f"{n('4', 'empresas públicas de TI vencedoras', VR, '3')} empresas públicas de TI venderam {n('4', 'valor vendido por empresas públicas de TI (soma por categoria)', SC, '3')}, "
     f"{n('4', 'participação no valor dos resultados (soma por categoria)', SC, '3')} do valor vendido nas seis categorias. Em Nuvem, a fatia é de {n('4', 'participação em Nuvem', SC, '3')}."),
    ("4", "IA generativa chega acoplada a licenças",
     f"Copilot e Gemini acoplados a licenças somaram {ia_n('valor do acréscimo à licença (aba de IA)', mi(_ia_v))} em {ia_n('compras do acréscimo à licença (aba de IA)', inteiro(len(_ia_acr)))} compras, "
     f"como na aba de inteligência artificial; só {ia_n('compras do acréscimo na categoria Inteligência artificial', inteiro(_ia_a))} dessas compras estão na categoria Inteligência artificial."),
]
assert all(len(t.split()) <= 30 for _, _, t in ACH), [len(t.split()) for _, _, t in ACH]
assert not any("dupla contagem" in t for _, _, t in ACH)
grava("pn_achados.csv", ["achado", "titulo", "texto"], ACH)
grava("pn_achados_numeros.csv", ["achado", "achado_f2_11", "indicador", "valor_exibido", "arquivo_de_origem", "base"], _usados)
# componentes do grupo NV no grafico 9 (soma por categoria): suporte e manutencao de licenca (ordem 4) e compras sem itens com valor (ordem 0)
grava("pn_modelo_grupo_componentes.csv", ["categoria", "ano", "ordem", "classe", "valor_nominal", "valor_deflacionado"], con.sql("""
SELECT m.segmento, c.ano, m.ordem, CASE m.ordem WHEN 0 THEN 'Compras sem itens com valor' ELSE 'Suporte e manutenção de licença' END,
  sum(m.valor), sum(m.valor * pb.fator)
FROM modelo_valor_cat m JOIN (SELECT DISTINCT segmento, id_compra, ano FROM compras_escopo) c USING (segmento, id_compra)
JOIN p.pb pb ON pb.id_compra = m.id_compra WHERE m.ordem IN (0, 4) GROUP BY ALL ORDER BY 1, 2, 3""").fetchall())
# licenciamento de direitos permanentes de uso identificado so pelo nome do codigo do catalogo, total das seis categorias
grava("pn_direitos_permanentes_codigo.csv", ["valor_classe_total", "valor_so_codigo_catalogo", "pct_so_codigo_catalogo"], con.sql(r"""
SELECT sum(v.valor), sum(v.valor) FILTER (WHERE m.termo LIKE '%bdireitos permanentes'),
  100 * sum(v.valor) FILTER (WHERE m.termo LIKE '%bdireitos permanentes') / sum(v.valor)
FROM modelo_valor_2a v JOIN modelo_item_v3 m USING (id_compra_item) WHERE m.ordem = 3""").fetchall())
grava("pn_estatais_vencedoras.csv", ["raiz_cnpj", "nome_empresarial", "tipo_vendedor", "compras", "valor_resultados_soma_por_categoria"], con.sql("""
SELECT substr(ni_fornecedor, 1, 8), min(nome_fornecedor), tipo, count(DISTINCT id_compra), sum(v) FROM res_tipo
WHERE tipo IN ('Empresa pública de TI', 'Outra empresa estatal') GROUP BY 1, 3 ORDER BY 3, 5 DESC""").fetchall())

# controles
cat = {(r["categoria"], r["ano"]): float(r["valor_nominal"]) for r in csv.DictReader(open(TP + "pn_categoria_ano.csv", encoding="utf-8"), delimiter=";")}
sm = {}
for c, a, o, n, v, vd in modelo:
    sm[(c, str(a))] = sm.get((c, str(a)), 0) + v
assert all(abs(sm.get(k, 0) - v) < 1 for k, v in cat.items()) and set(sm) <= set(cat), "modelo nao reproduz pn_categoria_ano"
fl = {}
for r in csv.DictReader(open(TP + "pn_fluxo.csv", encoding="utf-8"), delimiter=";"):
    fl[(r["categoria"], r["ano"])] = fl.get((r["categoria"], r["ano"]), 0) + float(r["valor_nominal"])
sv = {}
for c, a, t, v, vd in vend:
    sv[(c, str(a))] = sv.get((c, str(a)), 0) + v
assert set(sv) == set(fl) and all(abs(sv[k] - fl[k]) < 1 for k in fl), "tipo de vendedor nao reproduz pn_fluxo"
print("ok:", len(modelo), "linhas de modelo;", len(vend), "de tipo de vendedor; controles com o painel conferidos")
