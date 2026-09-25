## 1. Revisão e persistência

- [x] 1.1 Registrar no início da implementação a revisão humana já recebida sobre reenvio explícito e pagamento confirmado, e preparar branch a partir de develop preservando o diff local anterior; reconciliar mandato/roadmap para rótulos verde/cinza, gate financeiro e sétimo evento configurável. Verificar escopo pelo diff e pela referência à decisão nesta change.
- [x] 1.2 Adicionar campos de link, data UTC e revisão no pedido com migration aditiva; validar upgrade com pedido preexistente, valor inicial indisponível e preservação de dados em teste SQLite e PostgreSQL quando disponível, registrando eventual limitação.
- [x] 1.3 Implementar validação de URLs Google Photos com testes de link curto/completo, parâmetros, espaços, vazio, tamanho, esquemas, credenciais, portas e domínios enganosos; demonstrar rejeição sem rede e sem alterar o link anterior.

## 2. Entrega e notificações no backend

- [x] 2.1 Registrar `order_delivery_ready` na central com textos, variáveis, limites e canais existentes; testar leitura/edição do sétimo evento e preservação dos seis anteriores, sem replay ao ativar canais.
- [x] 2.2 Implementar endpoint administrativo com pagamento confirmado, transação, controle de revisão, auditoria sem URL e evento durável na mesma transação; testar criação, edição, remoção permitida mesmo sem confirmação, rollback, repetição idempotente, conflito concorrente, isolamento por pedido/cliente e ausência de alteração de valores, itens e decisões financeiras.
- [x] 2.3 Implementar revalidação da entrega no worker por propriedade, pagamento confirmado e revisão do pedido, sem dependência de galeria operacional; validar com provedores falsos canais independentes, TTL/retentativas, link removido/substituído, cliente indevido, galeria expirada/removida e falha de transporte sem desfazer a entrega.
- [x] 2.4 Projetar link/data/revisão/capacidades para administração e link autorizado para Compras somente em pedidos confirmados, sem N+1; testar ausência de exposição anônima/entre clientes/não confirmados, pedidos individuais/agrupados e persistência após expiração ou remoção de acervo.
- [x] 2.5 Invalidar a revisão de entrega na correção financeira, preservando o link administrativo e ocultando-o da cliente até reconfirmação; testar todos os pedidos com link em PIX agrupado, correção/reconfirmação antes do worker, ausência de replay e concorrência com disponibilização seguindo a ordem existente dos locks.
- [x] 2.6 Implementar Reenviar aviso com versão e UUID de operação, usando o evento existente e os canais atualmente habilitados; testar mesma URL com novo aviso deliberado, repetição do UUID sem duplicação, retorno após falha de rede, revisão desatualizada, ausência de link, pagamento não confirmado e remoção/substituição antes do worker.

## 3. Interface administrativa e cliente

- [x] 3.1 Substituir histórico visual pelo campo Google Photos e botão Enviar, com edição, remoção confirmada e estados de gravação/agendamento; testar bloqueio explicado sem pagamento confirmado, ausência de histórico, digitação sem envio, falha com rascunho preservado, sucesso persistido e canais desligados.
- [x] 3.2 Exibir botão verde Fotos disponíveis somente com link autorizado e pagamento confirmado, ou cinza Fotos indisponíveis nos demais casos, fora das prévias em Compras, com âncora de pedido para push; testar destino externo seguro, suspensão/reconfirmação financeira, prévias/ampliação preservadas, atualização ao foco e pedidos de PIX agrupado.
- [x] 3.3 Validar o novo evento na tela Notificações com controles e textos existentes; testes de componente devem comprovar configuração independente e evitar afirmação de entrega/leitura quando apenas houve agendamento.
- [x] 3.4 Incluir Reenviar aviso com confirmação e proteção contra duplo clique; testar UUID estável na repetição da mesma ação, novo UUID na próxima ação deliberada, bloqueio com rascunho diferente do link salvo e indisponibilidade sem link ou pagamento confirmado.

## 4. Integração e entrega para revisão

- [ ] 4.4 Corrigir as falhas do CI do PR #98: reconciliar expectativa do histórico com o novo campo de entrega e tratar o falso positivo sintético do gitleaks com exceção exata; reproduzir, validar e publicar correção sem merge/deploy.

- [x] 4.1 Executar regressões pertinentes de pagamentos/correções, histórico, notificações e migração; lint backend/frontend, typecheck, build e OpenSpec estrito. Registrar comandos, resultados e limites em validation.md sem marcar validações indisponíveis como concluídas.
- [x] 4.2 Validar navegador com dados sintéticos em mobile/desktop e temas claro/escuro: formulário, Compras com/sem link, prévias, foco/teclado, contraste, ausência de overflow e nova configuração. Registrar evidências sem envio real ou álbuns pessoais.
- [x] 4.3 Revisar diff e preparar commit/push + PR somente desta change após implementação autorizada; anexar PR e registrar continuidade. Parar após push aguardando confirmação humana do CI. Merge, publicação, homologação remota e sincronização/arquivamento dependem das respectivas etapas humanas do processo.
