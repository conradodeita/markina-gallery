## Why

O smoke do rebrand encontrou logo, favicon e ícone registrados no banco, mas arquivos ausentes: a API grava em `/app/media/branding`, fora dos volumes persistentes. Recriar o container pode perder esses uploads e impedir o uso da arte oficial e a instalação do aplicativo.

## What Changes

- Persistir os três ativos em volume exclusivo do projeto, independente do ciclo de vida da API.
- Preservar os arquivos legados ainda existentes antes da primeira recriação, sem sobrescrever ativos diferentes nem remover fontes.
- Manter uploads, validações, URLs, chaves de banco e preferências existentes; ausência de arquivo continua com fallback seguro, sem gerar arte substituta.
- Documentar backup dos arquivos, recuperação, reenvio dos ativos ausentes e verificação de recriação com comparação de hashes.
- Validar cirurgicamente armazenamento, upload e entrega de branding; sem suíte completa local.

## Capabilities

### New Capabilities

Nenhuma capacidade de produto adicional. O contrato de upload já está descrito em `add-branding-and-login-copy`; esta correção acrescenta durabilidade operacional.

### Modified Capabilities

- `deployment-operations`: persistência dos ativos de identidade visual e transição segura do armazenamento legado durante deploys.

## Impact

Compose da API, procedimento/script de deploy, testes direcionados e documentação operacional. Volume proposto `markina-gallery_branding-assets`, montado em `/var/lib/markina/branding`, sem porta pública ou acesso direto pelo proxy. Sem migration de banco, alteração financeira/facial, mudança de arte ou segredo. A nova publicação exige inventário e aprovação do plano operacional; autorização do deploy anterior não substitui esse gate.

Diagnóstico já realizado em `../rebrand-pick-your-pic/deployment-result.md`. Não foi determinado em qual recriação os arquivos desapareceram; os três arquivos individuais deverão ser reenviados após corrigir a persistência caso não sejam recuperáveis. Não repetir investigação ampla nem prometer recuperação a partir do backup SQL.
