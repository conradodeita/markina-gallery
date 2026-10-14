## Context

Ver proposal.md. O service worker atual só trata navegação offline e não usa CacheStorage. `membership_notifications.py` mantém outbox administrativa; o login usa `client_logged_in:{challenge.id}` e não envia externamente. A criação usa `private_created:{gallery.id}`, inclusive por admin. Pagamentos possuem templates e fluxo externo próprios. Não confundir nenhum desses pontos com os dois novos marcos únicos aprovados.

## Goals / Non-Goals

**Goals:** seis eventos confiáveis, canais independentes, configuração simples e push autenticado para ambos os papéis.

**Non-Goals:** chat, campanhas, notificações de todas as ações, alteração de pagamentos, app nativo, confirmação de leitura, histórico de mensagens para cliente, cache de fotografias ou envio retroativo. Não incluir automaticamente push facial, de entrega final ou de expiração nesta primeira matriz.

## Decisions

### 1. Eventos duráveis e chaves de unicidade

Criar outbox transacional desacoplada dos transportes, com unicidade de chave lógica e entregas por destinatário/canal/dispositivo. Registrar evento na transação da operação de negócio; chamadas externas somente em worker. Persistir snapshots versionados de template e contexto mínimo. Consumidores com lock/lease, backoff e limite de tentativas; retomada após reinício. Desligar canal cancela entregas ainda não iniciadas e retentativas, não pode recolher mensagens já aceitas. Não prometer exactly-once externo diante de resposta ambígua; conservar política de ambiguidade do WhatsApp e usar identificador/tag estável no push para minimizar duplicação visual.

Marcos de primeiro login/seleção por cliente e identidade canônica da galeria: pública e privada derivada da mesma origem são uma jornada, não dois avisos. Conclusão OTP autentica, autorização da galeria é revalidada antes do marco; ao abrir nova galeria com sessão OTP válida, registrar seu primeiro acesso autorizado sem exigir novo OTP. Login sem contexto de galeria não fabrica evento. Primeira seleção tem marcador permanente mesmo depois de desmarcar, separado da existência da privada; reconhecimento e favorito isolados não contam. Migrations sem envios: usar evidências históricas persistidas para marcar eventos já ocorridos; se histórico não comprovar primeiro acesso/seleção de vínculo preexistente, estabelecer baseline silencioso para esse vínculo, sem anunciar evento antigo como novo. Novos vínculos após corte são elegíveis normalmente.

### 2. Lote explícito de uploads privados

Identificar lote durável iniciado pelo upload administrativo e seus ativos aceitos; fechamento explícito ao terminar os envios. Não inferir lote por cada callback de foto nem por uma simples janela de tempo. Persistir contagens/estados para sobreviver a reload e worker restart. Upload abortado/falha pode fechar como parcial com diagnóstico administrativo; só processamentos terminados entram no resumo. Disparar ao terminar o lote com ao menos uma nova prévia convencional protegida pronta e acessível. Falhas não anunciam fotos indisponíveis; nenhuma foto pronta significa nenhum aviso. Retry de lote já anunciado não repete evento; nova sessão de upload é novo lote. Lote aberto abandonado não gera anúncio prematuro; retomada/fechamento recuperável deve estar no fluxo de upload. Não esperar rosto ou ajuste de exposição. Fotos já existentes deduplicadas não contam como novas.

Enviar aos membros ativos que realmente podem acessar as novas fotos privadas, uma vez por lote/cliente; snapshot de destinatários com revalidação de vínculo no envio. Não enviar ao selecionar fotos da pública, definir capa, reprocessar prévias antigas ou regenerar watermark. Clientes vinculados posteriormente não recebem retroativos.

### 3. Matriz, templates e coexistência

Configuração por seis eventos/destinatário, booleanos WhatsApp/push e versão; opções habilitadas como defaults de produto conforme aprovação, mas transporte push tem gate operacional desligado até configuração segura e teste autorizado. WhatsApp usa transporte/número verificado existente. Não converter o gate de notificações legadas em autorização irrestrita de envio: a ativação dos novos eventos deve constar do plano operacional. Templates confirmados/recusados existentes são preservados para WhatsApp e movidos à nova página sem duplicar fonte de verdade. Push tem texto próprio, título até 60 caracteres e corpo até 140; WhatsApp mantém até 500. Contadores e prévia; limite também após interpolação, com abreviação controlada de nomes longos. Variáveis permitidas por evento, texto simples, sem HTML/URLs/dados bancários. Mensagens padrão de cliente neutras, sem nomes de crianças ou dados financeiros na tela bloqueada; dados personalizados podem aparecer nessa tela e a UI informa isso.

Defaults push propostos, editáveis:

| Evento | Título | Corpo |
|---|---|---|
| Primeiro login | Primeiro acesso | {{cliente}} acessou {{galeria}}. |
| Primeira seleção | Seleção iniciada | {{cliente}} começou a escolher em {{galeria}}. |
| Fotos privadas prontas | Novas fotos | Novas fotos disponíveis na sua galeria. |
| Pagamento informado | Pagamento informado | {{cliente}} informou pagamento do pedido {{pedido}}. |
| Confirmação | Pagamento confirmado | Confirmamos o pagamento do seu pedido. |
| Recusa | Pagamento não localizado | Não localizamos seu pagamento. Confira seu pedido. |

Preservar outboxes e auditoria anteriores sem replay, e impedir que os produtores legados dupliquem os seis eventos novos. Registros de logins subsequentes e mudanças de membros continuam auditáveis, mas a obrigação da antiga lista read/unread é supersedida. Mensagens de outros fluxos (OTP, convites, recuperação, reabertura, facial) permanecem fora da central desta versão, com comportamento preservado. A correção silenciosa de pagamento continua silenciosa em ambos os canais.

