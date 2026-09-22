## 1. Origem e validação

- [x] 1.1 Repassar origem canônica ao worker facial e resolver link com precedência explícita; testar Compose e compatibilidade legada. Evidência: `validation.md`, 91 testes da origem e Compose resolvido para cinco serviços.
- [x] 1.2 Recusar URLs impróprias antes do envio; testar mensagem completa, origem principal inválida, ambientes e ausência de chamada ao provedor sem afetar outbox/idempotência. Evidência: `validation.md`, suíte de origem e regressão do worker.

## 2. Entrega

- [x] 2.1 Executar testes backend pertinentes, ruff, validação Compose/OpenSpec e diff; registrar evidências e preparar PR. Evidência: `validation.md`; publicação na branch `feature/fix-facial-notification-origin`, com PR para `develop`.

Pedido autoriza corrigir o defeito. Após push + PR, parar e aguardar confirmação humana do CI. Sem deploy, envio real de mensagem ou mudança de `.env` nesta execução. Sincronização/arquivo somente após revisão humana. Trabalho local de outras changes preservado.
