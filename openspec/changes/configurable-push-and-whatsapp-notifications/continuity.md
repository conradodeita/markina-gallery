# Continuidade da implementação

## Reconciliação — 14/09/2026

- Change solicitada explicitamente: `configurable-push-and-whatsapp-notifications`. Branch isolada `codex/configurable-push-and-whatsapp-notifications`; baseline de código `5d7de64`. Nenhuma alteração remota ou de secrets nesta etapa.
- `persist-branding-assets-across-deploys` permanece independente e pendente. Não absorver seus arquivos neste commit. Backend, migrations, central e testes sintéticos de push são independentes; aceite de instalação com arte oficial e deploy dependem da persistência e do reenvio humano dos ativos ausentes. Não certificar instalação oficial com fallback ou ícone sintético.
- `GalleryMembershipNotificationOutbox` permanece como histórico técnico. O disparo externo `private_created` não representa primeira seleção: criação manual não notifica na nova matriz. OTPs posteriores continuam auditados; primeiro acesso externo usa cliente + `parent_gallery_id` canônico, não `challenge.id`.
- `PaymentMessageTemplate` contém os textos que serão preservados. A API legada deverá delegar à configuração central, sem manter dois editores/fontes. `PaymentNotificationOutbox` e `WhatsAppDelivery` históricos ficam preservados; os produtores novos não poderão alimentar simultaneamente a fila antiga e a nova para o mesmo evento. Correções financeiras continuam silenciosas.
- A spec consolidada antiga de pastas/liberação e propriedade exclusiva foi ampliada pelas changes de prévias automáticas e membros compartilhados já implementadas. Esta change não restaura liberação manual nem propriedade exclusiva. Lote de anúncio é identidade nova explícita, não pasta nem job facial; destinatários são membros ativos autorizados.
- Service worker existente `/markina-sw.js` mantém navegação offline sem CacheStorage. Adicionar handlers no mesmo worker, sem outro scope e sem cache privado.

## Sequência e gates

1. Persistência aditiva e baseline silencioso → configuração/snapshots → produtores → inscrições/transporte → central e controles → integração focada.
2. Validar individualmente antes de marcar cada tarefa; nunca executar suíte completa local nesta rodada.
3. Deploy/segredos/ativação e dispositivos reais (5.3/5.4) exigem participação humana e inventário atualizado. Nenhum destes gates bloqueia trabalho local independente. Preservação de branding exige sua change própria antes do aceite real.

## Evidência inicial

Leitura de proposal/design/deltas/tasks, mandato, roadmap, diretrizes, auth e acesso, specs legadas de mensagens e implementação dos produtores/worker. Conflitos e substituições estão explícitos acima e na proposal/design. Nenhum comportamento de negócio financeiro alterado nesta reconciliação.

## Implementação local

- Migration `20260914_0056` aditiva: sete tabelas novas, sem envios históricos; templates confirmados/recusados copiados sem alterar tabela/outboxes legadas. Baseline por cliente/origem para vínculos antigos. Rollback operacional preserva dados; downgrade só permitido em schema novo vazio de teste.
- Configuração central e APIs legadas usam `NotificationSetting` como única fonte. Histórico `PaymentMessageTemplate` preservado; consumidores sem snapshot leem configuração central. Snapshots existentes não são alterados.
- Testes em SQLite temporário exclusivo: migration + configuração = 8 passed (76,71 s); rodada anterior incluindo templates existentes = 10 passed. Ruff passou nos arquivos modificados. Sem suíte completa local e sem acesso remoto.
- Ajuste adicional de transação SQLite validado: iniciar BEGIN antes de SAVEPOINT quando o driver legado ainda não abriu transação. Evita outbox persistida por RELEASE antes do commit do negócio. Teste de rollback aprovado.

- 2.1: primeiro acesso implementado nas entradas OTP/contextual e rotas de galeria. 2 testes OTP direcionados passaram; dois OTPs auditados, um evento externo. Testes novos de acesso/configuração 11 passed; nenhum envio em acesso negado/baseline.
- 2.2: primeira seleção privada/publicamente derivada usa marco independente. Concorrência revelou conflito preexistente na inserção privada sob SQLite; aplicado savepoint com verificação da constraint, preservando lock comercial PostgreSQL. 4 testes de eventos e 1 rota pública existente passaram. Pesquisa/favorito não enfileiram seleção.
- 2.3/2.4: lotes explícitos com fechamento/retomada, fingerprint SHA-256 de arquivos privados e snapshot de destinatários no fechamento. Frontend 10 passed e typecheck exit 0; backend lote 4 passed, cobrindo lote aberto, jobs pendentes, falha parcial/total, membro posterior/bloqueado e ausência de repetição.
- 2.5/3.3 concluídas e validadas localmente: projeção financeira acompanha o consumidor e cancelamento; retentativa administrativa delega com TTL, limites e revalidação. Outboxes anteriores sem evento continuam no fluxo legado. O teste antigo de duas galerias simulava aceite alterando só a outbox antiga; atualizado para simular a entrega na fila nova e injetar o provedor nela, sem enfraquecer as assertivas financeiras (1 passed/71 deselected).
- 3.1/3.2 concluídas e validadas localmente: inscrição Fernet com contexto de identidade/geração, cookie opaco HttpOnly de instalação, dez dispositivos/conta, sessão como autoridade, CSRF e rate limit. Logout/troca de conta revogam; expiração natural não. Par VAPID validado antes de oferecer ativação. Adaptador cifra via pywebpush; DNS público e conexão fixada, sem redirects ou multicast. Nenhuma chave real configurada.

