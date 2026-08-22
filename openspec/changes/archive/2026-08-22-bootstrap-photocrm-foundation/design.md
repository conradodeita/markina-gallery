## Context

Ponto de partida: diretório com apenas os dois documentos do proprietário (`INSTRUCOES_EXECUTOR_CLAUDE_CODE.md` e `ROADMAP_ARQUITETURA.md`), sem repositório Git, sem código e sem specs. A fundação precisa estabelecer o processo OpenSpec, o repositório seguro, a topologia Docker Compose, a estratégia de ambientes e segredos, a CI e a documentação antes de qualquer funcionalidade. A fonte de verdade (`openspec/specs/`) SHALL conter apenas comportamento implementado; nesta mudança, somente `deployment-operations` é sincronizada. Ver proposal.md para a motivação.

## Goals / Non-Goals

**Goals:**

- Fundação reproduzível: ambiente local sobe com `docker compose up` e healthchecks verdes.
- Segurança de segredos verificável desde o primeiro commit.
- Scaffolding técnico mínimo (estruturas vazias e endpoints `/health`) para validar o Compose de ponta a ponta.
- Fluxo OpenSpec operando para Claude Code (comandos `/opsx:*`) e Codex (skills).

**Non-Goals:**

- Nenhum código de negócio: sem autenticação, sem CRUD, sem regras da Markina Gallery e sem migration de banco; nenhum deploy.
- Nenhuma funcionalidade de produto — cada uma virá em mudança própria, com delta spec criada junto da implementação.
- Nenhuma spec antecipada de domínio em `openspec/specs/` — a fonte de verdade reflete apenas comportamento implementado.
- Criação do repositório GitHub remoto (depende do proprietário fornecer o repositório privado).

## Decisions

### Decisão: OpenSpec como processo obrigatório, com schema spec-driven
Cada mudança nasce em `openspec/changes/<change-id>/` com proposal, delta specs, design e tasks; após teste e deploy, é sincronizada em `openspec/specs/` e arquivada. Artefatos em português, com cabeçalhos estruturais e SHALL/MUST em inglês (regra fixada em `openspec/config.yaml`).
- **Alternativa**: desenvolver sem specs formais — rejeitada pela INSTRUCOES §1.1 e pelo roadmap (Fase 0).

### Decisão: Specs refletem apenas comportamento implementado
`openspec/specs/` SHALL conter somente o que está implementado. A fundação sincroniza apenas `deployment-operations`; `auth`, `client-access`, `gallery-sales`, `media-storage`, `messaging` e `privacy-biometric` terão delta specs criadas e sincronizadas nas mudanças que as implementarem. A arquitetura completa desses domínios permanece nos MDs principais.
- **Alternativa**: criar specs antecipadas por domínio — rejeitada pelo proprietário: specs de funcionalidades futuras poluiriam a fonte de verdade.

### Decisão: Monorepo único
`frontend/` (Next.js), `backend/` (FastAPI), `docker/`, `scripts/`, `docs/`, `.github/workflows/` e `openspec/` na raiz.
- **Alternativa**: dois repositórios separados — rejeitada por simplicidade operacional de um único fotógrafo self-hosted.

### Decisão: Docker Compose com serviços isolados
Serviços: `nginx` (entrada HTTPS única), `web` (Next.js), `api` (FastAPI), `db` (PostgreSQL), `redis` e `worker`. Rede interna dedicada; `db` e `redis` sem portas públicas; volumes nomeados; healthchecks em todos os serviços. Jobs (importação, miniaturas, Drive, mensagens) nunca dependem do ciclo HTTP.
- **Alternativa**: Kubernetes — descartada para o MVP por complexidade desproporcional.

### Decisão: Ambientes separados e segredos fora do Git
Ambientes `local`, `homolog` e `prod` com domínio, banco, segredos, WhatsApp e integrações totalmente distintos. Segredos apenas em `.env.<ambiente>` não versionado ou secret store do servidor; `.env.example` documenta as variáveis sem valores; varredura de segredos (gitleaks) no fluxo local e na CI.
- **Alternativa**: variáveis versionadas com placeholders — descartada por risco de vazamento.

### Decisão: CI no GitHub Actions
Workflow de pull request com lint, testes, build e validação OpenSpec (`--strict`); segredos apenas no GitHub Secrets. `main` protegida, `develop` e `feature/*`; commits em Conventional Commits.
- **Alternativa**: CI self-hosted — adiável; GitHub Actions atende sem infraestrutura extra.

### Decisão: Observabilidade mínima desde o início
Logs estruturados (JSON), healthchecks em todos os serviços e correlação job/request.
- **Alternativa**: APM completo — postergado para depois do MVP.

### Decisão: Backups e capacidade
Backup diário cifrado do PostgreSQL no Google Drive com restauração testada em homologação; reserva de 25% do disco local; alerta e bloqueio de importações em 75% de ocupação configurável.
- **Alternativa**: backups apenas locais — descartada; o roadmap exige cópia externa cifrada.

### Decisão: Convenções de dados
UUIDs públicos, UTC no banco e valores monetários em centavos inteiros — estabelecidas nas specs e aplicadas nas próximas mudanças.
- **Alternativa**: IDs sequenciais e valores decimais — descartada por exposição de IDs e erros de arredondamento.

## Risks / Trade-offs

- [Repositório GitHub privado ainda não fornecido] → Mitigação: fundação completa local; criação do remote e proteção de branches fica como ação manual do proprietário e não bloqueia a conclusão da fundação.
- [CI sem runners e secrets configurados] → Mitigação: workflow pronto; ativação exige configuração de secrets no GitHub.
- [Servidor Oracle e domínio não fornecidos] → Mitigação: homologação e produção documentadas, mas não provisionadas nesta mudança.
- [Requisitos escritos em português com SHALL/MUST em inglês] → Mitigação: regra fixada em `openspec/config.yaml`, exigida pelo validador OpenSpec.
- [`.gitignore` amplo demais para casos específicos] → Mitigação: revisão por mudança; `.env.example` é a única exceção de negação.
- [Scaffolding mínimo ainda é código] → Mitigação: restrito a estruturas vazias e endpoints `/health`; nenhuma rota de negócio, verificado por revisão de diff.

## Migration Plan

Não aplicável: apenas arquivos novos, sem comportamento existente para migrar. Rollback = remover os arquivos criados ou reverter o commit da mudança; nenhum dado em risco.
