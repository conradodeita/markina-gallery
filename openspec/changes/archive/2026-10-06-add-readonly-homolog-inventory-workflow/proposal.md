## Why

O deploy de homologação é acionado por mudanças em `develop`, mas o fluxo de inventário disponível não está no branch padrão e compartilha o modo somente leitura com uma operação destrutiva. É necessário obter um inventário atual, revisável e claramente somente leitura antes de aprovar mudanças no ambiente.

## What Changes

- Adiciona um workflow manual, disponível em `main`, que exige o SHA completo esperado da versão implantada e valida a chave SSH do servidor.
- Adiciona um script de inventário limitado ao checkout e ao projeto Compose `markina-gallery` em `/opt/markina-gallery`.
- Expõe somente estado operacional e contagens agregadas necessárias para planejar homologação, sem PII, conteúdo de fotos, payloads de jobs ou segredos.
- Mantém o workflow separado de manutenção que pode apagar dados.

## Non-goals

- Não executa deploy, migration, backup, limpeza, restart, stop, prune ou alteração de configuração.
- Não consulta, lista ou altera recursos de outros projetos, proxy, firewall, DNS ou certificados.
- Não faz merge nem deploy da PR #139.

## Impact

- Domínio: `deployment-operations`.
- Novos arquivos: workflow dispatch-only, script remoto e cobertura automatizada de política/validação.
- Mesclar esta mudança em `main` não aciona o deploy, que permanece condicionado a push em `develop`.
- Após o merge, o inventário é disparado manualmente contra o SHA atualmente implantado; seu resultado será revisado antes de qualquer ação de deploy.
