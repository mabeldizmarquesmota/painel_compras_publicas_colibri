from __future__ import annotations

import csv
from pathlib import Path

import duckdb

BASE = Path(r"c:\Users\mabel\OneDrive\Desktop\colibri_baixado_duckdb")
PARQUET = BASE / "parquet"
OUT = BASE / "Processado"
OUT.mkdir(parents=True, exist_ok=True)
SOURCE_NOTE = "Fonte: PNCP, via Colibri (gestaogovbr). Dados coletados em 28/09/2026. Valores correntes."

con = duckdb.connect(database=":memory:")
con.execute("SET preserve_insertion_order = false")
con.execute("SET threads = 4")


def q(sql: str):
    return con.execute(sql).fetchall()


def clean(value):
    return "" if value is None else str(value).replace("|", "/").replace("\r", " ").replace("\n", " ")


def money(value):
    return "" if value is None else f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def md_table(rows):
    if not rows:
        return "Sem registros."
    headers = list(rows[0])
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join("---" for _ in headers) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(clean(row[h]) for h in headers) + " |")
    return "\n".join(lines)


def write_csv(path: Path, headers, rows):
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)


for name in ["compras", "itens"]:
    path = (PARQUET / f"{name}.parquet").as_posix()
    con.execute(f"CREATE VIEW {name}_raw AS SELECT * FROM read_parquet('{path}')")

con.execute("""CREATE VIEW compras_dedup AS
    SELECT * FROM compras_raw WHERE is_current = TRUE
    QUALIFY ROW_NUMBER() OVER (PARTITION BY id_compra ORDER BY
        TRY_CAST(data_atualizacao AS TIMESTAMP) DESC NULLS LAST,
        TRY_CAST(data_inclusao AS TIMESTAMP) DESC NULLS LAST,
        TRY_CAST(valido_de AS TIMESTAMP) DESC NULLS LAST) = 1""")
con.execute("""CREATE VIEW item_aggregate AS
    SELECT id_compra, COUNT(*) item_count,
        SUM(TRY_CAST(NULLIF(TRIM(valor_total), '') AS DOUBLE)) item_sum,
        SUM(TRY_CAST(NULLIF(TRIM(quantidade), '') AS DOUBLE) *
            TRY_CAST(NULLIF(TRIM(valor_unitario_estimado), '') AS DOUBLE)) qty_unit_sum
    FROM itens_raw WHERE is_current = TRUE GROUP BY id_compra""")

# Audit purchase totals against item totals and quantity * unit price.
con.execute("""CREATE VIEW value_audit AS
    SELECT c.id_compra,c.orgao_entidade_razao_social orgao,
        c.orgao_entidade_esfera_id esfera_codigo,c.orgao_entidade_poder_id poder_codigo,
        c.modalidade_nome AS modalidade,c.situacao_compra_nome AS situacao,c.objeto_compra,c.data_publicacao_pncp,
        TRY_CAST(NULLIF(TRIM(c.valor_total_estimado), '') AS DOUBLE) valor_estimado,
        TRY_CAST(NULLIF(TRIM(c.valor_total_homologado), '') AS DOUBLE) valor_homologado,
        a.item_count,a.item_sum,a.qty_unit_sum,
        CASE WHEN c.valor_total_estimado IS NOT NULL AND a.item_sum IS NOT NULL AND a.item_sum > 0
            THEN GREATEST(TRY_CAST(NULLIF(TRIM(c.valor_total_estimado), '') AS DOUBLE)/a.item_sum,
                          a.item_sum/TRY_CAST(NULLIF(TRIM(c.valor_total_estimado), '') AS DOUBLE)) END ratio_estimado_item,
        CASE WHEN c.valor_total_homologado IS NOT NULL AND a.item_sum IS NOT NULL AND a.item_sum > 0
            THEN GREATEST(TRY_CAST(NULLIF(TRIM(c.valor_total_homologado), '') AS DOUBLE)/a.item_sum,
                          a.item_sum/TRY_CAST(NULLIF(TRIM(c.valor_total_homologado), '') AS DOUBLE)) END ratio_homologado_item,
        CASE WHEN c.valor_total_estimado IS NOT NULL AND a.qty_unit_sum IS NOT NULL AND a.qty_unit_sum > 0
            THEN GREATEST(TRY_CAST(NULLIF(TRIM(c.valor_total_estimado), '') AS DOUBLE)/a.qty_unit_sum,
                          a.qty_unit_sum/TRY_CAST(NULLIF(TRIM(c.valor_total_estimado), '') AS DOUBLE)) END ratio_estimado_qty_unit,
        CASE WHEN c.valor_total_homologado IS NOT NULL AND a.qty_unit_sum IS NOT NULL AND a.qty_unit_sum > 0
            THEN GREATEST(TRY_CAST(NULLIF(TRIM(c.valor_total_homologado), '') AS DOUBLE)/a.qty_unit_sum,
                          a.qty_unit_sum/TRY_CAST(NULLIF(TRIM(c.valor_total_homologado), '') AS DOUBLE)) END ratio_homologado_qty_unit
    FROM compras_dedup c LEFT JOIN item_aggregate a USING (id_compra)""")

