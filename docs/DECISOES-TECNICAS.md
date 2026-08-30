# Decisões técnicas e limitações conhecidas — Markina Gallery

Documento vivo; revisar a cada mudança. Fonte completa das decisões: `openspec/changes/<id>/design.md` de cada mudança.

## Decisões da fundação (`bootstrap-photocrm-foundation`)

1. **OpenSpec como processo obrigatório** (schema `spec-driven`), artefatos em português com cabeçalhos e SHALL/MUST em inglês. `openspec/specs/` reflete apenas comportamento implementado; cada domínio ganha delta spec junto da mudança que o implementa.
2. **Monorepo único**: `frontend/` (Next.js App Router + TS), `backend/` (FastAPI), `docker/`, `scripts/`, `docs/`, `.github/workflows/`, `openspec/`.
3. **Docker Compose com serviços isolados**: `nginx` (entrada única), `web`, `api`, `db` (PostgreSQL 17), `redis` (Redis 7), `worker`. Rede interna `markina-gallery_internal`; `db`/`redis` sem portas públicas; healthchecks em todos os serviços.
4. **Isolamento de máquinas compartilhadas**: projeto Compose exclusivo `markina-gallery`; volumes `markina-gallery_pgdata`/`markina-gallery_redisdata`; única porta publicada no host = Nginx em `${MARKINA_GALLERY_PORT:-8080}`. **Porta 3000 do host já é usada pelo projeto `firefly_telegram` desta máquina — a Markina Gallery não publica 3000/8000/5432/6379 no host.** Em conflito, muda-se a porta da Markina Gallery, nunca a do outro projeto. Proibidos prunes e `docker compose down` sem `-p markina-gallery -f docker/docker-compose.yml`.
5. **Ambientes separados**: `local`, `homolog`, `prod` com banco, segredos e integrações totalmente distintos (`.env.local`/`.env.homolog`/`.env.prod`).
6. **Segredos fora do Git**: `.env*` ignorado (exceto `.env.example`); gitleaks local e na CI; GitHub Secrets apenas na CI.
7. **CI no GitHub Actions**: lint, testes, build, validação OpenSpec (`--strict`) e gitleaks em pull requests.
8. **Observabilidade mínima**: healthchecks reais (`/health`, `/api/health`, `/healthz`) desde a fundação; logs estruturados e correlação job/request virão com as mudanças de cada domínio.
9. **Convenções de dados** (aplicadas nas próximas mudanças): UUIDs públicos, UTC no banco, valores monetários em centavos inteiros.
10. **Convenções de repositório**: Conventional Commits; `main` protegida por convenção, `develop`, `feature/*`.
11. **Marca oficial (2026-08-22)**: o produto passou a se chamar **Markina Gallery**, alinhado à marca existente **Markina Photographer**. Regras: (a) "Markina Gallery" é o nome público em títulos, documentação, interfaces e contexto OpenSpec; (b) `markina-gallery` é o nome do repositório GitHub, do projeto Docker Compose e o prefixo de containers, redes, volumes e serviços (ex.: `markina-gallery_internal`, `markina-gallery_pgdata`); (c) o change-id `bootstrap-photocrm-foundation` permanece como identificador de auditoria, sem renomeação; (d) domínio/subdomínio serão definidos antes do deploy no Oracle. Nome anterior: PhotoCRM.
12. **Plano GitHub gratuito (2026-08-23)**: o proprietário mantém o plano gratuito — projeto pessoal, sem intenção de venda. Proteção técnica de branches em repositórios privados exige GitHub Pro (API e regras retornam 403 no plano gratuito). Portanto `main` é protegida **por convenção**: PR com CI verde e revisão antes do merge, registrado na spec `deployment-operations`. Se um dia houver upgrade, ativar a regra com os 4 checks da CI (`backend`, `frontend`, `openspec`, `gitleaks`).

## Versões fixadas no scaffolding

- Next.js 16.3 + React 19.2 (lockfile `frontend/package-lock.json`)
- ESLint **9.x** (fixado: `eslint-config-next` 16 empacota plugin incompatível com ESLint 10)
- Vitest 4 (testes de rota), TypeScript 6
- FastAPI 0.141, Uvicorn 0.52, pytest 9, ruff 0.16 (Python 3.13 no container; 3.12 local)
- PostgreSQL 17-alpine, Redis 7-alpine, Nginx 1.27-alpine, Node 24-alpine

## Limitações conhecidas

- **Nenhuma funcionalidade de negócio**: sem autenticação, CRUD, migrations ou regras — por decisão de escopo; cada domínio entra por mudança OpenSpec própria.
- **Worker é placeholder** (loop de espera); a fila real (Redis + Celery/RQ) chega com a mudança do domínio correspondente.
- **HTTPS/TLS** é configurado no deploy (proxy reverso do servidor), não nesta fundação.
- **Backups cifrados no Drive** e scripts de restauração: pendentes da mudança `media-storage`.
- **Repositório GitHub privado, proteção de `main` e remote**: ação manual do proprietário (não bloqueia a fundação local).
- `pytest` emite warning de depreciação `httpx`/`httpx2` (dependência do Starlette); sem impacto funcional, acompanhar em mudança futura.
