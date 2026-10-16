"""Fase 2, etapa 8 (C): marca mencionada e tipo de vendedor (base 'quem vende' = grafico 9 do painel).
Executar a partir de Processado/, depois de f2_01:  python fase2/scripts/f2_08_marcas_vendedores.py
Entradas: fase2/f2.duckdb (itens_escopo, compras_escopo, res_venda); resultados_dedup.parquet (nomes e natureza juridica
  de todos os vencedores da base, para identificar CNPJs).
Regras:
  - marca no item: termos do dicionario (fase2/dicionario_marcas.csv) no texto do item (descricao, resumida, detalhada),
    normalizado (minusculas, sem acentos); se o item nao cita marca, valem as marcas citadas no objeto da compra.
  - fabricante direto: CNPJ (raiz de 8 digitos) vencedor pertence a subsidiaria brasileira da marca citada, identificada
    pelo nome empresarial nos resultados da base (fase2/fabricantes_cnpj.csv). Marcas sem subsidiaria vencedora na base
    nao tem venda direta registrada.
  - empresa publica de TI: natureza juridica Empresa Publica (2011) ou Sociedade de Economia Mista (2038) e nome empresarial
    de empresa de tecnologia da informacao (processamento de dados, informatica, tecnologia da informacao etc.); a lista
    de raizes de CNPJ (fase2/empresas_publicas_ti.csv) vale tambem para resultados sem natureza juridica preenchida.
    Estatais de outros ramos (telecomunicacoes, correios, bancos etc.) ficam em 'Outra empresa estatal'.
  - precedencia do tipo de vendedor no resultado: fabricante direto (marca citada) > empresa publica de TI > outra
    empresa estatal > revendedor ou integrador (marca citada, vencedor nao e o fabricante) > demais fornecedores privados.
  - valores: valor homologado dos resultados (base do grafico 9); por marca, um resultado que cita duas marcas entra nas duas.
  - maiores revendedores: empresa identificada pela raiz do CNPJ (8 digitos), somando matriz e filiais.
Saidas: fase2/dicionario_marcas.csv; fase2/fabricantes_cnpj.csv; fase2/empresas_publicas_ti.csv;
  fase2/f2.duckdb (res_marca: resultado x marca; res_tipo: tipo de vendedor por resultado);
  fase2/tabelas/f2_08_*.csv (valor por marca e categoria, fabricante x revendedor, 5 maiores revendedores, empresas
  publicas de TI por categoria, tipo de vendedor por categoria)
"""
import csv
import re
import unicodedata

import duckdb

