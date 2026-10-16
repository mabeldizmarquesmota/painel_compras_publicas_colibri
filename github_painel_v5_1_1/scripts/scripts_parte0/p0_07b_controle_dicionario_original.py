"""Controle: aplica o mesmo calculo de p0_07_soberania.sql a classificacao da etapa 4
(dicionario original: compras_segmentos.parquet e itens_seg_match.parquet), para verificar se o script reproduz
os valores das versoes anteriores do painel e isolar o efeito do ajuste do dicionario.
Executar a partir de Processado/ (usa o banco de trabalho scripts_parte0/p0.duckdb, depois de p0_01 e p0_07).
Saida: tabelas_parte0/p0_controle_dicionario_original.csv
"""
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
import subprocess

sql = open("scripts_parte0/p0_07_soberania.sql", encoding="utf-8").read()
sql = re.sub(r"\bcat_compra\b", "cat_compra_v1", sql)
sql = re.sub(r"\bitem_match\b", "item_match_v1", sql)
sql = re.sub(r"\bp0_", "p0v1_", sql)
# tabelas intermediarias com nome proprio, para nao sobrescrever as da classificacao final
sql = re.sub(r"\b(item_val|cat_itens|cat_valor|c_obj|d_itens|compra_unica|tot_ano|res_cat_valid|res_cat)\b", r"\1_v1", sql)
sql = re.sub(r"COPY p0v1_\w+ TO '[^']+' \(HEADER, DELIMITER ';'\);\n", "", sql)
sql = re.sub(r"SELECT \* FROM p0v1_\w+;\n", "", sql)
prefixo = """
CREATE OR REPLACE TABLE cat_compra_v1 AS
SELECT DISTINCT id_compra, segmento, local_match FROM read_parquet('compras_segmentos.parquet')
WHERE id_compra IN (SELECT id_compra FROM bl);
CREATE OR REPLACE TABLE item_match_v1 AS
SELECT DISTINCT id_compra_item, id_compra, segmento FROM read_parquet('itens_seg_match.parquet');
"""
sufixo = """
COPY (SELECT 'dicionario original (etapa 4)' AS classificacao, * EXCLUDE (recorte) FROM p0v1_soberania_tres_regras
      UNION ALL
      SELECT 'dicionario final', * EXCLUDE (recorte) FROM p0_soberania_tres_regras)
  TO 'tabelas_parte0/p0_controle_dicionario_original.csv' (HEADER, DELIMITER ';');
SELECT * FROM read_csv('tabelas_parte0/p0_controle_dicionario_original.csv', delim=';');
"""
r = subprocess.run(["duckdb", "scripts_parte0/p0.duckdb"], input=prefixo + sql + sufixo, text=True,
                   capture_output=True, encoding="utf-8", errors="replace")
print(r.stdout[-3000:], r.stderr[-2000:])
