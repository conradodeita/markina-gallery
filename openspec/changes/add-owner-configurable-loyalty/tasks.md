# Tasks: Programa de fidelidade configurável

- [x] 1.1 Decisão do proprietário em 07/11/2026: adiar o programa de fidelidade para depois do primeiro release; não definir regras comerciais agora, nem criar defaults ativos.
- [ ] 1.2 Depender da autorização global/comercial da Fase 5 e do contrato de ledger da carteira Fase 2; provar que grants técnicos e sessão de fotógrafo não concedem administração.
- [ ] 2.1 Revisar produtores de eventos comerciais relevantes e definir atomicidade/idempotência entre evento de origem, pontos, recompensa e ledger de crédito.
- [ ] 2.2 Aprovar schema versionado e migration aditiva para regras, pontos, recompensas e referências de origem; testar PostgreSQL vazio/atual, constraints, concorrência e rollback.
- [ ] 3.1 Implementar configuração de regras sem valores padrão, capability global e trilha de auditoria.
- [ ] 3.2 Implementar ledger/histórico de pontos e recompensa idempotente, integrando ao ledger de créditos somente por evento referenciado.
- [ ] 3.3 Implementar telas do proprietário e do fotógrafo com autorização, isolamento, responsividade e estados vazios claros.
- [ ] 4.1 Validar replay/concorrência, suspensão de regra, saldo reconstruível, reversões, isolamento PostgreSQL e integração wallet; executar lint/typecheck/build/OpenSpec e revisar diff.


## Adiamento

As tasks 1.2–4.1 permanecem pendentes e adiadas junto com a feature. Retomá-las somente quando o proprietário decidir incluir fidelidade e especificar eventos, critérios, quantidades, conversão, benefícios, validade e tratamento de estornos/chargebacks. Não marcar implementação ou testes como concluídos.
