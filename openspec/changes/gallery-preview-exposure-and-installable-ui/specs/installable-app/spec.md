## ADDED Requirements

### Requirement: Instalação contextual para ambos os papéis

O frontend SHALL oferecer manifesto e ícones válidos e a ação “Instalar aplicativo” no topo para fotógrafo e cliente em navegadores compatíveis. A ação SHALL abrir o prompt disponível ou instruções de instalação manual e SHALL ficar oculta em modo instalado.

#### Scenario: Navegador com prompt nativo
- **WHEN** o navegador sinaliza disponibilidade e o usuário clica em instalar
- **THEN** o prompt nativo é acionado uma vez, sem repetição automática após recusa

#### Scenario: Instalação manual
- **WHEN** um usuário em iPhone abre a opção de instalação
- **THEN** vê instruções curtas de adicionar à tela de início e pode fechá-las

### Requirement: Offline sem retenção privada

O PWA SHALL manter autenticação e autorização existentes e SHALL NOT armazenar respostas privadas, fotos ou tokens em cache de aplicação. Sem conexão, SHALL apresentar somente um aviso neutro para reconectar.

#### Scenario: Navegação sem rede
- **WHEN** uma navegação documental falha por falta de conexão
- **THEN** o aplicativo mostra aviso offline sem nomes, galerias, fotos ou dados financeiros
