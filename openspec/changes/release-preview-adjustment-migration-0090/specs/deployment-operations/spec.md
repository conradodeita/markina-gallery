# Spec Delta

## ADDED Requirements

### Requirement: Release dedicado da migration de intensidade de prévias
O sistema SHALL oferecer operações manuais separadas para inventariar e publicar exclusivamente a migration `20261026_0090`, avançando de `20261025_0089` para `20261026_0090` e iniciando apenas os runtimes compatíveis previstos no plano aprovado. O fluxo SHALL falhar fechado diante de SHA, schema, diff ou serviço divergente.

#### Scenario: Origem e alvo aprovados
- **WHEN** o SHA candidato está integrado à `main`, todos os checks exigidos passaram, o inventário confirma schema `20261025_0089` e o fingerprint exato foi aprovado
- **THEN** o release aplica somente `20261026_0090`, publica os runtimes aprovados e confirma schema `20261026_0090` antes de liberar tráfego

#### Scenario: Schema ou escopo divergente
- **WHEN** o inventário aponta revisão diferente, o diff contém outra migration ou runtime não aprovado, ou o estado muda após aprovação
- **THEN** o procedimento falha antes de alterar banco, containers ou configuração

### Requirement: Backup e aprovação precedem a migration de produção
O release SHALL validar um backup recente e restaurável, executar preflight somente-leitura separado e vincular a aprovação humana ao fingerprint completo do SHA e do estado operacional observado. A credencial mutável SHALL permanecer indisponível ao preflight.

#### Scenario: Backup ou aprovação ausente
- **WHEN** o backup não pode ser verificado, o fingerprint está ausente/divergente ou não houve aprovação específica
- **THEN** nenhum escritor é interrompido e nenhuma migration ou publicação é iniciada

### Requirement: Recuperação da release 0090 falha fechada
O release SHALL preservar versão e imagens anteriores e SHALL NOT executar downgrade, restauração do banco ou rollback automático após iniciar a migration. Falha SHALL manter o tráfego fechado e registrar estado suficiente para recuperação explicitamente aprovada.

#### Scenario: Falha após início da migration
- **WHEN** Alembic iniciou e a verificação de schema, saúde ou smoke falha
- **THEN** o fluxo preserva backup, schema e artefatos, não declara sucesso nem executa downgrade automático, e exige reconciliação antes de liberar tráfego

### Requirement: Atualização restrita do wrapper de preflight
O sistema SHALL oferecer uma operação manual protegida que instale atomicamente somente o wrapper versionado e com SHA/blob verificados no caminho root-owned aprovado. A operação SHALL preservar backup e permissões `root:root 0755`, SHALL NOT alterar `authorized_keys` nem tocar em serviços, banco, imagens ou runtimes e SHALL verificar a recusa de comandos SSH arbitrários.

#### Scenario: Wrapper instalado com identidade exata
- **WHEN** a operação manual na `main` passa CI e aprovação do environment `production`, e o SHA/blob do wrapper corresponde ao checkout versionado
- **THEN** a cópia root-owned é substituída atomicamente, a anterior é preservada em backup e proprietário/modo/hash são conferidos

#### Scenario: Blob, sudo ou chave restrita diverge
- **WHEN** o arquivo, permissões, acesso root não interativo ou regra SSH restrita diferem do contrato esperado
- **THEN** a instalação falha fechada, não altera `authorized_keys` nem serviços e não inicia preflight ou release