con.execute("""CREATE VIEW value_audit_flagged AS
    SELECT *, CASE WHEN
        ratio_estimado_item >= 1000 OR ratio_homologado_item >= 1000 OR
        ratio_estimado_qty_unit >= 1000 OR ratio_homologado_qty_unit >= 1000
        THEN TRUE ELSE FALSE END flag_valor_suspeito,
        CASE WHEN ratio_estimado_item >= 1000 THEN 'estimado_vs_soma_itens'
             WHEN ratio_homologado_item >= 1000 THEN 'homologado_vs_soma_itens'
             WHEN ratio_estimado_qty_unit >= 1000 THEN 'estimado_vs_quantidade_unitario'
             WHEN ratio_homologado_qty_unit >= 1000 THEN 'homologado_vs_quantidade_unitario'
             ELSE '' END motivo_valor_suspeito
    FROM value_audit""")

audit_parquet = (OUT / "etapa2_compras_auditadas.parquet").as_posix().replace("'", "''")
con.execute(f"COPY (SELECT * FROM value_audit_flagged) TO '{audit_parquet}' (FORMAT PARQUET)")

# 50 largest values, including every requested comparison column.
audit_headers = ["id_compra", "orgao", "esfera_codigo", "poder_codigo", "modalidade", "objeto_compra", "data_publicacao_pncp", "valor_estimado", "valor_homologado", "item_count", "item_sum", "qty_unit_sum", "ratio_estimado_item", "ratio_homologado_item", "ratio_estimado_qty_unit", "ratio_homologado_qty_unit", "flag_valor_suspeito", "motivo_valor_suspeito"]
for value_field, label in [("valor_estimado", "estimado"), ("valor_homologado", "homologado")]:
    rows = q(f"SELECT {', '.join(audit_headers)} FROM value_audit_flagged WHERE {value_field} IS NOT NULL ORDER BY {value_field} DESC LIMIT 50")
    records = [dict(zip(audit_headers, row)) for row in rows]
    write_csv(OUT / f"etapa2_extremos_50_{label}.csv", audit_headers, records)

# Suspicious values are retained in the purchase table but excluded only from value charts.
flagged_count = q("SELECT COUNT(*),COALESCE(SUM(valor_estimado),0),COALESCE(SUM(valor_homologado),0) FROM value_audit_flagged WHERE flag_valor_suspeito")[0]
annual_before_after = q("""SELECT ano_referencia,
    COUNT(*) numero_compras,
    SUM(valor_estimado) valor_estimado_antes,
    SUM(valor_homologado) valor_homologado_antes,
    SUM(valor_estimado) FILTER(WHERE NOT flag_valor_suspeito) valor_estimado_depois,
    SUM(valor_homologado) FILTER(WHERE NOT flag_valor_suspeito) valor_homologado_depois,
    COUNT(*) FILTER(WHERE flag_valor_suspeito) compras_suspeitas
    FROM (SELECT YEAR(TRY_CAST(data_publicacao_pncp AS DATE)) ano_referencia,* FROM value_audit_flagged)
    GROUP BY 1 ORDER BY 1""")
annual_headers = ["ano_referencia", "numero_compras", "valor_estimado_antes", "valor_homologado_antes", "valor_estimado_depois", "valor_homologado_depois", "compras_suspeitas"]
annual_records = [dict(zip(annual_headers, row)) for row in annual_before_after]
write_csv(OUT / "etapa2_totais_antes_depois_suspeitos.csv", annual_headers, annual_records)

# PNCP semantic labels. The API schema is the source; raw false is not a documented code.
esfera_map = {"F": "Federal", "E": "Estadual", "M": "Municipal", "D": "Distrital", "N": "Não se aplica", "false": "Não identificado", "(nulo)": "Não identificado"}
poder_map = {"E": "Executivo", "J": "Judiciário", "L": "Legislativo", "N": "Não se aplica", "false": "Não identificado", "(nulo)": "Não identificado"}

def label(mapping, code):
    return mapping.get(str(code), "Não identificado")