MARCAS = {
    "Microsoft": [r"\bmicrosoft\b", r"\bazure\b", r"\b(office|microsoft|m) ?365\b", r"\bwindows server\b", r"\bsql server\b", r"\bsharepoint\b",
                  r"\bpower ?bi\b", r"\bcopilot\b", r"\bdynamics 365\b", r"\bexchange (server|online)\b", r"\bvisual studio\b",
                  r"\bpower (apps|automate|platform|pages)\b", r"\bwindows (10|11) (pro|professional|enterprise)\b", r"\bmicrosoft teams\b"],
    "Google": [r"\bgoogle\b", r"\bgcp\b", r"\bgemini\b", r"\bbigquery\b", r"\bg ?suite\b", r"\bapigee\b"],
    "Amazon/AWS": [r"\baws\b", r"\bamazon\b"],
    "Oracle": [r"\boracle\b", r"\bexadata\b", r"\bweblogic\b", r"\bmysql enterprise\b"],
    "SAP": [r"\bsap (s/?4 ?hana|hana|erp|ecc|bw|business|basis|netweaver|ariba|successfactors|concur|crm|analytics|cloud|btp|gui|fiori|businessobjects|solution manager)\b",
            r"\bs/?4 ?hana\b", r"\b(ambiente|sistema|solucao|licencas?|modulos?|plataforma|suporte|consultoria|sustentacao) sap\b"],
    "IBM": [r"\bibm\b", r"\bwebsphere\b", r"\bdb2\b", r"\bqradar\b", r"\bspss\b", r"\bcognos\b"],
    "Red Hat": [r"\bred ?hat\b", r"\brhel\b", r"\bopenshift\b", r"\bansible\b", r"\bjboss\b"],
    "VMware/Broadcom": [r"\bvmware\b", r"\bvsphere\b", r"\bvcenter\b", r"\bvsan\b", r"\bbroadcom\b", r"\bvrealize\b", r"\bnsx\b"],
    "Salesforce": [r"\bsalesforce\b", r"\btableau\b", r"\bmulesoft\b", r"\bslack\b"],
    "Adobe": [r"\badobe\b", r"\bacrobat\b", r"\bphotoshop\b", r"\bcreative cloud\b", r"\billustrator\b", r"\bindesign\b", r"\bpremiere pro\b"],
    "Huawei": [r"\bhuawei\b", r"\boceanstor\b"],
    "Cisco": [r"\bcisco\b", r"\bwebex\b", r"\bmeraki\b", r"\bfirepower\b"],
    "Fortinet": [r"\bfortinet\b", r"\bforti(gate|analyzer|manager|client|web|mail|siem|switch|ap|edr|nac|sandbox|authenticator|token|care|guard)\b"],
    "Palo Alto": [r"\bpalo ?alto\b", r"\bprisma (access|cloud)\b", r"\bcortex (xdr|xsoar|xsiam)\b", r"\bpan-?os\b"],
    "Check Point": [r"\bcheck ?point\b"],
}
EXCL = {"Amazon/AWS": [r"\bamazon(as|ia|ica|ico|ense)\b"], "SAP": [r"administracao penitenciaria"]}
# subsidiarias: padrao do nome empresarial (inicio do nome), conferido nos resultados da base
SUBS = {"Microsoft": r"^microsoft (informatica|do brasil)", "Google": r"^google (brasil|cloud brasil|llc)", "Amazon/AWS": r"^amazon (aws servicos brasil|servicos de varejo do brasil)",
        "Oracle": r"^oracle do brasil sistemas", "IBM": r"^ibm brasil", "Adobe": r"^adobe systems brasil", "Huawei": r"^huawei (do brasil|gestao e servicos)",
        "SAP": r"^sap brasil", "Red Hat": r"^red hat", "VMware/Broadcom": r"^(vmware|broadcom)", "Salesforce": r"^salesforce", "Cisco": r"^cisco do brasil",
        "Fortinet": r"^fortinet", "Palo Alto": r"^palo alto", "Check Point": r"^check point"}
TI_NOME = r"processamento de dados|informatica|tecnologia da informacao|tecnologia de informacao|transformacao digital|automacao|serpro|dataprev|prodesp|prodam|prodemge|celepar|prodepa|iplanrio|procergs|prodeb|ciasc|codata|prodap|prodest"


def norm(t):
    t = unicodedata.normalize("NFKD", (t or "").replace("\xa0", " ")).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", t).strip()


RE = {m: [re.compile(e) for e in es] for m, es in MARCAS.items()}
REX = {m: [re.compile(e) for e in es] for m, es in EXCL.items()}


def marcas(t):
    return sorted(m for m in RE if any(p.search(t) for p in RE[m]) and not any(p.search(t) for p in REX.get(m, [])))


