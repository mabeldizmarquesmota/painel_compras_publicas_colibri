# Painel de compras públicas de tecnologias críticas para a soberania digital

Painel do projeto do Ipea **"Novas soluções para o governo digital: Soberania Digital, Inteligência Artificial e Infraestruturas Públicas Digitais"**.

Mede o peso das tecnologias críticas para a soberania digital nas compras do Estado brasileiro. Usa as compras registradas no Portal Nacional de Contratações Públicas (PNCP) entre 10/08/2021 e 24/05/2026, na base ComprasGov do [Colibri](https://gestaogovbr.github.io/colibri/), extraída em 28/09/2026.

O painel é um único arquivo HTML. Funciona sem internet: dados, gráficos e bibliotecas ficam embutidos no arquivo.

## Principais números (2021 a 2026, valores nominais)

| Indicador | Valor |
|---|---|
| Compras publicadas no PNCP | 875.682 |
| Valor global homologado | R$ 952 bi |
| Compras de tecnologias críticas (seis categorias) | R$ 34,8 bi (3,7% do total) |
| Fornecedores vencedores / órgãos compradores nas seis categorias | 5.369 / 1.693 |
| Tecnologia de inteligência artificial | 983 compras, R$ 1,28 bi |
| Capacitação em inteligência artificial | 1.471 compras, R$ 34,9 mi |

## Como abrir

Baixe `painel_soberania_digital_v5_1_1.html` e abra no navegador.

O painel tem cinco abas:

- **Sobre:** contexto, objetivo, guia de leitura e fontes.
- **Compras públicas:** panorama de todas as compras (ano, esfera, poder e modalidade).
- **Tecnologias críticas para a soberania digital:** seis categorias (nuvem, plataformas e licenciamento, data center, segurança cibernética, inteligência artificial e identidade e infraestrutura pública digital), modalidades, fornecedores, órgãos, marcas e instrumentos de política.
- **Inteligência artificial:** tipos de solução, fornecedores, órgãos, marcas e capacitação.
- **Metodologia:** procedimentos, critérios e downloads dos scripts e das tabelas agregadas.

Os filtros de ano, categoria e valores nominais ou deflacionados (IPCA, a preços de agosto de 2026) atualizam números, gráficos e tabelas. O ícone **i** de cada elemento explica como interpretar o dado.

## Versão

Esta pasta traz a **versão 5.1.1** (06/10/2026), a versão de referência do painel. Ela é a v5.1 com um novo rodapé e sem um parágrafo da aba Metodologia; os números são os mesmos da v5.1. O que mudou e o resultado de cada verificação estão em `relatorio_final_painel_v5_1_1.md`.

## Conteúdo da pasta

```
painel_soberania_digital_v5_1_1.html   o painel
METODOLOGIA_v5_1_1.md                   metodologia completa
relatorio_final_painel_v5_1_1.md        relatório da entrega (mudanças, verificações e hashes)
LEIAME.txt                              pré-requisitos e ordem de execução dos scripts
scripts/                                todos os scripts, da limpeza da base ao painel
tabelas_agregadas/                      tabelas que alimentam cada gráfico e tabela do painel
verificacao/                            conferência de números, diff, buscas, verificações e hashes
```

`verificacao/conferencia_numeros_v5_1.csv` confere cada número exibido no painel contra as tabelas agregadas, com 100% "sim". Ela vale para a v5.1.1, que não mudou nenhum número.

Os dados brutos e as bases intermediárias (arquivos Parquet e bancos DuckDB, vários GB) não estão nesta pasta. Podem ser obtidos de novo no Colibri, como descrito abaixo.

## Como reproduzir

**Pré-requisitos:**

- Python 3.14, com os módulos `duckdb` e `playwright` (este só para a verificação no navegador).
- DuckDB (linha de comando).
- Acesso de leitura ao lake do Colibri.

**1. Extrair os dados brutos.** No Colibri, exporte as três tabelas para `parquet/`:

```sql
COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__compras) TO 'compras.parquet' (FORMAT parquet);
COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__itens) TO 'itens.parquet' (FORMAT parquet);
COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__resultados) TO 'resultados.parquet' (FORMAT parquet);
```

**2. Rodar os scripts.** Use a ordem do `LEIAME.txt`. Os scripts esperam rodar a partir de uma pasta de trabalho `Processado/`, com os Parquet em `../parquet/`; as pastas de `scripts/` vão para dentro dela com os mesmos nomes.

- scripts `.sql`: `duckdb scripts_parte0/p0.duckdb < <script>`;
- scripts `.py`: `python <script>`.

**3. Conferir.** Os scripts de verificação rodam no navegador (Chromium sem internet, em 1440 px e 390 px). Os de conferência comparam cada número exibido com as tabelas agregadas.

## Metodologia, em resumo

A metodologia completa está em `METODOLOGIA_v5_1_1.md` e na aba Metodologia do painel.

- **Base:** só registros vigentes e sem duplicidade. Republicações foram identificadas por cinco campos (órgão, unidade, processo, objeto e valor) e pelo mesmo conjunto de fornecedores vencedores.
- **Auditoria de valores:** valores com erro de preenchimento foram excluídos das somas, sem apagar a compra. Exemplos: sequências de 9, valores acima de R$ 1 trilhão e divergências extremas entre valor estimado e homologado. Houve regras automáticas e revisão manual.
- **Valor homologado:** soma dos itens adjudicados aos vencedores. Não equivale ao valor contratado nem ao valor pago.
- **Seis categorias:** classificação por palavras-chave no objeto da compra e na descrição dos itens. Cada categoria foi verificada por amostragem, com precisão final entre 81% e 90%. Os termos estão em `dicionario_termos.csv`.
- **Três regras de soma:** no total das seis categorias, cada compra entra uma vez. Nos gráficos por categoria, a compra entra em cada categoria em que foi classificada.
- **Aba de IA:** classes Acréscimo à licença, Solução de IA, Outros e Capacitação. Cada classe foi verificada por amostragem e por revisão manual realizada pela pesquisadora responsável.
- **Fornecedor:** CNPJ do vencedor, que pode ser revendedor, e não o fabricante.
- **Margem de preferência por NCM:**
  - o NCM vem do item; na falta dele, do tradutor CATMAT → NCM do Colibri, com classificação humana ou sugestão de IA;
  - o item é elegível se estiver coberto por resolução CICS vigente na data da compra.

## Limitações

- O Colibri não informa se a base ComprasGov cobre todas as contratações publicadas no PNCP.
- 2021 e 2022 têm cobertura parcial, porque a publicação no PNCP só se tornou obrigatória ao fim da transição da Lei 14.133/2021, em 30/12/2023. 2026 vai até 24/05.
- O valor homologado não é gasto executado. Em registro de preços, é o teto da ata.
- A classificação por palavras-chave está sujeita a falsos positivos e falsos negativos.
- O país de origem do produto está preenchido em 0,006% dos resultados. Não é possível medir diretamente a dependência de tecnologia estrangeira.
- O painel mede compras de tecnologias críticas, não o grau de soberania digital do Estado.

## Fontes de dados

- Portal Nacional de Contratações Públicas (PNCP): <https://pncp.gov.br>
- Colibri, base ComprasGov (Ministério da Gestão e da Inovação em Serviços Públicos): <https://gestaogovbr.github.io/colibri/>
- IPCA, IBGE, SIDRA, tabela 1737: <https://sidra.ibge.gov.br/tabela/1737>

## Autoria

Elaboração: Mabel Mota, para discussão interna no Ipea. Ferramentas: Python 3.14 e DuckDB.
