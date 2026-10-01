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

#### Scenario: Prévia e comparação por URL direta
- **WHEN** uma sessão de A usa UUID de foto, variante ou comparação de prévia pertencente a B
- **THEN** o backend recusa antes de resolver o caminho ou ler o arquivo, sem metadados de B, mantendo a autorização por pasta nos acessos próprios

#### Scenario: Upload retomável e arquivo legado
- **WHEN** o fotógrafo retoma um JPEG já registrado em pasta própria ou registra um JPEG novo
- **THEN** o registro legado conserva sua storage key e UUID, enquanto o novo arquivo recebe namespace de conta atribuído pelo servidor, sem aceitar chave de outra pasta ou conta

### Requirement: Configuração comercial e comunicação próprias da conta

Branding comercial, PIX, preços editáveis, templates, preferências de avisos e processamento de prévias SHALL ser resolvidos na conta proprietária. A ausência de configuração SHALL apresentar estado não configurado ou canal indisponível, sem usar dados comerciais ou canal de outra conta. Conectores externos SHALL exigir vínculo explícito e autorização operacional; credenciais MUST permanecer fora de tabelas comuns, frontend, logs e relatórios. Configurações técnicas de instalação e catálogos imutáveis compartilhados SHALL permanecer restritos à operação e sem dados comerciais de fotógrafos.

#### Scenario: Segunda conta recém-criada
- **WHEN** o fotógrafo B abre configurações antes de configurar sua identidade e canais
- **THEN** não recebe logo, PIX, destinatários administrativos nem integrações comerciais do fotógrafo A

#### Scenario: Canal não vinculado
- **WHEN** um aviso ou OTP da conta B exige canal externo ainda não vinculado
- **THEN** o sistema informa indisponibilidade de forma sanitizada e não envia pelo canal da conta A

#### Scenario: Associação ambígua ou credenciais de outro ambiente
- **WHEN** a configuração de servidor associa duas contas ao mesmo alias, instância no mesmo endpoint ou segredo de webhook, ou usa credenciais de outro ambiente
- **THEN** o transporte afetado é recusado sem expor valores de configuração e sem escolher a primeira associação

#### Scenario: Webhook de outra instância
- **WHEN** um evento usa o segredo de B com a instância registrada de A ou um ID externo também existente em B
- **THEN** a fronteira recusa a associação incompatível; um evento autorizado de A atualiza e deduplica somente registros de A

#### Scenario: Destinatário revogado durante consulta do canal
- **WHEN** a conta é suspensa ou o vínculo do destinatário é revogado após o claim e antes do envio
- **THEN** o transporte revalida a conta e o destinatário antes de descriptografar ou enviar; suspensão anterior ao efeito conserva o trabalho durável, sem consumir a fila de B

#### Scenario: Reenvio OTP com canal removido
- **WHEN** o vínculo de canal deixa de existir antes do reenvio do desafio
- **THEN** a operação informa indisponibilidade sem trocar hash, invalidar a entrega anterior ou usar o canal legado de outra conta

#### Scenario: Recuperação pública com canal próprio indisponível
- **WHEN** a recuperação administrativa recebe e-mail conhecido ou desconhecido e o canal OTP próprio não está disponível
- **THEN** mantém resposta pública neutra e desafio técnico sem sujeito elegível, sem envio nem fallback para outra conta, preservando desafios elegíveis anteriores

#### Scenario: Marca contextual na entrada
- **WHEN** uma entrada apresenta convite opaco válido da conta B, mesmo com sessão de A
- **THEN** a marca e os assets são resolvidos por B, com resposta privada sem cache; convite explicitamente inválido ou entrada anônima sem contexto apresenta somente identidade técnica, sem escolher uma conta

#### Scenario: Confirmação do PIX com vínculo revogado
- **WHEN** o proprietário do desafio difere da conta autorizada ou o vínculo administrativo é revogado antes da confirmação ou reenvio
- **THEN** o sistema recusa antes de consumir o código ou alterar o desafio e mantém o PIX de ambas as contas

### Requirement: Contexto durável em jobs e manutenção

