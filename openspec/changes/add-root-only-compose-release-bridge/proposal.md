# Proposal

## Why

O inventário API/web usa um conjunto canônico de arquivos Compose, mas os containers ativos foram criados por snapshots protegidos, gerados pelos fluxos faciais e de preview. O helper não reconhece esses serviços e bloqueia o release; expor os snapshots à conta SSH comum ou ignorar a divergência destruiria a garantia de proveniência e o rollback.

## What Changes

- Criar uma ponte operacional root-only, com interface fixa e comandos allowlistados para inventário, release e rollback somente de `api` e `web`.
- Validar os arquivos Compose pelos labels dos containers, limitar caminhos às raízes persistentes aprovadas, verificar tipo, symlink, proprietário/modo e hashes, e manter o conteúdo fora de logs e artefatos do GitHub.
- Fazer o preflight read-only usar a ponte exclusivamente para produzir inventário minimizado e fingerprint; permitir mutação somente pelo workflow protegido `production` após correspondência do fingerprint.
- Validar a origem Git por allowlist exata em HTTPS, URI SSH ou formato SCP do OpenSSH, somente para o host e repositório autorizados, sem reescrever `origin`.
- Preservar os snapshots originais e as imagens antes do release, e exigir novo inventário e aprovação próprios para rollback.
- Manter schema, `.env`, `APP_ENV=production`, `FACIAL_PROCESSING_ENABLED=true`, workers, banco, Redis, nginx, backup, dados e recursos de outros projetos fora do escopo.

## Capabilities

### New Capabilities

- `deployment-operations/root-only-app-compose-bridge`: acesso privilegiado restrito para inventariar e publicar/recuperar API/web quando a configuração ativa vem de snapshots Compose protegidos.

### Modified Capabilities

Nenhuma. O contrato geral do release API/web continua sendo o da change `add-production-app-release-workflow`; esta change adiciona a fronteira privilegiada necessária para atender a configuração existente.

## Impact

Afeta o helper de release API/web, o wrapper SSH de preflight, o workflow CI, os instaladores root-owned, testes de contrato/segurança e o runbook. A instalação e o primeiro uso no host ocorrerão somente depois de CI/PR verdes e por workflow protegido; nenhuma configuração de produção será lida ou alterada por esta proposta.

## Proveniência do corte de 17/11

O proprietário aprovou em 18/11 a retomada pela configuração efetiva comprovada no recibo privado do promovido `bfe511f8`. A ponte passa a admitir esse par exato de containers Docker Engine e os sucessores registrados por ela. O caminho Compose existente continua exigindo equivalência com as suas próprias fontes. As fontes históricas deste par continuam protegidas, verificadas e preservadas para recuperação sem serem tratadas como prova do runtime promovido.
