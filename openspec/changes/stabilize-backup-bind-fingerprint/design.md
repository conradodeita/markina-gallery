## Decisions

Selecionar a mesma projeção v2 para install e bind-and-rehearse no workflow. Para bind-and-rehearse, conferir o campo v2 novamente no wrapper sob o lock, com precondições atuais de instalação e disponibilidade de espaço, antes de gravar o vínculo. Reconcile mantém comparação integral e comportamento anterior.

O vínculo continua exigindo runtime instalado no SHA/pacote exato da operação. Depois de CI e merge autorizados, preparar suporte e instalar de forma inerte o pacote desse SHA com autorização própria. Solicitar nova seleção do Picker apenas quando o vínculo estiver pronto para disparo.
