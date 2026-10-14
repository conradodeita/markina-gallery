# Notificações transacionais — Pick-your-Pic

Implementação da change `configurable-push-and-whatsapp-notifications`. Validação local não significa transporte habilitado em homologação/produção.

## Central e eventos

`/admin/notifications` substitui a listagem antiga por configuração global. Cada evento tem título/corpo de push, texto WhatsApp, duas opções independentes de envio e prévia. Alterar afeta todos os clientes; as mensagens podem aparecer na tela bloqueada. Usar texto simples, variáveis listadas, sem URLs, HTML, dados bancários ou dados sensíveis. Push: título 60/corpo 140 caracteres em uma linha; WhatsApp: 500. Nomes longos são abreviados no snapshot. Não há caixa de entrada nova para cliente.

| Evento | Destinatário | Marco |
|---|---|---|
| Primeiro acesso | Fotógrafo | Primeiro acesso autorizado por cliente/galeria canônica, inclusive com sessão existente |
| Primeira seleção | Fotógrafo | Primeira seleção persistida; favorito/busca/criação administrativa não contam |
| Novas fotos | Clientes autorizados da privada | Lote encerrado e ao menos uma nova prévia protegida acessível; não espera reconhecimento ou ajuste |
| Pagamento informado | Fotógrafo | Comunicação persistida pelo cliente |
| Pagamento confirmado | Cliente do pedido | Decisão confirmada do fotógrafo |
| Pagamento recusado | Cliente do pedido | Decisão de pagamento não localizado |

Desmarcar/reselecionar não repete marco. Lote aberto pode ser retomado ou encerrado parcialmente no upload privado; falha total não avisa. Novos vínculos posteriores ao lote não recebem retroativo. Correção financeira silenciosa continua sem mensagens.

## Configuração externa (não configurada automaticamente)

Somente `api` e worker geral recebem os placeholders do Compose. Não são abertas novas portas. Arquivos reais de ambiente e chaves exigem autorização específica e editor seguro no servidor; nunca colar valores em conversa/log, frontend, Git ou argumentos de shell.

| Variável | Finalidade |
|---|---|
| `WEB_PUSH_ENABLED` | Gate do transporte push; padrão `false` |
| `TRANSACTIONAL_WHATSAPP_ENABLED` | Gate dos três eventos novos via WhatsApp; padrão `false`. Pagamentos preservam ativação anterior e respeitam interruptor da central |
| `WEB_PUSH_VAPID_PUBLIC_KEY` | Chave pública P-256, ponto não comprimido em base64url; única chave enviada ao navegador |
| `WEB_PUSH_VAPID_PRIVATE_KEY` | Chave privada VAPID codificada em base64url, nunca caminho de arquivo; par gerado por ferramenta padrão py-vapid |
| `WEB_PUSH_VAPID_SUBJECT` | Contato operacional `mailto:` do responsável pelo serviço |
| `PUSH_SUBSCRIPTION_ENCRYPTION_KEY` | Chave Fernet separada, usada para cifrar endpoint e chaves da inscrição |

Usar um par VAPID por ambiente e conservá-lo entre deploys. A API verifica correspondência do par/contato antes de oferecer ativação. Rotação exige procedimento de reinscrição; não substituir chaves em produção de forma improvisada. Não há novo fornecedor WhatsApp: usa adaptador, estado de conexão e número verificado existentes, inclusive número do fotógrafo.

## Segurança e ciclo de vida

