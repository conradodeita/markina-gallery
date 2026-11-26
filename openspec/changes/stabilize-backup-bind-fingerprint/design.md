> **SUPERCEDIDA — NÃO IMPLEMENTAR NEM DESPACHAR.** Este fluxo de bind-and-rehearse e seu vínculo com o Picker foram cancelados em 25/11/2026. Mantido apenas para auditoria. Consulte [retire-platform-backup-runtime](../retire-platform-backup-runtime/proposal.md) e [prove-open-source-backup-and-recovery](../prove-open-source-backup-and-recovery/proposal.md).

## Decisions

Selecionar a mesma projeção v2 para install e bind-and-rehearse no workflow. Para bind-and-rehearse, conferir o campo v2 novamente no wrapper sob o lock, com precondições atuais de instalação e disponibilidade de espaço, antes de gravar o vínculo. Reconcile mantém comparação integral e comportamento anterior.

O vínculo continua exigindo runtime instalado no SHA/pacote exato da operação. Depois de CI e merge autorizados, preparar suporte e instalar de forma inerte o pacote desse SHA com autorização própria. Solicitar nova seleção do Picker apenas quando o vínculo estiver pronto para disparo.
