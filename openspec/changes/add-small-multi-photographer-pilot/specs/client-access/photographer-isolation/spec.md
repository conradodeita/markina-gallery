# Spec Delta

## Purpose

Permitir fotógrafos independentes na mesma instalação, preservando a separação de clientes, acervos, comércio, configurações e efeitos assíncronos em todas as jornadas.

## ADDED Requirements

### Requirement: Cliente independente por conta de fotógrafo

O sistema SHALL manter identidade de cliente própria de cada conta de fotógrafo, com unicidade de telefone normalizado dentro da conta. O mesmo telefone SHALL poder existir em contas diferentes com UUIDs e dados independentes. O sistema MUST NOT mesclar cadastros, revelar existência em outra conta ou propagar alterações de nome, telefone, preferências, exclusão, consentimento ou histórico entre contas.

#### Scenario: Mesmo telefone com dois fotógrafos
- **WHEN** dois fotógrafos cadastram o mesmo telefone em suas respectivas contas
- **THEN** cada um recebe uma identidade distinta e visualiza somente seu cadastro e seus vínculos

#### Scenario: Alteração ou exclusão em uma conta
- **WHEN** uma cliente muda seu telefone ou tem exclusão operacional elegível confirmada na conta A
- **THEN** o cadastro, os acessos e o histórico da cliente com o mesmo telefone na conta B permanecem inalterados

#### Scenario: Duplicação dentro da conta
- **WHEN** um cadastro tenta usar telefone já reservado por outra cliente da mesma conta
- **THEN** a operação é recusada sem mesclar identidades, preservando as verificações e proteções existentes

### Requirement: Domínio e efeitos restritos ao proprietário

O sistema SHALL revalidar a conta ativa e o vínculo autorizado antes de listar, ler, alterar ou excluir recursos. Galerias, pastas, fotos e suas variantes, clientes, vínculos, seleções, favoritos, comentários, visualizações, carrinhos, pedidos, pagamentos, entregas, histórico, estatísticas e auditorias de domínio SHALL permanecer no mesmo proprietário. Referências cruzadas MUST ser recusadas também na persistência. Identificadores, URLs de mídia, filtros e parâmetros externos MUST NOT ampliar o escopo.

#### Scenario: Identificador da outra conta
- **WHEN** fotógrafo ou cliente da conta A solicita recurso ou arquivo da conta B, inclusive por URL direta
- **THEN** o backend nega o acesso sem revelar conteúdo ou metadados da conta B

#### Scenario: Carrinho com recebedores distintos
- **WHEN** uma operação tenta vincular foto, cliente, pedido ou carrinho de contas distintas
- **THEN** a operação falha integralmente e nenhum pedido ou pagamento misto é criado

### Requirement: Configuração comercial e comunicação próprias da conta

Branding comercial, PIX, preços editáveis, templates, preferências de avisos e processamento de prévias SHALL ser resolvidos na conta proprietária. A ausência de configuração SHALL apresentar estado não configurado ou canal indisponível, sem usar dados comerciais ou canal de outra conta. Conectores externos SHALL exigir vínculo explícito e autorização operacional; credenciais MUST permanecer fora de tabelas comuns, frontend, logs e relatórios. Configurações técnicas de instalação e catálogos imutáveis compartilhados SHALL permanecer restritos à operação e sem dados comerciais de fotógrafos.

#### Scenario: Segunda conta recém-criada
- **WHEN** o fotógrafo B abre configurações antes de configurar sua identidade e canais
- **THEN** não recebe logo, PIX, destinatários administrativos nem integrações comerciais do fotógrafo A

#### Scenario: Canal não vinculado
- **WHEN** um aviso ou OTP da conta B exige canal externo ainda não vinculado
- **THEN** o sistema informa indisponibilidade de forma sanitizada e não envia pelo canal da conta A

### Requirement: Contexto durável em jobs e manutenção

Jobs, outboxes, tentativas, deduplicação, caches e operações de lifecycle SHALL carregar ou derivar proprietário persistido de fonte autorizada, revalidando-o antes de efeitos e publicação. Workers MUST NOT escolher uma conta pelo primeiro registro ou por um contexto global. Suspensão ou revogação SHALL impedir efeitos da conta afetada sem bloquear jobs válidos de outras contas. Limpezas, exclusões e retenção SHALL respeitar o proprietário e as proteções comerciais existentes; permissões biométricas SHALL permanecer específicas e não ser copiadas entre contas.

#### Scenario: Suspensão durante job
- **WHEN** a conta A é suspensa após iniciar um job e antes da publicação
- **THEN** o job não publica conteúdo nem envia avisos de A, preserva estado durável conforme sua política e trabalhos válidos de B continuam executáveis

#### Scenario: Repetição com duas contas
- **WHEN** ambas as contas executam operações equivalentes com retries ou caches
- **THEN** cada resultado e efeito permanece associado à sua conta, sem reaproveitar autorização, resultado ou deduplicação da outra

### Requirement: Legado preservado e ativação condicionada

A evolução SHALL atribuir o legado à conta única já existente, preservando UUIDs, relacionamentos, valores, snapshots, arquivos, credenciais e configurações dessa conta. Dados sem proprietário inequívoco SHALL impedir a liberação até reconciliação documentada. A segunda conta SHALL permanecer não operacional até aprovação e comprovação do isolamento em todos os caminhos inventariados. A mudança MUST NOT relaxar os gates biométricos ou permitir restauração destrutiva automática.

#### Scenario: Ensaio de migration do legado
- **WHEN** o upgrade é aplicado a cópia sintética representativa da instalação única
- **THEN** contagens, identidades, vínculos, instruções comerciais e referências de mídia anteriores permanecem equivalentes dentro da conta original

#### Scenario: Proprietário ambíguo
- **WHEN** o inventário encontra registro cuja propriedade não pode ser demonstrada
- **THEN** a liberação é bloqueada com evidência sanitizada, sem eleger conta arbitrariamente
