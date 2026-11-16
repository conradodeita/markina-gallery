# Proposal

## Why

O inventário de `enable-tenant-subdomain-ingress` constatou que o NPM 2.15.1 persistiria o token DNS em JSON no SQLite 0644, com diretórios ascendentes atravessáveis. A emissão wildcard precisa de custódia comprovada antes de receber uma credencial real, preservando o atendimento existente.

## What Changes

- Especificar custódia restrita, proteção em repouso e recuperação de credenciais DNS-01 sem persistência no banco compartilhado do NPM.
- Avaliar primeiro um emissor ACME dedicado com segredo cifrado fora do NPM; selecionar o mecanismo somente após provar integração, renovação e privilégios mínimos em laboratório local.
- Exigir evidência de ausência de segredo em DB/logs/artefatos, testes de falha e recuperação e plano de operação sem desativar hosts existentes.
- Manter token real, Cloudflare, NPM e Oracle fora da implementação local; qualquer operação externa exige revisão do mecanismo e autorização específica.

## Capabilities

### New Capabilities

Nenhuma.

### Modified Capabilities

- `deployment-operations`: precisar o uso de store seguro do servidor e acrescentar o contrato específico de custódia DNS-01 para o wildcard.

## Impact

Dependência de segurança para as tasks 3.3/3.4 de `enable-tenant-subdomain-ingress`. Pode afetar o mecanismo futuro de emissão/renovação e instalação do certificado no NPM; não substitui o proxy nem altera raiz/markina. Versões, licença, APIs, permissões e alcance do mecanismo candidato precisam de inventário próprio. Nenhuma instalação, credencial ou modificação externa está autorizada por esta proposta.
