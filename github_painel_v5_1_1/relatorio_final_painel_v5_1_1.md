# Relatório final do painel, versão 5.1.1

Feita a partir de versao_congelada_v5_1/painel_soberania_digital_v5_1.html e de METODOLOGIA_v5_1.md, só com as duas alterações pedidas.

## Python

Versão usada nos scripts do painel (python --version): **Python 3.14.2**, ou seja, 3.14. O rodapé foi gravado.

## Diff resumido (v5.1 → v5.1.1)

Só duas diferenças, conferidas pelo script: desfazendo as duas substituições, o HTML novo volta byte a byte ao da v5.1 (diff completo em verificacao_html_v5_1_1/diff_v5_1_para_v5_1_1.txt).

```
linha 426, a partir do caractere 325:
  - <p class='nota-dl'>Os dois pacotes são os mesmos arquivos de <code>pacote_downloads_v5_1.zip</code> (pastas scripts e tabelas_agregadas). Extração dos dados brutos: <code>COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__compras) TO 'compras.parquet' (FORMAT parquet)</code>; o mesmo para <code>__itens</code> e <code>__resultados</code>. Os Parquet não fazem parte do pacote.</p>
  + 
linha 543, a partir do caractere 19:
  - , gerada em 04/10/2026. Base extraída em 28/09/2026. Fonte: PNCP, via Colibri (gestaogovbr). Elaboração Mabel Mota para discussão interna no Ipea. Proibida a reprodução
  + .1, gerada em 06/10/2026. Base extraída em 28/09/2026. Fonte: PNCP, via Colibri (gestaogovbr). Elaboração: Mabel Mota para discussão interna no Ipea. Ferramentas: Python 3.14
```

METODOLOGIA_v5_1_1.md: o parágrafo não existe nessa redação no Markdown; o mesmo conteúdo estava em lista, na seção "## Downloads" (os dois pacotes, a extração com COPY e "Os Parquet não fazem parte do pacote"). A seção inteira saiu, com o título, sem deixar linha vazia nem título órfão (trecho removido em verificacao_html_v5_1_1/metodologia_trecho_removido.txt). O rodapé não aparece na metodologia. O cabeçalho do Markdown não foi alterado e continua citando a versão 5.1, porque o escopo era só as duas alterações.

## Verificações

| Verificação | Resultado | Detalhe |
|---|---|---|
| 2. sem 'pacote_downloads_v5_1' | ok | 0 ocorrências |
| 2. sem 'COPY (SELECT' | exceção aceita | exceção mantida por decisão da pesquisadora: a ocorrência restante está em outro parágrafo da seção 1 da Metodologia ("Extração: as tabelas foram exportadas integralmente para Parquet com COPY (SELECT * FROM ...)..."), que não faz parte da alteração 1; removê-la acrescentaria uma terceira diferença ao diff. O mesmo parágrafo segue na METODOLOGIA_v5_1_1.md. |
| 2. sem 'Os Parquet não fazem parte' | ok | 0 ocorrências |
| 3. rodapé novo exatamente uma vez | ok | 1 ocorrência(s), no <footer> |
| 4. sem travessão (—) | exceção aceita | exceção mantida por decisão da pesquisadora: os 16 travessões estão nos objetos de compra copiados literalmente do PNCP (dados embutidos, exibidos nas tabelas de cadeias e nas dicas dos objetos), já presentes na v5.1; nenhum está em texto do painel. |
| 4. sem 'Proibida a reprodução' | ok | 0 ocorrências |
| 5. todas as abas carregam (1440 px) | ok | [True, True, True, True, True] |
| 1. parágrafo fora da tela, botões de download mantidos (1440 px) | ok | 3 botões |
| 3. rodapé exibido igual ao texto (1440 px) | ok | Versão 5.1.1, gerada em 06/10/2026. Base extraída em 28/09/2 |
| 5. gráfico 8 clicável: clique num fornecedor filtra o diagrama e a tabela (1440 px) | ok | [41357674407.939964, 51225] -> [1058884708.91, 4631] |
| 5. gráfico 9 clicável: clique num fornecedor filtra o diagrama e a tabela (1440 px) | ok | [1280681757.8300016, 25456] -> [361871241.5400001, 20930] |
| 5. gráfico 1 responde ao alternador Valor/Quantidade (1440 px) | ok | Quantidade de compras públicas homologadas, 2021 a |
| 5. cartões de KPI idênticos aos da v5.1 (1440 px: texto, borda, cantos, sombra, cor do número, tamanho e posição do i) | ok | 13 cartões; diferentes: [] |
| 5. todas as abas carregam (390 px) | ok | [True, True, True, True, True] |
| 1. parágrafo fora da tela, botões de download mantidos (390 px) | ok | 3 botões |
| 3. rodapé exibido igual ao texto (390 px) | ok | Versão 5.1.1, gerada em 06/10/2026. Base extraída em 28/09/2 |
| 5. gráfico 8 clicável: clique num fornecedor filtra o diagrama e a tabela (390 px) | ok | [41357674407.939964, 51225] -> [1058884708.91, 4631] |
| 5. gráfico 9 clicável: clique num fornecedor filtra o diagrama e a tabela (390 px) | ok | [1280681757.8300016, 25456] -> [361871241.5400001, 20930] |
| 5. gráfico 1 responde ao alternador Valor/Quantidade (390 px) | ok | Quantidade de compras públicas homologadas, 2021 a |
| 5. cartões de KPI idênticos aos da v5.1 (390 px: texto, borda, cantos, sombra, cor do número, tamanho e posição do i) | ok | 13 cartões; diferentes: [] |
| 5. console sem erros nem avisos (1440 e 390 px) | ok | [] |

Buscas com o local de cada ocorrência: verificacao_html_v5_1_1/buscas.csv. Navegador: Chromium (motor do Chrome), sem internet, em 1440 px e 390 px.

## Hashes

| Versão congelada | Registrados | Idênticos no fim |
|---|---|---|
| v3 | 105 | 105 |
| v4 | 33 | 33 |
| v5 | 35 | 35 |
| v5.1 | 28 | 28 |
| v5.2 | 31 | 31 |

Versões congeladas inalteradas: sim (a v5.1 também foi conferida antes de começar: 28 de 28). Nenhum script dessas pastas foi executado.

## Entrega

- Zip de envio: `C:\Users\mabel\OneDrive\Desktop\colibri_baixado_duckdb\Processado\painel_v5_1_1_envio.zip`, com a mesma composição do painel_v5_1_envio.zip: painel_soberania_digital_v5_1_1.html (atualizado) e pacote_downloads_v5_1.zip (sem mudança nesta versão, cópia da v5.1 congelada).
- painel_soberania_digital_v5_1_1.html: `2d47fd85b6327b3a845f569d30130927b0e31a70712a0a1d98cb4671448d7c3c`
- painel_v5_1_1_envio.zip: `5ff2f4dd1598a79c41059613aa94b85463761af6c5803c5bbe73bfa3e9b5718c`
- Versão congelada: versao_congelada_v5_1_1/, com hashes_sha256_v5_1_1.csv.
