## Purpose

Permitir que fotógrafo e cliente escolham uma aparência confortável e consistente, preservando legibilidade e cores reais das fotografias.

## ADDED Requirements

### Requirement: Aparência persistente para todos os acessos

O website e o PWA SHALL oferecer no topo um controle acessível de aparência Claro, Escuro e Sistema, disponível na entrada, administração e área do cliente. Sem escolha explícita, SHALL seguir a preferência do dispositivo. A escolha SHALL persistir no mesmo navegador, sem armazenar dados pessoais, e SHALL prevalecer sobre a preferência do dispositivo até nova escolha.

#### Scenario: Escolha explícita
- **WHEN** o usuário escolhe Escuro e navega ou recarrega a página
- **THEN** a interface mantém o modo escuro sem apresentar flash perceptível do tema claro

#### Scenario: Preferência do sistema
- **WHEN** a opção Sistema está selecionada e o dispositivo muda de aparência
- **THEN** a interface acompanha a alteração sem exigir novo login

#### Scenario: Armazenamento indisponível
- **WHEN** o navegador impede persistir a preferência
- **THEN** o controle continua funcional durante o acesso e a página não falha

### Requirement: Tema consistente sem alterar mídias

O modo escuro SHALL abranger fundos, navegação, cards, tabelas, formulários, diálogos, estados, carrinho e visualizadores, mantendo a identidade preta/amarela, texto legível e foco visível. O modo claro SHALL preservar o fundo cinza claro e os botões secundários bege aprovados. Fotografias, logos, favicons e QR Code SHALL NOT sofrer inversão, escurecimento por filtro ou distorção pelo tema; tipografia/cor do título e personalizações da capa SHALL permanecer preservadas.

#### Scenario: Experiência responsiva
- **WHEN** fotógrafo ou cliente utiliza os dois temas em celular, tablet ou desktop
- **THEN** controles e informações permanecem legíveis sem overflow, com contraste mínimo de 4,5:1 no texto normal e 3:1 no texto grande e indicadores essenciais

#### Scenario: Fotografia e pagamento
- **WHEN** o usuário alterna o tema ao visualizar fotos ou pagar
- **THEN** a imagem permanece com suas cores originais e o QR Code mantém fundo e contraste adequados à leitura
