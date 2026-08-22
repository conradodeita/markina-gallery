## Why

A Markina Gallery começa sem repositório, sem estrutura de engenharia e sem especificações consolidadas; a INSTRUCOES_EXECUTOR_CLAUDE_CODE.md (§1.1 e §11) e o ROADMAP_ARQUITETURA.md (Fase 0) exigem que a primeira mudança estabeleça a fundação do projeto antes de qualquer implementação.

## What Changes

- Inicialização do Git com branch `main`, identidade configurada somente no repositório e `.gitignore` que exclui segredos, chaves de API e `.env*` (exceto `.env.example`), verificada com `git check-ignore`.
- OpenSpec inicializado para Claude Code e Codex (comandos `/opsx:*` e skills em `.claude/` e `.agents/`), schema `spec-driven`, contexto do projeto em português.
- Delta spec do domínio `deployment-operations`, cobrindo apenas o que a fundação efetivamente implementa: Compose com serviços isolados e healthchecks, rede interna, ambientes por variáveis separadas, segredos fora do Git, CI, branches protegidas e documentação. A arquitetura dos demais domínios permanece nos MDs principais, e cada domínio receberá sua delta spec na mudança que o implementar.
- Scaffolding técnico mínimo: estruturas vazias de `frontend/` (Next.js) e `backend/` (FastAPI) com endpoints `/health` reais — sem autenticação, CRUD ou regras de negócio da Markina Gallery.
- Design técnico da fundação: topologia Docker Compose (Nginx, Next.js, FastAPI, PostgreSQL, Redis, worker), ambientes local/homologação/produção, segredos fora do Git, CI, observabilidade mínima e documentação.
- `tasks.md` verificável cobrindo repositório, OpenSpec, scaffolding, Compose, variáveis de ambiente, CI e documentação.

## Capabilities

### New Capabilities

- `deployment-operations`: operação da fundação — Docker Compose com serviços isolados e healthchecks, rede interna, ambientes definidos por variáveis separadas, segredos fora do Git, CI, branches protegidas e documentação de desenvolvimento, deploy e rollback.

### Modified Capabilities

<!-- Nenhuma: esta é a primeira spec do projeto. -->

Os domínios `auth`, `client-access`, `gallery-sales`, `media-storage`, `messaging` e `privacy-biometric` descrevem funcionalidades futuras: a arquitetura completa deles permanece em `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md` e `ROADMAP_ARQUITETURA.md`, e cada um ganhará delta spec criada e sincronizada junto da mudança que o implementar — nunca antes.

## Impact

- Apenas arquivos novos; os documentos existentes (`INSTRUCOES_EXECUTOR_CLAUDE_CODE.md`, `ROADMAP_ARQUITETURA.md`) permanecem intactos.
- Nenhum código de negócio (autenticação, CRUD ou regras da Markina Gallery) e nenhum deploy nesta mudança; o único código é o scaffolding mínimo com `/health`.
- Ao concluir a mudança, apenas `deployment-operations` será sincronizada em `openspec/specs/`; nenhuma spec de funcionalidade futura será sincronizada ou arquivada.
