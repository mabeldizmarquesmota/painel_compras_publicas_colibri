"""Margem de preferencia (passo 1): lista as tabelas e views do catalogo Colibri, somente leitura.

O arquivo C:/Users/mabel/Documents/colibri/ducklake_session.duckdb (e o catalogo local meta.ducklake) estavam
bloqueados pelo processo "colibri lake ui" aberto na maquina. Para nao interferir nele, este script baixa uma
copia do catalogo (s3://colibri-prod/meta.ducklake) para uma pasta temporaria, com a credencial de
visualizador ja configurada no Colibri, e anexa o lake em modo READ_ONLY. Nada e gravado no bucket.

Executar com o Python do ambiente do Colibri:
    C:/Users/mabel/Documents/colibri/env/Scripts/python.exe scripts_parte0/p0_06_margem_colibri_listar.py <pasta_temp>
Saida: tabelas_parte0/p0_colibri_catalogo.csv
"""
import csv
import os
import sys
from urllib.parse import urlparse

RAIZ_COLIBRI = "C:/Users/mabel/Documents/colibri"
sys.path.insert(0, RAIZ_COLIBRI)
os.chdir(RAIZ_COLIBRI)  # carregar_segredo le .segredos.yml a partir da raiz do projeto

import duckdb  # noqa: E402
from utils.carregar_segredo import carregar_segredo  # noqa: E402
from utils.criar_cliente import criar_cliente  # noqa: E402
from utils.constantes import NOME_SEGREDO_VISUALIZADOR, BUCKET_PRODUCAO, DATA_PATH  # noqa: E402

pasta = sys.argv[1]
os.makedirs(pasta, exist_ok=True)
catalogo = os.path.join(pasta, "meta_copia_leitura.ducklake")

config = carregar_segredo(NOME_SEGREDO_VISUALIZADOR)
criar_cliente(config).download_file(BUCKET_PRODUCAO, "meta.ducklake", catalogo)

con = duckdb.connect()  # banco em memoria, sem arquivo de sessao
for cmd in ("INSTALL httpfs", "LOAD httpfs", "INSTALL ducklake", "LOAD ducklake"):
    con.execute(cmd)
con.execute(f"SET s3_endpoint = '{urlparse(config['endpoint']).netloc}'")
con.execute(f"SET s3_access_key_id = '{config['access_key']}'")
con.execute(f"SET s3_secret_access_key = '{config['secret_key']}'")
con.execute("SET s3_region = 'auto'")
con.execute("SET s3_url_style = 'path'")
con.execute(f"ATTACH 'ducklake:{catalogo}' AS lake (DATA_PATH '{DATA_PATH}', OVERRIDE_DATA_PATH TRUE, READ_ONLY)")

rows = con.execute("""
    SELECT schema_name, table_name, 'tabela' AS tipo FROM duckdb_tables() WHERE database_name = 'lake'
    UNION ALL
    SELECT schema_name, view_name, 'view' FROM duckdb_views() WHERE database_name = 'lake' AND NOT internal
    ORDER BY 1, 2
""").fetchall()
saida = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tabelas_parte0", "p0_colibri_catalogo.csv")
with open(saida, "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, delimiter=";")
    w.writerow(["schema", "nome", "tipo"])
    w.writerows(rows)
print(len(rows), "objetos no catalogo")
for r in rows:
    if any(k in r[1].lower() for k in ("margem", "ncm", "catmat", "cics", "tradutor")):
        print(r)
