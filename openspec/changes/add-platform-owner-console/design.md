# Design: Painel do proprietário da plataforma

## Estado

Implementação e incrementos locais em 06/11/2026, sem publicação. Carteira/compra já possuem autoridade comercial explícita pelo `PlatformOwner` persistido, independente dos grants técnicos. Inventários em `access-inventory.md` e `operational-sources.md`; decisões de onboarding e suspensão reconciliadas abaixo. Resultados e limites na validação da change.

## Incremento independente de leitura

- O shell `/admin/platform` e suas rotas de leitura usam a propriedade persistida já aprovada, sessão administrativa vigente, e-mail verificado e vínculo/tenant do ator ativos. Não criam grant, transferência ou schema novo. `MonitorGrant` e `InstallationOperator` permanecem exclusivamente técnicos.
- A autorização é revalidada após consultar e antes de entregar dados. Falhas e negativas são privadas/não cacheáveis. Não há cache de dados globais no cliente e perda de autorização limpa o estado exibido.
- Diretório server-side paginado (máximo 20) inicia vazio; seleção explícita de Todos/alfabética/recentes ou pesquisa por e-mail. Não depende de carteira existente, inclui suspensos e contas sem administrador; múltiplos vínculos não autorizam escolher uma identidade arbitrária. Nome não é inferido.
- Com 0097 da prova de cadastro, o diretório também pesquisa/exibe o nome fornecido pelo fotógrafo. Legado continua sem nome; nenhum backfill ou inferência por e-mail/cliente foi feito.
- Detalhe por UUID consultado pelo proprietário contém somente status/host, contagens de galerias/fotos e proveniência. Não retorna acervo, clientes, senhas, TOTP, chaves, caminhos físicos ou pedidos. A carteira continua na interface existente de créditos.
- O console lê, sem tráfego externo, o registro owner-only `GoogleDriveConnection` e a última observação de quota já persistida pelo fluxo OAuth. `connected` significa que há autorização registrada, não que o Google Drive esteja atualmente acessível ou saudável; quota só aparece junto de seu timestamp. Backup, arquivo e restauração seguem desconhecidos até possuírem fontes/adapters validados. Não reutilizar snapshot de 02/11 como dado atual. Fontes técnicas existentes mantêm suas rotas/grants.
- Tasks 2.2/2.3 podem avançar nesse incremento sem implementar as mutações das tasks 2.4/2.5, o novo log 3.1 ou o schema 2.1. A consulta não amplia o escopo financeiro aprovado. Não remover/reescrever os fluxos financeiros e técnicos existentes.

## Decisões reconciliadas — 03/11/2026