with open("fase2/dicionario_marcas.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["marca", "tipo", "expressao"])
    for m, es in MARCAS.items():
        w.writerows([[m, "inclusao", e] for e in es] + [[m, "exclusao", e] for e in EXCL.get(m, [])])

con = duckdb.connect("fase2/f2.duckdb")
# CNPJs das subsidiarias e das empresas publicas de TI (todos os vencedores da base)
venc = con.sql("""SELECT substr(ni_fornecedor, 1, 8) AS raiz, ni_fornecedor, trim(nome_razao_social_fornecedor) AS nome, natureza_juridica_id
  FROM read_parquet('resultados_dedup.parquet') WHERE length(ni_fornecedor) = 14 GROUP BY ALL""").fetchall()
fab = {}
for raiz, ni, nome, nat in venc:
    for m, p in SUBS.items():
        if re.search(p, norm(nome)):
            fab.setdefault((m, raiz), set()).add(nome)
pub = {}
for raiz, ni, nome, nat in venc:
    if nat in ("2011", "2038") and re.search(TI_NOME, norm(nome)):
        pub.setdefault(raiz, set()).add(nome)
est = {raiz for raiz, ni, nome, nat in venc if nat in ("2011", "2038")} - set(pub)
with open("fase2/fabricantes_cnpj.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["marca", "raiz_cnpj", "nomes_empresariais_na_base"])
    w.writerows([[m, r, " / ".join(sorted(n))] for (m, r), n in sorted(fab.items())])
with open("fase2/empresas_publicas_ti.csv", "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["raiz_cnpj", "nomes_empresariais_na_base"])
    w.writerows([[r, " / ".join(sorted(n))] for r, n in sorted(pub.items())])
FAB = {}
for (m, r) in fab:
    FAB.setdefault(m, set()).add(r)

# marcas por item (texto do item; sem marca no item, as do objeto)
itens = con.sql("""SELECT DISTINCT i.id_compra_item, concat_ws(' | ', i.descricao, i.descricao_resumida, i.descricao_detalhada), c.objeto_compra
  FROM itens_escopo i JOIN (SELECT DISTINCT id_compra, objeto_compra FROM compras_escopo) c USING (id_compra)""").fetchall()
mi = []
for i, t, ob in itens:
    ms = marcas(norm(t))
    origem = "item"
    if not ms:
        ms, origem = marcas(norm(ob)), "objeto"
    mi += [(i, m, origem) for m in ms]
con.sql("CREATE OR REPLACE TABLE item_marca (id_compra_item VARCHAR, marca VARCHAR, origem VARCHAR)")
con.executemany("INSERT INTO item_marca VALUES (?, ?, ?)", mi)
con.sql("CREATE OR REPLACE TABLE fab (marca VARCHAR, raiz VARCHAR)")
con.executemany("INSERT INTO fab VALUES (?, ?)", [(m, r) for m, rs in FAB.items() for r in rs])
con.sql("CREATE OR REPLACE TABLE pub_ti (raiz VARCHAR)")
con.executemany("INSERT INTO pub_ti VALUES (?)", [(r,) for r in pub])
con.sql("CREATE OR REPLACE TABLE estatal (raiz VARCHAR)")
con.executemany("INSERT INTO estatal VALUES (?)", [(r,) for r in est])
con.sql("""
CREATE OR REPLACE TABLE res_v AS
SELECT row_number() OVER (ORDER BY segmento, id_compra, id_compra_item, ni_fornecedor, v) AS rid, *, substr(ni_fornecedor, 1, 8) AS raiz,
  substr(ni_fornecedor, 1, 8) IN (SELECT raiz FROM pub_ti) AS pub, substr(ni_fornecedor, 1, 8) IN (SELECT raiz FROM estatal) AS est
FROM res_venda""")
con.sql("""
CREATE OR REPLACE TABLE res_marca AS
SELECT r.rid, r.segmento, r.id_compra, r.id_compra_item, r.ni_fornecedor, r.nome_fornecedor, r.v, im.marca, im.origem,
  CASE WHEN r.raiz IN (SELECT raiz FROM fab f WHERE f.marca = im.marca) THEN 'Fabricante direto'
       WHEN r.pub THEN 'Empresa pública de TI' WHEN r.est THEN 'Outra empresa estatal'
       ELSE 'Revendedor ou integrador' END AS tipo
FROM res_v r JOIN item_marca im USING (id_compra_item)""")
con.sql("""
CREATE OR REPLACE TABLE res_tipo AS
SELECT r.*, CASE WHEN EXISTS (SELECT 1 FROM res_marca m WHERE m.rid = r.rid AND m.tipo = 'Fabricante direto') THEN 'Fabricante direto'
  WHEN r.pub THEN 'Empresa pública de TI' WHEN r.est THEN 'Outra empresa estatal'
  WHEN EXISTS (SELECT 1 FROM res_marca m WHERE m.rid = r.rid) THEN 'Revendedor ou integrador'
  ELSE 'Demais fornecedores privados' END AS tipo
FROM res_v r""")
assert abs(con.sql("SELECT sum(v) FROM res_tipo").fetchone()[0] - con.sql("SELECT sum(v) FROM res_venda").fetchone()[0]) < 1


def grava(nome, cab, q):
    rows = con.sql(q).fetchall()
    with open(f"fase2/tabelas/{nome}.csv", "w", encoding="utf-8", newline="") as fo:
        w = csv.writer(fo, delimiter=";")
        w.writerow(cab)
        w.writerows(rows)
    return rows


grava("f2_08_marca_categoria", ["categoria", "marca", "compras", "resultados", "valor_homologado_resultados"],
      "SELECT segmento, marca, count(DISTINCT id_compra), count(DISTINCT rid), sum(v) FROM res_marca GROUP BY ALL ORDER BY 1, 5 DESC")
grava("f2_08_marca_total", ["marca", "compras", "valor_homologado_resultados", "valor_fabricante_direto", "valor_revendedores",
                            "valor_empresas_publicas_ti", "valor_outras_estatais", "pct_fabricante_direto", "pct_revendedores"],
      """WITH d AS (SELECT DISTINCT rid, id_compra, marca, tipo, v FROM res_marca)  -- resultado em duas categorias conta uma vez por marca
      SELECT marca, count(DISTINCT id_compra), sum(v), coalesce(sum(v) FILTER (WHERE tipo = 'Fabricante direto'), 0),
        coalesce(sum(v) FILTER (WHERE tipo = 'Revendedor ou integrador'), 0), coalesce(sum(v) FILTER (WHERE tipo = 'Empresa pública de TI'), 0),
        coalesce(sum(v) FILTER (WHERE tipo = 'Outra empresa estatal'), 0),
        100 * coalesce(sum(v) FILTER (WHERE tipo = 'Fabricante direto'), 0) / sum(v), 100 * coalesce(sum(v) FILTER (WHERE tipo = 'Revendedor ou integrador'), 0) / sum(v)
      FROM (SELECT DISTINCT r.id_compra_item, r.ni_fornecedor, r.v, m.marca, m.tipo, m.id_compra, min(m.rid) AS rid FROM res_marca m JOIN res_v r USING (rid) GROUP BY ALL) d
      GROUP BY 1 ORDER BY 3 DESC""")
grava("f2_08_marca_tipo_categoria", ["categoria", "marca", "tipo_vendedor", "compras", "valor_homologado_resultados"],
      "SELECT segmento, marca, tipo, count(DISTINCT id_compra), sum(v) FROM res_marca GROUP BY ALL ORDER BY 1, 2, 5 DESC")
grava("f2_08_top5_revendedores", ["marca", "posicao", "raiz_cnpj", "fornecedor", "compras", "valor_homologado_resultados", "pct_da_marca"],
      """WITH d AS (SELECT DISTINCT r.id_compra_item, r.ni_fornecedor, r.nome_fornecedor, r.v, m.marca, m.tipo, r.id_compra
                    FROM res_marca m JOIN res_v r USING (rid)),
      t AS (SELECT marca, sum(v) AS tv FROM d GROUP BY 1),
      s AS (SELECT marca, substr(ni_fornecedor, 1, 8) AS ni_fornecedor, min(nome_fornecedor) AS nome, count(DISTINCT id_compra) AS n, sum(v) AS v FROM d
            WHERE tipo = 'Revendedor ou integrador' GROUP BY 1, 2)  -- empresa = raiz do CNPJ (matriz e filiais juntas)
      SELECT marca, rk, ni_fornecedor, nome, n, v, 100 * v / tv FROM (
        SELECT s.*, t.tv, row_number() OVER (PARTITION BY s.marca ORDER BY s.v DESC, s.ni_fornecedor) AS rk FROM s JOIN t USING (marca))
      WHERE rk <= 5 ORDER BY marca, rk""")
grava("f2_08_tipo_vendedor_categoria", ["categoria", "tipo_vendedor", "compras", "fornecedores", "valor_homologado_resultados", "pct_da_categoria"],
      """WITH t AS (SELECT segmento, sum(v) AS tv FROM res_tipo GROUP BY 1)
      SELECT segmento, tipo, count(DISTINCT id_compra), count(DISTINCT ni_fornecedor), sum(v), 100 * sum(v) / any_value(tv)
      FROM res_tipo JOIN t USING (segmento) GROUP BY ALL ORDER BY 1, 5 DESC""")
grava("f2_08_empresas_publicas_ti", ["categoria", "cnpj", "fornecedor", "compras", "valor_homologado_resultados"],
      "SELECT segmento, ni_fornecedor, any_value(nome_fornecedor), count(DISTINCT id_compra), sum(v) FROM res_tipo WHERE tipo = 'Empresa pública de TI' GROUP BY 1, 2 ORDER BY 1, 5 DESC")
grava("f2_08_tipo_vendedor_total", ["tipo_vendedor", "compras", "fornecedores", "valor_homologado_resultados_distintos"],
      """SELECT tipo, count(DISTINCT id_compra), count(DISTINCT ni_fornecedor), sum(v) FROM
         (SELECT DISTINCT id_compra, id_compra_item, ni_fornecedor, v, tipo FROM res_tipo) GROUP BY 1 ORDER BY 4 DESC""")
print(len(fab), "pares marca x CNPJ de fabricante;", len(pub), "raizes de empresas publicas de TI;", len(mi), "pares item x marca")
for r in con.sql("SELECT tipo, round(sum(v)/1e6) FROM res_tipo GROUP BY 1 ORDER BY 2 DESC").fetchall():
    print(r)
con.close()
