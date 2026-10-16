# Metodologia do painel de compras públicas de tecnologias críticas para a soberania digital

Versão 5.1, gerada por `scripts_painel_v5_1/p51_02_painel.py` em 04/10/2026 a partir de METODOLOGIA_v5.md: revisão manual atribuída à pesquisadora responsável, gráfico 9 com o comportamento do gráfico 8 e reconciliação da aba de IA com a categoria Inteligência artificial; nenhuma classificação foi refeita. Os números coincidem com os do painel `painel_soberania_digital_v5_1.html` (conferência em `conferencia_numeros_v5_1.csv`).

## 1. Fonte e cobertura

Os dados partem da camada tratada (main_intermediate) do Colibri (gestaogovbr.github.io/colibri), base ComprasGov, que organiza dados oficiais do Portal Nacional de Contratações Públicas (pncp.gov.br). A extração, em 28/09/2026, reuniu 902.636 compras, 9.666.224 itens e 7.219.099 resultados publicados entre 10/08/2021 e 24/05/2026. Após manter apenas os registros vigentes e remover duplicidades, restaram 875.682 compras únicas, aproveitamento de 97% do total extraído. O Colibri não informa se a base ComprasGov abrange a totalidade das contratações publicadas no PNCP. Os resultados referem-se às compras presentes nessa base.

Valor global homologado: soma dos valores dos itens adjudicados aos fornecedores vencedores ao final da licitação ou da contratação direta, conforme registrado no PNCP. Não equivale ao valor contratado nem ao valor efetivamente pago.

