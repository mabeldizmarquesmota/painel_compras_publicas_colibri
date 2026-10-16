"""Painel v5.1.1, etapa 3: conferencia dos hashes das versoes congeladas, zip de envio, relatorio e congelamento da v5.1.1.

Executar a partir de Processado/, depois de p511_02:  python scripts_painel_v5_1_1/p511_03_relatorio_final.py
Entradas: verificacao_html_v5_1_1/verificacoes.csv, buscas.csv, diff_v5_1_para_v5_1_1.txt; versao_congelada_*/hashes_*.csv;
  versao_congelada_v5_1/painel_v5_1_envio.zip (composicao) e pacote_downloads_v5_1.zip.
Zip de envio: mesma composicao do painel_v5_1_envio.zip (HTML do painel e pacote de downloads), trocando so o arquivo atualizado (o HTML);
  o pacote de downloads nao mudou nesta versao e entra o da v5.1 congelada.
Saidas: relatorio_final_painel_v5_1_1.md; painel_v5_1_1_envio.zip; versao_congelada_v5_1_1/ com hashes_sha256_v5_1_1.csv.
"""
import csv
import hashlib
import os
import platform
import shutil
import sys
import zipfile

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")


def sha(c):
    h = hashlib.sha256()
    with open(c, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


ler = lambda c: list(csv.DictReader(open(c, encoding="utf-8-sig"), delimiter=";"))
HS = []
for v in ("v3", "v4", "v5", "v5_1", "v5_2"):
    d = f"versao_congelada_{v}/"
    if os.path.exists(d):
        reg = ler(d + f"hashes_sha256_{v}.csv")
        HS.append((v.replace("_", "."), len(reg), sum(1 for r in reg if os.path.exists(d + r["arquivo"]) and sha(d + r["arquivo"]) == r["sha256"])))
hs_ok = all(n == i for _, n, i in HS)

ENV0 = zipfile.ZipFile("versao_congelada_v5_1/painel_v5_1_envio.zip").namelist()
assert ENV0 == ["painel_soberania_digital_v5_1.html", "pacote_downloads_v5_1.zip"], ENV0
with zipfile.ZipFile("painel_v5_1_1_envio.zip", "w", zipfile.ZIP_DEFLATED) as z:
    z.write("painel_soberania_digital_v5_1_1.html")
    z.write("versao_congelada_v5_1/pacote_downloads_v5_1.zip", "pacote_downloads_v5_1.zip")
H_HTML, H_ENV = sha("painel_soberania_digital_v5_1_1.html"), sha("painel_v5_1_1_envio.zip")
assert sha("versao_congelada_v5_1/pacote_downloads_v5_1.zip") == {r["arquivo"]: r["sha256"] for r in ler("versao_congelada_v5_1/hashes_sha256_v5_1.csv")}["pacote_downloads_v5_1.zip"]

V = ler("verificacao_html_v5_1_1/verificacoes.csv")
B = ler("verificacao_html_v5_1_1/buscas.csv")
dif = open("verificacao_html_v5_1_1/diff_v5_1_para_v5_1_1.txt", encoding="utf-8").read().split("\n")
EXC = {"2. sem 'COPY (SELECT'": "exceção mantida por decisão da pesquisadora: a ocorrência restante está em outro parágrafo da seção 1 da Metodologia "
                                 "(\"Extração: as tabelas foram exportadas integralmente para Parquet com COPY (SELECT * FROM ...)...\"), que não faz parte da alteração 1; "
                                 "removê-la acrescentaria uma terceira diferença ao diff. O mesmo parágrafo segue na METODOLOGIA_v5_1_1.md.",
       "4. sem travessão (—)": "exceção mantida por decisão da pesquisadora: os 16 travessões estão nos objetos de compra copiados literalmente do PNCP (dados "
                                "embutidos, exibidos nas tabelas de cadeias e nas dicas dos objetos), já presentes na v5.1; nenhum está em texto do painel."}
L = ["# Relatório final do painel, versão 5.1.1", "",
     "Feita a partir de versao_congelada_v5_1/painel_soberania_digital_v5_1.html e de METODOLOGIA_v5_1.md, só com as duas alterações pedidas.", "",
     "## Python", "", f"Versão usada nos scripts do painel (python --version): **Python {platform.python_version()}**, ou seja, 3.14. O rodapé foi gravado.", "",
     "## Diff resumido (v5.1 → v5.1.1)", "",
     "Só duas diferenças, conferidas pelo script: desfazendo as duas substituições, o HTML novo volta byte a byte ao da v5.1 (diff completo em "
     "verificacao_html_v5_1_1/diff_v5_1_para_v5_1_1.txt).", ""]
L += ["```"] + [x for x in dif[2:] if x] + ["```", "",
      "METODOLOGIA_v5_1_1.md: o parágrafo não existe nessa redação no Markdown; o mesmo conteúdo estava em lista, na seção \"## Downloads\" (os dois pacotes, a extração "
      "com COPY e \"Os Parquet não fazem parte do pacote\"). A seção inteira saiu, com o título, sem deixar linha vazia nem título órfão (trecho removido em "
      "verificacao_html_v5_1_1/metodologia_trecho_removido.txt). O rodapé não aparece na metodologia. O cabeçalho do Markdown não foi alterado e continua citando a versão 5.1, "
      "porque o escopo era só as duas alterações.", "",
      "## Verificações", "", "| Verificação | Resultado | Detalhe |", "|---|---|---|"]
for r in V:
    res = "ok" if r["confere"] == "sim" else ("exceção aceita" if r["verificacao"] in EXC else "FALHOU")
    L.append(f"| {r['verificacao']} | {res} | {EXC.get(r['verificacao'], r['detalhe']).replace('|', '/')} |")
L += ["", "Buscas com o local de cada ocorrência: verificacao_html_v5_1_1/buscas.csv. Navegador: Chromium (motor do Chrome), sem internet, em 1440 px e 390 px.", "",
      "## Hashes", "", "| Versão congelada | Registrados | Idênticos no fim |", "|---|---|---|"]
L += [f"| {v} | {n} | {i} |" for v, n, i in HS]
L += ["", f"Versões congeladas inalteradas: {'sim' if hs_ok else 'NÃO'} (a v5.1 também foi conferida antes de começar: 28 de 28). Nenhum script dessas pastas foi executado.", "",
      "## Entrega", "",
      "- Zip de envio: `C:\\Users\\mabel\\OneDrive\\Desktop\\colibri_baixado_duckdb\\Processado\\painel_v5_1_1_envio.zip`, com a mesma composição do painel_v5_1_envio.zip: "
      "painel_soberania_digital_v5_1_1.html (atualizado) e pacote_downloads_v5_1.zip (sem mudança nesta versão, cópia da v5.1 congelada).",
      f"- painel_soberania_digital_v5_1_1.html: `{H_HTML}`", f"- painel_v5_1_1_envio.zip: `{H_ENV}`",
      "- Versão congelada: versao_congelada_v5_1_1/, com hashes_sha256_v5_1_1.csv.", ""]
open("relatorio_final_painel_v5_1_1.md", "w", encoding="utf-8").write("\n".join(L))

DEST = "versao_congelada_v5_1_1"
assert not os.path.exists(DEST), f"{DEST} já existe"
arquivos = ["painel_soberania_digital_v5_1_1.html", "METODOLOGIA_v5_1_1.md", "painel_v5_1_1_envio.zip", "relatorio_final_painel_v5_1_1.md"]
for pasta in ("scripts_painel_v5_1_1", "verificacao_html_v5_1_1"):
    arquivos += sorted(os.path.join(pasta, x).replace("\\", "/") for x in os.listdir(pasta) if os.path.isfile(os.path.join(pasta, x)))
linhas = []
for a in arquivos:
    os.makedirs(os.path.dirname(os.path.join(DEST, a)) or DEST, exist_ok=True)
    shutil.copy2(a, os.path.join(DEST, a))
    h_ = sha(a)
    assert sha(os.path.join(DEST, a)) == h_, a
    linhas.append([a, os.path.getsize(a), h_])
with open(os.path.join(DEST, "hashes_sha256_v5_1_1.csv"), "w", encoding="utf-8", newline="") as fo:
    w = csv.writer(fo, delimiter=";")
    w.writerow(["arquivo", "bytes", "sha256"])
    w.writerows(linhas)
print(f"congeladas inalteradas: {hs_ok} {HS}; v5.1.1 congelada com {len(linhas)} arquivos")
