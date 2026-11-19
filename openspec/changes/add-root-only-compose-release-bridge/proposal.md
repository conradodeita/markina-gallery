# Proposal

## Why

O inventário API/web usa um conjunto canônico de arquivos Compose, mas os containers ativos foram criados por snapshots protegidos, gerados pelos fluxos faciais e de preview. O helper não reconhece esses serviços e bloqueia o release; expor os snapshots à conta SSH comum ou ignorar a divergência destruiria a garantia de proveniência e o rollback.

## What Changes

- Decisão do proprietário em 19/11/2026: preparar adoção explícita do runtime saudável como nova base privada quando os labels apontarem para snapshots históricos divergentes. Essa decisão aprova o planejamento; não autoriza automaticamente instalação, captura persistente de credenciais ou deploy. O inventário normal continua falhando fechado até existir base adotada, comprovada e aprovada por operação protegida.
- Separar diagnóstico read-only, prova de reprodução do modelo ativo e adoção persistente protegida. Vincular a base aos IDs exatos de containers/imagens, configuração efetiva, fontes históricas e aprovação; preservar snapshots e valores TOTP existentes, sem editar `.env` ou recriar containers para corrigir labels.

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

O diagnóstico read-only de 19/11 confirmou que os labels apontam para snapshots anteriores ao runtime `bfe511f`: API difere em ambiente, usuário, labels e mounts; web difere em ambiente, comando, entrypoint, usuário e labels. As imagens referidas pelas fontes não são as ativas. O comparador ainda recusa `tmpfs` da API e há `CgroupnsMode` não padrão em ambos. Os valores de segredos não foram exibidos. A adoção não declara esses snapshots equivalentes: registra uma nova origem explicitamente aprovada e exige prova independente de que seu modelo reproduz o runtime.