- O proprietário autorizou explicitamente implementar/testar suspensão local, sem operação em produção. Suspensão bloqueia acesso/admin/cliente, uploads, jobs e mensagens; não apaga registros. Reativação é explícita. A conta proprietária não pode ser suspensa pelo console, evitando perda de acesso global. Sessões ainda vigentes podem voltar a funcionar após reativação; a operação não cria/revoga sessões nem reenvia mensagens antigas por si só.
- Pagamentos iniciados continuam sendo recebidos/conciliados. A exceção interna `bind_financial_reconciliation` é utilizada somente pela inbox assinada e pelos consumidores de pagamentos persistidos; permite commit financeiro de tenant suspenso, sem modificar resolvedores de acesso/acervo. Os demais workers continuam filtrando conta ativa. Mensagens financeiras podem ficar duráveis na fila, sem envio enquanto suspenso.
- Capabilities de consulta/mutação continuam derivadas do `PlatformOwner` persistido, com sessão/vínculo/tenant do ator ativos. Não criar tabela de grants comerciais delegáveis: somente o proprietário administra a plataforma. Monitor/operador não concedem essa autoridade. Schema novo é exclusivamente `platform_admin_event` (0096), sem alterar `AuditEvent` ou grants existentes.
- Toda mutação sensível exige senha atual + TOTP one-time, rate limit, precondição/UUID de idempotência e locks aplicáveis. Replay da mesma intenção não consome outro TOTP; reutilização para outro alvo/ação é recusada. Erros não ecoam credenciais. Sessão, identidade `PlatformOwner`, vínculo e tenant são revalidados imediatamente antes de cada commit com efeitos; qualquer falha reverte a transação. A autorização também é revalidada antes da resposta. Leituras permanecem privadas e revalidam antes de devolver dados.
- Esse gate também cobre concessões/revogações, criação/edição de pacotes e decisões de revisão financeira, embora os formulários e serviços residam na área `/admin/credits`. A autorização owner-only, ledgers e decisões comerciais existentes permanecem; a API exige intenção única e step-up para cada mutação, registra auditoria administrativa transacional sem texto livre e mantém a idempotência financeira já aprovada.
- Durante uma mutação financeira pendente, a interface mantém fixo o tenant selecionado até receber o resultado; ao trocar a busca/tenant, limpa quantidade, referência, senha e TOTP de concessão/revogação. Feedback da fila de revisão permanece junto à fila mesmo sem carteira selecionada.
- Auditoria global contém ator UUID, tenant/objeto UUID, ação permitida, resultado, origem fixa e instante UTC. Não inclui texto arbitrário, IP, conteúdo/PII, senha, código ou segredo. Append-only no PostgreSQL, protegida da limpeza de homologação; sem purge/retention automática inventada. Downgrade recusa remover histórico. A política de retenção definitiva depende de revisão própria, sem exclusão de dados nesta entrega.
- Cadastro é automatizado pelo website, com ativação após e-mail verificado e MFA; decisão explícita substitui aprovação manual anterior. Console não envia convite nem cria credenciais. A task 2.4 passa a verificar essa fronteira; implementação/prova local simples de onboarding pertence à change do portal, autorizada pelo proprietário sem ativação remota.
- A fundação local de backup de `add-platform-backup-recovery` foi concluída em 06/11, mas não tem caller no runtime da aplicação nem é lida pelo console; não usá-la para afirmar saúde de produção. Backup runtime, arquivo de mídia e restauração continuam dependências da 2.7 até existirem fontes duráveis/autenticadas e validação operacional. A quota real do Drive ainda depende da task 3.1 de `add-google-drive-storage-foundation`. Fidelidade continua dependência da 2.9, condicionada às decisões comerciais próprias. Não ligar credenciais externas nem inventar regras para concluir o console. A 2.6 lê somente a autorização Drive e a quota previamente persistidas.

## Fronteira do baseline

- Identidade de proprietário: registro único `PlatformOwner` associado ao UUID do administrador verificado, com referência de autorização. O e-mail informado no bootstrap confirma a conta, mas não é o grant em si.
- Monitor técnico: permissões read-only próprias; `InstallationOperator` acrescenta somente diagnóstico de capacidade. Nenhuma delas concede acesso financeiro ou de administração de tenants.
- Provisionamento: serviço CLI offline, com dry-run e confirmação de UUID; criação de administrador exige credenciais externas. Não deve ser exposto diretamente como endpoint público.
- Dados: `Tenant` tem estado ativo/suspenso; o monitor tem agregados sanitizados de capacidade/filas/alertas. O log comum não modela claramente resultado e origem das ações administrativas.

## Contratos preservados

1. Manter entrada/sessão de fotógrafo e área de proprietário separadas, com autorização no servidor por identidade/permissão persistidas e revalidação antes da resposta e da escrita.
2. Criar capabilities globais para leitura e para mutações explicitamente aprovadas. Grant de monitor ou operador técnico não habilita capability comercial.
3. Mostrar diretório com dados mínimos e contagens por tenant; não oferecer impersonação nem acesso automático a acervo/PII.
4. Suspensão muda somente estado. Nenhuma limpeza, remoção de histórico, cancelamento financeiro, purge de arquivo ou replay de jobs implícito.
5. Cada fonte operacional inclui escopo e timestamp. Backup/Drive indisponível ou ainda sem integração aparece como desconhecido/não configurado, nunca como saudável.
6. Usar log administrativo imutável com ator, tenant, ação, objeto, timestamp, resultado e origem; sanitizar tokens, credenciais, fotografias e dados pessoais.

## Dependências ainda abertas

- Validação real de quota/permissões do Drive segue no gate próprio da change `add-google-drive-storage-foundation`; a leitura do console é apenas do registro persistido e não faz chamada Google. Sources de backup/arquivo/restauração aguardam adapters, origem, quota, retenção e recovery validados (2.7).
- Fidelidade e sua política de regras/eventos/recompensas (2.9).
- Revisão humana, compatibilidade de release, política definitiva de retenção e autorização operacional antes de publicação. Não há purge automático nem migração remota nesta entrega.
