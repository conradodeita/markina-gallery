# Markina Gallery

Plataforma self-hosted de gestão, prova, venda e acompanhamento de fotografias escolares e de eventos. Experiência mobile-first para responsáveis, painel administrativo rápido para um único fotógrafo, galerias privadas importadas do DigiKam e eventos coletivos com liberação individual de resultados.

> **Status: fundação (scaffolding).** Nenhuma funcionalidade de negócio, autenticação, CRUD ou regra da Markina Gallery foi implementada ainda — apenas estrutura, Compose, CI, health checks e documentação.

## Documentos do proprietário

- `INSTRUCOES_EXECUTOR_CLAUDE_CODE.md` — especificação operacional (fonte operacional)
- `ROADMAP_ARQUITETURA.md` — decisões arquiteturais (segurança e privacidade obrigatórias)

## Stack

Next.js (App Router, TypeScript) · FastAPI (Python) · PostgreSQL 17 · Redis 7 · Nginx · Docker Compose · OpenSpec (processo de desenvolvimento).

## Estrutura

| Diretório | Responsabilidade |
|---|---|
| `frontend/` | Portal Next.js (scaffolding: `/api/health` + página placeholder) |
| `backend/` | API FastAPI + worker (scaffolding: `/health` + worker placeholder) |
| `docker/` | `docker-compose.yml` (projeto `markina-gallery`) e configuração do Nginx |
| `scripts/` | Scripts operacionais (backup/restauração virão com a mudança de mídia) |
| `docs/` | Decisões técnicas e checklists |
| `.github/workflows/` | CI (lint, testes, build, OpenSpec, gitleaks) |
| `openspec/` | Processo OpenSpec (specs consolidadas e mudanças) |

## Pré-requisitos

Docker com Compose v2, Node 24+, Python 3.12+ (para desenvolvimento fora de container) e Git.

## Ambiente local (Docker)

```bash
cp .env.example docker/.env   # ajuste valores locais; docker/.env nunca é versionado
docker compose -p markina-gallery -f docker/docker-compose.yml up -d --build
curl http://localhost:8080/healthz        # Nginx
curl http://localhost:8080/api/health     # FastAPI via Nginx
curl http://localhost:8080/               # Next.js
```

Única porta publicada no host: Nginx em `${MARKINA_GALLERY_PORT:-8080}`. `db` e `redis` nunca publicam portas; os volumes de banco, Redis e mídia são exclusivos do projeto; rede `markina-gallery_internal`. Veja também [prévia protegida de mídia](docs/MIDIA-PREVIAS-PROTEGIDAS.md).

Verificar saúde: `docker compose -p markina-gallery -f docker/docker-compose.yml ps`
Parar somente a Markina Gallery: `docker compose -p markina-gallery -f docker/docker-compose.yml down`

> ⚠️ **Máquinas/servidores compartilhados:** outros projetos Docker podem estar em execução. Nunca rode
> `docker compose down` sem `-p markina-gallery -f docker/docker-compose.yml`, nunca rode prunes, e nunca altere
> containers, imagens, redes, volumes, proxy, firewall, DNS ou certificados de outros projetos.
> Se a porta local estiver ocupada, mude `MARKINA_GALLERY_PORT` no `docker/.env` — sem tocar no outro projeto.

## Desenvolvimento fora de container

- Frontend: `cd frontend && npm install && npm run dev`
- Backend (Windows): `cd backend && python -m venv .venv && .venv/Scripts/pip install -r requirements.txt && .venv/Scripts/python -m uvicorn app.main:app --port 8000` (no Linux: `.venv/bin/...`)
- Lint/testes/build: ver os READMEs de `frontend/` e `backend/` (mesmos comandos que a CI executa)

## Processo OpenSpec (obrigatório)

Fluxo por mudança: `/opsx:propose <change-id>` → revisão humana → `/opsx:apply` → testes e validação → `/opsx:sync` → `/opsx:archive`.

- `openspec/specs/` reflete **apenas comportamento implementado**; cada domínio ganha delta spec junto da mudança que o implementa.
- Artefatos em português, com cabeçalhos estruturais e SHALL/MUST em inglês (regra em `openspec/config.yaml`).
- Nunca escrever código de funcionalidade antes de a proposta/spec ser revisada e aceita pelo proprietário.

## Convenções de commits e branches

- **Conventional Commits**: `feat:`, `fix:`, `chore:`, `docs:`, `refactor:`, `test:` — mensagens objetivas.
- **Branches**: `main` protegida **por convenção** — alterações somente via pull request com CI verde e revisão (o plano gratuito do GitHub não oferece enforcement técnico em repositórios privados); `develop` como integração; `feature/*` para funcionalidades.
- Nunca commitar segredos, chaves, `.env*` (exceto `.env.example`) ou artefatos de build.

## Segredos

Somente em `.env` não versionado ou na secret store do servidor; na CI, somente GitHub Secrets. `.env.example` documenta as variáveis sem valores reais.

Varredura local com gitleaks (instalado fora do repositório):

```bash
gitleaks git --staged -v   # antes do commit (somente o que será commitado)
gitleaks git -v            # histórico completo
```

O scan de diretório (`gitleaks detect --no-git`) gera falsos positivos em `frontend/.next/` — use sempre o scan Git, que respeita o `.gitignore`. A CI usa o gitleaks-action com o histórico completo.

## Deploy

Ver `DEPLOY.md` (homologação e produção) e `docs/CHECKLIST-DEPLOY-ROLLBACK.md`.
