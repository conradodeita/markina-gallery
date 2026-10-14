## ADDED Requirements

### Requirement: Hierarquia cromática compartilhada

O site SHALL usar tokens e componentes compartilhados na identidade preta/amarela, com cinza e bege para superfícies e tons derivados para destacar navegação, ações e seções. SHALL manter legibilidade, foco acessível e layout fluido; texto sobre amarelo SHALL ser escuro com contraste adequado. Cores semânticas fora da paleta SHALL limitar-se a estados de sucesso/erro. Mídias SHALL manter cores próprias e superfícies neutras; temas configurados das galerias SHALL ser preservados. Ícone e cores do PWA SHALL seguir a identidade preta/amarela.

#### Scenario: Administração e cliente responsivos
- **WHEN** o usuário navega no desktop ou mobile
- **THEN** distingue ações e seções por contraste e espaçamento consistentes, sem limitar a largura útil ou introduzir overflow horizontal

#### Scenario: Fundo e ações secundárias
- **WHEN** as páginas administrativas e do cliente são exibidas
- **THEN** o fundo principal SHALL ser cinza claro neutro, com bege reservado a botões secundários e amarelo nos destaques