# The false category is explicitly reported rather than silently recoded.
false_sphere = q("""SELECT orgao_entidade_razao_social,orgao_entidade_poder_id,unidade_orgao_uf_sigla,COUNT(*) n
    FROM compras_dedup WHERE orgao_entidade_esfera_id='false'
    GROUP BY 1,2,3 ORDER BY n DESC LIMIT 20""")
false_total = q("SELECT COUNT(*) FROM compras_dedup WHERE orgao_entidade_esfera_id='false'")[0][0]

con.execute("""CREATE VIEW base_etapa2 AS
    SELECT id_compra,YEAR(TRY_CAST(data_publicacao_pncp AS DATE)) ano_referencia,
           CASE WHEN esfera_codigo='false' THEN 'Não identificado'
               WHEN esfera_codigo IS NULL THEN 'Não identificado'
               ELSE esfera_codigo END esfera_codigo,
           CASE WHEN poder_codigo IS NULL THEN 'Não identificado' ELSE poder_codigo END poder_codigo,
        COALESCE(modalidade,'Não identificado') modalidade,
        COALESCE(situacao,'(nulo)') situacao,
        valor_estimado,valor_homologado,flag_valor_suspeito,
        orgao FROM value_audit_flagged""")

# Long-form detailed table; counts remain unfiltered, value sums exclude flagged purchases.
rows = q("""SELECT ano_referencia,'esfera' dimensao,esfera_codigo categoria,
    COUNT(*) numero_compras,
    SUM(valor_estimado) FILTER(WHERE NOT flag_valor_suspeito) valor_estimado,
    SUM(valor_homologado) FILTER(WHERE NOT flag_valor_suspeito) valor_homologado,
    COUNT(*) FILTER(WHERE flag_valor_suspeito) compras_suspeitas
    FROM base_etapa2 GROUP BY 1,2,3
    UNION ALL SELECT ano_referencia,'poder',poder_codigo,COUNT(*),
    SUM(valor_estimado) FILTER(WHERE NOT flag_valor_suspeito),SUM(valor_homologado) FILTER(WHERE NOT flag_valor_suspeito),COUNT(*) FILTER(WHERE flag_valor_suspeito)
    FROM base_etapa2 GROUP BY 1,2,3
    UNION ALL SELECT ano_referencia,'modalidade',modalidade,COUNT(*),
    SUM(valor_estimado) FILTER(WHERE NOT flag_valor_suspeito),SUM(valor_homologado) FILTER(WHERE NOT flag_valor_suspeito),COUNT(*) FILTER(WHERE flag_valor_suspeito)
    FROM base_etapa2 GROUP BY 1,2,3 ORDER BY 1,2,3""")
headers = ["ano_referencia", "dimensao", "categoria", "numero_compras", "valor_estimado", "valor_homologado", "compras_suspeitas"]
row_dicts = [dict(zip(headers, row)) for row in rows]
write_csv(OUT / "etapa2_por_ano_dimensao.csv", headers, row_dicts)

situations = q("""SELECT situacao,COUNT(*) numero_compras,
    SUM(valor_estimado) FILTER(WHERE NOT flag_valor_suspeito) valor_estimado,
    SUM(valor_homologado) FILTER(WHERE NOT flag_valor_suspeito) valor_homologado,
    COUNT(*) FILTER(WHERE flag_valor_suspeito) compras_suspeitas
    FROM base_etapa2 GROUP BY 1 ORDER BY numero_compras DESC""")
situation_headers = ["situacao_compra_nome", "numero_compras", "valor_estimado", "valor_homologado", "compras_suspeitas"]
situation_records = [dict(zip(situation_headers, row)) for row in situations]
write_csv(OUT / "etapa2_situacoes.csv", situation_headers, situation_records)

totals = q("""SELECT ano_referencia,COUNT(*) numero_compras,
    SUM(valor_estimado) FILTER(WHERE NOT flag_valor_suspeito) valor_estimado,
    SUM(valor_homologado) FILTER(WHERE NOT flag_valor_suspeito) valor_homologado,
    SUM(valor_estimado) valor_estimado_antes,SUM(valor_homologado) valor_homologado_antes,
    COUNT(*) FILTER(WHERE flag_valor_suspeito) compras_suspeitas
    FROM base_etapa2 GROUP BY 1 ORDER BY 1""")
total_headers = ["ano_referencia", "numero_compras", "valor_estimado", "valor_homologado", "valor_estimado_antes", "valor_homologado_antes", "compras_suspeitas"]
total_records = [dict(zip(total_headers, row)) for row in totals]
write_csv(OUT / "etapa2_totais_por_ano.csv", total_headers, total_records)

