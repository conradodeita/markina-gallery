## 1. Repositório e segurança de segredos

- [x] 1.1 Confirmar Git inicializado com branch `main` e documentos do proprietário intactos — verificar com `git status` mostrando os documentos e nenhuma alteração neles
- [x] 1.2 Manter `.gitignore` cobrindo `.env`, `.env.*` (exceto `.env.example`), chaves, artefatos de build e volumes locais — verificar com `git check-ignore -v .env .env.local .env.homolog .env.prod` e confirmando que `.env.example` não é ignorado
- [x] 1.3 Configurar identidade Git (`user.name`/`user.email`) no repositório — verificar com `git config user.name` e `git config user.email` retornando valores
- [x] 1.4 Adicionar varredura de segredos (gitleaks) como ferramenta local e na CI — verificar executando a varredura e obtendo zero achados
- [x] 1.5 Documentar convenção de commits (Conventional Commits) e modelo de branches (`main` protegida, `develop`, `feature/*`) — verificar lendo a seção correspondente no README

## 2. OpenSpec

- [x] 2.1 OpenSpec inicializado para Claude Code e Codex, com comandos `/opsx:*` e skills em `.claude/` e `.agents/` — verificar com `openspec doctor` sem problemas e listando os comandos de `.claude/commands/opsx/`
- [x] 2.2 Contexto do projeto (`openspec/config.yaml`) preenchido com stack, convenções e restrições do PhotoCRM em português — verificar com `openspec context --json` exibindo o contexto
- [x] 2.3 Mudança validada sem erros — verificar com `openspec validate bootstrap-photocrm-foundation --strict`
- [x] 2.4 Revisão humana da proposta, das specs e das tarefas (gate obrigatório antes de aplicar) — verificar com aprovação explícita do proprietário

## 3. Estrutura inicial e scaffolding mínimo

- [x] 3.1 Criar diretórios `frontend/`, `backend/`, `docker/`, `scripts/`, `docs/` e `.github/workflows/`, cada um com README curto descrevendo sua responsabilidade — verificar listando a árvore de diretórios
- [x] 3.2 Criar scaffolding técnico mínimo: estruturas vazias de `frontend/` (Next.js) e `backend/` (FastAPI) com endpoints `/health` reais — sem autenticação, CRUD, regras de negócio ou funcionalidades do PhotoCRM — verificar que `/health` responde 200 e que nenhuma rota de negócio existe
- [x] 3.3 Garantir que nenhum código de negócio foi escrito nesta mudança — verificar revisando o diff completo do commit

## 4. Docker Compose (ambiente local)

- [x] 4.1 Criar `docker/docker-compose.yml` com serviços `nginx`, `web` (Next.js), `api` (FastAPI), `db` (PostgreSQL), `redis` e `worker` — verificar com `docker compose config` validando o arquivo sem erros
- [x] 4.2 Configurar rede interna dedicada, com `db` e `redis` sem portas expostas publicamente — verificar inspecionando as portas publicadas do Compose
- [x] 4.3 Criar volumes nomeados para PostgreSQL, Redis e ativos locais — verificar com `docker volume ls` após subir o ambiente
- [x] 4.4 Adicionar healthchecks em todos os serviços, usando os endpoints `/health` do scaffolding para `web` e `api` — verificar com `docker compose ps` exibindo todos os serviços saudáveis
- [x] 4.5 Subir o ambiente local — verificar com `docker compose up -d` e healthchecks verdes em todos os containers

## 5. Variáveis de ambiente e segredos

- [x] 5.1 Criar `.env.example` documentando todas as variáveis necessárias, sem valores reais — verificar lendo o arquivo e confirmando ausência de segredos
- [x] 5.2 Documentar a estratégia por ambiente (`.env.local`, `.env.homolog`, `.env.prod`), sempre ignorados pelo Git — verificar com `git check-ignore` em cada nome de arquivo
- [x] 5.3 Confirmar que nenhum segredo aparece em código, frontend, logs ou tabelas comuns — verificar com varredura de segredos e revisão do diff

## 6. CI no GitHub

- [x] 6.1 Criar workflow de pull request com lint, testes e build — verificar executando os mesmos comandos localmente (lint/testes/build verdes); primeira execução real na CI ocorre após 6.4 (repositório GitHub)
- [x] 6.2 Criar workflow de validação OpenSpec (`openspec validate --strict --all`) na CI — verificar com o mesmo comando executado localmente (`Totals: 1 passed, 0 failed`)
- [x] 6.3 Documentar uso exclusivo do GitHub Secrets para segredos de CI — verificar lendo a seção correspondente no DEPLOY.md
- [x] 6.4 Ação manual do proprietário (externa; não bloqueia a conclusão da fundação local): criar o repositório privado no GitHub, aplicar proteção de `main` e definir `develop` — verificar as configurações na interface do GitHub quando o repositório for fornecido

## 7. Documentação

- [x] 7.1 Criar `README.md` de desenvolvimento (pré-requisitos, setup local, fluxo OpenSpec) — verificar executando os comandos documentados em máquina limpa
- [x] 7.2 Criar `DEPLOY.md` com homologação e produção separados (domínio, banco, chaves, WhatsApp e dados distintos) — verificar revisando os passos por ambiente
- [x] 7.3 Criar `docs/DECISOES-TECNICAS.md` com decisões técnicas e limitações conhecidas — verificar revisando o documento completo
- [x] 7.4 Criar `docs/CHECKLIST-DEPLOY-ROLLBACK.md` com checklist de deploy e rollback — verificar revisando o documento completo

## 8. Validação final e fechamento

- [x] 8.1 Validar a mudança e todas as specs — verificar com `openspec validate bootstrap-photocrm-foundation --strict` sem erros
- [x] 8.2 Confirmar ausência total de segredos no repositório — verificar com varredura de segredos no histórico completo do Git
- [x] 8.3 Criar commit inicial `chore: bootstrap photocrm foundation` imediatamente antes de sincronizar/arquivar a mudança, após revisar `git status`, `git diff` e a varredura de segredos — verificar com `git show --stat` revisando cada arquivo do commit e confirmando que nenhuma chave, `.env` ou dado sensível foi incluído
- [x] 8.4 Após o commit e o aceite do proprietário, sincronizar apenas a spec `deployment-operations` em `openspec/specs/` e arquivar a mudança — verificar com `openspec list` mostrando a mudança arquivada e `openspec list --specs` mostrando somente `deployment-operations`; os demais domínios ganham specs apenas nas mudanças que os implementarem
