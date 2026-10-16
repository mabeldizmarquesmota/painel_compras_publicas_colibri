"""Painel v5.1.1, etapa 1: HTML e metodologia da versao 5.1.1 (so duas mudancas sobre a v5.1 congelada).

Executar a partir de Processado/:  python scripts_painel_v5_1_1/p511_01_painel.py
Entradas (somente leitura): versao_congelada_v5_1/painel_soberania_digital_v5_1.html e METODOLOGIA_v5_1.md.
Mudancas: (1) sai o paragrafo sob os botoes de download da aba Metodologia (e, na metodologia em Markdown, a secao Downloads, que tem o
  mesmo conteudo em lista); (2) rodape novo. Nada mais muda: o script confere que o HTML novo e igual ao da v5.1 com exatamente essas duas
  substituicoes e grava o diff.
Saidas: painel_soberania_digital_v5_1_1.html, METODOLOGIA_v5_1_1.md, verificacao_html_v5_1_1/diff_v5_1_para_v5_1_1.txt.
"""
import difflib
import os
import platform
import re
import sys

sys.dont_write_bytecode = True
sys.stdout.reconfigure(encoding="utf-8")
OUT = "verificacao_html_v5_1_1"
os.makedirs(OUT, exist_ok=True)
for a in ("painel_soberania_digital_v5_1_1.html", "METODOLOGIA_v5_1_1.md"):
    assert not os.path.exists(a) or "--refazer" in sys.argv, f"{a} já existe: não sobrescrever sem autorização"
assert platform.python_version_tuple()[:2] == ("3", "14"), platform.python_version()  # o rodape cita Python 3.14

v51 = open("versao_congelada_v5_1/painel_soberania_digital_v5_1.html", encoding="utf-8").read()
RODAPE = ("Versão 5.1.1, gerada em 06/10/2026. Base extraída em 28/09/2026. Fonte: PNCP, via Colibri (gestaogovbr). Elaboração: Mabel Mota para discussão "
          "interna no Ipea. Ferramentas: Python 3.14.")
m = re.search(r"<p class='nota-dl'>Os dois pacotes são os mesmos arquivos de <code>pacote_downloads_v5_1\.zip</code>.*?Os Parquet não fazem parte do pacote\.</p>", v51)
assert m and v51.count("<p class='nota-dl'>") == 1
PAR = m.group(0)
f = re.search(r"<footer>.*?</footer>", v51)
assert f and v51.count("<footer>") == 1
ROD_ANT = f.group(0)
novo = v51.replace(PAR, "", 1).replace(ROD_ANT, f"<footer>{RODAPE}</footer>", 1)
# so as duas diferencas: desfazendo as duas substituicoes volta-se exatamente a v5.1
assert novo.replace(f"<footer>{RODAPE}</footer>", ROD_ANT, 1)[:m.start()] + PAR + novo.replace(f"<footer>{RODAPE}</footer>", ROD_ANT, 1)[m.start():] == v51
open("painel_soberania_digital_v5_1_1.html", "w", encoding="utf-8").write(novo)

# diff legivel: linhas alteradas, com o trecho alterado de cada linha (as linhas do HTML podem ter milhares de caracteres)
la, lb = v51.split("\n"), novo.split("\n")
dif = ["Diff entre versao_congelada_v5_1/painel_soberania_digital_v5_1.html e painel_soberania_digital_v5_1_1.html", ""]
for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(None, la, lb, autojunk=False).get_opcodes():
    if tag == "equal":
        continue
    for k, (x, y) in enumerate(zip(la[i1:i2], lb[j1:j2])):
        p = 0  # prefixo e sufixo comuns: mostra o trecho alterado inteiro
        while p < min(len(x), len(y)) and x[p] == y[p]:
            p += 1
        q = 0
        while q < min(len(x), len(y)) - p and x[-1 - q] == y[-1 - q]:
            q += 1
        dif += [f"linha {i1 + k + 1}, a partir do caractere {p + 1}:", f"  - {x[p:len(x) - q]}", f"  + {y[p:len(y) - q]}", ""]
    assert i2 - i1 == j2 - j1, "número de linhas mudou"
open(f"{OUT}/diff_v5_1_para_v5_1_1.txt", "w", encoding="utf-8").write("\n".join(dif))

# metodologia em Markdown: a secao Downloads e a versao em lista do mesmo paragrafo (pacote, extracao e Parquet)
md = open("METODOLOGIA_v5_1.md", encoding="utf-8").read()
sec = re.search(r"## Downloads\n\n- Scripts executados.*?Os Parquet não fazem parte do pacote\.\n\n", md, flags=re.S)
assert sec and md.count("## Downloads") == 1
md_novo = md.replace(sec.group(0), "", 1)
assert "\n\n\n" not in md_novo[max(0, sec.start() - 5):sec.start() + 5]
open("METODOLOGIA_v5_1_1.md", "w", encoding="utf-8").write(md_novo)
open(f"{OUT}/metodologia_trecho_removido.txt", "w", encoding="utf-8").write(sec.group(0))
print("ok | python", platform.python_version(), "| diff:", len([x for x in dif if x.startswith("linha")]), "trechos")
print("\n".join(dif))
