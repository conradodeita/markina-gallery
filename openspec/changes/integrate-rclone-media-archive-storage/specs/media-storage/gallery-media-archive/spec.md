# Spec Delta

## ADDED Requirements

### Requirement: Provider alternativo preserva o ciclo de arquivo frio

Um provider de armazenamento alternativo SHALL usar o mesmo catálogo, executor, fila, lease, manifesto, API e billing do arquivo frio existente. SHALL preservar isolamento por tenant e a verificação integral antes de promover arquivo ou recuperação. MUST NOT criar autorização, operação, cobrança, prazo ou retenção paralelos.

#### Scenario: Arquivo frio usa provider Rclone aprovado

- **WHEN** o executor recebe explicitamente um provider Rclone durável e autorizado para o tenant
- **THEN** a pasta e seus objetos seguem o ciclo, ownership, namespace e readback já definidos por `add-gallery-media-archive`
- **AND** elegibilidade, reserva/liberação de créditos em falha comprovada, isenção do proprietário, reconciliação e ausência de expurgo automático seguem o contrato compartilhado
- **AND** cada nova recuperação paga libera exatamente 30 dias após a recuperação íntegra; prazo inicial por pasta e janela pré-arquivo permanecem como definidos pelo produto, e recuperações já contratadas preservam o prazo registrado
- **AND** o tenant vê o progresso efetivo da recuperação, sem promessa de SLA de duração, e créditos só são debitados após promoção bem-sucedida
- **AND** opções históricas de 7/14/30 dias não regem novas recuperações

#### Scenario: Provider não foi aprovado ou configurado

- **WHEN** não há provider durável explicitamente configurado ou a configuração é inválida/ambígua
- **THEN** o worker não consulta nem reivindica operações e nenhum provider ou storage sintético é selecionado como fallback

### Requirement: Identidade explícita acompanha cada objeto novo

O catálogo e cada item do manifesto v2 SHALL persistir `provider_id` opaco e tenant-scoped. Todo novo objeto SHALL registrar identidade escolhida; gravações Rclone MUST NOT omiti-la. A composição seleciona o adapter por objeto antes de chamar `MediaArchiveStorage`, sem alterar as assinaturas do protocolo.

#### Scenario: Nova gravação Rclone persiste identidade por objeto

- **WHEN** o executor grava objeto novo por um binding Rclone autorizado
- **THEN** catálogo e item de manifesto v2 recebem o `provider_id` explícito e a leitura/exclusão futura usa o mesmo binding

### Requirement: OAuth preserva binding somente para a mesma conta e raiz

Uma reautorização SHALL preservar `provider_id` somente quando identidade estável e verificada da conta e raiz de mídia forem iguais. Mudança de conta ou raiz SHALL criar novo binding; objetos existentes MUST NOT ser reatribuídos. E-mail MUST NOT ser a única evidência de identidade.

#### Scenario: Reautorização mantém conta e raiz

- **WHEN** OAuth reconecta a mesma conta verificada e a raiz de mídia não mudou
- **THEN** a credencial pode ser rotacionada sem mudar `provider_id` nem o roteamento dos objetos existentes

#### Scenario: Conta ou raiz mudou

- **WHEN** a conta verificada ou a raiz de mídia difere do binding existente
- **THEN** novas gravações usam outro `provider_id` e objetos antigos continuam associados ao binding anterior, sem fallback

### Requirement: Registros legados continuam no Drive sem fallback

Catálogo legado sem `provider_id` e manifesto v1 sem provider SHALL resolver somente para o adapter Drive legado, sem migração automática. Se o binding Drive não resolver, a operação falha fechado. Identidade ausente em v2, desconhecida, de outro tenant ou divergente entre catálogo/manifesto MUST NOT acionar outro provider.

#### Scenario: Objeto legado mantém o provider Drive

- **WHEN** a leitura ou exclusão recebe registro sem `provider_id` legado ou item de manifesto v1 sem provider
- **THEN** a composição resolve somente o adapter Drive legado e não migra nem tenta outro provider se esse binding estiver indisponível

#### Scenario: Binding original de V1 não pode ser comprovado

- **WHEN** os registros V1 não permitem provar a conta e a raiz Drive originais
- **THEN** leitura, recuperação e exclusão falham fechado sem usar a conta/raiz conectada atualmente

#### Scenario: Identidade ausente ou divergente

- **WHEN** um registro v2 não tem `provider_id`, o binding não pertence ao tenant ou catálogo e manifesto divergem
- **THEN** a operação falha fechado antes de ler, gravar, restaurar ou excluir bytes, sem fallback automático