# Markdown extreme-value report and treatment summary.
extreme_sections = ["# Auditoria de valores extremos\n", f"Regra: `flag_valor_suspeito = true` quando valor de compra diverge da soma dos itens ou de quantidade x valor unitario por fator >= 1.000, com comparador disponivel. Compras sem itens comparaveis nao foram marcadas automaticamente.\n\n", f"Foram marcadas {flagged_count[0]:,} compras; elas permanecem na base e sao excluidas apenas das somas de valor dos graficos. Valor estimado excluido: R$ {flagged_count[1]:,.2f}; valor homologado excluido: R$ {flagged_count[2]:,.2f}.\n\n", "## Totais anuais antes e depois\n", md_table([{k: money(v) if k.startswith('valor_') else v for k,v in row.items()} for row in annual_records]), "\n\n"]
for label, title in [("estimado", "50 maiores valores estimados"), ("homologado", "50 maiores valores homologados")]:
    path = OUT / f"etapa2_extremos_50_{label}.csv"
    with path.open(encoding="utf-8-sig", newline="") as handle:
        records = list(csv.DictReader(handle))
    display = []
    for record in records:
        display.append({"id_compra":record["id_compra"],"orgao":record["orgao"],"modalidade":record["modalidade"],"valor_estimado_R$":money(float(record["valor_estimado"])) if record["valor_estimado"] else "","valor_homologado_R$":money(float(record["valor_homologado"])) if record["valor_homologado"] else "","soma_itens_R$":money(float(record["item_sum"])) if record["item_sum"] else "","quantidade_x_unitario_R$":money(float(record["qty_unit_sum"])) if record["qty_unit_sum"] else "","ratio_maximo":record["ratio_estimado_item"] or record["ratio_homologado_item"],"flag_valor_suspeito":record["flag_valor_suspeito"],"objeto_compra":record["objeto_compra"]})
    extreme_sections += [f"## {title}\n", md_table(display), "\n\n"]
extreme_sections += ["## Categoria esfera `false`\n", f"Foram encontradas {false_total} compras. `false` nao consta entre os codigos semanticos adotados; aparece associado principalmente a orgaos federais, mas com poder/UF heterogeneos, portanto foi rotulado como `Não identificado` e nao recodificado silenciosamente. Exemplos:\n\n", md_table([{"orgao":r[0],"poder_codigo":r[1],"UF":r[2],"compras":r[3]} for r in false_sphere]), "\n\n", f"Fonte do mapeamento semantico: esquema/documentacao da API Consulta do PNCP, disponível em https://pncp.gov.br/api/consulta/swagger-ui.html; códigos nao documentados permanecem `Não identificado`.\n"]
(OUT / "etapa2_extremos.md").write_text("\n".join(extreme_sections), encoding="utf-8")

# Main total tables for charts: all three metrics are rendered as separate figures.
main_rows = q("""SELECT ano_referencia,COUNT(*) numero_compras,
    SUM(valor_estimado) FILTER(WHERE NOT flag_valor_suspeito) valor_estimado,
    SUM(valor_homologado) FILTER(WHERE NOT flag_valor_suspeito) valor_homologado,
    COUNT(*) FILTER(WHERE flag_valor_suspeito) compras_suspeitas
    FROM base_etapa2 GROUP BY 1 ORDER BY 1""")

try:
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    from matplotlib.ticker import FuncFormatter
except ImportError as exc:
    raise RuntimeError("matplotlib e necessario para os graficos") from exc

partial_years = {2021, 2026}
source_note = SOURCE_NOTE
br_number = FuncFormatter(lambda value, pos: f"{int(value):,}".replace(",", "."))
br_billions = FuncFormatter(lambda value, pos: f"{value:.1f}")


def plot_metric(rows_to_plot, metric, title, ylabel, filename, scale=1):
    years = [row[0] for row in rows_to_plot if row[0] is not None]
    fig, ax = plt.subplots(figsize=(12, 7))
    categories = sorted({row[2] for row in rows_to_plot})
    for category in categories:
        values = {row[0]: row[3] for row in rows_to_plot if row[2] == category}
        ax.plot(years, [(values.get(year) or 0) / scale for year in years], marker="o", linewidth=2 if category == "Total geral" else 1.5, label=category)
        partial = [year for year in years if year in partial_years]
        ax.scatter(partial, [(values.get(year) or 0) / scale for year in partial], marker="s", facecolors="white", edgecolors="black", zorder=4)
    ax.set_title(title)
    ax.set_xlabel("Ano de publicação")
    ax.set_ylabel(ylabel)
    ax.grid(True, alpha=0.25)
    if metric == "numero_compras":
        ax.yaxis.set_major_formatter(br_number)
    else:
        ax.yaxis.set_major_formatter(br_billions)
    ax.set_xticks(years)
    handles, labels = ax.get_legend_handles_labels()
    handles.extend([Line2D([0], [0], marker="s", color="black", markerfacecolor="white", linestyle="None"), Line2D([0], [0], color="none")])
    labels.extend(["Ano parcial", "2021 desde 10/08; 2026 até 24/05"])
    ax.legend(handles, labels, loc="upper left", bbox_to_anchor=(1.01, 1), fontsize=8)
    ax.text(0.01, -0.18, source_note + "  Anos parciais: 2021 (desde 10/08) e 2026 (até 24/05).", transform=ax.transAxes, fontsize=8)
    fig.tight_layout(rect=(0, 0.08, 0.82, 1))
    fig.savefig(OUT / filename, dpi=160)
    plt.close(fig)

