## ADDED Requirements

### Requirement: Processamento facial automático por pasta privada

O sistema SHALL iniciar reconhecimento facial para cada foto de conteúdo enviada a uma pasta privada quando o gate operacional facial global estiver habilitado e a foto cumprir os requisitos técnicos e de privacidade vigentes. A interface da pasta SHALL NOT oferecer herança, permissão ou pausa de novos trabalhos facial por pasta. O progresso SHALL permanecer visível, e a ação de retentativa SHALL chamar-se “Refazer reconhecimento”.

#### Scenario: Upload em pasta privada elegível

- **WHEN** uma foto de conteúdo termina o upload numa pasta privada e o gate facial operacional está habilitado
- **THEN** a foto entra no fluxo facial durável e o progresso existente reflete o trabalho sem ação manual do fotógrafo

#### Scenario: Gate facial global indisponível

- **WHEN** uma foto é enviada enquanto o rollout operacional global não admite novos trabalhos
- **THEN** nenhum job facial é criado, o estado informa indisponibilidade e a interface não oferece uma opção local para contornar o gate

#### Scenario: Retentativa manual

- **WHEN** o fotógrafo aciona “Refazer reconhecimento”
- **THEN** somente falhas e fotos elegíveis sem índice são reenfileiradas de forma idempotente

### Requirement: Ajuste automático isolado por pasta privada

Cada pasta do Acervo do Cliente com `audience_scope = 'selected'` SHALL possuir configuração efetiva independente da galeria pública, ativa por padrão com intensidade 75% e exposição 0,0 EV. A interface SHALL NOT oferecer herança, personalização opcional ou desligamento por pasta. Mudanças de intensidade ou exposição SHALL ser salvas automaticamente e aplicar-se às próximas prévias.

#### Scenario: Pasta privada criada ou aberta sem configuração

- **WHEN** uma pasta privada não possui configuração própria ou tem somente valor herdado/desligado legado
- **THEN** o sistema apresenta e aplica configuração ativa em 75% e 0,0 EV, sem ler valores da galeria pública

#### Scenario: Reconhecimento facial concluído

- **WHEN** o reconhecimento facial de uma foto termina com sucesso
- **THEN** um job durável de ajuste de prévia é criado com a configuração vigente da pasta

#### Scenario: Ajuste facial falhou

- **WHEN** o job facial da foto termina em falha
- **THEN** o ajuste automático daquela foto não começa até o reconhecimento ser refeito com sucesso, e a prévia convencional permanece disponível

#### Scenario: Parâmetro alterado durante trabalho

- **WHEN** intensidade ou exposição é alterada enquanto há ajuste enfileirado ou em execução
- **THEN** trabalhos da geração anterior são cancelados logicamente e a foto é reprocessada com os novos valores a partir do derivado limpo da fonte original, sem usar o resultado ajustado anterior

#### Scenario: Progresso e ordem visual

- **WHEN** o fotógrafo abre o processamento de uma pasta privada no desktop
- **THEN** o cartão de reconhecimento facial aparece acima do cartão de ajuste automático, os dois ocupam uma coluna, as barras de progresso permanecem e o menu recolhível da pasta continua disponível

### Requirement: Preservação da fonte e autorização

O ajuste privado SHALL preservar o original, a prévia convencional, a entrada facial e as proteções atuais. Jobs SHALL ser executados fora do ciclo HTTP, com autorização administrativa para configuração e leitura de progresso, e validação de geração antes da publicação.

#### Scenario: Processamento repetido

- **WHEN** a mesma foto é reprocessada após alteração de parâmetros
- **THEN** o motor usa a fonte limpa vinculada ao original, preserva os outros derivados e publica apenas o resultado da geração vigente
