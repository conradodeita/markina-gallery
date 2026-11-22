# Continuidade do fluxo de subdomínio — 05/11/2026

## Estado mais recente — retomada concluída localmente

O proprietário pediu retomar e a pausa foi encerrada. A change está em **6/6 tarefas concluídas localmente**: API GET/PUT de reserva, nomes protegidos, idempotência/auditoria, corridas PostgreSQL e interface desktop/mobile implementados e validados. Ver validation.md e activation-gates.md para evidências e limites. Não houve sync/arquivo/deploy, DNS curinga, TLS/proxy por tenant nem promoção pública de hostname.

API local8000 e frontend3039 ficaram ativos com banco sintético novo pyp-subdomain-ui-20261105 em loopback15472; a aba Chrome autenticada mostra a reserva marca-do-estudio.pickyourpic.com.br em preparação. Banco de testes15470 também permanece disponível. Não apagar/reiniciar recursos preexistentes. Prova de UI terminou; nenhum teste/build ficou pendente.

DNSSEC Cloudflare permanece pendente na change de DNS: reavaliar após o gate de caches registrado (06/11/2026 16:45 BRT) e conferir estado atual antes de agir. Autorização já existe para a transição/reassinatura, não para wildcard/proxy/deploy. Próxima evolução do hostname exige especificar e validar operação de ativação conforme activation-gates.md. Revisão humana precede sync/arquivo.

## Checkpoint histórico da pausa original

O proprietário pediu pausar por limite de tokens. O checkpoint abaixo descreve o estado anterior à retomada; não representa pendências atuais quando substituído pelo estado mais recente acima.

## Worktree e proteções

- Usar exclusivamente `C:/codex-data/worktrees/saas-release-candidate/Photo Delivery`, branch feature/saas-release-candidate. Há amplo diff SaaS anterior; não resetar, limpar, descartar, trocar checkout nem fazer commit indiscriminado.
- Ler AGENTS, mandato, roadmap, política de refatoração, proposal/design/spec/tasks desta change e validation.md antes de continuar.
- Sem autorização de deploy/migration remota, alterações de secrets/.env, wildcard, proxy, WAF/cache ou interrupção de produção. Nenhum serviço produtivo pode ser desligado sem consentimento específico. Autorização DNS existente é estreita e está na change de migração.

## Fluxo de subdomínio — estado exato

- Decisão expressa mais recente: **nome.pickyourpic.com.br será escolhido no primeiro acesso após verificar e-mail**, e não durante o cadastro leve inicial. Conta continua autoativada; WhatsApp continua obrigatório para uploads.
- Change add-photographer-subdomain-onboarding está em 2/6 tasks. Proposal/design/delta/tasks existem e passaram strict antes do código. Nenhuma sincronização/arquivo.
- Implementação feita: nova coluna nullable Tenant.canonical_host_status (`reserved`/`ready`, NULL legado); check preserva consistência; migration aditiva 0105 depois de 0104, downgrade recusa estado persistido. tenant_hosts.py recusa host reserved e geração de URLs públicas. A unicidade continua no mesmo canonical_host existente, sem segundo catálogo.
- Arquivos novos: backend/migrations/versions/20261105_0105_tenant_host_reservation.py, backend/tests/test_tenant_host_reservation.py e test_tenant_host_reservation_migration.py. Alterações focadas dentro de auth.py (que já tinha diff preexistente) e tenant_hosts.py.
- Evidência: 5 testes SQLite passaram; 6 PostgreSQL passaram incluindo migration/rollback, namespace único entre legado/reserva, pending/ready e desconhecido. Nenhum skip nessa execução PostgreSQL. Não rodaram lint/build/typecheck/regressões amplas depois destas mudanças.
- Não existem ainda serviço/API de reserva, validação de prefixos, auditoria de escolha, UI ou concorrência. Retomar task 2.1 e validar antes de avançar à 3.1. A resposta anterior ao usuário explicou reserva versus prontidão e isso está especificado.

## Próxima implementação especificada

