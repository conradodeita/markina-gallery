## Context

Consulte `proposal.md` para a motivação e `specs/messaging/whatsapp-transport/spec.md` para o contrato. Hoje `WhatsAppProvider` possui adaptadores sandbox e Evolution, mas o adaptador real apenas faz `POST /message/sendText/{instance}`, aceita qualquer resposta HTTP abaixo de 400 e não preserva corpo, identificador ou estado. OTP chama o provider durante a requisição HTTP; notificações de pagamento usam uma outbox específica. O Compose não instala Evolution e o painel administrativo não conhece a identidade ou a saúde do canal.

A Evolution API 2.3.7 oficial suporta Baileys, criação/conexão/consulta de instância, envio de texto, webhooks configuráveis e estados de conexão. A integração Baileys não é a API oficial da Meta e depende de uma sessão de WhatsApp Web; por isso reconexão, bloqueio por divergência de identidade e rollback para sandbox são requisitos operacionais.

## Goals / Non-Goals

**Goals:**

- Tornar Evolution API 2.3.7 + Baileys um adaptador real substituível, com contrato de resposta e erro tipado.
- Unificar OTP e notificações já implementadas em uma entrega durável, observável e idempotente.
- Oferecer configuração administrativa do número esperado e operação de pareamento sem expor segredos.
- Instalar o provedor em rede e volumes exclusivos da Markina, sem porta pública.
- Permitir homologação real com telefone próprio e dados sintéticos.

**Non-Goals:**

- Criar inbox/chat livre entre cliente e fotógrafo, chatbot, campanhas ou responder automaticamente mensagens recebidas.
- Implementar agora todos os eventos futuros da Fase 6; novos templates e gatilhos continuam exigindo specs próprias.
- Usar o número digitado como autorização de remetente ou guardar sessão/chave Evolution em tabela comum.
- Migrar para WhatsApp Cloud API oficial da Meta nesta change.

## Decisions

### 1. A instância conectada, e não o campo de telefone, define o remetente

O painel armazenará somente o número esperado, normalizado em E.164, e metadados operacionais não secretos. O backend consultará a instância dedicada e só considerará o canal `ready` quando estado e identidade conectada coincidirem. Como Baileys pode devolver para contas brasileiras o JID legado sem o nono dígito, a igualdade canônica aceita exclusivamente a inserção/remoção de um `9` na posição posterior a `+55` e ao DDD, desde que todo o restante seja idêntico; país, DDD ou qualquer outra diferença continuam em fail closed. A troca do número esperado move o canal para `pending_pairing`; ela não altera magicamente o remetente.

Alternativa descartada: um campo livre `número remetente` que seja usado no payload. Baileys envia pelo dispositivo pareado e não permite provar posse apenas com texto configurado.

### 2. Segredos em ambiente seguro; operação mediada pela API Markina

URL interna, API key, nome fixo da instância, segredo de webhook e chave de criptografia dos payloads OTP continuam no arquivo seguro do ambiente. Endpoints administrativos da Markina consultam/criam a instância e obtêm QR ou código efêmero; o navegador nunca fala diretamente com a Evolution nem recebe sua chave. Respostas administrativas mascaram telefones e não persistem material de pareamento.

Alternativa descartada: expor Evolution Manager ou a API Evolution no proxy público. Isso amplia a superfície e permitiria contornar autorização/auditoria da Markina.

### 3. Outbox genérica para toda entrega WhatsApp implementada

Será criada uma entrega genérica que referencia tipo de evento, objeto de origem, destinatário autorizado, template/versionamento, chave idempotente, validade, tentativas, estado, identificador externo e erro sanitizado. Registros da outbox de pagamento serão migrados de forma aditiva ou compatibilizados durante a transição, preservando histórico e a primeira decisão financeira.

OTP também será enfileirado. Como o código precisa chegar ao worker mas não pode ficar em texto puro, o payload efêmero será cifrado de forma autenticada com chave exclusiva do ambiente e apagado quando aceito, expirado ou encerrado; o hash do desafio continua sendo a fonte de validação. A API retorna a resposta neutra imediatamente e o worker prioriza OTP pela validade curta.

Alternativas descartadas: manter OTP síncrono, contrariando a fila prevista e tornando a requisição dependente do provedor; armazenar código em texto puro; usar apenas Redis sem registro durável e auditável.

### 4. Estados internos distinguem aceitação de entrega

O provider retornará um resultado tipado com identificador externo, destinatário normalizado e estado inicial. A entrega avançará por estados como `queued`, `processing`, `accepted`, `delivered`, `read`, `failed`, `unknown` e `expired`. O corpo Evolution 2.3.7 será validado; HTTP 2xx sem chave/destinatário coerentes vira `unknown`, nunca `delivered`.

