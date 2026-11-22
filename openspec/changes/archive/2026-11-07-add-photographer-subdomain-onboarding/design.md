# Design

## Context

Decisão expressa de 05/11: escolher o endereço no primeiro acesso após verificar e-mail. Tenant.canonical_host já possui constraint única global; tenant_hosts.py resolve Host exato, ignora X-Forwarded-Host e limita fallback legado. Signup autoativa a conta sem aprovação manual. A migração de autoridade Cloudflare já é observada em 1.1.1.1 e 8.8.8.8; a assinatura nova aguarda caches em change própria. Isso não habilita wildcard/TLS nem provisionamento SaaS.

## Goals / Non-Goals

- Escolha autenticada com indicação clara de reserva e conflito sem revelar o titular de outro nome.
- Concorrência com garantia no banco e identidade derivada da sessão, nunca tenant_id/hostname arbitrário enviado pelo browser.
- Preservar proprietário/legados e impedir que a reserva vire host ativo ou link quebrado anunciado como pronto.
- Não implementar alteração posterior de nome, domínio externo, DNS por cadastro, sessão entre subdomínios, e-mail remetente ou publicação remota nesta entrega.

## Decisions

1. **Uma autoridade de nomes:** reutilizar canonical_host e sua unicidade, evitando um segundo catálogo com corrida entre reserva e host ativo. Adicionar canonical_host_status nullable (`reserved`/`ready`): NULL preserva o contrato dos hosts legados; nova reserva escreve `reserved`. Nenhum endpoint self-service promove para ready.
2. **Reserva não é ativação:** resolvedor e geradores de links recusam hosts reserved. UI mostra texto sem link navegável, distinguindo escolha concluída de preparação pendente. Promoção exige validação operacional DNS/TLS/proxy/isolation e não será simulada por atribuição de estado em produção. Testes sintéticos podem exercitar ready no banco isolado para provar o contrato.
3. **Prefixo:** 1–63 caracteres ASCII, letras/números/hífen, sem hífen nas extremidades. Aparar espaços externos e converter caixa; não aceitar domínio inteiro, porta, path, ponto, underscore, Unicode ou punycode `xn--`. Sugestão derivada do nome por normalização local é editável e não constitui reserva. Base fixa do produto `pickyourpic.com.br`, nunca Host/Forwarded do request.
4. **Reservados:** markina, www, api, admin, app, auth, console, platform, mail, smtp, imap, pop, pop3, support, suporte, status, static, cdn, assets, media, files, storage, drive, webhook, webhooks, billing, payments, pagamentos, dev, test, staging, homolog, localhost. Nomes existentes no catálogo único também são indisponíveis. Lista técnica protege infraestrutura; não atribui aliases novos nem cria hosts.
5. **Transação:** bloquear tenant ativo e revalidar a conta verificada/membership pelo contexto já existente. Primeiro PUT reserva; repetir o mesmo prefixo é idempotente; outro nome para o mesmo tenant retorna conflito sem liberar o anterior. Constraint única resolve corrida entre tenants. Auditoria somente após sucesso, sem senha, e-mail, CPF ou segredos.
6. **UI:** aviso no painel para conta signup elegível sem subdomínio; link leva à primeira etapa em Configurações. A linguagem identifica a escolha como link/URL da marca e esclarece que o prefixo formará um link sob pickyourpic.com.br, evitando confusão com endereço físico. Aviso usa CSS local e fica dentro do contêiner de conteúdo administrativo, alinhado ao painel em telas largas e estreitas; não altera o aviso compartilhado de outros gates. Card com prévia, confirmação de reserva, check de escolha e estado de preparação. Dono/legados não recebem esse fluxo; falha de consulta mostra indisponibilidade na etapa, nunca sucesso. Falha não apaga a entrada.
7. **Compatibilidade e refatoração:** nova coluna sem backfill de host nem alteração de produção. Downgrade recusa se existir estado novo, evitando perder a proteção reserved. Publicação futura deve atualizar todos os consumidores de tenant_hosts antes de permitir reservas; runtime antigo ignora o estado novo, logo não há autorização de rollout misto. Reusar _context/database e construir lógica pequena em módulo próprio.
8. **Recusa opcional sem alerta global:** `_address_context` mantém a recusa de PlatformOwner/contas inelegíveis. Como o hook da etapa já interpreta 403/404 dessa leitura como ausência esperada da funcionalidade, `SessionBoundary` não deve converter somente um `GET /api/admin/onboarding/address` com 403 no aviso global. A exceção é limitada a esse método e caminho; 401 e demais respostas 403 seguem o contrato geral. Nenhum bypass de autorização da API é introduzido.

## Risks / Trade-offs

- Reserva não torna o endereço acessível externamente. Mostrar essa distinção e manter a ativação operacional em gate posterior.
- Nome reservado permanece ocupado inclusive após suspensão; não introduzir reciclagem/expiração que poderia entregar links de outra pessoa.
- Disponibilidade é garantida somente pelo PUT/constraint; não implementar busca pública enumerável nem prometer exclusividade pela prévia.
- URL desconhecida/reservada não pode herdar o proprietário. Cookies host-only e resolvedor continuam preservados; troca de sessão entre hosts não é implementada.

## Migration Plan

Migration aditiva 0105 acrescenta estado nullable e check. Testar upgrade/downgrade vazio e recusa com estado persistido em PostgreSQL sintético local. Nenhuma execução remota nem `.env` alterado. Gate posterior de wildcard/TLS/proxy/ativação precisa plano e autorização próprios.

O runner da demonstração local precisa acompanhar a revisão 0105: modelos que leem a coluna nova não podem usar schema 0104. Atualizar somente a revisão esperada, mantendo os guardas de loopback/ambiente/banco vazio e sem migrar bancos existentes automaticamente.
