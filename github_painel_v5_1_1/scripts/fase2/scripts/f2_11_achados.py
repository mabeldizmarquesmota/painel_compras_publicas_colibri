"""Fase 2, etapa 11 (F): achados candidatos para cartoes, calculados so a partir das tabelas da Fase 2 e da base do painel.
Executar a partir de Processado/, depois de f2_06 a f2_10:  python fase2/scripts/f2_11_achados.py
Entradas: fase2/tabelas/f2_06_situacao_classes.csv, f2_07_*.csv, f2_08_*.csv, f2_10_porte_categoria.csv; fase2/f2.duckdb
  (res_marca, res_v, modelo_valor_2a, modelo_item_v3, compras_escopo) para os agregados novos, gravados em
  fase2/tabelas/f2_11_*.csv; formatacao igual a do painel (scripts_painel_v2/formatacao.py, so leitura).
Regras: HHI e CR4 por marca com o vendedor identificado pela raiz do CNPJ (matriz e filiais juntas); IA acoplada = itens da classe 1 cujo texto cita Copilot ou Gemini; so classes aprovadas na validacao (f2_06); HHI na escala de 0 a 1, s_i = valor do vendedor / valor da marca;
  nenhum nome de empresa privada no titulo; cada numero registrado com o arquivo de origem.
Saidas: fase2/tabelas/f2_11_numeros_achados.csv (achado; indicador; valor_exibido; arquivo_de_origem);
        fase2/tabelas/f2_11_hhi_vendedores_marca.csv; fase2/tabelas/f2_11_ia_acoplada_ano.csv; fase2/achados_candidatos.md
"""
import csv
import sys

import duckdb

sys.path.insert(0, "scripts_painel_v2")
from formatacao import bi, fmt_num, fmt_pct, inteiro, mi  # noqa: E402

T = "fase2/tabelas/"
ler = lambda n: list(csv.DictReader(open(T + n, encoding="utf-8"), delimiter=";"))
f = float
sit = {int(r["ordem"]): r["situacao"] for r in ler("f2_06_situacao_classes.csv")}
NUM = []


def reg(achado, ind, val, arq):
    NUM.append([achado, ind, val, arq])
    return val


