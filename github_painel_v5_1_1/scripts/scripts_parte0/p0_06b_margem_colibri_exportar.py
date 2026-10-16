"""Margem de preferencia (passo 2): exporta, somente leitura, as tabelas de margem de preferencia (NCMs cobertas por
resolucao CICS) e de mapeamento CATMAT -> NCM do catalogo Colibri para Parquet local.

Mesma conexao de p0_06_margem_colibri_listar.py (copia do catalogo em pasta temporaria, lake em READ_ONLY).
Executar com o Python do ambiente do Colibri:
    C:/Users/mabel/Documents/colibri/env/Scripts/python.exe scripts_parte0/p0_06b_margem_colibri_exportar.py <pasta_temp>
Saidas: tabelas_parte0/colibri_mrt_margem__ncms_cics.parquet, tabelas_parte0/colibri_mrt_tradutor_catmat_ncm.parquet,
        tabelas_parte0/colibri_stg_margem__resolucoes.parquet,
        tabelas_parte0/colibri_int_margem__ncm_prefixos.parquet, tabelas_parte0/colibri_int_ncm_prefixos.parquet
"""
import os
import sys
from urllib.parse import urlparse

RAIZ_COLIBRI = "C:/Users/mabel/Documents/colibri"
SAIDA = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tabelas_parte0"))
sys.path.insert(0, RAIZ_COLIBRI)
os.chdir(RAIZ_COLIBRI)

import duckdb  # noqa: E402
from utils.carregar_segredo import carregar_segredo  # noqa: E402
from utils.criar_cliente import criar_cliente  # noqa: E402
from utils.constantes import NOME_SEGREDO_VISUALIZADOR, BUCKET_PRODUCAO, DATA_PATH  # noqa: E402

pasta = sys.argv[1]
os.makedirs(pasta, exist_ok=True)
catalogo = os.path.join(pasta, "meta_copia_leitura.ducklake")
config = carregar_segredo(NOME_SEGREDO_VISUALIZADOR)
criar_cliente(config).download_file(BUCKET_PRODUCAO, "meta.ducklake", catalogo)

con = duckdb.connect()
for cmd in ("INSTALL httpfs", "LOAD httpfs", "INSTALL ducklake", "LOAD ducklake"):
    con.execute(cmd)
con.execute(f"SET s3_endpoint = '{urlparse(config['endpoint']).netloc}'")
con.execute(f"SET s3_access_key_id = '{config['access_key']}'")
con.execute(f"SET s3_secret_access_key = '{config['secret_key']}'")
con.execute("SET s3_region = 'auto'")
con.execute("SET s3_url_style = 'path'")
con.execute(f"ATTACH 'ducklake:{catalogo}' AS lake (DATA_PATH '{DATA_PATH}', OVERRIDE_DATA_PATH TRUE, READ_ONLY)")
con.execute("USE lake")

for origem, destino in [
    ("main_marts.mrt_margem__ncms_cics", "colibri_mrt_margem__ncms_cics.parquet"),
    ("main_marts.mrt_tradutor_catmat_ncm__mapeamento_ia", "colibri_mrt_tradutor_catmat_ncm.parquet"),
    ("main_staging.stg_margem__resolucoes", "colibri_stg_margem__resolucoes.parquet"),
    # historico de vigencias por prefixo de NCM (todas as resolucoes, nao so a ativa) e expansao prefixo -> NCM
    ("main_intermediate.int_margem__ncm_prefixos", "colibri_int_margem__ncm_prefixos.parquet"),
    ("main_intermediate.int_ncm_prefixos", "colibri_int_ncm_prefixos.parquet"),
]:
    caminho = os.path.join(SAIDA, destino).replace("\\", "/")
    con.execute(f"COPY (SELECT * FROM {origem}) TO '{caminho}' (FORMAT PARQUET)")
    n = con.execute(f"SELECT count(*) FROM '{caminho}'").fetchone()[0]
    print(origem, n, "linhas")
    print(con.execute(f"DESCRIBE SELECT * FROM '{caminho}'").fetchall())
