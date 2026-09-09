## ADDED Requirements

### Requirement: Sistema de layout fluido em toda a aplicação

O sistema SHALL usar um layout full-width, fluido e responsivo em todas as páginas administrativas, da cliente e de autenticação. Shells, seções, cards, listas, tabelas, grids, galerias e mídias SHALL ocupar a área útil horizontal da viewport com gutters adaptativos, SHALL reorganizar seu conteúdo conforme o espaço disponível e SHALL NOT herdar containers centrais estreitos como limite estrutural. Limites de largura MAY ser aplicados somente a texto corrido, formulários de leitura sequencial e diálogos quando necessários à legibilidade ou usabilidade, sem limitar a seção que os contém. Imagens e mídias SHALL preencher seus containers quando apropriado, preservar a proporção e não sofrer distorção.

#### Scenario: Página administrativa em monitor largo

- **WHEN** o fotógrafo abre qualquer página administrativa em uma viewport desktop larga
- **THEN** o conteúdo principal, cards, grids e listas usam praticamente toda a largura útil após os gutters laterais, sem grandes áreas vazias causadas por um limite global estreito

#### Scenario: Jornada da cliente em desktop

- **WHEN** a cliente abre biblioteca, galeria, seleção, checkout, pedido ou entrega em desktop
- **THEN** as seções e mídias se expandem horizontalmente e os textos longos preservam uma medida de leitura independente da largura da seção

#### Scenario: Reorganização responsiva

- **WHEN** a viewport muda entre desktop, tablet e smartphone
- **THEN** grids e grupos de ações aumentam, reduzem ou reorganizam colunas sem overflow horizontal, sobreposição, perda de texto ou controles inacessíveis

#### Scenario: Página de autenticação

- **WHEN** a pessoa abre um formulário de autenticação em tela larga
- **THEN** o canvas e a composição usam a viewport, enquanto o formulário mantém largura de leitura adequada sem impor esse limite às demais superfícies da aplicação

#### Scenario: Mídia em container fluido

- **WHEN** uma imagem ou mídia é apresentada em card, galeria ou visualizador
- **THEN** ela usa a largura disponível de seu container, preserva sua razão e aplica enquadramento explícito sem distorção

