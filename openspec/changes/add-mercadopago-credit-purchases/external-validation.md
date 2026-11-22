# Roteiro da validação externa — task 4.2

## Pré-condições

- Executar no ambiente local isolado, com `APP_ENV=development` ou `test` e banco descartável. Registrar o commit e a revisão de schema usados.
- Disponibilizar contas e credenciais de teste do Mercado Pago em configuração segura local. Não enviar valores no chat, registrar em Git ou usar configuração de produção.
- O tenant do proprietário configura a conta recebedora como conta de teste; o fotógrafo comprador é outro tenant da aplicação, com carteira finita. Conforme a documentação específica de Orders, os testes por API não exigem criar ou autenticar uma conta compradora Mercado Pago separada; usar e-mail sintético válido e dados públicos de teste do meio de pagamento.
- Criar pacote sintético ativo com quantidade e preço conhecidos. Registrar o saldo inicial do comprador.
- Para callback externo, disponibilizar URL HTTPS de teste que encaminhe apenas à aplicação local de teste; configuração de webhook de produção permanece fora deste roteiro.

## Verificações e evidências

| Cenário | Evidência esperada |
|---|---|
| Preparação e envio pelo checkout transparente | Snapshot do pacote/preço permanece estável; Order pertence à conta de teste do proprietário e à compra do tenant autenticado. Nenhuma venda de fotos é criada. |
| Aprovação por cartão de teste | Consulta autoritativa confirma o valor e recebedor; há um único crédito no ledger, igual à quantidade congelada. |
| PIX nativo Mercado Pago, quando disponível no teste | Checkout apresenta o método do provedor; PIX interno não aparece; saldo fica indisponível enquanto pendente. |
| Recusa ou cancelamento de teste | Compra registra o estado e não cria crédito. |
| Callback assinado e repetido | Inbox aceita assinatura válida, rejeita inválida e o saldo não duplica após replay, inclusive com outro request-id. |
| Callback não entregue e aprovação tardia | Reconciliação consulta a Order existente e credita uma vez sem nova cobrança. |
| Reembolso parcial/total ou chargeback, quando simulável pelo provedor | Estado confirmado abre revisão; uploads e compras ficam bloqueados; ledger não recebe débito automático. |
| Revisão manual | Só PlatformOwner libera ou mantém bloqueio com justificativa; outra revisão pendente continua bloqueando o tenant. |
| Compatibilidade de fotografias | Verificar os meios configurados e o fluxo de checkout de fotos no ambiente de teste, com recebedor do tenant vendedor e registros próprios. |

## Critério de encerramento

- Registrar resultado por cenário como confirmado, falhou ou não executável no ambiente de teste do provedor, com data e evidência sanitizada.
- Evidência mínima: identificadores sintéticos da compra/Order, estados antes/depois, valor e quantidade esperados, saldo antes/depois e contagem de movimentos do ledger. Não registrar tokens, CPF, PAN, CVV, cookies, segredos de webhook ou payloads pessoais integrais.
- Cenário não simulável externamente mantém o limite documentado; testes sintéticos internos não constituem prova de execução do provedor.
- Em 02/11/2026, os resultados e limites foram reconciliados com o proprietário, que aceitou as limitações de simulação registradas em `external-validation-results.md`; a task 4.2 foi concluída. Este roteiro não autoriza pagamento real, mudança de configuração de produção ou deploy.