### 4. Inscrições e transporte Web Push

Adicionar modelo de inscrição por identidade/papel e instalação, com unicidade de endpoint e limite operacional por conta, criptografia dos endpoints/segredos de inscrição e fingerprint para deduplicação. Chave privada VAPID e chave de criptografia separadas em configuração segura; apenas chave VAPID pública pode ir ao navegador. Não usar bancos comuns em texto puro para segredos de inscrição. Endpoints autenticados de registrar/consultar estado/revogar com proteção de origem/CSRF e rate limit; não aceitar ID de destinatário do browser como autoridade.

Transporte via adaptador Web Push padrão para worker, biblioteca mantida com licença/dependências fixadas e verificadas antes de adoção; não desenvolver criptografia própria. Implementação deve documentar allowlist exata dos provedores efetivamente suportados (Chrome/Edge, Firefox e Apple), HTTPS sem userinfo/redirects, rejeição de loopback/privados/link-local e proteção contra DNS rebinding. Nunca tratar endpoint fornecido pelo cliente como URL de fetch genérica. Mensagem cifrada conforme protocolo, timeout, limite de concorrência, 404/410 revogam, 429/5xx retentam com atraso; logs só classes/IDs opacos. TTL curto de uma hora para evitar avisos excessivamente atrasados e expiração durável, sem confundir aceite do provedor com leitura.

Ao sair explicitamente, revogar inscrição da instalação e limpar notificações exibidas quando possível. Troca de conta na mesma instalação invalida associação antiga de forma atômica; não transmitir simultaneamente admin e cliente para a mesma inscrição. Revalidar vínculo/conta antes de enviar. Expiração natural da sessão não exige manter página aberta; clique exige novo login quando necessário. Logout global/revogação de conta revoga suas inscrições; desligar um dispositivo não afeta os outros.

### 5. Service worker e interfaces

Estender o worker existente no mesmo caminho/scope, com handlers push/notificationclick e sem caches de conteúdo privado. Payload só texto curto, identificador de evento e destino interno controlado; não incluir tokens, fotos ou biometria. Permitir apenas rotas conhecidas da aplicação e revalidar autorização no backend. Focar aba existente ou abrir destino seguro; sessão expirada segue login existente. Rejeitar links externos e caminhos arbitrários.

Controle compacto `Ativar notificações` no acesso autenticado admin/cliente e opção de desligar; solicitar permissão somente no clique. Mostrar bloqueio ou instrução de instalação necessária sem modal recorrente. Central `/admin/notifications` usa cards por evento/destinatário, prévia e dois canais; remoção do editor duplicado em Configurações e ajuste dos links de edição dos pagamentos. Não adicionar outra caixa de entrada ao cliente. Larguras 390/768/1440, teclado, estados de salvar/erro e temas claro/escuro.

### 6. Compatibilidade e dependências

Docs primárias consultadas em 14/09/2026: [MDN Push API](https://developer.mozilla.org/en-US/docs/Web/API/Push_API) para ciclo sem página aberta, inscrição e proteção de endpoint/CSRF; [WebKit](https://webkit.org/blog/13878/web-push-for-web-apps-on-ios-and-ipados/) para instalação na tela inicial e permissão por gesto no iOS/iPadOS 16.4+. A aparência, som, truncamento e entrega dependem do sistema, conexão e permissões. Simulação local não substitui entrega real em Android/iPhone.

Persistência dos ativos de marca deve ser reconciliada antes desta implementação conforme a sequência do repositório. Se o reenvio humano bloquear apenas a arte real, registrar e continuar backend/UI de push que não dependam dela; não apresentar teste sintético como validação da instalação oficial. O escopo de 10 MB não foi aprovado como plano e fica separado.

## Risks / Trade-offs

- Avisos na tela bloqueada → defaults mínimos, variáveis restritas e prévia; não prometer privacidade se admin inserir informação pessoal em texto livre.
- Permissão negada/provedor externo indisponível → estado explícito e WhatsApp independente, sem fallback que ignore interruptor.
- Página antiga removida → preservar auditoria e diagnóstico de falhas na operação técnica, sem recriar a caixa de entrada obsoleta.
- Concorrência de seleção/uploads → constraints, locks e eventos transacionais; testes de duas requisições simultâneas e retomada.
- Lote com falhas/abandono → fechamento durável e avisos só sobre fotos realmente disponíveis; não usar processamento facial como gatilho.
- Hospedagem compartilhada → worker limitado, sem novas portas de entrada nem alteração de proxy/DNS; saída HTTPS para provedores identificados exige inventário operacional.

## Migration Plan

Migrations aditivas para configurações, inscrições cifradas, marcos, lotes e outbox; preservar histórico/templates. Reconciliar fontes antigas antes de trocar produtores, nunca drenar duas filas para o mesmo evento. Atualizar mandato/roadmap apenas quanto à nova central, primeiro acesso e canais aprovados, mantendo auditoria de logins. Testes focados locais por tarefa; checks CI obrigatórios preservados, sem suíte completa local nesta rodada. Após implementação, inventário e aprovação de deploy e segredos específicos, backup, migrations e configuração segura com transporte inicialmente desligado. Ativar e testar somente dispositivos/contas de teste aprovados, verificar os seis eventos e canais, rejeição de permissão, clique autenticado e preservação dos terceiros. Rollback operacional desliga push e preserva dados; não executar downgrade destrutivo. Sync/archive somente após revisão humana.
