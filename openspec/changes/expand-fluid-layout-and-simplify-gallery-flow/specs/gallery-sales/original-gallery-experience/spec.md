## ADDED Requirements

### Requirement: Seções ocupam a largura útil

Todas as páginas administrativas, da cliente e de autenticação SHALL usar shells fluidos e gutters adaptativos. Seções, cards, listas, tabelas, grids e galerias SHALL usar a área horizontal útil e reorganizar-se sem containers centrais estreitos como limite estrutural.

#### Scenario: Página administrativa em monitor largo

- **WHEN** o fotógrafo abre uma página administrativa em viewport desktop larga
- **THEN** o conteúdo, cards, grids e listas usam a largura útil após os gutters, sem grandes vazios laterais causados por limite global estreito

#### Scenario: Jornada da cliente em desktop

- **WHEN** a cliente abre biblioteca, galeria, seleção, checkout, pedido ou entrega em desktop
- **THEN** seções e mídias se expandem e textos longos mantêm medida de leitura própria

#### Scenario: Reorganização responsiva

- **WHEN** a viewport muda entre desktop, tablet e smartphone
- **THEN** grids e ações reorganizam colunas sem overflow horizontal, sobreposição, perda de texto ou controles inacessíveis

#### Scenario: Página de autenticação

- **WHEN** a pessoa abre um formulário de autenticação em tela larga
- **THEN** canvas e composição usam a viewport, enquanto o formulário mantém largura de leitura adequada

### Requirement: Limites preservam legibilidade e proporção

O sistema MAY limitar texto corrido, formulários sequenciais e diálogos para legibilidade, sem restringir a seção que os contém. Imagens e mídias SHALL usar a largura disponível quando apropriado, preservar a proporção e evitar distorção.

#### Scenario: Mídia em container fluido

- **WHEN** uma imagem ou mídia é apresentada em card, galeria ou visualizador
- **THEN** ela usa a largura do container, preserva sua proporção e aplica enquadramento explícito sem distorção