Atualizações autenticadas do provedor poderão avançar o estado monotonicamente. O sistema não reverte `delivered/read` por eventos atrasados nem repete regras de negócio em webhooks.

Alternativa descartada: conservar o estado único `sent`, que mistura aceitação HTTP, envio ao WhatsApp e entrega ao aparelho.

### 5. Timeout ambíguo exige reconciliação antes de retry

Falhas comprovadamente anteriores à aceitação podem retornar à fila. Timeout, EOF ou queda depois do envio geram `unknown`; um job separado consulta o provedor quando houver identificador, correlaciona por metadados seguros disponíveis ou aguarda uma janela antes de liberar reenvio controlado. A chave idempotente local impede duplicidade de evento, mas o cabeçalho `Idempotency-Key` não será tratado como garantia do provedor sem evidência oficial.

Alternativa descartada: retry imediato de todo timeout, que pode duplicar OTP ou notificação já aceita.

### 6. Webhook interno mínimo

A Evolution será configurada para enviar apenas atualizações de conexão e mensagem necessárias. O webhook apontará para a API Markina pela rede interna e incluirá header secreto dedicado. O backend limitará corpo, validará header em tempo constante, deduplicará por impressão do evento/identificador e ignorará conteúdo recebido fora de fluxos futuramente especificados.

Alternativa descartada: habilitar todos os eventos ou usar mensagens recebidas como comandos implícitos.

### 7. Infraestrutura dedicada dentro do projeto Markina

O Compose adicionará `evolution-api`, `evolution-db` e `evolution-redis`, todos sem `ports`, na rede interna e com volumes nomeados exclusivos. A imagem Evolution será fixada em `2.3.7` e no digest verificado durante a implementação; PostgreSQL e Redis também serão fixados a versões compatíveis. O frontend Manager não será instalado. Healthchecks da Markina distinguirão API Evolution viva, instância conectada e canal pronto.

Alternativa considerada: reutilizar PostgreSQL/Redis da aplicação. Foi rejeitada para o primeiro rollout porque credenciais e comandos de um provedor comprometido ampliariam o impacto sobre sessões, filas e dados principais.

### 8. Abstração preserva futura Meta Cloud API

O domínio dependerá de operações como `send`, `connection_status`, `sender_identity` e `reconcile`, não de DTOs Evolution. O adaptador traduz payloads e estados. QR/pairing é uma extensão operacional Baileys separada do envio, permitindo outro adaptador substituir o canal sem reescrever OTP, pagamentos ou futuras entregas.

## Risks / Trade-offs

- [Baileys é integração não oficial e pode desconectar ou sofrer bloqueio] → usar número exclusivo, mostrar estado, persistir sessão, bloquear envio quando degradado e manter caminho de futura migração para Meta.
- [Mensagem pode ser aceita durante timeout e duplicada] → estado `unknown`, reconciliação e ausência de retry cego.
- [Outbox de OTP aumenta latência] → prioridade própria, worker saudável, validade explícita e métrica de tempo até aceitação.
- [Payload OTP cifrado ainda é material sensível] → chave fora do banco, AEAD, TTL curto, limpeza após uso e nenhuma emissão em logs.
- [Três serviços extras consomem recursos do Oracle] → inventário pré-deploy, limites de recursos e healthchecks; nenhum serviço ou volume de terceiro é alterado.
- [Webhook falso altera diagnóstico] → rede interna, segredo dedicado, comparação constante, limites e deduplicação.
- [O número configurado pode divergir do dispositivo pareado] → fail closed até coincidência verificada.

## Migration Plan

1. Implementar modelos/migration aditivos, contrato do provider, fake Evolution e testes sem efeitos externos.
2. Migrar OTP e notificações de pagamento para a outbox genérica preservando registros e mantendo `sandbox` como padrão.
3. Implementar endpoints administrativos, painel de estado/pareamento, webhook e documentação operacional.
4. Adicionar os serviços Evolution isolados ao Compose com perfis/configuração que não ativem efeitos externos por padrão; validar configuração, persistência e reinício local com dados sintéticos.
5. Antes de homologação, apresentar inventário, portas (nenhuma nova pública), volumes, consumo estimado e plano de rollback. Aguardar autorização explícita para alterar infraestrutura/deploy.
6. Após deploy autorizado, solicitar ao proprietário somente o telefone próprio de homologação e a ação de QR/pairing; confirmar identidade, executar OTP real e mensagens transacionais sintéticas, reiniciar controladamente e repetir a validação.
7. Em rollback, desativar efeitos externos pelo provider sandbox, preservar outbox/auditoria e manter volumes Evolution para recuperação; não apagar sessão, banco ou filas automaticamente.

## Open Questions

- O digest publicado para a imagem oficial `evoapicloud/evolution-api:2.3.7` será registrado no runbook depois de verificação no registry durante a implementação; a versão funcional permanece fixada em 2.3.7.
