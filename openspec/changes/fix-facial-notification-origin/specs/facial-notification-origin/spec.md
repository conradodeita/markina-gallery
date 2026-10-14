## ADDED Requirements

### Requirement: Notificação facial usa a origem pública configurada no deploy

O sistema SHALL transmitir `PUBLIC_APP_ORIGIN` ao worker facial e usá-la prioritariamente nos links de conclusão. Quando ausente, MAY usar `MARKINA_PUBLIC_URL` validada para compatibilidade. Configuração principal inválida SHALL NOT cair silenciosamente no fallback. O caminho SHALL permanecer restrito à galeria da consulta e a mensagem SHALL preservar o acesso autenticado existente.

#### Scenario: Homologação com fallback local legado
- **WHEN** o deploy configura uma origem HTTPS pública e a variável legada ainda contém localhost
- **THEN** o worker produz o link usando a origem HTTPS pública e o caminho da galeria, nunca o fallback local

### Requirement: Origem inválida impede envio

Fora de desenvolvimento/teste local, origem de notificação SHALL usar HTTPS e host não local/público. Origem com localhost, IP não global, credenciais, porta inválida, caminho, query ou fragmento SHALL ser recusada antes de chamar o provedor. Configuração inválida SHALL preservar o tratamento de erro e idempotência existentes, sem envio real nem reenvio automático de mensagens já entregues.

#### Scenario: Worker configurado incorretamente
- **WHEN** o worker de homologação só recebe localhost ou origem principal inválida
- **THEN** nenhum envio é realizado e a outbox registra erro de configuração conforme a política vigente

#### Scenario: Desenvolvimento local
- **WHEN** a execução está explicitamente em desenvolvimento/teste local com URL HTTP válida
- **THEN** o link local continua permitido para testes
