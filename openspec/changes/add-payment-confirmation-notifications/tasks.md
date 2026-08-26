## 1. Pagamento manual e persistência

- [ ] 1.1 Criar migration aditiva para comunicação de pagamento, decisão imutável, templates controlados e caixa de saída, verificando upgrade e downgrade em banco sintético.
- [ ] 1.2 Implementar API autorizada para o cliente comunicar pagamento próprio e verificar testes de isolamento e idempotência.
- [ ] 1.3 Implementar API administrativa para listar, confirmar ou recusar comunicações e verificar auditoria, estado financeiro e histórico do cliente.

## 2. Notificações transacionais

- [ ] 2.1 Implementar porta WhatsApp, worker de caixa de saída, limite de tentativas e configuração exclusiva por ambiente, verificando testes com adaptador sintético.
- [ ] 2.2 Implementar templates de confirmação e recusa com variáveis controladas, verificando validação, renderização e ausência de dados sensíveis em logs.
- [ ] 2.3 Enfileirar aviso ao fotógrafo e resposta ao cliente a partir das transições válidas, verificando que reexecuções não duplicam decisão ou mensagem.

## 3. Interface, qualidade e operação

- [ ] 3.1 Implementar telas de comunicação do cliente, revisão do fotógrafo e configuração de mensagens, verificando estados pendente, confirmado, recusado e entrega falha.
- [ ] 3.2 Cobrir autorização, idempotência, limites, tentativas, destino verificado e privacidade com testes automatizados.
- [ ] 3.3 Validar lint, build, migrations, OpenSpec e homologação exclusivamente com dados sintéticos e adaptador sandbox.
- [ ] 3.4 Atualizar documentação de segredos, ativação do provedor, templates e procedimento de rollback, verificando que nenhuma credencial é versionada.
