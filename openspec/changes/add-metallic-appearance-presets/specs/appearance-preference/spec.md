## ADDED Requirements

### Requirement: Seletor único de aparência

O website e o PWA SHALL oferecer um único seletor acessível chamado “Aparência” na entrada, administração e área do cliente. Esse seletor SHALL conter presets que combinem o modo Sistema, Claro ou Escuro com os acabamentos Neutro, Cinza metálico, Azul metálico ou Vinho metálico. O rótulo selecionado SHALL identificar modo e acabamento, e SHALL NOT existir um seletor separado de acabamento.

#### Scenario: Seleção de preset combinado

- **WHEN** o usuário seleciona “Claro · Azul metálico” e navega ou recarrega o website
- **THEN** o modo Claro e o acabamento Azul metálico são mantidos em todas as áreas do sistema e o mesmo preset aparece selecionado

#### Scenario: Alternância entre modos e acabamentos

- **WHEN** o usuário seleciona “Escuro · Vinho metálico”
- **THEN** a interface preserva as superfícies escuras e coordena textos e realces com a paleta vinho, atualizando o único seletor para o preset completo

#### Scenario: Controle compacto único

- **WHEN** o usuário abre os controles de aparência em qualquer área do sistema
- **THEN** encontra um único seletor “Aparência” com modo e acabamento combinados e nenhum seletor “Acabamento” separado

### Requirement: Preferências de modo e acabamento persistentes

O preset escolhido SHALL persistir localmente no mesmo navegador e aplicar-se às superfícies compartilhadas da administração e da área do cliente. Um modo ausente ou inválido SHALL resolver para Sistema, e acabamento ausente ou inválido SHALL resolver para Neutro. Falha de armazenamento SHALL NOT impedir o uso do seletor ou o carregamento da interface.

#### Scenario: Preferência inválida ou armazenamento indisponível

- **WHEN** o navegador retorna um acabamento desconhecido ou impede a gravação local
- **THEN** o sistema usa Neutro como fallback e mantém o seletor funcional durante o acesso

### Requirement: Texto coordenado ao acabamento

Os acabamentos metálicos SHALL usar gradientes predefinidos e discretos em superfícies aprovadas e SHALL coordenar cores de texto principal e secundário com o acabamento, modo e superfície. Os pares SHALL preservar hierarquia, foco visível e contraste mínimo vigente para textos e indicadores.

#### Scenario: Texto coordenado à paleta

- **WHEN** o usuário seleciona um acabamento metálico em modo claro ou escuro
- **THEN** textos principais e secundários adotam as cores coordenadas à paleta e mantêm contraste legível sobre suas superfícies em telas móveis e desktop

### Requirement: Integridade das mídias temáticas

O sistema SHALL NOT aplicar gradientes, filtros, inversão ou alteração de cor a fotografias, logos, favicons ou QR Codes quando o acabamento visual mudar.

#### Scenario: Fotografia ou QR Code visível

- **WHEN** o usuário muda o acabamento enquanto visualiza fotografias ou pagamento por QR Code
- **THEN** as cores e a legibilidade das mídias permanecem inalteradas
