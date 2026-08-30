## Why

O login de cliente e as notificações transacionais já passam por uma abstração WhatsApp, porém homologação permanece no adaptador `sandbox`, que aceita a solicitação sem produzir efeito externo. A validação ponta a ponta agora depende de ativar uma instância Evolution API 2.3.7 + Baileys dedicada à Markina, tornar sua identidade e saúde verificáveis pelo fotógrafo e endurecer o resultado de entrega além de um simples HTTP 2xx.

## What Changes

- Adicionar uma capacidade operacional de transporte WhatsApp real, mantendo `WhatsAppProvider` independente de Evolution/Baileys e o sandbox para testes automatizados e desenvolvimento.
- Vincular cada ambiente a uma única instância dedicada e a um número remetente efetivamente pareado; o painel administrativo exibirá identidade mascarada, estado da conexão e divergências, sem armazenar chave, credencial ou sessão em tabela comum.
- Permitir ao fotógrafo iniciar ou retomar o pareamento seguro da instância autorizada e acompanhar conexão/reconexão; QR ou código de pareamento e confirmação no telefone continuam sendo ações humanas.
- Fazer OTP e mensagens transacionais já especificadas utilizarem o mesmo transporte configurado, preservando regras de negócio, destinatários verificados, templates, auditoria, opt-out quando aplicável e separação entre ambientes.
- Interpretar o corpo real da resposta Evolution, persistir identificador externo e estado de entrega quando disponíveis e tratar recusa, timeout ambíguo, retry e risco de duplicação de maneira explícita.
- Receber somente webhooks necessários ao ciclo de conexão e entrega, autenticados e deduplicados, sem introduzir chat livre, campanhas ou novos eventos de comunicação não previstos nas specs existentes.
- Preparar Compose, persistência, health/readiness e operação de homologação com Evolution API 2.3.7 fixada, isolada dos demais projetos e sem exposição pública desnecessária.

## Capabilities

### New Capabilities

- `messaging/whatsapp-transport`: configuração administrativa segura, identidade remetente pareada, adaptação Evolution/Baileys, estados de conexão e entrega, webhooks, idempotência e operação isolada por ambiente.

### Modified Capabilities

- Nenhuma. O OTP de cliente e as notificações de pagamento já exigem envio por adaptador WhatsApp; esta change fornece o transporte real e sua operação sem alterar as regras desses domínios.

## Impact

- Backend: contrato do provider, persistência operacional de envios, resposta/erros Evolution, webhooks autenticados, endpoints administrativos e health/readiness.
- Frontend: painel `Configurações → WhatsApp` com remetente esperado/conectado, estado, pareamento e diagnóstico sanitizado.
- Infraestrutura: serviço Evolution API 2.3.7 + Baileys, volume exclusivo de sessão, rede interna, configuração segura por ambiente, backup/recuperação e runbook de ativação/rollback.
- Testes e homologação: fake HTTP/provider para automação; dados e telefones sintéticos/próprios; pareamento e recebimento real exigem participação humana e deploy autorizado.
- Segurança: chaves, sessão e dados de pareamento permanecem fora do Git, frontend e tabelas comuns; webhooks e endpoints administrativos usam autenticação, menor exposição e auditoria.
