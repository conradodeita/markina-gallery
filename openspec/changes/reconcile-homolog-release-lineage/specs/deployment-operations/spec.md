# Spec Delta

## Purpose

Manter a release de homologação alinhada ao código e ao grafo de migrations já instalados no servidor.

## ADDED Requirements

### Requirement: Publicar homologação sem retroceder a linha instalada

O fluxo de publicação de homologação SHALL usar uma revisão descendente da revisão de app confirmada pelo inventário. Migrations novas SHALL ter identificadores únicos e encadear a revisão efetivamente aplicada no banco. A aprovação de reviewer configurada no ambiente SHALL permanecer obrigatória.

#### Scenario: Branch de deploy está atrás do servidor

- **WHEN** o inventário confirma que o commit de homologação não é ancestral do alvo de deploy
- **THEN** o fluxo SHALL bloquear a publicação até reconciliar as branches e validar o alvo novamente

#### Scenario: Revisão Alembic já aplicada pertence a outra linha

- **WHEN** uma migration nova usa um identificador já associado a outro arquivo na revisão instalada
- **THEN** o fluxo SHALL bloquear a publicação até gerar um identificador único encadeado após a revisão aplicada e testar a atualização

#### Scenario: Branch de deploy não está permitida no ambiente

- **WHEN** o job de deploy usa a branch homologada pelo fluxo, mas a política do ambiente a rejeita
- **THEN** o fluxo SHALL manter a aprovação de reviewer e habilitar somente a branch de deploy designada, sem remover controles de produção

### Requirement: Separar gates de produção da validação de homologação

A CI SHALL executar as verificações de blobs e autorização do release facial em PRs com destino `main` e em pushes para `main`. A CI de `develop` SHALL manter seus testes de homologação e NÃO SHALL alterar, ignorar ou ampliar a lista de blobs autorizados para production.

#### Scenario: PR de homologação modifica arquivo também fixado pelo gate facial

- **WHEN** uma PR de `develop` altera um arquivo compartilhado, mas não muda comportamento facial
- **THEN** a CI SHALL validar o escopo da homologação sem executar o gate de release facial; o gate facial SHALL continuar obrigatório para qualquer PR direcionada a `main`
