## Why

A autenticação unificada está validada localmente, mas não pode ser levada a um servidor compartilhado sem um plano verificável de homologação. O plano precisa impedir impacto em outros projetos e exigir que banco, segredos, migration e smoke tests sejam preparados antes de qualquer publicação.

## What Changes

- Registrar o procedimento de preparação de homologação para a autenticação.
- Exigir inventário somente-leitura do servidor, definição explícita de porta e subdomínio, e aprovação do proprietário antes de mudanças externas.
- Definir variáveis, migration Alembic, seed seguro do administrador e smoke tests como gates da futura implantação.
- Documentar rollback limitado ao projeto `markina-gallery`.

## Capabilities

### New Capabilities

<!-- Nenhuma. -->

### Modified Capabilities

- `deployment-operations`: acrescentar os gates de homologação e rollback para a autenticação unificada.

## Impact

- Homologação controlada da Markina Gallery e um host HTTPS novo no Proxy Manager, somente após aprovação humana explícita.
- Nenhum recurso existente de terceiros será editado, removido ou reiniciado; o único compartilhamento autorizado é a associação do nginx da Markina à rede de entrada já usada pelo Proxy Manager.