con = duckdb.connect("fase2/f2.duckdb", read_only=True)
# ---- agregados novos
hhi = con.sql("""
WITH d AS (SELECT DISTINCT r.id_compra_item, r.ni_fornecedor, r.nome_fornecedor, r.v, m.marca, m.tipo FROM res_marca m JOIN res_v r USING (rid)),
nc AS (SELECT marca, count(DISTINCT id_compra) AS compras FROM res_marca GROUP BY 1),
s AS (SELECT marca, substr(ni_fornecedor, 1, 8) AS ni_fornecedor, sum(v) AS v FROM d GROUP BY 1, 2), t AS (SELECT marca, sum(v) AS tv, count(*) AS n FROM s GROUP BY 1)
SELECT s.marca, t.n AS vendedores, t.tv AS valor, sum((s.v / t.tv) * (s.v / t.tv)) AS hhi,
  100 * sum(s.v) FILTER (WHERE rk <= 4) / t.tv AS cr4, 100 * max(s.v) / t.tv AS cr1, any_value(nc.compras) AS compras
FROM (SELECT *, row_number() OVER (PARTITION BY marca ORDER BY v DESC, ni_fornecedor) AS rk FROM s) s JOIN t USING (marca) JOIN nc USING (marca)
GROUP BY s.marca, t.n, t.tv ORDER BY valor DESC""").fetchall()
with open(T + "f2_11_hhi_vendedores_marca.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["marca", "vendedores", "valor_homologado_resultados", "hhi", "cr4_pct", "maior_vendedor_pct", "compras"])
    w.writerows(hhi)
ia = con.sql("""
SELECT c.ano, count(DISTINCT v.id_compra) AS compras, sum(v.valor) AS valor
FROM modelo_valor_2a v JOIN modelo_item_v3 m USING (id_compra_item)
JOIN (SELECT DISTINCT id_compra, ano FROM compras_escopo) c USING (id_compra)
JOIN (SELECT DISTINCT id_compra_item, lower(concat_ws(' ', descricao, descricao_resumida, descricao_detalhada)) AS t FROM itens_escopo) i USING (id_compra_item)
WHERE m.ordem = 1 AND regexp_matches(i.t, '\\b(copilot|gemini)\\b') GROUP BY 1 ORDER BY 1""").fetchall()
ia_cat = con.sql("""
SELECT v.segmento, count(DISTINCT v.id_compra) AS compras, sum(v.valor) AS valor
FROM modelo_valor_cat v JOIN modelo_item_v3 m USING (id_compra_item)
JOIN (SELECT DISTINCT id_compra_item, lower(concat_ws(' ', descricao, descricao_resumida, descricao_detalhada)) AS t FROM itens_escopo) i USING (id_compra_item)
WHERE m.ordem = 1 AND regexp_matches(i.t, '\\b(copilot|gemini)\\b') GROUP BY 1 ORDER BY 3 DESC""").fetchall()
with open(T + "f2_11_ia_acoplada_categoria.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["categoria", "compras", "valor_homologado_regra_por_categoria"])
    w.writerows(ia_cat)
with open(T + "f2_11_ia_acoplada_ano.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["ano", "compras", "valor_homologado_sem_dupla_contagem"])
    w.writerows(ia)
marca_tipo = con.sql("""
WITH d AS (SELECT DISTINCT r.id_compra_item, r.ni_fornecedor, r.v, r.rid, m.tipo FROM res_marca m JOIN res_v r USING (rid)),
u AS (SELECT DISTINCT id_compra_item, ni_fornecedor, v, CASE WHEN bool_or(tipo = 'Fabricante direto') THEN 'Fabricante direto'
        WHEN bool_or(tipo = 'Empresa pública de TI') THEN 'Empresa pública de TI' WHEN bool_or(tipo = 'Outra empresa estatal') THEN 'Outra empresa estatal'
        ELSE 'Revendedor ou integrador' END AS tipo FROM d GROUP BY 1, 2, 3)
SELECT tipo, sum(v) FROM u GROUP BY 1""").fetchall()
with open(T + "f2_11_marca_qualquer_tipo.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["tipo_vendedor", "valor_homologado_resultados_com_marca"])
    w.writerows(marca_tipo)

# ---- achados
A = []
tot = {int(r["ordem"]): r for r in ler("f2_07_modelo_total_sem_dupla_contagem.csv")}
cat = {(r["categoria"], int(r["ordem"])): r for r in ler("f2_07_modelo_categoria.csv")}
F7T, F7C = "fase2/tabelas/f2_07_modelo_total_sem_dupla_contagem.csv", "fase2/tabelas/f2_07_modelo_categoria.csv"
assert sit[2] == sit[3] == sit[6] == sit[1] == "aprovada"
p2, v2 = f(tot[2]["pct_do_total"]), f(tot[2]["valor_homologado_nominal"])
A.append(("1", "Contratação como serviço predomina",
          f"A classe subscrição ou serviço reúne assinaturas, licenças por prazo, serviços de nuvem e certificados digitais. Esses itens respondem por {reg('1', 'participação de subscrição ou serviço no valor sem dupla contagem', fmt_pct(p2), F7T)} "
          f"do valor homologado das tecnologias críticas para a soberania digital ({reg('1', 'valor de subscrição ou serviço', bi(v2), F7T)}). "
          f"Em Nuvem, a participação chega a {reg('1', 'participação em Nuvem', fmt_pct(f(cat[('nuvem', 2)]['pct_da_categoria'])), F7C)}; "
          f"em Plataformas e licenciamento, a {reg('1', 'participação em Plataformas e licenciamento', fmt_pct(f(cat[('plataformas', 2)]['pct_da_categoria'])), F7C)}."))
p3, v3 = f(tot[3]["pct_do_total"]), f(tot[3]["valor_homologado_nominal"])
A.append(("2", "Licenciamento de direitos permanentes de uso é residual",
          f"O licenciamento de direitos permanentes de uso soma {reg('2', 'valor de licenciamento de direitos permanentes de uso', bi(v3), F7T)}, {reg('2', 'participação de licenciamento de direitos permanentes de uso', fmt_pct(p3), F7T)} do valor sem dupla contagem. "
          f"Para cada R$ 1 em licenciamento de direitos permanentes de uso, o Estado homologou R$ {reg('2', 'razão subscrição/direitos permanentes de uso', fmt_num(v2 / v3, 0), F7T)} em subscrições e serviços."))
A.append(("3", "Em data center, quase metade é equipamento",
          f"Equipamentos e infraestrutura física representam {reg('3', 'participação de equipamentos em Data center', fmt_pct(f(cat[('data_center', 6)]['pct_da_categoria'])), F7C)} "
          f"do valor de Data center ({reg('3', 'valor de equipamentos em Data center', bi(f(cat[('data_center', 6)]['valor_homologado_nominal'])), F7C)}), "
          f"ante {reg('3', 'participação de equipamentos em Nuvem', fmt_pct(f(cat[('nuvem', 6)]['pct_da_categoria'])), F7C)} em Nuvem."))
mt = {r[0]: r[1] for r in marca_tipo}
tm = sum(mt.values())
mk = {r["marca"]: r for r in ler("f2_08_marca_total.csv")}
F8 = "fase2/tabelas/f2_08_marca_total.csv"
sem_direta = sum(f(r["valor_fabricante_direto"]) == 0 for r in mk.values())
A.append(("4", "Marcas globais chegam por revenda",
          f"Nas compras que citam uma das 15 marcas analisadas, revendedores e integradores venderam {reg('4', 'participação de revendedores no valor com marca', fmt_pct(100 * mt['Revendedor ou integrador'] / tm), T + 'f2_11_marca_qualquer_tipo.csv')} "
          f"do valor dos resultados, e as subsidiárias brasileiras das marcas, {reg('4', 'participação de fabricantes diretos', fmt_pct(100 * mt['Fabricante direto'] / tm), T + 'f2_11_marca_qualquer_tipo.csv')}. "
          f"Em {reg('4', 'marcas sem venda direta', inteiro(sem_direta), F8)} das 15 marcas não há venda direta registrada; "
          f"nas compras que citam Microsoft ({reg('4', 'compras com Microsoft', inteiro(int(mk['Microsoft']['compras'])), F8)}), revendedores ficaram com "
          f"{reg('4', 'participação de revendedores Microsoft', fmt_pct(f(mk['Microsoft']['pct_revendedores'])), F8)} do valor."))
tv = {r["tipo_vendedor"]: r for r in ler("f2_08_tipo_vendedor_total.csv")}
F8T = "fase2/tabelas/f2_08_tipo_vendedor_total.csv"
tt = sum(f(r["valor_homologado_resultados_distintos"]) for r in tv.values())
pub = tv["Empresa pública de TI"]
tc = {(r["categoria"], r["tipo_vendedor"]): r for r in ler("f2_08_tipo_vendedor_categoria.csv")}
npub = len({r["cnpj"][:8] for r in ler("f2_08_empresas_publicas_ti.csv")})
FTC = "fase2/tabelas/f2_08_tipo_vendedor_categoria.csv"
vpc = sum(f(r["valor_homologado_resultados"]) for r in tc.values() if r["tipo_vendedor"] == "Empresa pública de TI")
tpc = sum(f(r["valor_homologado_resultados"]) for r in tc.values())
A.append(("5", "Empresas públicas de TI têm peso relevante",
          f"{reg('5', 'empresas públicas de TI vencedoras', inteiro(npub), T + 'f2_08_empresas_publicas_ti.csv')} empresas públicas de tecnologia da informação venderam "
          f"{reg('5', 'valor vendido por empresas públicas de TI (soma por categoria)', bi(vpc), FTC)}, "
          f"{reg('5', 'participação no valor dos resultados (soma por categoria)', fmt_pct(100 * vpc / tpc), FTC)} do valor dos resultados das seis categorias, somado por categoria. "
          f"Em Nuvem, a participação é de {reg('5', 'participação em Nuvem', fmt_pct(f(tc[('nuvem', 'Empresa pública de TI')]['pct_da_categoria'])), 'fase2/tabelas/f2_08_tipo_vendedor_categoria.csv')}."))
po = {(r["categoria"], r["porte"]): r for r in ler("f2_10_porte_categoria.csv")}
F10 = "fase2/tabelas/f2_10_porte_categoria.csv"
n9 = con.sql("SELECT count(DISTINCT id_compra) FROM res_v").fetchone()[0]
reg("6", "compras na base do gráfico 9", inteiro(n9), "fase2/f2.duckdb, tabela res_venda (= tabelas_painel_v2/pn_fluxo_compras.csv)")
A.append(("6", "Micro e pequenas empresas vencem muito e vendem pouco",
          f"Micro ou pequenas empresas (ME ou EPP) venceram resultados em {reg('6', 'compras com vencedor ME ou EPP', inteiro(int(po[('Seis categorias', 'ME ou EPP')]['compras'])), F10)} das {inteiro(n9)} compras com vencedor identificado "
          f"({reg('6', 'percentual de compras com vencedor ME ou EPP', fmt_pct(100 * int(po[('Seis categorias', 'ME ou EPP')]['compras']) / n9), F10)}), mas ficaram com "
          f"{reg('6', 'participação ME ou EPP no valor', fmt_pct(f(po[('Seis categorias', 'ME ou EPP')]['pct_do_valor'])), F10)} do valor. "
          f"Fornecedores de porte 'Demais' concentraram {reg('6', 'participação Demais no valor', fmt_pct(f(po[('Seis categorias', 'Demais')]['pct_do_valor'])), F10)}."))
hh = {r[0]: r for r in hhi}
grandes = [r for r in hhi if r[6] >= 20]  # so marcas citadas em pelo menos 20 compras
mais = max(grandes, key=lambda r: r[3])
FH = T + "f2_11_hhi_vendedores_marca.csv"
A.append(("7", "Venda concentrada em poucos revendedores",
          f"Entre as marcas citadas em pelo menos 20 compras, a venda mais concentrada é a de {reg('7', 'marca de maior HHI', mais[0], FH)} "
          f"({reg('7', 'compras da marca de maior HHI', inteiro(mais[6]), FH)} compras): "
          f"o maior vendedor ficou com {reg('7', 'participação do maior vendedor da marca', fmt_pct(mais[5]), FH)} do valor, com HHI de {reg('7', 'HHI da marca', fmt_num(mais[3], 3), FH)} (escala de 0 a 1). "
          f"Mesmo em Microsoft ({reg('7', 'compras Microsoft', inteiro(hh['Microsoft'][6]), FH)} compras), com {reg('7', 'vendedores Microsoft', inteiro(hh['Microsoft'][1]), FH)} vendedores, o HHI é de {reg('7', 'HHI Microsoft', fmt_num(hh['Microsoft'][3], 3), FH)} "
          f"e os quatro maiores ficaram com {reg('7', 'CR4 Microsoft', fmt_pct(hh['Microsoft'][4]), FH)} do valor."))
iad = {r[0]: r for r in ia}
FI = T + "f2_11_ia_acoplada_ano.csv"
tia = sum(r[2] for r in ia)
FIC = T + "f2_11_ia_acoplada_categoria.csv"
icat = {r[0]: r for r in ia_cat}
v_ia = sum(f(r["valor_homologado_nominal"]) for r in ler("f2_07_modelo_categoria.csv") if r["categoria"] == "ia")
A.append(("8", "Parte da IA generativa chega como acréscimo a licenças",
          f"Assistentes de IA acoplados a licenças existentes (Copilot e Gemini) somaram {reg('8', 'valor de Copilot e Gemini', mi(tia), FI)} em "
          f"{reg('8', 'compras com Copilot e Gemini', inteiro(sum(r[1] for r in ia)), FI)} compras, sem dupla contagem. "
          f"A maior parte dessas compras está classificada em Plataformas e licenciamento ({reg('8', 'compras em Plataformas e licenciamento', inteiro(icat['plataformas'][1]), FIC)}) "
          f"e em Nuvem ({reg('8', 'compras em Nuvem', inteiro(icat['nuvem'][1]), FIC)}); só {reg('8', 'compras em Inteligência artificial', inteiro(icat['ia'][1]), FIC)} estão em Inteligência artificial (uma compra pode estar em mais de uma categoria), "
          f"com {reg('8', 'valor em Inteligência artificial', mi(icat['ia'][2]), FIC)}, {reg('8', 'participação no valor de Inteligência artificial', fmt_pct(100 * icat['ia'][2] / v_ia), F7C)} do valor da categoria."))
# achado 'Em data center, quase metade é equipamento' retirado: depende da classe de equipamentos, nao validada na
# revisao humana (fase2/validacao/resultado_revisao_humana.csv); os demais sao renumerados em sequencia
RETIRADOS = {"3"}
_novo = {k: str(i + 1) for i, k in enumerate(a[0] for a in A if a[0] not in RETIRADOS)}
A = [(_novo[k], t, x) for k, t, x in A if k not in RETIRADOS]
NUM = [[_novo[n[0]]] + n[1:] for n in NUM if n[0] not in RETIRADOS]
with open(T + "f2_11_numeros_achados.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["achado", "indicador", "valor_exibido", "arquivo_de_origem"])
    w.writerows(NUM)
with open(T + "f2_11_achados.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["achado", "titulo", "texto"])
    w.writerows(A)
md = ["# Achados candidatos (Fase 2)", "", "Calculados por `fase2/scripts/f2_11_achados.py`. Cada número está em `fase2/tabelas/f2_11_numeros_achados.csv`, com o arquivo de origem. "
      "Só usam classes aprovadas na verificação por amostragem e validadas na revisão humana; o achado sobre equipamentos em data center foi retirado.", ""]
for k, t, txt in A:
    md += [f"## {k}. {t}", "", txt, ""]
open("fase2/achados_candidatos.md", "w", encoding="utf-8").write("\n".join(md))
print("\n".join(md))
