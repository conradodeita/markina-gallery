## ADDED Requirements

### Requirement: Navegação permanente da cliente

A interface SHALL oferecer acesso consistente a `Galerias`, `Carrinho (N)` e `Compras` em todas as telas autenticadas da cliente, inclusive galeria, pasta, busca, revisão e detalhes de compra. A contagem SHALL representar as fotos do carrinho global persistido da identidade atual. Em dispositivos móveis, a navegação SHALL permanecer acessível sem cobrir fotos, ações essenciais, diálogos ou áreas seguras do dispositivo.

#### Scenario: Acesso a partir de uma pasta
- **WHEN** a cliente está em uma pasta com seleções também em outras galerias
- **THEN** pode abrir diretamente a revisão global pelo carrinho, acessar compras e retornar às galerias

#### Scenario: Galeria acessada por convite
- **WHEN** a cliente autenticada navega em uma galeria acessada por convite
- **THEN** encontra os mesmos destinos e a contagem global do restante da área da cliente

### Requirement: Revisão direta sem cards duplicados

O botão flutuante `Carrinho (N)` e os demais atalhos de carrinho SHALL abrir diretamente a tela `Revise suas fotos e faça o PIX`. Essa tela SHALL apresentar nomes de galeria seguidos das fotos selecionadas, identificação de pastas quando aplicável, quantidades e subtotais, e ao final um total geral, uma área PIX/QR Code e um botão `Informar pagamento`. A listagem de galerias SHALL NOT duplicar as mesmas galerias em cards adicionais de revisão do carrinho.

#### Scenario: Duas galerias com seleção
- **WHEN** a cliente possui cinco fotos de uma galeria e uma de outra
- **THEN** o botão mostra `Carrinho (6)` e abre os dois grupos de fotos na mesma revisão
- **AND** não exige escolher um card `Revisar carrinho` para cada galeria

#### Scenario: Carrinho vazio
- **WHEN** não há fotos selecionadas
- **THEN** o destino carrinho apresenta estado vazio com acesso às galerias, sem PIX ou comunicação de pagamento habilitada

#### Scenario: Acessibilidade da revisão
- **WHEN** a cliente usa teclado, leitor de tela ou uma tela móvel estreita
- **THEN** consegue identificar grupos, contagem, total, impedimentos e ações de pagamento com foco e rótulos acessíveis, sem rolagem horizontal obrigatória