1. Serviço pequeno para normalizar/validar prefixo e lista reservada do design; base fixa pickyourpic.com.br. Reutilizar Tenant.canonical_host e row lock/constraint única, sem sobrescrever host escolhido, idempotência para repetição igual e conflito neutro para outro tenant.
2. GET/PUT autenticados sob onboarding, reutilizando _context/database em photographer_onboarding.py: sessão admin + email verificado + Signup ativo + membership/tenant ativo. PUT deve exigir mesma origem como as mutações existentes. Não aceitar tenant_id, status ready ou hostname inteiro do browser. Audit helper tem assinatura audit(db,event,subject,*,tenant_id=...).
3. Testar sessão ausente/cliente, tenant suspenso, dono/legado, extras, inválidos/reservados, colisão e corrida com PostgreSQL. Fixture proof de backend/tests/test_photographer_signup.py já monta signup/onboarding routers e substitui SessionLocal; helpers start/verify/finish criam contas sintéticas sem TOTP obrigatório.
4. Aviso no painel após verificação leva à etapa de escolha em Configurações. Formulário com prévia, reserva/check e preparação pendente sem link clicável; sem aparecer para proprietário/legados. Reusar os padrões de OnboardingPanel, não alterar os gates financeiros/WhatsApp. Sem endpoint self-service de ativação/renomeação nesta entrega.
5. Ler guias Next locais .md (não .mdx) em frontend/node_modules/next/dist/docs. Guias link.md e use-client.md já foram consultados. Executar testes frontend pertinentes, lint, typecheck, build e validação visual local; registrar limites de infraestrutura.

## Banco local e ferramentas

- Docker observado desktop-linux, três containers locais Evolution preexistentes preservados. Novo container de teste desta sessão: pyp-subdomain-test-20261105; postgres:17.11-alpine local, loopback15470, database pyp_photographer_test, tmpfs. Usuário/senha são fixtures sintéticas do comando desta sessão; nunca usar produção. Para recuperar o comando sem credenciais operacionais, consultar histórico desta sessão; não imprimir Config.Env de containers reais. Fixture postgres_schema exige URL exata no host/porta/database permitidos e cria/remove somente schemas sintéticos exclusivos.
- Python correto: backend/.venv/Scripts/python.exe, com workdir backend. A primeira tentativa .venv na raiz falhou e foi corrigida. Frontend npm/vitest no diretório frontend.
- ai-memory MCP de consulta/handoff não foi exposto nesta sessão; não inventar chamada bem-sucedida nem gravar memória por outro canal. Continuidade está no repositório. Jev disponível e usado; sessão 91984bd5-6f79-4fa6-8307-b1e7ad4ff4c6. A API usa workspaceRoot/query (camelCase); consulta inicial com workspace_root foi rejeitada antes da busca. Evidência histórica não substitui código atual.

## DNS/Cloudflare — pendência operacional independente

- Troca Registro.br autorizada expressamente e aceita em 05/11 às 16:45 BRT: kara.ns.cloudflare.com + mustafa.ns.cloudflare.com, A raiz e markina 132.145.193.169, DNS-only, TTL3600. Nenhuma nova confirmação da mesma troca é necessária.
- Checkpoint desta retomada às19:08 BRT: 1.1.1.1 e8.8.8.8 já retornam os NS Cloudflare, A preservado; markina HTTPS200. Google DS NOERROR sem DS; ADfalse esperado durante transição sem cadeia.
- **DNSSEC Cloudflare ainda não ativado/publicado.** Não antecipar DS novo incompatível com caches antigos. Plano registra recomendação conservadora de24h de transição do provedor; reavaliar a partir de **06/11/2026 16:45 BRT**, verificando DNS/TTL/cadeia reais. Autorização para reativar após propagação já existe; não manter pendência esquecida nem declarar migração completa.
- Change migrate-pickyourpic-dns-to-cloudflare contém plano/estado/autorização/evidências. Continuam pendentes validação integrada final e DNSSEC; não publicar wildcard por causa desta change de subdomínio.
- CUA foi encerrado com completion_summary após a leitura desta retomada. Em nova sessão, inicializar cua e obter tabs novamente; não assumir bindings cfTab/registroTab existentes. Chrome último browser3, Cloudflare tab1714872499; Registro tab1714872506 pode exigir login. Sessão deve ser renovada pelo usuário sem mandar senha/código no chat.