## Checkpoint local final — 14/09/2026

- 16/18 tarefas concluídas; restam exclusivamente operação autorizada e dispositivos reais (5.3/5.4). Não executar sync/archive antes de revisão humana.
- Backend integrado restrito aos oito arquivos da change: **49 passed** em 53,01 s, SQLite temporário exclusivo. Além disso: **4 passed/50 deselected** nos consumidores financeiros antigos e **1 passed/71 deselected** no cenário comercial entre duas galerias. Rodadas OTP e derivação anteriores estão registradas acima. Nunca executada suíte completa local.
- Frontend, nove arquivos selecionados: **56 passed** em 26,89 s. `tsc --noEmit` e build Next.js aprovados, inclusive depois dos controles no acesso público e do cabeçalho responsivo. ESLint focado sem erros; aviso preexistente `no-img-element` no upload de branding em Configurações. Ruff aprovado nos módulos/testes tocados.
- Visual sintético local: `frontend/scripts/notification-visual-qa.cjs`, Edge headless, 390/768/1440 px claro/escuro, seis eventos, toggles por teclado, salvamento, permissão negada e controle no shell cliente. 12 capturas + `results.json` em `.codex-tmp/notification-qa`, fora do Git; sem overflow. Capturas revisadas, cabeçalho ajustado em tablet e teste repetido. Não é evidência de entrega real.
- Compose `config --quiet`, OpenSpec `validate --strict` e `git diff --check` aprovados. Docs em `docs/transactional-notifications.md`, roadmap e mandato reconciliados. Não modificados arquivos reais de ambiente, chaves, dados de homologação ou recursos externos.
- Branch continua `codex/configurable-push-and-whatsapp-notifications`, sem commit/push/merge/deploy desta change. Preservar `.codex-tmp/` e a change independente de branding; não adicionar artefatos locais ao Git.

## Próximo passo humano obrigatório

### PR e reconciliação de CI — 14/09/2026

- PR #84 aberto contra `develop`: https://github.com/conradodeita/markina-gallery/pull/84 . Commit inicial publicado `2e840d6`; o commit anterior de documentação de rebrand foi excluído desta branch antes do primeiro push, sem force push e sem alterar sua branch original.
- Primeiro CI `34888333629`: frontend/OpenSpec/gitleaks aprovados; backend 597 passed, 3 skipped, 7 failed. Não ignorar checks obrigatórios nem confundir essa suíte remota do CI com execução local completa.
- Correção: painel financeiro lê templates centrais + fallback legado em **uma consulta**, sem inicialização de configurações no GET. Mantida a asserção de orçamento de consultas, sem relaxar seu limite.
- Testes legados de retry atualizados para refletir falha também em `NotificationDelivery`, pois outbox financeira é somente projeção; teste de falha externa de membros usa `member_joined`, já que `private_created` deixou de enviar externamente pela decisão aprovada.
- Ciclos de downgrade legados agora têm limite superior explícito 0055. A proteção de 0056 não foi removida: teste próprio verifica upgrade, baseline e recusa de downgrade preenchido preservando inscrição/marcos.
- Evidências cirúrgicas: sete casos que falharam no CI = **7 passed/90 deselected**; configuração + migration de notificações = **9 passed**; Ruff e diff check aprovados. Sem alteração de homologação; merge aguarda CI verde e plano da dependência de branding confirmado.

Atualização operacional 14/09/2026: proprietário autorizou push, merge e deploy após o job. Inventário somente leitura: servidor em `23bdee9bb7b3c1f946693f08c48741dee28188f1`, checkout limpo, serviços próprios saudáveis, nginx próprio em `127.0.0.1:8080`, domínio `markina-homolog.duckdns.org`. Outros projetos e proxy compartilhado intocados. Plano de preservação de branding + publicação com transportes novos desligados apresentado para confirmação pós-inventário; PR pode avançar independentemente. Autorização não inclui criação/alteração de chaves nem envio real neste momento.

1. Autorizar publicação/etapa operacional e a sequência com a dependência `persist-branding-assets-across-deploys`. Antes de qualquer deploy/configuração remota, atualizar inventário, porta/subdomínio e apresentar plano de impacto zero para confirmação; não usar inventário antigo como evidência atual.
2. Configurar chaves VAPID e Fernet externas por procedimento seguro aprovado. Não solicitar segredos em conversa. Transportes novos permanecem `false` por padrão no Compose; WhatsApp dos pagamentos conserva fluxo já existente.
3. Testar com dispositivos Android/iPhone e contas autorizadas. Ativos de branding ausentes dependem de sua change e reenvio humano. Essas dependências bloqueiam somente 5.3/5.4; toda implementação/validação local independente foi concluída.
