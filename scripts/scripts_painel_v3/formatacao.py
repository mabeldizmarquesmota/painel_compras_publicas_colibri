"""Formatacao numerica do painel (padrao brasileiro), identica as funcoes JavaScript do painel.

Regras: valores em escala (bi, mi, mil) com uma casa decimal abaixo de 100 e nenhuma a partir de 100; percentuais com
uma casa abaixo de 10, nenhuma a partir de 10 e tres abaixo de 0,1; contagens inteiras; ',0' omitido; arredondamento
meio para cima sobre a representacao decimal mais curta do valor calculado. Valores em bilhoes so a partir de R$ 1 bi;
abaixo disso, em milhoes. Excecao: indicador de margem de preferencia por NCM em R$ milhoes com uma casa.
Usado por p1_02_painel.py e p1_04_conferencia.py.
"""
import re
from decimal import Decimal, ROUND_HALF_UP


def _dec(x, casas):
    q = Decimal(1).scaleb(-casas)
    # arredonda a partir da representacao decimal mais curta do numero (repr), como o Intl.NumberFormat do navegador
    return Decimal(repr(float(x))).quantize(q, rounding=ROUND_HALF_UP)


def fmt_num(x, casas=0):
    d = _dec(x, casas)
    neg = d < 0
    s = f"{abs(d):.{casas}f}"
    inteiro, _, frac = s.partition(".")
    inteiro = re.sub(r"(?<=\d)(?=(\d{3})+$)", ".", inteiro)
    out = inteiro + ("," + frac if casas and set(frac) != {"0"} else "")
    return ("-" if neg and out.strip("0,.") else "") + out


def fmt_escala(v):  # valores em escala (bi, mi, mil): uma casa abaixo de 100, nenhuma a partir de 100
    return fmt_num(v, 1 if abs(_dec(v, 1)) < 100 else 0)


def fmt_pct(p):  # percentuais: '< 0,001%' abaixo disso; tres casas abaixo de 0,1; uma casa abaixo de 10; nenhuma a partir de 10
    a = abs(float(p))
    if 0 < a < 0.001:
        return "< 0,001%"
    if 0 < a < 0.1:
        return fmt_num(p, 3) + "%"
    return fmt_num(p, 1 if abs(_dec(p, 1)) < 10 else 0) + "%"


def bi(x):  # bilhoes a partir de R$ 1 bi; abaixo disso, milhoes (nunca "R$ 1 bi" por arredondamento)
    if abs(float(x)) < 1e9:
        return mi(x)
    return "R$ " + fmt_escala(float(x) / 1e9) + " bi"


def mi(x):
    return "R$ " + fmt_escala(float(x) / 1e6) + " mi"


def mi1(x):  # indicador de margem por NCM: R$ milhoes com uma casa
    return "R$ " + fmt_num(float(x) / 1e6, 1) + " mi"


def reais(x, casas=2):
    return "R$ " + fmt_num(x, casas)


def inteiro(x):
    return fmt_num(x, 0)


def vauto(x):  # valor com a unidade adequada: bi a partir de R$ 1 bi, mi a partir de R$ 1 mi, mil abaixo
    x = float(x)
    if abs(x) >= 1e9:
        return bi(x)
    if abs(x) >= 1e6:
        return mi(x)
    return "R$ " + fmt_escala(x / 1e3) + " mil"