- Cadastro/revogação autenticados em `/push/subscription`; origem obrigatória nas mutações, rate limit, máximo dez dispositivos/conta. Identidade sempre da sessão, não do payload.
- Endpoint e chaves cifrados com identidade/geração vinculadas. Cookie opaco HttpOnly identifica instalação; unicidade de endpoint impede associação a duas contas. Logout explícito/global e troca de conta invalidam inscrições. Desligar um dispositivo não altera os outros.
- Permissão pedida apenas em clique. iPhone/iPad no navegador recebe instrução para abrir instalação da Tela de Início. Permissão negada não repete prompts automaticamente. Sistema/conexão podem atrasar ou silenciar mensagens; instalação não garante recebimento.
- Natural expiração da sessão não revoga push. Clique abre rota interna conhecida; APIs mantêm autenticação e autorização existentes, inclusive se for necessário novo login. Payload não transporta fotos, OTP, token, PIX nem biometria.
- Service worker existente preserva fallback offline, sem CacheStorage privado. Tag estável reduz duplicação visual. Logout solicita fechamento das notificações já exibidas, quando suportado.
- Transporte: `fcm.googleapis.com`, `updates.push.services.mozilla.com`, subdomínios de `push.apple.com` e `notify.windows.com`; HTTPS/443, sem userinfo ou redirects. DNS rejeita qualquer IP não global; conexão fixada no IP validado, mantendo certificado/SNI do hostname. Nada de proxies herdados, corpos de resposta ou credenciais em logs. Licenças/versões: `openspec/changes/configurable-push-and-whatsapp-notifications/transport-review.md`.

## Entrega e compatibilidade

Evento e entregas persistidos na transação do negócio; worker separado do request realiza envio. Snapshot imutável por versão. TTL de uma hora, lease de 60 segundos, até três tentativas com backoff de 30/60 segundos; DNS até 3 s e operação HTTPS até 8 s por estágio. 404/410 revogam inscrição. 429/5xx retentam enquanto elegíveis. WhatsApp ambíguo ou tentativa interrompida não é reenviado automaticamente. Cada canal avança independentemente.

`accepted` significa aceite do provedor, não leitura. Falha não desfaz pagamento, seleção ou upload. Desligar canal cancela fila/retries; não recolhe mensagens aceitas. Editar/religar não reenvia histórico. Snapshots e inscrições nunca são serializados em APIs administrativas genéricas; IDs técnicos/estados são suficientes para diagnóstico. Exclusões de entidades preservam as regras comerciais existentes; as novas relações usam as cascatas da migration.

Migration aditiva `20260914_0056`: preserva dados/outboxes antigas e copia templates; baseline silencioso para vínculos anteriores, sem envios. `PaymentNotificationOutbox` é projeção técnica para os cards financeiros quando há `NotificationEvent` com a mesma chave; o materializador antigo exclui essas chaves. Outboxes históricas sem novo evento mantêm pipeline anterior. Não drenar duas filas para o mesmo evento.

## Implantação e rollback

1. Reconciliar dependência `persist-branding-assets-across-deploys`; os ativos oficiais ausentes exigem reenvio humano. Não substituir esse aceite por ícone sintético.
2. Apresentar inventário atual, containers próprios, SHA, porta/subdomínio e plano de impacto zero; obter autorização específica para deploy e configuração externa das chaves. Nenhum recurso de terceiros deve mudar.
3. PR/CI, backup operacional, migration, aplicação e worker geral na mesma versão. Inicialmente gates novos desligados; saúde e histórico preservados. Não executar downgrade sobre dados preenchidos.
4. Após autorização de teste, configurar chaves externamente e habilitar transportes para contas/dispositivos aprovados. Gerar somente eventos novos de teste. Conferir admin/cliente Android e iPhone instalado, página fechada, clique autenticado, seis eventos, ambos os canais e interruptores.
5. Rollback operacional: desligar gates novos, preservar chaves/dados/histórico e versão de schema; não apagar filas nem inscrições indiscriminadamente. Reativação respeita cancelamento/TTL, sem replay. Não marcar aceite final sem teste real e revisão humana.

## Validação cirúrgica

Backend: arquivos `test_notification_*`, `test_private_upload_batches.py`, `test_push_subscriptions.py`, `test_web_push.py`, `test_transactional_notification_migration.py`, sempre com `DATABASE_URL` SQLite temporário exclusivo. Acrescentar somente testes antigos dos fluxos tocados. Não executar suíte completa local.

Frontend: testes de notificações, controles/SW, configurações e superfícies tocadas, typecheck/lint/build. `frontend/scripts/notification-visual-qa.cjs` aceita `PLAYWRIGHT_MODULE`, usa apenas localhost:3035, mocks sintéticos e navegador Edge headless; gera capturas/resultados fora do Git em `.codex-tmp/notification-qa`. Se necessário, escolher Chrome via `NOTIFICATION_QA_BROWSER=chrome`. Não equivale a envio real.
