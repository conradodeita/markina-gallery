## ADDED Requirements

### Requirement: Acabamentos metálicos controlados

O website e o PWA SHALL oferecer, junto ao seletor existente Claro/Escuro/Sistema, os acabamentos Neutro, Cinza metálico, Azul metálico e Vinho metálico. A escolha SHALL ser independente do modo de aparência, persistir localmente no mesmo navegador e aplicar-se às superfícies compartilhadas da administração e da área do cliente. Um valor ausente ou inválido SHALL resolver para Neutro. Falha de armazenamento SHALL NOT impedir o uso do seletor ou o carregamento da interface.

#### Scenario: Seleção de acabamento

- **WHEN** o usuário seleciona Azul metálico e navega ou recarrega o website
- **THEN** o acabamento é mantido em todas as áreas do sistema sem alterar sua escolha Claro/Escuro/Sistema

#### Scenario: Preferências independentes

- **WHEN** o usuário muda de Claro para Escuro mantendo Vinho metálico
- **THEN** a interface preserva as superfícies escuras e coordena textos e realces com a paleta vinho

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
