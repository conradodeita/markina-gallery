## ADDED Requirements

### Requirement: Feedback discreto dos cards

Os cards de navegação de galerias e pastas SHALL oferecer elevação de 2 px com transição de aproximadamente 180 ms ao passar o mouse em dispositivos com hover e ponteiro preciso. Cards administrativos com formulários ou ações internas SHALL preservar posição e dimensões, usando apenas destaque sutil de borda. O feedback SHALL acompanhar os tokens do tema, preservar estados semânticos e não disparar consultas ou operações de backend.

#### Scenario: Navegação por mouse
- **WHEN** o usuário passa o mouse sobre um card de navegação elegível
- **THEN** o card eleva discretamente e retorna suavemente quando o mouse sai

#### Scenario: Formulário dentro de card
- **WHEN** o usuário aponta ou focaliza um campo no card administrativo
- **THEN** o destaque da borda não desloca campos nem botões

### Requirement: Interações acessíveis e responsivas dos cards

Os links SHALL manter foco de teclado visível. Em dispositivos de toque, o feedback SHALL ser breve durante o toque, sem depender de hover. A preferência `prefers-reduced-motion: reduce` SHALL desativar o movimento e as transições introduzidos por esta mudança, preservando feedback estático e funcionalidade.

#### Scenario: Preferência por movimento reduzido
- **WHEN** o dispositivo indica movimento reduzido
- **THEN** o card não eleva nem executa a nova transição e continua acessível

#### Scenario: Navegação por teclado ou toque
- **WHEN** o usuário focaliza um link com teclado ou pressiona um card em tela de toque
- **THEN** recebe indicação visual sem depender do efeito de mouse
