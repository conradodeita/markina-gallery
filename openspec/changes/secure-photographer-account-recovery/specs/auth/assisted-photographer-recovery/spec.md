# Spec Delta

## Purpose

Separar identificação cadastral de comprovação de titularidade no atendimento de recuperação do fotógrafo, protegendo o histórico e a decisão administrativa de reabertura.

## ADDED Requirements

### Requirement: Identificação não concede acesso

O sistema SHALL permitir conferir nome e CPF para identificar um cadastro em atendimento autorizado. Esses dados MUST NOT, sozinhos, comprovar titularidade, autorizar troca de e-mail, criar sessão ou liberar histórico. Respostas públicas SHALL evitar enumeração de contas.

#### Scenario: Pessoa conhece nome e CPF
- **WHEN** uma pessoa informa nome e CPF de um fotógrafo
- **THEN** não recebe acesso, histórico nem autorização de troca de e-mail apenas por conhecer esses dados

### Requirement: Meios anteriores antes do atendimento excepcional

O sistema SHALL priorizar recuperação pelos meios anteriormente verificados e vinculados ao fotógrafo. Telefone informado ou canal WhatsApp pareado MUST NOT ser tratado como comprovação de titularidade por si só. Nome/CPF não concedem acesso. O sistema SHALL orientar atendimento manual quando os meios disponíveis não puderem ser usados.

#### Scenario: Fotógrafo mantém meio válido
- **WHEN** o fotógrafo consegue usar recuperação existente por e-mail ou fatores válidos
- **THEN** recebe orientação para esse caminho antes da exceção administrativa

#### Scenario: Todos os meios anteriores foram perdidos
- **WHEN** o fotógrafo não consegue usar nenhum meio anterior
- **THEN** pode procurar o proprietário externamente, sem desbloqueio automático por nome, CPF ou novo e-mail

### Requirement: Decisão manual externa do proprietário

Somente o proprietário SHALL autorizar excepcionalmente a recuperação após verificar a identidade fora do sistema e declarar sua decisão no console. O SaaS MUST exigir confirmação explícita e motivo auditável, sem exigir fator antigo para essa exceção. O SaaS MUST NOT coletar documento, selfie ou evidências externas nesse fluxo.

#### Scenario: Proprietário reconhece a identidade no atendimento externo
- **WHEN** o proprietário confirma que verificou a identidade e atende os controles da ação sensível
- **THEN** pode iniciar a recuperação assistida, sujeita à verificação do novo e-mail e aos gates de estado da conta

#### Scenario: Declaração ausente ou ator sem permissão
- **WHEN** falta confirmação manual, motivo ou autorização do proprietário
- **THEN** a identidade e o acesso permanecem inalterados

### Requirement: Proprietário autoriza operação sensível auditada

Somente o proprietário autenticado e reautenticado SHALL concluir a troca assistida após a declaração de verificação externa e a verificação do novo e-mail. A operação SHALL registrar alvo, ator, motivo e instante, invalidar sessões anteriores e impedir replay, sem expor provas pessoais, senhas ou códigos na resposta ou auditoria comum.

#### Scenario: Sessão ou identidade mudou durante atendimento
- **WHEN** a confirmação usa sessão, alvo ou estado desatualizado
- **THEN** a operação é recusada e exige nova conferência, sem alterar outro tenant

### Requirement: Recuperação de identidade não reabre conta

Troca assistida de e-mail SHALL preservar o encerramento e a suspensão. Recuperação de arquivos e reabertura SHALL continuar ações separadas, com seus gates existentes. Exclusão definitiva de mídia MUST NOT ser revertida por recuperação de identidade.

#### Scenario: Conta encerrada troca e-mail com atendimento comprovado
- **WHEN** a troca é concluída para uma conta encerrada
- **THEN** a conta continua sem acesso até a reabertura administrativa autorizada e as demais condições aplicáveis

### Requirement: Desafio ligado ao atendimento

A verificação do contato SHALL ficar ligada à mesma conta, atendimento e destinatário autorizado, com expiração e consumo único. Provas de fatores antigos, quando usadas, SHALL manter os controles existentes. A exceção manual MUST depender da declaração e reautenticação do proprietário, sem exigir fator antigo perdido.

#### Scenario: Fotógrafo verifica novo contato no atendimento autorizado
- **WHEN** fotógrafo verifica o novo e-mail no atendimento manual autorizado pelo proprietário
- **THEN** o proprietário pode confirmar a troca com reautenticação, sem reabrir automaticamente uma conta encerrada

#### Scenario: Prova reutilizada ou destinatário alterado
- **WHEN** uma prova consumida é reapresentada ou usada para outro atendimento, conta ou destinatário
- **THEN** a operação é recusada e não altera a identidade de nenhuma conta
