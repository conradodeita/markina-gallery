# Spec Delta

## REMOVED Requirements

### Requirement: Operação restrita a um fotógrafo nesta etapa

**Reason**: A transição aprovada em `add-small-multi-photographer-pilot` substitui o gate global de conta única por propriedade, contexto inequívoco e isolamento integral das contas. Suspensão continua negando operações da conta afetada, preservando o funcionamento autorizado das demais.

**Migration**: Aplicar 0070/0071 somente depois dos testes de preservação, isolamento e prontidão e da autorização operacional do pacote. Preservar a conta e os vínculos legados. Não selecionar primeira conta nem criar automaticamente outro fotógrafo; provisionamento remoto continua explícito. A spec consolidada permanece inalterada até revisão humana desta change.