Jobs, outboxes, tentativas, deduplicação, caches e operações de lifecycle SHALL carregar ou derivar proprietário persistido de fonte autorizada, revalidando-o antes de efeitos e publicação. Workers MUST NOT escolher uma conta pelo primeiro registro ou por um contexto global. Suspensão ou revogação SHALL impedir efeitos da conta afetada sem bloquear jobs válidos de outras contas. Limpezas, exclusões e retenção SHALL respeitar o proprietário e as proteções comerciais existentes; permissões biométricas SHALL permanecer específicas e não ser copiadas entre contas.

#### Scenario: Revalidação contextual antes do commit
- **WHEN** uma transação altera registros de A e a conta é suspensa ou o vínculo administrativo demonstrado é revogado antes do commit
- **THEN** recusa a transação de A, inclusive após flush intermediário, sem selecionar uma conta global nem impedir transações independentes autorizadas de B

#### Scenario: Suspensão durante job
- **WHEN** a conta A é suspensa após iniciar um job e antes da publicação
- **THEN** o job não publica conteúdo nem envia avisos de A, preserva estado durável conforme sua política e trabalhos válidos de B continuam executáveis

#### Scenario: Limpeza periódica de segurança com conta suspensa
- **WHEN** A é suspensa antes ou durante a minimização de desafios administrativos terminais e B continua ativa
- **THEN** conserva material contextual de A e conclui a minimização de B em transação independente; material técnico sem owner não é atribuído a qualquer fotógrafo

#### Scenario: Repetição com duas contas
- **WHEN** ambas as contas executam operações equivalentes com retries ou caches
- **THEN** cada resultado e efeito permanece associado à sua conta, sem reaproveitar autorização, resultado ou deduplicação da outra

#### Scenario: Limpeza com manifesto ou chave legada cruzada
- **WHEN** um manifesto de A contém arquivo de B ou uma chave legada resolve para referência viva de B
- **THEN** a limpeza recusa o lote antes do primeiro unlink, preserva os arquivos e registra falha sanitizada para reconciliação

#### Scenario: Falha do provider facial após suspensão
- **WHEN** o carregamento do provider falha após suspender a conta do job reservado
- **THEN** não registra falha/retry contextual nem interrompe o worker; libera somente o lease demonstrado para retomada, preservando o trabalho de B

#### Scenario: Referência facial com autorização interrompida
- **WHEN** conta, origem, política, público autorizado ou lease deixa de ser válido antes de ler referência cifrada, descriptografar índice ou publicar resultado
- **THEN** o processamento revalida a origem própria e impede o efeito; criptografia, AAD e nomes UUID legados permanecem compatíveis

#### Scenario: Retomada facial em outra identidade ou sessão
- **WHEN** o navegador troca de cliente ou sessão autenticada, recebe recusa de acesso ou encerra a sessão
- **THEN** o estado facial anterior é removido e respostas em voo não o restauram; a retomada guarda somente o UUID da consulta dentro de contexto opaco de conta, cliente e sessão validado pelo servidor

#### Scenario: Logout com instalação push em contas independentes
- **WHEN** um cliente ou administrador de A encerra sua sessão com instalação push ativa, enquanto B permanece autenticada
- **THEN** valida a instalação antes de revogar a sessão na mesma transação e desativa somente as inscrições da sessão A, preservando sessão e inscrições de B

### Requirement: Legado preservado e ativação condicionada

A evolução SHALL atribuir o legado à conta única já existente, preservando UUIDs, relacionamentos, valores, snapshots, arquivos, credenciais e configurações dessa conta. Dados sem proprietário inequívoco SHALL impedir a liberação até reconciliação documentada. A segunda conta SHALL permanecer não operacional até aprovação e comprovação do isolamento em todos os caminhos inventariados. A mudança MUST NOT relaxar os gates biométricos ou permitir restauração destrutiva automática.

#### Scenario: Ensaio de migration do legado
- **WHEN** o upgrade é aplicado a cópia sintética representativa da instalação única
- **THEN** contagens, identidades, vínculos, instruções comerciais e referências de mídia anteriores permanecem equivalentes dentro da conta original

#### Scenario: Proprietário ambíguo
- **WHEN** o inventário encontra registro cuja propriedade não pode ser demonstrada
- **THEN** a liberação é bloqueada com evidência sanitizada, sem eleger conta arbitrariamente
