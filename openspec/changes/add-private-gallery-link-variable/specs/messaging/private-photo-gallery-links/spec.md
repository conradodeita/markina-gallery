# Spec Delta

## Purpose

Definir como o aviso WhatsApp de novas fotos privadas inclui um endereço seguro para a galeria pública que originou a pasta privada.

## ADDED Requirements

### Requirement: Link da galeria de origem no aviso WhatsApp

O template WhatsApp do evento `private_photos_ready` SHALL aceitar a variável `{{link_galeria}}`, resolvida pelo servidor para a galeria-mãe associada ao evento. O texto padrão SHALL ser `Essa mensagem é automática! Novas fotos disponíveis na sua galeria. Acesso no link: {{link_galeria}}.`. A variável SHALL ser exibida entre as variáveis disponíveis na configuração administrativa e SHALL NOT estar disponível em push ou em outros eventos.

#### Scenario: Aviso de pasta privada criada por galeria
- **WHEN** um aviso WhatsApp `private_photos_ready` é criado para uma pasta privada derivada de uma galeria
- **THEN** `{{link_galeria}}` é substituída pelo endereço HTTPS canônico `/public-galleries/{uuid-da-galeria-mãe}`, sem token de autenticação, e a mensagem renderizada é persistida no snapshot do evento

#### Scenario: Galeria-mãe em aviso de pasta restrita
- **WHEN** um aviso WhatsApp `private_photos_ready` é criado para uma pasta privada restrita
- **THEN** o link usa a galeria-mãe já associada ao contexto do evento, sem usar o nome da pasta privada nem um endereço fornecido pelo cliente

#### Scenario: Configuração administrativa
- **WHEN** o administrador configura o template WhatsApp de `private_photos_ready`
- **THEN** a lista de variáveis disponíveis inclui `{{link_galeria}}`, a prévia demonstra uma URL da galeria e a validação aceita essa variável somente nesse evento e canal

### Requirement: Validação do destino e isolamento de canal

O servidor SHALL construir o endereço exclusivamente a partir da galeria-mãe persistida e do hostname HTTPS canônico validado para o tenant. SHALL rejeitar hostnames fornecidos pela requisição, hosts não canônicos, protocolos diferentes de HTTPS, credenciais, portas, parâmetros e fragmentos. Se não houver galeria-mãe válida ou hostname canônico validado, SHALL cancelar somente a entrega WhatsApp antes de qualquer tentativa de transporte, preservando o fluxo independente de push.

#### Scenario: Origem ou hostname inválido
- **WHEN** o evento não possui uma galeria-mãe válida ou o tenant não possui hostname canônico HTTPS validável
- **THEN** a entrega WhatsApp é cancelada com motivo operacional sanitizado, nenhuma URL arbitrária é enviada e os demais canais seguem sua política independente

#### Scenario: Tentativa de injetar destino
- **WHEN** dados de requisição ou template tentam fornecer domínio, esquema, porta, parâmetros ou fragmento para `{{link_galeria}}`
- **THEN** o servidor ignora esses dados e usa apenas o destino canônico derivado do contexto persistido, ou cancela WhatsApp caso esse destino não possa ser validado

#### Scenario: Acesso continua protegido
- **WHEN** o destinatário abre o link da galeria
- **THEN** a galeria aplica seu fluxo normal de autorização e OTP, sem conceder acesso por meio da mensagem ou do próprio link

### Requirement: Atualização segura do texto padrão

Uma atualização SHALL substituir o texto anterior padrão `Novas fotos disponíveis na sua galeria.` pelo novo texto padrão somente quando o valor armazenado corresponder exatamente ao padrão anterior. SHALL preservar templates personalizados e SHALL afetar apenas avisos criados após a atualização, sem alterar snapshots ou entregas existentes.

#### Scenario: Template padrão anterior
- **WHEN** a atualização encontra configuração de `private_photos_ready` cujo texto WhatsApp é exatamente `Novas fotos disponíveis na sua galeria.`
- **THEN** atualiza o texto para o novo padrão e incrementa a versão da configuração conforme o contrato existente

#### Scenario: Template personalizado ou histórico
- **WHEN** a configuração contém outro texto, ou existem mensagens de evento já persistidas
- **THEN** preserva o texto personalizado e o conteúdo de todas as mensagens e snapshots existentes