main_plot_rows = []
for row in main_rows:
    main_plot_rows.append((row[0], "total", "Total geral", row[1]))
    # metric-specific replacement happens below
for metric, ylabel, filename, scale in [("numero_compras", "Quantidade de compras", "etapa2_grafico_total_quantidade.png", 1), ("valor_estimado", "Valor estimado (R$ bilhões, valores correntes)", "etapa2_grafico_total_estimado.png", 1_000_000_000), ("valor_homologado", "Valor homologado (R$ bilhões, valores correntes)", "etapa2_grafico_total_homologado.png", 1_000_000_000)]:
    data = [(row[0], "total", "Total geral", row[1 if metric == "numero_compras" else 2 if metric == "valor_estimado" else 3]) for row in main_rows]
    plot_metric(data, metric, f"Etapa 2 - total geral anual: {ylabel}", ylabel, filename.replace("etapa2_", "etapa2_v2_"), scale)

for dimension, column in [("esfera", 1), ("poder", 1), ("modalidade", 1)]:
    subset = [row for row in row_dicts if row["dimensao"] == dimension]
    for metric, field, ylabel, scale in [("numero_compras", "numero_compras", "Quantidade de compras", 1), ("valor_estimado", "valor_estimado", "Valor estimado (R$ bilhões, valores correntes)", 1_000_000_000), ("valor_homologado", "valor_homologado", "Valor homologado (R$ bilhões, valores correntes)", 1_000_000_000)]:
        data = [(row["ano_referencia"], dimension, row["categoria"], row[field]) for row in subset]
        plot_metric(data, metric, f"Etapa 2 - {ylabel} por {dimension}", ylabel, f"etapa2_v2_grafico_{dimension}_{metric}.png", scale)

report = ["# Etapa 2 - Tratamento de valores e agregacoes\n", "## Fonte e regra de tratamento\n", SOURCE_NOTE + "\n\n", f"A flag `flag_valor_suspeito` marcou {flagged_count[0]:,} compras. A base auditada completa, sem apagar compras, está em `etapa2_compras_auditadas.parquet`; apenas as somas de valor dos graficos excluem as marcadas. Valor estimado excluido: R$ {flagged_count[1]:,.2f}; homologado excluido: R$ {flagged_count[2]:,.2f}.\n\n", "Regra: incoerencia de pelo menos 1.000 vezes entre o valor da compra e a soma dos itens ou quantidade x valor unitario, quando o comparador esta disponivel.\n\n", "## Totais anuais antes e depois\n", md_table([{k: money(v) if k.startswith('valor_') else v for k,v in row.items()} for row in annual_records]), "\n\n", "## Totais por situacao\n", md_table([{k: money(v) if k.startswith('valor_') else v for k,v in row.items()} for row in situation_records]), "\n\n", "## Rotulos\n", "Esfera: F Federal, E Estadual, M Municipal, D Distrital, N Não se aplica. Poder: E Executivo, J Judiciário, L Legislativo, N Não se aplica. `false` e demais códigos nao documentados ficam como `Não identificado`. Fonte: esquema/documentacao da API Consulta do PNCP (https://pncp.gov.br/api/consulta/swagger-ui.html).\n\n", "## Notas\n", "- 2021 e parcial desde 10/08; 2026 e parcial ate 24/05.\n", "- A cobertura do PNCP e parcial antes de 2024, no contexto do fim da transicao da Lei 14.133/2021 em 30/12/2023.\n", "- Em registro de precos, valor homologado e teto de ata, nao gasto executado.\n"]
(OUT / "etapa2_relatorio.md").write_text("\n".join(report), encoding="utf-8")

print("Etapa 2 atualizada:", OUT)
print("Suspeitas:", flagged_count)
print("Falso esfera:", false_total)