Comparação com o PNCP em Números: não foi possível. O painel oficial (https://www.gov.br/pncp/pt-br/acesso-a-informacao/painel-pncp-em-numeros-2026) é um painel Qlik embutido que não carregou em navegador sem interface (Playwright com Chromium, com aceite de cookies) nas abas Visão Geral, Contratações Publicadas e Contratações Homologadas, e a página não traz números em texto nem arquivo para baixar. Não há, portanto, medida da cobertura da base ComprasGov em relação ao total publicado no PNCP.

Extração: as tabelas foram exportadas integralmente para Parquet com COPY (SELECT * FROM lake.main_intermediate.int_pncp_comprasgov__compras) TO 'compras.parquet' (FORMAT parquet), e o mesmo para __itens e __resultados. A exportação em CSV pela interface do DuckDB foi abandonada porque trunca o resultado em 50.000 linhas.

## 2. Tratamento da base de dados e auditoria de valores

- Vigência: somente registros com is_current = true. Compras deduplicadas por id_compra, mantendo a maior data_atualizacao (desempate por data_inclusao e valido_de): 878.083 compras (base_limpa.parquet).
- Itens deduplicados por id_compra_item, mantendo a maior data_atualizacao (desempate por valido_de): 7.401.299 itens vigentes, de 9.666.224 extraídos.
- Resultados deduplicados pela chave (id_compra_item, sequencial_resultado, ni_fornecedor), mantendo a maior data efetiva entre as colunas de atualização, inclusão e resultado, e excluídos os cancelados (data_cancelamento preenchida): 5.752.852 resultados.
- Chaves de junção: id_compra (compra, itens e resultados) e id_compra_item (itens e resultados). O número de controle do PNCP ficou apenas como atributo de auditoria, por ter nulos nos itens.
- Republicações: foram removidas 2.401 compras que repetem outra compra em CNPJ do órgão, unidade, número do processo, objeto normalizado (minúsculas, sem acentos, espaços colapsados), valor homologado e conjunto de fornecedores vencedores, mantida a versão com data_atualizacao mais recente. Resultado: 875.682 compras.
- Regras automáticas de valor suspeito (a flag é a união das três e não apaga a compra): (1) valor de preenchimento, formado por sequência de 9 ou acima de R$ 1 trilhão; (2) valor estimado e homologado divergentes em mais de 100 vezes, em qualquer direção; (3) inconsistência nos itens, quando o valor total difere de quantidade × valor unitário em mais de 1% ou quando a quantidade é igual ao valor unitário.
- Revisão manual: compras acima de R$ 1 bilhão não alcançadas pelas regras automáticas foram revisadas uma a uma (auditoria_revisao_manual_proposta.csv); as classificadas como erro provável (16 na base) têm o valor excluído das somas.
- Em todos os casos a compra continua na contagem de compras; apenas o valor sai das somas. O valor limpo é o homologado das compras sem exclusão.

**Valores excluídos por motivo (2021 a 2026)**

| Motivo principal da exclusão | Compras | Valor homologado bruto excluído |
|---|---|---|
| Regra 1: valor de preenchimento (sequência de 9 ou acima de R$ 1 trilhão) | 140 | R$ 5.205 bi |
| Revisão manual: erro provável (compras acima de R$ 1 bi sem regra automática) | 16 | R$ 1.440 bi |
| Regra 2: estimado e homologado divergem mais de 100 vezes (sem regra 1) | 8.498 | R$ 19,2 bi |
| Regra 3: inconsistência nos itens (sem regras 1 e 2) | 6.345 | R$ 3,9 bi |
| Total excluído | 14.999 | R$ 6.668 bi |

**Valor bruto e valor limpo por ano**

| Ano | Compras publicadas | Com homologado válido | Sem homologação | Valor excluído | Homologado bruto | Excluído | Homologado limpo |
|---|---|---|---|---|---|---|---|
| 2021 | 7.143 | 4.399 | 2.647 | 97 | R$ 530 mi | R$ 1,3 mi | R$ 529 mi |
| 2022 | 39.488 | 30.467 | 8.831 | 190 | R$ 4,4 bi | R$ 4,9 mi | R$ 4,4 bi |
| 2023 | 109.715 | 91.580 | 17.424 | 711 | R$ 101 bi | R$ 420 mi | R$ 101 bi |
| 2024 | 295.539 | 251.071 | 40.132 | 4.336 | R$ 6.113 bi | R$ 5.744 bi | R$ 369 bi |
| 2025 | 319.259 | 258.939 | 52.390 | 7.930 | R$ 1.186 bi | R$ 794 bi | R$ 392 bi |
| 2026 | 104.538 | 73.741 | 29.062 | 1.735 | R$ 216 bi | R$ 130 bi | R$ 85,6 bi |
| Total | 875.682 | 710.197 | 150.486 | 14.999 | R$ 7.620 bi | R$ 6.668 bi | R$ 952 bi |

## 3. Classificação das tecnologias críticas para a soberania digital

Soberania digital é a capacidade de o Estado controlar os dados, a infraestrutura e as tecnologias de que depende para funcionar (Madiega, 2020; Floridi, 2020). Critério de criticidade: são críticas as tecnologias de que o Estado depende para operar sistemas, guardar dados e identificar cidadãos, e cujo controle define onde os dados ficam, em que condições o serviço é prestado e se pode ser interrompido. As seis categorias seguem documentos de referência da política tecnológica europeia (Comissão Europeia, 2023; Bria, Timmers e Gernone, 2025), indicados na coluna Referência da tabela abaixo.

### Referências

- MADIEGA, T. Digital sovereignty for Europe. EPRS Ideas Paper. Bruxelas: European Parliamentary Research Service, 2020.
- FLORIDI, L. The fight for digital sovereignty: what it is, and why it matters, especially for the EU. Philosophy & Technology, v. 33, 2020.
- COMISSÃO EUROPEIA. Recomendação (UE) 2023/2113 da Comissão, de 3 de outubro de 2023, relativa a domínios tecnológicos críticos para a segurança económica da UE, visando a realização de uma nova avaliação dos riscos com os Estados-Membros. Jornal Oficial da União Europeia, 2023. Disponível em: https://eur-lex.europa.eu/eli/reco/2023/2113
- BRIA, F.; TIMMERS, P.; GERNONE, F. EuroStack: a European alternative for digital sovereignty. Gütersloh: Bertelsmann Stiftung, 2025. DOI: 10.11586/2025006.

Campos pesquisados: no nível da compra, objeto_compra e informacao_complementar; no nível do item, descricao, descricao_detalhada e descricao_resumida. O texto é convertido para minúsculas e sem acentos. Uma compra (ou item) entra na categoria quando contém algum termo de inclusão e nenhum termo de exclusão da mesma categoria no mesmo texto. As expressões exatas estão em dicionario_termos.csv, no pacote de downloads.

Total das seis categorias e soma por categoria. O painel usa só estes dois termos. Total das seis categorias (R$ 34,8 bi, nos KPIs): cada compra entra uma única vez. Soma por categoria (R$ 41,5 bi, nos gráficos e tabelas por categoria): uma compra classificada em duas categorias aparece nas duas, com o valor de cada uma; por isso a soma das categorias supera o total. Uma terceira medida aparece só nesta metodologia: a compra inteira em cada categoria identificada, inclusive quando o termo está só nos itens (R$ 55,6 bi).

Regra do total das seis categorias: cada compra é contada uma única vez. Quando o termo está no objeto de qualquer categoria, entra o homologado limpo integral da compra. Quando o termo aparece só nos itens, entra a soma do valor homologado nos resultados desses itens (cada item uma vez), limitada ao homologado limpo da compra. Por categoria, a mesma regra vale dentro de cada categoria, e uma compra pode aparecer em mais de uma.

**Dicionário de termos por categoria**

| Categoria | Camada tecnológica | Referência | Termos de inclusão | Termos de exclusão |
|---|---|---|---|---|
| Nuvem | Nuvem | Recomendação (UE) 2023/2113, domínio 2 (computação em nuvem e periférica); EuroStack, camada de infraestrutura de nuvem. | computação em nuvem; serviços de nuvem; nuvem pública, privada, híbrida ou de governo; cloud; IaaS; PaaS; SaaS; multinuvem; multicloud; broker de nuvem; Amazon Web Services; AWS; Azure; Google Cloud; GCP; Oracle Cloud; Huawei Cloud | cursos, capacitações, seminários, congressos, palestras, workshops, pós-graduação, inscrições e eventos sobre o tema; publicação de artigos sobre o tema; solda, eletrodo e vareta (AWS como norma de soldagem); Adobe Creative Cloud; antivírus Endpoint Security Cloud |
| Plataformas e licenciamento | Software de plataforma | EuroStack, camada de plataformas de software (sistemas operacionais e aplicações). | Microsoft 365; Office 365; M365; Windows Server; sistema operacional; VMware; virtualização; Red Hat; SAP; Oracle Database; SQL Server; subscrição; licença ou licenciamento de (uso de) software | licença ambiental, prêmio, maternidade ou paternidade; cursos, capacitações, seminários, congressos, palestras, workshops, pós-graduação, inscrições e eventos sobre o tema; publicação de artigos sobre o tema; equipamentos em que o software é atributo (microcomputador, notebook, tablet, celular, roteador, teclado, sonorização); sistema operacional como característica adicional de equipamento; SAP como Secretaria de Administração Penitenciária |
| Data center | Infraestrutura física | Recomendação (UE) 2023/2113, domínio 2 (computação de alto desempenho); EuroStack, camada de infraestrutura de nuvem (armazenamento e processamento). | data center; centro de dados; sala-cofre; colocation; storage; hiperconvergência; supercomputador; HPC (computação de alto desempenho); servidores de rede, rack ou blade | servidor público; servidor efetivo; cursos, capacitações, seminários, congressos, palestras, workshops, pós-graduação, inscrições e eventos sobre o tema; publicação de artigos sobre o tema; peça cuja aplicação é servidor ou storage (atributo do cadastro de material); storage NAS como característica adicional de equipamento; peça compatível com storage; edição Datacenter de software (Windows Server, Jira, suítes); licença for virtual datacenters; self storage (guarda-volumes); rótulo de catálogo de videowall ou telepresença; software Ansys; licença ou sistema de gestão com hospedagem incluída; software de virtualização, backup ou segurança para data center; DVR (gravador de vídeo); licença Windows Server edição Datacenter; sistema de gestão ou aplicação web hospedada em data center do fornecedor; links de internet, SD-WAN, telefonia, rede privada e energia elétrica; armazenamento ou servidor em nuvem (categoria nuvem); WAF e proteção de endpoints (categoria segurança); hélice de passo controlado, navio e embarcação; token, mídia criptográfica, frasco, storage tube e energy storage; objeto que começa por contratação de capacitação, treinamento, curso, inscrição ou participação |
| Segurança cibernética | Transversal | Recomendação (UE) 2023/2113, domínio 5 (tecnologias de cibersegurança); EuroStack, camada de plataformas de software. | solução, serviço, software, equipamento, auditoria, consultoria, monitoramento ou licença de segurança da informação; segurança cibernética; cibersegurança; firewall; centro de operações de segurança; EDR; XDR; SIEM; antivírus; criptografia; proteção de endpoint; teste de intrusão; pentest; solução, software, serviço, licença, fita, mídia, política ou infraestrutura de backup; backup em nuvem, como serviço, de dados ou corporativo; backup e recuperação (recovery, restore); fitas LTO; segurança da informação e cibernética | segurança patrimonial, privada ou do trabalho; vigilância patrimonial, armada ou desarmada; cursos, capacitações, seminários, congressos, palestras, workshops, pós-graduação, inscrições e eventos sobre o tema; publicação de artigos sobre o tema; criptografia WEP e Bluetooth EDR (atributos de equipamento); firewall integrado a equipamento; client server suite; pré-amplificador e mixer; certificado digital, e-CPF e e-CNPJ (categoria identidade); oxigênio, ar comprimido, hemodiálise e criogenia (backup de gases e equipamentos); notebook, microcomputador e all-in-one; criptografia WPA, WEP ou AES como atributo de equipamento de rede; celular, roteador, modem, receptor e tela Retina XDR; radiocomunicação, câmeras e leitores de cartão ou biometria; memória para firewall (atributo de peça); link de internet ou link de backup; equipamento, cilindro ou unidade de backup (não informático); hospedagem, servidor em nuvem e certificado SSL; segurança pública, CIOSP e reagentes; objeto que começa por contratação de capacitação, treinamento, curso, inscrição ou participação |
| Inteligência artificial | Inteligência artificial | Recomendação (UE) 2023/2113, domínio 2 (tecnologias de inteligência artificial); EuroStack, camada de dados e inteligência artificial. | inteligência artificial; aprendizado de máquina; machine learning; deep learning; IA generativa; LLM; modelos de linguagem; chatbot; assistente virtual; visão computacional; reconhecimento facial; processamento de linguagem natural; solução, plataforma, ferramenta, sistema ou modelo de IA | cursos, capacitações, seminários, congressos, palestras, workshops, pós-graduação, inscrições e eventos sobre o tema; publicação de artigos sobre o tema; inteligência artificial no nome de secretaria; cursos, eventos, turmas, oficinas e projetos de pesquisa ou extensão; fundação de apoio, gestão administrativa e financeira e termo de fomento; celular, notebook e televisor com recurso de IA; Creative Cloud, banco de imagens, Matlab e livros; objeto que começa por contratação de capacitação, treinamento, curso, inscrição ou participação; eventos, ações educacionais e palestras; contratação de capacitação, curso ou treinamento; elaboração de DFD, ETP e planilhas orçamentárias; fundação para apoiar projeto e gestão administrativo-financeira; banco de preços e CapCut |
| Identidade e infraestrutura pública digital | Aplicações de governo | Recomendação (UE) 2023/2113, domínio 5 (tecnologias de identidade digital); EuroStack, componente de identidade digital. | identidade digital; biometria; assinatura eletrônica ou digital; certificado digital; identificação civil | nenhum |

Verificação por amostragem: em cada categoria, uma amostra de 150 compras, sorteada por hash determinístico, foi revisada uma a uma. A compra é pertinente quando a tecnologia da categoria faz parte do que é contratado; não é pertinente quando o termo aparece como tema de curso, evento ou publicação, como nome de órgão, como atributo acessório de equipamento ou em menção incidental. As categorias abaixo de 80% tiveram o dicionário ajustado e foram medidas em nova amostra independente, sem repetir compras, até todas superarem 80%. A precisão final é a da última amostra, excluídas as compras que saíram da base como republicação.

**Precisão por categoria**

| Categoria | Amostra final | Compras revisadas | Pertinentes | Precisão | Dicionário ajustado |
|---|---|---|---|---|---|
| Nuvem | amostra2 | 149 | 134 | 90% | sim |
| Plataformas e licenciamento | amostra2 | 150 | 127 | 85% | sim |
| Data center | amostra3 | 150 | 122 | 81% | sim |
| Segurança cibernética | amostra3 | 150 | 135 | 90% | sim |
| Inteligência artificial | amostra4 | 149 | 121 | 81% | sim |
| Identidade e infraestrutura pública digital | amostra1 | 150 | 131 | 87% | não |

Remoção indevida pelo ajuste do dicionário: entre as compras que o dicionário original classificava e o dicionário final deixou de classificar, 100 por categoria foram sorteadas (hash com o rótulo remocao1) e julgadas com o mesmo critério. A regra previa novo ajuste se alguma categoria passasse de 20%; nenhuma passou.

**Remoção indevida por categoria**

| Categoria | Pares compra × categoria removidos | Julgadas | Remoções indevidas | Taxa |
|---|---|---|---|---|
| Nuvem | 2.147 | 100 | 3 | 3% |
| Plataformas e licenciamento | 7.486 | 100 | 3 | 3% |
| Data center | 1.567 | 100 | 12 | 12% |
| Segurança cibernética | 1.938 | 100 | 9 | 9% |
| Inteligência artificial | 1.658 | 100 | 1 | 1% |

### Dicionário de termos por categoria

Conceito, palavras-chave e verificação de cada uma das seis categorias; o ícone i do gráfico 5 remete a esta seção. As palavras-chave estão em linguagem comum; as expressões exatas estão em dicionario_termos.csv, no pacote de downloads.

Nuvem. Conceito: Capacidade de processamento e armazenamento contratada como serviço. Palavras-chave: computação em nuvem; serviços de nuvem; nuvem pública, privada, híbrida ou de governo; cloud; IaaS; PaaS; SaaS; multinuvem; multicloud; broker de nuvem; Amazon Web Services; AWS; Azure; Google Cloud; GCP; Oracle Cloud; Huawei Cloud. Verificação: Verificada por amostragem de 149 compras, com precisão de 90%.

Plataformas e licenciamento. Conceito: Software básico de que os sistemas do governo dependem. Palavras-chave: Microsoft 365; Office 365; M365; Windows Server; sistema operacional; VMware; virtualização; Red Hat; SAP; Oracle Database; SQL Server; subscrição; licença ou licenciamento de (uso de) software. Verificação: Verificada por amostragem de 150 compras, com precisão de 85%.

Data center. Conceito: Infraestrutura física de processamento e armazenamento. Palavras-chave: data center; centro de dados; sala-cofre; colocation; storage; hiperconvergência; supercomputador; HPC (computação de alto desempenho); servidores de rede, rack ou blade. Verificação: Verificada por amostragem de 150 compras, com precisão de 81%.

Segurança cibernética. Conceito: Proteção de redes, dados e sistemas. Palavras-chave: solução, serviço, software, equipamento, auditoria, consultoria, monitoramento ou licença de segurança da informação; segurança cibernética; cibersegurança; firewall; centro de operações de segurança; EDR; XDR; SIEM; antivírus; criptografia; proteção de endpoint; teste de intrusão; pentest; solução, software, serviço, licença, fita, mídia, política ou infraestrutura de backup; backup em nuvem, como serviço, de dados ou corporativo; backup e recuperação (recovery, restore); fitas LTO; segurança da informação e cibernética. Verificação: Verificada por amostragem de 150 compras, com precisão de 90%.

Inteligência artificial. Conceito: Sistemas que automatizam análise, decisão ou atendimento. Palavras-chave: inteligência artificial; aprendizado de máquina; machine learning; deep learning; IA generativa; LLM; modelos de linguagem; chatbot; assistente virtual; visão computacional; reconhecimento facial; processamento de linguagem natural; solução, plataforma, ferramenta, sistema ou modelo de IA. Verificação: Verificada por amostragem de 149 compras, com precisão de 81%.

Identidade e infraestrutura pública digital. Conceito: Meios de identificar cidadãos e validar documentos. Palavras-chave: identidade digital; biometria; assinatura eletrônica ou digital; certificado digital; identificação civil. Verificação: Verificada por amostragem de 150 compras, com precisão de 87%.

## 4. Teste de robustez

**TABELA 4. Valor global homologado e posição de cada categoria em duas versões da classificação (2021 a 2026) (Em R$ milhões)**

| Categoria | (a) Só termo no objeto | Posição (a) | (b) Objeto e itens | Posição (b) |
|---|---|---|---|---|
| Nuvem | R$ 10.576 mi | 1 | R$ 18.622 mi | 1 |
| Plataformas e licenciamento | R$ 10.513 mi | 2 | R$ 11.830 mi | 2 |
| Data center | R$ 3.774 mi | 3 | R$ 4.483 mi | 3 |
| Segurança cibernética | R$ 3.469 mi | 4 | R$ 4.435 mi | 4 |
| Inteligência artificial | R$ 810 mi | 5 | R$ 1.114 mi | 5 |
| Identidade e infraestrutura pública digital | R$ 780 mi | 6 | R$ 968 mi | 6 |

A ordem entre as categorias se mantém nas duas versões. A versão (b), objeto e itens, é o critério adotado no painel.

## 5. Indicadores de concentração

sᵢ = valor homologado do fornecedor i ÷ valor homologado total da categoria no ano; CR4 = (s₁ + s₂ + s₃ + s₄) × 100, com os quatro maiores sᵢ; HHI = Σ sᵢ², de 0 a 1. Base: resultados vigentes e não cancelados das compras da categoria (compra com termo no objeto: todos os resultados; termo só nos itens: resultados desses itens), com valor positivo, em compras sem valor excluído. O fornecedor é o CNPJ do vencedor (ni_fornecedor), que pode ser revendedor, e não o fabricante. Os resultados (pn_concentracao.csv) estão no pacote de downloads e não são exibidos em gráfico no painel.

## 6. Valores deflacionados

IPCA, número-índice mensal, IBGE, SIDRA tabela 1737 (https://sidra.ibge.gov.br/tabela/1737), arquivo ipca_1737.csv. Mês-base: agosto de 2026 (último mês disponível, índice 7.633,23). Regra: valor deflacionado = valor nominal × índice do mês-base ÷ índice do mês de publicação da compra, a mesma data usada para definir o ano. No período, o homologado limpo soma R$ 952 bi em valores nominais e R$ 1.022 bi em valores de agosto/2026; nas seis categorias, R$ 34,8 bi e R$ 37,1 bi.

## 7. Modelo de aquisição e tipo de vendedor

Os principais achados da aba de tecnologias críticas e a tabela 2 (marcas) usam duas classificações adicionais, modelo de aquisição e tipo de vendedor, feitas sobre a mesma base do painel e a mesma classificação das seis categorias; nenhum valor já publicado foi recalculado. Os resultados do modelo de aquisição, do tipo de vendedor e do porte estão no pacote de downloads (pn_modelo_categoria_ano.csv, pn_vendedor_categoria_ano.csv, pn_porte_compras.csv e pn_porte_valor.csv) e não são exibidos em gráfico no painel; as marcas estão em pn_marca_resultados.csv e os achados, em pn_achados.csv.

### Modelo de aquisição

Classificação de cada item do escopo das seis categorias pelo texto do item (descrição, descrição resumida, descrição detalhada e unidade de medida), em minúsculas e sem acentos. Classes mutuamente exclusivas, nesta precedência: 1 acréscimo a licença existente; 2 subscrição ou serviço (assinaturas, licenças por prazo, nuvem e certificados digitais); 3 licenciamento de direitos permanentes de uso (inclusive licença com software assurance); 4 suporte e manutenção de licença; 5 desenvolvimento e serviços técnicos (inclusive instalação, manutenção e garantia de equipamentos; treinamento não entra); 6 equipamentos e infraestrutura física (itens de material com função de hardware); 7 não identificado. O item recebe a primeira classe em que alguma expressão de inclusão aparece, nenhuma de exclusão aparece (no item ou, quando indicado, no objeto da compra) e o tipo de item exigido (material ou serviço) coincide.

Licenciamento de direitos permanentes de uso: licença de software por prazo indeterminado, comprada uma vez. O nome segue o catálogo de compras do governo federal ('Licenciamento de Direitos Permanentes de Uso de Software').

Valor por classe: o valor de cada compra × categoria pela regra de soma por categoria é repartido entre os itens do escopo na proporção do valor homologado nos resultados de cada item; sem resultado, na proporção do valor estimado do item; sem nenhum dos dois, o valor fica sem classe. As somas por categoria e ano reproduzem o gráfico 5.

**Dicionário do modelo de aquisição (versão final)**

| Classe | Subregra | Tipo | Expressões (expressões regulares) |
|---|---|---|---|
| 1. Acréscimo a licença existente | a | inclusao | \badd[- ]?ons?\b; \bcopilot\b; \bgemini\b; \bmodulos? adiciona; \blicen[cs]\w* adiciona; \bexpansao d[aeo]s? (quantitativo d[aeo]s? )?licen; \bampliacao d[aeo]s? (quantitativo d[aeo]s? )?licen; \bacrescimo d[aeo]s? (quantitativo d[aeo]s? )?licen; \bcomplemento d[aeo]s? licen; \blicen[cs]\w* complementar; \btrue[- ]?up\b |
| 2. Subscrição ou serviço | a | exclusao | , nome: ; \b(com/para/de) assinatura (digital/eletronica); \bassinatura (digital/eletronica) de documentos; \bassinador; \bsob demanda\b.*\b(recarga/gas/extintor); \brecarga\b |
| 2. Subscrição ou serviço | a | inclusao | \bsubscri; \bsubscription; \bassinatura; \bsaas\b; \biaas\b; \bpaas\b; \bcomo servico\b; \bcloud broker; \bbroker de nuvem; \bbrokerage; \bsob demanda\b; \bcreditos? (de )?(nuvem/cloud/consumo); \bpor usuario; \busuarios?\s*/\s*mes; \busuarios? mes\b; \bmensalidade; \blocacao de (software/licen/sistema/programa); \bcessao temporaria de direitos; \bcomputacao em nuvem; \bservicos? (de/em) nuvem; \bnuvem publica; \bhospedagem; \b(microsoft/office/windows/w) ?365\b; \bm365\b; \bgoogle workspace; \blicen[cs]\w* (de uso )?(anual/mensal); \bemissao de (outros tipos de )?certificad; \bcertificados? digita; \bmensageria |
| 2. Subscrição ou serviço | a | material | S |
| 2. Subscrição ou serviço | b | exclusao | , nome: ; \binstalacao; \bconfiguracao; \bmigracao; \bconsultoria; \btreinamento; \bimplantacao; \bbackup em fita |
| 2. Subscrição ou serviço | b | inclusao | \bcloud\b; \bem nuvem\b; \bna nuvem\b |
| 2. Subscrição ou serviço | b | material | S |
| 3. Licenciamento de direitos permanentes de uso | a | exclusao | \bupdate (&/and) support; \brenewal; \breativacao; \brenovacao; \bcsi\b; ^\W*(suporte/atualizac/servico); \bservicos? de (suporte/atualizac); \b(suporte/atualizac\w*)( tecnico)? (e/,) ?(suporte/atualizac\w*)? ?(para/d[aeo]s?) (as )?licen\w* (perpetu/existente); \b(suporte/atualizac\w*/manutencao)\b[^/]{0,60}\bprocessor perpetual |
| 3. Licenciamento de direitos permanentes de uso | a | inclusao | \bperpetu; \bvitalici; \bdefinitiv; \buso permanente; \blicen[cs]\w* permanente; \bprazo indeterminado; \btempo indeterminado |
| 3. Licenciamento de direitos permanentes de uso | b | exclusao | \bsub\b; \bsubscri; \bper user\b; \bpor usuario; \banual; \bannual; \byears?\b; \b\d+ ?anos?\b; \bmeses\b; \bmensal; \brenovacao; \bsuporte; \bgarantia; \bsoftware assurance; \bnuvem; \bcloud; \bservico; \bimplementacao; \batualizac; \bexpansao; \badiciona; \bmonthly; \bmonth\b; , nome:  |
| 3. Licenciamento de direitos permanentes de uso | b | exclusao_objeto | \bsubscri; \bassinatura; \b365\b; \bnuvem; \bcloud; \bcontinuad; \bsuporte; \brenovacao; \batualizac; \bprestacao de servic; \bcontratacao de servic; \bservico de licenc; \bservicos de licenc; \bexpansao |
| 3. Licenciamento de direitos permanentes de uso | b | inclusao | \bdireitos permanentes |
| 3. Licenciamento de direitos permanentes de uso | c | exclusao | \brenovacao d[aeo]s? software assurance; \b^\W*renovacao; \bsomente software assurance |
| 3. Licenciamento de direitos permanentes de uso | c | inclusao | \blicen\w*[^/]{0,40}\+ ?software assurance; \bsem (o )?software assurance; \b(alng/slng) lsa\b; \blsa (2l/ucal/dcal)\b; \blicen\w* e software assurance |
| 3. Licenciamento de direitos permanentes de uso | c | material | S |
| 4. Suporte e manutenção de licença | a | exclusao | \bcorretiva; \badaptativa; \bevolutiva; \bperfectiva; \bdesenvolvimento; \bfabrica de software; \brastreamento; \blocacao; \bcomodato; \bcftv; \bcircuito fechado; \bcamera; \bcatraca; \brelogio; \bponto eletronico; \bnobreak; \bimpressao; \boutsourcing; \binstalacao; \bimplantacao; \bimplementacao; \bmigracao; \boperacao; \bmonitoramento; \bhardware; \bequipamentos?\b; \bfornecimento de (solucao/equipamento); \baquisicao de (solucao/equipamento); \bgerenciad; \bespecificacoes minimas; \bstorage; \bservidor; \bswitch; \bhiperconverg; \bappliances?\b.*\bhardware; \bcertificad; \bnovas? licen; \bcom suporte\b.*\bmeses\b.*\blicen; \b(aquisicao/fornecimento/compra) d[ae]s? (\d+ )?licen; \bperpetu; \bvitalici; \blicen\w*[^/]{0,40}\+ ?software assurance; \bsem (o )?software assurance; \b(alng/slng) lsa\b; \blsa (2l/ucal/dcal)\b; \brenovacao d[aeo]s? (licen\w*/solucao/software/subscri); \breativacao; \bvigencia; \bincluindo licenciamento; \blicenciamento e suporte |
| 4. Suporte e manutenção de licença | a | exige | \blicen[cs]; \bsoftware; \bprogramas? de computador; \bsubscri; \bversao; \bversoes; \bsistema operacional; \bbanco de dados; \bantivirus; \baplicativo; \bfirewall; \boracle; \bmicrosoft; \bfortigate; \bpalo alto; \bcheck point; \bvmware; \bred hat; \bsql; \bwindows |
| 4. Suporte e manutenção de licença | a | inclusao | \bsuporte (tecnico )?(e/,) ?(a /de )?atualizac; \batualizac\w* (e/de) (suporte/versao/versoes); \bsuporte e manutencao d[aeo]s? (licen/software); \bmanutencao d[aeo]s? licen; \bplanos? (anual /anuais )?de (suporte/manutencao); \bsoftware assurance; \brenovacao d[aeo]s? (suporte/garantia); \bextensao d[aeo]s? (suporte/garantia); \bsuporte (tecnico )?(d[oa]/ao/para o) licenciamento; \bupgrade d[ae] versao; \bvalidade tecnica; \b(garantia/suporte) premium; \bsuporte (oficial )?do fabricante; \bupgrade support; \bsuporte (tecnico )?(e/,) ?(manutencao/garantia); \bmanutencao (e/,) ?(suporte/atualizac); \bsuporte tecnico especializado; \bum ano de suporte |
| 4. Suporte e manutenção de licença | a | material | S |
| 5. Desenvolvimento e serviços técnicos | a | exclusao | , nome: ; \btreinamento; \bcapacitacao; \bcurso\b; \bvouchers?\b; \blocacao de equipamento; \barrendamento; \bassinatura; \bmensageria; \bbrokerage; \blicenciamento; \brenovacao d[aeo]s? (licen\w*/solucao/software/subscri) |
| 5. Desenvolvimento e serviços técnicos | a | inclusao | \bdesenvolviment; \bfabrica de software; \bsustentacao; \bimplantacao; \bimplementacao; \bintegracao; \bconsultoria; \bassessoria; \boperacao\b; \boperacao (de/da/do/e)\b; \binstalacao; \bconfiguracao; \bparametrizacao; \bmigracao; \bcustomizacao; \bmanutencao; \bponto de funcao; \bunidade de servico tecnico; \bservico tecnico; \bservicos tecnicos; \bservice desk; \bcentral de servicos; \bsuporte; \bassistencia tecnica; \bmonitoramento; \bservicos auxiliares de tecnologia; \bservicos para a infraestrutura; \boutsourcing; \bgerenciamento; \bhoras? (de )?(servico/tecnic); \bmao de obra; \bgarantia; \brecarga; \btestes? de (intrusao/invasao); \bpentest; \bservicos? gerenciad; \bmontagem |
| 5. Desenvolvimento e serviços técnicos | a | material | S |
| 6. Equipamentos e infraestrutura física | a | exclusao | \bmicrofone; \betiqueta; \bcartucho; \btoner; \bsuporte\s*(,///de)\s*(nobreak/videocassete/televisao/tv/monitor/parede); \bassistente virtual; \bsmart speaker; \bfita led |
| 6. Equipamentos e infraestrutura física | a | inclusao | \bservidor; \bstorage; \brack\b; \bappliance; \bswitch; \broteador; \bfirewall; \bno-?break; \bnobreak; \bups\b; \baccess point; \bponto de acesso; \bequipamento (de rede/wireless/de seguranca); \bdisco; \bssd\b; \bhd\b; \bmemoria; \bprocessador; computador; \bnotebook; \bdesktop; \bestacao de trabalho; \bmonitor\b; \btoken; \bleitor; \bcamera; \bunidade de fita; \bfita (de )?(gravacao/backup); \blto\b; \btape; \bgpu\b; \bplaca; \btransceiver; \bgbic; \bsfp\b; \bpatch panel; \bcabo; \bgerador; \bar condicionado de precisao; \bprecisao\b.*\bclimatiza; \bbateria; \bfonte de alimentacao; \bfonte alimentacao; \bmodulo eletronico; \bchip; \bimpressora; \bscanner; \btablet; \bdispositivo; \bcontrolador; \bbiometric; \bcatraca; \bsensor; \bantena; \bhub\b; \bconector; \bpdu\b; \bsala cofre; \btelefon; \bmesa digitalizadora; \bcontrole (de )?acesso; \bfechadura; \bmouse; \bteclado; \bestabilizador; \bregua eletrica; \bextensao optica; \bfibra optica; \bcoletor |
| 6. Equipamentos e infraestrutura física | a | material | M |

### Revisão manual realizada pela pesquisadora responsável (Mabel Mota)

Depois da verificação por amostragem, a pesquisadora responsável (Mabel Mota) julgou, em revisão manual, uma subamostra aleatória dos casos já verificados (semente f2_revisao_humana): 15 itens por classe aprovada do modelo de aquisição, 20 compras com menção a marca e 10 compras com vencedor classificado como empresa pública de TI, 120 casos ao todo, sem acesso aos julgamentos anteriores. Cada caso foi marcado como certo ou errado com o mesmo critério da verificação. Concordância = casos certos ÷ casos revisados; a classe é validada com pelo menos 80%.

**Resultado da revisão manual realizada pela pesquisadora responsável (Mabel Mota), por classe**

| Grupo | Classe | Casos revisados | Certo | Errado | Concordância | Validada |
|---|---|---|---|---|---|---|
| Modelo de aquisição | Acréscimo a licença existente | 15 | 15 | 0 | 100% | sim |
| Modelo de aquisição | Subscrição ou serviço | 15 | 13 | 2 | 87% | sim |
| Modelo de aquisição | Licenciamento de direitos permanentes de uso | 15 | 14 | 1 | 93% | sim |
| Modelo de aquisição | Desenvolvimento e serviços técnicos | 15 | 8 | 7 | 53% | não |
| Modelo de aquisição | Equipamentos e infraestrutura física | 15 | 6 | 9 | 40% | não |
| Modelo de aquisição | Não identificado | 15 | 9 | 6 | 60% | não |
| Marca e tipo de vendedor | Marca e tipo de vendedor | 20 | 19 | 1 | 95% | sim |
| Empresa pública de TI | Empresa pública de TI | 10 | 10 | 0 | 100% | sim |

Concordância entre a revisão manual realizada pela pesquisadora responsável (Mabel Mota) e a verificação por amostragem, nos mesmos casos: 88 de 120 (73%). O número considera a correção de um caso da revisão manual realizada pela pesquisadora responsável, Mabel Mota (licença de software para cálculo do lucro real pelo prazo de um ano, marcada como errada na classe 3, porque licença por prazo é subscrição), registrada em fase2/validacao/ajustes_revisao_humana_v3.csv.

O nome da classe 3 segue o catálogo de compras do governo federal em todas as tabelas. Nas fichas das amostras e na planilha da revisão manual realizada pela pesquisadora responsável (Mabel Mota), que já tinham julgamentos, o nome foi trocado uma única vez por fase2/scripts/f2_16_nome_classe_3.py, só na célula da classe, sem mudar julgamento, texto do PNCP ou número. Esse script não entra no pacote: numa execução nova, as fichas e a planilha já saem com o nome atual.

Classes validadas: acréscimo a licença existente, subscrição ou serviço, licenciamento de direitos permanentes de uso, marca e tipo de vendedor, empresa pública de TI. Não validadas: desenvolvimento e serviços técnicos, equipamentos e infraestrutura física, não identificado. Consequências: nos resultados do modelo de aquisição (pn_modelo_categoria_ano.csv) só aparecem separadamente acréscimo a licença existente, subscrição ou serviço e licenciamento de direitos permanentes de uso. As demais classes (desenvolvimento e serviços técnicos, equipamentos e infraestrutura física, suporte e manutenção de licença), os itens não identificados e as compras sem itens com valor formam o grupo 'Serviços técnicos, equipamentos e não identificados'. Os principais achados usam só classes validadas. Itens da amostra que estão fora da tecnologia da categoria em que a compra foi classificada estão listados, com o termo provável, em pendencias_dicionario_categorias.md; o dicionário das categorias não foi alterado.

**Precisão do modelo de aquisição por rodada de verificação**

| Classe | Rodada | Itens julgados | Pertinentes | Precisão |
|---|---|---|---|---|
| Acréscimo a licença existente | a1 | 100 | 84 | 84% |
| Subscrição ou serviço | a1 | 100 | 84 | 84% |
| Licenciamento de direitos permanentes de uso | a1 | 100 | 64 | 64% |
| Suporte e manutenção de licença | a1 | 100 | 26 | 26% |
| Desenvolvimento e serviços técnicos | a1 | 100 | 80 | 80% |
| Equipamentos e infraestrutura física | a1 | 100 | 93 | 93% |
| Não identificado | a1 | 100 | 63 | 63% |
| Subscrição ou serviço | a2 | 100 | 93 | 93% |
| Licenciamento de direitos permanentes de uso | a2 | 100 | 81 | 81% |
| Suporte e manutenção de licença | a2 | 93 | 42 | 45% |
| Desenvolvimento e serviços técnicos | a2 | 100 | 84 | 84% |
| Equipamentos e infraestrutura física | a2 | 100 | 95 | 95% |
| Não identificado | a2 | 100 | 82 | 82% |
| Licenciamento de direitos permanentes de uso | a3 | 100 | 86 | 86% |
| Não identificado | a3 | 100 | 82 | 82% |
| Suporte e manutenção de licença | a1+a2 (mesmos itens do ajuste) | 47 | 38 | 81% |

Verificação por amostragem: 100 itens por classe (ou todos), sorteados por hash com semente fixa e julgados um a um; classe abaixo de 80% teve o dicionário ajustado e foi medida em nova amostra independente; classe que não atingisse 80% após dois ajustes ficaria fora do painel. Situação final: Acréscimo a licença existente: 84%; Subscrição ou serviço: 93%; Licenciamento de direitos permanentes de uso: 86%; Suporte e manutenção de licença: fora do painel; Desenvolvimento e serviços técnicos: 84%; Equipamentos e infraestrutura física: 95%; Não identificado: 82%. A classe 'Suporte e manutenção de licença' ficou fora: Abaixo de 80% na amostra 1 (26%) e na amostra 2 (45%); após o segundo ajuste a classe ficou com 47 itens, todos já julgados nas amostras usadas para o ajuste, sem amostra independente possível. Nos resultados, seu valor entra em 'Serviços técnicos, equipamentos e não identificados'.

### Tipo de vendedor e marcas

Base: valor homologado nos resultados das seis categorias (a mesma do gráfico 8). Marca citada: termos de 15 marcas no texto do item; quando o item não cita marca, valem as marcas citadas no objeto da compra. Tipo do vencedor, nesta precedência: fabricante direto (subsidiária brasileira da marca citada, identificada pelo nome empresarial nos resultados da base); empresa pública de TI (natureza jurídica de empresa pública ou sociedade de economia mista e atividade de tecnologia da informação); outra empresa estatal; revendedor ou integrador (marca citada e vencedor que não é o fabricante); demais fornecedores privados. No tipo de vendedor (pn_vendedor_categoria_ano.csv), o valor é somado por categoria; na tabela de marcas (tabela 2), cada resultado conta uma vez por marca, e o vendedor é a raiz do CNPJ.

**Dicionário de marcas**

| Marca | Termos (expressões regulares) | Exclusões |
|---|---|---|
| Microsoft | \bmicrosoft\b; \bazure\b; \b(office/microsoft/m) ?365\b; \bwindows server\b; \bsql server\b; \bsharepoint\b; \bpower ?bi\b; \bcopilot\b; \bdynamics 365\b; \bexchange (server/online)\b; \bvisual studio\b; \bpower (apps/automate/platform/pages)\b; \bwindows (10/11) (pro/professional/enterprise)\b; \bmicrosoft teams\b | nenhuma |
| Google | \bgoogle\b; \bgcp\b; \bgemini\b; \bbigquery\b; \bg ?suite\b; \bapigee\b | nenhuma |
| Amazon/AWS | \baws\b; \bamazon\b | \bamazon(as/ia/ica/ico/ense)\b |
| Oracle | \boracle\b; \bexadata\b; \bweblogic\b; \bmysql enterprise\b | nenhuma |
| SAP | \bsap (s/?4 ?hana/hana/erp/ecc/bw/business/basis/netweaver/ariba/successfactors/concur/crm/analytics/cloud/btp/gui/fiori/businessobjects/solution manager)\b; \bs/?4 ?hana\b; \b(ambiente/sistema/solucao/licencas?/modulos?/plataforma/suporte/consultoria/sustentacao) sap\b | administracao penitenciaria |
| IBM | \bibm\b; \bwebsphere\b; \bdb2\b; \bqradar\b; \bspss\b; \bcognos\b | nenhuma |
| Red Hat | \bred ?hat\b; \brhel\b; \bopenshift\b; \bansible\b; \bjboss\b | nenhuma |
| VMware/Broadcom | \bvmware\b; \bvsphere\b; \bvcenter\b; \bvsan\b; \bbroadcom\b; \bvrealize\b; \bnsx\b | nenhuma |
| Salesforce | \bsalesforce\b; \btableau\b; \bmulesoft\b; \bslack\b | nenhuma |
| Adobe | \badobe\b; \bacrobat\b; \bphotoshop\b; \bcreative cloud\b; \billustrator\b; \bindesign\b; \bpremiere pro\b | nenhuma |
| Huawei | \bhuawei\b; \boceanstor\b | nenhuma |
| Cisco | \bcisco\b; \bwebex\b; \bmeraki\b; \bfirepower\b | nenhuma |
| Fortinet | \bfortinet\b; \bforti(gate/analyzer/manager/client/web/mail/siem/switch/ap/edr/nac/sandbox/authenticator/token/care/guard)\b | nenhuma |
| Palo Alto | \bpalo ?alto\b; \bprisma (access/cloud)\b; \bcortex (xdr/xsoar/xsiam)\b; \bpan-?os\b | nenhuma |
| Check Point | \bcheck ?point\b | nenhuma |

**CNPJs de fabricante direto**

| Marca | Raiz do CNPJ | Nome empresarial na base |
|---|---|---|
| Adobe | 02999520 | ADOBE SYSTEMS BRASIL LTDA. |
| Amazon/AWS | 15436940 | AMAZON SERVICOS DE VAREJO DO BRASIL LTDA. |
| Amazon/AWS | 23412247 | AMAZON AWS SERVICOS BRASIL LTDA |
| Google | 06947284 | GOOGLE LLC |
| Google | 06990590 | GOOGLE BRASIL INTERNET LTDA. |
| Google | 25012398 | GOOGLE CLOUD BRASIL COMPUTACAO E SERVICOS DE DADOS LTDA. |
| Huawei | 10519123 | HUAWEI GESTAO E SERVICOS DE TELECOMUNICACOES DO BRASIL LTDA. |
| IBM | 33372251 | IBM BRASIL-INDUSTRIA MAQUINAS E SERVICOS LIMITADA |
| Microsoft | 04712500 | MICROSOFT DO BRASIL IMPORTACAO E COMERCIO DE SOFTWARE E VIDEO GAMES LTDA |
| Microsoft | 60316817 | MICROSOFT INFORMATICA LTDA |
| Oracle | 59456277 | ORACLE DO BRASIL SISTEMAS LTDA |

**Empresas públicas de TI e outras estatais vencedoras nas seis categorias (valor somado por categoria)**

| Raiz do CNPJ | Nome empresarial | Tipo | Compras | Valor dos resultados |
|---|---|---|---|---|
| 33683111 | SERVICO FEDERAL DE PROCESSAMENTO DE DADOS (SERPRO) | Empresa pública de TI | 653 | R$ 2,6 bi |
| 62577929 | COMPANHIA DE PROCESSAMENTO DE DADOS DO ESTADO DE SAO PAULO - PRODESP | Empresa pública de TI | 891 | R$ 2,1 bi |
| 42422253 | EMPRESA DE TECNOLOGIA E INFORMACOES DA PREVIDENCIA - DATAPREV S.A. | Empresa pública de TI | 19 | R$ 2 bi |
| 73214439 | EMPRESA MUNICIPAL DE INFORMATICA SA - IPLANRIO | Empresa pública de TI | 8 | R$ 1,2 bi |
| 76545011 | COMPANHIA DE TECNOLOGIA DA INFORMACAO E COMUNICACAO DO PARANA - CELEPAR | Empresa pública de TI | 7 | R$ 476 mi |
| 43076702 | EMPRESA DE TECNOLOGIA DA INFORMACAO E COMUNICACAO DO MUNICIPIO DE SAO PAULO - PR | Empresa pública de TI | 15 | R$ 156 mi |
| 08839135 | EMPRESA DE TECNOLOGIA DE INFORMACAO DO ESTADO DO PIAUI S/A - ETIPI | Empresa pública de TI | 11 | R$ 66,9 mi |
| 48197859 | INFORMATICA DE MUNICIPIOS ASSOCIADOS S/A | Empresa pública de TI | 12 | R$ 44,8 mi |
| 15011059 | EMPRESA MATO-GROSSENSE DE TECNOLOGIA DA INFORMACAO - MTI | Empresa pública de TI | 5 | R$ 26,4 mi |
| 11006269 | EMPREL EMPRESA MUNICIPAL DE INFORMATICA | Empresa pública de TI | 6 | R$ 23,3 mi |
| 03773788 | EMPRESA DE TECNOLOGIA DA INFORMACAO DO CEARA - ETICE | Empresa pública de TI | 11 | R$ 17,5 mi |
| 13579586 | COMPANHIA DE PROCESSAMENTO DE DADOS DO ESTADO DA BAHIA | Empresa pública de TI | 2 | R$ 3,8 mi |
| 04407920 | PRODAM PROCESSAMENTO DE DADOS AMAZONAS S A | Empresa pública de TI | 2 | R$ 3,3 mi |
| 04850095 | COMPANHIA DE TRANSFORMACAO DIGITAL DO MUNICIPIO DE BELEM - BELEM DIGITAL | Empresa pública de TI | 1 | R$ 238 mil |
| 83043745 | CENTRO DE INFORMATICA E AUTOMACAO DO ESTADO DE SC S/A | Empresa pública de TI | 1 | R$ 38,9 mil |
| 05059613 | EMPRESA DE TECNOLOGIA DA INFORMACAO E COMUNICACAO DO ESTADO DO PARA - PRODEPA | Empresa pública de TI | 4 | R$ 25 mil |
| 16636540 | COMPANHIA DE TECNOLOGIA DA INFORMACAO DO ESTADO DE MINAS GERAIS - PRODEMGE | Empresa pública de TI | 2 | R$ 2,2 mil |
| 00336701 | TELECOMUNICACOES BRASILEIRAS SA TELEBRAS | Outra empresa estatal | 8 | R$ 822 mi |
| 09366790 | EMPRESA PARAIBANA DE COMUNICACAO S.A. - EPC | Outra empresa estatal | 8 | R$ 10,3 mi |
| 34028316 | EMPRESA BRASILEIRA DE CORREIOS E TELEGRAFOS | Outra empresa estatal | 6 | R$ 1,4 mi |
| 00000000 | BANCO DO BRASIL SA | Outra empresa estatal | 9 | R$ 852 mil |
| 27816487 | EMPRESA GERENCIAL DE PROJETOS NAVAIS | Outra empresa estatal | 1 | R$ 500 mil |
| 00360305 | CAIXA ECONOMICA FEDERAL | Outra empresa estatal | 1 | R$ 11,9 mil |

Verificação por amostragem: 87 de 100 compras com menção a marca julgadas pertinentes (87%) e 50 de 50 compras com vencedor classificado como empresa pública de TI (100%).

Porte: campo de porte do resultado no PNCP, com microempresa e empresa de pequeno porte numa classe única (micro ou pequena empresa) e demais empresas. As tabelas de porte (pn_porte_compras.csv e pn_porte_valor.csv) dão a parcela das compras com vencedor identificado em que alguma empresa do porte venceu e a parcela do valor dos resultados (cada resultado uma vez); estão no pacote de downloads e não são exibidas em gráfico no painel.

### Limitações destas classificações

- Muitos itens trazem só o nome do código do catálogo; quando o texto livre contradiz o código, o item fica como não identificado.
- Marcas, tipos de vendedor e porte usam a base de resultados (valor homologado nos resultados), que não coincide com o total das seis categorias dos KPIs.
- A menção à marca na compra não prova o produto entregue: a marca pode aparecer como referência, compatibilidade ou exemplo.
- A identificação do fabricante direto depende do nome empresarial nos resultados; vencedores estrangeiros sem CNPJ não são identificados.
- A verificação por amostragem foi feita por um único revisor; a revisão manual realizada pela pesquisadora responsável (Mabel Mota) cobriu 120 casos, e só as classes com concordância de pelo menos 80% aparecem separadamente.
- Os principais achados se referem ao período completo e às seis categorias e não mudam com os filtros. Cada número traz a sua base: total das seis categorias (cada compra uma vez), soma por categoria ou valor dos resultados; a lista está em pn_achados_numeros.csv. No achado 3, o valor vendido pelas empresas públicas de TI (R$ 8,7 bi) e a participação no valor vendido nas seis categorias (21%) usam a soma por categoria do valor dos resultados: uma venda em compra classificada em duas categorias conta nas duas. No achado 4, a base é a da aba de inteligência artificial: valor do acréscimo à licença repartido pelos itens (R$ 147 mi) e as 56 compras em que ele está, o mesmo número nas duas abas.

## 8. Limitações

- Cobertura: o Colibri não informa se a base ComprasGov abrange todas as contratações publicadas no PNCP, e a comparação com o PNCP em Números não foi possível.
- Cobertura parcial antes de 2024: a publicação no PNCP só se tornou obrigatória para todas as contratações após 30/12/2023, fim da transição da Lei 14.133/2021. 2021 começa em 10/08 e 2026 termina em 24/05.
- Valor homologado não equivale a gasto executado: em registro de preços, é o teto da ata; contratos de mais de um ano entram pelo valor integral no ano da compra.
- Fornecedor identificado pelo CNPJ do vencedor, que pode ser revendedor e não o fabricante da tecnologia.
- País de origem do produto ou serviço preenchido em 0,006% dos resultados das seis categorias (2 de 33.422). Com os dados do PNCP, não é possível medir diretamente a dependência de tecnologia estrangeira.
- Classificação por palavras-chave: sujeita a falsos positivos e negativos, medidos pela verificação por amostragem.
- Recorte tecnológico: as seis categorias cobrem as camadas de nuvem, plataformas de software, dados e inteligência artificial, segurança cibernética e identidade digital. Não incluem camadas de base que os documentos de referência também tratam como críticas, como semicondutores, redes e conectividade e dispositivos (Comissão Europeia, 2023; Bria, Timmers e Gernone, 2025). As referências utilizadas para delimitar as categorias são europeias.
- O painel mede a compra de tecnologias críticas para a soberania digital, não o grau de soberania do Estado; a base não informa a origem da tecnologia nem o local de hospedagem dos dados.
- Instrumentos de política: os campos de margem de preferência e de PPB estão sempre preenchidos com verdadeiro ou falso; não é possível distinguir 'não se aplica' de 'não informado'.
- No licenciamento de direitos permanentes de uso, 79% do valor (R$ 301 mi de R$ 381 mi) foi identificado só pelo nome do código do catálogo ('Direitos Permanentes de Uso'). Há compras com esse código que descrevem licenças por prazo; o valor da classe é indicativo.
- Margem de preferência por NCM: o NCM vem do item quando informado; a faixa superior usa o tradutor CATMAT→NCM do Colibri, que combina classificação humana e sugestão por IA.
- O campo de porte da fonte registra EPP em apenas 0,6% dos resultados da base, contra 71% para ME, o que indica que a distinção entre microempresa e empresa de pequeno porte não é confiável; o painel apresenta as duas em uma classe única.

**Frequência do campo de porte do fornecedor na base inteira (todos os resultados)**

| Porte registrado no resultado | Resultados | % dos resultados |
|---|---|---|
| ME | 4.060.933 | 71% |
| Demais | 1.547.976 | 27% |
| Não Informado | 104.355 | 1,8% |
| EPP | 36.880 | 0,6% |
| Não se aplica | 2.708 | 0,047% |

## 9. Aba Inteligência artificial

### Base da aba

A aba reúne três conjuntos de compras de 2021 a 2026, na mesma base limpa do painel; cada compra entra uma vez. A: compras da categoria Inteligência artificial do painel (mesmo dicionário e mesma regra de soma por categoria). B: compras de capacitação em IA que o dicionário da categoria exclui: termo de inclusão da categoria IA e termo de capacitação no mesmo texto (objeto e informação complementar, ou texto do item); valor pela regra do painel (compra inteira quando o texto da compra casa; só os resultados dos itens que casam, quando só os itens casam). C: compras com assistente de IA acoplado a licença existente (itens da classe 'acréscimo a licença existente' da fase 2 cujo texto cita copilot, gemini ou duet ai) que não estão em A nem em B; valor desses itens, cada item uma vez. Valores deflacionados pelo fator de cada compra (IPCA, mesmo mês-base do painel).

**Reconciliação da base da aba com a categoria IA do painel (ia_reconciliacao.csv)**

| Conjunto | Compras | Valor |
|---|---|---|
| Categoria Inteligência artificial do painel (pn_categoria_ano.csv) | 945 | R$ 1.114 mi |
| A. Compras da categoria IA na base da aba | 945 | R$ 1.114 mi |
| B. Capacitação em IA, excluída pelo dicionário da categoria | 1.453 | R$ 32,6 mi |
| C. Acréscimo de IA a licença em outras categorias (fase 2) | 56 | R$ 171 mi |
| Compras com acréscimo de IA a licença já na categoria IA (contadas em A) | 12 | R$ 77,5 mi |
| Total da aba Inteligência artificial (A + B + C, cada compra uma vez) | 2.454 | R$ 1.317 mi |

### Valor por classe e contagem de compras

O valor de cada compra é repartido entre as classes pelos itens, a mesma regra do modelo de aquisição (seção 7): nas compras da categoria IA, o valor da compra na categoria é repartido entre os itens na proporção do valor nos resultados (sem resultado, do valor estimado do item); a classe Acréscimo à licença recebe só os itens com assistente acoplado e os demais itens ficam com a classe que o dicionário indica para a compra. Para contar compras, cada compra entra uma vez, na classe em que tem mais valor. Tecnologia de IA = Acréscimo à licença, Solução de IA (exclusiva ou em pacote) e Outros; Capacitação em IA = classe Capacitação, que não faz parte do total das tecnologias críticas para a soberania digital. Fornecedores, órgãos, o gráfico 9 e a tabela de cadeias logo abaixo dele usam o valor homologado nos resultados (compras com vencedor identificado), a mesma base do gráfico 8.

### Classes e dicionário

Classes, na ordem de precedência: Capacitação; Acréscimo à licença; Solução de IA (exclusiva ou em pacote), soma das classes IA exclusiva e Pacote multi-software do dicionário; Outros. O texto é convertido para minúsculas e sem acentos; as expressões são expressões regulares. Versões do dicionário: 1 (inicial), 2 e 3 (ajustes depois das amostras 1 e 2), 4 (regra das fundações de apoio, depois da verificação por valor). Arquivo: tabelas_painel_v3/dicionario_ia_classes.csv (versões anteriores em dicionario_ia_classes_v1.csv a _v3.csv).

**Dicionário das classes da aba Inteligência artificial (versão final)**

| Classe | Tipo | Expressão | Justificativa |
|---|---|---|---|
| Capacitação | inclusao | \b(capacitac\w*/treinament\w*/cursos?/inscric\w*/pos[- ]?graduac\w*/mba/especializac\w*/seminarios?/congressos?/simposios?/palestras?/workshops?/masterclass/webinars?/conferencias?/summit/eventos?/oficinas?/horas?[- ]aula/instrutor\w*/qualificac\w*/aperfeicoamento/imersao/bootcamp/mentoria/letramento)\b | Compras fora da categoria IA (excluídas pelo dicionário da categoria): termo de IA da categoria e termo de capacitação no mesmo texto (objeto e informação complementar, ou texto do item). |
| Capacitação | inclusao_inicio_objeto | ^\W*((contratacao/aquisicao/prestacao/pagamento/realizacao) (de /da /do /dos /das )?)?((empresa/servicos?/vagas?/taxas?)( especializada)?( de/ em/ para/ para ministrar)? )?(uma? /os? /as? )?(capacitac/treinament/cursos?\b/inscric/participac/pos[- ]?graduac/mba\b/especializac/eventos?\b/seminario/congresso/palestra/workshop/oficinas?\b/letramento) | Compras da categoria IA ou com acréscimo à licença: o objeto começa pela contratação de curso, treinamento, inscrição, evento ou pós-graduação. |
| Capacitação | inclusao_objeto | \b(formacao (de/dos/das/continuada/para)( \w+){0,3} (professores/profissionais/servidores/docentes/educadores/gestores)/work ?shops?/cursos?/capacitar/ecossistema de ensino/pos[- ]?graduac\w*/mba/seminarios?/congressos?/palestras?/letramento/trilhas? de aprendizagem/(acao/curso/evento/programa/atividade) de capacitac\w*/capacitac\w* (com/sobre/em) (o tema/inteligencia/ia\b))\b | Versão 2: compras da categoria IA ou com acréscimo à licença cujo objeto trata de formação, workshop, curso ou evento sobre IA. Versão 3: também ação, curso, evento ou programa de capacitação. |
| Capacitação | exclusao_fundacao | \bfundac(ao/oes) (de apoio/da universidade/de amparo/de desenvolvimento/de pesquisa/de ensino)/\bfundacao [a-z ]{0,60}(apoio/pesquisa/ensino/extensao/inovacao/desenvolvimento)/\b(funape/funtef/fadex/fundep/finatec/fapunifesp/fap unifesp/funpar/fapeu/fade/fepese/fundape/fapex/fapeg/funarbe/fundecc/fauscs/fadesp/fundatec/faurgs/fapern/funcamp/fusp/fundunesp/fau)\b | Versão 4: fundação de apoio no objeto ou na informação complementar (com o termo de gestão abaixo, a compra sai da classe e da base B). |
| Capacitação | exclusao_fundacao_gestao | \b(gestao/gerenciamento/apoio/suporte)( (a/da/de/do/na/no/ao))?( [a-z]+){0,3} (administrativ\w*/financeir\w*/operacional)/administrativ\w* e financeir\w*/administrativo-financeir/\b(administracao/gestao/gerenciamento) d[oa]s? ([a-z]+ ){0,3}(curso/projeto/turma/especializacao/mba)/apoiar a execucao/gestao de recursos financeiros/contratacao d[ao] fundacao de apoio | Versão 4: a fundação é contratada para gestão administrativa, financeira ou operacional de curso ou projeto da instituição; não é compra de capacitação nem de tecnologia de IA. |
| Capacitação | excecao_fundacao | \binscric/\bparticipac\w* (de/do/dos) (\d+/um/dois/tres/servidor)/ministrado pela | Versão 4: inscrição ou participação de servidores em curso ou evento continua como capacitação, mesmo com fundação de apoio no texto. |
| Acréscimo à licença | inclusao | \b(copilot/gemini/duet ai)\b | Item da classe 'acréscimo a licença existente' da fase 2 cujo texto cita assistente de IA acoplado à licença (Copilot, Gemini for Workspace, Duet AI). |
| Acréscimo à licença | inclusao_acoplado | copilot(?! studio)/gemini (para/for) (o )?(google )?workspace/gemini (enterprise/business/education)/duet ai | Versão 2: o item cita o assistente acoplado à licença (Copilot para Microsoft 365, Gemini para Workspace); Copilot Studio sozinho não conta. |
| Acréscimo à licença | exclusao_objeto | chat ?gpt/\bopen ?ai\b/anthropic/\bclaude\b | Versão 2: objeto com assinatura de ChatGPT, OpenAI ou Claude é IA exclusiva, não acréscimo à licença. |
| IA exclusiva | inclusao | chat ?gpt/\bopen ?ai\b/anthropic/\bclaude (ai/pro/team/enterprise/max/sonnet/opus/haiku/code)\b/\bgemini\b/\bcopilot\b/\bllama\b/deep ?seek/\bmistral\b/\bperplexity\b/\bmanus\b/\bgpt[- ]?[0-9] | Objeto da compra com termo de IA da categoria ou com marca de IA (ChatGPT, OpenAI, Claude, Gemini, Copilot, Llama, DeepSeek, Mistral, Perplexity, Manus). |
| IA exclusiva | exclusao | \b(servidor(es)?/gpus?/placas? de video/equipamentos?/cameras?/cftv/videomonitoramento/computador(es)?/estac(ao/oes) de trabalho/storage/rack/notebooks?/drones?/totens?/catracas?/smartphones?/celular(es)?/hardware/appliance/leitor(es)?/sensor(es)?)\b/\b(controle de acesso/controlador(es/as)?/terminal/terminais/fechaduras?/salas? de reuniao/all-in-one/equipamentos? de videoconferencia/seguranca eletronica/registrador(es)?/relogios? de ponto/smart speakers?)\b/\b(dispositivos?/relogio\w*( eletronico)? de ponto/ponto eletronico/video-?monitoramento/placas?)\b | Objeto com equipamento ou hardware (inclusive controle de acesso, terminal, videoconferência, registrador de ponto): a IA vem embarcada em equipamento. Versão 3: também dispositivos, relógio ou ponto eletrônico, videomonitoramento e equipamento de sala de reunião. |
| IA exclusiva | exclusao_multi | (termos da classe Pacote multi-software) | Objeto com nuvem, suíte, atendimento omnichannel, segurança ou sistema de gestão: a IA é um componente entre vários. |
| IA exclusiva | exclusao_composta | \b(servicos tecnicos especializados/apoio a/consultoria/dados juridicos/desenvolvimento de (software/sistemas?)/fabrica de software/sustentacao/projetos de sistemas/demandas sucessivas)\b | Versão 2: serviço mais amplo que a solução de IA (serviços técnicos, consultoria, desenvolvimento de sistema). Versão 3: também sustentação e projetos de sistemas. |
| Pacote multi-software | inclusao | \bnuvem\b/\bcloud\b/\b(microsoft/office) ?365\b/\bm365\b/\bo365\b/google workspace/\bworkspace\b/pacote office/\bsuites?\b/\berp\b/omni ?channel/omnicanal/multicanal/contact ?center/call ?center/central de (atendimento/relacionamento)/seguranca (da informacao/cibernetica)/ciberseguranca/firewall/antivirus/\bendpoint/\bsiem\b/\bsoc\b/\bwaf\b/sistema (integrado )?de gestao/plataforma de (gestao/comunicacao/atendimento)/licenciamento microsoft/\bdynamics\b/\bsalesforce\b/\bservicenow\b/\baplicativos?\b/ciencia de dados/geoprocessamento/solucoes digitais/business intelligence/gerenciamento de atendimentos?/whatsapp business/integracao com (os )?sistemas | Termo de nuvem, suíte de produtividade, atendimento omnichannel, segurança ou sistema de gestão no objeto ou no item com IA. Versão 2: também aplicativo, ciência de dados, geoprocessamento e soluções digitais (vários componentes). Versão 3: também gerenciamento de atendimento e plataforma WhatsApp Business com integrações. |
| Pacote multi-software | exclusao | (termos de exclusão da IA exclusiva: equipamento ou hardware) | Versão 2: equipamento com software vai para Outros. |
| Outros | restante |  | Compras da base que não se enquadram nas classes anteriores (por exemplo, IA embarcada em equipamento ou mencionada só em itens de contratação mais ampla). |

### Verificação das classes

A classificação da aba de Inteligência artificial foi verificada por amostragem, com 20 compras por classe em cada rodada, sorteadas por hash com semente fixa e sem repetir compras entre rodadas; a classe é validada com pelo menos 80% de compras pertinentes. O dicionário teve dois ajustes (versões 2 e 3). As classes IA exclusiva e Pacote multi-software não chegaram a 80% em nenhuma rodada depois dos ajustes (65% e 75% na amostra 3). A maior parte dos erros estava na fronteira entre as duas, que é ambígua: um chatbot de atendimento por WhatsApp, por exemplo, pode ser a própria solução de IA ou um componente de uma plataforma de atendimento. Por isso as duas classes foram somadas em 'Solução de IA (exclusiva ou em pacote)', sem nova mudança no dicionário, e a classe somada foi medida numa amostra nova (amostra 4): 17 de 20 compras pertinentes (85%). Classes finais: Capacitação, Acréscimo à licença, Solução de IA (exclusiva ou em pacote) e Outros.

**Verificação das classes da aba Inteligência artificial, por amostra**

| Classe | Amostra | Dicionário | Compras julgadas | Pertinentes | Precisão | Rodada final |
|---|---|---|---|---|---|---|
| Capacitação | amostra 1 | versão 1 | 20 | 19 | 95% | não |
| Acréscimo à licença | amostra 1 | versão 1 | 20 | 17 | 85% | não |
| IA exclusiva | amostra 1 | versão 1 | 20 | 7 | 35% | não |
| Pacote multi-software | amostra 1 | versão 1 | 20 | 17 | 85% | não |
| Outros | amostra 1 | versão 1 | 20 | 20 | 100% | não |
| Capacitação | amostra 2 | versão 2 | 20 | 19 | 95% | não |
| Acréscimo à licença | amostra 2 | versão 2 | 20 | 19 | 95% | sim |
| IA exclusiva | amostra 2 | versão 2 | 20 | 12 | 60% | não |
| Pacote multi-software | amostra 2 | versão 2 | 20 | 17 | 85% | não |
| Outros | amostra 2 | versão 2 | 20 | 18 | 90% | não |
| Capacitação | amostra 3 | versão 3 | 20 | 19 | 95% | sim |
| IA exclusiva | amostra 3 | versão 3 | 20 | 13 | 65% | não |
| Pacote multi-software | amostra 3 | versão 3 | 20 | 15 | 75% | não |
| Outros | amostra 3 | versão 3 | 20 | 19 | 95% | sim |
| Solução de IA (exclusiva ou em pacote) | amostra 4 | versão 3, classes somadas | 20 | 17 | 85% | sim |

Revisão manual realizada pela pesquisadora responsável (Mabel Mota): 50 compras já verificadas, sorteadas por hash (semente ia_revisao_humana): 10 de Capacitação, 10 de Acréscimo à licença, 20 de Solução de IA (exclusiva ou em pacote) e 10 de Outros, julgadas sem acesso aos julgamentos anteriores, com o mesmo critério. Concordância com a verificação por amostragem: 45 de 50 (90%). Todas as classes passaram de 80% nas duas verificações; o dicionário não mudou depois da revisão manual realizada pela pesquisadora responsável (Mabel Mota). As divergências, com o motivo de cada uma, estão em validacao_ia/divergencias_revisao_humana_ia.csv.

**Revisão manual realizada pela pesquisadora responsável (Mabel Mota): classificação da aba Inteligência artificial**

| Classe | Casos revisados | Certo | Errado | Concordância | Validada | Concordância entre revisões |
|---|---|---|---|---|---|---|
| Capacitação | 10 | 9 | 1 | 90% | sim | 8 de 10 |
| Acréscimo à licença | 10 | 10 | 0 | 100% | sim | 10 de 10 |
| Solução de IA (exclusiva ou em pacote) | 20 | 19 | 1 | 95% | sim | 18 de 20 |
| Outros | 10 | 9 | 1 | 90% | sim | 9 de 10 |

Verificação por valor da classe Capacitação: as 10 compras de maior valor da classe foram revisadas à mão (validacao_ia/capacitacao_maiores_valores_revisadas.csv). 5 de 10 estavam certas; R$ 26,1 mi dos R$ 36,1 mi dessas compras (72%) estavam em compras erradas, todas contratos de gestão administrativa e financeira com fundações de apoio. Daí as duas regras abaixo.

Regra das fundações de apoio (versão 4 do dicionário das classes): sai da classe Capacitação e da base da aba a compra cujo objeto contrata fundação de apoio para gestão administrativa, financeira ou operacional de curso ou projeto da instituição, porque não é compra de capacitação nem de tecnologia de IA. A regra vale para toda a base: 30 compras, R$ 41 mi, listadas em validacao_ia/exclusao_fundacoes_apoio.csv. Inscrição ou participação de servidores em curso ou evento continua como capacitação, mesmo com fundação de apoio no texto.

Revisão manual da lista, realizada pela pesquisadora responsável (Mabel Mota), que revisou à mão as 30 compras excluídas pela regra das fundações de apoio, à procura de curso para os servidores do órgão. Nenhuma é curso; a exclusão foi confirmada nas 30 compras (coluna "revisão humana" de validacao_ia/exclusao_fundacoes_apoio.csv).

Regra dos itens na capacitação: quando a compra classificada pelo objeto tem itens identificáveis (algum item com termo de IA e algum sem), conta só a parte dos itens com termo de IA, repartida pelo valor dos resultados de cada item (sem resultado, pelo valor estimado), a mesma regra do modelo de aquisição. 18 compras mudaram de valor; o efeito é de R$ -4,3 mi (validacao_ia/capacitacao_itens_repartidos.csv).

### Tipos de objeto (O que vendeu)

Cada compra recebe um tipo de objeto pelo texto do objeto, da informação complementar e dos itens com IA, na ordem da tabela; compras de capacitação ficam em 'Outros objetos', que no painel aparece com o nome 'Capacitação' (o tipo só reúne compras dessa classe). Tipo com menos de 3 compras vai para 'Outras soluções de IA', salvo as marcas de IA (Microsoft Copilot, Google Gemini, ChatGPT/OpenAI, Claude/Anthropic, Perplexity e Manus), que aparecem sempre com nome próprio.

**Dicionário dos tipos de objeto (dicionario_ia_tipos.csv)**

| Ordem | Tipo de objeto | Expressão | Justificativa |
|---|---|---|---|
| 1 | Microsoft Copilot | \bcopilot\b | Assistente de IA da Microsoft citado no objeto ou no item com IA. |
| 2 | Google Gemini | \bgemini\b | Assistente de IA do Google citado no objeto ou no item com IA. |
| 3 | ChatGPT/OpenAI | chat ?gpt/\bopen ?ai\b/\bgpt[- ]?[0-9] | Produto ou modelo da OpenAI. |
| 4 | Claude/Anthropic | \banthropic\b/\bclaude ?(ai/pro/team/enterprise/max/sonnet/opus/haiku/code)\b | Produto ou modelo da Anthropic (Claude só seguido do nome do produto, para não pegar nomes de pessoas). |
| 5 | Perplexity | \bperplexity\b | Assistente de IA Perplexity. |
| 6 | Manus | \bmanus ?(ai/im)\b/\b(software/licencas?/plataforma/assinaturas?) (do /da )?manus\b | Agente de IA Manus (o termo sozinho pega sobrenomes e nomes de campus). |
| 7 | Microsoft 365 + IA | \b(microsoft/office) ?365\b/\bm365\b/\bo365\b | Suíte Microsoft 365 com componente de IA, sem Copilot citado. |
| 8 | IA jurídica/licitações | juridic/processua/peticao/peticoes/jurisprud/procuradori/advocaci/licitac/pregao/editais/contratacoes publicas/compras publicas | Solução de IA para atividade jurídica, processual ou de licitações. |
| 9 | Infraestrutura/equipamentos | \b(servidor(es)?/gpus?/placas? de video/equipamentos?/cameras?/cftv/videomonitoramento/computador(es)?/estac(ao/oes) de trabalho/storage/rack/notebooks?/drones?/totens?/catracas?/smartphones?/celular(es)?/hardware/appliance/leitor(es)?/sensor(es)?)\b | Equipamento ou infraestrutura com IA (servidores, GPUs, câmeras, computadores). |
| 10 | Nuvem com serviços de IA (nas tabelas do pacote: Nuvem/cloud broker) | cloud broker/\bnuvem\b/\bcloud\b/\baws\b/\bazure\b/google cloud/oracle cloud/\boci\b | Serviço de nuvem ou intermediação de nuvem com serviços de IA. |
| 11 | Plataforma/licença de IA | \b(plataformas?/licenc\w*/assinaturas?/subscric\w*/softwares?/apis?/solucao/solucoes/ferramentas?/sistemas?)\b | Plataforma, licença, assinatura ou software de IA não enquadrado nos tipos anteriores. |
| 12 | Outras soluções de IA |  | Compra com termo de IA sem tipo anterior; recebe também os tipos com menos de 3 compras, salvo as marcas de IA (Copilot, Gemini, ChatGPT/OpenAI, Claude/Anthropic, Perplexity, Manus), que aparecem sempre com nome próprio. |
| 13 | Outros objetos (no painel: Capacitação) |  | Compra sem termo de IA no objeto nem nos itens com IA, e compras de capacitação (curso ou evento não é solução de IA). |

Nuvem com serviços de IA: contratos de nuvem cujo objeto cita serviços de inteligência artificial (por exemplo, créditos de nuvem com acesso a modelos de IA). O valor é o do contrato inteiro; o PNCP não permite separar a parte gasta com IA. No painel, o tipo de objeto antes chamado 'Nuvem/cloud broker' (nome mantido nas tabelas do pacote, como ia_base.csv e ia_resultados.csv) aparece como 'Nuvem com serviços de IA'. São 39 compras, com R$ 159 mi de valor homologado na aba (período completo, valores nominais); no gráfico 9, que usa o valor dos resultados, são 26 compras com vencedor identificado e R$ 159 mi (ia_nuvem_servicos_ia.csv).

### Correções do gráfico 9

Correções da versão 5. (1) Capacitação: o dicionário de tipos de objeto põe as compras de capacitação no tipo 'Outros objetos', e o nó central do gráfico 9 mostrava esse nome com o botão Capacitação. Como o tipo só reúne compras da classe Capacitação, no painel ele passou a se chamar 'Capacitação' (gráfico, legenda, tooltips, tabela de cadeias e CSV), sem reclassificar nenhuma compra; nenhuma compra de Capacitação aparece em Outros. A classe tem 1.471 compras e R$ 34,9 mi na tabela de classes; o gráfico 9 usa o valor dos resultados e mostra as 1.378 compras com vencedor identificado (R$ 31,3 mi); as outras 93 compras não têm resultado com vencedor publicado (ia_capacitacao_reconciliacao.csv). (2) Tabela de cadeias: o clique no nó de tipo de objeto e o clique num fluxo não tinham ação, e a tabela não acompanhava essas seleções. Agora, como no gráfico 8, os botões de classe e os cliques em fornecedor, tipo de objeto, órgão ou fluxo filtram o diagrama e a tabela de cadeias logo abaixo; o botão Limpar seleção volta ao recorte do filtro.

Versão 5.1: o gráfico 9 usa o mesmo componente e o mesmo comportamento do gráfico 8: botões em pílula no mesmo estilo e na mesma posição; o clique num nó de fornecedor, de tipo de objeto ou de órgão, num fluxo ou na legenda filtra o diagrama e a tabela logo abaixo; um novo clique no mesmo elemento, ou no botão já ativo, desfaz a seleção, nos dois gráficos; as dicas ao passar o mouse seguem o mesmo formato.

### Aba de IA e categoria Inteligência artificial

A aba de inteligência artificial não coincide com a categoria Inteligência artificial da aba de tecnologias críticas: exclui as compras de capacitação e inclui as compras de acréscimo de IA a licenças (Copilot, Gemini) classificadas em outras categorias. Por isso os totais diferem. Reconciliação, período completo, valores nominais, compras com vencedor identificado (ia_reconciliacao_grafico8_grafico9.csv): o gráfico 8, com a categoria Inteligência artificial, tem 738 compras, 537 fornecedores, 411 órgãos e R$ 1.112 mi; saem 16 compras de capacitação classificadas na categoria (10 fornecedores e 6 órgãos que só aparecem nelas; R$ 2 mi) e entram 54 compras de acréscimo de IA a licenças classificadas em outras categorias (14 fornecedores e 24 órgãos novos; R$ 171 mi). O resultado é o gráfico 9, com o botão Todas (tecnologia): 776 compras, 541 fornecedores, 429 órgãos e R$ 1.281 mi. As 722 compras comuns aos dois gráficos têm o mesmo valor (R$ 1.110 mi).

### Marcas de IA citadas

A tabela 3 busca a marca no texto do item, no objeto e na informação complementar de todas as compras do painel (não só da base da aba), sem corte mínimo de compras; termo de exclusão no mesmo texto descarta a menção. Compras de capacitação (na base da aba, classe Capacitação; fora dela, objeto de capacitação) aparecem separadas. Valor das compras de produto: valor homologado da compra quando a marca está no objeto ou na informação complementar; senão, resultados dos itens que a citam. As menções estão listadas em ia_marcas_mencoes.csv.

**Dicionário das marcas de IA (dicionario_ia_marcas.csv)**

| Marca | Tipo | Expressão | Justificativa |
|---|---|---|---|
| Microsoft Copilot | inclusao | \bcopilot\b | Assistente de IA da Microsoft (Copilot para Microsoft 365, Copilot Studio, GitHub Copilot). |
| Microsoft Copilot | exclusao | extremecloud/extreme networks | CoPilot da Extreme Networks (gerenciamento de rede), não é da Microsoft. |
| ChatGPT/OpenAI | inclusao | chat ?gpt/\bopen ?ai\b | ChatGPT ou OpenAI. |
| Google Gemini | inclusao | \bgemini\b | Gemini do Google. |
| Google Gemini | exclusao | \blaser\b/\bforros?\b/\bpvc\b/lambri/\bpinca\b/cirurgic/odontolog/\bsensor\b/bluetooth/pet ?/ ?ct/\bpet-ct\b/tomograf/philips/\bgerador/\bhplc\b/coalescente/compressor | Outros produtos chamados Gemini (laser odontológico, forro de PVC, pinça cirúrgica, sensor de ciclismo, tomógrafo PET/CT, gerador, coluna de HPLC, elemento de compressor). |
| Claude/Anthropic | inclusao | \banthropic\b/\bclaude ?(ai/pro/team/enterprise/max/sonnet/opus/haiku/code)\b | Só 'anthropic' ou 'claude' seguido do nome do produto, para não pegar nomes de pessoas. |
| Manus | inclusao | \bmanus ?(ai/im)\b/\b(software/licencas?/plataforma/assinaturas?) (do /da )?manus\b | Agente de IA Manus; o termo sozinho pega sobrenomes, 'longa manus' e nomes de campus. |
| Mistral | inclusao | \bmistral ?(ai/7b/8x7b/large/medium/small/nemo)\b/le chat mistral | Modelos da Mistral AI; o termo sozinho pega nomes próprios (Gabriela Mistral) e equipamentos. |
| Perplexity | inclusao | \bperplexity\b | Perplexity. |
| Meta Llama | inclusao | \bllama\b | Modelos Llama da Meta. |
| DeepSeek | inclusao | deep ?seek | DeepSeek. |

### Reconciliação do Copilot e do acréscimo à licença

**Achado 4 da aba de tecnologias críticas, classe Acréscimo, tipos e marca Copilot (ia_reconciliacao_copilot.csv)**

| Conjunto | Compras | Valor | Base de valor | Motivo da diferença |
|---|---|---|---|---|
| Achado 4 da aba de tecnologias críticas (fase 2) | 68 | R$ 194 mi | valor dos itens, cada item uma vez (total das seis categorias) | conjunto de referência |
| Mesmo conjunto na soma por categoria | 68 | R$ 267 mi | valor dos itens na soma por categoria (item em duas categorias conta nas duas) | um item classificado em duas categorias conta duas vezes; a aba de IA conta cada compra uma vez e usa a base do achado 4 |
| Parte de acréscimo à licença na aba IA (valor repartido pelos itens) | 56 | R$ 147 mi | nas compras da categoria IA, a parte do valor da compra na categoria que cabe aos itens de acréscimo (regra do modelo de aquisição); nas demais, o valor desses itens, cada um uma vez | saem 12 compras: 7 itens só de Copilot Studio ou de treinamento em Copilot, sem assistente acoplado à licença; 2 assinatura de ChatGPT, OpenAI ou Claude no objeto (solução de IA, não acréscimo); 2 compra de capacitação (a classe Capacitação tem precedência); 1 itens de acréscimo fora do escopo da categoria IA (sem valor na categoria pela regra do modelo de aquisição). Valor: -0.0 mi nas compras da categoria IA (parte dos itens de acréscimo no valor da compra na categoria, em vez do valor dos itens) e -36.7 mi nas demais (só os itens com assistente acoplado) |
| Classe Acréscimo à licença (compras contadas na classe de maior valor) | 50 | R$ 147 mi | o valor da classe soma a parte de acréscimo de todas as compras | 6 compras com parte de acréscimo contam em outra classe, porque o restante da compra vale mais que os itens de Copilot ou Gemini |
| Tipo 'Microsoft Copilot' em O que vendeu (aba IA) | 64 | R$ 229 mi | valor total da compra na aba (todas as classes) | 47 compras também estão na classe Acréscimo; 5 citam Copilot fora do conjunto do achado 4 (Copilot Studio, Copilot em compra de solução de IA); 7 compras do achado 4 são do tipo Google Gemini e 2 de outro tipo ou de capacitação |
| Tipo 'Google Gemini' em O que vendeu (aba IA) | 12 | R$ 38 mi | valor da compra na aba | 7 compras estão no conjunto do achado 4 |
| Marca Microsoft Copilot, compras de produto (tabela de marcas) | 86 | R$ 203 mi | valor homologado da compra quando a marca está no objeto; senão, resultados dos itens que a citam | 63 compras de produto na base da aba e 23 fora dela (compras com Copilot em itens que a fase 2 não classificou como acréscimo, como Copilot Studio, ou fora das seis categorias); a base de valor é outra |
| Marca Microsoft Copilot, compras de capacitação | 9 | R$ 0 mi | não se aplica | total da marca: 95 compras = 86 de produto + 9 de capacitação |

### Principais achados da aba

Achado 4 (concentração dos fornecedores): base de valor dos resultados da tecnologia de IA (Acréscimo à licença, Solução de IA e Outros, sem Capacitação), período completo, valores nominais. O fornecedor é o CNPJ completo do vencedor, a mesma definição da linha-resumo do gráfico 9 e dos fornecedores da aba de tecnologias críticas: 541 fornecedores, e os 10 maiores ficaram com 72% do valor. Contada pela raiz do CNPJ (8 dígitos), critério da versão anterior do achado, a base tem 539 fornecedores, porque duas empresas venceram com dois estabelecimentos (dois CNPJs com a mesma raiz); a participação dos 10 maiores é a mesma (72%). Dados em ia_achado4_fornecedores.csv e ia_achado4_raizes_com_mais_de_um_cnpj.csv; texto e números dos achados em ia_achados_v4.csv e ia_achados_numeros_v4.csv. Na versão 5, os achados 1 e 3 são qualitativos e os números dos achados 2 e 4 estão em ia_achados_v5.csv e ia_achados_numeros_v5.csv; a síntese fica no fim da aba.

### Limitações da aba

- Classificação por palavras-chave: a verificação por amostragem e a revisão manual realizada pela pesquisadora responsável (Mabel Mota) medem a precisão das classes, não a cobertura; compras de IA sem termo de IA no texto ficam de fora.
- A fronteira entre IA exclusiva e pacote multi-software é ambígua; por isso as duas classes foram somadas.
- Outros reúne sobretudo equipamentos com IA embarcada e contratações mais amplas que citam IA nos itens; parte delas não é compra de tecnologia de IA (por exemplo, manutenção de CFTV apontada na revisão manual realizada pela pesquisadora responsável, Mabel Mota).
- A menção a uma marca não comprova o produto entregue; a tabela de marcas cobre toda a base do painel.
- O valor da capacitação em IA depende da separação dos itens; quando a compra não tem itens identificáveis, entra o valor homologado inteiro.

## Trilha dos números

Do total extraído até o valor exibido em cada KPI, linha por linha.

| Passo | Arquivo de entrada | Script | Regra | Registros antes | Registros depois | Valor antes | Valor depois |
|---|---|---|---|---|---|---|---|
| 1 | parquet/compras.parquet | extração (Colibri) | todas as versões das compras | - | 902.636 | - | - |
| 2 | parquet/compras.parquet | etapa3_base_limpa.sql | vigentes (is_current) e únicas por id_compra | 902.636 | 878.083 | - | R$ 7.622 bi |
| 3 | base_limpa.parquet | p0_14_duplicidades.sql, p0_15_base_sem_duplicidades.sql | remoção de republicações (cinco campos e mesmos vencedores) | 878.083 | 875.682 | R$ 7.622 bi | R$ 7.620 bi |
| 4 | tabela bl (p0.duckdb) | p1_01_dados_painel.sql | KPI compras publicadas | 875.682 | 875.682 | - | - |
| 5 | base_limpa.parquet, auditoria_revisao_manual_proposta.csv | p0_01_totais_homologados.sql | Regra 1: valor de preenchimento (sequência de 9 ou acima de R$ 1 trilhão): valor excluído | - | 140 compras | R$ 7.620 bi | R$ 2.415 bi |
| 6 | base_limpa.parquet, auditoria_revisao_manual_proposta.csv | p0_01_totais_homologados.sql | Revisão manual: erro provável (compras acima de R$ 1 bi sem regra automática): valor excluído | - | 16 compras | R$ 2.415 bi | R$ 975 bi |
| 7 | base_limpa.parquet, auditoria_revisao_manual_proposta.csv | p0_01_totais_homologados.sql | Regra 2: estimado e homologado divergem mais de 100 vezes (sem regra 1): valor excluído | - | 8.498 compras | R$ 975 bi | R$ 956 bi |
| 8 | base_limpa.parquet, auditoria_revisao_manual_proposta.csv | p0_01_totais_homologados.sql | Regra 3: inconsistência nos itens (sem regras 1 e 2): valor excluído | - | 6.345 compras | R$ 956 bi | R$ 952 bi |
| 9 | tabela bl | p1_01_dados_painel.sql | KPI valor homologado total (limpo) | - | - | R$ 952 bi | R$ 952 bi |
| 10 | tabelas cat_compra, item_match (p0_02) | p0_07_soberania.sql | compras em ao menos uma categoria | 875.682 | 18.574 | R$ 952 bi | R$ 34,8 bi |
| 11 | compra_unica (p0_07) | p1_01_dados_painel.sql | KPI tecnologias críticas para a soberania digital (total das seis categorias) | - | - | - | R$ 34,8 bi |
| 12 | pn_soberania_tres_regras.csv | p1_02_painel.py | KPI participação = soberania ÷ homologado total | - | - | - | 3,7% |

## Três regras de soma das tecnologias críticas para a soberania digital

| Regra | Valor | Uso no painel |
|---|---|---|
| Total das seis categorias (cada compra uma vez) | R$ 34,8 bi | KPIs, participação e gráfico 6 |
| Soma por categoria | R$ 41,5 bi | gráficos e tabelas por categoria |
| Compra inteira em cada categoria identificada | R$ 55,6 bi | só nesta metodologia |

## Verificações de qualidade da base

Duplicidades. O critério inicial considerava duplicidade a coincidência de cinco campos: CNPJ do órgão, unidade, número do processo, objeto normalizado e valor homologado. Aplicado literalmente, ele removeria 16.522 compras (R$ 3,7 bi de homologado bruto). A regra adotada pela equipe de pesquisa exige também o mesmo conjunto de fornecedores vencedores, porque credenciamentos geram contratações com mesmo processo, objeto e valor e fornecedores distintos (por exemplo, o credenciamento de pipeiros da Operação Carro-Pipa, em que cada compra tem um fornecedor diferente). Com a condição adicional foram removidas 2.401 compras (R$ 1,2 bi de homologado bruto e R$ 1,1 bi de homologado limpo), das quais 45 nas seis categorias (R$ 62,3 mi de homologado limpo). Casos com os mesmos campos exceto o número do processo (2.551 grupos, 12.444 compras) foram mantidos e listados em possiveis_duplicidades_processo_diferente.csv.

Remoção indevida pelo ajuste do dicionário: ver seção 3 (taxas por categoria, todas abaixo de 20%).

Margem de preferência. O valor homologado com margem aplicada em toda a base soma R$ 512 mi (612 itens), todo em compras publicadas a partir de 01/09/2024. Desse valor, R$ 63,1 mi estão em itens com NCM coberto por resolução CICS vigente na data da compra e R$ 449 mi fora dessa cobertura. Causas identificadas nos dados: NCM coberto por resolução CIIA-PAC vigente (ncm_do_item), R$ 243 mi; item sem NCM (nem informado nem no tradutor) (sem_ncm), R$ 183 mi; NCM coberto por resolução CICS, fora da vigência (tradutor_ia), R$ 18,2 mi; NCM sem cobertura CICS nem CIIA-PAC (ncm_do_item), R$ 2,3 mi; NCM sem cobertura CICS nem CIIA-PAC (tradutor_ia), R$ 2,2 mi; NCM coberto por resolução CIIA-PAC vigente (tradutor_ia), R$ 0,2 mi; NCM coberto por resolução CICS, fora da vigência (ncm_do_item), R$ 0,1 mi; NCM coberto por resolução CICS, fora da vigência (tradutor_humano), R$ 0 mi. Como a diferença tem causa identificada, o indicador por NCM usa como número principal o valor em itens com NCM informado no item e, como limite superior, o valor com NCM do item mais o tradutor CATMAT→NCM. O indicador está no pacote de downloads (pn_margem_ncm.csv) e não é exibido no painel.

| Indicador (seis categorias, 2021 a 2026) | Valor |
|---|---|
| Valor homologado em itens de material com NCM coberto por margem de preferência (resoluções CICS vigentes na data da compra), NCM informado no item | R$ 1.265,1 mi |
| Mesmo indicador com NCM do item e, na falta, do tradutor CATMAT→NCM (limite superior) | R$ 2.214,1 mi |
| Valor dos itens de material com margem de preferência efetivamente aplicada | R$ 4,4 mi |
| Valor das compras com ao menos um resultado com margem aplicada (total das seis categorias) | R$ 12,5 mi |

Os dois últimos valores medem coisas diferentes: R$ 12,5 mi é o valor homologado das compras em que ao menos um resultado teve a margem aplicada (a compra inteira ou os itens da categoria, pela regra de soma); R$ 4,4 mi é o valor dos próprios itens com a margem aplicada.

## Critérios de apresentação

- O gráfico 4 mostra todas as modalidades presentes na base, sem agrupar; esfera e poder não informados aparecem em azul-claro, por último.
- Anos de cobertura parcial: 2021 e 2022 em tom mais claro, com a marcação 'cobertura parcial do PNCP'; 2026 em tom mais claro, com a marcação 'parcial, até 24/05'.
- Esfera: códigos fora de F, E, M e D (N e o valor 'false') aparecem como Esfera não informada; poder fora de E, L e J, como Poder não informado.
- Tabela 1 (Principais relações entre fornecedores, objetos e órgãos compradores): logo abaixo do gráfico 8, com o mesmo valor dos resultados e reativa à seleção no gráfico; mostra até 50 cadeias por categoria, em ordem de valor. Tabela 2 (compras com menção à marca): responde aos filtros de ano e de categoria e usa o valor dos resultados (ver seção 7). Concentração (CR4 e HHI) e perfil das compras não são exibidos no painel; os dados por categoria e ano estão no pacote de downloads (pn_concentracao.csv, pn_perfil.csv, pn_perfil_valores_por_compra.csv e pn_perfil_bens.csv) e no CSV de download da aba.
- Categorias em ordem de valor homologado de 2021 a 2026 pela regra de soma por categoria, em gráficos, legendas, filtros e tabelas.
- Gráfico 8 (Sankey) e tabelas 1 e 2 usam o valor dos resultados (vencedores), a única fonte que identifica o fornecedor; os demais gráficos por categoria usam a regra de soma por categoria. No Sankey, os 10 maiores fornecedores e os 10 maiores órgãos do recorte aparecem nominalmente; os demais são agrupados em Demais. O clique numa categoria equivale ao filtro de categoria; o clique num fornecedor ou órgão refaz o diagrama só com os fluxos desse nó; um novo clique no mesmo elemento (ou no botão já ativo) desfaz a seleção. Os valores dos tooltips saem da tabela fornecedor × categoria × órgão (pn_fluxo.csv). Como o diagrama usa o valor dos resultados, seus valores podem diferir dos gráficos por categoria, que usam o valor homologado das compras (nota no ícone i do gráfico 8). Aba Inteligência artificial: os botões de classe e os cliques no gráfico 9 (fornecedor, tipo de objeto, órgão ou fluxo) filtram o diagrama e a tabela de cadeias logo abaixo, como no gráfico 8.
- Indicadores de instrumentos de política (cartões numéricos no bloco 'Instrumentos de política pública associados às compras'): margem prevista e PPB são marcados na compra quando algum item do escopo da categoria tem o campo verdadeiro; margem aplicada, quando algum resultado desse escopo tem aplicacao_margem_preferencia verdadeiro. O percentual é o valor dessas compras sobre o total das seis categorias ou o valor da categoria filtrada. O preenchimento dos três campos (sempre verdadeiro ou falso) e a busca por encomenda tecnológica e CPSI estão no ícone i desses indicadores. O indicador por NCM não é exibido no painel; está no pacote de downloads (pn_margem_ncm.csv). Gráficos e tabelas são numerados em sequência, pela ordem de aparição: gráficos 1 a 9 e tabelas 1 a 3 no painel, tabela 4 nesta metodologia; a tabela de cadeias da aba de inteligência artificial fica junto do gráfico 9, sem número; os instrumentos de política são apresentados como indicadores, não como gráfico.
- Aba Tecnologias críticas para a soberania digital: os quatro KPIs respondem aos filtros de ano e de categoria. Compras e valor seguem o total das seis categorias (ou o valor da categoria, com uma categoria filtrada); fornecedores vencedores e órgãos compradores são contados uma única vez no recorte, na mesma base do gráfico 8 (resultados com valor positivo; fornecedor pelo CNPJ do vencedor; órgão pelo nome do órgão comprador). Os KPIs de fornecedores e órgãos consideram apenas as compras com vencedor identificado (resultado vencedor publicado). Acima do gráfico 8, a linha-resumo mostra as compras com vencedor identificado, os fornecedores, os órgãos e o valor dos fluxos exibidos, na base dos resultados e somado por categoria (uma compra em mais de uma categoria entra em cada uma), e acompanha o filtro e os cliques em categoria, fornecedor ou órgão (pn_fluxo.csv e pn_fluxo_compras.csv).
- Modelo de aquisição, tipo de vendedor, porte e concentração: os resultados sustentam os principais achados e estão no pacote de downloads (pn_modelo_categoria_ano.csv, pn_vendedor_categoria_ano.csv, pn_porte_compras.csv, pn_porte_valor.csv e pn_concentracao.csv); não são exibidos em gráfico no painel. A síntese dos principais achados, no fim da aba, reflete o período completo e não mudam com os filtros.
- Encomenda tecnológica e CPSI: busca por menção explícita no amparo legal (nome e descrição), na modalidade e no objeto; o resultado aparece no ícone i dos indicadores de instrumentos de política.
- Precisão informada no Dicionário de termos por categoria: amostra final de cada categoria, sem as compras removidas como republicação.
- Formatação: valores em bilhões somente a partir de R$ 1 bi (abaixo disso, em milhões); valores em escala (bi, mi, mil) com uma casa decimal abaixo de 100 e nenhuma a partir de 100, na unidade adequada ao valor; percentuais com uma casa abaixo de 10, nenhuma a partir de 10, três abaixo de 0,1 e '< 0,001%' abaixo disso; contagens inteiras; ',0' é omitido. O indicador de margem de preferência por NCM é exibido em R$ milhões com uma casa decimal. Exemplos em reais por R$ 100, com centavos.
- Arredondamento: meio para cima, sobre a representação decimal mais curta do valor calculado (a mesma regra do navegador); nenhum número é digitado.

## Scripts, em ordem de execução

- 1. etapa2_agregacao.py: Deduplicação de compras e regras automáticas de valor suspeito (etapa2_compras_auditadas.parquet).
- 2. etapa3_dedup_compras_extra.sql: Deduplicação complementar de compras (colunas extras).
- 3. etapa3_dedup_itens.sql: Deduplicação de itens (itens_dedup.parquet).
- 4. etapa3_dedup_resultados.sql: Deduplicação de resultados (resultados_dedup.parquet).
- 5. etapa3_base_limpa.sql: Base limpa de compras com regras de valor suspeito (base_limpa.parquet).
- 6. scripts_parte0/p0_01_totais_homologados.sql: Recálculo do valor limpo a partir das flags e da revisão manual, e controles.
- 7. scripts_parte0/p0_14_duplicidades.sql: Identificação de republicações.
- 8. scripts_parte0/p0_15_base_sem_duplicidades.sql: Base de análise sem republicações (tabela bl).
- 9. scripts_parte0/p0_05_dicionario_v2.py: Geração do dicionário final a partir do original.
- 10. scripts_parte0/p0_02_classificacao.sql: Classificação de compras e itens nas seis categorias.
- 11. scripts_parte0/p0_16_duplicidades_resumo.sql: Resumo das republicações por ano e nas seis categorias.
- 12. scripts_parte0/p0_03_fichas_validacao.sql: Fichas da amostra 1 de validação.
- 13. scripts_parte0/p0_04_precisao.py: Precisão da amostra 1.
- 14. scripts_parte0/p0_06_margem_colibri_listar.py: Lista das tabelas de margem no Colibri (somente leitura).
- 15. scripts_parte0/p0_06b_margem_colibri_exportar.py: Cópia das tabelas de margem e do tradutor CATMAT→NCM.
- 16. scripts_parte0/p0_07_soberania.sql: Valores de soberania (três regras), robustez e país de origem.
- 17. scripts_parte0/p0_07b_controle_dicionario_original.py: Controle com o dicionário original.
- 18. scripts_parte0/p0_08_margem_preferencia.sql: Margem de preferência por NCM.
- 19. scripts_parte0/p0_09_amostra2.sql: Amostra 2 de validação.
- 20. scripts_parte0/p0_10_amostra3.sql: Amostra 3 de validação.
- 21. scripts_parte0/p0_11_amostra4.sql: Amostra 4 de validação.
- 22. scripts_parte0/p0_12_consolidar_validacao.py: Consolidação da precisão por categoria.
- 23. scripts_parte0/p0_17_fichas_remocao.sql: Sorteio das compras removidas pelo ajuste do dicionário.
- 24. scripts_parte0/p0_18_remocao_indevida.py: Julgamentos e taxa de remoção indevida.
- 25. scripts_parte0/p0_19_margem_decomposicao.sql: Decomposição do valor com margem aplicada.
- 26. scripts_painel_v3/p1_00_dicionario_legivel.py: Palavras-chave em linguagem comum, idênticas ao dicionário.
- 27. scripts_painel_v3/p1_01_dados_painel.sql: Tabelas agregadas do painel.
- 28. fase2/scripts/f2_01_base_escopo.py: Base das classificações de modelo de aquisição e tipo de vendedor (banco do painel aberto somente para leitura).
- 29. fase2/scripts/f2_02_diagnostico_campos.py: Existência e preenchimento dos campos usados nas classificações.
- 30. fase2/scripts/f2_03_dicionario_modelo_v1.py: Dicionário do modelo de aquisição, versão 1.
- 31. fase2/scripts/f2_04_classifica_modelo.py: Classificação dos itens (argumentos: dicionário e rótulo; executado com v1, v2 e v3).
- 32. fase2/scripts/f2_05_amostra_modelo.py: Amostras de verificação do modelo de aquisição (sementes f2_modelo_a1, a2 e a3).
- 33. fase2/validacao/julgamentos_modelo_f2_modelo_a1.py: Julgamentos da amostra 1.
- 34. fase2/scripts/f2_03b_dicionario_modelo_v2.py: Dicionário do modelo de aquisição, versão 2.
- 35. fase2/validacao/julgamentos_modelo_f2_modelo_a2.py: Julgamentos da amostra 2.
- 36. fase2/scripts/f2_03c_dicionario_modelo_v3.py: Dicionário do modelo de aquisição, versão 3 (final).
- 37. fase2/validacao/julgamentos_modelo_f2_modelo_a3.py: Julgamentos da amostra 3.
- 38. fase2/scripts/f2_06_precisao_modelo.py: Precisão por classe e situação final.
- 39. fase2/scripts/f2_07_modelo_valores.py: Valor por modelo de aquisição e categoria.
- 40. fase2/scripts/f2_08_marcas_vendedores.py: Marcas citadas, fabricantes, empresas públicas de TI e tipo de vendedor.
- 41. fase2/scripts/f2_09_amostra_marcas.py: Amostra de verificação de marca e tipo de vendedor (semente f2_marca_a1).
- 42. fase2/validacao/julgamentos_marcas_f2_marca_a1.py: Julgamentos da amostra de marcas.
- 43. fase2/scripts/f2_10_porte.py: Compras e valor por porte do vencedor.
- 44. fase2/scripts/f2_11_achados.py: Principais achados e números de origem.
- 45. fase2/scripts/f2_14_revisao_humana.py: Planilha da revisão manual realizada pela pesquisadora responsável, Mabel Mota (120 casos).
- 46. fase2/scripts/f2_15_revisao_humana_resultado.py: Resultado da revisão manual realizada pela pesquisadora responsável (Mabel Mota), concordância entre revisões e pendências do dicionário das categorias.
- 47. scripts_painel_v3/p1_06_ia_base.py: Base, classes, tipos de objeto e resultados da aba de inteligência artificial (com a semente como argumento, gera as fichas de verificação: ia_a1 a ia_a4).
- 48. validacao_ia/julgamentos_ia_a1.py: Julgamentos da amostra 1 das classes de IA.
- 49. validacao_ia/julgamentos_ia_a2.py: Julgamentos da amostra 2 das classes de IA.
- 50. validacao_ia/julgamentos_ia_a3.py: Julgamentos da amostra 3 das classes de IA.
- 51. validacao_ia/julgamentos_ia_a4.py: Julgamentos da amostra 4 (classe somada Solução de IA).
- 52. scripts_painel_v3/p1_07_ia_validacao_marcas.py: Precisão das classes de IA, marcas de IA citadas, planilha da revisão manual realizada pela pesquisadora responsável, Mabel Mota (gerada uma vez; depois da revisão, fica congelada e não é regravada) e reconciliação do Copilot.
- 53. validacao_ia/capacitacao_maiores_valores.py: As 10 maiores compras da classe Capacitação, como linhas extras da planilha da revisão manual realizada pela pesquisadora responsável, Mabel Mota (lista congelada depois da revisão).
- 54. validacao_ia/resultado_revisao_humana_ia.py: Resultado da revisão manual realizada pela pesquisadora responsável (Mabel Mota) na aba de IA e divergências com a verificação por amostragem.
- 55. scripts_painel_v3/p1_08_ia_achados.py: Principais achados e nota da linha-resumo da aba de IA.
- 56. scripts_painel_v3/p1_01c_fase2_painel.py: Tabelas agregadas do bloco de modelo de aquisição e tipo de vendedor e dos principais achados.
- 57. scripts_painel_v3/p1_01d_cadeias.py: Base da tabela 1 (cadeias fornecedor, objeto e órgão comprador), com controle contra a base do gráfico 8.
- 58. scripts_painel_v3/p1_01b_fluxo_compras.py: Compras de cada fluxo do gráfico 8, para a contagem de compras distintas da linha-resumo do Sankey (banco aberto somente para leitura).
- 59. scripts_painel_v3/p1_02_painel.py: Painel HTML, metodologia e pacote de downloads.
- 60. scripts_painel_v3/p1_03_verificar_html.py: Verificação do HTML em Chromium sem internet e capturas de tela.
- 61. scripts_painel_v3/p1_04_conferencia.py: Conferência dos números do painel com as tabelas agregadas.
- 62. scripts_painel_v3/p1_05_relatorio_final.py: Relatório final da entrega, com a conferência dos hashes das versões 1 e 2.
- 63. scripts_painel_v4/p4_00_hashes.py: Conferência dos hashes registrados das versões congeladas 1, 2 e 3 (no início e no fim da versão 4).
- 64. scripts_painel_v4/p4_01_ia_achados.py: Principais achados da aba de IA com o texto da versão 4 e a conta do achado 4 (fornecedores pelo CNPJ do vencedor).
- 65. scripts_painel_v4/p4_02_painel.py: Painel HTML da versão 4 a partir do HTML da versão 3, metodologia e pacote de downloads.
- 66. scripts_painel_v4/p4_03_verificar_html.py: Verificação do HTML em Chromium sem internet, em 1440 px e 390 px, e capturas de tela.
- 67. scripts_painel_v4/p4_04_conferencia.py: Conferência dos números do painel com as tabelas agregadas.
- 68. scripts_painel_v4/p4_05_relatorio_final.py: Relatório final, congelamento da versão 4 e conferência dos hashes.
- 69. scripts_painel_v5/p5_00_hashes.py: Conferência dos hashes registrados das versões congeladas 1 a 4 (no início e no fim da versão 5).
- 70. scripts_painel_v5/p5_01_ia_achados.py: Achados da aba de IA com o texto da versão 5, números de Nuvem com serviços de IA e reconciliação da classe Capacitação.
- 71. scripts_painel_v5/p5_02_painel.py: Painel HTML da versão 5 a partir do HTML da versão 4, metodologia e pacote de downloads.
- 72. scripts_painel_v5/p5_03_verificar_html.py: Verificação do HTML em Chromium sem internet, em 1440 px e 390 px, interação do gráfico 9 e capturas de tela.
- 73. scripts_painel_v5/p5_04_conferencia.py: Conferência dos números do painel com as tabelas agregadas.
- 74. scripts_painel_v5/p5_05_relatorio_final.py: Relatório final, congelamento da versão 5 e conferência dos hashes.
- 75. scripts_painel_v5_1/p51_00_hashes.py: Conferência dos hashes registrados das versões congeladas 1 a 5 (no início e no fim da versão 5.1).
- 76. scripts_painel_v5_1/p51_01_reconciliacao_ia.py: Reconciliação entre a categoria Inteligência artificial do gráfico 8 e a tecnologia de IA do gráfico 9.
- 77. scripts_painel_v5_1/p51_02_painel.py: Painel HTML da versão 5.1 a partir do HTML da versão 5, metodologia, pacote e lista das ocorrências da revisão manual.
- 78. scripts_painel_v5_1/p51_03_verificar_html.py: Verificação do HTML em Chromium sem internet, em 1440 px e 390 px, gráfico 9 comparado com o gráfico 8 e capturas.
- 79. scripts_painel_v5_1/p51_04_conferencia.py: Conferência dos números do painel com as tabelas agregadas.
- 80. scripts_painel_v5_1/p51_05_relatorio_final.py: Relatório final, congelamento da versão 5.1 e conferência dos hashes.
